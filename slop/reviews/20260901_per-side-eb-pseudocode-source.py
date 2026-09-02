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

        def empirical_bayes_raw(prompt_gradients: dict[int, torch.Tensor]):
            means_eb = {layer: prompt_gradients[layer].mean(0) for layer in layers}
            variances_eb = {
                layer: prompt_gradients[layer].var(0, unbiased=True) for layer in layers
            }
            n_prompts = next(iter(prompt_gradients.values())).shape[0]
            raw_eb, weights_eb, signal_variance = {}, {}, {}
            for layer in layers:
                noise_variance = variances_eb[layer] / n_prompts
                signal_variance[layer] = (means_eb[layer].square() - noise_variance).mean().clamp(min=0)
                weights_eb[layer] = signal_variance[layer] / (signal_variance[layer] + noise_variance)
                raw_eb[layer] = means_eb[layer] * weights_eb[layer]
            return raw_eb, weights_eb, signal_variance

        def unit_standardized_direction(candidate_raw: dict[int, torch.Tensor]):
            direction = torch.cat([
                (scales[side][layer].square() * candidate_raw[layer]).flatten()
                for layer in layers
            ])
            norm = direction.norm()
            if not torch.isfinite(norm) or norm == 0:
                raise ValueError(f"mlp-up {side} candidate direction is zero or nonfinite")
            return direction / norm

        raw_eb, weights_eb, signal_variance = empirical_bayes_raw(samples[side])
        current_unit = unit_standardized_direction(raw_current)
        eb_unit = unit_standardized_direction(raw_eb)
        raw = raw_eb
        weights = weights_eb
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
            split_raw_eb, _, _ = empirical_bayes_raw(split_samples)
            split_eb.append(unit_standardized_direction(split_raw_eb))
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
                "n_prompts": next(iter(samples[side].values())).shape[0],
