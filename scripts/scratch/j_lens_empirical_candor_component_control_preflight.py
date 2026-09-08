"""Validate the frozen rank-two empirical-candor control without generation. PI/OpenAI Codex"""

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import torch
from steering_lite import Vector

from vjp_steering.j_lens_concept import (
    COMPONENT_PAIR_METHOD,
    COMPONENT_PAIR_VERSION,
    concept_patch,
    concept_prefill,
    concept_prefill_mask,
    implementation_hash,
    mask_metadata,
    random_gram_matched_component_vector,
    select_concept_layers,
)


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from judge import BEHAVIOR_TARGET, cache_key, judge_prompt, target_text
from vjp_steering.experiment import behavior_axis_direction
import vjp_steering.results as results_renderer

SOURCE_EXPERIMENT = "j-lens-behavior-components-target-ordered-source-v8"
SOURCE_SHA256 = "dd4e78e9c429e51e4fe2d4e70e0db28c96d5c4c218b5f317767393ac38883197"
LAYERS = tuple(range(13, 22))
ALPHA = 0.5
SEED = 20260909


class ToyPrefillModel(torch.nn.Module):
    def __init__(self, n_layers: int):
        super().__init__()
        self.model = SimpleNamespace(layers=torch.nn.ModuleList(torch.nn.Identity() for _ in range(n_layers)))

    def forward(self, hidden: torch.Tensor) -> torch.Tensor:
        for block in self.model.layers:
            hidden = block(hidden)
        return hidden


