"""Paper-native J-lens verbal-report coordinate-swap reproduction."""

import argparse
import hashlib
import json
from contextlib import nullcontext
from pathlib import Path

import torch
from loguru import logger
from transformers import AutoModelForCausalLM, AutoTokenizer

from vjp_steering.lens_readout import qwen_rmsnorm
from vjp_steering.vjp import J_WORD_LENS_FILE, J_WORD_LENS_REPO, J_WORD_LENS_REVISION, j_lens_coordinate_prefill, j_lens_coordinate_swap


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "data/vendor/jacobian-lens/verbal-report.json"
DEFAULT_OUTPUT = ROOT / "outputs/experiments/paper-native-verbal-report-v1/results.json"
WORKSPACE_LAYERS = tuple(range(13, 22))
PROMPT_TEMPLATE = "Think of a {category}. Answer in one word:"


def parse_layers(value: str) -> tuple[int, ...]:
    layers = tuple(int(layer) for layer in value.split(","))
    if not layers or len(set(layers)) != len(layers):
        raise ValueError("layers must be a nonempty comma-separated set")
    return layers


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


def next_logits(
    model, tokenizer, text: str, vector=None, coordinate_diagnostics: dict[int, dict] | None = None,
) -> tuple[torch.Tensor, dict[int, int]]:
    encoded = tokenizer(text, return_tensors="pt", add_special_tokens=False).to(next(model.parameters()).device)
    final = encoded.attention_mask.sum(1) - 1
    context = nullcontext({}) if vector is None else j_lens_coordinate_prefill(
        model, vector, encoded.attention_mask.bool(), coordinate_diagnostics
    )
    with context as calls, torch.inference_mode():
        logits = model(**encoded, use_cache=False).logits[torch.arange(len(final), device=final.device), final][0].float()
    if vector is not None and not all(value == 1 for value in calls.values()):
        raise AssertionError(f"coordinate swap hook calls were {calls}")
    return logits.cpu(), calls


