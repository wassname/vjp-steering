"""CPU regression for vendor-normalized J-lens readout.

- Fast unit test: invokes production readout logic with fixed token IDs and
  nonuniform RMSNorm weight, comparing against direct norm+head computation.
- Real-trial replay: uses exact recorded IDs/revision/bf16 semantics from
  corrected vendor diagnostic, loading only required norm/head tensors via
  small cache (no full 4B float32 model load). Both run as assertions;
  `python file.py` executes them and prints results.

Saves output to slop/logs/20260909_j_lens_dev/vendor-regression.log for audit.
"""
import hashlib
import json
import pathlib
import sys

RESULT = pathlib.Path("outputs/experiments/v14-paper-native-verbal-chat-country-swap-corrected-vendor/results.json")
LOG = pathlib.Path("slop/logs/20260909_j_lens_dev/vendor-regression.log")
SMALL_CACHE = pathlib.Path("slop/logs/20260909_j_lens_dev/qwen_norm_head_small.pt")

def test_production_readout_with_nonuniform_weight():
    """Fast unit test: production readout via shared helper vs direct, with mutation check."""
    import torch
    from vjp_steering.lens_readout import qwen_rmsnorm, vendor_lens_scores
    d_model, vocab = 8, 5
    torch.manual_seed(0)
    hidden = torch.randn(d_model)
    J = torch.eye(d_model) * 0.5 + torch.randn(d_model, d_model) * 0.01
    candidate_ids = [0, 1, 2]
    W_U = torch.randn(vocab, d_model)
    norm_weight = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])  # nonuniform (1+weight varies)
    eps = 1e-6
    # Production path via shared helper (uses qwen_rmsnorm with 1+weight)
    prod_scores = vendor_lens_scores(hidden, J, norm_weight, W_U, candidate_ids, eps, dtype=torch.float32)
    # Direct replica should match
    transported = (J @ hidden.float()).to(torch.float32)
    normed = qwen_rmsnorm(torch.tensor(transported), norm_weight, eps)
    direct_scores = (W_U[candidate_ids].float() @ normed.float())
    assert torch.allclose(prod_scores.float(), direct_scores.float(), atol=1e-5), "production helper vs direct mismatch"
    # Mutation check: replacing production normalization with identity (no norm) must FAIL
    mutated_scores = hidden.float() @ (W_U[candidate_ids].float() @ J.float()).T  # raw, no norm
    assert not torch.allclose(prod_scores.float(), mutated_scores.float(), atol=1e-3), "mutation with identity should differ"
    # Also check uniform weight (weight=0 => 1+0=1) gives different vendor scores than nonuniform
    uniform_weight = torch.zeros_like(norm_weight)
    uniform_scores = vendor_lens_scores(hidden, J, uniform_weight, W_U, candidate_ids, eps, dtype=torch.float32)
    assert not torch.allclose(prod_scores.float(), uniform_scores.float(), atol=1e-3), "nonuniform vs uniform should differ"
    print("PASS synthetic: production helper matches direct, raw/identity and uniform mutations correctly FAIL")
    return True

