# Extracted from src/vjp_steering/vjp.py, lines 242-295 and 442-516.
# This is the complete weighting path requested for review.

def _class_prompt_vjp_scale(...):
    gradients_by_layer = {layer: [] for layer in layers}
    activation_sum = {layer: None for layer in layers}
    activation_square_sum = {layer: None for layer in layers}
    activation_count = 0
    for batch in batches:
        gradients, valid, activations = _batch_gradients(...)
        mask = valid.unsqueeze(-1)
        counts = valid.sum(dim=1, keepdim=True).float()
        activation_count += int(valid.sum())
        for layer in layers:
            gradient = gradients[layer].float()
            # g_i: pooled VJP for one prompt
            gradients_by_layer[layer].append((gradient * mask).sum(dim=1) / counts)
            activation = activations[layer].double()
            double_mask = mask.to(dtype=torch.float64)
            batch_sum = (activation * double_mask).sum(dim=(0, 1)).cpu()
            batch_square_sum = (activation.square() * double_mask).sum(dim=(0, 1)).cpu()
            activation_sum[layer] = batch_sum if activation_sum[layer] is None else activation_sum[layer] + batch_sum
            activation_square_sum[layer] = batch_square_sum if activation_square_sum[layer] is None else activation_square_sum[layer] + batch_square_sum
    prompt_gradients = {layer: torch.cat(values).cpu() for layer, values in gradients_by_layer.items()}
    activation_scale = {}
    for layer in layers:
        mean = activation_sum[layer] / activation_count
        variance = activation_square_sum[layer] / activation_count - mean.square()
        activation_scale[layer] = variance.clamp(min=0).sqrt().float()
    return prompt_gradients, activation_scale


def vjp_mlp_up_left_right_shrink(...):
    """Extract destination-conditioned MLP-up rays with per-side shrinkage and scale."""
    cotangent = _target_mean(positive_prompts) - _target_mean(negative_prompts)
    positive, positive_scale = _class_prompt_vjp_scale(positive_prompts, cotangent, ...)
    negative, negative_scale = _class_prompt_vjp_scale(negative_prompts, cotangent, ...)
    samples = {"+C": positive, "-C": negative}
    scales = {"+C": positive_scale, "-C": negative_scale}
    for side in ("+C", "-C"):
        means = {layer: samples[side][layer].mean(0) for layer in layers}
        weights = {
            layer: (
                1
                - samples[side][layer].var(0, unbiased=True)
                / means[layer].square().clamp(min=1e-30)
            ).clamp(min=0)
            for layer in layers
        }
        raw = {layer: means[layer] * weights[layer] for layer in layers}
        activation_norm = torch.stack(
            [(scales[side][layer] * raw[layer]).norm() for layer in layers]
        ).norm()
        directions = {
            layer: scales[side][layer].square() * raw[layer] / activation_norm
            for layer in layers
        }
        # Diagnostic only: standardized_energy = sum((directions / scales)^2)
