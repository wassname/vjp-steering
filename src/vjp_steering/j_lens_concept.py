"""Sparse J-space concept decomposition and prefill interventions. — PI/OpenAI Codex"""

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import torch
from jaxtyping import Float, Int
from loguru import logger
from steering_lite import Vector
from steering_lite.config import SteeringConfig, register_config

from .vjp import _activations, _blocks, _load_j_lens


SPEC_PATH = Path(__file__).with_name("j_lens_concepts.json")
METHOD = "j_lens_concept"
COMPONENT_PAIR_METHOD = "j_lens_concept_components"
VERSION = "mean100-gp16-unit-dictionary-signed-add-v1"
COMPONENT_PAIR_VERSION = "mean100-gp16-reconstruction-target-ordered-coordinate-exchange-all-prefill-v8"
COMPONENT_PAIR_REPRESENTATION_SOURCE = "paired_nonnegative_gp16_components_target_ordered_exchange"
PERSONA_COMPONENT_PAIR_VERSION = "matched-persona-prefill-gp16-target-ordered-coordinate-exchange-v15"
PERSONA_COMPONENT_PAIR_REPRESENTATION_SOURCE = "matched_persona_prefill_gp16_components"
PERSONA_FULL_COMPONENT_PAIR_VERSION = "matched-persona-prefill-full-residual-target-ordered-coordinate-exchange-control-v16"
PERSONA_FULL_COMPONENT_PAIR_REPRESENTATION_SOURCE = "matched_persona_prefill_full_residual_components"
PERSONA_VERSION = "paired-persona-gp16-unit-dictionary-signed-add-v1"
PERSONA_FULL_RESIDUAL_VERSION = "paired-persona-full-residual-signed-add-control-v1"
LEGACY_EXTRACTION_IMPLEMENTATION_SHA256 = "fc65ee58b5f5b4fc5d952cd0439f0e0f84f7f2ede2e06e7d1bb2134ff0085d31"


@register_config
@dataclass
class JLensConceptC(SteeringConfig):
    method: str = METHOD


@register_config
@dataclass
class JLensConceptComponentsC(SteeringConfig):
    method: str = COMPONENT_PAIR_METHOD


def concept_spec() -> tuple[dict, str]:
    spec = json.loads(SPEC_PATH.read_text())
    assert len(spec["baseline"]) == len(set(spec["baseline"])) == 100
    digest = hashlib.sha256(json.dumps([VERSION, spec], sort_keys=True).encode()).hexdigest()
    return spec, digest


def component_spec() -> tuple[dict, str]:
    spec, _ = concept_spec()
    digest = hashlib.sha256(json.dumps([COMPONENT_PAIR_VERSION, spec], sort_keys=True).encode()).hexdigest()
    return spec, digest


def persona_component_spec(projection: str = "j_gp16") -> tuple[dict, str]:
    versions = {
        "j_gp16": PERSONA_COMPONENT_PAIR_VERSION,
        "full_residual": PERSONA_FULL_COMPONENT_PAIR_VERSION,
    }
    if projection not in versions:
        raise ValueError(f"unknown persona component projection {projection}")
    spec = {
        "positive_instruction": "Answer as someone who is sycophantic.",
        "negative_instruction": (
            "Answer as someone who is bluntly candid; states plainly when the named method, framework, "
            "factor, or threshold does not exist; does not invent properties, limits, or valid uses for "
            "fabricated methods; provides a useful correction; and does not insult or refuse."
        ),
        "baseline_instruction": "Answer the user directly and accurately in a clear, respectful style.",
        "instruction_validation_experiment": "j-lens-persona-prompt-control-exact-flaw-dev-v3",
        "fit_fraction": 0.8,
        "source_pool_count": 200,
        "expected_unique_sources": 65,
        "source_seed": 0,
    }
    digest = hashlib.sha256(
        json.dumps([versions[projection], spec], sort_keys=True).encode()
    ).hexdigest()
    return spec, digest


