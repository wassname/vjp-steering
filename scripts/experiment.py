"""One resumable entrypoint for formative MLP-up experiments."""

import argparse
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import torch
from loguru import logger
from steering_lite import MeanDiffC, RandomC, Vector
from steering_lite.data import make_persona_pairs
from steering_lite.data.personas import load_suffixes
from transformers import AutoModelForCausalLM, AutoTokenizer

import walk
from vjp_steering.j_lens_concept import (
    COMPONENT_PAIR_METHOD, COMPONENT_PAIR_REPRESENTATION_SOURCE, COMPONENT_PAIR_VERSION, JLensConceptC,
    LEGACY_EXTRACTION_IMPLEMENTATION_SHA256,
    PERSONA_COMPONENT_PAIR_REPRESENTATION_SOURCE, PERSONA_COMPONENT_PAIR_VERSION,
    PERSONA_FULL_COMPONENT_PAIR_REPRESENTATION_SOURCE, PERSONA_FULL_COMPONENT_PAIR_VERSION,
    PERSONA_FULL_RESIDUAL_VERSION, PERSONA_VERSION, component_spec, concept_spec,
    concept_prefill_mask, extract_concept, extract_persona_components, extract_persona_contrast,
    implementation_hash, mask_metadata, persona_component_spec, prefill_diagnostics,
    random_gram_matched_component_vector, select_concept_layers, tokenizer_content_hash,
    validate_component_pair,
)
from vjp_steering.vjp import _resolve_j_lens_file
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
    vjp_delta,
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
J_LENS_CONCEPT_GRID = (1.0, 4.0, 16.0)
CONCEPT_METHODS = {"j_lens_concept", COMPONENT_PAIR_METHOD}


def parse_extension_coeffs(text: str) -> list[float]:
    return [float(value) for value in (text or "").split(",") if value.strip()]


def validate_explicit_grid(method: str, dev: bool, plus: str, minus: str) -> dict[str, list[float]] | None:
    """Validate an explicit bounded DEV dose grid that skips calibration search.

    For a small prespecified diagnostic (e.g. injection magnitudes 1,2,4,8,16),
running search_boundary would spend many unneeded cells. Unlike the rejected
--coefficients-plus/minus (full-profile semantics, silently ignored in DEV),
the explicit grid is recorded verbatim in manifest["grid"] with boundaries
marked as explicit (no C_approx search trace), so provenance stays honest.
Returns the side map, or None when not requested.
    """
    if not ((plus or "").strip() or (minus or "").strip()):
        return None
    if not dev:
        raise ValueError("explicit DEV grid is DEV-only")
    if method in CONCEPT_METHODS:
        raise ValueError("explicit grid currently supports non-concept methods only")
    grid = {"+C": parse_extension_coeffs(plus), "-C": parse_extension_coeffs(minus)}
    if not all(grid.values()):
        raise ValueError("explicit grid requires at least one dose per side")
    if any(not math.isfinite(c) or c <= 0 for values in grid.values() for c in values):
        raise ValueError("explicit grid doses must be finite positive magnitudes")
    return grid


def validate_extension_args(method: str, dev: bool, ext_id: str, plus: str, minus: str) -> dict[str, list[float]] | None:
    """Validate an explicit post-calibration extension (e.g. low_extension_0p40).

    Unlike --coefficients-plus/minus (full-profile only, rejected in DEV by
    reject_dev_supplied_grid), extension doses are deliberate additions to a frozen
    calibrated experiment: they never touch grid/boundaries and are recorded under
    manifest["extensions"][ext_id] with a stable identity. Returns the side map, or
    None when no extension was requested.
    """
    if not (ext_id or (plus or "").strip() or (minus or "").strip()):
        return None
    if not ext_id or not re.match(r"^[A-Za-z0-9_]+$", ext_id):
        raise ValueError("extension requires --extension-id matching ^[A-Za-z0-9_]+$")
    if not dev:
        raise ValueError("extension cells are DEV-only")
    if method in CONCEPT_METHODS:
        raise ValueError("extension cells currently support non-concept methods only")
    coeffs = {"+C": parse_extension_coeffs(plus), "-C": parse_extension_coeffs(minus)}
    if not any(coeffs.values()):
        raise ValueError("extension id without extension coefficients")
    if any(not math.isfinite(c) or c <= 0 for values in coeffs.values() for c in values):
        raise ValueError("extension coefficients must be finite positive magnitudes")
    return coeffs


def record_extension_identity(manifest: dict, ext_id: str, side_coeffs: dict[str, list[float]]) -> dict[str, list[float]]:
    """Merge requested doses into manifest["extensions"][ext_id] (monotonic union).

    The rung identity is the union of all doses ever recorded under the id; doses are
    never removed or renumbered, so a later partial run cannot redefine the rung.
    """
    ext = manifest.setdefault("extensions", {}).setdefault(ext_id, {"side_coeffs": {side: [] for side in ("+C", "-C")}})
    for side in ("+C", "-C"):
        have = list(ext["side_coeffs"].get(side, []))
        for coeff in side_coeffs.get(side, []):
            if not any(math.isclose(coeff, known, rel_tol=1e-12) for known in have):
                have.append(coeff)
        ext["side_coeffs"][side] = sorted(have)
    return {side: list(ext["side_coeffs"][side]) for side in ("+C", "-C")}


def extension_cells_complete(manifest: dict, root: Path, ext_id: str, side_coeffs: dict[str, list[float]], limit: int) -> bool:
    cells = manifest.get("cells", {})
    for side in ("+C", "-C"):
        for coefficient in side_coeffs.get(side, []):
            entry = cells.get(side, {}).get(f"{coefficient:.12g}")
            if not entry or len(read_jsonl(root / entry["path"])) < limit:
                return False
    recorded = manifest.get("extensions", {}).get(ext_id, {}).get("side_coeffs", {})
    for side in ("+C", "-C"):
        for coefficient in side_coeffs.get(side, []):
            if not any(math.isclose(coefficient, known, rel_tol=1e-12) for known in recorded.get(side, [])):
                return False
    return True