def clean_layer_lens_readouts(model, tokenizer, text: str, vector, candidate_ids: list[int], checkpoint: dict) -> tuple[dict[str, dict], dict[str, dict]]:
    """Read fitted J-lens scores at the final prompt token for category candidates.

    Two scores are returned per layer:
    - raw: hidden @ (W_U @ J).T  (no final norm). Kept for backward comparison only;
      it is not the vendor lens readout and must not be cited as reference fidelity.
    - vendor: W_U @ norm(J @ hidden) via the model's actual final RMSNorm and
      lm_head. This matches JacobianLens.apply -> HFLensModel.unembed, i.e.
      paper lens(h)=softmax(W_U norm(J h)) (Methods, Jacobian Lens).
    The swap basis itself remains raw rows of W_U J (paper's V=[v_s v_t]), not
    normed; the norm is a readout nonlinearity, not part of the residual-space
    coordinate basis. Qwen3.5's final norm is Qwen3_5RMSNorm(eps=1e-6) with a
    learned per-dim weight (mean ~2.19), included via model.model.norm.
    """
    encoded = tokenizer(text, return_tensors="pt", add_special_tokens=False).to(next(model.parameters()).device)
    final = int(encoded.attention_mask.sum().item() - 1)
    captured, handles = {}, []
    for layer in vector.cfg.layers:
        def record(layer):
            def hook(_module, _inputs, output):
                hidden = output[0] if isinstance(output, tuple) else output
                captured[layer] = hidden[0, final].float().detach().cpu()
            return hook
        handles.append(model.model.layers[layer].register_forward_hook(record(layer)))
    try:
        with torch.inference_mode():
            model(**encoded, use_cache=False)
    finally:
        for handle in handles:
            handle.remove()
    candidate_rows = model.lm_head.weight[candidate_ids].float().detach().cpu()
    device = next(model.parameters()).device
    target_dtype = model.lm_head.weight.dtype
    readouts = {}
    for layer, hidden in captured.items():
        # Raw score (no norm) - retained but not fidelity.
        lens_rows = candidate_rows @ checkpoint["J"][layer].float()
        raw_scores = hidden @ lens_rows.T
        # Vendor-normalized score: norm(J @ hidden) then W_U.
        transported = checkpoint["J"][layer].float() @ hidden.float()  # [d_model] cpu
        transported_dev = transported.to(device=device, dtype=target_dtype)
        # Qwen3.5: model.model.norm is Qwen3_5RMSNorm; vendor HFLensModel.unembed applies this before lm_head.
        # Handle Lite textual wrapper vs direct ForCausalLM: text decoder norm lives at model.model.norm for Qwen3.5.
        normed = model.model.norm(transported_dev.unsqueeze(0)).squeeze(0)  # [d_model]
        vendor_logits_full = model.lm_head(normed.unsqueeze(0)).float().squeeze(0).detach().cpu()  # [vocab]
        vendor_scores = vendor_logits_full[candidate_ids]
        source_index = candidate_ids.index(vector.cfg.source_token_id)
        target_index = candidate_ids.index(vector.cfg.target_token_id)
        raw_source, raw_target = float(raw_scores[source_index]), float(raw_scores[target_index])
        vendor_source, vendor_target = float(vendor_scores[source_index]), float(vendor_scores[target_index])
        readouts[str(layer)] = {
            "source_lens_readout": raw_source,
            "target_lens_readout": raw_target,
            "source_candidate_rank": int((raw_scores > raw_source).sum()) + 1,
            "target_candidate_rank": int((raw_scores > raw_target).sum()) + 1,
            "source_vendor_lens_readout": vendor_source,
            "target_vendor_lens_readout": vendor_target,
            "source_vendor_candidate_rank": int((vendor_scores > vendor_source).sum()) + 1,
            "target_vendor_candidate_rank": int((vendor_scores > vendor_target).sum()) + 1,
        }
    # Hidden capture for CPU regression (small, with hashes)
    # Use already-known lens metadata (resolved file) and model revision, not checkpoint internal dict
    from vjp_steering.vjp import _resolve_j_lens_file
    try:
        resolved_lens_file = str(_resolve_j_lens_file(None))
    except Exception:
        resolved_lens_file = str(checkpoint.get("_lens_file", "") or "")
    # Prefer explicit checkpoint _lens_file if main set it, else resolved
    lens_file = str(checkpoint.get("_lens_file", resolved_lens_file) or resolved_lens_file)
    import hashlib
    lens_sha = None
    if lens_file and Path(lens_file).exists():
        lens_sha = hashlib.sha256(Path(lens_file).read_bytes()).hexdigest()
    # Model revision via config commit hash or snapshot
    model_revision = getattr(getattr(model, "config", None), "_commit_hash", None) or getattr(getattr(model, "config", None), "_name_or_path", "")
    hidden_capture = {}
    for layer, hidden in captured.items():
        hidden_capture[str(layer)] = {
            "hidden_sha256": hashlib.sha256(hidden.numpy().tobytes()).hexdigest(),
            "hidden_mean": float(hidden.mean()),
            "hidden_norm": float(hidden.norm()),
            "d_model": int(hidden.shape[0]),
        }
    hidden_vectors_all = {str(l): h.tolist() for l, h in captured.items()}
    hidden_meta = {
        "per_layer": hidden_capture,
        "hidden_vectors": hidden_vectors_all,
        "lens_file": lens_file,
        "lens_sha256": lens_sha,
        "lens_n_prompts": int(checkpoint.get("n_prompts", 0)),
        "d_model": int(checkpoint.get("d_model", 0)),
        "model": str(getattr(getattr(model, "config", None), "_name_or_path", "Qwen/Qwen3.5-4B")),
        "model_revision": str(model_revision),
        "model_dtype": str(next(model.parameters()).dtype),
    }
    return readouts, hidden_meta


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
    parser.add_argument("--layers", default=",".join(map(str, WORKSPACE_LAYERS)))
    parser.add_argument("--coordinate-diagnostics", action="store_true")
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    layers = parse_layers(args.layers)

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
                model, layers, source_token_id=source_id,
                target_token_id=target_id, lens_file=args.lens_file,
            )
            zero = vector
            zero.cfg.coeff = 0.0
            zero_logits, zero_calls = next_logits(model, tokenizer, text, zero)
            torch.testing.assert_close(zero_logits, clean_logits, rtol=0, atol=0)
            vector.cfg.coeff = args.coefficient
            coordinate_diagnostics = {} if args.coordinate_diagnostics else None
            swapped_logits, calls = next_logits(model, tokenizer, text, vector, coordinate_diagnostics)
            checkpoint = torch.load(metadata["lens_file"], map_location="cpu", weights_only=True, mmap=True)
            checkpoint["_lens_file"] = metadata["lens_file"]
            layer_readouts, hidden_capture = (
                clean_layer_lens_readouts(model, tokenizer, text, vector, category_ids, checkpoint)
                if args.coordinate_diagnostics else (None, None)
            )
            trials.append({
                "hidden_capture": hidden_capture,
                "category": category, "prompt": text, "source_token_id": source_id,
                "source_token": tokenizer.decode([source_id]), "target_token_id": target_id,
                "target_token": tokenizer.decode([target_id]), "clean_target_rank": rank(clean_logits, target_id),
                "swapped_target_rank": rank(swapped_logits, target_id),
                "clean_top_token": tokenizer.decode([int(clean_logits.argmax())]),
                "swapped_top_token": tokenizer.decode([int(swapped_logits.argmax())]),
                "clean_source_logit": float(clean_logits[source_id]),
                "clean_target_logit": float(clean_logits[target_id]),
                "swapped_source_logit": float(swapped_logits[source_id]),
                "swapped_target_logit": float(swapped_logits[target_id]),
                "success_top1": int(swapped_logits.argmax()) == target_id,
                "zero_hook_calls": zero_calls, "swap_hook_calls": calls,
                "coordinate_diagnostics": coordinate_diagnostics,
                "clean_layer_lens_readouts": layer_readouts,
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
        "coordinate_diagnostics_requested": args.coordinate_diagnostics,
        "model_layers": model.config.num_hidden_layers,
        "final_norm_module": type(model.model.norm).__name__,
        "lens_repository": J_WORD_LENS_REPO,
        "lens_repository_revision": J_WORD_LENS_REVISION,
        "lens_repository_file": J_WORD_LENS_FILE,
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
            "layers": list(layers), "n_trials": len(trials),
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
