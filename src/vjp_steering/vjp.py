"""VJP-delta extraction for activation steering.

For a target layer T and source layer L:

    c = mean(h_T positive) - mean(h_T negative)
    v_L = mean_positive(J_L_to_T(x)^T c) - mean_negative(J_L_to_T(x)^T c)

The target cotangent and source gradient are both pooled over valid prompt
positions. Each source-layer result is normalized before steering.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from pathlib import Path

import torch
from loguru import logger
from jaxtyping import Bool, Float, Int
from steering_lite import Vector, VjpDeltaC
from steering_lite.config import register, register_config
from steering_lite.variants.vjp_delta import VjpDelta


@register_config
@dataclass
class JWordC(VjpDeltaC):
    method: str = "J_word"


@register
class JWord:
    name = "J_word"
    apply = staticmethod(VjpDelta.apply)


@register_config
@dataclass
class VjpMlpUpLeftRightShrinkC(VjpDeltaC):
    method: str = "vjp_mlp_up_left_right_shrink"


@register
class VjpMlpUpLeftRightShrink:
    name = "vjp_mlp_up_left_right_shrink"
    apply = staticmethod(VjpDelta.apply)


@register_config
@dataclass
class VjpMlpUpSharedEBC(VjpDeltaC):
    method: str = "vjp_mlp_up_shared_eb"


@register
class VjpMlpUpSharedEB:
    name = "vjp_mlp_up_shared_eb"
    apply = staticmethod(VjpDelta.apply)


J_WORD_LENS_REPO = "neuronpedia/jacobian-lens"
J_WORD_LENS_REVISION = "qwen-n1000"
J_WORD_LENS_FILE = "qwen3.5-4b/jlens/Salesforce-wikitext/Qwen3.5-4B_jacobian_lens_n1000.pt"
J_WORD_POSITIVE = "sycophantic"
J_WORD_NEGATIVE = "abrasive"


def _blocks(model):
    return model.model.layers


@contextmanager
def _activations(
    model,
    layers: tuple[int, ...],
    graph_root: int | None = None,
    source_readout: str | None = None,
    target_layer: int | None = None,
):
    found = {}
    handles = []

    def hook(layer):
        def record(_module, _inputs, output):
            hidden = output[0] if isinstance(output, tuple) else output
            if layer == graph_root:
                hidden = hidden.detach().requires_grad_(True)
                output = (hidden, *output[1:]) if isinstance(output, tuple) else hidden
            found[layer] = hidden
            return output

        return record

    for layer in layers:
        block = _blocks(model)[layer]
        module = block if source_readout is None or layer == target_layer else block.get_submodule(source_readout)
        handles.append(module.register_forward_hook(hook(layer)))
    try:
        yield found
    finally:
        for handle in handles:
            handle.remove()


def _encode(model, tokenizer, prompts: list[str], max_length: int):
    return tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_length,
        padding_side="right",
        add_special_tokens=False,
    ).to(next(model.parameters()).device)


def _valid_mask(
    attention_mask: Int[torch.Tensor, "b s"], skip_first: int
) -> Bool[torch.Tensor, "b s"]:
    positions = torch.arange(attention_mask.shape[1], device=attention_mask.device)
    real_length = attention_mask.sum(dim=1, keepdim=True)
    return (
        (positions[None, :] >= skip_first)
        & (positions[None, :] < real_length - 1)
        & attention_mask.bool()
    )


@torch.no_grad()
def _target_mean(
    model,
    tokenizer,
    prompts: list[str],
    target_layer: int,
    batch_size: int,
    max_length: int,
) -> torch.Tensor:
    total = None
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        encoded = _encode(model, tokenizer, batch, max_length)
        with _activations(model, (target_layer,)) as found:
            model(**encoded)
        last = encoded["attention_mask"].sum(dim=1) - 1
        rows = torch.arange(len(batch), device=last.device)
        values = found[target_layer][rows, last].float()
        total = values.sum(0) if total is None else total + values.sum(0)
    return total / len(prompts)


def _batch_gradients(
    model,
    tokenizer,
    prompts: list[str],
    layers: tuple[int, ...],
    target_layer: int,
    cotangent: Float[torch.Tensor, " d"],
    skip_first: int,
    max_length: int,
    source_readout: str | None = None,
) -> tuple[
    dict[int, Float[torch.Tensor, "b s d"]],
    Bool[torch.Tensor, "b s"],
    dict[int, Float[torch.Tensor, "b s d"]],
]:
    encoded = _encode(model, tokenizer, prompts, max_length)
    valid = _valid_mask(encoded["attention_mask"], skip_first)
    if valid.sum(dim=1).min() == 0:
        raise ValueError(f"a prompt has no valid positions after skip_first={skip_first}")

    with _activations(
        model,
        (*layers, target_layer),
        graph_root=min(layers),
        source_readout=source_readout,
        target_layer=target_layer,
    ) as found:
        with torch.enable_grad():
            model(**encoded)
            target = found[target_layer]
            expanded = cotangent.detach().to(target).view(1, 1, -1)
            gradients = torch.autograd.grad(
                target,
                [found[layer] for layer in layers],
                grad_outputs=expanded * valid.unsqueeze(-1),
            )
            activations = {layer: found[layer].detach() for layer in layers}
    return dict(zip(layers, gradients, strict=True)), valid, activations


def _class_mean_vjp(
    model,
    tokenizer,
    prompts: list[str],
    layers: tuple[int, ...],
    target_layer: int,
    cotangent: Float[torch.Tensor, " d"],
    batch_size: int,
    max_length: int,
    skip_first: int,
) -> dict[int, Float[torch.Tensor, " d"]]:
    totals = {layer: torch.zeros_like(cotangent, dtype=torch.float32) for layer in layers}
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        gradients, valid, _ = _batch_gradients(
            model,
            tokenizer,
            batch,
            layers,
            target_layer,
            cotangent,
            skip_first,
            max_length,
        )
        counts = valid.sum(dim=1, keepdim=True).float()
        for layer, gradient in gradients.items():
            per_prompt = (gradient.float() * valid.unsqueeze(-1)).sum(dim=1) / counts
            totals[layer] += per_prompt.sum(0)
    return {layer: total / len(prompts) for layer, total in totals.items()}


def _class_prompt_vjp(
    model,
    tokenizer,
    prompts: list[str],
    layers: tuple[int, ...],
    target_layer: int,
    cotangent: Float[torch.Tensor, " d"],
    batch_size: int,
    max_length: int,
    skip_first: int,
    source_readout: str,
) -> dict[int, torch.Tensor]:
    values = {layer: [] for layer in layers}
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        gradients, valid, _ = _batch_gradients(
            model,
            tokenizer,
            batch,
            layers,
            target_layer,
            cotangent,
            skip_first,
            max_length,
            source_readout=source_readout,
        )
        counts = valid.sum(dim=1, keepdim=True).float()
        for layer, gradient in gradients.items():
            values[layer].append((gradient.float() * valid.unsqueeze(-1)).sum(dim=1) / counts)
    return {layer: torch.cat(layer_values) for layer, layer_values in values.items()}


def _class_prompt_vjp_scale(
    model,
    tokenizer,
    prompts: list[str],
    layers: tuple[int, ...],
    target_layer: int,
    cotangent: Float[torch.Tensor, " d"],
    batch_size: int,
    max_length: int,
    skip_first: int,
    source_readout: str,
    *,
    return_moments: bool = False,
) -> tuple[dict[int, torch.Tensor], dict[int, torch.Tensor]] | tuple[dict[int, torch.Tensor], dict[int, torch.Tensor], dict[str, object]]:
    gradients_by_layer = {layer: [] for layer in layers}
    activation_sum = {layer: None for layer in layers}
    activation_square_sum = {layer: None for layer in layers}
    activation_count = 0
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        gradients, valid, activations = _batch_gradients(
            model,
            tokenizer,
            batch,
            layers,
            target_layer,
            cotangent,
            skip_first,
            max_length,
            source_readout=source_readout,
        )
        mask = valid.unsqueeze(-1)
        counts = valid.sum(dim=1, keepdim=True).float()
        activation_count += int(valid.sum())
        for layer in layers:
            gradient = gradients[layer].float()
            gradients_by_layer[layer].append((gradient * mask).sum(dim=1) / counts)
            activation = activations[layer].double()
            double_mask = mask.to(dtype=torch.float64)
            batch_sum = (activation * double_mask).sum(dim=(0, 1)).cpu()
            batch_square_sum = (activation.square() * double_mask).sum(dim=(0, 1)).cpu()
            activation_sum[layer] = batch_sum if activation_sum[layer] is None else activation_sum[layer] + batch_sum
            activation_square_sum[layer] = (
                batch_square_sum
                if activation_square_sum[layer] is None
                else activation_square_sum[layer] + batch_square_sum
            )
    if activation_count == 0:
        raise ValueError("mlp-up activation scale has no valid positions")
    prompt_gradients = {layer: torch.cat(values).cpu() for layer, values in gradients_by_layer.items()}
    activation_scale = {}
    for layer in layers:
        mean = activation_sum[layer] / activation_count
        variance = activation_square_sum[layer] / activation_count - mean.square()
        activation_scale[layer] = variance.clamp(min=0).sqrt().float()
    moments = {
        "count": activation_count,
        "sum": activation_sum,
        "square_sum": activation_square_sum,
    }
    if return_moments:
        return prompt_gradients, activation_scale, moments
    return prompt_gradients, activation_scale


def j_word(
    model,
    tokenizer,
    layers: tuple[int, ...],
    *,
    lens_file: Path | None = None,
) -> tuple[Vector, dict[str, object]]:
    """Steer the persona-word contrast through a cached full Jacobian lens."""
    if lens_file is None:
        from huggingface_hub import hf_hub_download

        lens_file = Path(
            hf_hub_download(
                repo_id=J_WORD_LENS_REPO,
                revision=J_WORD_LENS_REVISION,
                filename=J_WORD_LENS_FILE,
            )
        )
    checkpoint = torch.load(lens_file, map_location="cpu", weights_only=True, mmap=True)
    assert set(checkpoint) == {"J", "n_prompts", "source_layers", "d_model"}
    assert checkpoint["d_model"] == model.config.hidden_size
    assert set(layers) <= set(checkpoint["source_layers"])

    unembedding = model.lm_head.weight

    def word_embedding(word: str) -> tuple[torch.Tensor, list[int]]:
        token_ids = tokenizer(" " + word, add_special_tokens=False).input_ids
        return unembedding[torch.tensor(token_ids, device=unembedding.device)].float().mean(0), token_ids

    positive, positive_ids = word_embedding(J_WORD_POSITIVE)
    negative, negative_ids = word_embedding(J_WORD_NEGATIVE)
    cotangent = positive - negative
    directions = {
        layer: cotangent.cpu() @ checkpoint["J"][layer].float() for layer in layers
    }
    logger.info(
        "J_word lens={} n_prompts={} words={} ids={} - {} ids={} cotangent_norm={:.3f}",
        lens_file,
        checkpoint["n_prompts"],
        J_WORD_POSITIVE,
        positive_ids,
        J_WORD_NEGATIVE,
        negative_ids,
        cotangent.norm(),
    )
    vector = Vector(
        JWordC(layers=layers),
        {layer: {} for layer in layers},
        {layer: {"v": (direction / direction.norm()).unsqueeze(0)} for layer, direction in directions.items()},
    )
    return vector, {
        "lens_file": str(lens_file),
        "lens_sha256": hashlib.sha256(lens_file.read_bytes()).hexdigest(),
        "lens_n_prompts": checkpoint["n_prompts"],
        "cotangent": f"{J_WORD_POSITIVE} - {J_WORD_NEGATIVE}",
        "cotangent_norm": cotangent.norm().item(),
        "layer_norms": {str(layer): direction.norm().item() for layer, direction in directions.items()},
    }


def vjp_mlp_up_shrink(
    model,
    tokenizer,
    positive_prompts: list[str],
    negative_prompts: list[str],
    *,
    target_layer: int | None = None,
    batch_size: int = 8,
    max_length: int = 384,
    skip_first: int = 16,
) -> tuple[Vector, dict[str, object]]:
    """Pull back the persona contrast to every prior MLP up projection."""
    model.requires_grad_(False)
    target_layer = len(_blocks(model)) - 3 if target_layer is None else target_layer
    layers = tuple(range(target_layer))
    cotangent = _target_mean(
        model, tokenizer, positive_prompts, target_layer, batch_size, max_length
    ) - _target_mean(
        model, tokenizer, negative_prompts, target_layer, batch_size, max_length
    )
    positive = _class_prompt_vjp(
        model, tokenizer, positive_prompts, layers, target_layer, cotangent,
        batch_size, max_length, skip_first, "mlp.up_proj",
    )
    negative = _class_prompt_vjp(
        model, tokenizer, negative_prompts, layers, target_layer, cotangent,
        batch_size, max_length, skip_first, "mlp.up_proj",
    )
    if len(positive_prompts) != len(negative_prompts):
        raise ValueError("mlp-up shrinkage needs paired persona prompts")
    paired = {layer: positive[layer] - negative[layer] for layer in layers}
    weights = {
        layer: (1 - paired[layer].var(0, unbiased=True) / paired[layer].mean(0).square().clamp(min=1e-30)).clamp(min=0)
        for layer in layers
    }
    directions = {layer: paired[layer].mean(0) * weights[layer] for layer in layers}
    total_norm = torch.stack([direction.norm() for direction in directions.values()]).norm()
    if not torch.isfinite(total_norm) or total_norm == 0:
        raise ValueError("mlp-up shrinkage produced a zero or nonfinite vector")
    normalized = {layer: direction / total_norm for layer, direction in directions.items()}
    names = {layer: "mlp.up_proj" for layer in layers}
    logger.info(
        "vjp_mlp_up_shrink target={} source_layers={} global_norm={:.3f} live={}",
        target_layer,
        len(layers),
        total_norm,
        sum(int((weight > 0).sum()) for weight in weights.values()),
    )
    vector = Vector(
        VjpDeltaC(layers=layers, target_submodule="mlp.up_proj", target_layer=target_layer),
        {f"layers.{layer}.{names[layer]}": {} for layer in layers},
        {f"layers.{layer}.{names[layer]}": {"v": normalized[layer].unsqueeze(0)} for layer in layers},
    )
    return vector, {
        "source_readout": "mlp.up_proj",
        "delta_estimator": "shrink_between_pair_std",
        "normalization": "global",
        "target_layer": target_layer,
        "source_layers": list(layers),
        "global_norm": total_norm.item(),
        "live_coordinates": {str(layer): int((weight > 0).sum()) for layer, weight in weights.items()},
    }


def _layer_tensor_sha256(tensors: dict[int, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for layer, tensor in sorted(tensors.items()):
        value = tensor.detach().contiguous().cpu()
        digest.update(f"{layer}:{value.dtype}:{tuple(value.shape)}".encode())
        digest.update(value.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def _empirical_bayes_raw(
    prompt_gradients: dict[int, torch.Tensor],
) -> tuple[dict[int, torch.Tensor], dict[int, torch.Tensor], dict[int, torch.Tensor]]:
    means = {layer: gradients.mean(0) for layer, gradients in prompt_gradients.items()}
    variances = {
        layer: gradients.var(0, unbiased=True) for layer, gradients in prompt_gradients.items()
    }
    n_prompts = next(iter(prompt_gradients.values())).shape[0]
    raw, weights, signal_variance = {}, {}, {}
    for layer in prompt_gradients:
        noise_variance = variances[layer] / n_prompts
        signal_variance[layer] = (means[layer].square() - noise_variance).mean().clamp(min=0)
        weights[layer] = signal_variance[layer] / (signal_variance[layer] + noise_variance)
        raw[layer] = means[layer] * weights[layer]
    return raw, weights, signal_variance


def _pooled_activation_scale(
    first: dict[str, object], second: dict[str, object], layers: tuple[int, ...]
) -> dict[int, torch.Tensor]:
    count = int(first["count"]) + int(second["count"])
    if count == 0:
        raise ValueError("pooled activation scale has no valid positions")
    sums_first = first["sum"]
    sums_second = second["sum"]
    squares_first = first["square_sum"]
    squares_second = second["square_sum"]
    return {
        layer: (
            (squares_first[layer] + squares_second[layer]) / count
            - ((sums_first[layer] + sums_second[layer]) / count).square()
        ).clamp(min=0).sqrt().float()
        for layer in layers
    }


def vjp_mlp_up_left_right_shrink(
    model,
    tokenizer,
    positive_prompts: list[str],
    negative_prompts: list[str],
    *,
    target_layer: int | None = None,
    batch_size: int = 8,
    max_length: int = 384,
    skip_first: int = 16,
) -> tuple[dict[str, Vector], dict[str, object]]:
    """Extract destination-conditioned MLP-up rays with empirical-Bayes VJP shrinkage."""
    model.requires_grad_(False)
    if len(positive_prompts) != len(negative_prompts) or len(positive_prompts) < 2:
        raise ValueError("per-side shrinkage needs at least two paired persona prompts")
    target_layer = len(_blocks(model)) - 3 if target_layer is None else target_layer
    layers = tuple(range(target_layer))
    cotangent = _target_mean(
        model, tokenizer, positive_prompts, target_layer, batch_size, max_length
    ) - _target_mean(
        model, tokenizer, negative_prompts, target_layer, batch_size, max_length
    )
    positive, positive_scale = _class_prompt_vjp_scale(
        model, tokenizer, positive_prompts, layers, target_layer, cotangent,
        batch_size, max_length, skip_first, "mlp.up_proj",
    )
    negative, negative_scale = _class_prompt_vjp_scale(
        model, tokenizer, negative_prompts, layers, target_layer, cotangent,
        batch_size, max_length, skip_first, "mlp.up_proj",
    )
    samples = {"+C": positive, "-C": negative}
    scales = {"+C": positive_scale, "-C": negative_scale}
    vectors = {}
    metadata = {
        "source_readout": "mlp.up_proj",
        "delta_estimator": "destination_conditioned_per_side_shrink",
        "noisy_coordinate_estimator": "empirical_bayes_normal_normal_per_layer",
        "normalization": "global_activation_scaled",
        "target_layer": target_layer,
        "source_layers": list(layers),
        "sides": {},
    }
    names = {layer: "mlp.up_proj" for layer in layers}
    flattened = {}
    for side in ("+C", "-C"):
        n_prompts = next(iter(samples[side].values())).shape[0]
        means = {layer: samples[side][layer].mean(0) for layer in layers}
        current_weights = {
            layer: (
                1
                - samples[side][layer].var(0, unbiased=True)
                / means[layer].square().clamp(min=1e-30)
            ).clamp(min=0)
            for layer in layers
        }
        raw_current = {
            layer: means[layer] * current_weights[layer] for layer in layers
        }

        def unit_standardized_direction(candidate_raw: dict[int, torch.Tensor]):
            direction = torch.cat([
                (scales[side][layer].square() * candidate_raw[layer]).flatten()
                for layer in layers
            ])
            norm = direction.norm()
            if not torch.isfinite(norm) or norm == 0:
                raise ValueError(f"mlp-up {side} candidate direction is zero or nonfinite")
            return direction / norm

        raw_eb, weights_eb, signal_variance = _empirical_bayes_raw(samples[side])
        current_unit = unit_standardized_direction(raw_current)
        eb_unit = unit_standardized_direction(raw_eb)
        raw = raw_eb
        weights = weights_eb
        split_half_cosine = None
        if n_prompts >= 4:
            split_current, split_eb = [], []
            for split in (0, 1):
                split_samples = {layer: samples[side][layer][split::2] for layer in layers}
                split_means = {layer: split_samples[layer].mean(0) for layer in layers}
                split_weights = {
                    layer: (
                        1
                        - split_samples[layer].var(0, unbiased=True)
                        / split_means[layer].square().clamp(min=1e-30)
                    ).clamp(min=0)
                    for layer in layers
                }
                split_current.append(unit_standardized_direction({
                    layer: split_means[layer] * split_weights[layer] for layer in layers
                }))
                split_raw_eb, _, _ = _empirical_bayes_raw(split_samples)
                split_eb.append(unit_standardized_direction(split_raw_eb))
            split_half_cosine = {
                "current": torch.nn.functional.cosine_similarity(
                    split_current[0], split_current[1], dim=0
                ).item(),
                "empirical_bayes": torch.nn.functional.cosine_similarity(
                    split_eb[0], split_eb[1], dim=0
                ).item(),
            }
        activation_norm = torch.stack(
            [(scales[side][layer] * raw[layer]).norm() for layer in layers]
        ).norm()
        if not torch.isfinite(activation_norm) or activation_norm == 0:
            raise ValueError(f"mlp-up {side} activation-scaled norm is zero or nonfinite")
        directions = {
            layer: scales[side][layer].square() * raw[layer] / activation_norm
            for layer in layers
        }
        if not all(torch.isfinite(direction).all() for direction in directions.values()):
            raise ValueError(f"mlp-up {side} direction is nonfinite")
        vectors[side] = Vector(
            VjpMlpUpLeftRightShrinkC(
                layers=layers,
                target_submodule="mlp.up_proj",
                target_layer=target_layer,
            ),
            {f"layers.{layer}.{names[layer]}": {} for layer in layers},
            {
                f"layers.{layer}.{names[layer]}": {"v": directions[layer].unsqueeze(0)}
                for layer in layers
            },
        )
        flattened[side] = torch.cat([directions[layer].flatten() for layer in layers])
        energy = torch.cat([direction.square().flatten() for direction in directions.values()])
        standardized_energy = torch.cat([
            torch.where(
                scales[side][layer] > 0,
                (directions[layer] / scales[side][layer]).square(),
                torch.zeros_like(directions[layer]),
            ).flatten()
            for layer in layers
        ])
        sorted_energy = energy.sort(descending=True).values
        total_energy = energy.sum()
        standardized_total = standardized_energy.sum()
        flattened_scales = torch.cat([scales[side][layer].flatten() for layer in layers])
        top_coordinate_index = int(energy.argmax())
        top_coordinate_scale = flattened_scales[top_coordinate_index]
        metadata["sides"][side] = {
            "conditioning_class": "positive" if side == "+C" else "negative",
            "activation_weighted_gradient_norm": activation_norm.item(),
            "shrinkage_weight_sha256": _layer_tensor_sha256(weights),
            "activation_scale_sha256": _layer_tensor_sha256(scales[side]),
            "noisy_coordinate_audit": {
                "n_prompts": n_prompts,
                "current_vs_empirical_bayes_cosine": torch.nn.functional.cosine_similarity(
                    current_unit, eb_unit, dim=0
                ).item(),
                "split_half_cosine": split_half_cosine,
                "zero_fraction": {
                    "current": torch.cat([
                        (current_weights[layer] == 0).flatten() for layer in layers
                    ]).float().mean().item(),
                    "empirical_bayes": torch.cat([
                        (weights_eb[layer] == 0).flatten() for layer in layers
                    ]).float().mean().item(),
                },
                "empirical_bayes_signal_variance": {
                    str(layer): signal_variance[layer].item() for layer in layers
                },
            },
            "direction_sha256": _layer_tensor_sha256(directions),
            "live_coordinates": {
                str(layer): int((weights[layer] > 0).sum()) for layer in layers
            },
            "activation_scale_mean": {
                str(layer): scales[side][layer].mean().item() for layer in layers
            },
            "standardized_intervention_norm": standardized_total.sqrt().item(),
            "layer_energy": {
                str(layer): (directions[layer].square().sum() / total_energy).item()
                for layer in layers
            },
            "top_coordinate_energy": {
                "top1": (sorted_energy[:1].sum() / total_energy).item(),
                "top10": (sorted_energy[:10].sum() / total_energy).item(),
                "top100": (sorted_energy[:100].sum() / total_energy).item(),
                "top1000": (sorted_energy[:1000].sum() / total_energy).item(),
            },
            "top_coordinate_activation_scale": top_coordinate_scale.item(),
            "top_coordinate_activation_scale_percentile": (
                (flattened_scales <= top_coordinate_scale).float().mean().item()
            ),
        }
    metadata["stored_ray_cosine_descriptive_only"] = torch.nn.functional.cosine_similarity(
        flattened["+C"], flattened["-C"], dim=0
    ).item()
    metadata["applied_side_cosine_descriptive_only"] = torch.nn.functional.cosine_similarity(
        flattened["+C"], -flattened["-C"], dim=0
    ).item()
    logger.info(
        "vjp_mlp_up_left_right_shrink target={} layers={} live_plus={} live_minus={}",
        target_layer,
        len(layers),
        sum(metadata["sides"]["+C"]["live_coordinates"].values()),
        sum(metadata["sides"]["-C"]["live_coordinates"].values()),
    )
    return vectors, metadata


def vjp_mlp_up_shared_eb(
    model,
    tokenizer,
    positive_prompts: list[str],
    negative_prompts: list[str],
    *,
    target_layer: int | None = None,
    batch_size: int = 8,
    max_length: int = 384,
    skip_first: int = 16,
) -> tuple[dict[str, Vector], dict[str, object]]:
    """Extract one pair-mean EB VJP ray for opposite-sign application."""
    model.requires_grad_(False)
    if len(positive_prompts) != len(negative_prompts) or len(positive_prompts) < 2:
        raise ValueError("shared EB needs at least two paired persona prompts")
    target_layer = len(_blocks(model)) - 3 if target_layer is None else target_layer
    layers = tuple(range(target_layer))
    cotangent = _target_mean(
        model, tokenizer, positive_prompts, target_layer, batch_size, max_length
    ) - _target_mean(
        model, tokenizer, negative_prompts, target_layer, batch_size, max_length
    )
    positive, _, positive_moments = _class_prompt_vjp_scale(
        model, tokenizer, positive_prompts, layers, target_layer, cotangent,
        batch_size, max_length, skip_first, "mlp.up_proj", return_moments=True,
    )
    negative, _, negative_moments = _class_prompt_vjp_scale(
        model, tokenizer, negative_prompts, layers, target_layer, cotangent,
        batch_size, max_length, skip_first, "mlp.up_proj", return_moments=True,
    )
    pair_means = {
        layer: (positive[layer] + negative[layer]) / 2 for layer in layers
    }
    pooled_scale = _pooled_activation_scale(positive_moments, negative_moments, layers)
    raw, weights, signal_variance = _empirical_bayes_raw(pair_means)
    activation_norm = torch.stack(
        [(pooled_scale[layer] * raw[layer]).norm() for layer in layers]
    ).norm()
    if not torch.isfinite(activation_norm) or activation_norm == 0:
        raise ValueError("shared EB activation-scaled norm is zero or nonfinite")
    directions = {
        layer: pooled_scale[layer].square() * raw[layer] / activation_norm
        for layer in layers
    }
    if not all(torch.isfinite(direction).all() for direction in directions.values()):
        raise ValueError("shared EB direction is nonfinite")

    def unit_direction(candidate_raw: dict[int, torch.Tensor]) -> torch.Tensor:
        direction = torch.cat([
            (pooled_scale[layer].square() * candidate_raw[layer]).flatten()
            for layer in layers
        ])
        norm = direction.norm()
        if not torch.isfinite(norm) or norm == 0:
            raise ValueError("shared EB split direction is zero or nonfinite")
        return direction / norm

    n_pairs = next(iter(pair_means.values())).shape[0]
    split_half_cosine = None
    if n_pairs >= 4:
        split_raw = [
            _empirical_bayes_raw({layer: pair_means[layer][split::2] for layer in layers})[0]
            for split in (0, 1)
        ]
        split_half_cosine = torch.nn.functional.cosine_similarity(
            unit_direction(split_raw[0]), unit_direction(split_raw[1]), dim=0
        ).item()
    names = {layer: "mlp.up_proj" for layer in layers}

    def make_vector() -> Vector:
        return Vector(
            VjpMlpUpSharedEBC(
                layers=layers,
                target_submodule="mlp.up_proj",
                target_layer=target_layer,
            ),
            {f"layers.{layer}.{names[layer]}": {} for layer in layers},
            {
                f"layers.{layer}.{names[layer]}": {"v": directions[layer].unsqueeze(0)}
                for layer in layers
            },
        )

    vectors = {side: make_vector() for side in ("+C", "-C")}
    energy = torch.cat([directions[layer].square().flatten() for layer in layers])
    total_energy = energy.sum()
    standardized_energy = torch.cat([
        torch.where(
            pooled_scale[layer] > 0,
            (directions[layer] / pooled_scale[layer]).square(),
            torch.zeros_like(directions[layer]),
        ).flatten()
        for layer in layers
    ])
    direction_sha256 = _layer_tensor_sha256(directions)
    metadata = {
        "source_readout": "mlp.up_proj",
        "delta_estimator": "destination_conditioned_shared_pair_mean",
        "noisy_coordinate_estimator": "empirical_bayes_normal_normal_per_layer",
        "normalization": "global_pooled_activation_scaled",
        "target_layer": target_layer,
        "source_layers": list(layers),
        "pairing": "mean_of_matched_positive_negative_prompt_vjps",
        "pooled_activation_token_count": (
            int(positive_moments["count"]) + int(negative_moments["count"])
        ),
        "shared": {
            "n_pairs": n_pairs,
            "activation_weighted_gradient_norm": activation_norm.item(),
            "shrinkage_weight_sha256": _layer_tensor_sha256(weights),
            "activation_scale_sha256": _layer_tensor_sha256(pooled_scale),
            "direction_sha256": direction_sha256,
            "split_half_cosine": split_half_cosine,
            "empirical_bayes_signal_variance": {
                str(layer): signal_variance[layer].item() for layer in layers
            },
            "standardized_intervention_norm": standardized_energy.sum().sqrt().item(),
            "layer_energy": {
                str(layer): (directions[layer].square().sum() / total_energy).item()
                for layer in layers
            },
        },
        "sides": {
            "+C": {
                "conditioning_class": "shared_pair_mean",
                "application_sign": 1,
                "direction_sha256": direction_sha256,
            },
            "-C": {
                "conditioning_class": "shared_pair_mean",
                "application_sign": -1,
                "direction_sha256": direction_sha256,
            },
        },
        "stored_ray_cosine_descriptive_only": 1.0,
        "applied_side_cosine_descriptive_only": -1.0,
    }
    logger.info(
        "vjp_mlp_up_shared_eb target={} layers={} pairs={} split_half_cosine={}",
        target_layer,
        len(layers),
        metadata["shared"]["n_pairs"],
        split_half_cosine,
    )
    return vectors, metadata


def vjp_delta(
    model,
    tokenizer,
    positive_prompts: list[str],
    negative_prompts: list[str],
    layers: tuple[int, ...],
    *,
    target_layer: int | None = None,
    batch_size: int = 8,
    max_length: int = 384,
    skip_first: int = 16,
) -> Vector:
    """Extract one normalized VJP-delta direction per source layer."""
    model.requires_grad_(False)
    target_layer = len(_blocks(model)) - 3 if target_layer is None else target_layer
    if max(layers) >= target_layer:
        raise ValueError("source layers must precede the target layer")

    cotangent = _target_mean(
        model, tokenizer, positive_prompts, target_layer, batch_size, max_length
    ) - _target_mean(
        model, tokenizer, negative_prompts, target_layer, batch_size, max_length
    )
    positive = _class_mean_vjp(
        model,
        tokenizer,
        positive_prompts,
        layers,
        target_layer,
        cotangent,
        batch_size,
        max_length,
        skip_first,
    )
    negative = _class_mean_vjp(
        model,
        tokenizer,
        negative_prompts,
        layers,
        target_layer,
        cotangent,
        batch_size,
        max_length,
        skip_first,
    )
    directions = {layer: positive[layer] - negative[layer] for layer in layers}
    stacked = {
        layer: {"v": (direction / direction.norm()).unsqueeze(0)}
        for layer, direction in directions.items()
    }
    config = VjpDeltaC(
        layers=layers,
        target_layer=target_layer,
        skip_first=skip_first,
        cotangent_scope="all_valid",
        source_scope="all_valid",
    )
    return Vector(config, {layer: {} for layer in layers}, stacked)