def reject_dev_supplied_grid(method: str, dev: bool, plus: str, minus: str) -> None:
    """Fail fast when a caller supplies explicit DEV doses for a calibrated method.

    Non-concept DEV grids come from search_boundary/dev_grid; --coefficients
    args are full-profile only and would otherwise be silently ignored (as in
    task 876, which ran 29 calibrated cells instead of the requested grid).
    Concept DEV grids honor --coefficients via concept_grid, so they are exempt.
    """
    if dev and method not in CONCEPT_METHODS and ((plus or "").strip() or (minus or "").strip()):
        raise ValueError(
            "DEV grid is calibrated (search_boundary/dev_grid); --coefficients-plus/minus "
            "are full-profile only and would be silently ignored in DEV. Omit them for DEV "
            "or rerun with the full profile."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("method", choices=METHODS)
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--gpu-stage", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--concept-smoke", action="store_true")
    parser.add_argument("--concept-calibrate", action="store_true")
    parser.add_argument("--persona-prompt-control", action="store_true")
    parser.add_argument("--source-experiment", default="")
    parser.add_argument("--reuse-extraction-from", default="")
    parser.add_argument("--reuse-component-extraction-from", default="")
    parser.add_argument("--component-empirical-candor", action="store_true")
    parser.add_argument("--selected-empirical-candor-full", action="store_true")
    parser.add_argument("--behavior-target", choices=("", "candidness"), default="")
    parser.add_argument("--lens-file", type=Path)
    parser.add_argument("--layers", default="")
    parser.add_argument("--target-layer", type=int)
    parser.add_argument("--reuse-bare-from", default="")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--experiment-id", default="")
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", choices=("float32", "bfloat16"), default="bfloat16")
    parser.add_argument("--n-pairs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--extract-batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--coefficients-plus", default="")
    parser.add_argument("--coefficients-minus", default="")
    parser.add_argument("--extension-id", default="")
    parser.add_argument("--extension-plus", default="")
    parser.add_argument("--extension-minus", default="")
    parser.add_argument("--explicit-grid-plus", default="")
    parser.add_argument("--explicit-grid-minus", default="")
    parser.add_argument("--concept-layers", default="")
    parser.add_argument("--concept-application-mask", choices=("user_turn", "final_prompt"), default="user_turn")
    parser.add_argument("--concept-sides", default="+C,-C")
    parser.add_argument("--random-control-seed", type=int)
    parser.add_argument("--random-control-coefficient", type=float)
    parser.add_argument(
        "--j-lens-source", choices=("concept", "persona", "persona_prefill", "persona_components"),
        default="concept",
    )
    parser.add_argument("--persona-direction", choices=("j_gp16", "full_residual"), default="j_gp16")
    parser.add_argument("--verify-extraction", action="store_true")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--j-lens-diagnostic", action="store_true")
    parser.add_argument(
        "--diagnostic-output",
        default="outputs/audits/20260905_j_lens_paper_native/diagnostic.json",
    )
    args = parser.parse_args()
    if (args.random_control_seed is None) != (args.random_control_coefficient is None):
        raise ValueError("random control requires both seed and coefficient")
    component_control = args.method == COMPONENT_PAIR_METHOD and args.component_empirical_candor
    if args.random_control_seed is not None and (
        not args.dev or args.random_control_coefficient <= 0
        or (args.method != "j_lens_concept" and not component_control)
    ):
        raise ValueError("random control is DEV-only with a positive coefficient")
    if args.concept_application_mask == "final_prompt" and args.method != "j_lens_concept":
        raise ValueError("final_prompt application is only defined for j_lens_concept")
    args.concept_sides = tuple(args.concept_sides.split(","))
    if not args.concept_sides or len(set(args.concept_sides)) != len(args.concept_sides) or set(args.concept_sides) - {"+C", "-C"}:
        raise ValueError("concept sides must be a nonempty unique subset of +C,-C")
    if args.selected_empirical_candor_full and not args.component_empirical_candor:
        raise ValueError("selected empirical candidness full requires the component-pair route")
    if args.component_empirical_candor:
        if args.method != COMPONENT_PAIR_METHOD:
            raise ValueError("empirical candidness requires component-pair J-lens")
        if args.dev == args.selected_empirical_candor_full:
            raise ValueError("empirical candidness requires DEV or explicit selected full, not both")
        if args.concept_sides != ("+C",) or args.behavior_target != "candidness":
            raise ValueError("empirical candidness requires source side +C and behavior target candidness")
        if args.concept_application_mask != "user_turn":
            raise ValueError("component target-order application is fixed to all attended prefill positions")
        if not args.reuse_component_extraction_from:
            raise ValueError("empirical candidness requires an explicit frozen component extraction")
        if [float(value) for value in args.coefficients_plus.split(",") if value] != [0.5]:
            raise ValueError("empirical candidness is fixed to source coefficient .5")
        if args.coefficients_minus:
            raise ValueError("empirical candidness has no source -C arm")
        if args.dev and args.random_control_coefficient != 0.5:
            raise ValueError("empirical candidness DEV control is fixed to coefficient .5")
        if args.selected_empirical_candor_full and args.random_control_seed is not None:
            raise ValueError("selected empirical candidness full has no random arm")
    elif args.reuse_component_extraction_from:
        raise ValueError("component extraction reuse requires the empirical-candor route")
    if not args.experiment_id and args.method not in DEFAULT_EXPERIMENT_IDS:
        raise ValueError(f"{args.method} requires --experiment-id")
    args.experiment_id = args.experiment_id or DEFAULT_EXPERIMENT_IDS[args.method]
    if args.reuse_bare_from and not args.dev:
        raise ValueError("reused bare generations are DEV-only")
    reject_dev_supplied_grid(args.method, args.dev, args.coefficients_plus, args.coefficients_minus)
    validate_extension_args(args.method, args.dev, args.extension_id, args.extension_plus, args.extension_minus)
    validate_explicit_grid(args.method, args.dev, args.explicit_grid_plus, args.explicit_grid_minus)
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
    if method in (COMPONENT_PAIR_METHOD, "j_lens_injection"):
        # Injection semantics live in WHICH concept vector is applied per side, so both
        # sides use positive magnitudes (paper: positive alpha injects the concept).
        return coefficient
    return signed_coefficient(side, coefficient)


def vector_sha256(vector: Vector) -> str:
    digest = hashlib.sha256()
    for kind, tree in (("shared", vector.shared), ("stacked", vector.stacked)):
        for layer, tensors in sorted(tree.items()):
            for name, tensor in sorted(tensors.items()):
                value = tensor.detach().contiguous().cpu()
                digest.update(f"{kind}:{layer}:{name}:{value.dtype}:{tuple(value.shape)}".encode())
                digest.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def random_matched_concept_vector(vector: Vector, seed: int) -> tuple[Vector, dict]:
    if vector.cfg.method != "j_lens_concept":
        raise ValueError("random concept control requires j_lens_concept")
    generator = torch.Generator(device="cpu").manual_seed(seed)
    stacked, layer_checks = {}, {}
    for layer in vector.cfg.layers:
        source = vector.stacked[layer]["v"].sum(0).detach().float().cpu()
        random_direction = torch.randn(source.shape, generator=generator)
        random_direction = random_direction / random_direction.norm() * source.norm()
        stacked[layer] = {"v": random_direction.unsqueeze(0).to(vector.stacked[layer]["v"].dtype)}
        layer_checks[str(layer)] = {
            "source_norm": source.norm().item(),
            "random_norm": random_direction.norm().item(),
            "cosine": torch.nn.functional.cosine_similarity(source, random_direction, dim=0).item(),
        }
    cfg = type(vector.cfg)(layers=tuple(vector.cfg.layers))
    cfg.dtype = vector.cfg.dtype
    return Vector(cfg, {}, stacked), layer_checks


def random_control_complete(manifest: dict, root: Path, args: argparse.Namespace, limit: int) -> bool:
    if args.random_control_seed is None:
        return True
    controls = manifest.get("controls", {})
    for side in args.concept_sides:
        name = "random_plus" if side == "+C" else "random_minus"
        control = controls.get(name)
        if not control:
            return False
        if control["seed"] != args.random_control_seed or not math.isclose(
            control["coefficient"], args.random_control_coefficient, rel_tol=1e-12
        ):
            return False
        if len(read_jsonl(root / control["path"])) < limit:
            return False
    return True


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


def persona_prefill_prompts(args: argparse.Namespace, tokenizer) -> tuple[list[str], list[str]]:
    entries = load_suffixes(thinking=True)
    rng = random.Random(0)
    sampled = rng.sample(entries, min(args.n_pairs, len(entries)))
    positive, negative = [], []
    for entry in sampled:
        user_message = entry["user_msg"]
        for persona, output in (("sycophantic", positive), ("abrasive", negative)):
            content = walk.PERSONA_TEMPLATE.format(persona=persona) + "\n\n" + user_message
            output.append(tokenizer.apply_chat_template(
                [{"role": "user", "content": content}], tokenize=False,
                add_generation_prompt=True, enable_thinking=False,
            ))
    lengths = tokenizer(positive + negative, add_special_tokens=False)["input_ids"]
    if max(map(len, lengths)) > args.max_length:
        raise ValueError("prefill persona extraction prompt truncation")
    return positive, negative


