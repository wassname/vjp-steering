# Question

Audit the mathematical and implementation correctness of the coordinate weighting and normalization in `vjp_mlp_up_left_right_shrink`. Do not judge prose or suggest a new broad method. We need the next discriminating test before spending more GPU or judging calls.

## Context

We want a vector that increases a target direction (+C) using positive persona prompts and decreases it (-C) using negative persona prompts. At target layer T:

```
c = mean(h_T | positive) - mean(h_T | negative)
```

For a source layer L and prompt i, we pool a VJP over valid prompt tokens:

```
g_i = mean_token [ d <h_T, c> / d up_proj_L ]
μ = mean_i(g_i)
v = Var_i(g_i)
w = max(0, 1 - v / μ²)
r = μ ⊙ w
σ = Std_token(up_proj_L activations), pooled over the destination class
N = sqrt(sum_L ||σ ⊙ r_L||²)
implemented intervention d_L = σ² ⊙ r_L / N
```

The intervention hook adds `C * d_L` to `mlp.up_proj` output. The +C vector uses positive prompts. The -C vector uses negative prompts and is applied at coefficient `-C`.

The name `global_activation_scaled` describes the intended normalization, but it has no cited mathematical definition in this repo.

## Observed judged result

A fresh extraction after fixing an extra special-token leak was judged on 100 fixed questions with both AB and BA display orders (one pass each). Both sides are health-admissible:

```
+C: effect +0.4525, off-axis damage 0.6510
-C: effect -0.7915, off-axis damage 0.6375
```

Its aggregate table score is -0.199. Existing baselines have much better on-axis effect at similar/lower damage. This is a weak method result, but it does not itself determine the formula is wrong.

A trial changing the implemented `σ²` to `σ` produced no DEV-admissible -C dose. That is one noisy, coarse-grid result, not a derivation.

## Required review

1. Derive which of `r/N`, `σ r/N`, or `σ² r/N` is consistent with each plausible objective or constraint:
   - Euclidean intervention norm;
   - activation-standardized norm `||d/σ||`;
   - activation-weighted norm `||σ d||`;
   - diagonal Fisher / inverse-variance preconditioning.
2. Identify whether the formula currently has an internal contradiction: the stated normalization is `N=||σr||`, but applied direction is `σ²r/N`.
3. Assess the shrinkage factor `max(0, 1 - Var(g)/mean(g)^2)`: what estimator/prior would justify it? Is `n=256` absent incorrectly? Would a t-statistic or Fisher/SNR weight give a coherent alternative? Explain whether they are variants rather than a bug fix.
4. Propose exactly one low-cost, discriminating calculation using already saved extraction tensors or a fresh extraction metadata run. It must decide between formula interpretations before generation/judging.
5. Report findings by severity (P0 correctness error, P1 unsupported convention, or no bug). Quote the exact relevant source line(s) from attached code.

Be concise and explicitly distinguish derivation from speculation.

— PI/Codex
