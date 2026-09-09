"""Direct CPU test for JLensInjection extraction and apply.

Paper behavior under test (docs/papers/jacobian_lens_workspace.md, Writing):
h <- h + alpha v_t with positive alpha injecting the concept; negative alpha
is ablation (suppression), discussed only for that intervention. Semantic
direction here comes from WHICH concept vector is injected per side (+C
flattering, -C abrasive = our persona adaptation), never from sign: both
sides use positive magnitudes.
"""
import torch
from types import SimpleNamespace


def _tiny_setup():
    from vjp_steering import vjp as vjp_mod
    d_model = 8
    vocab = 10
    torch.manual_seed(2)
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

    import tempfile
    from pathlib import Path
    lens_file = Path(tempfile.mkdtemp()) / "tiny_lens.pt"
    lens_file.write_bytes(b"tiny-lens-bytes")
    return vjp_mod, FakeModel(), TinyTok(), lens_file, fake_ckpt, W_U


def test_injection_extraction_both_sides():
    from unittest.mock import patch
    from vjp_steering.vjp import j_lens_injection
    vjp_mod, model, tok, lens_file, fake_ckpt, W_U = _tiny_setup()
    got = {}
    with patch.object(vjp_mod, "_load_j_lens", return_value=(lens_file, fake_ckpt)):
        for concept in ("flattering", "abrasive"):
            vector, meta = j_lens_injection(model, tok, (16,), concept_token=concept)
            assert vector.cfg.method == "j_lens_injection"
            assert vector.cfg.concept_token == concept
            assert meta["concept_token_id"] == (2 if concept == "flattering" else 1)
            v_hat = vector.shared[16]["v"]
            expected = W_U[meta["concept_token_id"]].float()
            expected = expected / expected.norm()
            assert torch.allclose(v_hat.float(), expected.float(), atol=1e-5), f"{concept} vector mismatch"
            assert torch.allclose(v_hat.norm(), torch.tensor(1.0), atol=1e-5)
            got[concept] = v_hat
    assert not torch.allclose(got["flattering"], got["abrasive"]), "side vectors must differ"
    print("PASS extraction: production j_lens_injection returns distinct unit vectors per side")


def test_injection_apply():
    from vjp_steering.vjp import JLensInjection, JLensInjectionC
    torch.manual_seed(3)
    d_model = 8
    for concept in ("flattering", "abrasive"):
        v_hat = torch.randn(d_model)
        v_hat = v_hat / v_hat.norm()
        shared = {"v": v_hat}
        cfg = JLensInjectionC(layers=(16,), concept_token=concept, concept_token_id=1)
        # positive amplitude moves hidden along the injected concept
        for C in (1.0, 2.0, 4.0, 8.0, 16.0):
            cfg.coeff = float(C)
            y = torch.randn(1, 5, d_model, dtype=torch.bfloat16)
            out = JLensInjection.apply(None, None, y, shared, None, cfg)
            assert out.shape == y.shape and out.dtype == y.dtype, f"{concept} C={C} shape/dtype"
            expected = y + C * v_hat.to(device=y.device, dtype=y.dtype)
            assert torch.allclose(out.float(), expected.float(), atol=1e-4), f"{concept} C={C} equation"
        # C=0 is the bare no-op
        cfg.coeff = 0.0
        y = torch.randn(1, 5, d_model, dtype=torch.bfloat16)
        assert torch.allclose(JLensInjection.apply(None, None, y, shared, None, cfg).float(), y.float(), atol=1e-6)
        # decode position skipped
        cfg.coeff = 4.0
        y1 = torch.randn(1, 1, d_model, dtype=torch.bfloat16)
        assert torch.equal(JLensInjection.apply(None, None, y1, shared, None, cfg), y1)
    print("PASS apply: grid 1,2,4,8,16 positive amplitudes, C=0 no-op, dtype/shape, seq_len=1 skip")


if __name__ == "__main__":
    test_injection_extraction_both_sides()
    test_injection_apply()
    print("ALL TESTS PASS")
