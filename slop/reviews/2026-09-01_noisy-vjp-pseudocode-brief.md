# Task: choose a mathematically coherent way to reduce noisy VJP coordinates

We have prompt-level VJP samples for each source coordinate:

```py
# g ∈ R[n,d], n=200 persona prompts, per side and layer
μ = mean(g, dim=0)
v = var(g, dim=0, unbiased=True)
σ = std(activation tokens, dim=0)
```

The steering vector is applied to `mlp.up_proj` output. We want a per-coordinate estimator `r(μ,v,n)` that reduces prompt-specific or noisy coordinates, then a separately justified normalization. Existing code uses:

```py
w = clamp(1 - v / μ**2, min=0)
r = μ * w
# applied vector: d = σ**2 * r / ||σ*r||
```

This is destination-conditioned: +C samples use positive prompts; -C samples use negative prompts; the -C stored vector is applied with negative C. Results are weak but admissible on all 100 judged questions. Do not use the judged result as evidence that a formula is mathematically correct.

## Requirements

Propose one or two **distinct** coherent estimators. You may use empirical-Bayes shrinkage, a t-statistic, SNR, robust aggregation, or another standard method. Do not stack several unmotivated penalties.

For each estimator:
1. State a probabilistic model or optimization objective.
2. Give compact Unicode Python pseudocode (not runnable) using `μ`, `v`, `n`, `σ`, `g`.
3. Say whether `n` must enter, and why.
4. Specify interaction with the existing activation-standardized constraint `||d/σ||=1`, whose steepest-ascent solution is `d=σ²r/||σr||`.
5. State one failure mode specific to persona-prompt VJPs.
6. State exactly what extraction-only statistic should decide whether it is worth a DEV generation run.

Then choose one estimator, or say no choice is possible from these data. Do not recommend all-100 judging until a changed vector first passes DEV.

Evidence status: this is method design. No paper citation has been supplied. Mark derivations as derivations and guesses as guesses.

— PI/Codex
