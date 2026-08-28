"""Continue one missing directional health boundary without replacing an old paired walk."""

import argparse
import hashlib
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import torch
from loguru import logger
from steering_lite.data import make_persona_pairs
from transformers import AutoModelForCausalLM, AutoTokenizer

import walk


ROOT = Path(__file__).resolve().parents[1]
PROCEDURE = "continuation_side_health_v1"
HEALTH_RULE = "health_v1: unfinished<0.5, role_leak<0.25, repetition<0.25"
SEARCH_MAX_STEPS = 16
SEARCH_LOG_TOLERANCE = math.log(2.0) / 6.0
TAIL_FRACTION = 0.66


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("method", nargs="?", choices=("J_word", "vjp_delta", "vjp_mlp_up_shrink", "mean_diff", "pca"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--side", choices=("+C", "-C"))
    parser.add_argument("--continuation-id")
    parser.add_argument("--coefficient", type=float)
    parser.add_argument("--phase", choices=("search", "tail"))
    parser.add_argument("--walk", action="store_true")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def health_margin(stats: dict[str, float | int]) -> float:
    answers = int(stats["answers"])
    return min(
        0.5 - int(stats["unfinished"]) / answers,
        0.25 - int(stats["role_leaks"]) / answers,
        0.25 - int(stats["repeated"]) / answers,
    )


def assert_monotone_health(trace: list[dict]) -> None:
    ordered = sorted(trace, key=lambda entry: entry["coefficient"])
    clean = [entry["health_clean"] for entry in ordered]
    assert clean == sorted(clean, reverse=True), f"nonmonotone observed health trace: {ordered}"


def old_grid_tail(c_lo: float) -> tuple[list[float], int, list[float]]:
    grid = [coefficient for coefficient in walk.GRID if coefficient < c_lo]
    grid.append(c_lo)
    assert grid == sorted(set(grid))
    tail_start = math.ceil(TAIL_FRACTION * len(grid))
    tail = grid[tail_start:]
    assert tail == grid[tail_start:] and tail[-1] == c_lo
    return grid, tail_start, tail


def bare_digest(rows: list[dict]) -> str:
    return hashlib.sha256(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows).encode()
    ).hexdigest()


def first_failure(rungs: list[dict], side: str) -> int:
    indices = [index for index, rung in enumerate(rungs) if rung[side]["breakdown_reasons"]]
    assert indices, f"historical {side} walk has no health failure"
    index = indices[0]
    assert index > 0, f"historical {side} walk has no health-clean lower rung"
    return index


def reused_minus_endpoint(method: str, seed: int, require_missing_plus: bool = False) -> dict:
    certificate_path = ROOT / "outputs" / f"walk_{method}_s{seed}.json"
    certificate = json.loads(certificate_path.read_text())
    assert certificate["status"] == "COMPLETE"
    assert certificate["method"] == method and certificate["seed"] == seed
    failure_index = first_failure(certificate["rungs"], "-C")
    lo_rung = certificate["rungs"][failure_index - 1]
    hi_rung = certificate["rungs"][failure_index]
    assert lo_rung["coefficient"] < hi_rung["coefficient"]
    assert not lo_rung["-C"]["breakdown_reasons"]
    assert hi_rung["-C"]["breakdown_reasons"]
    source_dir = ROOT / lo_rung["run_dir"]
    source_artifact_path = source_dir / f"{method}.json"
    source_artifact = json.loads(source_artifact_path.read_text())
    assert source_artifact["method"] == method and source_artifact["seed"] == seed
    assert math.isclose(source_artifact["fixed_coefficient_magnitude"], lo_rung["coefficient"], rel_tol=1e-12)
    cohort, cohort_sha256 = walk.read_cohort(100)
    bare = [
        json.loads(line)
        for line in (source_dir / "moral_demos.jsonl").read_text().splitlines()
        if json.loads(line)["label"] == "bare"
    ]
    assert len(bare) == 100, f"missing canonical bare source: {source_dir}"
    assert [(row["scenario"], row["prompt"]) for row in bare] == [
        (row["scenario"], row["prompt"]) for row in cohort
    ]
    assert source_artifact["cohort_sha256"] == cohort_sha256
    if require_missing_plus:
        assert not any(rung["+C"]["breakdown_reasons"] for rung in certificate["rungs"]), (
            f"{method} seed {seed} already has a +C health failure; continuation is only for missing +C evidence"
        )
    config_keys = (
        "model", "dtype", "layers", "target_layer", "n_pairs_requested", "n_pairs",
        "batch_size", "max_length", "max_new_tokens", "cohort_sha256", "cohort_size",
        "persona", "axis", "demo_set", "eval_version", "extraction_sample_id",
    )
    config = {key: source_artifact[key] for key in config_keys}
    if "extract_batch_size" in source_artifact:
        config["extract_batch_size"] = source_artifact["extract_batch_size"]
        config["extract_batch_size_provenance"] = "source artifact"
    else:
        config["extract_batch_size"] = source_artifact["batch_size"]
        config["extract_batch_size_provenance"] = "scripts/walk.py@1add103: extraction used batch_size"
    return {
        "config": config,
        "bare": bare,
        "provenance": {
            "historical_certificate": str(certificate_path.relative_to(ROOT)),
            "historical_certificate_sha256": hashlib.sha256(certificate_path.read_bytes()).hexdigest(),
            "historical_shared_stop_plus_health_clean_C": certificate["rungs"][-1]["coefficient"],
            "reused_minus_health_clean_C_lo": lo_rung["coefficient"],
            "reused_minus_health_failing_C_hi": hi_rung["coefficient"],
            "reused_minus_health_clean_run": lo_rung["run_dir"],
            "reused_minus_health_failing_run": hi_rung["run_dir"],
            "bare_source": str((source_dir / "moral_demos.jsonl").relative_to(ROOT)),
            "bare_sha256": bare_digest(bare),
            "bare_source_artifact": str(source_artifact_path.relative_to(ROOT)),
            "bare_source_artifact_sha256": hashlib.sha256(source_artifact_path.read_bytes()).hexdigest(),
        },
    }


def continuation_certificate_path(args: argparse.Namespace) -> Path:
    side = args.side.replace("+", "plus").replace("-", "minus")
    return ROOT / "outputs" / f"continuation_{args.method}_s{args.seed}_{side}_{args.continuation_id}.json"


def artifact_matches(artifact: dict, args: argparse.Namespace, endpoint: dict, coefficient: float) -> bool:
    return (
        artifact.get("schema") == PROCEDURE
        and artifact.get("status") == "RESULT"
        and artifact.get("continuation_id") == args.continuation_id
        and artifact.get("method") == args.method
        and artifact.get("seed") == args.seed
        and artifact.get("generated_side") == args.side
        and math.isclose(artifact.get("fixed_coefficient_magnitude", -1), coefficient, rel_tol=1e-12)
        and artifact.get("canonical_bare", {}).get("sha256") == endpoint["provenance"]["bare_sha256"]
        and artifact.get("model") == endpoint["config"]["model"]
    )


def adopted_rung(args: argparse.Namespace, endpoint: dict, coefficient: float) -> tuple[Path, dict] | None:
    matches = []
    for artifact_path in (ROOT / "outputs").glob(f"run_*/{args.method}.json"):
        artifact = json.loads(artifact_path.read_text())
        if not artifact_matches(artifact, args, endpoint, coefficient):
            continue
        records = [json.loads(line) for line in (artifact_path.parent / "moral_demos.jsonl").read_text().splitlines()]
        bare = [row for row in records if row["label"] == "bare"]
        side = [row for row in records if row["steer_direction"] == args.side]
        assert len(records) == len(bare) + len(side) == 200
        assert bare_digest(bare) == endpoint["provenance"]["bare_sha256"]
        matches.append((artifact_path.parent, artifact))
    assert len(matches) <= 1, f"duplicate continuation rung: {args.method=} {args.seed=} {args.side=} {coefficient=}" 
    return matches[0] if matches else None


@dataclass
class RungContext:
    config: dict
    rows: list[dict]
    tokenizer: object
    model: object
    vector: object
    extraction_metadata: dict
    prompts: list[object]


def probe(args: argparse.Namespace, endpoint: dict, context: RungContext, coefficient: float, phase: str) -> dict:
    adopted = adopted_rung(args, endpoint, coefficient)
    if adopted is None:
        logger.info("run side={} phase={} C={} in-process", args.side, phase, coefficient)
        write_rung(args, endpoint, context, coefficient, phase)
        adopted = adopted_rung(args, endpoint, coefficient)
        assert adopted is not None
    run_dir, artifact = adopted
    stats = artifact["demo_stats"][args.side]
    margin = health_margin(stats)
    reasons = artifact["breakdown_reasons"][args.side]
    assert (margin > 0) == (not reasons), f"health predicate mismatch: {run_dir}"
    return {
        "coefficient": coefficient,
        "health_clean": margin > 0,
        "health_margin": margin,
        "breakdown_reasons": reasons,
        "run_dir": str(run_dir.relative_to(ROOT)),
    }


def search_boundary(args: argparse.Namespace, endpoint: dict, context: RungContext) -> dict:
    trace: list[dict] = []

    def observe(coefficient: float) -> dict:
        entry = probe(args, endpoint, context, coefficient, "search")
        trace.append(entry)
        assert_monotone_health(trace)
        return entry

    current = observe(endpoint["provenance"]["historical_shared_stop_plus_health_clean_C"])
    if current["health_clean"]:
        lo = current
        for _ in range(SEARCH_MAX_STEPS):
            hi = observe(lo["coefficient"] * 2)
            if not hi["health_clean"]:
                break
            lo = hi
        else:
            raise RuntimeError(f"right-censored health boundary: {args.side} remains health-clean through {lo['coefficient']}")
    else:
        hi = current
        for _ in range(SEARCH_MAX_STEPS):
            lo = observe(hi["coefficient"] / 2)
            if lo["health_clean"]:
                break
            hi = lo
        else:
            raise RuntimeError(f"baseline health failure: {args.side} fails through {hi['coefficient']}")
    assert lo["health_clean"] and not hi["health_clean"] and lo["coefficient"] < hi["coefficient"]

    f_lo, f_hi = lo["health_margin"], hi["health_margin"]
    for _ in range(SEARCH_MAX_STEPS):
        if math.log(hi["coefficient"] / lo["coefficient"]) <= SEARCH_LOG_TOLERANCE:
            break
        log_lo, log_hi = math.log(lo["coefficient"]), math.log(hi["coefficient"])
        log_candidate = (log_lo * f_hi - log_hi * f_lo) / (f_hi - f_lo)
        if not log_lo < log_candidate < log_hi:
            log_candidate = (log_lo + log_hi) / 2
        candidate = observe(math.exp(log_candidate))
        if candidate["health_clean"]:
            lo, f_lo = candidate, candidate["health_margin"]
            f_hi *= 0.5
        else:
            hi, f_hi = candidate, candidate["health_margin"]
            f_lo *= 0.5
    else:
        raise RuntimeError(f"Illinois health search exhausted its budget for {args.side}")
    assert lo["health_clean"] and not hi["health_clean"]
    return {"C_lo": lo["coefficient"], "C_hi": hi["coefficient"], "trace": trace}


def write_certificate(args: argparse.Namespace, endpoint: dict, boundary: dict, rungs: list[dict], status: str) -> None:
    grid, tail_start, tail = old_grid_tail(boundary["C_lo"])
    certificate = {
        "schema": PROCEDURE,
        "status": status,
        "continuation_id": args.continuation_id,
        "method": args.method,
        "seed": args.seed,
        "generated_side": args.side,
        "coefficient_units": "historical fixed_coefficient_magnitude",
        "health_rule": HEALTH_RULE,
        "search": {
            "C_lo": boundary["C_lo"],
            "C_hi": boundary["C_hi"],
            "trace": boundary["trace"],
        },
        "tail": {"grid": grid, "tail_start": tail_start, "members": tail},
        "rungs": rungs,
        "config": endpoint["config"],
        "provenance": endpoint["provenance"],
    }
    continuation_certificate_path(args).write_text(json.dumps(certificate, indent=2) + "\n")


def walk_side(args: argparse.Namespace) -> None:
    assert args.continuation_id and args.side == "+C"
    endpoint = reused_minus_endpoint(args.method, args.seed, require_missing_plus=True)
    context = load_rung_context(args, endpoint)
    boundary = search_boundary(args, endpoint, context)
    rungs = []
    _, _, tail = old_grid_tail(boundary["C_lo"])
    for tail_index, coefficient in enumerate(tail):
        entry = probe(args, endpoint, context, coefficient, "tail")
        assert entry["health_clean"], f"tail has a health failure: {args.side} {coefficient}"
        entry["tail_index"] = tail_index
        rungs.append(entry)
        write_certificate(args, endpoint, boundary, rungs, "RUNNING")
    write_certificate(args, endpoint, boundary, rungs, "COMPLETE")
    logger.info("CONTINUATION_COMPLETE method={} seed={} side={} certificate={}", args.method, args.seed, args.side, continuation_certificate_path(args))


def load_rung_context(args: argparse.Namespace, endpoint: dict) -> RungContext:
    config = endpoint["config"]
    rows, cohort_sha256 = walk.read_cohort(100)
    assert cohort_sha256 == config["cohort_sha256"] and config["cohort_size"] == len(rows)
    tokenizer = AutoTokenizer.from_pretrained(config["model"])
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(
        config["model"], dtype=getattr(torch, config["dtype"]), attn_implementation="sdpa"
    ).to(args.device).eval()
    layers = tuple(config["layers"])
    positive, negative = make_persona_pairs(
        tokenizer,
        n_pairs=config["n_pairs_requested"],
        thinking=True,
        persona_pairs=walk.PERSONAS,
        template=walk.PERSONA_TEMPLATE,
        seed=args.seed,
    )
    assert len(positive) == len(negative) == config["n_pairs"]
    sample_id = "persona:" + hashlib.sha256(
        json.dumps([positive, negative], separators=(",", ":")).encode()
    ).hexdigest()[:16]
    assert sample_id == config["extraction_sample_id"]
    extraction_args = SimpleNamespace(
        method=args.method,
        extract_batch_size=config["extract_batch_size"],
        batch_size=config["batch_size"],
        target_layer=config["target_layer"],
        lens_file=None,
        max_length=config["max_length"],
        dtype=config["dtype"],
        seed=args.seed,
    )
    vector, extraction_metadata = walk.extract_vector(extraction_args, model, tokenizer, layers, positive, negative)
    return RungContext(
        config=config,
        rows=rows,
        tokenizer=tokenizer,
        model=model,
        vector=vector,
        extraction_metadata=extraction_metadata,
        prompts=walk.generation_inputs(tokenizer, rows),
    )


def write_rung(
    args: argparse.Namespace,
    endpoint: dict,
    context: RungContext,
    coefficient: float,
    phase: str,
) -> None:
    stamp = time.strftime("%Y%m%dT%H%M%S")
    coefficient_slug = str(coefficient).replace(".", "p")
    output = args.output or ROOT / "outputs" / f"run_{stamp}_{args.method}_s{args.seed}_{args.side[0]}c{coefficient_slug}"
    output.mkdir(parents=True, exist_ok=False)
    logger.remove()
    logger.add(sys.stderr, format="{time:HH:mm:ss} | {message}")
    logger.add(output / "run.log", format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}")

    vector_file = output / f"{args.method}_vector.safetensors"
    context.vector.save(str(vector_file))
    signed_coefficient = coefficient if args.side == "+C" else -coefficient
    walk.assert_hook_changes_logits(context.model, context.tokenizer, context.vector, context.prompts[0], signed_coefficient)
    with context.vector(context.model, C=signed_coefficient):
        steered = walk.generate(
            context.model,
            context.tokenizer,
            context.prompts,
            context.config["batch_size"],
            context.config["max_new_tokens"],
        )
    assert any(answer != row["text"] for answer, row in zip(steered, endpoint["bare"], strict=True))

    demo_path = output / "moral_demos.jsonl"
    with demo_path.open("w") as file:
        for row in endpoint["bare"]:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
        for row, answer in zip(context.rows, steered, strict=True):
            file.write(json.dumps({
                "label": args.method,
                "point_id": f"{args.method}_s{args.seed}_c{coefficient:g}",
                "steer_direction": args.side,
                "coefficient": signed_coefficient,
                "scenario": row["scenario"],
                "prompt": row["prompt"],
                "text": answer,
            }, ensure_ascii=False) + "\n")
    stats, reasons = walk.health(context.tokenizer, steered)
    logger.info(
        "SHOULD: unfinished<50%, role_leaks<25%, repeated<25%. ELSE this side is beyond health failure. side={} stats={} breakdown={}",
        args.side, stats, reasons,
    )
    artifact = {
        "schema": PROCEDURE,
        "status": "RESULT",
        "continuation_id": args.continuation_id,
        "walk_phase": phase,
        "generated_side": args.side,
        "coefficient_units": "historical fixed_coefficient_magnitude",
        "method": args.method,
        "seed": args.seed,
        "fixed_coefficient_magnitude": coefficient,
        **context.config,
        "extraction_metadata": context.extraction_metadata,
        "vector_file": vector_file.name,
        "vector_sha256": hashlib.sha256(vector_file.read_bytes()).hexdigest(),
        "vector_content_sha256": walk.vector_hash(context.vector),
        "health_rule": HEALTH_RULE,
        "demo_stats": {args.side: stats},
        "breakdown_reasons": {args.side: reasons},
        "canonical_bare": {
            "source": endpoint["provenance"]["bare_source"],
            "sha256": endpoint["provenance"]["bare_sha256"],
        },
        "provenance": endpoint["provenance"],
    }
    (output / f"{args.method}.json").write_text(json.dumps(artifact, indent=2) + "\n")


def run_rung(args: argparse.Namespace) -> None:
    assert args.continuation_id and args.side and args.coefficient is not None and args.phase
    endpoint = reused_minus_endpoint(args.method, args.seed)
    context = load_rung_context(args, endpoint)
    write_rung(args, endpoint, context, args.coefficient, args.phase)


def self_test() -> None:
    grid, tail_start, tail = old_grid_tail(1.0)
    assert grid[-1] == 1.0
    assert tail == grid[tail_start:]
    assert tail_start == math.ceil(0.66 * len(grid))
    assert health_margin({"answers": 100, "unfinished": 49, "role_leaks": 24, "repeated": 24}) > 0
    assert health_margin({"answers": 100, "unfinished": 50, "role_leaks": 0, "repeated": 0}) == 0
    assert_monotone_health([
        {"coefficient": 0.5, "health_clean": True},
        {"coefficient": 1.0, "health_clean": True},
        {"coefficient": 2.0, "health_clean": False},
    ])
    assert first_failure([
        {"-C": {"breakdown_reasons": []}},
        {"-C": {"breakdown_reasons": ["repetition"]}},
    ], "-C") == 1
    for method, seeds in {
        "vjp_delta": (0, 1, 2),
        "mean_diff": (0, 1, 2),
        "pca": (0, 1, 2),
        "J_word": (0,),
        "vjp_mlp_up_shrink": (0, 1, 2),
    }.items():
        for seed in seeds:
            endpoint = reused_minus_endpoint(method, seed)
            assert len(endpoint["bare"]) == 100
            assert endpoint["provenance"]["reused_minus_health_clean_C_lo"] < endpoint["provenance"]["reused_minus_health_failing_C_hi"]
            assert endpoint["provenance"]["historical_shared_stop_plus_health_clean_C"] > 0
    try:
        assert_monotone_health([
            {"coefficient": 0.5, "health_clean": False},
            {"coefficient": 1.0, "health_clean": True},
        ])
    except AssertionError:
        pass
    else:
        raise AssertionError("nonmonotone health trace did not fail")
    print("WALK_SELF_TEST_PASS")


def main() -> None:
    args = parse_args()
    if args.self_test:
        self_test()
    else:
        assert args.method
        if args.walk:
            assert args.coefficient is None and args.phase is None
            walk_side(args)
        else:
            run_rung(args)


if __name__ == "__main__":
    main()
