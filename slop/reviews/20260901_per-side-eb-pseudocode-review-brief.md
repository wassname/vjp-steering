# Review question

Review the per-side empirical-Bayes VJP pseudocode and attached implementation. Identify any mathematical or coding mismatch, especially an unintended +C/-C asymmetry. State whether the side difference can arise from the stated estimator without a bug. Give one cheapest discriminating measurement. Do not propose a new method unless it follows from a concrete flaw.

## Context

The model is Qwen/Qwen3.5-4B. We extract two steering vectors from 200 paired prompts. `+C` uses positive prompts and `-C` uses negative prompts. Both use a shared target cotangent:

```py
c = mean(h_target(positive_prompts)) - mean(h_target(negative_prompts))
```

For each side, `g[i, layer, coordinate]` is the prompt-level VJP of the shared target with respect to `mlp.up_proj` activations. The code calculates:

```py
for side in ("+C", "-C"):
    g = prompt_vjps(prompts[side], cotangent=c)   # n x layers x d, n=200
    for layer in layers:
        μ = mean(g[:, layer], axis=0)
        s2 = var(g[:, layer], axis=0) / n
        τ2 = max(mean(μ**2 - s2), 0)
        w = τ2 / (τ2 + s2)
        r = μ * w
        u[layer] = σ[side, layer]**2 * r
    Z = sqrt(sum_layer ||σ[side, layer] * r[layer]||²)
    d[side, layer] = u[layer] / Z
apply(+C, +d["+C"])
apply(-C, -d["-C"])
```

`σ` is the token-level activation standard deviation. `τ2` is a scalar per layer; `s2` and `w` are per-coordinate. The attached source is authoritative.

## Observed result

The all-100 AB/BA curve now has accepted points on both sides. The apparent earlier -C failure was caused by an unmeasured low-dose region, not a missing vector. The current method's best -C point is effect -0.968 and damage 0.416 at C=16. Its +C end point is effect +3.466 and damage 1.129 at C=44.064.

The extraction audit reports old-to-EB direction cosine 0.887665 for +C and 0.863008 for -C. This says EB changed -C more geometrically, but it is not a behavioral ablation.

## Required answer

1. Does the pseudocode accurately represent the source?
2. Is there any accidental sign, normalization, indexing, prompt, or variance asymmetry?
3. Which intentional asymmetries make different side outcomes expected?
4. What is the first missing measurement needed before claiming EB caused a one-side improvement?

— PI/Codex