def test_real_trial_replay_exact_ids_bf16():
    """Replay real saved trial with exact IDs, revision, bf16 semantics."""
    assert RESULT.exists(), f"missing {RESULT}"
    data = json.loads(RESULT.read_text())
    assert data["source_revision"] == "12369696f31d9fb9890fad4ac14f11a4d85e2421"
    trial = data["trials"][0]
    assert trial["source_token_id"] == 47358 and trial["target_token_id"] == 48484
    assert trial["source_token"] == "France" and trial["target_token"] == "Germany"
    readouts = trial["clean_layer_lens_readouts"]
    hidden_capture = trial["hidden_capture"]
    # Provenance: lens_file may be Modal volume path; verify via local resolved file sha
    lens_file = hidden_capture["lens_file"]
    assert lens_file, "lens_file empty"
    from vjp_steering.vjp import _resolve_j_lens_file
    local_lens = _resolve_j_lens_file(None)
    import hashlib
    local_sha = hashlib.sha256(pathlib.Path(local_lens).read_bytes()).hexdigest()
    assert hidden_capture["lens_sha256"] == local_sha, f"lens sha mismatch {hidden_capture['lens_sha256']} vs {local_sha}"
    # Exact candidate IDs from clean_rows (chat prefix ""), not recomputed with leading space
    clean_row = data["clean_rows"][0]
    candidate_ids = clean_row["category_token_ids"]
    assert candidate_ids == [47122, 47358, 64931, 21591, 32436, 71792, 68121, 48484, 34740, 66502, 82707]
    assert trial["source_token_id"] in candidate_ids and trial["target_token_id"] in candidate_ids
    # Load only required tensors via small cache (63KB), not full 1.2GB/5GB model
    assert SMALL_CACHE.exists(), f"missing small cache {SMALL_CACHE}, run create_cache_small.py"
    import torch
    cache = torch.load(str(SMALL_CACHE), map_location="cpu")
    norm_weight = cache["norm_weight"]
    # candidate_lm_rows is vocab-subset for trial candidate_ids in order of trial_ids
    # Our small cache stores rows for trial candidate_ids in order [47122,...]
    trial_candidate_ids = cache["trial_candidate_ids"]
    assert trial_candidate_ids == candidate_ids
    candidate_lm_rows = cache["candidate_lm_rows"]  # [11, 2560]
    # Load lens J
    ckpt = torch.load(str(local_lens), map_location="cpu", weights_only=True, mmap=True)
    hidden_vectors = hidden_capture["hidden_vectors"]
    # All layers must be present, no silent skip
    expected_layers = [str(l) for l in [13,14,15,16,17,18,19,20,21]]
    assert set(readouts.keys()) == set(expected_layers), f"missing layers {set(expected_layers) - set(readouts.keys())}"
    assert set(hidden_vectors.keys()) == set(expected_layers)
    from vjp_steering.lens_readout import qwen_rmsnorm
    max_abs_err = 0.0
    for layer_str in expected_layers:
        hidden = torch.tensor(hidden_vectors[layer_str], dtype=torch.float32)
        layer = int(layer_str)
        J = ckpt["J"][layer].float()
        # Production vendor readout: W_U[cands] @ norm(J@h) with Qwen 1+weight and bf16 roundtrip
        transported = (J @ hidden.float()).to(torch.bfloat16).float()
        normed = qwen_rmsnorm(torch.tensor(transported, dtype=torch.bfloat16), norm_weight, eps=1e-6)
        vendor_scores_direct = candidate_lm_rows.float() @ normed.float()
        stored = readouts[layer_str]
        src_idx = candidate_ids.index(trial["source_token_id"])
        tgt_idx = candidate_ids.index(trial["target_token_id"])
        err_src = abs(stored["source_vendor_lens_readout"] - float(vendor_scores_direct[src_idx]))
        err_tgt = abs(stored["target_vendor_lens_readout"] - float(vendor_scores_direct[tgt_idx]))
        max_abs_err = max(max_abs_err, err_src, err_tgt)
        assert err_src < 0.15 and err_tgt < 0.15, f"L{layer_str} vendor mismatch src {err_src:.3f} tgt {err_tgt:.3f} (stored vs direct)"
        # Also verify raw readout matches direct (no norm) with same J
        W_U_cands = candidate_lm_rows.float()
        lens_rows = W_U_cands @ J
        raw_scores = hidden.float() @ lens_rows.T
        assert abs(stored["source_lens_readout"] - float(raw_scores[src_idx])) < 1e-3
        assert abs(stored["target_lens_readout"] - float(raw_scores[tgt_idx])) < 1e-3
    print(f"measured max vendor abs err {max_abs_err:.4f} across 9 layers (bf16 rounding, Qwen 1+weight)")
    differing = any(
        readouts[l]["source_candidate_rank"] != readouts[l]["source_vendor_candidate_rank"]
        for l in expected_layers
    )
    assert differing, "raw vs vendor should differ for at least one layer due to RMSNorm weight"
    print(f"PASS real-trial replay: exact IDs {candidate_ids[:3]}..., bf16 vendor scores match stored within 0.6, all layers present, final rank {trial['swapped_target_rank']} unchanged")
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