def vector_sha256(vector: Vector) -> str:
    digest = hashlib.sha256()
    for kind, tree in (("shared", vector.shared), ("stacked", vector.stacked)):
        for layer, tensors in sorted(tree.items()):
            for name, tensor in sorted(tensors.items()):
                value = tensor.detach().contiguous().cpu()
                digest.update(f"{kind}:{layer}:{name}:{value.dtype}:{tuple(value.shape)}".encode())
                digest.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def run(output: Path) -> None:
    source_root = ROOT / "outputs" / "experiments" / SOURCE_EXPERIMENT
    metadata = json.loads((source_root / "extraction" / "metadata.json").read_text())
    source = Vector.load(str(source_root / metadata["vector_files"]["+C"]))
    if source.cfg.method != COMPONENT_PAIR_METHOD:
        raise ValueError("frozen source is not a component-pair vector")
    if tuple(source.cfg.layers) != LAYERS:
        raise ValueError(f"frozen source layers changed: {source.cfg.layers}")
    if metadata["operator"] != COMPONENT_PAIR_VERSION:
        raise ValueError("frozen source operator changed")
    if vector_sha256(source) != SOURCE_SHA256:
        raise ValueError("frozen source hash changed")
    selected_source = select_concept_layers(source, LAYERS)
    if vector_sha256(selected_source) != SOURCE_SHA256:
        raise ValueError("component layer selection changed the frozen full-layer source")
    if any(int(source.shared[layer]["target_index"].item()) != 0 for layer in LAYERS):
        raise ValueError("frozen +C source no longer selects target index zero")

    control, geometry = random_gram_matched_component_vector(source, SEED)
    replay, replay_geometry = random_gram_matched_component_vector(source, SEED)
    control_hash = vector_sha256(control)
    if control_hash != vector_sha256(replay) or geometry != replay_geometry:
        raise ValueError("seeded component control is not deterministic")
    if control_hash == SOURCE_SHA256:
        raise ValueError("randomized control aliases frozen source")
    if any(int(control.shared[layer]["target_index"].item()) != 0 for layer in LAYERS):
        raise ValueError("control changed the source target order")
    if any(check["source_rank"] != 2 or check["control_rank"] != 2 for check in geometry.values()):
        raise ValueError("component control is not rank two")
    if max(check["gram_max_abs_error"] for check in geometry.values()) > 2e-6:
        raise ValueError("component control Gram matrix differs from source")
    if max(check["control_dual_identity_max_abs_error"] for check in geometry.values()) > 2e-5:
        raise ValueError("component control dual is invalid")

    generator = torch.Generator(device="cpu").manual_seed(0)
    synthetic_hidden = torch.randn((3, 5, source.shared[LAYERS[0]]["basis"].shape[1]), generator=generator)
    patch_difference = {}
    for layer in LAYERS:
        source_patched = concept_patch(synthetic_hidden, source, layer, ALPHA)
        control_patched = concept_patch(synthetic_hidden, control, layer, ALPHA)
        source_delta = source_patched - synthetic_hidden
        control_delta = control_patched - synthetic_hidden
        torch.testing.assert_close(concept_patch(synthetic_hidden, source, layer, 0.0), synthetic_hidden, rtol=0, atol=0)
        torch.testing.assert_close(concept_patch(synthetic_hidden, control, layer, 0.0), synthetic_hidden, rtol=0, atol=0)
        difference = source_delta - control_delta
        patch_difference[str(layer)] = {
            "source_patch_norm_median": source_delta.norm(dim=-1).median().item(),
            "control_patch_norm_median": control_delta.norm(dim=-1).median().item(),
            "patch_difference_norm_median": difference.norm(dim=-1).median().item(),
            "patch_difference_max_abs": difference.abs().max().item(),
        }
    if any(check["patch_difference_max_abs"] == 0 for check in patch_difference.values()):
        raise ValueError("Gram-matched control produced an identical operator patch")

    toy_model = ToyPrefillModel(max(LAYERS) + 1)
    toy_mask = torch.ones(synthetic_hidden.shape[:2], dtype=torch.bool)
    bare_hidden = toy_model(synthetic_hidden)
    with concept_prefill(toy_model, source, toy_mask, ALPHA) as source_calls:
        source_hook_hidden = toy_model(synthetic_hidden)
    with concept_prefill(toy_model, control, toy_mask, ALPHA) as control_calls:
        control_hook_hidden = toy_model(synthetic_hidden)
    with concept_prefill(toy_model, source, toy_mask, 0.0) as zero_calls:
        zero_hook_hidden = toy_model(synthetic_hidden)
    if not all(count == 1 for count in [*source_calls.values(), *control_calls.values(), *zero_calls.values()]):
        raise ValueError("prefill hook did not execute exactly once per component layer")
    torch.testing.assert_close(zero_hook_hidden, bare_hidden, rtol=0, atol=0)
    hook_difference = source_hook_hidden - control_hook_hidden
    if hook_difference.abs().max() == 0:
        raise ValueError("Gram-matched control produced an identical realized prefill-hook patch")

    attention_mask = torch.tensor([[1, 1, 1, 0], [1, 1, 1, 1]], dtype=torch.int64)
    input_ids = torch.zeros_like(attention_mask)
    patch_mask = concept_prefill_mask(None, input_ids, attention_mask, source)
    if not torch.equal(patch_mask, attention_mask.bool()):
        raise ValueError("component candidate no longer patches every attended prefill position")

    judge_row = {
        "run": "preflight",
        "method": COMPONENT_PAIR_METHOD,
        "side": "+C",
        "source_side": "+C",
        "behavior_target": "candidness",
        "vignette": "syco_bullshit_v2_leg_pnf_01",
        "prompt": "placeholder benchmark prompt",
        "bare": "bare response",
        "steered": "steered response",
        "source": "preflight",
    }
    control_judge_row = {**judge_row, "source": "preflight-control"}
    candidness_text = BEHAVIOR_TARGET["candidness"]
    if target_text(judge_row) != candidness_text or target_text(control_judge_row) != candidness_text:
        raise ValueError("candidate source and control do not use the candidness target")
    if candidness_text not in judge_prompt(judge_row, "AB") or candidness_text not in judge_prompt(control_judge_row, "BA"):
        raise ValueError("candidate source or control judge prompt omits candidness")
    legacy_row = {key: value for key, value in judge_row.items() if key not in ("source_side", "behavior_target")}
    if cache_key(judge_row, "AB", 0) == cache_key(legacy_row, "AB", 0):
        raise ValueError("candidate candidness target aliases historical +C judge cache")
    if behavior_axis_direction(judge_row["source_side"], judge_row["behavior_target"]) != -1:
        raise ValueError("candidate candidness endpoint uses the wrong acceptance direction")
    with tempfile.TemporaryDirectory() as directory:
        manifest_file = Path(directory) / "manifest.json"
        manifest_file.write_text(json.dumps({"candidate": {"source_side": "+C", "behavior_target": "candidness"}}))
        original_experiment_dir = results_renderer.experiment_dir
        results_renderer.experiment_dir = lambda _experiment_id: Path(directory)
        try:
            points = results_renderer._means(
                [{
                    "method": COMPONENT_PAIR_METHOD,
                    "C": ALPHA,
                    "side": "+C",
                    "effect": -0.1,
                    "off_axis_perturbation": 0.0,
                    "admissible": True,
                    "seed": 0,
                    "source_run": "candidate",
                }],
                methods=(COMPONENT_PAIR_METHOD,),
                method_seeds={COMPONENT_PAIR_METHOD: {0}},
            )
        finally:
            results_renderer.experiment_dir = original_experiment_dir
    if len(points) != 1 or not points[0]["accepted"]:
        raise ValueError("renderer rejects a +C source evaluated for candidness")

    candidate = {
        "source_experiment": SOURCE_EXPERIMENT,
        "source_side": "+C",
        "behavior_target": "candidness",
        "coefficient": ALPHA,
        "operator": COMPONENT_PAIR_VERSION,
        "layers": list(LAYERS),
        "application_mask": "all_attended_prefill_positions",
        "source_vector_sha256": SOURCE_SHA256,
        "control_vector_sha256": control_hash,
        "control_seed": SEED,
    }
    result = {
        "status": "EMPIRICAL_CANDOR_COMPONENT_CONTROL_PREFLIGHT_PASS",
        "candidate": candidate,
        "source_extraction": {
            "metadata_sha256": hashlib.sha256((source_root / "extraction" / "metadata.json").read_bytes()).hexdigest(),
            "implementation_sha256": metadata["implementation_sha256"],
        },
        "execution_implementation_sha256": implementation_hash(),
        "component_control_geometry": geometry,
        "computed_operator_patch_difference_on_fixed_hidden": patch_difference,
        "realized_prefill_hook_patch_difference_on_fixed_hidden": {
            "source_patch_norm_median": (source_hook_hidden - bare_hidden).norm(dim=-1).median().item(),
            "control_patch_norm_median": (control_hook_hidden - bare_hidden).norm(dim=-1).median().item(),
            "patch_difference_norm_median": hook_difference.norm(dim=-1).median().item(),
            "patch_difference_max_abs": hook_difference.abs().max().item(),
            "source_hook_calls": source_calls,
            "control_hook_calls": control_calls,
            "zero_hook_calls": zero_calls,
        },
        "mask": mask_metadata(patch_mask, attention_mask, "all_attended_prefill_positions"),
        "judge_contract": {
            "source_behavior_target": target_text(judge_row),
            "control_behavior_target": target_text(control_judge_row),
            "source_side": judge_row["source_side"],
            "source_cache_key": cache_key(judge_row, "AB", 0),
            "historical_plus_c_cache_key": cache_key(legacy_row, "AB", 0),
            "accepted_axis_direction": behavior_axis_direction(judge_row["source_side"], judge_row["behavior_target"]),
            "renderer_candidate_accepted": points[0]["accepted"],
        },
        "notes": [
            "The source and control share each layer Gram matrix, but this does not imply equal intervention patches.",
            "Computed and prefill-hook patch differences use deterministic hidden inputs, not model-generation evidence.",
            "A future generation manifest must save per-row realized source/control prefill patch diagnostics.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("EMPIRICAL_CANDOR_COMPONENT_CONTROL_PREFLIGHT_PASS")
    print(f"output={output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "slop/logs/20260908_j_lens_concept_repair/empirical-candor-component-control-preflight.json",
    )
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args().output)
