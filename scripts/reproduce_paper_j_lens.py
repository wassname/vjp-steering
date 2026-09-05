"""Paper-native J-lens verbal-report coordinate-swap reproduction."""

import argparse
import hashlib
import json
from contextlib import nullcontext
from pathlib import Path

import torch
from loguru import logger
from transformers import AutoModelForCausalLM, AutoTokenizer

from vjp_steering.vjp import j_lens_coordinate_prefill, j_lens_coordinate_swap


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data/vendor/jacobian-lens/verbal-report.json"
DEFAULT_OUTPUT = ROOT / "outputs/experiments/paper-native-verbal-report-v1/results.json"
WORKSPACE_LAYERS = tuple(range(13, 22))
PROMPT_TEMPLATE = "Think of a {category}. Answer in one word:"


def token_id(tokenizer, word: str, prefix: str) -> int | None:
    ids = tokenizer(prefix + word, add_special_tokens=False).input_ids
    return ids[0] if len(ids) == 1 else None


def rank(logits: torch.Tensor, token: int) -> int:
    return int((logits > logits[token]).sum().item()) + 1


def prompt(tokenizer, category: str, mode: str) -> str:
    text = PROMPT_TEMPLATE.format(category=category)
    if mode == "raw":
        return text
    if mode == "chat":
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": text}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    raise ValueError(f"unknown prompt mode {mode}")


def top_tokens(logits: torch.Tensor, tokenizer, k: int = 10) -> list[dict[str, float | int | str]]:
    values, ids = logits.topk(k)
    return [
        {"token_id": int(token), "token": tokenizer.decode([int(token)]), "logit": float(value)}
        for value, token in zip(values, ids, strict=True)
    ]


def next_logits(model, tokenizer, text: str, vector=None) -> tuple[torch.Tensor, dict[int, int]]:
    encoded = tokenizer(text, return_tensors="pt", add_special_tokens=False).to(next(model.parameters()).device)
    final = encoded.attention_mask.sum(1) - 1
    context = nullcontext({}) if vector is None else j_lens_coordinate_prefill(
        model, vector, encoded.attention_mask.bool()
    )
    with context as calls, torch.inference_mode():
        logits = model(**encoded, use_cache=False).logits[torch.arange(len(final), device=final.device), final][0].float()
    if vector is not None and not all(value == 1 for value in calls.values()):
        raise AssertionError(f"coordinate swap hook calls were {calls}")
    return logits.cpu(), calls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--lens-file", type=Path)
    parser.add_argument("--limit-categories", type=int)
    parser.add_argument("--limit-targets", type=int)
    parser.add_argument("--prompt-mode", choices=("raw", "chat"), default="raw")
    parser.add_argument("--clean-only", action="store_true")
    parser.add_argument("--coefficient", type=float, default=1.0)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()

    data = json.loads(args.data.read_text())
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=getattr(torch, args.dtype), attn_implementation="sdpa"
    ).cuda().eval()
    categories = list(data["candidates"].items())
    if args.limit_categories is not None:
        categories = categories[: args.limit_categories]
    trials = []
    clean_rows = []
    candidate_prefix = " " if args.prompt_mode == "raw" else ""
    for category, words in categories:
        text = prompt(tokenizer, category, args.prompt_mode)
        clean_logits, _ = next_logits(model, tokenizer, text)
        source_id = int(clean_logits.argmax())
        category_ids = [token_id(tokenizer, word, candidate_prefix) for word in words]
        category_ids = [word_id for word_id in category_ids if word_id is not None]
        clean_rows.append({
            "category": category,
            "prompt": text,
            "clean_token_id": source_id,
            "clean_token": tokenizer.decode([source_id]),
            "clean_is_listed_category_item": source_id in category_ids,
            "category_token_ids": category_ids,
            "top_tokens": top_tokens(clean_logits, tokenizer),
        })
        if args.clean_only:
            continue
        if source_id not in category_ids:
            logger.warning("category={} clean token is not a listed category item: {}", category, tokenizer.decode([source_id]))
            continue
        target_ids = [token_id(tokenizer, word, candidate_prefix) for word in words[:10]]
        target_ids = [target for target in target_ids if target is not None and target != source_id and rank(clean_logits, target) > 10]
        if args.limit_targets is not None:
            target_ids = target_ids[: args.limit_targets]
        logger.info("category={} clean={} source_id={} valid_targets={}", category, tokenizer.decode([source_id]), source_id, len(target_ids))
        for target_id in target_ids:
            vector, metadata = j_lens_coordinate_swap(
                model, WORKSPACE_LAYERS, source_token_id=source_id,
                target_token_id=target_id, lens_file=args.lens_file,
            )
            zero = vector
            zero.cfg.coeff = 0.0
            zero_logits, zero_calls = next_logits(model, tokenizer, text, zero)
            torch.testing.assert_close(zero_logits, clean_logits, rtol=0, atol=0)
            vector.cfg.coeff = args.coefficient
            swapped_logits, calls = next_logits(model, tokenizer, text, vector)
            trials.append({
                "category": category, "prompt": text, "source_token_id": source_id,
                "source_token": tokenizer.decode([source_id]), "target_token_id": target_id,
                "target_token": tokenizer.decode([target_id]), "clean_target_rank": rank(clean_logits, target_id),
                "swapped_target_rank": rank(swapped_logits, target_id),
                "clean_top_token": tokenizer.decode([int(clean_logits.argmax())]),
                "swapped_top_token": tokenizer.decode([int(swapped_logits.argmax())]),
                "success_top1": int(swapped_logits.argmax()) == target_id,
                "zero_hook_calls": zero_calls, "swap_hook_calls": calls,
                "layer_condition_numbers": {layer: info["condition_number"] for layer, info in metadata["layers"].items()},
            })
    common = {
        "model": args.model,
        "source_revision": args.source_revision,
        "data": str(args.data),
        "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "prompt_mode": args.prompt_mode,
        "candidate_prefix": candidate_prefix,
        "prompt_format":  "paper verbal-report colon prefill" if args.prompt_mode == "raw" else "Qwen chat template around the paper verbal-report colon prefill",
        "clean_rows": clean_rows,
    }
    if args.clean_only:
        summary = {
            **common,
            "n_categories": len(clean_rows),
            "n_semantic_clean_answers": sum(row["clean_is_listed_category_item"] for row in clean_rows),
        }
    else:
        if not trials:
            raise ValueError("no clean source token was a listed category item with a valid one-token target outside the clean top 10")
        summary = {
            **common,
            "operator": "h + V(swap(V^dagger h) - V^dagger h)",
            "coefficient": args.coefficient,
            "layers":  list(WORKSPACE_LAYERS), "n_trials": len(trials),
            "n_top1": sum(trial["success_top1"] for trial in trials),
            "top1_rate": sum(trial["success_top1"] for trial in trials) / len(trials),
            "median_clean_target_rank": float(torch.tensor([trial["clean_target_rank"] for trial in trials]).median()),
            "median_swapped_target_rank": float(torch.tensor([trial["swapped_target_rank"] for trial in trials]).median()),
            "trials": trials,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print("PAPER_NATIVE_J_LENS_VERBAL_REPORT_COMPLETE", json.dumps({
        key: summary[key] for key in summary if key not in {"trials", "clean_rows"}
    }))


if __name__ == "__main__":
    main()