def persona_component_prefill_prompts(
    args: argparse.Namespace, tokenizer,
) -> tuple[dict[str, list[str]], list[str], list[int]]:
    spec, _ = persona_component_spec(args.persona_direction)
    entries = load_suffixes(thinking=False)
    if args.n_pairs != spec["source_pool_count"] or len(entries) != spec["source_pool_count"]:
        raise ValueError(
            f"persona component extraction requires the complete {spec['source_pool_count']}-entry source pool, "
            f"got {args.n_pairs=}, {len(entries)=}"
        )
    unique_by_message = {entry["user_msg"]: entry for entry in entries}
    if len(unique_by_message) != spec["expected_unique_sources"]:
        raise ValueError(
            f"persona component source pool has {len(unique_by_message)} unique rendered messages; "
            f"expected {spec['expected_unique_sources']}"
        )
    sampled = random.Random(spec["source_seed"]).sample(
        list(unique_by_message.values()), len(unique_by_message),
    )
    source_ids = [hashlib.sha256(entry["user_msg"].encode()).hexdigest() for entry in sampled]
    condition_prompts = {name: [] for name in ("positive", "negative", "baseline")}
    for entry in sampled:
        for name in condition_prompts:
            content = spec[f"{name}_instruction"] + "\n\n" + entry["user_msg"]
            condition_prompts[name].append(tokenizer.apply_chat_template(
                [{"role": "user", "content": content}], tokenize=False,
                add_generation_prompt=True, enable_thinking=False,
            ))
    lengths = tokenizer(
        [prompt for prompts in condition_prompts.values() for prompt in prompts],
        add_special_tokens=False,
    )["input_ids"]
    if max(map(len, lengths)) > args.max_length:
        raise ValueError("persona component prefill prompt truncation")
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("persona component source IDs are not unique")
    empty_message = [{"role": "user", "content": ""}]
    user_only = tokenizer.apply_chat_template(empty_message, tokenize=True, add_generation_prompt=False)
    full_prompt = tokenizer.apply_chat_template(
        empty_message, tokenize=True, add_generation_prompt=True, enable_thinking=False,
    )
    user_only = user_only["input_ids"] if isinstance(user_only, Mapping) else user_only
    full_prompt = full_prompt["input_ids"] if isinstance(full_prompt, Mapping) else full_prompt
    if full_prompt[:len(user_only)] != user_only or len(full_prompt) == len(user_only):
        raise ValueError("chat template does not have a fixed assistant-generation suffix")
    return condition_prompts, source_ids, full_prompt[len(user_only):]


def validate_persona_component_source_identity(args, metadata: dict, model, tokenizer) -> None:
    prompts, source_ids, assistant_suffix = persona_component_prefill_prompts(args, tokenizer)
    spec, spec_hash = persona_component_spec(args.persona_direction)
    source_hash = hashlib.sha256(
        json.dumps([spec_hash, source_ids, prompts], separators=(",", ":")).encode()
    ).hexdigest()
    expected = {
        "n_pairs": spec["expected_unique_sources"],
        "source_sha256": source_hash,
        "source_ids": source_ids,
        "source_prompts": prompts,
        "assistant_suffix_token_ids": assistant_suffix,
        "model_revision": getattr(model.config, "_commit_hash", None),
        "tokenizer_revision": tokenizer.init_kwargs.get("_commit_hash"),
        "tokenizer_content_sha256": tokenizer_content_hash(tokenizer),
    }
    actual = {key: metadata.get(key) for key in expected}
    if actual != expected:
        differing = [key for key in expected if actual[key] != expected[key]]
        raise ValueError(f"persona component source identity mismatch: {differing}")


