"""Replay saved v16 component vectors through the real patch and hook. — PI/OpenAI Codex"""

import argparse
import copy
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import torch
from steering_lite import Vector

from vjp_steering.j_lens_concept import concept_patch, concept_prefill


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXTRACTION = ROOT / "outputs/experiments/j-lens-persona-full-components-calibration-v16/extraction"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_hash(vector):
    digest = hashlib.sha256()
    for kind, tree in (("shared", vector.shared), ("stacked", vector.stacked)):
        for layer, tensors in sorted(tree.items()):
            for name, tensor in sorted(tensors.items()):
                value = tensor.detach().contiguous().cpu()
                digest.update(f"{kind}:{layer}:{name}:{value.dtype}:{tuple(value.shape)}".encode())
                digest.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def independent_exchange(hidden, basis, semantic_target, alpha):
    # Solve the two-component Gram system in float64 without the stored dual or production sorter.
    b = basis.double()
    h = hidden.double()
    coordinates = torch.linalg.solve(b @ b.T, (h @ b.T).T).T
    destination = coordinates.clone()
    other = 1 - semantic_target
    for row in range(len(coordinates)):
        if coordinates[row, semantic_target] < coordinates[row, other]:
            destination[row, semantic_target] = coordinates[row, other]
            destination[row, other] = coordinates[row, semantic_target]
    delta = alpha * ((destination - coordinates) @ b)
    return h + delta, coordinates, coordinates + alpha * (destination - coordinates), delta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction", type=Path, default=DEFAULT_EXTRACTION)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reproduce-tie-failure", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    torch.set_num_threads(1)
    started = time.monotonic()
    print("SHOULD: saved basis rows equal normalized positive/negative full signals; targets +C=positive and -C=negative", flush=True)
    print("SHOULD: real concept_patch matches independent Gram-solve coordinate exchange; alpha0 and already-ordered inputs are identity", flush=True)
    print("SHOULD: actual concept_prefill edits only attended first-forward positions; second forward is untouched", flush=True)
    print("SHOULD: wrong-target and no-op controls disagree on deliberately eligible inputs", flush=True)
    metadata_path = args.extraction / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    assert metadata["projection"] == "full_residual"
    assert metadata["method"] == "j_lens_concept_components"
    assert metadata["semantic_directions"] == {
        "+C": "put larger coordinate on positive component", "-C": "put larger coordinate on negative component",
    }
    vectors, provenance = {}, {}
    for side in ("+C", "-C"):
        path = args.extraction.parent / metadata["vector_files"][side]
        vector = Vector.load(str(path))
        assert vector.cfg.method == metadata["method"]
        assert list(vector.cfg.layers) == metadata["source_layers"]
        actual_hash = content_hash(vector)
        assert actual_hash == metadata["vector_content_sha256"][side]
        vectors[side] = vector
        provenance[side] = {"path": str(path.relative_to(ROOT)), "file_sha256": sha256(path),
                            "content_sha256": actual_hash, "config_dtype": str(vector.cfg.dtype)}
    implementation = ROOT / "src/vjp_steering/j_lens_concept.py"
    historical_source = subprocess.check_output(["git", "show", "c670930:src/vjp_steering/j_lens_concept.py"], cwd=ROOT)
    assert historical_source == implementation.read_bytes(), "actual module differs from task461 revision"
    geometry, results = [], []
    template = torch.tensor([[3., 1.], [1., 3.], [-1., -3.], [-3., -1.], [0., 0.]], dtype=torch.float64)
    for layer in metadata["source_layers"]:
        plus = vectors["+C"].shared[layer]
        minus = vectors["-C"].shared[layer]
        basis, dual = plus["basis"], plus["dual"]
        assert basis.dtype == dual.dtype == torch.float32
        assert torch.equal(basis, minus["basis"]) and torch.equal(dual, minus["dual"])
        decomposition = metadata["layers"][str(layer)]["decomposition"]
        row_errors = {}
        for index, name in enumerate(("positive", "negative")):
            signal = torch.tensor(decomposition[name]["full_signal"], dtype=torch.float32)
            row_errors[name] = float((basis[index] - signal / signal.norm()).abs().max())
            torch.testing.assert_close(basis[index], signal / signal.norm(), rtol=1e-6, atol=1e-7)
        b = basis.double()
        oracle_dual = torch.linalg.solve(b @ b.T, b)
        dual_error = float((dual.double() - oracle_dual).abs().max())
        torch.testing.assert_close(dual.double(), oracle_dual, rtol=1e-4, atol=1e-6)
        random = torch.randn(b.shape[1], generator=torch.Generator().manual_seed(461 + layer), dtype=torch.float64)
        orthogonal = random - (random @ oracle_dual.T) @ b
        orthogonal /= orthogonal.norm()
        geometry.append({"layer": layer, "basis_dtype": str(basis.dtype), "dual_dtype": str(dual.dtype),
                         "basis_row_max_errors": row_errors, "dual_max_error": dual_error,
                         "gram_identity_max_error": float((basis @ dual.T - torch.eye(2)).abs().max()),
                         "orthogonal_coordinate_max": float((orthogonal @ oracle_dual.T).abs().max()),
                         "basis_condition_number": float(torch.linalg.cond(b))})
        for side, target in (("+C", 0), ("-C", 1)):
            vector = vectors[side]
            assert int(vector.shared[layer]["target_index"]) == target
            for dtype in (torch.float32, torch.bfloat16):
                hidden = (template @ b + orthogonal).to(dtype)
                if not args.reproduce_tie_failure:
                    hidden[-1].zero_()
                for alpha in (0., 1., 2.):
                    expected, before, expected_coordinates, delta = independent_exchange(hidden, basis, target, alpha)
                    actual = concept_patch(hidden, vector, layer, alpha)
                    error = (actual.double() - expected).abs()
                    staged = hidden + delta.to(dtype)
                    rounding_bound = 2 * torch.finfo(dtype).eps * (hidden.double().abs() + delta.abs() + expected.abs()) + 1e-6
                    assert bool((error <= rounding_bound).all()), (layer, side, dtype, alpha, float(error.max()))
                    if dtype == torch.float32:
                        torch.testing.assert_close(actual.double(), expected, rtol=2e-5, atol=2e-6)
                    ordered = before[:, target] >= before[:, 1 - target]
                    if not torch.equal(actual[ordered], hidden[ordered]):
                        print("ORDERED_IDENTITY_FAILURE", json.dumps({
                            "layer": layer, "side": side, "dtype": str(dtype), "alpha": alpha,
                            "oracle_coordinates": before.tolist(),
                            "production_coordinates": (hidden.float() @ dual.T).tolist(),
                            "ordered_rows": ordered.tolist(),
                            "row_max_hidden_change": (actual.double() - hidden.double()).abs().max(-1).values.tolist(),
                        }), flush=True)
                    assert torch.equal(actual[ordered], hidden[ordered])
                    if alpha == 0:
                        assert torch.equal(actual, hidden)
                    recovered = actual.double() @ oracle_dual.T
                    row = {"layer": layer, "side": side, "dtype": str(dtype), "alpha": alpha,
                           "coordinates_before": before.tolist(), "coordinates_expected": expected_coordinates.tolist(),
                           "coordinates_actual": recovered.tolist(),
                           "max_output_error_vs_float64": float(error.max()),
                           "max_output_error_vs_staged_rounding": float((actual.double() - staged.double()).abs().max()),
                           "max_coordinate_error": float((recovered - expected_coordinates).abs().max()),
                           "max_error_to_rounding_bound_ratio": float((error / rounding_bound).max()),
                           "changed_values": int((actual != hidden).sum()), "already_ordered_identity": True}
                    results.append(row)
                expected, before, _, _ = independent_exchange(hidden, basis, target, 1.)
                eligible = before[:, target] < before[:, 1 - target]
                assert int(eligible.sum()) >= 2
                wrong_vector = copy.deepcopy(vector)
                wrong_vector.shared[layer]["target_index"] = torch.tensor(1 - target)
                wrong = concept_patch(hidden, wrong_vector, layer, 1.)
                noop = concept_patch(hidden, vector, layer, 0.)
                assert float((wrong.double() - expected).abs().max()) > 0.01
                assert float((noop.double()[eligible] - expected[eligible]).abs().max()) > 0.01
                hook_vector = copy.copy(vector)
                hook_vector.cfg = copy.copy(vector.cfg)
                hook_vector.cfg.layers = (layer,)
                model = SimpleNamespace(model=SimpleNamespace(layers=torch.nn.ModuleList(
                    [torch.nn.Identity() for _ in range(layer + 1)])))
                mask = torch.tensor([[True, True, False, True, False]])
                input_ = hidden.unsqueeze(0)
                with concept_prefill(model, hook_vector, mask, 1.) as calls:
                    first = model.model.layers[layer](input_)
                    second = model.model.layers[layer](input_)
                patch = concept_patch(hidden, vector, layer, 1.).unsqueeze(0)
                torch.testing.assert_close(first, torch.where(mask.unsqueeze(-1), patch, input_), rtol=0, atol=0)
                assert torch.equal(second, input_) and calls == {layer: 1}
        print("V16_LAYER_REPLAY_PASS", json.dumps(geometry[-1], sort_keys=True), flush=True)
    summary = {"decision": "ACTUAL_V16_COMPONENT_REPLAY_PASS", "patch_cases": len(results),
               "hook_cases": len(geometry) * 4, "saved_mapping_pass": True,
               "historical_module_byte_identity": True, "negative_controls_detected": True,
               "max_errors_by_dtype": {dtype: {key: max(r[key] for r in results if r["dtype"] == dtype)
                    for key in ("max_output_error_vs_float64", "max_output_error_vs_staged_rounding", "max_coordinate_error",
                                "max_error_to_rounding_bound_ratio")}
                    for dtype in ("torch.float32", "torch.bfloat16")}}
    output = {"summary": summary, "metadata_sha256": sha256(metadata_path), "vectors": provenance,
              "metadata_source_implementation_sha256": metadata["implementation_sha256"],
              "implementation_sha256": sha256(implementation), "script_sha256": sha256(Path(__file__)),
              "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "historical_revision": "c670930", "geometry": geometry, "cases": results,
              "fixture_coordinates": template.tolist(), "seed": "461 + layer", "device": "cpu",
              "torch": torch.__version__, "python": platform.python_version(),
              "seconds_after_import": time.monotonic() - started,
              "limitations": ["synthetic hidden states, not Qwen forward or behavioral generation",
                              "rounding-bound check does not require bitwise FP64 parity",
                              "fake identity block exercises actual hook registration, masking and removal only"],
              "author": "PI/OpenAI Codex"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        stream.write(json.dumps(output, indent=2) + "\n")
    print("V16_ACTUAL_REPLAY_COMPLETE", json.dumps(summary, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
