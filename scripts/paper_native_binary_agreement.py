"""Paper-native No→Yes coordinate swaps on false-claim agreement prompts."""

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from reproduce_paper_j_lens import WORKSPACE_LAYERS, next_logits, token_id
from vjp_steering.vjp import j_lens_coordinate_swap


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data/dev/paper_native_false_claim_agreement.json"


def prompt(tokenizer, claim: str) -> str:
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": claim}], tokenize=False,
        add_generation_prompt=True, enable_thinking=False,
    )


def rank(logits: torch.Tensor, token_id: int) -> int:
    return int((logits > logits[token_id]).sum()) + 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--dtype", default="bfloat16")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--coefficient", type=float, default=2.0)
    args = parser.parse_args()

    claims = json.loads(args.data.read_text())
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=getattr(torch, args.dtype), attn_implementation="sdpa"
    ).cuda().eval()
    no_id, yes_id = token_id(tokenizer, "No", ""), token_id(tokenizer, "Yes", "")
    if no_id is None or yes_id is None:
        raise ValueError("Yes/No must each tokenize to one no-space assistant token")
    trials = []
    for claim in claims:
        text = prompt(tokenizer, claim)
        clean, _ = next_logits(model, tokenizer, text)
        if int(clean.argmax()) != no_id:
            continue
        vector, metadata = j_lens_coordinate_swap(
            model, WORKSPACE_LAYERS, source_token_id=no_id, target_token_id=yes_id,
        )
        vector.cfg.coeff = 0.0
        zero, zero_calls = next_logits(model, tokenizer, text, vector)
        torch.testing.assert_close(zero, clean, rtol=0, atol=0)
        vector.cfg.coeff = args.coefficient
        swapped, calls = next_logits(model, tokenizer, text, vector)
        trials.append({
            "claim": claim, "clean_top": tokenizer.decode([int(clean.argmax())]),
            "swapped_top": tokenizer.decode([int(swapped.argmax())]),
            "clean_yes_rank": rank(clean, yes_id), "swapped_yes_rank": rank(swapped, yes_id),
            "yes_top1": int(swapped.argmax()) == yes_id,
            "zero_hook_calls": zero_calls, "swap_hook_calls": calls,
            "layer_condition_numbers": {layer: row["condition_number"] for layer, row in metadata["layers"].items()},
        })
    if not trials:
        raise ValueError("no false-claim prompt had clean No as its top token")
    output = {
        "source_revision": args.source_revision, "model": args.model, "coefficient": args.coefficient,
        "operator": "h + V(swap(V^dagger h) - V^dagger h)", "layers": list(WORKSPACE_LAYERS),
        "n_claims": len(claims), "n_eligible": len(trials),
        "n_yes_top1": sum(row["yes_top1"] for row in trials), "trials": trials,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print("PAPER_NATIVE_BINARY_AGREEMENT_COMPLETE", json.dumps({k: v for k, v in output.items() if k != "trials"}))


if __name__ == "__main__":
    main()
