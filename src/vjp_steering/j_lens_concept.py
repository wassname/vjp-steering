"""Sparse concept decomposition and signed prompt-only addition. — PI/OpenAI Codex"""

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
VERSION = "mean100-gp16-unit-dictionary-signed-add-v1"
PERSONA_VERSION = "paired-persona-gp16-unit-dictionary-signed-add-v1"
PERSONA_FULL_RESIDUAL_VERSION = "paired-persona-full-residual-signed-add-control-v1"
LEGACY_EXTRACTION_IMPLEMENTATION_SHA256 = "fc65ee58b5f5b4fc5d952cd0439f0e0f84f7f2ede2e06e7d1bb2134ff0085d31"


@register_config
@dataclass
class JLensConceptC(SteeringConfig):
    method: str = METHOD


def concept_spec() -> tuple[dict, str]:
    spec = json.loads(SPEC_PATH.read_text())
    assert len(spec["baseline"]) == len(set(spec["baseline"])) == 100
    digest = hashlib.sha256(json.dumps([VERSION, spec], sort_keys=True).encode()).hexdigest()
    return spec, digest


def implementation_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def tensor_hash(tensor: torch.Tensor) -> str:
    return hashlib.sha256(tensor.detach().float().contiguous().cpu().numpy().tobytes()).hexdigest()


def select_concept_layers(vector: Vector, layers: tuple[int, ...]) -> Vector:
    available = tuple(vector.cfg.layers)
    if not layers or len(set(layers)) != len(layers) or any(layer not in available for layer in layers):
        raise ValueError(f"invalid concept application layers={layers}; available={available}")
    cfg = JLensConceptC(layers=layers)
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


@torch.no_grad()
def gradient_pursuit(
    signal: Float[torch.Tensor, "d"], dictionary: Float[torch.Tensor, "v d"], k: int = 16,
) -> tuple[torch.Tensor, torch.Tensor, list[float]]:
    if not torch.isfinite(signal).all() or not torch.isfinite(dictionary).all():
        raise ValueError("nonfinite pursuit input")
    weights = torch.zeros(dictionary.shape[0], device=dictionary.device)
    errors = []
    for _ in range(k):
        residual = signal - weights @ dictionary
        scores = dictionary @ residual
        active = weights != 0
        active[scores.argmax()] = True
        gradient = active * scores
        change = gradient @ dictionary
        denominator = change.square().sum()
        if denominator == 0:
            break
        step = (change @ residual) / denominator
        weights = (weights + step * gradient).clamp_min(0)
        errors.append((signal - weights @ dictionary).norm().item())
    return weights, weights @ dictionary, errors


