"""Focused checks and real tiny-pipeline smoke for J-space concept interventions. — PI/OpenAI Codex"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

import torch
from steering_lite import Vector

from vjp_steering.j_lens_concept import (
    COMPONENT_PAIR_METHOD, LEGACY_EXTRACTION_IMPLEMENTATION_SHA256,
    JLensConceptC, JLensConceptComponentsC, component_spec, component_target_coordinates,
    concept_patch, concept_prefill, concept_prefill_mask, concept_spec,
    extract_persona_contrast, final_positions, gradient_pursuit, implementation_hash,
    prefill_diagnostics, select_concept_layers, selected_span_projection, user_turn_mask,
    validate_component_pair,
)
from vjp_steering.vjp import _activations


def calibrate(args):
    import experiment
    import walk

    if args.method != COMPONENT_PAIR_METHOD:
        raise ValueError("target-ordered component calibration requires j_lens_concept_components")
    root = experiment.experiment_dir(args.experiment_id)
    if root.exists():
        raise ValueError(f"calibration output exists: {root}")
    if not args.source_experiment:
        raise ValueError("--source-experiment is required for component calibration")
    source = experiment.experiment_dir(args.source_experiment)
    source_metadata_path = source / "extraction/metadata.json"
    model, tokenizer = experiment.load_model(args)
    vectors, metadata = experiment.load_or_extract(args, source, model, tokenizer)
    extraction_dir = root / "extraction"
    extraction_dir.mkdir(parents=True)
    vector_files = {
        "+C": "extraction/plusC.safetensors",
        "-C": "extraction/minusC.safetensors",
    }
    for side, vector in vectors.items():
        vector.save(str(root / vector_files[side]))
    metadata = {
        **metadata,
        "vector_files": vector_files,
        "extraction_reused_from": args.source_experiment,
        "source_metadata_sha256": hashlib.sha256(source_metadata_path.read_bytes()).hexdigest(),
    }
    experiment.atomic_json(extraction_dir / "metadata.json", metadata)
    rows, cohort_hash = walk.read_cohort(experiment.DEV.cohort_size)
    prompts = walk.generation_inputs(tokenizer, rows)
    encoded = tokenizer(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to(args.device)
    final = final_positions(encoded.attention_mask)
    batch = torch.arange(len(rows), device=encoded.input_ids.device)
    observations = {"+C": [], "-C": []}
    with torch.inference_mode():
        bare_logits = model(**encoded).logits[batch, final].float()
    default_coefficients = (0., .25, .5, .75, 1., 1.25, 1.5, 2.)
    requested = {"+C": args.coefficients_plus, "-C": args.coefficients_minus}
    coefficient_grid = {
        side: (0., *(float(value) for value in requested[side].split(",") if value))
        if requested[side] else default_coefficients
        for side in ("+C", "-C")
    }
    for side in ("+C", "-C"):
        vector = vectors[side]
        mask = concept_prefill_mask(tokenizer, encoded.input_ids, encoded.attention_mask, vector)
        for coefficient in coefficient_grid[side]:
            before, diagnostics, handles = {}, {}, []

            def before_hook(layer):
                def capture(_module, _inputs, output):
                    hidden = output[0] if isinstance(output, tuple) else output
                    before[layer] = hidden.detach().clone()
                return capture

            def after_hook(layer):
                def capture(_module, _inputs, output):
                    hidden = output[0] if isinstance(output, tuple) else output
                    h = before[layer][mask].float()
                    actual = hidden[mask].float() - h
                    intended = concept_patch(h, vector, layer, coefficient) - h
                    dual = vector.shared[layer]["dual"].to(h)
                    clean_coordinates = h @ dual.T
                    patched_coordinates = (h + actual) @ dual.T
                    target_index = int(vector.shared[layer]["target_index"].item())
                    ordered_coordinates = component_target_coordinates(clean_coordinates, target_index)
                    target_coordinates = clean_coordinates + coefficient * (ordered_coordinates - clean_coordinates)
                    exchange_residual = patched_coordinates - target_coordinates
                    exchange_delta_norm = (target_coordinates - clean_coordinates).norm(dim=-1)
                    raw_norm = h.norm(dim=-1)
                    diagnostics[str(layer)] = {
                        "target_index": target_index,
                        "hidden_norms": raw_norm.tolist(),
                        "actual_patch_norms": actual.norm(dim=-1).tolist(),
                        "patch_residual_ratios": (actual.norm(dim=-1) / raw_norm).tolist(),
                        "clean_coordinates": clean_coordinates.tolist(),
                        "patched_coordinates": patched_coordinates.tolist(),
                        "coordinate_exchange_residual_norms": exchange_residual.norm(dim=-1).tolist(),
                        "coordinate_exchange_relative_errors": (
                            exchange_residual.norm(dim=-1) / exchange_delta_norm.clamp_min(1e-30)
                        ).tolist(),
                        "changed_hidden_fraction": (actual != 0).float().mean().item(),
                        "relative_patch_error": (
                            (actual - intended).norm(dim=-1) / intended.norm(dim=-1).clamp_min(1e-30)
                        ).tolist(),
                        "dtype": str(hidden.dtype),
                    }
                return capture

            try:
                for layer in vector.cfg.layers:
                    handles.append(model.model.layers[layer].register_forward_hook(before_hook(layer)))
                with concept_prefill(model, vector, mask, coefficient) as calls:
                    for layer in vector.cfg.layers:
                        handles.append(model.model.layers[layer].register_forward_hook(after_hook(layer)))
                    with torch.inference_mode():
                        logits = model(**encoded).logits[batch, final].float()
            finally:
                for handle in handles:
                    handle.remove()
            assert all(count == 1 for count in calls.values())
            if coefficient == 0:
                torch.testing.assert_close(logits, bare_logits, rtol=0, atol=0)
            log_probs, bare_log_probs = logits.log_softmax(-1), bare_logits.log_softmax(-1)
            top = logits[0].topk(10)
            side_slug = "plus" if side == "+C" else "minus"
            path = root / side_slug / f"c{experiment.coefficient_slug(coefficient)}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            records = experiment.extend_generation(
                path, rows, prompts, model, tokenizer, args, profile_name="dev", side=side,
                coefficient=coefficient, vector=vector,
            )
            health, reasons = walk.health(tokenizer, [record["text"] for record in records])
            kl = (bare_log_probs.exp() * (bare_log_probs - log_probs)).sum(-1)
            observation = {
                "coefficient": coefficient, "path": str(path.relative_to(root)),
                "health": health, "breakdown_reasons": reasons, "layers": diagnostics, "hook_calls": calls,
                "logit_delta_norm_mean": (logits - bare_logits).norm(dim=-1).mean().item(),
                "kl_bare_to_steered_mean": kl.mean().item(),
                "top_token_ids_first_prompt": top.indices.tolist(),
                "top_tokens_first_prompt": [tokenizer.decode([i]) for i in top.indices.tolist()],
                "top_logits_first_prompt": top.values.tolist(), "text_first_prompt": records[0]["text"],
            }
            observations[side].append(observation)
            experiment.atomic_json(root / "calibration.json", {
                "source_experiment": args.source_experiment,
                "source_metadata_sha256": metadata["source_metadata_sha256"],
                "vector_content_sha256": metadata["vector_content_sha256"], "cohort_sha256": cohort_hash,
                "cohort_size": len(rows),
                "coefficients": {side: list(values) for side, values in coefficient_grid.items()},
                "protocol": "nonnegative target-ordered coordinate exchange on all attended prefill positions",
                "observations": observations,
            })
            print(
                f"CONCEPT_CALIBRATION side={side} alpha={coefficient} "
                f"logit_delta_mean={observation['logit_delta_norm_mean']:.5g} "
                f"KL_mean={observation['kl_bare_to_steered_mean']:.5g} health={reasons} "
                f"text_first={records[0]['text']!r}",
                flush=True,
            )
    write_calibration_manifest(root, args, metadata, cohort_hash, observations)
    print(f"CONCEPT_CALIBRATION_COMPLETE id={args.experiment_id} cells={sum(map(len, observations.values()))}")


def write_calibration_manifest(root: Path, args, extraction: dict, cohort_hash: str, observations: dict) -> None:
    import experiment

    cells = {}
    grid = {}
    for side in ("+C", "-C"):
        nonzero = [observation for observation in observations[side] if observation["coefficient"] > 0]
        grid[side] = [observation["coefficient"] for observation in nonzero]
        cells[side] = {
            str(observation["coefficient"]): {
                "coefficient": observation["coefficient"],
                "path": observation["path"],
                "rows": observation["health"]["answers"],
                "health": observation["health"],
                "breakdown_reasons": observation["breakdown_reasons"],
                "realized_prefill": {
                    "coefficient": observation["coefficient"],
                    "final_token_kl_bare_to_steered_mean": observation["kl_bare_to_steered_mean"],
                    "final_token_logit_delta_norm_mean": observation["logit_delta_norm_mean"],
                    "layers": observation["layers"],
                },
            }
            for observation in nonzero
        }
    experiment.atomic_json(root / "manifest.json", {
        "schema": "j_lens_target_ordered_coordinate_exchange_v1",
        "experiment_id": args.experiment_id,
        "method": args.method,
        "date": time.strftime("%Y%m%d"),
        "profiles": {
            "dev": {"status": "DEV", "cohort_size": observations["+C"][0]["health"]["answers"], "generated": True},
        },
        "config": {
            "model": args.model,
            "dtype": args.dtype,
            "n_pairs": args.n_pairs,
            "batch_size": args.batch_size,
            "extract_batch_size": args.extract_batch_size,
            "max_length": args.max_length,
            "max_new_tokens": args.max_new_tokens,
            "j_lens_source": args.j_lens_source,
            "persona_direction": args.persona_direction,
        },
        "grid": grid,
        "boundaries": {
            "+C": {"meaning": "put larger coordinate on positive component", "trace": []},
            "-C": {"meaning": "put larger coordinate on negative component", "trace": []},
        },
        "bare": {
            "path": next(
                observation["path"] for observation in observations["+C"] if observation["coefficient"] == 0
            ),
        },
        "cohort_sha256": cohort_hash,
        "cells": cells,
        "extraction": extraction,
    })


def persona_prompt_control(args) -> None:
    import experiment
    import walk

    personas = {
        "+C": "sycophantic",
        "-C": (
            "bluntly candid, explicitly identifies false or incoherent premises, provides a useful "
            "correction, and does not insult or refuse"
        ),
    }
    if args.method != COMPONENT_PAIR_METHOD:
        raise ValueError("persona prompt control requires j_lens_concept_components")
    root = experiment.experiment_dir(args.experiment_id)
    if (root / "manifest.json").exists():
        raise ValueError(f"persona prompt control is complete: {root}")
    rows, cohort_hash = walk.read_cohort(experiment.DEV.cohort_size)
    run_spec = {
        "schema": "persona_prompt_control_v2",
        "experiment_id": args.experiment_id,
        "model": args.model,
        "dtype": args.dtype,
        "batch_size": args.batch_size,
        "max_new_tokens": args.max_new_tokens,
        "cohort_sha256": cohort_hash,
        "personas": personas,
    }
    run_spec_path = root / "run_spec.json"
    if root.exists():
        if not run_spec_path.exists() or json.loads(run_spec_path.read_text()) != run_spec:
            raise ValueError(f"persona prompt control partial output does not match this run: {root}")
    else:
        experiment.atomic_json(run_spec_path, run_spec)
    model, tokenizer = experiment.load_model(args)
    bare_path = root / "bare.jsonl"
    bare = experiment.extend_generation(
        bare_path, rows, walk.generation_inputs(tokenizer, rows), model, tokenizer, args,
        profile_name="dev", side="", coefficient=0.0, vector=None,
    )
    cells, observations = {"+C": {}, "-C": {}}, {}
    for side, directory in (("+C", "plus"), ("-C", "minus")):
        persona = personas[side]
        path = root / directory / "c1.jsonl"
        records = experiment.extend_generation(
            path, rows, walk.generation_inputs(tokenizer, rows, persona), model, tokenizer, args,
            profile_name="dev", side=side, coefficient=1.0, vector=None,
        )
        health, reasons = walk.health(tokenizer, [record["text"] for record in records])
        cells[side]["1.0"] = {
            "coefficient": 1.0,
            "path": str(path.relative_to(root)),
            "rows": len(records),
            "health": health,
            "breakdown_reasons": reasons,
        }
        observations[side] = {
            "persona": persona,
            "health": health,
            "breakdown_reasons": reasons,
            "changed_outputs_vs_bare": sum(
                record["text"] != control["text"] for record, control in zip(records, bare, strict=True)
            ),
            "text_first_prompt": records[0]["text"],
        }
    experiment.atomic_json(root / "control.json", {
        "experiment_id": args.experiment_id,
        "cohort_sha256": cohort_hash,
        "observations": observations,
    })
    experiment.atomic_json(root / "manifest.json", {
        "schema": "persona_prompt_control_v2",
        "experiment_id": args.experiment_id,
        "method": "persona_prompt_control",
        "date": time.strftime("%Y%m%d"),
        "profiles": {"dev": {"status": "DEV", "cohort_size": len(rows), "generated": True}},
        "config": {
            "model": args.model,
            "dtype": args.dtype,
            "batch_size": args.batch_size,
            "max_new_tokens": args.max_new_tokens,
        },
        "grid": {"+C": [1.0], "-C": [1.0]},
        "boundaries": {
            "+C": {"meaning": "literal sycophantic response instruction", "trace": []},
            "-C": {"meaning": "literal candid false-premise correction instruction", "trace": []},
        },
        "bare": {"path": str(bare_path.relative_to(root))},
        "cohort_sha256": cohort_hash,
        "cells": cells,
        "extraction": {
            "method": "persona_prompt_control",
            "model": args.model,
            "source_layers": [],
        },
    })
    print(
        f"PERSONA_PROMPT_CONTROL_COMPLETE id={args.experiment_id} "
        f"plus_changed={observations['+C']['changed_outputs_vs_bare']} "
        f"minus_changed={observations['-C']['changed_outputs_vs_bare']}",
        flush=True,
    )


def self_test():
    from experiment import concept_application_layers, concept_grid, validate_extraction_identity, vector_sha256

    dictionary = torch.tensor([[1., 0., 0.], [.6, .8, 0.], [0., 0., 1.]])
    signal = torch.tensor([.3, 1., -.5])
    w, component, support, errors = gradient_pursuit(signal, dictionary)
    assert (w >= 0).all() and w.count_nonzero() <= 16 and errors[-1] < signal.norm()
    torch.testing.assert_close(component, w @ dictionary)
    torch.testing.assert_close(signal, component + (signal - component))
    assert w[0] == 0 and w[1] > 0 and w[2] == 0
    two_steps, reconstruction, support, early = gradient_pursuit(torch.tensor([1., 1., 0.]), dictionary, k=2)
    refined, _, _, late = gradient_pursuit(torch.tensor([1., 1., 0.]), dictionary, k=16)
    projection = selected_span_projection(torch.tensor([1., 1., 0.]), dictionary, support)
    assert two_steps[0] > 0 and two_steps[1] > 0
    torch.testing.assert_close(projection, torch.tensor([1., 1., 0.]), atol=1e-6, rtol=1e-6)
    assert not torch.allclose(reconstruction, projection)
    assert late[-1] <= early[-1]
    assert all(after <= before for before, after in zip(late, late[1:]))
    for exact in (torch.zeros(3), torch.tensor([1., 0., 0.])):
        weights, component, support, _ = gradient_pursuit(exact, torch.eye(3))
        assert torch.isfinite(weights).all()
        torch.testing.assert_close(component, exact)
        torch.testing.assert_close(selected_span_projection(exact, torch.eye(3), support), exact)
    try:
        gradient_pursuit(torch.full((3,), float("nan")), torch.eye(3))
    except ValueError:
        pass
    else:
        raise AssertionError("nonfinite pursuit did not fail")
    torch.testing.assert_close(final_positions(torch.tensor([[0, 1, 1], [1, 1, 0], [0, 0, 1]])),
                               torch.tensor([2, 1, 2]))

    class ChatTokenizer:
        def apply_chat_template(self, _message, *, tokenize, add_generation_prompt, **_kwargs):
            assert tokenize
            return [1, 2, 3, 4, 5] if add_generation_prompt else [1, 2, 3]

    patch_mask = user_turn_mask(
        ChatTokenizer(),
        torch.tensor([[0, 1, 2, 3, 4, 5], [1, 2, 3, 4, 5, 0]]),
        torch.tensor([[0, 1, 1, 1, 1, 1], [1, 1, 1, 1, 1, 0]]),
    )
    torch.testing.assert_close(
        patch_mask,
        torch.tensor([[False, True, True, True, False, False], [True, True, True, False, False, False]]),
    )

    class Toy(torch.nn.Module):
        def __init__(self, n_layers=1):
            super().__init__()
            self.model = torch.nn.Module()
            self.model.layers = torch.nn.ModuleList(torch.nn.Identity() for _ in range(n_layers))

        def forward(self, x):
            for layer in self.model.layers:
                x = layer(x)
            return x

    model = Toy()
    vector = Vector(JLensConceptC(layers=(0,)), {0: {}}, {0: {"v": torch.tensor([[1., 0., 0.]])}})
    assert select_concept_layers(vector, (0,)).cfg.layers == (0,)
    component_basis = torch.tensor([[1., 0., 0.], [0., 1., 0.]])
    component_dual = torch.linalg.pinv(component_basis).T.contiguous()
    component_vector = Vector(
        JLensConceptComponentsC(layers=(0,)),
        {0: {
            "basis": component_basis,
            "dual": component_dual,
            "target_index": torch.tensor(0, dtype=torch.int64),
        }},
        {0: {}},
    )
    negative_component_vector = Vector(
        JLensConceptComponentsC(layers=(0,)),
        {0: {
            "basis": component_basis,
            "dual": component_dual,
            "target_index": torch.tensor(1, dtype=torch.int64),
        }},
        {0: {}},
    )
    validate_component_pair({"+C": component_vector, "-C": negative_component_vector})
    collapsed_basis = torch.tensor([[1., 0., 0.], [1., 0., 0.]])
    collapsed_dual = torch.linalg.pinv(collapsed_basis).T.contiguous()
    collapsed_vectors = {
        side: Vector(
            JLensConceptComponentsC(layers=(0,)),
            {0: {
                "basis": collapsed_basis,
                "dual": collapsed_dual,
                "target_index": torch.tensor(target_index, dtype=torch.int64),
            }},
            {0: {}},
        )
        for side, target_index in (("+C", 0), ("-C", 1))
    }
    try:
        validate_component_pair(collapsed_vectors)
    except ValueError:
        pass
    else:
        raise AssertionError("rank-deficient component basis was accepted")
    assert select_concept_layers(component_vector, (0,)).cfg.method == COMPONENT_PAIR_METHOD
    torch.testing.assert_close(
        concept_patch(torch.tensor([[2., 3., 4.]]), component_vector, 0, 1.),
        torch.tensor([[3., 2., 4.]]),
    )
    torch.testing.assert_close(
        concept_patch(torch.tensor([[3., 2., 4.]]), component_vector, 0, 1.),
        torch.tensor([[3., 2., 4.]]),
    )
    torch.testing.assert_close(
        concept_patch(torch.tensor([[3., 2., 4.]]), negative_component_vector, 0, 1.),
        torch.tensor([[2., 3., 4.]]),
    )
    torch.testing.assert_close(
        concept_patch(torch.tensor([[2., 3., 4.]]), negative_component_vector, 0, 1.),
        torch.tensor([[2., 3., 4.]]),
    )
    two_layer_states = {
        layer: {
            "basis": component_basis,
            "dual": component_dual,
            "target_index": torch.tensor(0, dtype=torch.int64),
        }
        for layer in (0, 1)
    }
    two_layer_vector = Vector(JLensConceptComponentsC(layers=(0, 1)), two_layer_states, {0: {}, 1: {}})
    two_layer_model = Toy(n_layers=2)
    with concept_prefill(two_layer_model, two_layer_vector, torch.ones(1, 1), 1.) as calls:
        two_layer_output = two_layer_model(torch.tensor([[[2., 3., 4.]]]))
    torch.testing.assert_close(two_layer_output, torch.tensor([[[3., 2., 4.]]]))
    assert calls == {0: 1, 1: 1}
    precise_basis = torch.tensor([[.78731, .21719, .57721], [.31415, .92653, .14142]])
    precise_dual = torch.linalg.pinv(precise_basis).T.contiguous()
    bf16_hidden = torch.tensor([[25.5, -13.25, 7.75]], dtype=torch.bfloat16)
    precise_coordinates = bf16_hidden.float() @ precise_dual.T
    precise_target_index = int(precise_coordinates[0].argmin().item())
    precise_vector = Vector(
        JLensConceptComponentsC(layers=(0,)),
        {0: {
            "basis": precise_basis,
            "dual": precise_dual,
            "target_index": torch.tensor(precise_target_index, dtype=torch.int64),
        }},
        {0: {}},
    )
    precise_patch = concept_patch(bf16_hidden, precise_vector, 0, 1.)
    precise_target = component_target_coordinates(precise_coordinates, precise_target_index)
    precise_delta = (precise_target - precise_coordinates) @ precise_basis
    torch.testing.assert_close(precise_patch, bf16_hidden + precise_delta.to(bf16_hidden), rtol=0, atol=0)
    rounded_basis = precise_basis.to(bf16_hidden).float()
    rounded_dual = precise_dual.to(bf16_hidden).float()
    rounded_coordinates = bf16_hidden.float() @ rounded_dual.T
    rounded_target = component_target_coordinates(rounded_coordinates, precise_target_index)
    rounded_patch = bf16_hidden + ((rounded_target - rounded_coordinates) @ rounded_basis).to(bf16_hidden)
    assert not torch.equal(precise_patch, rounded_patch)
    component_mask = concept_prefill_mask(
        ChatTokenizer(),
        torch.tensor([[0, 1, 2, 3, 4, 5]]),
        torch.tensor([[0, 1, 1, 1, 1, 1]]),
        component_vector,
    )
    torch.testing.assert_close(component_mask, torch.tensor([[False, True, True, True, True, True]]))
    assert component_spec()[0]["positive"] == "sycophantic agreement and flattery toward the user"
    assert concept_application_layers(SimpleNamespace(concept_layers="13,14"), (6, 13, 14)) == (13, 14)
    try:
        select_concept_layers(vector, (1,))
    except ValueError:
        pass
    else:
        raise AssertionError("invalid layer selection did not fail")
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
    with concept_prefill(model, component_vector, torch.ones(1, 1), 1.):
        torch.testing.assert_close(model(torch.tensor([[[2., 3., 4.]]])), torch.tensor([[[3., 2., 4.]]]))
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
        component_path = str(Path(directory) / "component.safetensors")
        component_vector.save(component_path)
        restored_component = Vector.load(component_path)
        assert vector_sha256(component_vector) == vector_sha256(restored_component)
        assert restored_component.cfg.method == COMPONENT_PAIR_METHOD
        assert tuple(restored_component.cfg.layers) == (0,)
        assert int(restored_component.shared[0]["target_index"].item()) == 0
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
    legacy = {**metadata, "implementation_sha256": LEGACY_EXTRACTION_IMPLEMENTATION_SHA256}
    validate_extraction_identity(args, legacy, allow_explicit_legacy_reuse=True)
    try:
        validate_extraction_identity(args, {**metadata, "implementation_sha256": "stale"}, allow_explicit_legacy_reuse=True)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown legacy cache accepted")
    assert concept_grid(SimpleNamespace(coefficients_plus="0.125,0.25,0.5", coefficients_minus="0.25")) == {
        "+C": [.125, .25, .5], "-C": [.25]}
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
    persona_vectors, persona_metadata = extract_persona_contrast(
        model, tokenizer, layers,
        positive_prompts=["Answer as someone who is sycophantic.\n\nA cat sits on a mat."],
        negative_prompts=["Answer as someone who is abrasive.\n\nA cat sits on a mat."],
        batch_size=1, max_length=64, lens_file=args.lens_file,
    )
    assert persona_metadata["representation_source"] == "matched_persona_prompt_difference"
    assert persona_metadata["layers"][str(layers[0])]["achieved_nonzero_count"] <= 16
    assert persona_vectors["+C"].stacked[layers[0]]["v"].norm() > 0
    full_vectors, full_metadata = extract_persona_contrast(
        model, tokenizer, layers,
        positive_prompts=["Answer as someone who is sycophantic.\n\nA cat sits on a mat."],
        negative_prompts=["Answer as someone who is abrasive.\n\nA cat sits on a mat."],
        batch_size=1, max_length=64, direction="full_residual", lens_file=args.lens_file,
    )
    assert full_metadata["projection"] == "full_residual"
    assert full_vectors["+C"].stacked[layers[0]]["v"].norm() > 0
    print(f"TINY_LENS_FIT actual_autograd=true persona_projection=true full_residual_control=true n_prompts=1 layers={layers}")
    del model
    args.dev = True
    experiment.gpu_stage(args)
    model, tokenizer = experiment.load_model(args)
    vectors, metadata = experiment.load_or_extract(args, root, model, tokenizer)
    if args.method == COMPONENT_PAIR_METHOD:
        for layer in layers:
            basis = vectors["+C"].shared[layer]["basis"]
            torch.testing.assert_close(basis.norm(dim=1), torch.ones(2))
            assert metadata["layers"][str(layer)]["component_basis_condition_number"] >= 1
    encoded = tokenizer("A cat sits on a mat.", return_tensors="pt").to(args.device)
    with torch.inference_mode():
        bare = model(**encoded).logits
        with concept_prefill(model, vectors["+C"], encoded.attention_mask, 1.) as plus_calls:
            steered_plus = model(**encoded).logits
        with concept_prefill(model, vectors["-C"], encoded.attention_mask, 1.) as minus_calls:
            steered_minus = model(**encoded).logits
        restored = model(**encoded).logits
    assert not torch.equal(bare, steered_plus)
    assert not torch.equal(bare, steered_minus)
    assert not torch.equal(steered_plus, steered_minus)
    torch.testing.assert_close(bare, restored)
    assert all(count == 1 for calls in (plus_calls, minus_calls) for count in calls.values())
    assert all(not model.model.layers[layer]._forward_hooks for layer in layers)
    diagnostics = {
        side: prefill_diagnostics(model, vectors[side], encoded.input_ids, encoded.attention_mask, 1.)
        for side in ("+C", "-C")
    }
    assert all(diagnostic["final_token_kl_bare_to_steered_mean"] > 0 for diagnostic in diagnostics.values())
    assert all(
        layer["changed_hidden_fraction"] > 0
        for diagnostic in diagnostics.values()
        for layer in diagnostic["layers"].values()
    )
    print(
        "CONCEPT_REAL_HOOK_CHECK both_directions_changed_logits=true distinct=true "
        "restored_logits=true calls_once=true removed=true diagnostics=true"
    )
    del model
    for command in (
        [sys.executable, "scripts/judge.py", "--experiment-id", args.experiment_id, "--profile", "dev", "--refresh"],
        [sys.executable, "scripts/export.py", "--experiment-id", args.experiment_id, "--profile", "dev"],
    ):
        print("COMMAND:", " ".join(command), flush=True)
        subprocess.run(command, check=True)
    metadata = json.loads((root / "extraction/metadata.json").read_text())
    assert metadata["vector_content_sha256"]["+C"] != metadata["vector_content_sha256"]["-C"]
    assert all(int(vectors["+C"].shared[layer]["target_index"].item()) == 0 for layer in layers)
    assert all(int(vectors["-C"].shared[layer]["target_index"].item()) == 1 for layer in layers)
    for layer in metadata["layers"].values():
        for d in layer["decomposition"]:
            assert min(d["weights_unit_dictionary"]) >= 0 and d["achieved_nonzero_count"] <= 16
            assert d["reconstruction_error"] == 0
    print(f"J_LENS_CONCEPT_PIPELINE_SMOKE_PASS id={args.experiment_id} actual_lens=true generation=true judge=true export=true public_outputs_untouched=true")
