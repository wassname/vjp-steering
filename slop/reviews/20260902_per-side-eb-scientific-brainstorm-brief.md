# Scientific brainstorm question

We need a conceptual review of a per-side VJP steering method. Do not limit the answer to code correctness. Brainstorm scientifically plausible intended and unintended outcomes, competing mechanistic explanations, and tests that discriminate among them. Treat the measured data as observations, not proof of causality.

## Method

Model: Qwen/Qwen3.5-4B. We use 200 paired positive/sycophantic and negative/abrasive prompts. First form one target hidden-state contrast:

```py
c = mean(h_target(positive_prompts)) - mean(h_target(negative_prompts))
```

Then extract one prompt-level VJP for every prompt, conditional on its own prompt tokens but using the shared target cotangent `c`:

```py
for side in ("+C", "-C"):
    g = prompt_vjps(prompts[side], cotangent=c)   # n × source_layers × d
    for layer in source_layers:
        μ = mean(g[:, layer], axis=0)
        s2 = var(g[:, layer], unbiased=True, axis=0) / n
        τ2 = max(mean(μ**2 - s2), 0)              # one scalar per layer
        w = τ2 / (τ2 + s2)                        # one weight per coordinate
        r = μ * w
        u[layer] = σ[side, layer]**2 * r
    Z = sqrt(sum_layer ||σ[side, layer] * r[layer]||²)
    d[side, layer] = u[layer] / Z

apply(+C, +d["+C"])
apply(-C, -d["-C"])
```

`σ` is token-level standard deviation of the source activations, measured separately for each side. The attachment is the authoritative source slice.

The preceding estimator hard-shrunk each coordinate using `max(0, 1 - Var(g)/mean(g)^2)`. The current empirical-Bayes (EB) estimator changes it to the formula above, using variance of the sample mean `Var(g)/n` and a layer-level signal-variance estimate.

## Observations

- EB direction differs from prior estimator: cosine is +C 0.887665 and -C 0.863008. This is a geometric observation only.
- Full AB/BA judged curve, current EB vector:
  - -C best accepted measured point: effect -0.968, damage 0.416 at C=16.
  - +C final accepted point: effect +3.4665, damage 1.129 at C=44.064.
- Initial -C grid only started at C=28.6 and failed health acceptance. New lower-dose measurements found the accepted -C region. Therefore the prior missing -C public curve was a dose-coverage error, not direct evidence that EB failed on -C.
- A different baseline VJP method (`vjp_delta`) has stronger overall published results. The per-side EB method differs from it in more than shrinkage, including per-side extraction and normalization.

## Requested analysis

1. Explain the causal story the method appears to assume. Which parts are strong assumptions rather than consequences of VJP or EB?
2. Brainstorm at least five distinct mechanisms by which +C and -C can legitimately have different behavioral dose-response curves. Include mechanisms from nonlinear model geometry, class-conditioned Jacobians, prompt distributions/token lengths, activation normalization, estimator SNR, and evaluator semantics where relevant.
3. Identify likely unintended objectives or failure modes. Examples to assess: changing generic agreement/harshness rather than the desired trait; shared cotangent mismatch for the negative class; EB changing sparsity or layer allocation rather than simply “removing noise”; side-specific σ turning the two vectors into different metrics; saturation or threshold behavior; paired samples ignored in variance estimation.
4. For each promising mechanism, give an observation that would support it and one economical discriminating test. Do not give a shopping list of generic ablations; rank the three most informative tests.
5. Consider whether a paired estimator or a joint/two-sided extraction could better express the intended scientific object. State the exact hypothesis it would test, potential benefit, and what it could confound. This is brainstorming, not a request to implement it.
6. Assess whether “EB helped one side more” is even a coherent expected claim under this design. If not, state what narrower claim is justified.

Label observations, inferences, and speculation separately. Be concrete and challenge the premise where needed.

— PI/Codex