@contextmanager
def concept_prefill(model, vector: Vector, mask: torch.Tensor, coefficient: float):
    handles = []
    calls = {layer: 0 for layer in vector.cfg.layers}

    def hook(layer):
        def apply(_module, _inputs, output):
            calls[layer] += 1
            hidden = output[0] if isinstance(output, tuple) else output
            delta = vector.stacked[layer]["v"].sum(0).to(hidden)
            edited = hidden + coefficient * mask.to(hidden).unsqueeze(-1) * delta
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
                        coefficient: float) -> dict:
    """Measure the actual prompt patch and final-token distribution change for one cell."""
    mask = attention_mask.bool()
    batch = torch.arange(mask.shape[0], device=mask.device)
    final = final_positions(mask)
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
            direction = vector.stacked[layer]["v"].sum(0).to(original)
            ratio = actual.norm(dim=-1) / original.norm(dim=-1)
            summaries[str(layer)] = {
                "patch_residual_ratio_median": ratio.median().item(),
                "patch_residual_ratio_p90": ratio.quantile(.9).item(),
                "actual_patch_norm_median": actual.norm(dim=-1).median().item(),
                "actual_direction_coordinate_median": (actual @ direction).median().item(),
                "changed_coordinate_fraction": (actual != 0).float().mean().item(),
                "dtype": str(hidden.dtype),
            }
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
def extract_concept(model, tokenizer, layers, *, batch_size, max_length, dev_prompts, lens_file=None):
    spec, spec_hash = concept_spec()
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
    state, layer_meta = {}, {}
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
            weights, component, errors = gradient_pursuit(concept, dictionary, 16)
            selected = weights.nonzero().flatten()
            remainder = concept - component
            components.append(component)
            decomposition.append({
                "concept": texts[index], "achieved_nonzero_count": selected.numel(), "selected_ids": selected.tolist(),
                "selected_tokens": [tokenizer.decode([i]) for i in selected.tolist()],
                "weights_unit_dictionary": weights[selected].tolist(), "raw_row_norms": norms[selected].tolist(),
                "concept_norm": concept.norm().item(), "j_norm": component.norm().item(),
                "remainder_norm": remainder.norm().item(), "error_history": errors,
                "j_remainder_dot": (component @ remainder).item(),
                "reconstruction_error": (concept - component - remainder).norm().item(),
                "concept_vector": concept.tolist(), "j_vector": component.tolist(), "remainder": remainder.tolist(),
                "concept_sha256": tensor_hash(concept), "j_sha256": tensor_hash(component),
                "remainder_sha256": tensor_hash(remainder),
            })
        contrast = components[0] - components[1]
        if not torch.isfinite(contrast).all() or contrast.norm() <= 1e-6 * max(c.norm() for c in components):
            raise ValueError(f"zero, nonfinite, or numerically unresolved concept contrast at layer {layer}")
        state[layer] = {"v": (contrast / contrast.norm()).cpu().unsqueeze(0)}
        layer_meta[str(layer)] = {
            "decomposition": decomposition, "contrast_norm": contrast.norm().item(),
            "component_cosine": torch.nn.functional.cosine_similarity(components[0], components[1], dim=0).item(),
            "baseline_mean": baseline.tolist(), "baseline_mean_sha256": tensor_hash(baseline),
            "pair_unit_cosine": (dictionary[pair_ids[0]] @ dictionary[pair_ids[1]]).item(),
            "pair_singular_values": torch.linalg.svdvals(dictionary[pair_ids]).tolist(),
            "baseline_activity": _activity(hs[2:102], dictionary, pair_ids, null_ids, norms),
            "dev_activity": _activity(hs[102:], dictionary, pair_ids, null_ids, norms),
        }
        logger.info("concept layer={} j_norms={} remainder_norms={} contrast_norm={:.4f}", layer,
                    [d["j_norm"] for d in decomposition], [d["remainder_norm"] for d in decomposition], contrast.norm())
    vector = Vector(JLensConceptC(layers=layers), {layer: {} for layer in layers}, state)
    return {"+C": vector, "-C": vector}, {
        "operator": VERSION, "representation_source": "concept_mean100", "spec_sha256": spec_hash,
        "implementation_sha256": implementation_hash(),
        "spec": spec, "source_layers": list(layers),
        "equation": "h_valid_prompt + C * unit(j_positive - j_negative)",
        "extraction_mask": "final_real_chat_prompt_token", "application_mask": "all_valid_prefill_tokens_only",
        "activity_mask": "final_real_chat_prompt_token_only_not_all_patched_positions",
        "dictionary_normalization": "unit_rows_local_convention_not_specified_by_paper", "gp_steps": 16,
        "concept_prompts": prompts, "dev_prompts": dev_prompts, "token_records": token_records,
        "pair_ids": pair_ids, "pair_tokens": [tokenizer.decode([i]) for i in pair_ids],
        "null_token_ids": null_ids, "null_seed": 0,
        "lens_sha256": hashlib.sha256(lens_file.read_bytes()).hexdigest(),
        "lens_file": str(lens_file), "lens_n_prompts": checkpoint["n_prompts"], "layers": layer_meta,
    }


@torch.inference_mode()
def extract_persona_contrast(model, tokenizer, layers, *, positive_prompts, negative_prompts,
                             batch_size, max_length, direction="j_gp16", lens_file=None):
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
        weights, j_component, errors = gradient_pursuit(difference, dictionary, 16)
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
        "representation_source": "matched_persona_prompt_difference",
        "projection": direction, "implementation_sha256": implementation_hash(), "source_layers": list(layers),
        "equation": "h_valid_prompt + C * unit(project_J(mean(h_sycophantic) - mean(h_abrasive)))"
                    if direction == "j_gp16" else "h_valid_prompt + C * unit(mean(h_sycophantic) - mean(h_abrasive))",
        "extraction_mask": "final_real_chat_prompt_token", "application_mask": "all_valid_prefill_tokens_only",
        "dictionary_normalization": "unit_rows_local_convention_not_specified_by_paper", "gp_steps": 16,
        "n_pairs": n_pairs, "prompt_sha256": prompt_hash,
        "positive_prompts": positive_prompts, "negative_prompts": negative_prompts,
        "token_records": token_records, "lens_sha256": hashlib.sha256(lens_file.read_bytes()).hexdigest(),
        "lens_file": str(lens_file), "lens_n_prompts": checkpoint["n_prompts"], "layers": layer_meta,
    }
