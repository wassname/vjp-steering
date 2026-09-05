"""One resumable entrypoint for formative MLP-up experiments."""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import torch
from loguru import logger
from steering_lite import Vector
from steering_lite.data import make_persona_pairs
from transformers import AutoModelForCausalLM, AutoTokenizer

import walk
from vjp_steering.j_lens_concept import concept_spec, extract_concept, implementation_hash, prefill_diagnostics
from vjp_steering.experiment import (
    DEFAULT_EXPERIMENT_IDS,
    DEV,
    FULL,
    METHODS,
    experiment_dir,
    manifest_path,
)
from vjp_steering.vjp import (
    J_LENS_SWAP_SOURCE,
    J_LENS_SWAP_TARGET,
    JLensSwap,
    JLensSwapC,
    _load_j_lens,
    _swap_lens_coordinates,
    _transfer_lens_coordinate,
    j_lens_swap,
    vjp_mlp_up_left_right_shrink,
    vjp_mlp_up_shared_eb,
    vjp_mlp_up_shared_last_token_eb,
)


EXTRACTORS = {
    "vjp_mlp_up_left_right_shrink": vjp_mlp_up_left_right_shrink,
    "vjp_mlp_up_shared_eb": vjp_mlp_up_shared_eb,
    "vjp_mlp_up_shared_last_token_eb": vjp_mlp_up_shared_last_token_eb,
}


SEARCH_BUDGET = 10
SEARCH_LOG_TOLERANCE = math.log(2.0) / 6.0
GRID_LOW = 0.66
GRID_HIGH = 1.33
GRID_POINTS = 9
J_LENS_SWAP_POSITIVE_GRID = (0.5, 1.0, 1.125, 1.25, 1.375, 1.5, 1.625, 1.75, 2.0, 3.0, 4.0, 6.0, 8.0)
J_LENS_SWAP_NEGATIVE_GRID = J_LENS_SWAP_POSITIVE_GRID
J_LENS_CONCEPT_GRID = (1.0, 4.0, 16.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("method", choices=METHODS)
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--gpu-stage", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--concept-smoke", action="store_true")
    parser.add_argument("--concept-calibrate", action="store_true")
    parser.add_argument("--source-experiment", default="j-lens-concept-dev-v1")
    parser.add_argument("--reuse-extraction-from", default="")
    parser.add_argument("--lens-file", type=Path)
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--experiment-id", default="")
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", choices=("float32", "bfloat16"), default="bfloat16")
    parser.add_argument("--n-pairs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--extract-batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--coefficients-plus", default="")
    parser.add_argument("--coefficients-minus", default="")
    parser.add_argument("--verify-extraction", action="store_true")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--j-lens-diagnostic", action="store_true")
    parser.add_argument(
        "--diagnostic-output",
        default="outputs/audits/20260905_j_lens_paper_native/diagnostic.json",
    )
    args = parser.parse_args()
    args.experiment_id = args.experiment_id or DEFAULT_EXPERIMENT_IDS[args.method]
    return args


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def atomic_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def coefficient_slug(coefficient: float) -> str:
    return f"{coefficient:.12g}".replace(".", "p").replace("-", "m")


def cell_path(root: Path, side: str, coefficient: float) -> Path:
    side_slug = "plus" if side == "+C" else "minus"
    return root / "cells" / side_slug / f"c{coefficient_slug(coefficient)}.jsonl"


def probe_path(root: Path, side: str, coefficient: float) -> Path:
    side_slug = "plus" if side == "+C" else "minus"
    return root / "probes" / side_slug / f"c{coefficient_slug(coefficient)}.jsonl"


def signed_coefficient(side: str, coefficient: float) -> float:
    return coefficient if side == "+C" else -coefficient


def applied_coefficient(method: str, side: str, coefficient: float) -> float:
    return coefficient if method == "j_lens_swap" else signed_coefficient(side, coefficient)


def vector_sha256(vector: Vector) -> str:
    digest = hashlib.sha256()
    for kind, tree in (("shared", vector.shared), ("stacked", vector.stacked)):
        for layer, tensors in sorted(tree.items()):
            for name, tensor in sorted(tensors.items()):
                value = tensor.detach().contiguous().cpu()
                digest.update(f"{kind}:{layer}:{name}:{value.dtype}:{tuple(value.shape)}".encode())
                digest.update(value.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def load_model(args: argparse.Namespace):
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        dtype=getattr(torch, args.dtype),
        attn_implementation="sdpa",
    ).to(args.device).eval()
    return model, tokenizer


def extraction_prompts(args: argparse.Namespace, tokenizer) -> tuple[list[str], list[str]]:
    positive, negative = make_persona_pairs(
        tokenizer,
        n_pairs=args.n_pairs,
        thinking=True,
        persona_pairs=walk.PERSONAS,
        template=walk.PERSONA_TEMPLATE,
        seed=0,
    )
    if len(positive) != len(negative) or not positive:
        raise ValueError("persona extraction pairs are empty or unpaired")
    lengths = tokenizer(positive + negative, add_special_tokens=False)["input_ids"]
    if max(map(len, lengths)) > args.max_length:
        raise ValueError("extraction prompt truncation")
    return positive, negative


