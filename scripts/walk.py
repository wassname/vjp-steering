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

from vjp_steering import vjp_delta


ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "data/bullshit_bench_v2.jsonl"
PERSONAS = [("sycophantic", "abrasive")]
PERSONA_TEMPLATE = "Answer as someone who is {persona}."
ROLE_LEAK = re.compile(r"<\s*/?\s*think\s*>|^\s*(user|assistant|system)\s*$", re.I | re.M)
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
    parser.add_argument("method", choices=("vjp_delta", "mean_diff", "pca"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--coefficient", type=float)
    parser.add_argument("--walk", action="store_true")
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
    parser.add_argument("--target-layer", type=int)
    parser.add_argument("--status", choices=("RESULT", "SMOKE_PASS"), default="RESULT")
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


def adopted_rung(method: str, seed: int, coefficient: float, model: str) -> tuple[Path, dict] | None:
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


def walk(args: argparse.Namespace) -> None:
    assert args.limit == 100 and args.status == "RESULT"
    state = {side: {"streak": 0, "boundary": None} for side in ("+C", "-C")}
    entries = []
    certificate_path = ROOT / "outputs" / f"walk_{args.method}_s{args.seed}.json"
    for grid_index, coefficient in enumerate(GRID):
        adopted = adopted_rung(args.method, args.seed, coefficient, args.model)
        command = rung_command(args, coefficient)
        if adopted is None and args.dry_run:
            logger.info("DRY_RUN missing grid={} C={} command={}", grid_index, coefficient, shlex.join(command))
            return
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
            adopted = adopted_rung(args.method, args.seed, coefficient, args.model)
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
            entry[side] = {
                "breakdown_reasons": reasons,
                "post_boundary": state[side]["boundary"] is not None and grid_index > state[side]["boundary"],
            }
        entries.append(entry)
        certificate = {
            "schema": "dose_walk_v1",
            "status": "RUNNING",
            "method": args.method,
            "seed": args.seed,
            "model": args.model,
            "grid": "2^(n/6), n=-30..84",
            "state": state,
            "rungs": entries,
        }
        certificate_path.write_text(json.dumps(certificate, indent=2) + "\n")
        # stop on the first side to confirm a boundary (two consecutive breakdowns + 2 extra
        # rungs). vjp_delta's +C never degrades, so requiring both sides climbs to the ceiling.
        if any(state[side]["boundary"] is not None and grid_index >= state[side]["boundary"] + 2 for side in state):
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


def extract_vector(args, model, tokenizer, layers, positive, negative) -> Vector:
    batch_size = args.extract_batch_size or args.batch_size
    if args.method == "vjp_delta":
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
    vector.cfg.dtype = getattr(torch, args.dtype)
    return vector


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
    assert args.coefficient is not None
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
    vector = extract_vector(args, model, tokenizer, layers, positive, negative)
    extraction_seconds = time.monotonic() - started
    vector_file = output / f"{args.method}_vector.safetensors"
    vector.save(str(vector_file))
    vector_sha256 = hashlib.sha256(vector_file.read_bytes()).hexdigest()

    prompts = generation_inputs(tokenizer, rows)
    first_length = len(tokenizer(prompts[0], add_special_tokens=False)["input_ids"])
    assert first_length <= args.max_length
    logger.info(
        "SHOULD: this is the exact chat-formatted benchmark prompt with thinking disabled. "
        "ELSE generation scores are invalid.\n=== generation input 0 ===\n{}\n=== end input ===",
        prompts[0],
    )
    assert_hook_changes_logits(model, tokenizer, vector, prompts[0], args.coefficient)

    logger.info("stage=generate side=bare")
    bare = generate(model, tokenizer, prompts, args.batch_size, args.max_new_tokens)
    logger.info("stage=generate side=+C")
    with vector(model, C=args.coefficient):
        positive_answers = generate(model, tokenizer, prompts, args.batch_size, args.max_new_tokens)
    logger.info("stage=generate side=-C")
    with vector(model, C=-args.coefficient):
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

    artifact = {
        "schema": "fixed_c_pair_v1",
        "status": args.status,
        "method": args.method,
        "seed": args.seed,
        "fixed_coefficient_magnitude": args.coefficient,
        "model": args.model,
        "dtype": args.dtype,
        "layers": layers,
        "target_layer": vector.cfg.target_layer if args.method == "vjp_delta" else None,
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
        "vector_file": vector_file.name,
        "vector_sha256": vector_sha256,
        "vector_content_sha256": vector_hash(vector),
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
        assert args.coefficient is None
        walk(args)
    else:
        assert not args.dry_run
        run_rung(args)


if __name__ == "__main__":
    main()
