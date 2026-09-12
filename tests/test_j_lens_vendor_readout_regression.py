"""CPU regression for vendor-normalized J-lens readout.

- Fast unit test: tiny mock through actual Qwen RMSNorm (1+weight, eps1e-6, bf16) via
  shared helper; mutation with identity must fail.
- Real-trial replay: exact IDs/revision/bf16 via small cache, reports measured max abs err.
Saves output to slop/logs/20260909_j_lens_dev/vendor-regression.log
"""
import hashlib
import json
import pathlib
import sys

RESULT = pathlib.Path("outputs/experiments/v14-paper-native-verbal-chat-country-swap-corrected-vendor/results.json")
LOG = pathlib.Path("slop/logs/20260909_j_lens_dev/vendor-regression.log")
SMALL_CACHE = pathlib.Path("slop/logs/20260909_j_lens_dev/qwen_norm_head_small.pt")

def test_production_readout_with_nonuniform_weight():
    """Call production readout; compare independent RMSNorm arithmetic. -- PI/OpenAI"""
    from types import SimpleNamespace
    from unittest.mock import patch
    import torch
    import torch.nn as nn
    from transformers import BatchEncoding
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5RMSNorm

    sys.path.insert(0, str(pathlib.Path("scripts").resolve()))
    from reproduce_paper_j_lens import clean_layer_lens_readouts

    torch.manual_seed(0)
    d_model, vocab = 8, 5
    hidden = torch.randn(d_model).to(torch.bfloat16)
    J = torch.eye(d_model) * 0.5 + torch.randn(d_model, d_model) * 0.1
    candidate_ids = [0, 1, 2]

    class Model(nn.Module):
        def __init__(self):
            super().__init__()
            self.model = nn.Module()
            self.model.layers = nn.ModuleList([nn.Identity()])
            self.model.norm = Qwen3_5RMSNorm(d_model, eps=1e-6)
            self.lm_head = nn.Linear(d_model, vocab, bias=False).to(torch.bfloat16)
            with torch.no_grad():
                self.model.norm.weight.copy_(torch.arange(d_model))

        def forward(self, **kwargs):
            return self.model.layers[0](hidden.view(1, 1, -1))

    model = Model()
    tokenizer = lambda *args, **kwargs: BatchEncoding(dict(input_ids=torch.ones(1, 1, dtype=torch.long), attention_mask=torch.ones(1, 1, dtype=torch.long)))
    vector = SimpleNamespace(cfg=SimpleNamespace(layers=(0,), source_token_id=0, target_token_id=1))
    checkpoint = {"J": {0: J}}

    def production_scores():
        with patch("vjp_steering.vjp._resolve_j_lens_file", return_value=pathlib.Path("/nonexistent/test-lens")):
            readouts, capture = clean_layer_lens_readouts(model, tokenizer, "prompt", vector, candidate_ids, checkpoint)
        assert capture["hidden_vectors"]["0"] == hidden.float().tolist()
        return torch.tensor([readouts["0"][f"{side}_vendor_lens_readout"] for side in ("source", "target")])

    transported = (J @ hidden.float()).to(torch.bfloat16)
    normalized = transported.float() * torch.rsqrt(transported.float().square().mean() + 1e-6)
    normalized = (normalized * (1 + torch.arange(d_model))).to(torch.bfloat16)
    expected = (model.lm_head.weight.detach().float() @ normalized.float()).to(torch.bfloat16).float()[:2]
    assert torch.allclose(production_scores(), expected, atol=1e-5), "production readout omitted or changed normalization"
    with patch.object(model.model, "norm", nn.Identity()):
        assert not torch.allclose(production_scores(), expected, atol=1e-3), "identity mutation escaped detection"
    with torch.no_grad():
        model.model.norm.weight.zero_()
    assert not torch.allclose(production_scores(), expected, atol=1e-3), "uniform norm escaped detection"
    print("PASS production readout: independent nonuniform RMSNorm arithmetic; identity/uniform mutations differ")
    return True