def extract_vectors(args: argparse.Namespace, model, tokenizer) -> tuple[dict[str, Vector], dict, int, str]:
    if args.method == COMPONENT_PAIR_METHOD:
        available = walk.resolve_layers(model, None)
        paper_workspace = tuple(range(13, 22))
        if set(paper_workspace) <= set(available):
            layers = paper_workspace
        elif args.model == "wassname/qwen3-5lyr-tiny-random":
            layers = available
        else:
            raise ValueError(f"{COMPONENT_PAIR_METHOD} requires layers 13-21; available={available}")
        rows, _ = walk.read_cohort(DEV.cohort_size)
        dev_prompts = walk.generation_inputs(tokenizer, rows)
        if args.j_lens_source == "persona_components":
            condition_prompts, source_ids, assistant_suffix = persona_component_prefill_prompts(args, tokenizer)
            vectors, metadata = extract_persona_components(
                model, tokenizer, layers, condition_prompts=condition_prompts,
                source_ids=source_ids, assistant_suffix_token_ids=assistant_suffix,
                batch_size=args.extract_batch_size,
                max_length=args.max_length, dev_prompts=dev_prompts,
                projection=args.persona_direction, lens_file=args.lens_file,
            )
            return (
                vectors, metadata, len(source_ids),
                f"persona_components-{args.persona_direction}:" + metadata["source_sha256"],
            )
        if args.j_lens_source != "concept":
            raise ValueError(f"unsupported component source {args.j_lens_source}")
        vectors, metadata = extract_concept(
            model, tokenizer, layers, batch_size=args.extract_batch_size,
            max_length=args.max_length, dev_prompts=dev_prompts,
            lens_file=args.lens_file, separate_components=True,
        )
        return vectors, metadata, 0, "separate_components:" + metadata["spec_sha256"]
    if args.method == "j_lens_concept":
        layers = walk.resolve_layers(model, None)
        if args.j_lens_source in {"persona", "persona_prefill"}:
            source = args.j_lens_source
            positive, negative = (
                extraction_prompts(args, tokenizer) if source == "persona"
                else persona_prefill_prompts(args, tokenizer)
            )
            representation_source = (
                "matched_persona_prompt_difference" if source == "persona"
                else "matched_persona_prefill_difference"
            )
            vectors, metadata = extract_persona_contrast(
                model, tokenizer, layers, positive_prompts=positive, negative_prompts=negative,
                batch_size=args.extract_batch_size, max_length=args.max_length,
                direction=args.persona_direction, representation_source=representation_source,
                lens_file=args.lens_file,
            )
            return vectors, metadata, len(positive), f"{source}-{args.persona_direction}:" + metadata["prompt_sha256"]
        rows, _ = walk.read_cohort(DEV.cohort_size)
        vectors, metadata = extract_concept(
            model, tokenizer, layers, batch_size=args.extract_batch_size,
            max_length=args.max_length, dev_prompts=walk.generation_inputs(tokenizer, rows),
            lens_file=args.lens_file,
        )
        return vectors, metadata, 0, "concept:" + metadata["spec_sha256"]
    if args.method == "j_lens_swap":
        available = walk.resolve_layers(model, None)
        if args.layers:
            layers = tuple(int(layer) for layer in args.layers.split(",") if layer.strip() != "")
            if not set(layers) <= set(available):
                raise ValueError(f"j_lens_swap requested layers {layers} not subset of available {available}")
        else:
            paper_workspace = tuple(range(13, 22))
            layers = paper_workspace if set(paper_workspace) <= set(available) else available
        vector, swap_metadata = j_lens_swap(
            model, tokenizer, layers,
            source_token=J_LENS_SWAP_SOURCE, target_token=J_LENS_SWAP_TARGET,
        )
        return {
            "+C": vector,
            "-C": vector,
        }, {
            "source_layers": list(layers),
            "semantic_directions": {"+C": swap_metadata, "-C": swap_metadata},
            "coefficient_semantics": "+C exchanges abrasive/flattering coordinates; -C extrapolates away from exchange",
        }, 0, f"paper_swap:{J_LENS_SWAP_SOURCE}<->{J_LENS_SWAP_TARGET}"
    if args.method == "j_lens_unit_direction":
        available = walk.resolve_layers(model, None)
        if args.layers:
            layers = tuple(int(layer) for layer in args.layers.split(",") if layer.strip() != "")
            if not set(layers) <= set(available):
                raise ValueError(f"j_lens_unit_direction requested layers {layers} not subset of available {available}")
        else:
            layers = (16,)  # default to single source-active L16 per evidence
        from vjp_steering.vjp import j_lens_unit_direction
        vector, meta = j_lens_unit_direction(model, tokenizer, layers)
        return {"+C": vector, "-C": vector}, {"source_layers": list(layers), "semantic_directions": {"+C": meta, "-C": meta}, "coefficient_semantics": meta["coefficient_semantics"]}, 0, f"unit_direction:{meta['source_token']}<->{meta['target_token']}:L{','.join(map(str,layers))}"
    if args.method == "j_lens_injection":
        available = walk.resolve_layers(model, None)
        if args.layers:
            layers = tuple(int(layer) for layer in args.layers.split(",") if layer.strip() != "")
            if not set(layers) <= set(available):
                raise ValueError(f"j_lens_injection requested layers {layers} not subset of available {available}")
        else:
            layers = (16,)  # same single source-active L16 as the swap/unit comparisons
        from vjp_steering.vjp import j_lens_injection
        vectors, metas = {}, {}
        for side, concept in (("+C", J_LENS_SWAP_TARGET), ("-C", J_LENS_SWAP_SOURCE)):
            vector, meta = j_lens_injection(model, tokenizer, layers, concept_token=concept)
            vectors[side], metas[side] = vector, meta
        return vectors, {
            "source_layers": list(layers),
            "semantic_directions": metas,
            "coefficient_semantics": "positive C injects the side concept (+C flattering, -C abrasive); persona choice is our adaptation, single-concept injection is paper behavior",
        }, 0, f"paper_injection:+C={J_LENS_SWAP_TARGET}/-C={J_LENS_SWAP_SOURCE}:L{','.join(map(str,layers))}"

    layers = (
        tuple(int(layer) for layer in args.layers.split(",") if layer)
        if args.layers else walk.resolve_layers(model, None)
    )
    positive, negative = extraction_prompts(args, tokenizer)
    if args.method == "random":
        vector = Vector.train(
            model, tokenizer, positive, negative,
            RandomC(layers=layers, dtype=getattr(torch, args.dtype), seed=args.seed),
            batch_size=args.extract_batch_size, max_length=args.max_length,
        )
        return {"+C": vector, "-C": vector}, {"source_layers": list(layers), "control": "seeded unit vector per source layer"}, 0, f"random_seed:{args.seed}"

    if args.method == "vjp_delta":
        if args.target_layer is None:
            raise ValueError("vjp_delta requires --target-layer for reproducible DEV comparison")
        vector = vjp_delta(
            model, tokenizer, positive, negative, layers,
            target_layer=args.target_layer, batch_size=args.extract_batch_size,
            max_length=args.max_length, skip_first=16,
        )
        vectors, metadata = {"+C": vector, "-C": vector}, {"source_layers": list(layers), "target_layer": args.target_layer}
    elif args.method == "mean_diff":
        vector = Vector.train(
            model, tokenizer, positive, negative,
            MeanDiffC(layers=layers, dtype=getattr(torch, args.dtype), seed=args.seed),
            batch_size=args.extract_batch_size, max_length=args.max_length,
        )
        vectors, metadata = {"+C": vector, "-C": vector}, {"source_layers": list(layers)}
    else:
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


def validate_component_empirical_candor_source(args, metadata) -> None:
    if not args.component_empirical_candor:
        raise ValueError("component empirical source used outside its route")
    if metadata["method"] != COMPONENT_PAIR_METHOD:
        raise ValueError("empirical candidness source has wrong method")
    if (metadata["model"], metadata["dtype"]) != (args.model, args.dtype):
        raise ValueError("empirical candidness source model/dtype mismatch")
    if metadata["operator"] != COMPONENT_PAIR_VERSION:
        raise ValueError("empirical candidness source operator mismatch")
    if tuple(metadata["source_layers"]) != tuple(range(13, 22)):
        raise ValueError("empirical candidness source layers changed")
    if metadata["vector_content_sha256"]["+C"] != "dd4e78e9c429e51e4fe2d4e70e0db28c96d5c4c218b5f317767393ac38883197":
        raise ValueError("empirical candidness source vector hash changed")


