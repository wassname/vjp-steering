# Gradient-pursuit implementation check

— PI/OpenAI Codex

## Source

TransformerLens' independent implementation says its `gradient_pursuit` option “matches the update used in the paper”: [`jacobian_lens_decomposition.py`](https://github.com/TransformerLensOrg/TransformerLens/blob/2a05c15df238caf8b7869188ea27b5d39a903d35/transformer_lens/tools/analysis/jacobian_lens_decomposition.py). This is not code published by the paper authors. Anthropic's [`jacobian-lens`](https://github.com/anthropics/jacobian-lens) repository contains lens fitting and inference but no concept-decomposition implementation.

The independent implementation selects a new dictionary item on each iteration:

> `for chosen in selected:`
> `    correlation[chosen] = float("-inf")`
> `candidate = int(torch.argmax(correlation).item())`

It stops when no unused item has materially positive residual correlation:

> `if float(correlation[candidate].detach()) <= correlation_tol:`
> `    break`

It then updates all selected coefficients with one projected-gradient step and reduces the step if projection onto nonnegative coefficients increases reconstruction error:

> `candidate = (coefficients + step * direction).clamp_min(0.0)`
> `if candidate_residual_squared <= current_residual_squared:`
> `    return candidate`
> `step *= 0.5`

## Local discrepancy and correction

The implementation used by task 348 did not mask previously selected dictionary items, had no correlation stopping condition, and had no post-projection step reduction. It could spend several of its 16 iterations updating an existing support instead of selecting up to 16 distinct items. Therefore task 348 did not test the intended gradient-pursuit decomposition.

The corrected local implementation matches TransformerLens' `gradient_pursuit` reconstruction and active support on five seeded synthetic problems:

> `GRADIENT_PURSUIT_PARITY_PASS cases=5 implementation=TransformerLens-gradient_pursuit reconstruction=true`

The parity check is saved at [`../logs/20260906_j_lens_native/gradient-pursuit-parity.log`](../logs/20260906_j_lens_native/gradient-pursuit-parity.log).