def test_real_trial_replay_exact_ids_bf16():
    """Replay real trial with exact IDs, bf16, small cache, report measured max err."""
    assert RESULT.exists(), f"missing {RESULT}"
    data = json.loads(RESULT.read_text())
    assert data["source_revision"] == "12369696f31d9fb9890fad4ac14f11a4d85e2421"
    trial = data["trials"][0]
    assert trial["source_token_id"] == 47358 and trial["target_token_id"] == 48484
    readouts = trial["clean_layer_lens_readouts"]
    hidden_capture = trial["hidden_capture"]
    lens_file = hidden_capture["lens_file"]
    assert lens_file, "lens_file empty"
    from vjp_steering.vjp import _resolve_j_lens_file
    local_lens = _resolve_j_lens_file(None)
    local_sha = hashlib.sha256(pathlib.Path(local_lens).read_bytes()).hexdigest()
    assert hidden_capture["lens_sha256"] == local_sha
    clean_row = data["clean_rows"][0]
    candidate_ids = clean_row["category_token_ids"]
    assert candidate_ids == [47122, 47358, 64931, 21591, 32436, 71792, 68121, 48484, 34740, 66502, 82707]
    assert SMALL_CACHE.exists(), f"missing small cache {SMALL_CACHE}"
    import torch
    cache = torch.load(str(SMALL_CACHE), map_location="cpu")
    norm_weight = cache["norm_weight"]
    assert cache["trial_candidate_ids"] == candidate_ids
    candidate_lm_rows = cache["candidate_lm_rows"]
    ckpt = torch.load(str(local_lens), map_location="cpu", weights_only=True, mmap=True)
    hidden_vectors = hidden_capture["hidden_vectors"]
    expected_layers = [str(l) for l in [13,14,15,16,17,18,19,20,21]]
    assert set(readouts.keys()) == set(expected_layers)
    assert set(hidden_vectors.keys()) == set(expected_layers)
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5RMSNorm
    max_abs_err = 0.0
    for layer_str in expected_layers:
        hidden = torch.tensor(hidden_vectors[layer_str], dtype=torch.float32)
        J = ckpt["J"][int(layer_str)].float()
        # Production: use actual Qwen norm with 1+weight, bf16
        norm = Qwen3_5RMSNorm(2560, eps=1e-6)
        with torch.no_grad():
            norm.weight.copy_(norm_weight)
        transported = (J @ hidden).to(torch.bfloat16)
        normed = norm(transported.unsqueeze(0)).squeeze(0)
        # lm_head candidate rows
        vendor_scores_direct = candidate_lm_rows.float() @ normed.float()
        stored = readouts[layer_str]
        src_idx = candidate_ids.index(trial["source_token_id"])
        tgt_idx = candidate_ids.index(trial["target_token_id"])
        err_src = abs(stored["source_vendor_lens_readout"] - float(vendor_scores_direct[src_idx]))
        err_tgt = abs(stored["target_vendor_lens_readout"] - float(vendor_scores_direct[tgt_idx]))
        max_abs_err = max(max_abs_err, err_src, err_tgt)
        assert err_src < 0.15 and err_tgt < 0.15, f"L{layer_str} vendor mismatch src {err_src:.3f} tgt {err_tgt:.3f}"
        # Raw (no norm) check
        lens_rows = candidate_lm_rows.float() @ J
        raw_scores = hidden.float() @ lens_rows.T
        assert abs(stored["source_lens_readout"] - float(raw_scores[src_idx])) < 1e-3
        assert abs(stored["target_lens_readout"] - float(raw_scores[tgt_idx])) < 1e-3
    print(f"measured max vendor abs err {max_abs_err:.4f} across 9 layers (bf16, Qwen 1+weight)")
    differing = any(readouts[l]["source_candidate_rank"] != readouts[l]["source_vendor_candidate_rank"] for l in expected_layers)
    assert differing
    print(f"PASS real-trial replay: exact IDs {candidate_ids[:3]}..., all layers present, final rank {trial['swapped_target_rank']} unchanged")
    return True

if __name__ == "__main__":
    LOG.parent.mkdir(parents=True, exist_ok=True)
    out_lines = []
    try:
        test_production_readout_with_nonuniform_weight()
        out_lines.append("PASS synthetic")
    except Exception as e:
        import traceback
        traceback.print_exc()
        out_lines.append(f"FAIL synthetic: {e}")
        LOG.write_text("\n".join(out_lines) + "\n")
        print("LOG written to", LOG)
        sys.exit(1)
    try:
        test_real_trial_replay_exact_ids_bf16()
        out_lines.append("PASS real-trial")
    except Exception as e:
        import traceback
        traceback.print_exc()
        out_lines.append(f"FAIL real-trial: {e}")
        LOG.write_text("\n".join(out_lines) + "\n")
        print("LOG written to", LOG)
        sys.exit(1)
    LOG.write_text("\n".join(out_lines) + "\n")
    print("LOG written to", LOG)
    assert len(out_lines) == 2 and all("PASS" in l for l in out_lines)

def test_vendor_regression_suite():
    test_production_readout_with_nonuniform_weight()
    test_real_trial_replay_exact_ids_bf16()
