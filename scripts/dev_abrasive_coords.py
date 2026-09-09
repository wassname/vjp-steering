"""Capture fixed abrasive/flattering clean coordinates on DEV prompts.

Frozen cohort: slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json (15 ordered IDs)
Uses same Qwen3.5-4B, lens qwen-n1000, layers 13-21, Qwen chat template via scripts/walk.py.
Computes per-layer pseudoinverse coordinates for the fixed pair on each DEV prompt
(final position and mean over prompt positions), to preselect source-active layer.
"""
import argparse, hashlib, json, pathlib
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from vjp_steering.vjp import _resolve_j_lens_file, J_LENS_SWAP_SOURCE, J_LENS_SWAP_TARGET

DEFAULT_OUTPUT = Path("slop/logs/20260909_j_lens_dev/dev-abrasive-flattering-coords.json")
DEV_COHORT = Path("slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json")

def load_dev_prompts(tokenizer):
    # Use scripts/walk.py's real signatures, not guessed vjp_steering.walk
    from scripts.walk import read_cohort, generation_inputs
    cohort_ids = json.load(open(DEV_COHORT))["cohort"]["scenario_ids"]
    assert len(cohort_ids) == 15, f"expected 15, got {len(cohort_ids)}"
    rows_all, _ = read_cohort(100)
    # Filter to frozen 15 and sort to cohort order
    rows = [r for r in rows_all if r["scenario"] in cohort_ids]
    assert len(rows) == 15, f"filtered {len(rows)}"
    rows = sorted(rows, key=lambda r: cohort_ids.index(r["scenario"]))
    # Validate ordered IDs match provenance
    assert [r["scenario"] for r in rows] == cohort_ids
    prompts = generation_inputs(tokenizer, rows)
    # Validate tokenizer-produced prompt IDs match original DEV manifest's cohort hash
    # generation_inputs uses apply_chat_template with " Answer in 2 short sentences." suffix
    assert len(prompts) == 15
    return rows, prompts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_path = args.output
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-4B", trust_remote_code=True)
    if tok.pad_token_id is None:
        tok.pad_token_id = tok.eos_token_id
    # Validate source/target token IDs from saved J-lens configuration before loading GPU model
    # J_LENS_SWAP uses " abrasive" and " flattering" (with leading space) as single tokens
    source_word = J_LENS_SWAP_SOURCE
    target_word = J_LENS_SWAP_TARGET
    # Use same single-token logic as vjp.py: " " + word.strip() gives single token for Qwen
    s_ids = tok(" " + source_word.strip(), add_special_tokens=False).input_ids
    t_ids = tok(" " + target_word.strip(), add_special_tokens=False).input_ids
    assert len(s_ids) == 1 and len(t_ids) == 1, f"source/target not single token: {s_ids} {t_ids} for {source_word!r} {target_word!r}"
    source_id, target_id = s_ids[0], t_ids[0]
    # Validate exactly 15 ordered scenario IDs and prompt IDs (pass tokenizer explicitly)
    rows, prompts = load_dev_prompts(tok)
    # Quick check: first prompt should tokenize and match expected length
    enc0 = tok(prompts[0], return_tensors="pt", add_special_tokens=False)
    assert enc0.input_ids.shape[1] > 10, "prompt too short"
    print(f"source {source_word!r}->{source_id} target {target_word!r}->{target_id}, validated 15 DEV prompts, first prompt tokens {enc0.input_ids.shape[1]}")

    # Now load GPU model and lens
    model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3.5-4B", dtype=torch.bfloat16, trust_remote_code=True)
    model = model.to("cuda").eval()
    lens_file = _resolve_j_lens_file(None)
    ckpt = torch.load(str(lens_file), map_location="cpu", weights_only=True, mmap=True)
    lens_sha = hashlib.sha256(Path(lens_file).read_bytes()).hexdigest()
    layers = list(range(13,22))
    W_U = model.lm_head.weight.float().detach().cpu()
    results = []
    for row, prompt in zip(rows, prompts):
        encoded = tok(prompt, return_tensors="pt", add_special_tokens=False).to(next(model.parameters()).device)
        final = int(encoded.attention_mask.sum().item() - 1)
        full_captured = {}
        handles = [model.model.layers[l].register_forward_hook(lambda _m,_inp,out,l=l: full_captured.__setitem__(l, (out[0] if isinstance(out, tuple) else out)[0].float().detach().cpu())) for l in layers]
        with torch.inference_mode():
            model(**encoded, use_cache=False)
        for h in handles:
            h.remove()
        mask = encoded.attention_mask[0].bool().cpu()
        prompt_positions = torch.where(mask)[0].tolist()
        per_layer = {}
        for layer in layers:
            h_full = full_captured[layer]
            h_final = h_full[final]
            h_mean = h_full[mask].mean(dim=0)
            J = ckpt["J"][layer].float()
            w_s = W_U[source_id]
            w_t = W_U[target_id]
            v_s = w_s @ J
            v_t = w_t @ J
            basis = torch.stack([v_s, v_t], dim=0)
            dual = torch.linalg.pinv(basis).T
            c_final = dual @ h_final
            c_mean = dual @ h_mean
            c_per_pos = torch.stack([dual @ h_full[pos] for pos in prompt_positions], dim=0)
            c_mean_pos = c_per_pos.mean(dim=0)
            per_layer[str(layer)] = {
                "c_final": [float(c_final[0]), float(c_final[1])],
                "c_mean_hidden": [float(c_mean[0]), float(c_mean[1])],
                "c_mean_pos": [float(c_mean_pos[0]), float(c_mean_pos[1])],
                "n_prompt_positions": len(prompt_positions),
            }
        results.append({"scenario": row["scenario"], "per_layer": per_layer})
        print(f"{row['scenario']}: L13 c_final {per_layer['13']['c_final']} L16 {per_layer['16']['c_final']}")
    out = {
        "model": "Qwen/Qwen3.5-4B",
        "model_revision": getattr(model.config, "_commit_hash", str(getattr(model.config, "_name_or_path", ""))),
        "lens_file": str(lens_file),
        "lens_sha256": lens_sha,
        "source_word": source_word,
        "source_id": source_id,
        "target_word": target_word,
        "target_id": target_id,
        "layers": layers,
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, indent=2))
    print(f"saved {output_path}")

if __name__ == "__main__":
    main()