def implementation_hash() -> str:
    digest = hashlib.sha256()
    for path in (Path(__file__), Path(__file__).with_name("vjp.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def tensor_hash(tensor: torch.Tensor) -> str:
    return hashlib.sha256(tensor.detach().float().contiguous().cpu().numpy().tobytes()).hexdigest()


def tokenizer_content_hash(tokenizer) -> str:
    backend = json.loads(tokenizer.backend_tokenizer.to_str())
    backend.pop("padding", None)
    backend.pop("truncation", None)
    payload = {
        "backend": backend,
        "special_tokens_map": {key: str(value) for key, value in tokenizer.special_tokens_map.items()},
        "chat_template": tokenizer.chat_template,
        "padding_side": tokenizer.padding_side,
        "truncation_side": tokenizer.truncation_side,
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def select_concept_layers(vector: Vector, layers: tuple[int, ...]) -> Vector:
    available = tuple(vector.cfg.layers)
    if not layers or len(set(layers)) != len(layers) or any(layer not in available for layer in layers):
        raise ValueError(f"invalid concept application layers={layers}; available={available}")
    cfg = type(vector.cfg)(layers=layers)
    cfg.dtype = vector.cfg.dtype
    return Vector(
        cfg,
        {layer: vector.shared.get(layer, {}) for layer in layers},
        {layer: vector.stacked[layer] for layer in layers},
    )


def final_positions(mask: Int[torch.Tensor, "b s"]) -> Int[torch.Tensor, "b"]:
    positions = torch.arange(mask.shape[1], device=mask.device).expand_as(mask)
    last = positions.masked_fill(~mask.bool(), -1).max(dim=1).values
    assert (last >= 0).all(), "empty prompt"
    return last


def user_turn_mask(tokenizer, input_ids: Int[torch.Tensor, "b s"],
                   attention_mask: Int[torch.Tensor, "b s"]) -> Int[torch.Tensor, "b s"]:
    message = [{"role": "user", "content": ""}]
    user_turn = tokenizer.apply_chat_template(message, tokenize=True, add_generation_prompt=False)
    full_prompt = tokenizer.apply_chat_template(
        message, tokenize=True, add_generation_prompt=True, enable_thinking=False,
    )
    user_turn = user_turn["input_ids"] if isinstance(user_turn, Mapping) else user_turn
    full_prompt = full_prompt["input_ids"] if isinstance(full_prompt, Mapping) else full_prompt
    if full_prompt[:len(user_turn)] != user_turn or len(full_prompt) == len(user_turn):
        raise ValueError("chat template does not have a fixed assistant-generation suffix")
    assistant_suffix_length = len(full_prompt) - len(user_turn)
    final = final_positions(attention_mask)
    end = final + 1 - assistant_suffix_length
    positions = torch.arange(input_ids.shape[1], device=input_ids.device).expand_as(input_ids)
    mask = attention_mask.bool() & (positions < end[:, None])
    if not mask.any(dim=1).all():
        raise ValueError("empty user turn")
    return mask


def final_prompt_mask(attention_mask: Int[torch.Tensor, "b s"]) -> Int[torch.Tensor, "b s"]:
    final = final_positions(attention_mask)
    mask = torch.zeros_like(attention_mask, dtype=torch.bool)
    mask[torch.arange(mask.shape[0], device=mask.device), final] = True
    if not torch.equal(mask.sum(dim=1), torch.ones_like(final)):
        raise ValueError("final-prompt mask must select exactly one position per row")
    if (mask & ~attention_mask.bool()).any():
        raise ValueError("final-prompt mask selected padding")
    return mask


def mask_metadata(mask: Int[torch.Tensor, "b s"], attention_mask: Int[torch.Tensor, "b s"],
                  application_mask: str) -> dict:
    final = final_positions(attention_mask)
    selected = mask.sum(dim=1)
    return {
        "application_mask": application_mask,
        "rows": mask.shape[0],
        "selected_positions_per_row": selected.tolist(),
        "all_rows_select_one": bool(torch.equal(selected, torch.ones_like(final))),
        "selected_final_positions": bool(mask[torch.arange(mask.shape[0], device=mask.device), final].all()),
        "selected_padding_positions": int((mask & ~attention_mask.bool()).sum()),
    }


def concept_prefill_mask(tokenizer, input_ids: Int[torch.Tensor, "b s"],
                         attention_mask: Int[torch.Tensor, "b s"], vector: Vector,
                         application_mask: str = "user_turn") -> Int[torch.Tensor, "b s"]:
    if vector.cfg.method == COMPONENT_PAIR_METHOD:
        if application_mask != "user_turn":
            raise ValueError("component pairs only support user_turn application")
        return attention_mask.bool()
    if application_mask == "user_turn":
        return user_turn_mask(tokenizer, input_ids, attention_mask)
    if application_mask == "final_prompt":
        return final_prompt_mask(attention_mask)
    raise ValueError(f"unknown concept application mask: {application_mask}")


# PI/OpenAI Codex: follows TransformerLens' paper-matching gradient-pursuit update.
@torch.no_grad()
def gradient_pursuit(
    signal: Float[torch.Tensor, "d"], dictionary: Float[torch.Tensor, "v d"], k: int = 16,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[float]]:
    if not torch.isfinite(signal).all() or not torch.isfinite(dictionary).all():
        raise ValueError("nonfinite pursuit input")
    if not torch.allclose(dictionary.norm(dim=1), torch.ones(dictionary.shape[0], device=dictionary.device)):
        raise ValueError("gradient pursuit requires unit dictionary rows")
    weights = torch.zeros(dictionary.shape[0], device=dictionary.device)
    selected, coordinates, errors = [], signal.new_zeros(0), []
    residual = signal.float()
    correlation_tolerance = torch.finfo(torch.float32).eps ** 0.5 * signal.float().norm()
    for _ in range(k):
        scores = dictionary.float() @ residual
        if selected:
            scores[selected] = float("-inf")
        candidate = int(scores.argmax())
        if scores[candidate] <= correlation_tolerance:
            break
        selected.append(candidate)
        atoms = dictionary[selected].float().T
        coordinates = torch.cat([coordinates, coordinates.new_zeros(1)])
        direction = atoms.T @ residual
        change = atoms @ direction
        denominator = change.square().sum()
        if denominator == 0:
            break
        step = (change @ residual) / denominator
        previous_error = residual.square().sum()
        for _ in range(21):
            updated = (coordinates + step * direction).clamp_min(0)
            updated_residual = signal.float() - atoms @ updated
            if updated_residual.square().sum() <= previous_error:
                coordinates, residual = updated, updated_residual
                break
            step /= 2
        errors.append(residual.norm().item())
    weights[selected] = coordinates
    selected_support = torch.tensor(selected, dtype=torch.long, device=dictionary.device)
    return weights, weights @ dictionary, selected_support, errors


def selected_span_projection(signal: torch.Tensor, dictionary: torch.Tensor,
                             selected_support: torch.Tensor) -> torch.Tensor:
    if not selected_support.numel():
        return torch.zeros_like(signal)
    atoms = dictionary[selected_support].float().T
    return atoms @ (torch.linalg.pinv(atoms) @ signal.float())


def component_target_coordinates(coordinates: torch.Tensor, target_index: int) -> torch.Tensor:
    high = coordinates.max(dim=-1).values
    low = coordinates.min(dim=-1).values
    if target_index == 0:
        return torch.stack((high, low), dim=-1)
    if target_index == 1:
        return torch.stack((low, high), dim=-1)
    raise ValueError(f"component target index must be 0 or 1, got {target_index}")


def validate_component_pair(vectors: dict[str, Vector]) -> None:
    plus, minus = vectors["+C"], vectors["-C"]
    if plus.cfg.method != COMPONENT_PAIR_METHOD or minus.cfg.method != COMPONENT_PAIR_METHOD:
        raise ValueError("invalid component-pair method")
    if tuple(plus.cfg.layers) != tuple(minus.cfg.layers):
        raise ValueError("component-pair layers differ")
    for layer in plus.cfg.layers:
        plus_state, minus_state = plus.shared[layer], minus.shared[layer]
        if int(plus_state["target_index"].item()) != 0 or int(minus_state["target_index"].item()) != 1:
            raise ValueError(f"component targets differ from +C=0 and -C=1 at layer {layer}")
        basis, dual = plus_state["basis"].float(), plus_state["dual"].float()
        if not torch.equal(plus_state["basis"], minus_state["basis"]):
            raise ValueError(f"component bases differ between directions at layer {layer}")
        if not torch.equal(plus_state["dual"], minus_state["dual"]):
            raise ValueError(f"component duals differ between directions at layer {layer}")
        singular_values = torch.linalg.svdvals(basis)
        rank_tolerance = singular_values[0] * max(basis.shape) * torch.finfo(basis.dtype).eps
        if singular_values.shape != (2,) or singular_values[-1] <= rank_tolerance:
            raise ValueError(f"component basis is numerically rank deficient at layer {layer}")
        torch.testing.assert_close(
            basis @ dual.T,
            torch.eye(2, device=basis.device),
            rtol=1e-4,
            atol=1e-5,
        )


def concept_patch(hidden: torch.Tensor, vector: Vector, layer: int, coefficient: float) -> torch.Tensor:
    if vector.cfg.method == COMPONENT_PAIR_METHOD:
        shared = vector.shared[layer]
        basis = shared["basis"].to(device=hidden.device)
        dual = shared["dual"].to(device=hidden.device)
        coordinates = torch.einsum("...d,kd->...k", hidden.float(), dual.float())
        target_index = int(shared["target_index"].item())
        target_coordinates = component_target_coordinates(coordinates, target_index)
        delta = torch.einsum("...k,kd->...d", target_coordinates - coordinates, basis.float())
        return hidden + (coefficient * delta).to(hidden)
    delta = vector.stacked[layer]["v"].sum(0).to(hidden)
    return hidden + coefficient * delta


@contextmanager
def concept_prefill(model, vector: Vector, mask: torch.Tensor, coefficient: float):
    handles = []
    calls = {layer: 0 for layer in vector.cfg.layers}

    def hook(layer):
        def apply(_module, _inputs, output):
            calls[layer] += 1
            hidden = output[0] if isinstance(output, tuple) else output
            patched = concept_patch(hidden, vector, layer, coefficient)
            edited = torch.where(mask.to(device=hidden.device).bool().unsqueeze(-1), patched, hidden)
            handles_by_layer[layer].remove()
            return (edited, *output[1:]) if isinstance(output, tuple) else edited
        return apply

    handles_by_layer = {}
    try:
        for layer in vector.cfg.layers:
            handle = _blocks(model)[layer].register_forward_hook(hook(layer))
            handles_by_layer[layer] = handle
            handles.append(handle)
        yield calls
    finally:
        for handle in handles:
            handle.remove()


@torch.inference_mode()
def prefill_diagnostics(model, vector: Vector, input_ids: torch.Tensor, attention_mask: torch.Tensor,
                        coefficient: float, patch_mask: torch.Tensor | None = None) -> dict:
    """Measure the actual prompt patch and final-token distribution change for one cell."""
    mask = attention_mask.bool() if patch_mask is None else patch_mask.bool()
    batch = torch.arange(mask.shape[0], device=mask.device)
    final = final_positions(attention_mask)
    bare_logits = model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False).logits[batch, final].float()
    before, summaries, handles = {}, {}, []

    def capture_before(layer):
        def hook(_module, _inputs, output):
            hidden = output[0] if isinstance(output, tuple) else output
            before[layer] = hidden.detach().clone()
        return hook

    def capture_after(layer):
        def hook(_module, _inputs, output):
            hidden = output[0] if isinstance(output, tuple) else output
            original = before.pop(layer)[mask].float()
            actual = hidden[mask].float() - original
            intended = concept_patch(original, vector, layer, coefficient) - original
            ratio = actual.norm(dim=-1) / original.norm(dim=-1)
            summary = {
                "patch_residual_ratio_median": ratio.median().item(),
                "patch_residual_ratio_p90": ratio.quantile(.9).item(),
                "actual_patch_norm_median": actual.norm(dim=-1).median().item(),
                "relative_patch_error_median": (
                    (actual - intended).norm(dim=-1) / intended.norm(dim=-1).clamp_min(1e-30)
                ).median().item(),
                "changed_hidden_fraction": (actual != 0).float().mean().item(),
                "dtype": str(hidden.dtype),
            }
            if vector.cfg.method == COMPONENT_PAIR_METHOD:
                dual = vector.shared[layer]["dual"].to(original)
                clean_coordinates = original @ dual.T
                patched_coordinates = (original + actual) @ dual.T
                target_index = int(vector.shared[layer]["target_index"].item())
                ordered_coordinates = component_target_coordinates(clean_coordinates, target_index)
                target_coordinates = clean_coordinates + coefficient * (ordered_coordinates - clean_coordinates)
                exchange_residual = patched_coordinates - target_coordinates
                exchange_delta_norm = (target_coordinates - clean_coordinates).norm(dim=-1)
                summary["clean_coordinate_medians"] = clean_coordinates.median(dim=0).values.tolist()
                summary["patched_coordinate_medians"] = patched_coordinates.median(dim=0).values.tolist()
                summary["coordinate_exchange_residual_norm_median"] = exchange_residual.norm(dim=-1).median().item()
                summary["coordinate_exchange_relative_error_median"] = (
                    exchange_residual.norm(dim=-1) / exchange_delta_norm.clamp_min(1e-30)
                ).median().item()
            summaries[str(layer)] = summary
        return hook

    try:
        for layer in vector.cfg.layers:
            handles.append(_blocks(model)[layer].register_forward_hook(capture_before(layer)))
        with concept_prefill(model, vector, mask, coefficient) as calls:
            for layer in vector.cfg.layers:
                handles.append(_blocks(model)[layer].register_forward_hook(capture_after(layer)))
            steered_logits = model(
                input_ids=input_ids, attention_mask=attention_mask, use_cache=False,
            ).logits[batch, final].float()
    finally:
        for handle in handles:
            handle.remove()
    assert not before
    assert all(count == 1 for count in calls.values())
    if coefficient == 0:
        torch.testing.assert_close(steered_logits, bare_logits, rtol=0, atol=0)
    bare_log_probs = bare_logits.log_softmax(-1)
    steered_log_probs = steered_logits.log_softmax(-1)
    kl = (bare_log_probs.exp() * (bare_log_probs - steered_log_probs)).sum(-1)
    return {
        "coefficient": coefficient,
        "final_token_kl_bare_to_steered_mean": kl.mean().item(),
        "final_token_logit_delta_norm_mean": (steered_logits - bare_logits).norm(dim=-1).mean().item(),
        "layers": summaries,
    }


@torch.inference_mode()
def residuals(model, tokenizer, prompts, layers, batch_size, max_length):
    found_rows = {layer: [] for layer in layers}
    tokens = []
    for start in range(0, len(prompts), batch_size):
        encoded = tokenizer(prompts[start:start + batch_size], return_tensors="pt", padding=True,
                            add_special_tokens=False).to(next(model.parameters()).device)
        if encoded.input_ids.shape[1] > max_length:
            raise ValueError("concept/diagnostic prompt truncation")
        last = final_positions(encoded.attention_mask)
        with _activations(model, layers) as found:
            model.model(**encoded, use_cache=False)
        for layer in layers:
            found_rows[layer].append(found[layer][torch.arange(len(last), device=last.device), last].float().cpu())
        for ids, mask, position in zip(encoded.input_ids, encoded.attention_mask, last, strict=True):
            tokens.append({"input_ids": ids.tolist(), "attention_mask": mask.tolist(),
                           "final_position": position.item(), "final_token_id": ids[position].item()})
    return {layer: torch.cat(values) for layer, values in found_rows.items()}, tokens


@torch.inference_mode()
def attended_residuals(model, tokenizer, prompts, layers, batch_size, max_length):
    found_rows = {layer: [] for layer in layers}
    for start in range(0, len(prompts), batch_size):
        encoded = tokenizer(
            prompts[start:start + batch_size], return_tensors="pt", padding=True, add_special_tokens=False,
        ).to(next(model.parameters()).device)
        if encoded.input_ids.shape[1] > max_length:
            raise ValueError("attended-residual prompt truncation")
        with _activations(model, layers) as found:
            model.model(**encoded, use_cache=False)
        mask = encoded.attention_mask.bool()
        for layer in layers:
            found_rows[layer].extend(
                found[layer][index, row_mask].float().cpu()
                for index, row_mask in enumerate(mask)
            )
    return found_rows


def _activity(hidden, dictionary, pair_ids, null_ids, raw_norms):
    scores = hidden @ dictionary.T
    pair_scores = scores[:, pair_ids]
    null_scores = scores[:, null_ids]
    raw_scores = scores * raw_norms
    return {
        "raw_pair_scores": raw_scores[:, pair_ids].tolist(),
        "raw_vocabulary_ranks": (1 + (raw_scores.unsqueeze(1) > raw_scores[:, pair_ids].unsqueeze(-1)).sum(-1)).tolist(),
        "unit_scores": pair_scores.tolist(),
        "cosines": (pair_scores / hidden.norm(dim=-1, keepdim=True)).tolist(),
        "positive": (pair_scores > 0).tolist(),
        "vocabulary_ranks": (1 + (scores.unsqueeze(1) > pair_scores.unsqueeze(-1)).sum(-1)).tolist(),
        "null_token_unit_scores": null_scores.tolist(),
        "null_percentiles": (null_scores.unsqueeze(1) <= pair_scores.unsqueeze(-1)).float().mean(-1).tolist(),
        "pair_pseudoinverse_coordinates": (hidden @ torch.linalg.pinv(dictionary[pair_ids])).tolist(),
    }


@torch.inference_mode()
def extract_concept(
    model, tokenizer, layers, *, batch_size, max_length, dev_prompts, lens_file=None,
    separate_components: bool = False,
):
    spec, spec_hash = component_spec() if separate_components else concept_spec()
    operator = COMPONENT_PAIR_VERSION if separate_components else VERSION
    texts = [spec["positive"], spec["negative"], *spec["baseline"]]
    prompts = [tokenizer.apply_chat_template([{"role": "user", "content": f"Tell me about {text}"}],
               tokenize=False, add_generation_prompt=True, enable_thinking=False) for text in texts]
    logger.info("concept extraction spec={} layers={} final_prompt_token=true", spec_hash, layers)
    logger.info("concept extraction demo={} ", prompts[0])
    hidden, token_records = residuals(model, tokenizer, prompts + dev_prompts, layers, batch_size, max_length)
    lens_file, checkpoint = _load_j_lens(model, layers, lens_file)
    device = next(model.parameters()).device
    unembedding = model.lm_head.weight.detach().float()
    pair_ids = []
    for word in ("abrasive", "flattering"):
        ids = tokenizer(" " + word, add_special_tokens=False).input_ids
        if len(ids) != 1:
            raise ValueError(f"old lexical diagnostic requires one token: {word} {ids}")
        pair_ids.append(ids[0])
    null_ids = torch.randperm(unembedding.shape[0], generator=torch.Generator().manual_seed(0))
    null_ids = [i for i in null_ids.tolist() if i not in pair_ids][:128]
    shared_states = {"+C": {}, "-C": {}}
    stacked_states = {"+C": {}, "-C": {}}
    layer_meta = {}
    for layer in layers:
        raw = unembedding @ checkpoint["J"][layer].float().to(device)
        norms = raw.norm(dim=-1)
        if not (norms > 0).all():
            raise ValueError(f"zero J-lens row at layer {layer}")
        dictionary = raw / norms[:, None]
        del raw
        hs = hidden[layer].to(device)
        baseline = hs[2:102].mean(0)
        components, decomposition = [], []
        for index in (0, 1):
            concept = hs[index] - baseline
            weights, reconstruction, selected_support, errors = gradient_pursuit(concept, dictionary, 16)
            projection = selected_span_projection(concept, dictionary, selected_support)
            component = reconstruction
            active = weights.nonzero().flatten()
            remainder = concept - component
            components.append(component)
            decomposition.append({
                "concept": texts[index], "selected_count": selected_support.numel(),
                "selected_ids": selected_support.tolist(),
                "selected_tokens": [tokenizer.decode([i]) for i in selected_support.tolist()],
                "achieved_nonzero_count": active.numel(), "active_ids": active.tolist(),
                "active_tokens": [tokenizer.decode([i]) for i in active.tolist()],
                "weights_unit_dictionary": weights[active].tolist(), "raw_row_norms": norms[active].tolist(),
                "concept_norm": concept.norm().item(), "j_norm": component.norm().item(),
                "reconstruction_norm": reconstruction.norm().item(), "projection_norm": projection.norm().item(),
                "remainder_norm": remainder.norm().item(), "error_history": errors,
                "j_remainder_dot": (component @ remainder).item(),
                "reconstruction_projection_cosine": torch.nn.functional.cosine_similarity(
                    reconstruction, projection, dim=0,
                ).item(),
                "reconstruction_error": (concept - component - remainder).norm().item(),
                "concept_vector": concept.tolist(), "reconstruction_vector": reconstruction.tolist(),
                "j_vector": component.tolist(), "remainder": remainder.tolist(),
                "concept_sha256": tensor_hash(concept), "reconstruction_sha256": tensor_hash(reconstruction),
                "j_sha256": tensor_hash(component), "remainder_sha256": tensor_hash(remainder),
            })
        contrast = components[0] - components[1]
        neutral_residual_norm = hs[2:102].norm(dim=-1).mean()
        if separate_components:
            if any(not torch.isfinite(component).all() or component.norm() <= 1e-6 * hs[0].norm() for component in components):
                raise ValueError(f"zero, nonfinite, or numerically unresolved J component at layer {layer}")
            basis = torch.stack([component / component.norm() for component in components]).float().cpu()
            dual = torch.linalg.pinv(basis).T.contiguous()
            singular_values = torch.linalg.svdvals(basis)
            if not torch.isfinite(dual).all() or singular_values[-1] <= 0:
                raise ValueError(f"invalid concept-component coordinate basis at layer {layer}")
            shared_states["+C"][layer] = {
                "basis": basis, "dual": dual, "target_index": torch.tensor(0, dtype=torch.int64),
            }
            shared_states["-C"][layer] = {
                "basis": basis, "dual": dual, "target_index": torch.tensor(1, dtype=torch.int64),
            }
            stacked_states["+C"][layer] = {}
            stacked_states["-C"][layer] = {}
        else:
            if not torch.isfinite(contrast).all() or contrast.norm() <= 1e-6 * max(c.norm() for c in components):
                raise ValueError(f"zero, nonfinite, or numerically unresolved concept contrast at layer {layer}")
            direction = (contrast / contrast.norm()).cpu().unsqueeze(0)
            shared_states["+C"][layer] = {}
            shared_states["-C"][layer] = {}
            stacked_states["+C"][layer] = {"v": direction}
            stacked_states["-C"][layer] = {"v": direction}
        layer_meta[str(layer)] = {
            "decomposition": decomposition, "contrast_norm": contrast.norm().item(),
            "component_cosine": torch.nn.functional.cosine_similarity(components[0], components[1], dim=0).item(),
            "component_basis_norms": basis.norm(dim=1).tolist() if separate_components else None,
            "component_basis_singular_values": singular_values.tolist() if separate_components else None,
            "component_basis_condition_number": (
                (singular_values[0] / singular_values[-1]).item() if separate_components else None
            ),
            "baseline_mean": baseline.tolist(), "baseline_mean_sha256": tensor_hash(baseline),
            "neutral_final_token_residual_norm_mean": neutral_residual_norm.item(),
            "pair_unit_cosine": (dictionary[pair_ids[0]] @ dictionary[pair_ids[1]]).item(),
            "pair_singular_values": torch.linalg.svdvals(dictionary[pair_ids]).tolist(),
            "baseline_activity": _activity(hs[2:102], dictionary, pair_ids, null_ids, norms),
            "dev_activity": _activity(hs[102:], dictionary, pair_ids, null_ids, norms),
        }
        logger.info("concept layer={} j_norms={} remainder_norms={} contrast_norm={:.4f}", layer,
                    [d["j_norm"] for d in decomposition], [d["remainder_norm"] for d in decomposition], contrast.norm())
    cfg_type = JLensConceptComponentsC if separate_components else JLensConceptC
    vectors = {
        side: Vector(cfg_type(layers=layers), shared_states[side], stacked_states[side])
        for side in ("+C", "-C")
    }
    if separate_components:
        validate_component_pair(vectors)
    return vectors, {
        "operator": operator,
        "representation_source": COMPONENT_PAIR_REPRESENTATION_SOURCE if separate_components else "concept_mean100",
        "spec_sha256": spec_hash,
        "implementation_sha256": implementation_hash(),
        "spec": spec, "source_layers": list(layers),
        "equation": (
            "h_all_prefill + alpha * V * (target_sort(V^dagger h_all_prefill) - V^dagger h_all_prefill)"
            if separate_components else "h_user_turn + C * unit(j_positive - j_negative)"
        ),
        "extraction_mask": "final_real_chat_prompt_token",
        "application_mask": "all_attended_prefill_positions" if separate_components else "user_turn_including_chat_delimiters",
        "activity_mask": "final_real_chat_prompt_token_only_not_all_patched_positions",
        "dictionary_normalization": "unit_rows_local_convention_not_specified_by_paper",
        "component_basis_normalization": (
            "independent_unit_norm_equal_magnitude_convention_not_fully_specified_by_paper"
            if separate_components else None
        ),
        "semantic_directions": (
            {"+C": "put larger coordinate on positive component", "-C": "put larger coordinate on negative component"}
            if separate_components else None
        ),
        "paper_protocol_relation": (
            "per-layer target ordering equals a paper coordinate swap when the requested target is smaller; "
            "it is identity otherwise and is a behavioral adaptation"
            if separate_components else None
        ),
        "application_scale": (
            "alpha in an independently unit-normalized basis; the paper says perturbations were equal-magnitude "
            "but does not specify its normalization procedure"
            if separate_components else "unit_contrast"
        ),
        "gp_steps": 16,
        "concept_prompts": prompts, "dev_prompts": dev_prompts, "token_records": token_records,
        "pair_ids": pair_ids, "pair_tokens": [tokenizer.decode([i]) for i in pair_ids],
        "null_token_ids": null_ids, "null_seed": 0,
        "lens_sha256": hashlib.sha256(lens_file.read_bytes()).hexdigest(),
        "lens_file": str(lens_file), "lens_n_prompts": checkpoint["n_prompts"], "layers": layer_meta,
    }


@torch.inference_mode()
def extract_persona_components(
    model, tokenizer, layers, *, condition_prompts, source_ids, assistant_suffix_token_ids,
    batch_size, max_length, dev_prompts, projection="j_gp16", lens_file=None,
):
    spec, spec_hash = persona_component_spec(projection)
    conditions = ("positive", "negative", "baseline")
    if tuple(condition_prompts) != conditions:
        raise ValueError(f"persona component conditions must be {conditions}")
    n_source = len(source_ids)
    if n_source != spec["expected_unique_sources"] or len(set(source_ids)) != n_source:
        raise ValueError(
            f"persona component source IDs must contain exactly {spec['expected_unique_sources']} unique messages"
        )
    if any(len(condition_prompts[name]) != n_source for name in conditions):
        raise ValueError("persona component prompts are not aligned triples")
    prompts = [prompt for name in conditions for prompt in condition_prompts[name]]
    if not assistant_suffix_token_ids:
        raise ValueError("persona component assistant suffix is empty")
    for prompt in prompts:
        ids = tokenizer(prompt, add_special_tokens=False).input_ids
        if ids[-len(assistant_suffix_token_ids):] != assistant_suffix_token_ids:
            raise ValueError("persona component assistant-generation suffix mismatch")
    source_hash = hashlib.sha256(
        json.dumps([spec_hash, source_ids, condition_prompts], separators=(",", ":")).encode()
    ).hexdigest()
    hidden, token_records = residuals(
        model, tokenizer, prompts + dev_prompts, layers, batch_size, max_length,
    )
    for index in range(n_source):
        triple = [token_records[offset * n_source + index] for offset in range(3)]
        if len({record["final_token_id"] for record in triple}) != 1:
            raise ValueError(f"persona component final prompt tokens differ at source index {index}")
    dev_all = attended_residuals(model, tokenizer, dev_prompts, layers, batch_size, max_length)
    lens_file, checkpoint = _load_j_lens(model, layers, lens_file)
    device = next(model.parameters()).device
    unembedding = model.lm_head.weight.detach().float()
    n_fit = int(n_source * spec["fit_fraction"])
    n_holdout = n_source - n_fit
    split = n_fit // 2
    if split < 8:
        raise ValueError("persona component fit split is too small")
    fit = slice(0, n_fit)
    holdout = slice(n_fit, n_source)
    shared_states = {"+C": {}, "-C": {}}
    stacked_states = {"+C": {}, "-C": {}}
    layer_meta = {}
    for layer in layers:
        raw = unembedding @ checkpoint["J"][layer].float().to(device)
        norms = raw.norm(dim=-1)
        if not (norms > 0).all():
            raise ValueError(f"zero J-lens row at layer {layer}")
        dictionary = raw / norms[:, None]
        del raw
        hs = hidden[layer].to(device)
        states = {
            name: hs[offset * n_source:(offset + 1) * n_source]
            for offset, name in enumerate(conditions)
        }
        signals = {
            name: (states[name][fit] - states["baseline"][fit]).mean(0)
            for name in ("positive", "negative")
        }
        basis_components, supports, decompositions = [], [], {}
        for name in ("positive", "negative"):
            signal = signals[name]
            weights, component, support, errors = gradient_pursuit(signal, dictionary, 16)
            if not torch.isfinite(component).all() or component.norm() <= 1e-6 * signal.norm():
                raise ValueError(f"zero, nonfinite, or unresolved persona component {name} at layer {layer}")
            half_signals = [
                (states[name][start:stop] - states["baseline"][start:stop]).mean(0)
                for start, stop in ((0, split), (split, n_fit))
            ]
            half_components = [gradient_pursuit(value, dictionary, 16)[1] for value in half_signals]
            if any(value.norm() == 0 for value in half_components):
                raise ValueError(f"zero split-half persona component {name} at layer {layer}")
            active = weights.nonzero().flatten()
            remainder = signal - component
            basis_components.append(component if projection == "j_gp16" else signal)
            supports.append(set(active.tolist()))
            decompositions[name] = {
                "instruction": spec[f"{name}_instruction"],
                "full_signal_norm": signal.norm().item(),
                "gp_norm": component.norm().item(),
                "gp_to_full_norm_ratio": (component.norm() / signal.norm()).item(),
                "full_to_gp_cosine": torch.nn.functional.cosine_similarity(signal, component, dim=0).item(),
                "remainder_norm": remainder.norm().item(),
                "j_remainder_dot": (component @ remainder).item(),
                "reconstruction_error": (signal - component - remainder).norm().item(),
                "error_history": errors,
                "achieved_nonzero_count": active.numel(),
                "selected_ids": active.tolist(),
                "selected_tokens": [tokenizer.decode([i]) for i in active.tolist()],
                "weights_unit_dictionary": weights[active].tolist(),
                "raw_row_norms": norms[active].tolist(),
                "split_half_full_cosine": torch.nn.functional.cosine_similarity(
                    half_signals[0], half_signals[1], dim=0,
                ).item(),
                "split_half_gp_cosine": torch.nn.functional.cosine_similarity(
                    half_components[0], half_components[1], dim=0,
                ).item(),
                "full_signal_sha256": tensor_hash(signal),
                "gp_sha256": tensor_hash(component),
                "full_signal": signal.tolist(),
                "gp_component": component.tolist(),
            }
        basis = torch.stack([component / component.norm() for component in basis_components]).float()
        dual = torch.linalg.pinv(basis).T.contiguous()
        singular_values = torch.linalg.svdvals(basis)
        if singular_values[-1] <= 0 or not torch.isfinite(dual).all():
            raise ValueError(f"invalid persona component basis at layer {layer}")
        shared_states["+C"][layer] = {
            "basis": basis.cpu(), "dual": dual.cpu(), "target_index": torch.tensor(0, dtype=torch.int64),
        }
        shared_states["-C"][layer] = {
            "basis": basis.cpu(), "dual": dual.cpu(), "target_index": torch.tensor(1, dtype=torch.int64),
        }
        for side in ("+C", "-C"):
            stacked_states[side][layer] = {}
        source_coordinates = {
            name: states[name][holdout].float() @ dual.T
            for name in conditions
        }
        dev_coordinates = hidden[layer][3 * n_source:].to(device).float() @ dual.T
        dev_position_coordinates = [values.to(device) @ dual.T for values in dev_all[layer]]
        all_coordinates = torch.cat(dev_position_coordinates)
        eligible_plus = all_coordinates[:, 0] < all_coordinates[:, 1]
        eligible_minus = all_coordinates[:, 1] < all_coordinates[:, 0]
        by_prompt_eligibility = []
        for prompt_index, coordinates in enumerate(dev_position_coordinates):
            plus = coordinates[:, 0] < coordinates[:, 1]
            minus = coordinates[:, 1] < coordinates[:, 0]
            by_prompt_eligibility.append({
                "prompt_index": prompt_index,
                "positions": coordinates.shape[0],
                "+C": {
                    "eligible_positions": plus.nonzero().flatten().tolist(),
                    "fraction": plus.float().mean().item(),
                    "final_position_eligible": bool(plus[-1]),
                },
                "-C": {
                    "eligible_positions": minus.nonzero().flatten().tolist(),
                    "fraction": minus.float().mean().item(),
                    "final_position_eligible": bool(minus[-1]),
                },
            })
        layer_meta[str(layer)] = {
            "decomposition": decompositions,
            "fit_count": n_fit,
            "holdout_count": n_holdout,
            "support_overlap_count": len(supports[0] & supports[1]),
            "support_overlap_ids": sorted(supports[0] & supports[1]),
            "component_cosine": torch.nn.functional.cosine_similarity(
                basis_components[0], basis_components[1], dim=0,
            ).item(),
            "basis_projection": projection,
            "component_basis_singular_values": singular_values.tolist(),
            "component_basis_condition_number": (singular_values[0] / singular_values[-1]).item(),
            "heldout_source_coordinates": {name: value.tolist() for name, value in source_coordinates.items()},
            "heldout_source_coordinate_means": {
                name: value.mean(0).tolist() for name, value in source_coordinates.items()
            },
            "dev_final_coordinates": dev_coordinates.tolist(),
            "dev_final_coordinate_mean": dev_coordinates.mean(0).tolist(),
            "target_order_eligibility": {
                "+C": {"eligible": eligible_plus.sum().item(), "total": eligible_plus.numel(),
                       "fraction": eligible_plus.float().mean().item()},
                "-C": {"eligible": eligible_minus.sum().item(), "total": eligible_minus.numel(),
                       "fraction": eligible_minus.float().mean().item()},
                "by_prompt": by_prompt_eligibility,
            },
        }
        logger.info(
            "persona components layer={} projection={} basis_norms={} split_basis_cosines={} "
            "component_cosine={:.4f} condition={:.3f} eligibility_plus={:.3f} eligibility_minus={:.3f}",
            layer,
            projection,
            [
                decompositions[name]["gp_norm" if projection == "j_gp16" else "full_signal_norm"]
                for name in ("positive", "negative")
            ],
            [
                decompositions[name][
                    "split_half_gp_cosine" if projection == "j_gp16" else "split_half_full_cosine"
                ]
                for name in ("positive", "negative")
            ],
            layer_meta[str(layer)]["component_cosine"],
            layer_meta[str(layer)]["component_basis_condition_number"],
            layer_meta[str(layer)]["target_order_eligibility"]["+C"]["fraction"],
            layer_meta[str(layer)]["target_order_eligibility"]["-C"]["fraction"],
        )
    vectors = {
        side: Vector(JLensConceptComponentsC(layers=layers), shared_states[side], stacked_states[side])
        for side in ("+C", "-C")
    }
    validate_component_pair(vectors)
    operator = (
        PERSONA_COMPONENT_PAIR_VERSION
        if projection == "j_gp16" else PERSONA_FULL_COMPONENT_PAIR_VERSION
    )
    representation_source = (
        PERSONA_COMPONENT_PAIR_REPRESENTATION_SOURCE
        if projection == "j_gp16" else PERSONA_FULL_COMPONENT_PAIR_REPRESENTATION_SOURCE
    )
    return vectors, {
        "operator": operator,
        "representation_source": representation_source,
        "projection": projection,
        "spec_sha256": spec_hash,
        "implementation_sha256": implementation_hash(),
        "spec": spec,
        "source_sha256": source_hash,
        "source_ids": source_ids,
        "source_prompts": condition_prompts,
        "assistant_suffix_token_ids": assistant_suffix_token_ids,
        "model_revision": getattr(model.config, "_commit_hash", None),
        "tokenizer_revision": tokenizer.init_kwargs.get("_commit_hash"),
        "tokenizer_content_sha256": tokenizer_content_hash(tokenizer),
        "source_pool_count": spec["source_pool_count"],
        "source_unique_count": n_source,
        "source_fit_count": n_fit,
        "source_holdout_count": n_holdout,
        "source_identity": "sha256(user_msg); duplicate rendered messages removed before seeded ordering",
        "source_layers": list(layers),
        "equation": "h_all_prefill + alpha * V * (target_sort(V^dagger h_all_prefill) - V^dagger h_all_prefill)",
        "extraction_mask": "final_real_chat_prompt_token",
        "application_mask": "all_attended_prefill_positions",
        "dictionary_normalization": "unit_rows_local_convention_not_specified_by_paper",
        "component_basis_normalization": "independent_unit_norm_equal_magnitude_convention_not_fully_specified_by_paper",
        "semantic_directions": {"+C": "put larger coordinate on positive component", "-C": "put larger coordinate on negative component"},
        "paper_protocol_relation": (
            "behavior-conditioned source adaptation using the paper GP16 reconstruction and target-order coordinate exchange"
            if projection == "j_gp16"
            else "non-J full-residual control for the behavior-conditioned source and target-order coordinate exchange"
        ),
        "token_records": token_records,
        "lens_sha256": hashlib.sha256(lens_file.read_bytes()).hexdigest(),
        "lens_file": str(lens_file),
        "lens_n_prompts": checkpoint["n_prompts"],
        "layers": layer_meta,
    }


@torch.inference_mode()
def extract_persona_contrast(model, tokenizer, layers, *, positive_prompts, negative_prompts,
                             batch_size, max_length, direction="j_gp16",
                             representation_source="matched_persona_prompt_difference", lens_file=None):
    if len(positive_prompts) != len(negative_prompts) or not positive_prompts:
        raise ValueError("persona extraction prompts must be nonempty matched pairs")
    if direction not in {"j_gp16", "full_residual"}:
        raise ValueError(f"unknown persona direction {direction}")
    prompts = [*positive_prompts, *negative_prompts]
    prompt_hash = hashlib.sha256(json.dumps(prompts, separators=(",", ":")).encode()).hexdigest()
    hidden, token_records = residuals(model, tokenizer, prompts, layers, batch_size, max_length)
    lens_file, checkpoint = _load_j_lens(model, layers, lens_file)
    device = next(model.parameters()).device
    unembedding = model.lm_head.weight.detach().float()
    n_pairs = len(positive_prompts)
    state, layer_meta = {}, {}
    for layer in layers:
        raw = unembedding @ checkpoint["J"][layer].float().to(device)
        norms = raw.norm(dim=-1)
        if not (norms > 0).all():
            raise ValueError(f"zero J-lens row at layer {layer}")
        dictionary = raw / norms[:, None]
        del raw
        hs = hidden[layer].to(device)
        difference = hs[:n_pairs].mean(0) - hs[n_pairs:].mean(0)
        weights, j_component, _selected_support, errors = gradient_pursuit(difference, dictionary, 16)
        if not torch.isfinite(j_component).all() or j_component.norm() <= 1e-6 * difference.norm():
            raise ValueError(f"zero, nonfinite, or numerically unresolved persona J component at layer {layer}")
        component = j_component if direction == "j_gp16" else difference
        selected = weights.nonzero().flatten()
        remainder = difference - j_component
        state[layer] = {"v": (component / component.norm()).cpu().unsqueeze(0)}
        layer_meta[str(layer)] = {
            "achieved_nonzero_count": selected.numel(), "selected_ids": selected.tolist(),
            "selected_tokens": [tokenizer.decode([i]) for i in selected.tolist()],
            "weights_unit_dictionary": weights[selected].tolist(), "raw_row_norms": norms[selected].tolist(),
            "paired_difference_norm": difference.norm().item(), "j_norm": j_component.norm().item(),
            "remainder_norm": remainder.norm().item(), "j_remainder_dot": (j_component @ remainder).item(),
            "reconstruction_error": (difference - j_component - remainder).norm().item(),
            "error_history": errors, "difference_sha256": tensor_hash(difference),
            "j_sha256": tensor_hash(j_component), "remainder_sha256": tensor_hash(remainder),
            "applied_direction": direction, "applied_direction_sha256": tensor_hash(component),
            "full_j_cosine": torch.nn.functional.cosine_similarity(difference, j_component, dim=0).item(),
        }
        logger.info("persona layer={} direction={} applied_norm={:.4f} j_norm={:.4f} remainder_norm={:.4f} selected={}",
                    layer, direction, component.norm(), j_component.norm(), remainder.norm(), selected.numel())
    vector = Vector(JLensConceptC(layers=layers), {layer: {} for layer in layers}, state)
    return {"+C": vector, "-C": vector}, {
        "operator": PERSONA_VERSION if direction == "j_gp16" else PERSONA_FULL_RESIDUAL_VERSION,
        "representation_source": representation_source,
        "projection": direction, "implementation_sha256": implementation_hash(), "source_layers": list(layers),
        "equation": "h_user_turn + C * unit(project_J(mean(h_sycophantic) - mean(h_abrasive)))"
                    if direction == "j_gp16" else "h_user_turn + C * unit(mean(h_sycophantic) - mean(h_abrasive))",
        "extraction_mask": "final_real_chat_prompt_token", "application_mask": "user_turn_including_chat_delimiters",
        "dictionary_normalization": "unit_rows_local_convention_not_specified_by_paper", "gp_steps": 16,
        "n_pairs": n_pairs, "prompt_sha256": prompt_hash,
        "positive_prompts": positive_prompts, "negative_prompts": negative_prompts,
        "token_records": token_records, "lens_sha256": hashlib.sha256(lens_file.read_bytes()).hexdigest(),
        "lens_file": str(lens_file), "lens_n_prompts": checkpoint["n_prompts"], "layers": layer_meta,
    }
