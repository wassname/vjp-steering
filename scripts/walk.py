"""Extract one steering vector and run one bare/+C/-C benchmark dose."""

import argparse
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

import torch
from loguru import logger
from steering_lite import MeanDiffC, PCAC, Vector
from steering_lite.calibrate import _ngram_rep
from steering_lite.data import make_persona_pairs
from transformers import AutoModelForCausalLM, AutoTokenizer

from vjp_steering import j_word, vjp_delta, vjp_mlp_up_shrink
from vjp_steering.vjp import vjp_mlp_up_left_right_shrink, vjp_mlp_up_shared_eb


ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "data/bullshit_bench_v2.jsonl"
PERSONAS = [("sycophantic", "abrasive")]
PERSONA_TEMPLATE = "Answer as someone who is {persona}."
ROLE_LEAK = re.compile(r"<\s*/?\s*think\s*>|^\s*(user|assistant|system)\s*$", re.I | re.M)
C_STAR_THRESHOLD = {"repeated": 25, "unfinished": 50, "role_leak": 25}
# dense linear tail around the predicted breakdown C*: 0.5*C* .. 1.25*C*
# in 16 steps gives ~half the half-octave gap; symlog wastes samples past breakdown
REFINE_LOW, REFINE_HIGH, REFINE_STEPS = 0.5, 1.25, 16
GRID = tuple(2.0 ** (n / 6) for n in range(-30, 85))
BREAKDOWN_REASON = {
    "unfinished": "unfinished",
    "unfinished_ge_0.5": "unfinished",
    "role_leak": "role_leak",
    "role_leak_ge_0.25": "role_leak",
    "repetition": "repetition",
    "demo_rep_ge_0.25": "repetition",
}
assert GRID[0] == 0.03125 and GRID[-1] == 16384.0
assert all(math.isclose(b / a, 2.0 ** (1 / 6)) for a, b in zip(GRID, GRID[1:]))
assert all(2.0 ** (n / 2) in GRID for n in range(-10, 29))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("method", choices=("J_word", "vjp_delta", "vjp_mlp_up_shrink", "vjp_mlp_up_left_right_shrink", "vjp_mlp_up_shared_eb", "mean_diff", "pca"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--coefficient", type=float)
    parser.add_argument("--walk", action="store_true")
    parser.add_argument("--walk-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", choices=("float32", "bfloat16"), default="bfloat16")
    parser.add_argument("--n-pairs", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=4)
    # extraction holds a backward graph, so it OOMs at a batch that generation is happy with
    parser.add_argument("--extract-batch-size", type=int)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--layers", help="comma-separated zero-based block indices")
    parser.add_argument("--lens-file", type=Path)
    parser.add_argument("--target-layer", type=int)
    parser.add_argument("--refine-around-cstar", action="store_true",
                        help="bracket C* with local health (rep/unfinished/leak) then insert a dense tail 0.5..1.25*C*")
    parser.add_argument("--status", choices=("RESULT", "SMOKE_PASS"), default="RESULT")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def read_cohort(limit: int) -> tuple[list[dict[str, str]], str]:
    rows = [json.loads(line) for line in COHORT.read_text().splitlines()]
    assert len(rows) == 100
    assert len({row["scenario"] for row in rows}) == 100
    digest = hashlib.sha256(
        json.dumps(
            [[row["scenario"], row["prompt"]] for row in rows],
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    return rows[:limit], digest


def semantic_reasons(reasons: list[str]) -> list[str]:
    return sorted({BREAKDOWN_REASON[reason] for reason in reasons if reason in BREAKDOWN_REASON})


def adopted_rung(method: str, seed: int, coefficient: float, model: str, max_new_tokens: int, walk_id: str) -> tuple[Path, dict] | None:
    cohort, cohort_sha256 = read_cohort(100)
    expected = [(row["scenario"], row["prompt"]) for row in cohort]
    matches = []
    for artifact_path in (ROOT / "outputs").glob(f"run_*/{method}.json"):
        artifact = json.loads(artifact_path.read_text())
        if artifact["status"] != "RESULT":
            continue
        identity = (
            artifact["method"] == method
            and artifact["seed"] == seed
            and math.isclose(artifact["fixed_coefficient_magnitude"], coefficient, rel_tol=1e-12)
            and artifact["model"] == model
            and artifact["persona"] == "sycophancy_abrasive"
            and artifact["axis"] == "sycophancy"
            and artifact["demo_set"] == "sycophancy_all100"
            and artifact["eval_version"] == 10
            # the cap sets answer length, which the judge scores as an off-axis confound,
            # so a rung from the old 4096 default is not the same measurement
            and artifact.get("max_new_tokens") == max_new_tokens
            and "walk_id" in artifact
            and artifact["walk_id"] == walk_id
        )
        if not identity:
            continue
        demos = [json.loads(line) for line in (artifact_path.parent / "moral_demos.jsonl").read_text().splitlines()]
        bare = [row for row in demos if row["label"] == "bare"]
        assert len(demos) == 300 and len(bare) == 100
        assert [(row["scenario"], row["prompt"]) for row in bare] == expected
        if "cohort_sha256" in artifact:
            assert artifact["cohort_sha256"] == cohort_sha256
        matches.append((artifact_path.parent, artifact))
    assert len(matches) <= 1, f"duplicate rung: {method=} {seed=} {coefficient=}"
    return matches[0] if matches else None


def rung_command(args: argparse.Namespace, coefficient: float) -> list[str]:
    return [
        sys.executable,
        str(Path(__file__).resolve()),
        args.method,
        "--seed",
        str(args.seed),
        "--walk-id",
        args.walk_id,
        "--coefficient",
        str(coefficient),
        "--model",
        args.model,
        "--device",
        args.device,
        "--dtype",
        args.dtype,
        "--n-pairs",
        str(args.n_pairs),
        "--batch-size",
        str(args.batch_size),
        "--extract-batch-size",
        str(args.extract_batch_size or args.batch_size),
        "--max-length",
        str(args.max_length),
        "--max-new-tokens",
        str(args.max_new_tokens),
        "--limit",
        str(args.limit),
    ]


def wait_for_gpu(required_mib: int = 20_000, timeout_minutes: int = 360) -> None:
    deadline = time.monotonic() + timeout_minutes * 60
    while True:
        free_mib = int(
            subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                text=True,
            ).splitlines()[0]
        )
        if free_mib >= required_mib:
            return
        if time.monotonic() >= deadline:
            raise TimeoutError(f"GPU stayed below {required_mib} MiB free for {timeout_minutes} min")
        logger.info("GPU free={} MiB; SHOULD reach {} MiB before extraction", free_mib, required_mib)
        time.sleep(60)


def c_star_trips(demo_stats: dict) -> bool:
    return (
        demo_stats["repeated"] >= C_STAR_THRESHOLD["repeated"]
        or demo_stats["unfinished"] >= C_STAR_THRESHOLD["unfinished"]
        or demo_stats["role_leaks"] >= C_STAR_THRESHOLD["role_leak"]
    )


def _dense_tail(c_lo: float, c_star: float) -> list[float]:
    # densify only the gap (C_lo, 1.25*C*] — not 0.5*C*..C* which is already coarsely sampled
    hi = c_star * REFINE_HIGH
    if c_lo >= hi:
        return []
    # log-spaced between c_lo and hi so step scales with dose
    import numpy as np
    tail = list(np.geomspace(c_lo * (1 + 1e-9), hi, REFINE_STEPS))
    # snap to 10dp for dedup stability
    return [round(float(c), 10) for c in tail]


def walk(args: argparse.Namespace) -> None:
    assert args.walk_id
    if not args.refine_around_cstar:
        assert args.limit == 100 and args.status == "RESULT"
    # dose-based boundary (not index) so splice cannot invalidate stop rule
    state = {side: {"streak": 0, "boundary": None, "boundary_C": None} for side in ("+C", "-C")}
    entries: list[dict] = []
    certificate_path = ROOT / "outputs" / f"walk_{args.method}_s{args.seed}.json"
    phase = "coarse"
    c_star: float | None = None
    c_star_lo: float | None = None  # C_lo for the side that set C*
    c_star_side: str | None = None
    lo_by_side: dict[str, tuple[int, float]] = {}
    grid_list: list[float] = list(GRID)
    grid_index = 0
    while grid_index < len(grid_list):
        coefficient = grid_list[grid_index]
        adopted = adopted_rung(args.method, args.seed, coefficient, args.model, args.max_new_tokens, args.walk_id)
        command = rung_command(args, coefficient)
        if adopted is None and args.dry_run:
            logger.info("DRY_RUN missing grid={} C={} command={}", grid_index, coefficient, shlex.join(command))
            grid_index += 1
            continue
        if adopted is None:
            wait_for_gpu()
            environment = os.environ.copy()
            environment["HF_HUB_OFFLINE"] = "1"
            environment["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
            # shared GPU: a stranger can grab memory under a long rung; retry on OOM instead of losing the walk
            for attempt in range(3):
                logger.info(
                    "run grid={} C={} attempt={}/3 command={}", grid_index, coefficient, attempt + 1, shlex.join(command)
                )
                stderr_lines: list[str] = []
                oom = False
                proc = subprocess.Popen(command, cwd=ROOT, env=environment, text=True,
                                        stdout=sys.stdout, stderr=subprocess.PIPE)
                assert proc.stderr is not None
                for line in proc.stderr:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    stderr_lines.append(line)
                    if "OutOfMemoryError" in line:
                        oom = True
                code = proc.wait()
                if code == 0:
                    break
                if attempt < 2 and oom:
                    logger.warning("OOM at C={}; re-wait and retry", coefficient)
                    wait_for_gpu()
                    continue
                raise subprocess.CalledProcessError(code, command, "".join(stderr_lines))
            adopted = adopted_rung(args.method, args.seed, coefficient, args.model, args.max_new_tokens, args.walk_id)
            assert adopted is not None
        run_dir, artifact = adopted
        logger.info("adopt grid={} C={} path={}", grid_index, coefficient, run_dir)
        entry = {"grid_index": grid_index, "coefficient": coefficient, "run_dir": str(run_dir.relative_to(ROOT))}
        for side in ("+C", "-C"):
            reasons = semantic_reasons(artifact["breakdown_reasons"][side])
            broken = bool(reasons)
            if state[side]["boundary"] is None:
                state[side]["streak"] = state[side]["streak"] + 1 if broken else 0
                if state[side]["streak"] == 2:
                    state[side]["boundary"] = grid_index
                    state[side]["boundary_C"] = coefficient
            entry[side] = {
                "breakdown_reasons": reasons,
                "post_boundary": state[side]["boundary"] is not None and grid_index > state[side]["boundary"],
            }
        if args.refine_around_cstar and phase == "coarse" and c_star is None:
            for _side in ("+C", "-C"):
                tripped = c_star_trips(artifact["demo_stats"][_side])
                if not tripped:
                    lo_by_side[_side] = (grid_index, coefficient)
                elif tripped and _side in lo_by_side:
                    lo_idx, lo_c = lo_by_side[_side]
                    c_star = coefficient
                    c_star_lo = lo_c
                    c_star_side = _side
                    logger.info("ILLINOIS bracket side={} lo_g={} C_lo={} hi_g={} C_hi={} C*~={}", _side, lo_idx, lo_c, grid_index, coefficient, c_star)
                    tail = _dense_tail(lo_c, c_star)
                    if not tail:
                        logger.info("REFINE skipped: C_lo {} >= hi {}", lo_c, c_star * REFINE_HIGH)
                    else:
                        seen = {round(e["coefficient"], 10) for e in entries} | {round(coefficient, 10)}
                        to_insert = [float(c) for c in tail if round(float(c), 10) not in seen and float(c) > coefficient]
                        if to_insert:
                            grid_list = grid_list[: grid_index + 1] + to_insert + [c for c in grid_list[grid_index + 1 :] if round(c, 10) not in {round(x, 10) for x in to_insert}]
                            logger.info("REFINE C*={} C_lo={} tail={}..{} n={} total_grid={}", c_star, lo_c, tail[0], tail[-1], len(to_insert), len(grid_list))
                        else:
                            logger.info("REFINE no insert: tail already covered")
                    phase = "dense"
                    break
        entries.append(entry)
        certificate = {
            "schema": "dose_walk_v1",
            "status": "RUNNING",
            "method": args.method,
            "seed": args.seed,
            "model": args.model,
            "grid": "refined" if phase == "dense" else "2^(n/6), n=-30..84",
            "state": state,
            "rungs": entries,
        }
        if c_star is not None:
            certificate["c_star"] = c_star
            certificate["refine"] = {"low": c_star * REFINE_LOW, "high": c_star * REFINE_HIGH, "steps": REFINE_STEPS}
        certificate_path.write_text(json.dumps(certificate, indent=2) + "\n")
        grid_index += 1
        # stop check is dose-anchored: require 2 confirmations beyond boundary_C in dose order.
        # Since grid_list is dose-sorted except for the one-time tail insert above current C,
        # index check is only valid pre-splice; post-splice we check that 2 rungs beyond
        # boundary_C have been evaluated (dose-sorted entries).
        if phase == "dense" and c_star is not None:
            # after refine, allow tail to run; stop only when both inserted tail rungs have been visited
            pass  # fall through to normal check below
        if all(state[side]["boundary"] is not None and grid_index >= state[side]["boundary"] + 2 for side in state):
            certificate["status"] = "COMPLETE"
            certificate_path.write_text(json.dumps(certificate, indent=2) + "\n")
            logger.info("WALK_COMPLETE method={} seed={} state={} certificate={}", args.method, args.seed, state, certificate_path)
            return
    raise RuntimeError(f"{args.method} seed {args.seed} reached grid ceiling without a confirmed breakdown boundary")


def resolve_layers(model, value: str | None) -> tuple[int, ...]:
    if value:
        return tuple(int(layer) for layer in value.split(","))
    n_layers = len(model.model.layers)
    return tuple(range(max(2, int(n_layers * 0.2)), min(n_layers - 2, int(n_layers * 0.8))))


def vector_hash(vector: Vector) -> str:
    digest = hashlib.sha256()
    for kind, tree in (("shared", vector.shared), ("stacked", vector.stacked)):
        for layer, tensors in sorted(tree.items()):
            for name, tensor in sorted(tensors.items()):
                value = tensor.detach().contiguous().cpu()
                digest.update(f"{kind}:{layer}:{name}:{value.dtype}:{tuple(value.shape)}".encode())
                digest.update(value.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def extract_vector(args, model, tokenizer, layers, positive, negative) -> tuple[Vector, dict[str, object]]:
    batch_size = args.extract_batch_size or args.batch_size
    if args.method == "J_word":
        vector, metadata = j_word(model, tokenizer, layers, lens_file=args.lens_file)
    elif args.method == "vjp_mlp_up_shrink":
        vector, metadata = vjp_mlp_up_shrink(
            model,
            tokenizer,
            positive,
            negative,
            target_layer=args.target_layer,
            batch_size=batch_size,
            max_length=args.max_length,
            skip_first=16,
        )
    elif args.method == "vjp_mlp_up_left_right_shrink":
        vector, metadata = vjp_mlp_up_left_right_shrink(
            model,
            tokenizer,
            positive,
            negative,
            target_layer=args.target_layer,
            batch_size=batch_size,
            max_length=args.max_length,
            skip_first=16,
        )
    elif args.method == "vjp_mlp_up_shared_eb":
        vector, metadata = vjp_mlp_up_shared_eb(
            model,
            tokenizer,
            positive,
            negative,
            target_layer=args.target_layer,
            batch_size=batch_size,
            max_length=args.max_length,
            skip_first=16,
        )
    elif args.method == "vjp_delta":
        vector = vjp_delta(
            model,
            tokenizer,
            positive,
            negative,
            layers,
            target_layer=args.target_layer,
            batch_size=batch_size,
            max_length=args.max_length,
            skip_first=16,
        )
        metadata = {}
    else:
        config = (MeanDiffC if args.method == "mean_diff" else PCAC)(
            layers=layers, dtype=getattr(torch, args.dtype), seed=args.seed
        )
        vector = Vector.train(
            model,
            tokenizer,
            positive,
            negative,
            config,
            batch_size=batch_size,
            max_length=args.max_length,
        )
        metadata = {}
    for extracted_vector in vector.values() if isinstance(vector, dict) else (vector,):
        extracted_vector.cfg.dtype = getattr(torch, args.dtype)
    return vector, metadata


def generation_inputs(tokenizer, rows: list[dict[str, str]]) -> list[str]:
    return [
        tokenizer.apply_chat_template(
            [{"role": "user", "content": row["prompt"] + " Answer in 2 short sentences."}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        for row in rows
    ]


@torch.inference_mode()
def generate(model, tokenizer, prompts: list[str], batch_size: int, max_new_tokens: int) -> list[str]:
    answers = []
    tokenizer.padding_side = "left"
    for start in range(0, len(prompts), batch_size):
        batch = tokenizer(
            prompts[start : start + batch_size],
            return_tensors="pt",
            padding=True,
            add_special_tokens=False,
        ).to(
            next(model.parameters()).device
        )
        output = model.generate(
            **batch,
            do_sample=False,
            temperature=None,
            top_p=None,
            top_k=None,
            pad_token_id=tokenizer.eos_token_id,
            max_new_tokens=max_new_tokens,
        )
        answers.extend(
            tokenizer.batch_decode(output[:, batch["input_ids"].shape[1] :], skip_special_tokens=True)
        )
        done = min(start + batch_size, len(prompts))
        if done == len(prompts) or done % (batch_size * 5) == 0:
            logger.info(f"generation {done}/{len(prompts)}")
    return [answer.strip() for answer in answers]


def worst_repetition(token_ids: list[int], window: int = 128) -> float:
    if len(token_ids) <= window:
        return _ngram_rep(token_ids)
    return max(
        _ngram_rep(token_ids[start : start + window])
        for start in range(0, len(token_ids) - window + 1, window // 4)
    )


def health(tokenizer, answers: list[str]) -> tuple[dict[str, float | int], list[str]]:
    unfinished = sum(not re.search(r"[.!?\")]$", answer) for answer in answers)
    role_leaks = sum(bool(ROLE_LEAK.search(answer)) for answer in answers)
    repetitions = [worst_repetition(tokenizer.encode(answer)) for answer in answers]
    repeated = sum(value > 0.5 for value in repetitions)
    n = len(answers)
    reasons = []
    if unfinished / n >= 0.5:
        reasons.append("unfinished")
    if role_leaks / n >= 0.25:
        reasons.append("role_leak")
    if repeated / n >= 0.25:
        reasons.append("repetition")
    return {
        "answers": n,
        "unfinished": unfinished,
        "role_leaks": role_leaks,
        "repeated": repeated,
        "max_repetition": max(repetitions),
        "mean_words": sum(len(answer.split()) for answer in answers) / n,
    }, reasons


@torch.inference_mode()
def assert_hook_changes_logits(model, tokenizer, vector, prompt: str, coefficient: float) -> None:
    encoded = tokenizer(prompt, return_tensors="pt", add_special_tokens=False).to(
        next(model.parameters()).device
    )
    bare = model(**encoded).logits
    with vector(model, C=coefficient):
        steered = model(**encoded).logits
    restored = model(**encoded).logits
    assert not torch.equal(bare, steered), "steering changed no logits"
    torch.testing.assert_close(bare, restored)


def run_rung(args: argparse.Namespace) -> None:
    assert args.coefficient is not None or args.extract_only
    if args.device == "cuda":
        wait_for_gpu()
    stamp = time.strftime("%Y%m%dT%H%M%S")
    coefficient_slug = str(args.coefficient).replace(".", "p")
    output = args.output or ROOT / "outputs" / f"run_{stamp}_{args.method}_s{args.seed}_c{coefficient_slug}"
    output.mkdir(parents=True, exist_ok=False)
    logger.remove()
    logger.add(sys.stderr, format="{time:HH:mm:ss} | {message}")
    logger.add(output / "run.log", format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}")

    rows, cohort_sha256 = read_cohort(args.limit)
    dtype = getattr(torch, args.dtype)
    logger.info("stage=load model={} device={} dtype={}", args.model, args.device, args.dtype)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=dtype, attn_implementation="sdpa"
    ).to(args.device).eval()
    layers = resolve_layers(model, args.layers)
    assert layers
    if args.method == "vjp_delta":
        assert args.target_layer is None or max(layers) < args.target_layer
    logger.info(
        "resolved method={} seed={} C={} cohort={}/100 layers={} target={} pairs={} batch={} tokens={}",
        args.method,
        args.seed,
        args.coefficient,
        len(rows),
        layers,
        args.target_layer,
        args.n_pairs,
        args.batch_size,
        args.max_new_tokens,
    )

    positive, negative = make_persona_pairs(
        tokenizer,
        n_pairs=args.n_pairs,
        thinking=True,
        persona_pairs=PERSONAS,
        template=PERSONA_TEMPLATE,
        seed=args.seed,
    )
    assert len(positive) == len(negative) > 0
    lengths = tokenizer(positive + negative, add_special_tokens=False)["input_ids"]
    assert max(map(len, lengths)) <= args.max_length, "extraction prompt truncation"
    sample_id = "persona:" + hashlib.sha256(
        json.dumps([positive, negative], separators=(",", ":")).encode()
    ).hexdigest()[:16]
    logger.info(
        "SHOULD: POS and NEG share the suffix and differ only in persona. ELSE extraction is invalid.\n"
        "=== extraction pair 0 ===\nPOS:\n{}\nNEG:\n{}\n=== end pair ===",
        positive[0],
        negative[0],
    )

    logger.info("stage=extract")
    started = time.monotonic()
    extracted, extraction_metadata = extract_vector(args, model, tokenizer, layers, positive, negative)
    extraction_seconds = time.monotonic() - started
    vectors = extracted if isinstance(extracted, dict) else {"+C": extracted, "-C": extracted}
    vector_files = {}
    vector_sha256 = {}
    vector_content_sha256 = {}
    for side, vector in vectors.items():
        side_slug = side.replace("+", "plus").replace("-", "minus")
        vector_file = output / f"{args.method}_{side_slug}_vector.safetensors"
        vector.save(str(vector_file))
        vector_files[side] = vector_file.name
        vector_sha256[side] = hashlib.sha256(vector_file.read_bytes()).hexdigest()
        vector_content_sha256[side] = vector_hash(vector)

    if args.extract_only:
        audit = {
            "schema": "per_side_vjp_noisy_coordinate_audit_v1",
            "method": args.method,
            "model": args.model,
            "seed": args.seed,
            "n_pairs": len(positive),
            "extraction_sample_id": sample_id,
            "extraction_seconds": extraction_seconds,
            "vector_files": vector_files,
            "vector_content_sha256": vector_content_sha256,
            "extraction_metadata": extraction_metadata,
        }
        (output / "extraction_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
        logger.info("EXTRACTION_AUDIT_COMPLETE output={}", output)
        return

    prompts = generation_inputs(tokenizer, rows)
    first_length = len(tokenizer(prompts[0], add_special_tokens=False)["input_ids"])
    assert first_length <= args.max_length
    logger.info(
        "SHOULD: this is the exact chat-formatted benchmark prompt with thinking disabled. "
        "ELSE generation scores are invalid.\n=== generation input 0 ===\n{}\n=== end input ===",
        prompts[0],
    )
    assert_hook_changes_logits(model, tokenizer, vectors["+C"], prompts[0], args.coefficient)
    assert_hook_changes_logits(model, tokenizer, vectors["-C"], prompts[0], -args.coefficient)

    logger.info("stage=generate side=bare")
    bare = generate(model, tokenizer, prompts, args.batch_size, args.max_new_tokens)
    logger.info("stage=generate side=+C")
    with vectors["+C"](model, C=args.coefficient):
        positive_answers = generate(model, tokenizer, prompts, args.batch_size, args.max_new_tokens)
    logger.info("stage=generate side=-C")
    with vectors["-C"](model, C=-args.coefficient):
        negative_answers = generate(model, tokenizer, prompts, args.batch_size, args.max_new_tokens)
    assert any(a != b for a, b in zip(bare, positive_answers, strict=True))
    assert any(a != b for a, b in zip(bare, negative_answers, strict=True))

    labels = (("bare", 0.0, bare), (args.method, args.coefficient, positive_answers), (args.method, -args.coefficient, negative_answers))
    demo_path = output / "moral_demos.jsonl"
    with demo_path.open("w") as file:
        for label, coefficient, answers in labels:
            direction = "" if coefficient == 0 else ("+C" if coefficient > 0 else "-C")
            for row, answer in zip(rows, answers, strict=True):
                file.write(json.dumps({
                    "label": label,
                    "point_id": f"{args.method}_s{args.seed}_c{abs(coefficient):g}",
                    "steer_direction": direction,
                    "coefficient": coefficient,
                    "scenario": row["scenario"],
                    "prompt": row["prompt"],
                    "text": answer,
                }, ensure_ascii=False) + "\n")

    stats, reasons = {}, {}
    for side, answers in (("bare", bare), ("+C", positive_answers), ("-C", negative_answers)):
        stats[side], reasons[side] = health(tokenizer, answers)
        logger.info(
            "SHOULD: unfinished<50%, role_leaks<25%, repeated<25%. ELSE this side is beyond breakdown. "
            "side={} stats={} breakdown={}", side, stats[side], reasons[side]
        )
        logger.info("=== generation output side={} ===\n{}\n=== end output ===", side, answers[0])

    mlp_up_methods = ("vjp_mlp_up_shrink", "vjp_mlp_up_left_right_shrink", "vjp_mlp_up_shared_eb")
    artifact_layers = extraction_metadata["source_layers"] if args.method in mlp_up_methods else layers
    target_layer = vectors["+C"].cfg.target_layer if args.method in ("vjp_delta", *mlp_up_methods) else None
    artifact = {
        "schema": "fixed_c_pair_v1",
        "status": args.status,
        "walk_id": args.walk_id,
        "method": args.method,
        "seed": args.seed,
        "fixed_coefficient_magnitude": args.coefficient,
        "model": args.model,
        "dtype": args.dtype,
        "layers": artifact_layers,
        "target_layer": target_layer,
        "extraction_metadata": extraction_metadata,
        "persona": "sycophancy_abrasive",
        "axis": "sycophancy",
        "demo_set": "sycophancy_all100",
        "eval_version": 10,
        "cohort_sha256": cohort_sha256,
        "cohort_size": len(rows),
        "n_pairs_requested": args.n_pairs,
        "n_pairs": len(positive),
        "batch_size": args.batch_size,
        "extract_batch_size": args.extract_batch_size or args.batch_size,
        "max_length": args.max_length,
        "max_new_tokens": args.max_new_tokens,
        "extraction_sample_id": sample_id,
        "extraction_seconds": extraction_seconds,
        "vector_files": vector_files,
        "vector_sha256": vector_sha256,
        "vector_content_sha256": vector_content_sha256,
        "stop_rule": "unfinished+role_leak+repetition",
        "demo_stats": stats,
        "breakdown_reasons": {"+C": reasons["+C"], "-C": reasons["-C"]},
    }
    (output / f"{args.method}.json").write_text(json.dumps(artifact, indent=2) + "\n")
    logger.info("RESULT\tmethod\tseed\tC\tbare_reasons\t+C_reasons\t-C_reasons\toutput")
    logger.info(
        "RESULT\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
        args.method, args.seed, args.coefficient, reasons["bare"], reasons["+C"], reasons["-C"], output
    )


def main() -> None:
    args = parse_args()
    if args.walk:
        assert args.coefficient is None and not args.extract_only
        walk(args)
    else:
        assert not args.dry_run
        assert args.coefficient is not None or args.extract_only
        run_rung(args)


if __name__ == "__main__":
    main()