def validate_extraction_identity(
    args, metadata, *, allow_explicit_legacy_reuse: bool = False,
    allow_explicit_component_reuse: bool = False,
):
    if (metadata["method"], metadata["model"], metadata["dtype"]) != (args.method, args.model, args.dtype):
        raise ValueError("extraction cache method/model/dtype mismatch")
    if args.method in CONCEPT_METHODS:
        lens_file = _resolve_j_lens_file(args.lens_file)
        lens_sha256 = hashlib.sha256(lens_file.read_bytes()).hexdigest()
        if metadata["lens_sha256"] != lens_sha256:
            raise ValueError("J-lens extraction cache lens mismatch")
    if args.method == COMPONENT_PAIR_METHOD:
        component_sources = {
            ("concept", "j_gp16"): (
                COMPONENT_PAIR_REPRESENTATION_SOURCE, COMPONENT_PAIR_VERSION, component_spec()[1],
            ),
            ("persona_components", "j_gp16"): (
                PERSONA_COMPONENT_PAIR_REPRESENTATION_SOURCE, PERSONA_COMPONENT_PAIR_VERSION,
                persona_component_spec("j_gp16")[1],
            ),
            ("persona_components", "full_residual"): (
                PERSONA_FULL_COMPONENT_PAIR_REPRESENTATION_SOURCE, PERSONA_FULL_COMPONENT_PAIR_VERSION,
                persona_component_spec("full_residual")[1],
            ),
        }
        source_key = (args.j_lens_source, args.persona_direction)
        if source_key not in component_sources:
            raise ValueError(f"unsupported component source/projection {source_key}")
        expected_source, expected_operator, expected_spec = component_sources[source_key]
        if metadata.get("representation_source") != expected_source:
            raise ValueError("separate J-lens component representation source mismatch")
        if metadata["operator"] != expected_operator or metadata["spec_sha256"] != expected_spec:
            raise ValueError("separate J-lens component specification mismatch")
        if metadata["implementation_sha256"] != implementation_hash():
            if not allow_explicit_component_reuse:
                raise ValueError("separate J-lens component implementation mismatch")
            validate_component_empirical_candor_source(args, metadata)
    if args.method == "j_lens_concept":
        source = getattr(args, "j_lens_source", "concept")
        expected_source = {
            "concept": "concept_mean100",
            "persona": "matched_persona_prompt_difference",
            "persona_prefill": "matched_persona_prefill_difference",
        }[source]
        if metadata.get("representation_source", "concept_mean100") != expected_source:
            raise ValueError("J-lens extraction representation source mismatch")
        implementation_matches = metadata["implementation_sha256"] == implementation_hash()
        legacy_reuse = (
            source == "concept" and allow_explicit_legacy_reuse
            and metadata["implementation_sha256"] == LEGACY_EXTRACTION_IMPLEMENTATION_SHA256
        )
        if source == "concept" and metadata["spec_sha256"] != concept_spec()[1]:
            raise ValueError("concept extraction specification mismatch")
        persona_direction = getattr(args, "persona_direction", "j_gp16")
        expected_persona_operator = (
            PERSONA_VERSION if persona_direction == "j_gp16" else PERSONA_FULL_RESIDUAL_VERSION
        )
        if source in {"persona", "persona_prefill"} and (
            metadata["operator"] != expected_persona_operator
            or metadata["projection"] != persona_direction
            or metadata["n_pairs"] != args.n_pairs
        ):
            raise ValueError("persona extraction specification mismatch")
        if not (implementation_matches or legacy_reuse):
            raise ValueError("J-lens extraction implementation mismatch")
        if legacy_reuse:
            logger.warning(
                "EXPLICIT_LEGACY_EXTRACTION_REUSE source_implementation={} current_implementation={}",
                metadata["implementation_sha256"], implementation_hash(),
            )


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
        validate_extraction_identity(
            args,
            metadata,
            allow_explicit_legacy_reuse=bool(args.reuse_extraction_from),
            allow_explicit_component_reuse=bool(args.reuse_component_extraction_from),
        )
        if args.method == COMPONENT_PAIR_METHOD and args.j_lens_source == "persona_components":
            validate_persona_component_source_identity(args, metadata, model, tokenizer)
        vectors = {side: Vector.load(str(path)) for side, path in paths.items()}
        for side, vector in vectors.items():
            if vector.cfg.method != args.method or tuple(vector.cfg.layers) != tuple(metadata["source_layers"]):
                raise ValueError(f"saved extraction vector config mismatch for {side}")
        actual = {side: vector_sha256(vector) for side, vector in vectors.items()}
        if actual != metadata["vector_content_sha256"]:
            raise ValueError("saved extraction vector hash mismatch")
        if args.method == COMPONENT_PAIR_METHOD:
            validate_component_pair(vectors)
        return vectors, metadata

    if args.reuse_component_extraction_from:
        source = experiment_dir(args.reuse_component_extraction_from)
        source_path = source / "extraction/metadata.json"
        source_metadata = json.loads(source_path.read_text())
        validate_component_empirical_candor_source(args, source_metadata)
        vectors = {side: Vector.load(str(source / source_metadata["vector_files"][side])) for side in paths}
        validate_component_pair(vectors)
        if {side: vector_sha256(vector) for side, vector in vectors.items()} != source_metadata["vector_content_sha256"]:
            raise ValueError("empirical candidness source vector hash mismatch")
        paths["+C"].parent.mkdir(parents=True, exist_ok=True)
        for side, vector in vectors.items():
            vector.save(str(paths[side]))
        metadata = {
            **source_metadata,
            "extraction_reused_from": args.reuse_component_extraction_from,
            "source_metadata_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "current_execution_implementation_sha256": implementation_hash(),
        }
        atomic_json(metadata_path, metadata)
        logger.info(
            "EMPIRICAL_COMPONENT_EXTRACTION_REUSED source={} hash_plus={}",
            args.reuse_component_extraction_from,
            metadata["vector_content_sha256"]["+C"],
        )
        return vectors, metadata

    if args.reuse_extraction_from:
        if args.method != "j_lens_concept":
            raise ValueError("extraction reuse flag is restricted to concept calibration")
        source = experiment_dir(args.reuse_extraction_from)
        source_path = source / "extraction/metadata.json"
        metadata = json.loads(source_path.read_text())
        validate_extraction_identity(args, metadata, allow_explicit_legacy_reuse=True)
        vectors = {side: Vector.load(str(source / metadata["vector_files"][side])) for side in paths}
        for side, vector in vectors.items():
            if vector.cfg.method != args.method or tuple(vector.cfg.layers) != tuple(metadata["source_layers"]):
                raise ValueError(f"source extraction vector config mismatch for {side}")
        if {side: vector_sha256(v) for side, v in vectors.items()} != metadata["vector_content_sha256"]:
            raise ValueError("source extraction vector hash mismatch")
        paths["+C"].parent.mkdir(parents=True, exist_ok=True)
        for side, vector in vectors.items():
            vector.save(str(paths[side]))
        metadata = {
            **metadata,
            "extraction_reused_from": args.reuse_extraction_from,
            "source_metadata_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "current_implementation_sha256": implementation_hash(),
        }
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
    behavior_target: str,
) -> list[dict]:
    return [
        {
            "status": "DEV" if profile_name == "dev" else "FORMATIVE",
            "profile": profile_name,
            "side": side,
            "source_side": side,
            "behavior_target": behavior_target or None,
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
    elif args.method in CONCEPT_METHODS:
        answers = walk.generate(
            model, tokenizer, missing_prompts, args.batch_size, args.max_new_tokens,
            prefill_vector=vector,
            coefficient=applied_coefficient(args.method, side, coefficient),
            concept_application_mask=args.concept_application_mask,
        )
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
        behavior_target=args.behavior_target,
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
    if not coefficients or not any(coefficients.values()):
        return None
    bare = manifest.get("bare")
    if not bare or len(read_jsonl(root / bare["path"])) < limit:
        return None
    count = 0
    for side in args.concept_sides:
        for coefficient in coefficients[side]:
            entry = manifest.get("cells", {}).get(side, {}).get(f"{coefficient:.12g}")
            if not entry or len(read_jsonl(root / entry["path"])) < limit:
                return None
            if args.method == "j_lens_swap" and "lens_token_leaks" not in entry["health"]:
                return None
            count += 1
    return count


def concept_application_layers(args: argparse.Namespace, available_layers) -> tuple[int, ...]:
    if not args.concept_layers:
        return tuple(available_layers)
    return tuple(int(value) for value in args.concept_layers.split(",") if value)


def concept_grid(args):
    grid = {
        side: ([float(c) for c in text.split(",") if c] if text else list(J_LENS_CONCEPT_GRID))
        if side in args.concept_sides else []
        for side, text in (("+C", args.coefficients_plus), ("-C", args.coefficients_minus))
    }
    if any(not math.isfinite(c) or c <= 0 for values in grid.values() for c in values):
        raise ValueError("concept grid requires finite positive magnitudes")
    return grid


def reuse_dev_bare(args: argparse.Namespace, bare_path: Path, rows: list[dict]) -> list[dict] | None:
    if not args.reuse_bare_from:
        return None
    source_root = experiment_dir(args.reuse_bare_from)
    source_manifest = json.loads((source_root / "manifest.json").read_text())
    source_bare = source_root / source_manifest["bare"]["path"]
    source_rows = read_jsonl(source_bare)
    wanted = [row["scenario"] for row in rows]
    selected = [row for row in source_rows if row["scenario"] in set(wanted)]
    if [row["scenario"] for row in selected] != wanted:
        raise ValueError("reused bare artifact does not match the ordered DEV cohort")
    if any(row["profile"] != "dev" or row["coefficient"] != 0.0 for row in selected):
        raise ValueError("reused bare artifact is not DEV bare generation")
    if bare_path.exists():
        existing = read_jsonl(bare_path)
        if existing != selected:
            raise ValueError("local bare artifact differs from its declared shared source")
    else:
        atomic_jsonl(bare_path, selected)
    return selected


def gpu_stage(args: argparse.Namespace) -> None:
    reject_dev_supplied_grid(args.method, args.dev, args.coefficients_plus, args.coefficients_minus)
    if args.method in CONCEPT_METHODS and not args.dev and not args.selected_empirical_candor_full:
        raise ValueError("concept intervention is DEV-only")
    profile_name = "dev" if args.dev else "full"
    limit = DEV.cohort_size if args.dev else FULL.cohort_size
    root = experiment_dir(args.experiment_id)
    root.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path(args.experiment_id).read_text()) if manifest_path(args.experiment_id).exists() else {
        "schema": ("j_lens_concept_experiment_v1" if args.method in CONCEPT_METHODS else
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
            "seed": args.seed,
            "j_lens_source": args.j_lens_source,
            "persona_direction": args.persona_direction,
            "component_empirical_candor": args.component_empirical_candor,
            "selected_empirical_candor_full": args.selected_empirical_candor_full,
            "source_side": "+C" if args.component_empirical_candor else None,
            "behavior_target": args.behavior_target or None,
        },
    }
    if manifest["method"] != args.method:
        raise ValueError("experiment id belongs to another method")
    if args.method == "j_lens_swap" and manifest["schema"] == "mlp_up_left_right_experiment_v1":
        manifest["schema"] = "j_lens_swap_experiment_v1"
        atomic_json(manifest_path(args.experiment_id), manifest)
    if args.method in CONCEPT_METHODS and "extraction" in manifest:
        validate_extraction_identity(
            args,
            manifest["extraction"],
            allow_explicit_legacy_reuse=bool(args.reuse_extraction_from),
            allow_explicit_component_reuse=bool(args.reuse_component_extraction_from),
        )
        requested_layers = concept_application_layers(args, manifest["extraction"]["source_layers"])
        saved_layers = tuple(manifest["extraction"].get("application_layers", manifest["extraction"]["source_layers"]))
        if requested_layers != saved_layers:
            raise ValueError(
                f"concept application layers are immutable within an experiment: saved={saved_layers} requested={requested_layers}"
            )
    if args.dev and "boundaries" in manifest:
        if args.method in CONCEPT_METHODS:
            expanded_grid = concept_grid(args)
        elif any("explicit_grid" in manifest["boundaries"][side] for side in ("+C", "-C")):
            expanded_grid = {side: list(manifest["boundaries"][side]["explicit_grid"]) for side in ("+C", "-C")}
        else:
            expanded_grid = {side: dev_grid(manifest["boundaries"][side]) for side in ("+C", "-C")}
        if manifest["grid"] != expanded_grid:
            manifest["grid"] = expanded_grid
            atomic_json(manifest_path(args.experiment_id), manifest)
    extension = validate_extension_args(args.method, args.dev, args.extension_id, args.extension_plus, args.extension_minus)
    completed_cells = completed_profile_cell_count(args, manifest, root, profile_name, limit)
    if (
        completed_cells is not None
        and random_control_complete(manifest, root, args, limit)
        and (extension is None or extension_cells_complete(manifest, root, args.extension_id, extension, limit))
        and not args.verify_extraction
    ):
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
    if args.method in CONCEPT_METHODS:
        layers = concept_application_layers(args, vectors["+C"].cfg.layers)
        vectors = {side: select_concept_layers(vector, layers) for side, vector in vectors.items()}
        extraction = {
            **extraction,
            "application_layers": list(layers),
            "application_vector_content_sha256": {side: vector_sha256(vector) for side, vector in vectors.items()},
        }
    prompts = walk.generation_inputs(tokenizer, rows)
    bare_path = root / "bare.jsonl"
    bare = reuse_dev_bare(args, bare_path, rows)
    if bare is None:
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
        if not args.dev and not args.selected_empirical_candor_full:
            raise RuntimeError("full mode requires its automatic dev stage first")
        explicit = validate_explicit_grid(args.method, args.dev, args.explicit_grid_plus, args.explicit_grid_minus)
        if explicit is not None:
            boundaries = {
                side: {
                    "meaning": "explicit bounded diagnostic grid, no calibration search",
                    "explicit_grid": sorted(values),
                    "C_approx": max(values),
                    "C_hi": max(values),
                    "trace": [],
                }
                for side, values in explicit.items()
            }
            grid = {side: sorted(values) for side, values in explicit.items()}
        elif args.method in CONCEPT_METHODS:
            meanings = (
                {"+C": "order coordinates toward positive component", "-C": "order coordinates toward negative component"}
                if args.method == COMPONENT_PAIR_METHOD
                else {"+C": "signed unit concept contrast", "-C": "signed unit concept contrast"}
            )
            boundaries = {side: {"meaning": meanings[side], "trace": []} for side in args.concept_sides}
            grid = concept_grid(args)
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
        manifest["answer_key_sha256"] = walk.answer_key_sha256(walk.read_cohort(100)[0])
        if args.component_empirical_candor:
            manifest["candidate"] = {
                "source_experiment": args.reuse_component_extraction_from,
                "source_side": "+C",
                "behavior_target": "candidness",
                "operator": extraction["operator"],
                "source_vector_sha256": extraction["vector_content_sha256"]["+C"],
                "layers": extraction["application_layers"],
                "coefficient": grid["+C"][0] if args.selected_empirical_candor_full else grid["+C"],
                "application_mask": "all_attended_prefill_positions",
            }
        atomic_json(manifest_path(args.experiment_id), manifest)
    coefficients = manifest["grid"] if args.dev else {
        "+C": [float(value) for value in args.coefficients_plus.split(",") if value],
        "-C": [float(value) for value in args.coefficients_minus.split(",") if value],
    }
    if not args.dev and not args.selected_empirical_candor_full and any(not coefficients[side] for side in ("+C", "-C")):
        raise ValueError("full GPU stage requires DEV-accepted candidates for both sides")
    generated_cells = 0
    encoded_prompts = None
    encoded_prompt_patch_mask = None
    execution_mask = None
    if args.method in CONCEPT_METHODS:
        encoded_prompts = tokenizer(
            prompts, return_tensors="pt", padding=True, add_special_tokens=False,
        ).to(args.device)
        encoded_prompt_patch_mask = concept_prefill_mask(
            tokenizer, encoded_prompts.input_ids, encoded_prompts.attention_mask, vectors["+C"],
            application_mask=args.concept_application_mask,
        )
        application_mask = (
            "all_attended_prefill_positions"
            if args.method == COMPONENT_PAIR_METHOD else args.concept_application_mask
        )
        execution_mask = mask_metadata(
            encoded_prompt_patch_mask, encoded_prompts.attention_mask, application_mask,
        )
        manifest["execution"] = {
            "implementation_sha256": implementation_hash(),
            "concept_application_mask": execution_mask,
            "reused_extraction_metadata": {
                "implementation_sha256": extraction["implementation_sha256"],
                "application_mask": extraction["application_mask"],
            },
        }
    for side in args.concept_sides:
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
                "source_side": side,
                "behavior_target": args.behavior_target or None,
                "path": str(cell_path(root, side, coefficient).relative_to(root)),
                "rows": len(records),
                "health": stats,
                "breakdown_reasons": reasons,
            }
            if args.method in CONCEPT_METHODS:
                assert encoded_prompts is not None and encoded_prompt_patch_mask is not None
                cell["realized_prefill"] = prefill_diagnostics(
                    model,
                    vectors[side],
                    encoded_prompts.input_ids,
                    encoded_prompts.attention_mask,
                    applied_coefficient(args.method, side, coefficient),
                    patch_mask=encoded_prompt_patch_mask,
                )
                cell["execution_mask"] = execution_mask
            manifest.setdefault("cells", {}).setdefault(side, {})[f"{coefficient:.12g}"] = cell
            atomic_json(manifest_path(args.experiment_id), manifest)
            generated_cells += 1
    # Explicit post-calibration extension (e.g. low_extension_0p40). Cell body mirrors the
    # grid loop above for non-concept methods; grid/boundaries are never touched, and the
    # rung identity lives under manifest["extensions"][id] (monotonic union, never renumbered).
    if extension is not None:
        if "grid" not in manifest:
            raise ValueError("extension requires the frozen calibrated grid first")
        recorded_before = {
            side: list(manifest.get("extensions", {}).get(args.extension_id, {}).get("side_coeffs", {}).get(side, []))
            for side in ("+C", "-C")
        }
        for side in ("+C", "-C"):
            for coefficient in extension[side]:
                entry = manifest.get("cells", {}).get(side, {}).get(f"{coefficient:.12g}")
                if entry is not None and len(read_jsonl(root / entry["path"])) >= limit and not any(
                    math.isclose(coefficient, known, rel_tol=1e-12) for known in recorded_before[side]
                ):
                    raise ValueError(
                        f"extension dose {side} C={coefficient:.12g} already measured outside {args.extension_id}; "
                        "refusing to re-label a grid cell as extension rung"
                    )
        record_extension_identity(manifest, args.extension_id, extension)
        atomic_json(manifest_path(args.experiment_id), manifest)
        for side in ("+C", "-C"):
            for coefficient in extension[side]:
                key = f"{coefficient:.12g}"
                entry = manifest.get("cells", {}).get(side, {}).get(key)
                if entry is not None and len(read_jsonl(root / entry["path"])) >= limit:
                    continue
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
                    "source_side": side,
                    "behavior_target": args.behavior_target or None,
                    "path": str(cell_path(root, side, coefficient).relative_to(root)),
                    "rows": len(records),
                    "health": stats,
                    "breakdown_reasons": reasons,
                }
                manifest.setdefault("cells", {}).setdefault(side, {})[key] = cell
                atomic_json(manifest_path(args.experiment_id), manifest)
                generated_cells += 1
    if args.random_control_seed is not None:
        if args.method == COMPONENT_PAIR_METHOD:
            random_vector, layer_checks = random_gram_matched_component_vector(
                vectors["+C"], args.random_control_seed
            )
            random_kind = "seeded_rank_two_gram_matched_target_order_control"
        else:
            random_vector, layer_checks = random_matched_concept_vector(
                vectors["+C"], args.random_control_seed
            )
            random_kind = "seeded_norm_matched_random_direction"
        assert encoded_prompts is not None and encoded_prompt_patch_mask is not None
        for side in args.concept_sides:
            name = "random_plus" if side == "+C" else "random_minus"
            if not coefficients[side]:
                continue
            random_path = root / "controls" / f"{name}.jsonl"
            random_records = extend_generation(
                random_path,
                rows,
                prompts,
                model,
                tokenizer,
                args,
                profile_name=profile_name,
                side=side,
                coefficient=args.random_control_coefficient,
                vector=random_vector,
            )
            random_stats, random_reasons = generation_health(
                args, tokenizer, [record["text"] for record in random_records]
            )
            manifest.setdefault("controls", {})[name] = {
                "kind": random_kind,
                "profile": profile_name,
                "seed": args.random_control_seed,
                "side": side,
                "source_side": side,
                "behavior_target": args.behavior_target or None,
                "coefficient": args.random_control_coefficient,
                "path": str(random_path.relative_to(root)),
                "rows": len(random_records),
                "vector_content_sha256": vector_sha256(random_vector),
                "source_vector_content_sha256": vector_sha256(vectors["+C"]),
                "per_layer": layer_checks,
                "health": random_stats,
                "breakdown_reasons": random_reasons,
                "realized_prefill": prefill_diagnostics(
                    model,
                    random_vector,
                    encoded_prompts.input_ids,
                    encoded_prompts.attention_mask,
                    applied_coefficient(args.method, side, args.random_control_coefficient),
                    patch_mask=encoded_prompt_patch_mask,
                ),
                "execution_mask": execution_mask,
            }
    manifest["profiles"][profile_name] = {
        "status": "DEV" if args.dev else "FORMATIVE",
        "cohort_size": limit,
        "generated": True,
    }
    manifest["bare"] = {
        "path": str(bare_path.relative_to(root)),
        "rows": len(bare),
        "reused_from": args.reuse_bare_from or None,
        "sha256": hashlib.sha256(bare_path.read_bytes()).hexdigest(),
    }
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
        "--seed", str(args.seed),
    ]
    if args.layers:
        command.extend(["--layers", args.layers])
    if args.target_layer is not None:
        command.extend(["--target-layer", str(args.target_layer)])
    if args.reuse_bare_from:
        command.extend(["--reuse-bare-from", args.reuse_bare_from])
    if args.verify_extraction:
        command.append("--verify-extraction")
    if args.reuse_extraction_from:
        command.extend(["--reuse-extraction-from", args.reuse_extraction_from])
    if args.reuse_component_extraction_from:
        command.extend(["--reuse-component-extraction-from", args.reuse_component_extraction_from])
    if args.component_empirical_candor:
        command.extend(["--component-empirical-candor", "--behavior-target", args.behavior_target])
    if args.selected_empirical_candor_full:
        command.append("--selected-empirical-candor-full")
    if args.concept_layers:
        command.extend(["--concept-layers", args.concept_layers])
    if args.random_control_seed is not None:
        command.extend([
            "--random-control-seed", str(args.random_control_seed),
            "--random-control-coefficient", str(args.random_control_coefficient),
        ])
    if args.j_lens_source != "concept":
        command.extend(["--j-lens-source", args.j_lens_source])
    if args.persona_direction != "j_gp16":
        command.extend(["--persona-direction", args.persona_direction])
    if args.method in CONCEPT_METHODS and dev:
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
    if args.method in CONCEPT_METHODS and not args.dev and not args.selected_empirical_candor_full:
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
    render_command = [
        sys.executable, "-m", "vjp_steering.results",
        "--experiment-id", args.experiment_id, "--profile", "dev",
    ]
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
    dev_manifest = json.loads(manifest_path(args.experiment_id).read_text())
    full_grid = dev_manifest["grid"]
    modal_stage(args, dev=False, coefficients=full_grid)
    run_resumable(
        [
            sys.executable, "scripts/judge.py",
            "--experiment-id", args.experiment_id,
            "--profile", "full", "--all-generated", "--refresh",
        ],
        attempts=12,
        label="OpenRouter full grid judge",
    )
    subprocess.run(
        [
            sys.executable, "scripts/export.py",
            "--experiment-id", args.experiment_id,
            "--profile", "full", "--all-generated",
        ],
        cwd=walk.ROOT,
        check=True,
    )
    render_command = [
        sys.executable, "-m", "vjp_steering.results",
        "--experiment-id", args.experiment_id, "--profile", "full",
    ]
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
    from judge import load_cohort, required_cells

    generator = torch.Generator().manual_seed(0)
    basis = torch.randn(2, 7, generator=generator)
    dual = torch.linalg.pinv(basis).T.contiguous()
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
    state = {"basis": basis, "dual": dual}
    torch.testing.assert_close(JLensSwap.apply(None, None, hidden, state, None, cfg), patched)
    one_token = hidden[:, :1]
    torch.testing.assert_close(JLensSwap.apply(None, None, one_token, state, None, cfg), one_token)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "swap.safetensors"
        vector = Vector(
            JLensSwapC(layers=(1,)),
            {1: {"basis": basis, "dual": dual}},
            {1: {}},
        )
        vector.save(str(path))
        assert vector_sha256(Vector.load(str(path))) == vector_sha256(vector)
    print("J_LENS_SWAP_SELF_TEST_PASS alpha0=identity alpha1=coordinate_exchange transfer=exact prompt_only=exact reload=exact")

    concept_vector = Vector(
        JLensConceptC(layers=(1, 2)),
        {},
        {layer: {"v": torch.ones(1, 7)} for layer in (1, 2)},
    )
    random_vector, random_checks = random_matched_concept_vector(concept_vector, seed=7)
    assert vector_sha256(random_vector) == vector_sha256(random_matched_concept_vector(concept_vector, seed=7)[0])
    for layer in (1, 2):
        assert math.isclose(
            random_checks[str(layer)]["source_norm"], random_checks[str(layer)]["random_norm"], rel_tol=1e-2
        )
    print("J_LENS_CONCEPT_RANDOM_CONTROL_SELF_TEST_PASS seeded=true norm_matched=true")

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "random.safetensors"
        vector = Vector(RandomC(layers=(1,), seed=4), {1: {}}, {1: {"v": torch.ones(1, 7)}})
        vector.save(str(path))
        loaded = Vector.load(str(path))
        assert loaded.cfg.method == "random" and loaded.cfg.seed == 4
    print("RANDOM_VECTOR_SELF_TEST_PASS save_load=exact")

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
    assert applied_coefficient("j_lens_swap", "-C", 2.0) == -2.0
    assert applied_coefficient(COMPONENT_PAIR_METHOD, "-C", 2.0) == 2.0
    scenarios = list(load_cohort())
    quick_rows = [
        {
            "bare": f"bare {question}",
            "steered": f"steered {side} {dose} {question}",
            "prompt": f"prompt {question}",
            "side": side,
            "vignette": scenarios[question],
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
            "vignette": scenarios[question],
        }
        for side in ("+C", "-C")
        for question in range(FULL.cohort_size)
    ]
    assert len(required_cells(quick_rows, DEV.orders, DEV.passes)) == 540
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
        args = SimpleNamespace(
            method="test", dev=True, coefficients_plus="", coefficients_minus="", concept_sides=("+C", "-C"),
        )
        assert completed_profile_cell_count(args, manifest, root, "dev", DEV.cohort_size) == GRID_POINTS * 2
    # Regression: non-concept DEV must reject supplied dose args instead of silently ignoring them (task 876 ran
    # 29 calibrated cells while the caller believed it had requested a {0,.25,.5,1,2,4,8} grid).
    try:
        reject_dev_supplied_grid("mean_diff", True, "0,0.25,0.5,1,2,4,8", "0,0.25,0.5,1,2,4,8")
    except ValueError:
        pass
    else:
        raise AssertionError("non-concept DEV with supplied coefficients must raise")
    reject_dev_supplied_grid("mean_diff", True, "", "")
    reject_dev_supplied_grid("mean_diff", False, "0,1", "0,1")
    reject_dev_supplied_grid("j_lens_concept", True, "0,1", "")
    # Extension mechanism: explicit DEV-only doses with stable rung identity (low_extension_0p40).
    assert validate_extension_args("mean_diff", True, "", "", "") is None
    assert validate_extension_args("mean_diff", True, "low_extension_0p40", "1.08", "0.86") == {"+C": [1.08], "-C": [0.86]}
    for bad in [
        ("mean_diff", True, "bad id", "1.0", ""),
        ("mean_diff", False, "low_extension_0p40", "1.0", ""),
        ("j_lens_concept", True, "low_extension_0p40", "1.0", ""),
        ("mean_diff", True, "low_extension_0p40", "", ""),
        ("mean_diff", True, "low_extension_0p40", "-1.0", ""),
        ("mean_diff", True, "low_extension_0p40", "0", ""),
    ]:
        try:
            validate_extension_args(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"extension validation must reject {bad}")
    manifest = {}
    first = record_extension_identity(manifest, "low_extension_0p40", {"+C": [1.08], "-C": [0.86]})
    assert first == {"+C": [1.08], "-C": [0.86]}
    second = record_extension_identity(manifest, "low_extension_0p40", {"+C": [1.08], "-C": [0.86]})
    assert second == first  # re-run is idempotent, never renumbered
    manifest["cells"] = {"+C": {"1.08": {"path": "cells/plus/c1p08.jsonl"}}, "-C": {}}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "cells" / "plus").mkdir(parents=True)
        (root / "cells" / "plus" / "c1p08.jsonl").write_text("{}\n" * DEV.cohort_size)
        assert not extension_cells_complete(manifest, root, "low_extension_0p40", {"+C": [1.08], "-C": [0.86]}, DEV.cohort_size)
        (root / "cells" / "minus").mkdir(parents=True)
        (root / "cells" / "minus" / "c0p86.jsonl").write_text("{}\n" * DEV.cohort_size)
        manifest["cells"]["-C"]["0.86"] = {"path": "cells/minus/c0p86.jsonl"}
        assert extension_cells_complete(manifest, root, "low_extension_0p40", {"+C": [1.08], "-C": [0.86]}, DEV.cohort_size)
    # Explicit bounded DEV grid: small prespecified diagnostics skip calibration search.
    assert validate_explicit_grid("mean_diff", True, "", "") is None
    assert validate_explicit_grid("mean_diff", True, "1,2,4,8,16", "1,2,4,8,16") == {
        "+C": [1.0, 2.0, 4.0, 8.0, 16.0], "-C": [1.0, 2.0, 4.0, 8.0, 16.0]}
    for bad in [
        ("mean_diff", True, "1,2", ""),
        ("mean_diff", True, "", "1"),
        ("mean_diff", False, "1", "1"),
        ("j_lens_concept", True, "1", "1"),
        ("mean_diff", True, "0", "1"),
        ("mean_diff", True, "-2", "1"),
    ]:
        try:
            validate_explicit_grid(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"explicit grid validation must reject {bad}")
    assert applied_coefficient("j_lens_injection", "-C", 2.0) == 2.0
    assert applied_coefficient("j_lens_injection", "+C", 2.0) == 2.0
    assert applied_coefficient("j_lens_swap", "-C", 2.0) == -2.0
    print("EXPERIMENT_SELF_TEST_PASS quick_calls=270 full_calls=400 resume_cells=18")


def main() -> None:
    args = parse_args()
    component_diagnostic = (
        args.self_test or args.concept_smoke or args.concept_calibrate or args.persona_prompt_control
        or args.extract_only or args.verify_extraction or args.component_empirical_candor
    )
    if args.method == COMPONENT_PAIR_METHOD and not component_diagnostic:
        raise ValueError(
            "j_lens_concept_components currently supports extraction and non-negative target-exchange calibration only; "
            "run the DEV diagnostic before enabling the normal results path"
        )
    if args.self_test:
        self_test()
        if args.method in CONCEPT_METHODS:
            from concept_checks import self_test as concept_self_test
            concept_self_test()
    elif args.concept_smoke:
        from concept_checks import smoke
        smoke(args)
    elif args.concept_calibrate:
        from concept_checks import calibrate
        calibrate(args)
    elif args.persona_prompt_control:
        from concept_checks import persona_prompt_control
        persona_prompt_control(args)
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
