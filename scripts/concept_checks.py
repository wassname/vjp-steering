"""Focused checks and real tiny-pipeline smoke for concept addition. — PI/OpenAI Codex"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import torch
from steering_lite import Vector

from vjp_steering.j_lens_concept import (
    JLensConceptC, concept_prefill, concept_spec, final_positions, gradient_pursuit, implementation_hash,
)
from vjp_steering.vjp import _activations


def self_test():
    from experiment import validate_extraction_identity, vector_sha256

    dictionary = torch.tensor([[1., 0., 0.], [.6, .8, 0.], [0., 0., 1.]])
    signal = torch.tensor([.3, 1., -.5])
    w, component, errors = gradient_pursuit(signal, dictionary)
    assert (w >= 0).all() and w.count_nonzero() <= 16 and errors[-1] < signal.norm()
    torch.testing.assert_close(component, w @ dictionary)
    torch.testing.assert_close(signal, component + (signal - component))
    assert w[0] == 0 and w[1] > 0 and w[2] == 0
    two_steps, _, early = gradient_pursuit(torch.tensor([1., 1., 0.]), dictionary, k=2)
    refined, _, late = gradient_pursuit(torch.tensor([1., 1., 0.]), dictionary, k=16)
    assert two_steps[0] > 0 and two_steps[1] > 0
    assert refined[1] != two_steps[1] and late[-1] < early[-1]
    for exact in (torch.zeros(3), torch.tensor([1., 0., 0.])):
        weights, component, _ = gradient_pursuit(exact, torch.eye(3))
        assert torch.isfinite(weights).all()
        torch.testing.assert_close(component, exact)
    try:
        gradient_pursuit(torch.full((3,), float("nan")), torch.eye(3))
    except ValueError:
        pass
    else:
        raise AssertionError("nonfinite pursuit did not fail")
    torch.testing.assert_close(final_positions(torch.tensor([[0, 1, 1], [1, 1, 0], [0, 0, 1]])),
                               torch.tensor([2, 1, 2]))

    class Toy(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.model = torch.nn.Module()
            self.model.layers = torch.nn.ModuleList([torch.nn.Identity()])

        def forward(self, x):
            return self.model.layers[0](x)

    model = Toy()
    vector = Vector(JLensConceptC(layers=(0,)), {0: {}}, {0: {"v": torch.tensor([[1., 0., 0.]])}})
    hidden = torch.zeros(2, 3, 3)
    mask = torch.tensor([[0, 1, 1], [1, 1, 1]])
    results = {}
    for coefficient in (0., 2., -2.):
        with concept_prefill(model, vector, mask, coefficient) as calls:
            results[coefficient] = model(hidden)
            assert calls == {0: 1}
            assert not model.model.layers[0]._forward_hooks
            torch.testing.assert_close(model(torch.zeros(2, 1, 3)), torch.zeros(2, 1, 3))
        assert not model.model.layers[0]._forward_hooks
    torch.testing.assert_close(results[0.], hidden)
    torch.testing.assert_close(results[2.], -results[-2.])
    torch.testing.assert_close(results[2.][:, :, 0], 2 * mask.float())
    with concept_prefill(model, vector, torch.ones(1, 1), 2.):
        torch.testing.assert_close(model(torch.zeros(1, 1, 3)), torch.tensor([[[2., 0., 0.]]]))
    try:
        with concept_prefill(model, vector, mask, 2.):
            raise RuntimeError("synthetic exception")
    except RuntimeError:
        pass
    assert not model.model.layers[0]._forward_hooks
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory) / "v.safetensors")
        vector.save(path)
        assert vector_sha256(vector) == vector_sha256(Vector.load(path))
    args = SimpleNamespace(method="j_lens_concept", model="tiny", dtype="float32", lens_file=None)
    metadata = {"method": args.method, "model": args.model, "dtype": args.dtype, "spec_sha256": concept_spec()[1],
                "implementation_sha256": implementation_hash()}
    validate_extraction_identity(args, metadata)
    for bad in ({**metadata, "method": "j_lens_swap"}, {**metadata, "spec_sha256": "old"},
                {**metadata, "model": "other"}, {**metadata, "dtype": "bfloat16"},
                {**metadata, "implementation_sha256": "stale"}):
        try:
            validate_extraction_identity(args, bad)
        except ValueError:
            pass
        else:
            raise AssertionError("stale cache accepted")
    print("J_LENS_CONCEPT_SELF_TEST_PASS nonnegative=true exact_fit=true zero_residual=true signed=true padding=true single_token=true cleanup=true reload=true cache_rejection=true")


def smoke(args):
    import experiment
    import walk

    torch.set_num_threads(4)
    if args.model != "wassname/qwen3-5lyr-tiny-random" or args.dtype != "float32":
        raise ValueError("concept smoke requires tiny random model and float32")
    root = experiment.experiment_dir(args.experiment_id)
    root.mkdir(parents=True, exist_ok=True)
    model, tokenizer = experiment.load_model(args)
    layers = walk.resolve_layers(model, None)
    prompt = tokenizer("A cat sits on a mat.", return_tensors="pt").to(args.device)
    jacobians = {layer: [] for layer in layers}
    with _activations(model, tuple(sorted({*layers, len(model.model.layers) - 1})), graph_root=min(layers)) as found:
        model.model(**prompt, use_cache=False)
        final = found[len(model.model.layers) - 1]
        n = final.shape[1]
        for dimension in range(final.shape[-1]):
            grads = torch.autograd.grad(final[..., dimension].sum(), [found[layer] for layer in layers], retain_graph=True)
            for layer, gradient in zip(layers, grads, strict=True):
                jacobians[layer].append(gradient.sum((0, 1)).detach().cpu() / (n * (n + 1) / 2))
    args.lens_file = root / "tiny_actual_jacobian.pt"
    torch.save({"J": {layer: torch.stack(rows) for layer, rows in jacobians.items()}, "n_prompts": 1,
                "source_layers": layers, "d_model": model.config.hidden_size}, args.lens_file)
    print(f"TINY_LENS_FIT actual_autograd=true n_prompts=1 layers={layers}")
    del model
    args.dev = True
    experiment.gpu_stage(args)
    model, tokenizer = experiment.load_model(args)
    vectors, _ = experiment.load_or_extract(args, root, model, tokenizer)
    encoded = tokenizer("A cat sits on a mat.", return_tensors="pt").to(args.device)
    with torch.inference_mode():
        bare = model(**encoded).logits
        with concept_prefill(model, vectors["+C"], encoded.attention_mask, 1.) as calls:
            steered = model(**encoded).logits
        restored = model(**encoded).logits
    assert not torch.equal(bare, steered)
    torch.testing.assert_close(bare, restored)
    assert all(count == 1 for count in calls.values())
    assert all(not model.model.layers[layer]._forward_hooks for layer in layers)
    print("CONCEPT_REAL_HOOK_CHECK changed_logits=true restored_logits=true calls_once=true removed=true")
    del model
    for command in (
        [sys.executable, "scripts/judge.py", "--experiment-id", args.experiment_id, "--profile", "dev", "--refresh"],
        [sys.executable, "scripts/export.py", "--experiment-id", args.experiment_id, "--profile", "dev"],
    ):
        print("COMMAND:", " ".join(command), flush=True)
        subprocess.run(command, check=True)
    metadata = json.loads((root / "extraction/metadata.json").read_text())
    assert metadata["vector_content_sha256"]["+C"] == metadata["vector_content_sha256"]["-C"]
    for layer in metadata["layers"].values():
        for d in layer["decomposition"]:
            assert min(d["weights_unit_dictionary"]) >= 0 and d["achieved_nonzero_count"] <= 16
            assert d["reconstruction_error"] == 0
    print(f"J_LENS_CONCEPT_PIPELINE_SMOKE_PASS id={args.experiment_id} actual_lens=true generation=true judge=true export=true public_outputs_untouched=true")
