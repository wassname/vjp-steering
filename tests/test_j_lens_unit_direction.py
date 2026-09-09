"""Direct CPU test for JLensUnitDirection.apply and j_lens_unit_direction extraction.

Withdraws the earlier helper-only preflight claim: the previous version never
called production code (dead fake model/tokenizer, print-only decode claim).
This version calls JLensUnitDirection.apply directly and calls extraction with
a patched tiny _load_j_lens checkpoint.
"""
import torch
from types import SimpleNamespace


def test_jlens_unit_direction_apply():
    from vjp_steering.vjp import JLensUnitDirection, JLensUnitDirectionC

    d_model = 8
    torch.manual_seed(0)
    d_hat = torch.randn(d_model)
    d_hat = d_hat / d_hat.norm()
    shared = {"d_hat": d_hat}
    cfg = JLensUnitDirectionC(layers=(16,), source_token="abrasive", target_token="flattering")
    for C in (0, 1, -1):
        cfg.coeff = float(C)
        y = torch.randn(1, 5, d_model, dtype=torch.bfloat16)
        out = JLensUnitDirection.apply(None, None, y, shared, None, cfg)
        assert out.shape == y.shape, f"shape mismatch C={C}"
        assert out.dtype == y.dtype, f"dtype mismatch C={C}: {out.dtype} vs {y.dtype}"
        expected = y + C * d_hat.to(device=y.device, dtype=y.dtype)
        assert torch.allclose(out.float(), expected.float(), atol=1e-5), f"C={C} equation mismatch"
    cfg.coeff = 1.0
    y1 = torch.randn(1, 1, d_model, dtype=torch.bfloat16)
    out1 = JLensUnitDirection.apply(None, None, y1, shared, None, cfg)
    assert torch.equal(out1, y1), "seq_len=1 must hit the skip branch unchanged"
    print("PASS JLensUnitDirection.apply: C=0,+1,-1 seq_len>1 dtype/shape/equation, seq_len=1 skip")


def test_extraction_with_patched_tiny_checkpoint(tmp_path=None):
    """Call production j_lens_unit_direction with patched _load_j_lens."""
    import tempfile
    from pathlib import Path
    from unittest.mock import patch
    from vjp_steering import vjp as vjp_mod
    from vjp_steering.vjp import j_lens_unit_direction

    d_model = 8
    vocab = 10
    torch.manual_seed(1)
    W_U = torch.randn(vocab, d_model)
    fake_J = {16: torch.eye(d_model)}
    fake_ckpt = {"J": fake_J, "n_prompts": 1, "source_layers": [16], "d_model": d_model}

    class TinyTok:
        def __call__(self, text, add_special_tokens=False, **kw):
            if text == " abrasive":
                return SimpleNamespace(input_ids=[1])
            if text == " flattering":
                return SimpleNamespace(input_ids=[2])
            return SimpleNamespace(input_ids=[3, 4, 5])

    class FakeModel:
        def __init__(self):
            self.config = SimpleNamespace(hidden_size=d_model)
            self.lm_head = SimpleNamespace(weight=W_U)

    directory = tempfile.mkdtemp() if tmp_path is None else str(tmp_path)
    lens_file = Path(directory) / "tiny_lens.pt"
    lens_file.write_bytes(b"tiny-lens-bytes")

    with patch.object(vjp_mod, "_load_j_lens", return_value=(lens_file, fake_ckpt)):
        vector, meta = j_lens_unit_direction(FakeModel(), TinyTok(), (16,))

    assert vector.cfg.method == "j_lens_unit_direction"
    assert vector.cfg.layers == (16,)
    got = vector.shared[16]["d_hat"]
    v_source = W_U[1].float() @ fake_J[16].float()
    v_target = W_U[2].float() @ fake_J[16].float()
    expected = (v_target - v_source)
    expected = expected / expected.norm()
    assert torch.allclose(got.float(), expected.float(), atol=1e-5), "d_hat mismatch vs normalize(v_t - v_s)"
    assert torch.allclose(got.norm(), torch.tensor(1.0), atol=1e-5), "d_hat not unit norm"
    assert meta["source_token_id"] == 1 and meta["target_token_id"] == 2
    assert meta["lens_n_prompts"] == 1
    print("PASS extraction via patched _load_j_lens: production j_lens_unit_direction returns unit d_hat")


if __name__ == "__main__":
    test_jlens_unit_direction_apply()
    test_extraction_with_patched_tiny_checkpoint()
    print("ALL TESTS PASS")
