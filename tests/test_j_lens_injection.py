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
    # Non-symmetric J: identity cannot detect transpose (J==J.T) or ignored-J
    # (J==I) bugs in the W_U @ J basis path, so the fixture must break both.
    tri = torch.triu(torch.randn(d_model, d_model)) + 2.0 * torch.eye(d_model)
    assert not torch.allclose(tri, tri.T) and not torch.allclose(tri, torch.eye(d_model))
    fake_J = {16: tri}
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
    return vjp_mod, FakeModel(), TinyTok(), lens_file, fake_ckpt, W_U, fake_J


def test_injection_extraction_both_sides():
    from unittest.mock import patch
    from vjp_steering.vjp import j_lens_injection
    vjp_mod, model, tok, lens_file, fake_ckpt, W_U, fake_J = _tiny_setup()
    got = {}
    with patch.object(vjp_mod, "_load_j_lens", return_value=(lens_file, fake_ckpt)):
        for concept in ("flattering", "abrasive"):
            vector, meta = j_lens_injection(model, tok, (16,), concept_token=concept)
            assert vector.cfg.method == "j_lens_injection"
            assert vector.cfg.concept_token == concept
            assert meta["concept_token_id"] == (2 if concept == "flattering" else 1)
            v_hat = vector.shared[16]["v"]
            # Non-symmetric J: this fails under transpose (J.T) or ignored-J bugs.
            expected = (W_U[meta["concept_token_id"]].float() @ fake_J[16].float())
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


def test_side_dispatch_through_production_path():
    """End-to-end dispatch: applied_coefficient -> Vector(model, C=..) hooks -> forward.

    Exercises the actual steering path (not manual concept loops): per-side vectors
from production extraction, unsigned positive C on both sides, hooked forward
through a tiny block. Non-symmetric J keeps transpose/ignored-J bugs detectable.
    """
    import sys
    import torch.nn
    from pathlib import Path
    from unittest.mock import patch
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from experiment import applied_coefficient
    from vjp_steering import vjp as vjp_mod
    from vjp_steering.vjp import j_lens_injection

    d_model = 8
    torch.manual_seed(11)
    W_U = torch.randn(10, d_model)
    tri = torch.triu(torch.randn(d_model, d_model)) + 2.0 * torch.eye(d_model)
    fake_ckpt = {"J": {0: tri}, "n_prompts": 1, "source_layers": [0], "d_model": d_model}

    class TinyTok:
        def __call__(self, text, add_special_tokens=False, **kw):
            if text == " abrasive":
                return SimpleNamespace(input_ids=[1])
            if text == " flattering":
                return SimpleNamespace(input_ids=[2])
            return SimpleNamespace(input_ids=[3])

    class TinyBlock(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.lin = torch.nn.Linear(d_model, d_model, bias=False)
            with torch.no_grad():
                self.lin.weight.copy_(torch.eye(d_model))

        def forward(self, x):
            return self.lin(x)

    class TinyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.config = SimpleNamespace(hidden_size=d_model)
            self.layers = torch.nn.ModuleList([TinyBlock()])
            self.lm_head = SimpleNamespace(weight=W_U)

    import tempfile
    lens_file = Path(tempfile.mkdtemp()) / "tiny_lens.pt"
    lens_file.write_bytes(b"tiny-lens-bytes")
    model = TinyModel()
    with patch.object(vjp_mod, "_load_j_lens", return_value=(lens_file, fake_ckpt)):
        vectors = {}
        for side, concept in (("+C", "flattering"), ("-C", "abrasive")):
            vectors[side], _ = j_lens_injection(model, TinyTok(), (0,), concept_token=concept)
            # Mirror production (gpu_stage sets cfg dtype to the run dtype); float32 keeps
            # this dispatch test exact, since buffers round-trip through cfg dtype.
            vectors[side].cfg.dtype = torch.float32
    for side, concept_id in (("+C", 2), ("-C", 1)):
        for C in (1.0, 2.0, 4.0, 8.0, 16.0):
            coeff = applied_coefficient("j_lens_injection", side, C)
            assert coeff == C and coeff > 0, f"{side} C={C} must dispatch unsigned positive"
            y = torch.randn(1, 4, d_model)
            with vectors[side](model, C=coeff):
                out = model.layers[0](y)
            v_hat = (W_U[concept_id].float() @ tri.float())
            v_hat = v_hat / v_hat.norm()
            assert torch.allclose(out.float(), (y + coeff * v_hat).float(), atol=1e-5), \
                f"{side} C={C} hooked forward mismatch"
    print("PASS dispatch: applied_coefficient unsigned both sides, hooked forward equals y + C*v_hat per side")


if __name__ == "__main__":
    test_injection_extraction_both_sides()
    test_injection_apply()
    test_side_dispatch_through_production_path()
    print("ALL TESTS PASS")