def extract_vectors(args: argparse.Namespace, model, tokenizer) -> tuple[dict[str, Vector], dict, int, str]:
    if args.method == "j_lens_concept":
        layers = walk.resolve_layers(model, None)
        rows, _ = walk.read_cohort(DEV.cohort_size)
        vectors, metadata = extract_concept(
            model, tokenizer, layers, batch_size=args.extract_batch_size,
            max_length=args.max_length, dev_prompts=walk.generation_inputs(tokenizer, rows),
            lens_file=args.lens_file,
        )
        return vectors, metadata, 0, "concept:" + metadata["spec_sha256"]
    if args.method == "j_lens_swap":
        layers = walk.resolve_layers(model, None)
        positive, positive_metadata = j_lens_swap(
            model, tokenizer, layers,
            source_token=J_LENS_SWAP_SOURCE, target_token=J_LENS_SWAP_TARGET,
        )
        negative, negative_metadata = j_lens_swap(
            model, tokenizer, layers,
            source_token=J_LENS_SWAP_TARGET, target_token=J_LENS_SWAP_SOURCE,
        )
        return {
            "+C": positive,
            "-C": negative,
        }, {
            "source_layers": list(layers),
            "semantic_directions": {"+C": positive_metadata, "-C": negative_metadata},
        }, 0, f"fixed_tokens:{J_LENS_SWAP_SOURCE}<->{J_LENS_SWAP_TARGET}"

    positive, negative = extraction_prompts(args, tokenizer)
    vectors, metadata = EXTRACTORS[args.method](
        model,
        tokenizer,
        positive,
        negative,
        batch_size=args.extract_batch_size,
        max_length=args.max_length,
        skip_first=16,
    )
    sample_id = "persona:" + hashlib.sha256(
        json.dumps([positive, negative], separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return vectors, metadata, len(positive), sample_id


def validate_extraction_identity(args, metadata):
    if (metadata["method"], metadata["model"], metadata["dtype"]) != (args.method, args.model, args.dtype):
        raise ValueError("extraction cache method/model/dtype mismatch")
    if args.method == "j_lens_concept":
        if metadata["spec_sha256"] != concept_spec()[1] or metadata["implementation_sha256"] != implementation_hash():
            raise ValueError("concept extraction cache specification/implementation mismatch")
        if args.lens_file is not None and metadata["lens_sha256"] != hashlib.sha256(args.lens_file.read_bytes()).hexdigest():
            raise ValueError("concept extraction cache lens mismatch")


def load_or_extract(
    args: argparse.Namespace,
    root: Path,
    model,
    tokenizer,
) -> tuple[dict[str, Vector], dict]:
    paths = {side: root / "extraction" / f"{side.replace('+', 'plus').replace('-', 'minus')}.safetensors" for side in ("+C", "-C")}
    metadata_path = root / "extraction" / "metadata.json"
    if metadata_path.exists() and all(path.exists() for path in paths.values()):
        metadata = json.loads(metadata_path.read_text())
        validate_extraction_identity(args, metadata)
        vectors = {side: Vector.load(str(path)) for side, path in paths.items()}
        actual = {side: vector_sha256(vector) for side, vector in vectors.items()}
        if actual != metadata["vector_content_sha256"]:
            raise ValueError("saved extraction vector hash mismatch")
        return vectors, metadata

    if args.reuse_extraction_from:
        if args.method != "j_lens_concept":
            raise ValueError("extraction reuse flag is restricted to concept calibration")
        source = experiment_dir(args.reuse_extraction_from)
        source_path = source / "extraction/metadata.json"
        metadata = json.loads(source_path.read_text())
        validate_extraction_identity(args, metadata)
        vectors = {side: Vector.load(str(source / metadata["vector_files"][side])) for side in paths}
        if {side: vector_sha256(v) for side, v in vectors.items()} != metadata["vector_content_sha256"]:
            raise ValueError("source extraction vector hash mismatch")
        paths["+C"].parent.mkdir(parents=True, exist_ok=True)
        for side, vector in vectors.items():
            vector.save(str(paths[side]))
        metadata = {**metadata, "extraction_reused_from": args.reuse_extraction_from,
                    "source_metadata_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest()}
        atomic_json(metadata_path, metadata)
        logger.info("EXTRACTION_REUSED source={} hashes={}", args.reuse_extraction_from, metadata["vector_content_sha256"])
        return vectors, metadata

    started = time.monotonic()
    vectors, extraction_metadata, n_pairs, sample_id = extract_vectors(args, model, tokenizer)
    paths["+C"].parent.mkdir(parents=True, exist_ok=True)
    for side, vector in vectors.items():
        vector.cfg.dtype = getattr(torch, args.dtype)
        vector.save(str(paths[side]))
    metadata = {
        "method": args.method,
        "model": args.model,
        "dtype": args.dtype,
        "n_pairs": n_pairs,
        "sample_id": sample_id,
        "seconds": time.monotonic() - started,
        "vector_files": {side: str(path.relative_to(root)) for side, path in paths.items()},
        "vector_content_sha256": {side: vector_sha256(vector) for side, vector in vectors.items()},
        **extraction_metadata,
    }
    atomic_json(metadata_path, metadata)
    return vectors, metadata


def extract_only(args: argparse.Namespace) -> None:
    root = experiment_dir(args.experiment_id)
    model, tokenizer = load_model(args)
    _, metadata = load_or_extract(args, root, model, tokenizer)
    print(
        "EXTRACTION_COMPLETE "
        f"id={args.experiment_id} hash_plus={metadata['vector_content_sha256']['+C']}"
    )


def verify_extraction(args: argparse.Namespace, root: Path, model, tokenizer) -> None:
    metadata_path = root / "extraction" / "metadata.json"
    existing = json.loads(metadata_path.read_text())
    started = time.monotonic()
    vectors, extraction_metadata, n_pairs, _ = extract_vectors(args, model, tokenizer)
    hashes = {side: vector_sha256(vector) for side, vector in vectors.items()}
    if hashes != existing["vector_content_sha256"]:
        raise ValueError("verification extraction differs from the generation vectors")
    verification = {
        "status": "FORMATIVE_EXTRACTION_VERIFICATION",
        "command": f"just experiment {args.method} --verify-extraction",
        "model": args.model,
        "n_pairs": n_pairs,
        "seconds": time.monotonic() - started,
        "hashes_match_generation": True,
        "vector_content_sha256": hashes,
        **extraction_metadata,
    }
    path = root / "extraction" / "verification.json"
    atomic_json(path, verification)
    logger.info(
        "EXTRACTION_VERIFICATION_COMPLETE experiment={} n_pairs={} hashes_match=true path={}",
        args.experiment_id,
        n_pairs,
        path,
    )


def generation_records(
    path: Path,
    rows: list[dict],
    answers: list[str],
    *,
    side: str,
    coefficient: float,
    profile_name: str,
    method: str,
) -> list[dict]:
    return [
        {
            "status": "DEV" if profile_name == "dev" else "FORMATIVE",
            "profile": profile_name,
            "side": side,
            "coefficient": applied_coefficient(method, side, coefficient) if side else 0.0,
            "scenario": row["scenario"],
            "prompt": row["prompt"],
            "text": answer,
            "source": str(path),
        }
        for row, answer in zip(rows, answers, strict=True)
    ]


def extend_generation(
    path: Path,
    rows: list[dict],
    prompts: list[str],
    model,
    tokenizer,
    args: argparse.Namespace,
    *,
    profile_name: str,
    side: str,
    coefficient: float,
    vector: Vector | None,
) -> list[dict]:
    existing = read_jsonl(path)
    if len(existing) > len(rows):
        existing = existing[: len(rows)]
    for index, record in enumerate(existing):
        if record["scenario"] != rows[index]["scenario"] or record["text"] == "":
            raise ValueError(f"artifact prefix mismatch: {path}")
    if len(existing) == len(rows):
        return existing
    missing_rows = rows[len(existing):]
    missing_prompts = prompts[len(existing):]
    if vector is None:
        answers = walk.generate(model, tokenizer, missing_prompts, args.batch_size, args.max_new_tokens)
    elif args.method == "j_lens_concept":
        answers = walk.generate(model, tokenizer, missing_prompts, args.batch_size, args.max_new_tokens,
                                prefill_vector=vector, coefficient=applied_coefficient(args.method, side, coefficient))
    else:
        with vector(model, C=applied_coefficient(args.method, side, coefficient)):
            answers = walk.generate(model, tokenizer, missing_prompts, args.batch_size, args.max_new_tokens)
    added = generation_records(
        path,
        missing_rows,
        answers,
        side=side,
        coefficient=coefficient,
        profile_name=profile_name,
        method=args.method,
    )
    combined = existing + added
    atomic_jsonl(path, combined)
    return combined


def generation_health(args: argparse.Namespace, tokenizer, answers: list[str]) -> tuple[dict, list[str]]:
    stats, reasons = walk.health(tokenizer, answers)
    if args.method == "j_lens_swap":
        leaks = sum(
            any(word in answer.lower() for word in (J_LENS_SWAP_SOURCE, J_LENS_SWAP_TARGET))
            for answer in answers
        )
        stats["lens_token_leaks"] = leaks
        if leaks:
            reasons.append("lens_token_leak")
    return stats, reasons


def health_margin(stats: dict[str, float | int]) -> float:
    answers = int(stats["answers"])
    return min(
        0.5 - int(stats["unfinished"]) / answers,
        0.25 - int(stats["role_leaks"]) / answers,
        0.25 - int(stats["repeated"]) / answers,
    )


def search_boundary(
    side: str,
    root: Path,
    rows: list[dict],
    prompts: list[str],
    model,
    tokenizer,
    vector: Vector,
    args: argparse.Namespace,
) -> dict:
    trace = []

    def observe(coefficient: float) -> dict:
        if len(trace) >= SEARCH_BUDGET:
            raise RuntimeError(f"{side} health search exhausted {SEARCH_BUDGET} probes")
        path = probe_path(root, side, coefficient)
        records = extend_generation(
            path,
            rows,
            prompts,
            model,
            tokenizer,
            args,
            profile_name="dev",
            side=side,
            coefficient=coefficient,
            vector=vector,
        )
        stats, reasons = generation_health(args, tokenizer, [record["text"] for record in records])
        entry = {
            "coefficient": coefficient,
            "health_margin": health_margin(stats),
            "health_clean": not reasons,
            "breakdown_reasons": reasons,
            "stats": stats,
            "path": str(path.relative_to(root)),
        }
        trace.append(entry)
        return entry

    current = observe(1.0)
    if current["health_clean"]:
        lo = current
        while len(trace) < SEARCH_BUDGET:
            hi = observe(lo["coefficient"] * 2)
            if not hi["health_clean"]:
                break
            lo = hi
        else:
            raise RuntimeError(f"{side} remains health-clean through C={lo['coefficient']}")
    else:
        hi = current
        while len(trace) < SEARCH_BUDGET:
            lo = observe(hi["coefficient"] / 2)
            if lo["health_clean"]:
                break
            hi = lo
        else:
            raise RuntimeError(f"{side} remains unhealthy through C={hi['coefficient']}")
    f_lo = lo["health_margin"]
    f_hi = hi["health_margin"]
    last_updated = None
    while len(trace) < SEARCH_BUDGET and math.log(hi["coefficient"] / lo["coefficient"]) > SEARCH_LOG_TOLERANCE:
        log_lo = math.log(lo["coefficient"])
        log_hi = math.log(hi["coefficient"])
        if math.isclose(f_hi, f_lo):
            log_candidate = (log_lo + log_hi) / 2
        else:
            log_candidate = (log_lo * f_hi - log_hi * f_lo) / (f_hi - f_lo)
        if not log_lo < log_candidate < log_hi:
            log_candidate = (log_lo + log_hi) / 2
        candidate = observe(math.exp(log_candidate))
        if candidate["health_clean"]:
            lo, f_lo = candidate, candidate["health_margin"]
            if last_updated == "lo":
                f_hi *= 0.5
            last_updated = "lo"
        else:
            hi, f_hi = candidate, candidate["health_margin"]
            if last_updated == "hi":
                f_lo *= 0.5
            last_updated = "hi"
    return {"C_approx": lo["coefficient"], "C_hi": hi["coefficient"], "trace": trace}


def local_grid(c_approx: float) -> list[float]:
    return [
        c_approx * (GRID_LOW + index * (GRID_HIGH - GRID_LOW) / (GRID_POINTS - 1))
        for index in range(GRID_POINTS)
    ]


def dev_grid(boundary: dict) -> list[float]:
    return sorted({
        *local_grid(boundary["C_approx"]),
        *(entry["coefficient"] for entry in boundary["trace"] if entry["health_clean"]),
    })


def completed_profile_cell_count(
    args: argparse.Namespace,
    manifest: dict,
    root: Path,
    profile_name: str,
    limit: int,
) -> int | None:
    profile = manifest.get("profiles", {}).get(profile_name)
    if not profile or not profile.get("generated"):
        return None
    coefficients = manifest.get("grid") if args.dev else {
        "+C": [float(value) for value in args.coefficients_plus.split(",") if value],
        "-C": [float(value) for value in args.coefficients_minus.split(",") if value],
    }
    if not coefficients or any(not coefficients[side] for side in ("+C", "-C")):
        return None
    bare = manifest.get("bare")
    if not bare or len(read_jsonl(root / bare["path"])) < limit:
        return None
    count = 0
    for side in ("+C", "-C"):
        for coefficient in coefficients[side]:
            entry = manifest.get("cells", {}).get(side, {}).get(f"{coefficient:.12g}")
            if not entry or len(read_jsonl(root / entry["path"])) < limit:
                return None
            if args.method == "j_lens_swap" and "lens_token_leaks" not in entry["health"]:
                return None
            count += 1
    return count


def concept_grid(args):
    grid = {side: [float(c) for c in text.split(",") if c] if text else list(J_LENS_CONCEPT_GRID)
            for side, text in (("+C", args.coefficients_plus), ("-C", args.coefficients_minus))}
    if any(not math.isfinite(c) or c <= 0 for values in grid.values() for c in values):
        raise ValueError("concept grid requires finite positive magnitudes")
    return grid


def gpu_stage(args: argparse.Namespace) -> None:
    if args.method == "j_lens_concept" and not args.dev:
        raise ValueError("concept intervention is DEV-only")
    profile_name = "dev" if args.dev else "full"
    limit = DEV.cohort_size if args.dev else FULL.cohort_size
    root = experiment_dir(args.experiment_id)
    root.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path(args.experiment_id).read_text()) if manifest_path(args.experiment_id).exists() else {
        "schema": ("j_lens_concept_experiment_v1" if args.method == "j_lens_concept" else
                   "j_lens_swap_experiment_v1" if args.method == "j_lens_swap" else "mlp_up_left_right_experiment_v1"),
        "experiment_id": args.experiment_id,
        "method": args.method,
        "date": time.strftime("%Y%m%d"),
        "profiles": {},
        "config": {
            "model": args.model,
            "dtype": args.dtype,
            "n_pairs": args.n_pairs,
            "batch_size": args.batch_size,
            "extract_batch_size": args.extract_batch_size,
            "max_length": args.max_length,
            "max_new_tokens": args.max_new_tokens,
        },
    }
    if manifest["method"] != args.method:
        raise ValueError("experiment id belongs to another method")
    if args.method == "j_lens_swap" and manifest["schema"] == "mlp_up_left_right_experiment_v1":
        manifest["schema"] = "j_lens_swap_experiment_v1"
        atomic_json(manifest_path(args.experiment_id), manifest)
    if args.method == "j_lens_concept" and "extraction" in manifest:
        validate_extraction_identity(args, manifest["extraction"])
    if args.dev and "boundaries" in manifest:
        if args.method == "j_lens_concept":
            expanded_grid = concept_grid(args)
        elif args.method == "j_lens_swap":
            expanded_grid = {
                "+C": list(J_LENS_SWAP_POSITIVE_GRID),
                "-C": list(J_LENS_SWAP_NEGATIVE_GRID),
            }
        else:
            expanded_grid = {side: dev_grid(manifest["boundaries"][side]) for side in ("+C", "-C")}
        if manifest["grid"] != expanded_grid:
            manifest["grid"] = expanded_grid
            atomic_json(manifest_path(args.experiment_id), manifest)
    completed_cells = completed_profile_cell_count(args, manifest, root, profile_name, limit)
    if completed_cells is not None and not args.verify_extraction:
        logger.info(
            "GPU_STAGE_COMPLETE experiment={} profile={} cells={} reused=true",
            args.experiment_id,
            profile_name,
            completed_cells,
        )
        return
    rows, cohort_sha256 = walk.read_cohort(limit)
    model, tokenizer = load_model(args)
    if args.verify_extraction:
        verify_extraction(args, root, model, tokenizer)
        return
    vectors, extraction = load_or_extract(args, root, model, tokenizer)
    prompts = walk.generation_inputs(tokenizer, rows)
    bare_path = root / "bare.jsonl"
    bare = extend_generation(
        bare_path,
        rows,
        prompts,
        model,
        tokenizer,
        args,
        profile_name=profile_name,
        side="",
        coefficient=0.0,
        vector=None,
    )
    if "grid" not in manifest:
        if not args.dev:
            raise RuntimeError("full mode requires its automatic dev stage first")
        if args.method == "j_lens_concept":
            boundaries = {side: {"meaning": "signed unit concept contrast", "trace": []} for side in ("+C", "-C")}
            grid = concept_grid(args)
        elif args.method == "j_lens_swap":
            boundaries = {
                "+C": {"meaning": "abrasive-to-flattering directed transfer", "trace": []},
                "-C": {"meaning": "flattering-to-abrasive directed transfer", "trace": []},
            }
            grid = {
                "+C": list(J_LENS_SWAP_POSITIVE_GRID),
                "-C": list(J_LENS_SWAP_NEGATIVE_GRID),
            }
        else:
            boundaries = {
                side: search_boundary(side, root, rows, prompts, model, tokenizer, vectors[side], args)
                for side in ("+C", "-C")
            }
            grid = {side: dev_grid(boundaries[side]) for side in ("+C", "-C")}
        manifest["boundaries"] = boundaries
        manifest["grid"] = grid
        manifest["extraction"] = extraction
        manifest["cohort_sha256"] = cohort_sha256
        atomic_json(manifest_path(args.experiment_id), manifest)
    coefficients = manifest["grid"] if args.dev else {
        "+C": [float(value) for value in args.coefficients_plus.split(",") if value],
        "-C": [float(value) for value in args.coefficients_minus.split(",") if value],
    }
    if not args.dev and any(not coefficients[side] for side in ("+C", "-C")):
        raise ValueError("full GPU stage requires DEV-accepted candidates for both sides")
    generated_cells = 0
    encoded_prompts = None
    if args.method == "j_lens_concept":
        encoded_prompts = tokenizer(
            prompts, return_tensors="pt", padding=True, add_special_tokens=False,
        ).to(args.device)
    for side in ("+C", "-C"):
        for coefficient in coefficients[side]:
            records = extend_generation(
                cell_path(root, side, coefficient),
                rows,
                prompts,
                model,
                tokenizer,
                args,
                profile_name=profile_name,
                side=side,
                coefficient=coefficient,
                vector=vectors[side],
            )
            stats, reasons = generation_health(args, tokenizer, [record["text"] for record in records])
            cell = {
                "coefficient": coefficient,
                "path": str(cell_path(root, side, coefficient).relative_to(root)),
                "rows": len(records),
                "health": stats,
                "breakdown_reasons": reasons,
            }
            if args.method == "j_lens_concept":
                assert encoded_prompts is not None
                cell["realized_prefill"] = prefill_diagnostics(
                    model,
                    vectors[side],
                    encoded_prompts.input_ids,
                    encoded_prompts.attention_mask,
                    applied_coefficient(args.method, side, coefficient),
                )
            manifest.setdefault("cells", {}).setdefault(side, {})[f"{coefficient:.12g}"] = cell
            atomic_json(manifest_path(args.experiment_id), manifest)
            generated_cells += 1
    manifest["profiles"][profile_name] = {
        "status": "DEV" if args.dev else "FORMATIVE",
        "cohort_size": limit,
        "generated": True,
    }
    manifest["bare"] = {"path": str(bare_path.relative_to(root)), "rows": len(bare)}
    atomic_json(manifest_path(args.experiment_id), manifest)
    logger.info("GPU_STAGE_COMPLETE experiment={} profile={} cells={}", args.experiment_id, profile_name, generated_cells)


def run_resumable(command: list[str], *, attempts: int, label: str) -> None:
    for attempt in range(1, attempts + 1):
        result = subprocess.run(command, cwd=walk.ROOT)
        if result.returncode == 0:
            return
        if result.returncode in {2, 126, 127}:
            raise subprocess.CalledProcessError(result.returncode, command)
        if attempt == attempts:
            raise subprocess.CalledProcessError(result.returncode, command)
        delay = min(300, 15 * 2 ** (attempt - 1))
        logger.warning("{} failed attempt={}/{}; resume in {}s", label, attempt, attempts, delay)
        time.sleep(delay)


def modal_stage(
    args: argparse.Namespace,
    dev: bool,
    coefficients: dict[str, list[float]] | None = None,
) -> None:
    command = [
        "uv", "run", "modal", "run", "scripts/run_modal.py::experiment",
        "--method", args.method,
        "--experiment-id", args.experiment_id,
        "--profile", "dev" if dev else "full",
        "--model", args.model,
        "--dtype", args.dtype,
        "--n-pairs", str(args.n_pairs),
        "--batch-size", str(args.batch_size),
        "--extract-batch-size", str(args.extract_batch_size),
        "--max-length", str(args.max_length),
        "--max-new-tokens", str(args.max_new_tokens),
    ]
    if args.verify_extraction:
        command.append("--verify-extraction")
    if args.reuse_extraction_from:
        command.extend(["--reuse-extraction-from", args.reuse_extraction_from])
    if args.method == "j_lens_concept" and dev:
        coefficients = concept_grid(args)
    if coefficients is not None:
        command.extend([
            "--coefficients-plus", ",".join(map(str, coefficients["+C"])),
            "--coefficients-minus", ",".join(map(str, coefficients["-C"])),
        ])
    run_resumable(command, attempts=4, label=f"Modal {'dev' if dev else 'full'} stage")
    run_resumable(
        [
            "uv", "run", "modal", "volume", "get", "--force", "jsteer-pub-cache",
            f"outputs/experiments/{args.experiment_id}",
            "outputs/experiments",
        ],
        attempts=4,
        label="Modal artifact pull",
    )


def local_pipeline(args: argparse.Namespace) -> None:
    if args.method == "j_lens_concept" and not args.dev:
        raise ValueError("concept intervention is DEV-only; full confirmation is not authorized")
    if args.local:
        args.gpu_stage = True
        gpu_stage(args)
        return
    modal_stage(args, dev=True)
    run_resumable(
        [sys.executable, "scripts/judge.py", "--experiment-id", args.experiment_id, "--profile", "dev", "--refresh"],
        attempts=12,
        label="OpenRouter dev judge",
    )
    subprocess.run(
        [sys.executable, "scripts/export.py", "--experiment-id", args.experiment_id, "--profile", "dev"],
        cwd=walk.ROOT,
        check=True,
    )
    render_command = [sys.executable, "-m", "vjp_steering.results"]
    if args.method != "j_lens_swap":
        render_command.extend(["--experiment-id", args.experiment_id, "--profile", "dev"])
    if args.method != "j_lens_concept":
        subprocess.run(render_command, cwd=walk.ROOT, check=True)
    if args.dev:
        return
    selected = json.loads((walk.ROOT / "data" / "dev" / args.experiment_id / "selected.json").read_text())
    missing_sides = [
        side for side in ("+C", "-C")
        if "candidates_descending" not in selected["sides"].get(side, {})
    ]
    if missing_sides:
        raise ValueError(f"DEV has no accepted endpoint for {', '.join(missing_sides)}")
    candidates = {
        side: selected["sides"][side]["candidates_descending"]
        for side in ("+C", "-C")
    }
    modal_stage(args, dev=False, coefficients=candidates)
    failed_sides: dict[str, list[float]] = {}
    for side in ("+C", "-C"):
        tested_candidates: list[float] = []
        for coefficient in selected["sides"][side]["candidates_descending"]:
            tested_candidates.append(coefficient)
            cell_args = [f"--side={side}", "--coefficient", str(coefficient)]
            run_resumable(
                [
                    sys.executable,
                    "scripts/judge.py",
                    "--experiment-id",
                    args.experiment_id,
                    "--profile",
                    "full",
                    "--refresh",
                    *cell_args,
                ],
                attempts=12,
                label=f"OpenRouter full judge {side} C={coefficient}",
            )
            subprocess.run(
                [
                    sys.executable,
                    "scripts/export.py",
                    "--experiment-id",
                    args.experiment_id,
                    "--profile",
                    "full",
                    *cell_args,
                ],
                cwd=walk.ROOT,
                check=True,
            )
            confirmed_path = walk.ROOT / "data" / "formative" / args.experiment_id / "selected.json"
            confirmed = json.loads(confirmed_path.read_text())
            if side in confirmed["sides"]:
                confirmed["sides"][side]["status"] = "accepted"
                atomic_json(confirmed_path, confirmed)
                break
        else:
            failed_sides[side] = tested_candidates
            logger.warning(
                "FULL_SIDE_UNCONFIRMED side={} tested_candidates={}",
                side,
                tested_candidates,
            )
    confirmed_path = walk.ROOT / "data" / "formative" / args.experiment_id / "selected.json"
    confirmed = json.loads(confirmed_path.read_text())
    for side, tested_candidates in failed_sides.items():
        confirmed["sides"][side] = {
            "status": "no_accepted_endpoint",
            "tested_candidates": tested_candidates,
        }
    atomic_json(confirmed_path, confirmed)
    render_command = [sys.executable, "-m", "vjp_steering.results"]
    if args.method != "j_lens_swap":
        render_command.extend(["--experiment-id", args.experiment_id, "--profile", "full"])
    subprocess.run(render_command, cwd=walk.ROOT, check=True)


def _lens_token_id(tokenizer, word: str) -> int:
    ids = tokenizer(" " + word.strip(), add_special_tokens=False).input_ids
    if len(ids) != 1:
        raise ValueError(f"expected one token for {word!r}, got {ids}")
    return ids[0]


def _j_lens_candidate_states(model, tokenizer, layers: tuple[int, ...], source: str, target: str):
    lens_file, checkpoint = _load_j_lens(model, layers, None)
    unembedding = model.lm_head.weight.detach().float().cpu()
    source_id = _lens_token_id(tokenizer, source)
    target_id = _lens_token_id(tokenizer, target)
    states = {name: {} for name in ("raw_exchange", "unit_exchange", "unit_transfer")}
    geometry = {}
    for layer in layers:
        jacobian = checkpoint["J"][layer].float()
        raw = torch.stack((unembedding[source_id] @ jacobian, unembedding[target_id] @ jacobian))
        unit = raw / raw.norm(dim=1, keepdim=True)
        states["raw_exchange"][layer] = {"basis": raw, "dual": torch.linalg.pinv(raw.T)}
        states["unit_exchange"][layer] = {"basis": unit, "dual": torch.linalg.pinv(unit.T)}
        states["unit_transfer"][layer] = {"source": unit[0], "target": unit[1]}
        geometry[str(layer)] = {
            "raw_norms": raw.norm(dim=1).tolist(),
            "unit_cosine": torch.dot(unit[0], unit[1]).item(),
        }
    return states, geometry, {
        "lens_file": str(lens_file),
        "lens_sha256": hashlib.sha256(lens_file.read_bytes()).hexdigest(),
        "source_id": source_id,
        "target_id": target_id,
    }


@contextmanager
def _j_lens_diagnostic_hooks(
    model,
    state: dict[int, dict[str, torch.Tensor]],
    operator: str,
    alpha: float,
):
    calls = {str(layer): 0 for layer in state}
    measurements = {}
    handles = []

    def make_hook(layer: int):
        layer_state = state[layer]

        def hook(_module, _inputs, output):
            hidden = output[0] if isinstance(output, tuple) else output
            hidden32 = hidden.float()
            calls[str(layer)] += 1
            if operator == "unit_transfer":
                source = layer_state["source"].to(hidden.device)
                target = layer_state["target"].to(hidden.device)
                patched32 = _transfer_lens_coordinate(hidden32, source, target, alpha)
                source_pre = torch.einsum("...d,d->...", hidden32, source)
                source_post = torch.einsum("...d,d->...", patched32, source)
                target_pre = torch.einsum("...d,d->...", hidden32, target)
                target_post = torch.einsum("...d,d->...", patched32, target)
                measurements[str(layer)] = {
                    "source_abs_mean_pre": source_pre.abs().mean().item(),
                    "source_mean_pre": source_pre.mean().item(),
                    "source_mean_post": source_post.mean().item(),
                    "target_mean_pre": target_pre.mean().item(),
                    "target_mean_post": target_post.mean().item(),
                }
            else:
                basis = layer_state["basis"].to(hidden.device)
                dual = layer_state["dual"].to(hidden.device)
                coordinates_pre = torch.einsum("...d,kd->...k", hidden32, dual)
                patched32 = _swap_lens_coordinates(hidden32, basis, dual, alpha)
                coordinates_post = torch.einsum("...d,kd->...k", patched32, dual)
                coordinates_expected = coordinates_pre + alpha * (coordinates_pre.flip(-1) - coordinates_pre)
                measurements[str(layer)] = {
                    "coordinate_abs_mean_pre": coordinates_pre.abs().mean(dim=(0, 1)).tolist(),
                    "coordinate_mean_pre": coordinates_pre.mean(dim=(0, 1)).tolist(),
                    "coordinate_mean_post": coordinates_post.mean(dim=(0, 1)).tolist(),
                    "swap_max_abs_error": (coordinates_post - coordinates_expected).abs().max().item(),
                }
            patched = patched32.to(hidden.dtype)
            return (patched, *output[1:]) if isinstance(output, tuple) else patched

        return hook

    for layer in state:
        handles.append(model.model.layers[layer].register_forward_hook(make_hook(layer)))
    try:
        yield calls, measurements
    finally:
        for handle in handles:
            handle.remove()


@torch.no_grad()
def _prompt_only_greedy(model, tokenizer, prompt: str, n_new: int, hook_context=None):
    input_ids = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).input_ids.to(model.device)
    if hook_context is None:
        output = model(input_ids, use_cache=True)
        calls, measurements = {}, {}
    else:
        with hook_context as (calls, measurements):
            output = model(input_ids, use_cache=True)
    past = output.past_key_values
    next_id = output.logits[:, -1].argmax(dim=-1, keepdim=True)
    generated = [int(next_id.item())]
    for _ in range(n_new - 1):
        output = model(next_id, past_key_values=past, use_cache=True)
        past = output.past_key_values
        next_id = output.logits[:, -1].argmax(dim=-1, keepdim=True)
        generated.append(int(next_id.item()))
    return generated[0], tokenizer.decode(generated), calls, measurements


def _starts_with_answer(text: str, answer: str) -> bool:
    return text.strip().lstrip("\"'`.,:;!?-— ").lower().startswith(answer.lower())


def j_lens_paper_native_diagnostic(args: argparse.Namespace) -> None:
    if args.method != "j_lens_swap":
        raise ValueError("--j-lens-diagnostic requires method=j_lens_swap")
    model, tokenizer = load_model(args)
    items = [
        {"source": "France", "target": "China", "source_answer": "Paris", "target_answer": "Beijing"},
        {"source": "Canada", "target": "Egypt", "source_answer": "Ottawa", "target_answer": "Cairo"},
    ]
    bands = {"current": tuple(range(6, 25)), "reference_fraction": tuple(range(9, 31)), "early_mid": tuple(range(4, 14))}
    records = []
    for item in items:
        prompt = f"The capital of {item['source']} is the city of"
        target_prompt = f"The capital of {item['target']} is the city of"
        source_first, source_text, _, _ = _prompt_only_greedy(model, tokenizer, prompt, 6)
        target_first, target_text, _, _ = _prompt_only_greedy(model, tokenizer, target_prompt, 6)
        source_expected = _lens_token_id(tokenizer, item["source_answer"])
        target_expected = _lens_token_id(tokenizer, item["target_answer"])
        baseline_ok = source_first == source_expected and target_first == target_expected
        records.append({
            "kind": "baseline", **item, "source_text": source_text, "target_text": target_text,
            "source_first": source_first, "target_first": target_first, "baseline_ok": baseline_ok,
        })
        for band_name, layers in bands.items():
            states, geometry, provenance = _j_lens_candidate_states(
                model, tokenizer, layers, item["source"], item["target"]
            )
            for operator, state in states.items():
                for alpha in (1.0, 2.0, 4.0):
                    context = _j_lens_diagnostic_hooks(model, state, operator, alpha)
                    first, text, calls, measurements = _prompt_only_greedy(model, tokenizer, prompt, 6, context)
                    if set(calls.values()) != {1}:
                        raise AssertionError(f"hooks were not prompt-only: {calls}")
                    records.append({
                        "kind": "intervention", **item, "band": band_name,
                        "layers": [layers[0], layers[-1]], "operator": operator, "alpha": alpha,
                        "text": text, "first_token": first,
                        "hit_target": first == target_expected or _starts_with_answer(text, item["target_answer"]),
                        "stayed_source": first == source_expected or _starts_with_answer(text, item["source_answer"]),
                        "baseline_ok": baseline_ok, "hook_calls": calls,
                        "layer_geometry": geometry, "layer_measurements": measurements,
                        "provenance": provenance,
                    })
    output = Path(args.diagnostic_output)
    payload = {
        "schema": "j_lens_paper_native_diagnostic_v1",
        "model": args.model,
        "dtype": args.dtype,
        "decode": "greedy_prompt_prefill_only",
        "records": records,
    }
    atomic_json(output, payload)
    interventions = [record for record in records if record["kind"] == "intervention" and record["baseline_ok"]]
    summary = {
        operator: {
            "n": len(selected := [r for r in interventions if r["operator"] == operator]),
            "hit_target": sum(r["hit_target"] for r in selected),
            "stayed_source": sum(r["stayed_source"] for r in selected),
        }
        for operator in ("raw_exchange", "unit_exchange", "unit_transfer")
    }
    print(json.dumps({"output": str(output), "summary": summary}, indent=2))


def self_test() -> None:
    from judge import required_cells

    generator = torch.Generator().manual_seed(0)
    basis = torch.randn(2, 7, generator=generator)
    dual = torch.linalg.pinv(basis.T)
    hidden = torch.randn(3, 5, 7, generator=generator)
    torch.testing.assert_close(_swap_lens_coordinates(hidden, basis, dual, 0), hidden)
    patched = _swap_lens_coordinates(hidden, basis, dual, 1)
    coordinates = torch.einsum("...d,kd->...k", hidden, dual)
    patched_coordinates = torch.einsum("...d,kd->...k", patched, dual)
    torch.testing.assert_close(patched_coordinates, coordinates.flip(-1), atol=1e-5, rtol=1e-5)
    source, target = torch.nn.functional.normalize(basis, dim=1)
    transferred = _transfer_lens_coordinate(hidden, source, target, 1)
    coefficient = torch.einsum("...d,d->...", hidden, source)
    expected = hidden + torch.einsum("...,d->...d", coefficient, target - source)
    torch.testing.assert_close(transferred, expected)
    cfg = JLensSwapC(layers=(1,))
    cfg.coeff = 1.0
    state = {"source": source, "target": target}
    torch.testing.assert_close(JLensSwap.apply(None, None, hidden, state, None, cfg), expected)
    one_token = hidden[:, :1]
    torch.testing.assert_close(JLensSwap.apply(None, None, one_token, state, None, cfg), one_token)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "swap.safetensors"
        vector = Vector(
            JLensSwapC(layers=(1,)),
            {1: {"source": source, "target": target}},
            {1: {}},
        )
        vector.save(str(path))
        assert vector_sha256(Vector.load(str(path))) == vector_sha256(vector)
    print("J_LENS_SWAP_SELF_TEST_PASS alpha0=identity alpha1=coordinate_exchange transfer=exact prompt_only=exact reload=exact")

    assert len(local_grid(1.0)) == GRID_POINTS
    assert math.isclose(local_grid(1.0)[0], GRID_LOW)
    assert math.isclose(local_grid(1.0)[-1], GRID_HIGH)
    assert dev_grid({
        "C_approx": 1.0,
        "trace": [
            {"coefficient": 0.5, "health_clean": True},
            {"coefficient": 2.0, "health_clean": False},
        ],
    }) == sorted({*local_grid(1.0), 0.5})
    assert signed_coefficient("+C", 2.0) == 2.0
    assert signed_coefficient("-C", 2.0) == -2.0
    assert applied_coefficient("j_lens_swap", "-C", 2.0) == 2.0
    quick_rows = [
        {
            "bare": f"bare {question}",
            "steered": f"steered {side} {dose} {question}",
            "prompt": f"prompt {question}",
            "side": side,
        }
        for side in ("+C", "-C")
        for dose in range(GRID_POINTS)
        for question in range(DEV.cohort_size)
    ]
    full_rows = [
        {
            "bare": f"bare {question}",
            "steered": f"steered {side} {question}",
            "prompt": f"prompt {question}",
            "side": side,
        }
        for side in ("+C", "-C")
        for question in range(FULL.cohort_size)
    ]
    assert len(required_cells(quick_rows, DEV.orders, DEV.passes)) == 270
    assert len(required_cells(full_rows, FULL.orders, FULL.passes)) == 400
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "bare.jsonl").write_text("{}\n" * DEV.cohort_size)
        manifest = {
            "profiles": {"dev": {"generated": True}},
            "bare": {"path": "bare.jsonl"},
            "grid": {side: local_grid(1.0) for side in ("+C", "-C")},
            "cells": {side: {} for side in ("+C", "-C")},
        }
        for side in ("+C", "-C"):
            for coefficient in manifest["grid"][side]:
                path = root / f"{side}_{coefficient}.jsonl"
                path.write_text("{}\n" * DEV.cohort_size)
                manifest["cells"][side][f"{coefficient:.12g}"] = {"path": path.name}
        args = SimpleNamespace(method="test", dev=True, coefficients_plus="", coefficients_minus="")
        assert completed_profile_cell_count(args, manifest, root, "dev", DEV.cohort_size) == GRID_POINTS * 2
    print("EXPERIMENT_SELF_TEST_PASS quick_calls=270 full_calls=400 resume_cells=18")


def main() -> None:
    args = parse_args()
    if args.self_test:
        self_test()
        if args.method == "j_lens_concept":
            from concept_checks import self_test as concept_self_test
            concept_self_test()
    elif args.concept_smoke:
        from concept_checks import smoke
        smoke(args)
    elif args.concept_calibrate:
        from concept_checks import calibrate
        calibrate(args)
    elif args.j_lens_diagnostic:
        j_lens_paper_native_diagnostic(args)
    elif args.gpu_stage:
        gpu_stage(args)
    elif args.extract_only:
        extract_only(args)
    elif args.verify_extraction:
        modal_stage(args, dev=True)
    else:
        local_pipeline(args)


if __name__ == "__main__":
    main()
