"""One resumable entrypoint for formative MLP-up experiments."""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import torch
from loguru import logger
from steering_lite import Vector
from steering_lite.data import make_persona_pairs
from transformers import AutoModelForCausalLM, AutoTokenizer

import walk
from vjp_steering.experiment import DEFAULT_EXPERIMENT_ID, DEV, FULL, METHOD, experiment_dir, manifest_path
from vjp_steering.vjp import vjp_mlp_up_left_right_shrink


SEARCH_BUDGET = 10
SEARCH_LOG_TOLERANCE = math.log(2.0) / 6.0
GRID_LOW = 0.66
GRID_HIGH = 1.33
GRID_POINTS = 9


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("method", choices=(METHOD,))
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--gpu-stage", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--experiment-id", default=DEFAULT_EXPERIMENT_ID)
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", choices=("float32", "bfloat16"), default="bfloat16")
    parser.add_argument("--n-pairs", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--extract-batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    return parser.parse_args()


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
        vectors = {side: Vector.load(str(path)) for side, path in paths.items()}
        actual = {side: vector_sha256(vector) for side, vector in vectors.items()}
        if actual != metadata["vector_content_sha256"]:
            raise ValueError("saved extraction vector hash mismatch")
        return vectors, metadata

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
    started = time.monotonic()
    vectors, extraction_metadata = vjp_mlp_up_left_right_shrink(
        model,
        tokenizer,
        positive,
        negative,
        batch_size=args.extract_batch_size,
        max_length=args.max_length,
        skip_first=16,
    )
    paths["+C"].parent.mkdir(parents=True, exist_ok=True)
    for side, vector in vectors.items():
        vector.cfg.dtype = getattr(torch, args.dtype)
        vector.save(str(paths[side]))
    metadata = {
        "method": METHOD,
        "model": args.model,
        "dtype": args.dtype,
        "n_pairs": len(positive),
        "sample_id": "persona:" + hashlib.sha256(
            json.dumps([positive, negative], separators=(",", ":")).encode()
        ).hexdigest()[:16],
        "seconds": time.monotonic() - started,
        "vector_files": {side: str(path.relative_to(root)) for side, path in paths.items()},
        "vector_content_sha256": {side: vector_sha256(vector) for side, vector in vectors.items()},
        **extraction_metadata,
    }
    atomic_json(metadata_path, metadata)
    return vectors, metadata


def generation_records(
    path: Path,
    rows: list[dict],
    answers: list[str],
    *,
    side: str,
    coefficient: float,
    profile_name: str,
) -> list[dict]:
    return [
        {
            "status": "DEV" if profile_name == "dev" else "FORMATIVE",
            "profile": profile_name,
            "side": side,
            "coefficient": signed_coefficient(side, coefficient) if side else 0.0,
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
    else:
        with vector(model, C=signed_coefficient(side, coefficient)):
            answers = walk.generate(model, tokenizer, missing_prompts, args.batch_size, args.max_new_tokens)
    added = generation_records(
        path,
        missing_rows,
        answers,
        side=side,
        coefficient=coefficient,
        profile_name=profile_name,
    )
    combined = existing + added
    atomic_jsonl(path, combined)
    return combined


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
        stats, reasons = walk.health(tokenizer, [record["text"] for record in records])
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


def gpu_stage(args: argparse.Namespace) -> None:
    profile_name = "dev" if args.dev else "full"
    limit = DEV.cohort_size if args.dev else FULL.cohort_size
    root = experiment_dir(args.experiment_id)
    root.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path(args.experiment_id).read_text()) if manifest_path(args.experiment_id).exists() else {
        "schema": "mlp_up_left_right_experiment_v1",
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
    rows, cohort_sha256 = walk.read_cohort(limit)
    model, tokenizer = load_model(args)
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
        boundaries = {
            side: search_boundary(side, root, rows, prompts, model, tokenizer, vectors[side], args)
            for side in ("+C", "-C")
        }
        manifest["boundaries"] = boundaries
        manifest["grid"] = {side: local_grid(boundaries[side]["C_approx"]) for side in ("+C", "-C")}
        manifest["extraction"] = extraction
        manifest["cohort_sha256"] = cohort_sha256
        atomic_json(manifest_path(args.experiment_id), manifest)
    for side in ("+C", "-C"):
        for coefficient in manifest["grid"][side]:
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
            stats, reasons = walk.health(tokenizer, [record["text"] for record in records])
            manifest.setdefault("cells", {}).setdefault(side, {})[f"{coefficient:.12g}"] = {
                "coefficient": coefficient,
                "path": str(cell_path(root, side, coefficient).relative_to(root)),
                "rows": len(records),
                "health": stats,
                "breakdown_reasons": reasons,
            }
            atomic_json(manifest_path(args.experiment_id), manifest)
    manifest["profiles"][profile_name] = {
        "status": "DEV" if args.dev else "FORMATIVE",
        "cohort_size": limit,
        "generated": True,
    }
    manifest["bare"] = {"path": str(bare_path.relative_to(root)), "rows": len(bare)}
    atomic_json(manifest_path(args.experiment_id), manifest)
    logger.info("GPU_STAGE_COMPLETE experiment={} profile={} cells={}", args.experiment_id, profile_name, GRID_POINTS * 2)


def run_resumable(command: list[str], *, attempts: int, label: str) -> None:
    for attempt in range(1, attempts + 1):
        result = subprocess.run(command, cwd=walk.ROOT)
        if result.returncode == 0:
            return
        if attempt == attempts:
            raise subprocess.CalledProcessError(result.returncode, command)
        delay = min(300, 15 * 2 ** (attempt - 1))
        logger.warning("{} failed attempt={}/{}; resume in {}s", label, attempt, attempts, delay)
        time.sleep(delay)


def modal_stage(args: argparse.Namespace, dev: bool) -> None:
    command = [
        "uv", "run", "modal", "run", "scripts/run_modal.py::experiment",
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
    run_resumable(command, attempts=4, label=f"Modal {'dev' if dev else 'full'} stage")
    run_resumable(
        ["uv", "run", "modal", "volume", "get", "--force", "jsteer-pub-cache", "outputs", "."],
        attempts=4,
        label="Modal artifact pull",
    )


def local_pipeline(args: argparse.Namespace) -> None:
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
    subprocess.run(
        [sys.executable, "-m", "vjp_steering.results", "--experiment-id", args.experiment_id, "--profile", "dev"],
        cwd=walk.ROOT,
        check=True,
    )
    if args.dev:
        return
    modal_stage(args, dev=False)
    selected = json.loads((walk.ROOT / "data" / "dev" / args.experiment_id / "selected.json").read_text())
    for side in ("+C", "-C"):
        for coefficient in selected["sides"][side]["candidates_descending"]:
            cell_args = ["--side", side, "--coefficient", str(coefficient)]
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
                break
        else:
            raise RuntimeError(f"full confirmation found no accepted endpoint for {side}")
    subprocess.run(
        [sys.executable, "-m", "vjp_steering.results", "--experiment-id", args.experiment_id, "--profile", "full"],
        cwd=walk.ROOT,
        check=True,
    )


def self_test() -> None:
    from judge import required_cells

    assert len(local_grid(1.0)) == GRID_POINTS
    assert math.isclose(local_grid(1.0)[0], GRID_LOW)
    assert math.isclose(local_grid(1.0)[-1], GRID_HIGH)
    assert signed_coefficient("+C", 2.0) == 2.0
    assert signed_coefficient("-C", 2.0) == -2.0
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
    print("EXPERIMENT_SELF_TEST_PASS quick_calls=270 full_calls=400")


def main() -> None:
    args = parse_args()
    if args.self_test:
        self_test()
    elif args.gpu_stage:
        gpu_stage(args)
    else:
        local_pipeline(args)


if __name__ == "__main__":
    main()
