"""Audit whether benchmark prompts activate proposed J-lens swap tokens. — PI/OpenAI Codex"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import median

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

import walk
from vjp_steering.j_lens_concept import final_positions
from vjp_steering.vjp import _activations, _load_j_lens


WORKSPACE_LAYERS = tuple(range(13, 22))
ASSESSMENT_PAIRS = (
    ("false", "true"),
    ("incorrect", "correct"),
    ("invalid", "valid"),
    ("impossible", "possible"),
    ("nonsense", "reasonable"),
    ("unrelated", "related"),
    ("unsupported", "supported"),
)
FIXED_PAIR = ("abrasive", "flattering")


def rank(scores: torch.Tensor, token_id: int) -> torch.Tensor:
    return 1 + (scores > scores[:, token_id, None]).sum(-1)


def one_token_ids(tokenizer, words: tuple[str, ...]) -> dict[str, int]:
    ids = {}
    for word in words:
        encoded = tokenizer(" " + word, add_special_tokens=False).input_ids
        if len(encoded) != 1:
            raise ValueError(f"J-lens audit word is not one leading-space token: {word} {encoded}")
        ids[word] = encoded[0]
    return ids


@torch.inference_mode()
def clean_state(model, tokenizer, prompts: list[str], token_ids: dict[str, int], batch_size: int):
    hidden = {layer: [] for layer in WORKSPACE_LAYERS}
    actual_ranks = {word: [] for word in token_ids}
    top_tokens = []
    for start in range(0, len(prompts), batch_size):
        encoded = tokenizer(
            prompts[start:start + batch_size], return_tensors="pt", padding=True,
            padding_side="right", add_special_tokens=False,
        ).to(next(model.parameters()).device)
        if encoded.input_ids.shape[1] > 384:
            raise ValueError("benchmark prompt exceeds audited context length")
        final = final_positions(encoded.attention_mask)
        rows = torch.arange(len(final), device=final.device)
        with _activations(model, WORKSPACE_LAYERS) as found:
            output = model.model(**encoded, use_cache=False)
        logits = model.lm_head(output.last_hidden_state[rows, final]).float()
        for layer in WORKSPACE_LAYERS:
            hidden[layer].append(found[layer][rows, final].float().cpu())
        for word, token_id in token_ids.items():
            actual_ranks[word].extend(rank(logits, token_id).cpu().tolist())
        values, ids = logits.topk(10, dim=-1)
        for row_values, row_ids in zip(values, ids, strict=True):
            top_tokens.append([
                {"token": tokenizer.decode([int(token_id)]), "token_id": int(token_id), "logit": float(value)}
                for value, token_id in zip(row_values, row_ids, strict=True)
            ])
    return (
        {layer: torch.cat(parts) for layer, parts in hidden.items()},
        actual_ranks,
        top_tokens,
    )


def pair_geometry_and_coordinates(
    hidden: dict[int, torch.Tensor], token_rows: dict[int, dict[str, torch.Tensor]],
    pairs: tuple[tuple[str, str], ...],
):
    geometry, coordinates = {}, {}
    for source, target in pairs:
        name = f"{source}<->{target}"
        geometry[name], coordinates[name] = {}, {}
        for layer in WORKSPACE_LAYERS:
            basis = torch.stack([token_rows[layer][source], token_rows[layer][target]])
            singular_values = torch.linalg.svdvals(basis)
            geometry[name][str(layer)] = {
                "basis_cosine": torch.nn.functional.cosine_similarity(basis[0], basis[1], dim=0).item(),
                "singular_values": singular_values.tolist(),
                "condition_number": (singular_values[0] / singular_values[-1]).item(),
            }
            coordinates[name][str(layer)] = (hidden[layer] @ torch.linalg.pinv(basis)).tolist()
    return geometry, coordinates


def summarize_ranks(values: list[int]) -> dict:
    return {
        "median": median(values),
        "min": min(values),
        "max": max(values),
        "top1": sum(value == 1 for value in values),
        "top10": sum(value <= 10 for value in values),
        "top25": sum(value <= 25 for value in values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--dtype", choices=("float32", "bfloat16"), default="bfloat16")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lens-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()

    rows, cohort_sha256 = walk.read_cohort(100)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token_id = tokenizer.eos_token_id
    words = tuple(dict.fromkeys([word for pair in (*ASSESSMENT_PAIRS, FIXED_PAIR) for word in pair]))
    token_ids = one_token_ids(tokenizer, words)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=getattr(torch, args.dtype), attn_implementation="sdpa",
    ).cuda().eval()
    prompts = walk.generation_inputs(tokenizer, rows)
    hidden, actual_ranks, top_tokens = clean_state(model, tokenizer, prompts, token_ids, args.batch_size)
    lens_file, checkpoint = _load_j_lens(model, WORKSPACE_LAYERS, args.lens_file)
    unembedding = model.lm_head.weight.detach().float()
    token_rows, j_ranks = {}, {word: {} for word in words}
    for layer in WORKSPACE_LAYERS:
        raw = unembedding @ checkpoint["J"][layer].float().to(unembedding.device)
        token_rows[layer] = {word: raw[token_id].cpu() for word, token_id in token_ids.items()}
        scores = hidden[layer].to(raw.device) @ raw.T
        for word, token_id in token_ids.items():
            j_ranks[word][str(layer)] = rank(scores, token_id).cpu().tolist()
        del scores, raw
    geometry, coordinates = pair_geometry_and_coordinates(
        hidden, token_rows, (*ASSESSMENT_PAIRS, FIXED_PAIR),
    )

    selections = {"+C": [], "-C": []}
    for side, source_index in (("+C", 0), ("-C", 1)):
        for row_index, row in enumerate(rows):
            sources = [pair[source_index] for pair in ASSESSMENT_PAIRS]
            source = min(sources, key=lambda word: median([
                j_ranks[word][str(layer)][row_index] for layer in WORKSPACE_LAYERS
            ]))
            pair = next(pair for pair in ASSESSMENT_PAIRS if source in pair)
            target = pair[1 - source_index]
            source_layer_ranks = [j_ranks[source][str(layer)][row_index] for layer in WORKSPACE_LAYERS]
            target_layer_ranks = [j_ranks[target][str(layer)][row_index] for layer in WORKSPACE_LAYERS]
            name = f"{pair[0]}<->{pair[1]}"
            selections[side].append({
                "scenario": row["scenario"],
                "source": source,
                "target": target,
                "source_j_ranks": source_layer_ranks,
                "target_j_ranks": target_layer_ranks,
                "source_active_layers_top25": sum(value <= 25 for value in source_layer_ranks),
                "target_median_outside_top10": median(target_layer_ranks) > 10,
                "source_actual_next_token_rank": actual_ranks[source][row_index],
                "target_actual_next_token_rank": actual_ranks[target][row_index],
                "pair_coordinates": {
                    str(layer): coordinates[name][str(layer)][row_index]
                    for layer in WORKSPACE_LAYERS
                },
            })

    summary = {"actual_next_token_ranks": {word: summarize_ranks(values) for word, values in actual_ranks.items()}}
    for side, selected in selections.items():
        summary[side] = {
            "selected_pairs": dict(Counter(f"{row['source']}->{row['target']}" for row in selected)),
            "source_gate_pass": sum(row["source_active_layers_top25"] >= 3 for row in selected),
            "target_gate_pass": sum(row["target_median_outside_top10"] for row in selected),
            "both_gates_pass": sum(
                row["source_active_layers_top25"] >= 3 and row["target_median_outside_top10"]
                for row in selected
            ),
            "actual_source_top1": sum(row["source_actual_next_token_rank"] == 1 for row in selected),
            "actual_source_top10": sum(row["source_actual_next_token_rank"] <= 10 for row in selected),
            "actual_source_rank_median": median(row["source_actual_next_token_rank"] for row in selected),
        }

    output = {
        "schema": "j_lens_benchmark_activity_audit_v1",
        "source_revision": args.source_revision,
        "model": args.model,
        "dtype": args.dtype,
        "cohort": "sycophancy_all100-v10",
        "cohort_sha256": cohort_sha256,
        "layers": list(WORKSPACE_LAYERS),
        "lens_file": str(lens_file),
        "lens_sha256": hashlib.sha256(lens_file.read_bytes()).hexdigest(),
        "lens_n_prompts": checkpoint["n_prompts"],
        "token_ids": token_ids,
        "assessment_pairs": ASSESSMENT_PAIRS,
        "fixed_pair": FIXED_PAIR,
        "summary": summary,
        "prompts": [
            {"scenario": row["scenario"], "prompt": prompt, "actual_top10": tokens}
            for row, prompt, tokens in zip(rows, prompts, top_tokens, strict=True)
        ],
        "j_lens_ranks": j_ranks,
        "selections": selections,
        "pair_geometry": geometry,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print("J_LENS_ACTIVITY_AUDIT_COMPLETE", json.dumps(summary))


if __name__ == "__main__":
    main()
