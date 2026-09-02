---
requested_model: moonshotai/kimi-k3
max_tokens: 20000
final_tokens: 20000
reasoning_effort: low
input_bytes: 9441
trace: /workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-02_kimi-k3_per-side-eb-pseudocode.trace.jsonl
generated: 2026-09-02T03:43:55.583865+00:00
---

# bounded completion

## First call reasoning

We need answer bounded. Need spot mismatch pseudocode says s2=var/n yes source. But attached also old current weights and split diagnostics, not final. Critical normalization pseudocode Z sqrt(sum ||σ*r||²), source activation_norm ||σ*r||, then directions σ²*r / norm. Wait pseudocode u=σ² r, Z=sqrt sum ||σ r||² yes same.

Potential mismatch variance unbiased vs pseudocode var unspecified. EB formula mathematically odd: tau scalar mean(mu² - noise), weight per coord tau/(tau+s2). Source does this. Intentional asym sides prompts, sigma; shared cotangent. Different outcomes expected. Biggest missing measurement paired comparator behavioral old vs EB under matched doses/random seeds, and perhaps swap audit. Cheapest discriminating measurement? To distinguish bug/asymmetry from estimator: run extraction with identical prompt set both sides? But "first missing measurement before claiming EB caused one-side improvement": matched behavioral ablation old vs EB per side, including dose curves. Cheapest likely compute and evaluate old vector already audit only cosine. Use paired bootstrap? One measurement: same heldout prompts, matched || standardized direction maybe C mapping, compare old-current vs EB each side at fixed C grid. They say don't propose new method unless concrete flaw. This is measurement not method.

Question source authoritative and pseudocode accurately? Mostly but omits legacy current/split audit and exact unbiased. Also file truncated but enough.

Sign apply external not shown in source; source only returns d. Cannot verify apply signs. Say no evidence in shown code. Shared cotangent can make projections differ.

Cheapest discriminating measurement for accidental side asymmetry: swap side labels/prompts while keeping cotangent fixed? If outputs don't swap exactly, asymmetry from side-specific scales/implementation. But different σ means expected no exact swap. A null measurement use same positive prompts as both sides and corresponding scales? _class scales generated per call, deterministic same; then outputs should exactly equal. This cheaply detects hidden side-dependent indexing/sign. Yet required "first missing measurement before claiming EB caused one-side improvement" behavioral ablation.

Could present both: null check and efficacy check, with first priority.

Need decision.
## First call answer

## Decision

Do **not** claim that empirical-Bayes shrinkage caused a one-sided behavioral improvement yet. The shown source has no evident accidental `+C`/`-C` sign, prompt, indexing, or normalization asymmetry. Side-specific results can arise from the stated estimator because the two sides use different prompt gradients and activation scales.

The pseudocode is a valid reduced description of the final EB path, but it omits some implementation details.

## 1. Pseudocode versus source

The final extraction path matches:

- shared cotangent  
  \[
  c=\bar h_{\text{target}}(+)-\bar h_{\text{target}}(-)
  \]
- prompt-level VJPs for each side
- per-side mean \(\mu\)
- noise estimate `var / n_prompts`
- one scalar signal variance per layer:
  ```py
  signal_variance[layer] =
      (means_eb[layer].square() - noise_variance).mean().clamp(min=0)
  ```
- coordinatewise shrinkage:
  ```py
  weights = signal_variance / (signal_variance + noise_variance)
  raw = means * weights
  ```
- numerator:
  ```py
  scales[side][layer].square() * raw[layer]
  ```
- denominator:
  ```py
  norm(concat(scales[side][layer] * raw[layer]))
  ```
  which is equivalent to the stated
  \[
  Z=\sqrt{\sum_l\|\sigma_{l}\,r_l\|^2}.
  \]

Differences/omissions:

1. The source uses `var(..., unbiased=True)`; the pseudocode does not specify the variance convention.
2. The source also computes a legacy “current” direction and split-half current/EB diagnostics. These do not determine the returned vector.
3. The file excerpt does not contain the later `apply(+C, +d)` and `apply(-C, -d)` calls, so the final intervention signs cannot be verified from this attachment alone.

Thus: **mostly accurate for the returned EB vector, incomplete as a full source description.**

## 2. Accidental asymmetry

I see no evidence in the shown code of an accidental `+C` versus `-C` asymmetry.

Both sides pass through the same functions and loop body. There is no visible:

- side-dependent sign flip
- side-dependent layer indexing
- reversed prompt list
- different variance formula
- different shrinkage formula
- different normalization rule
- different use of the shared cotangent

The suspicious-looking differences are intentional inputs: `samples[side]` and `scales[side]`.

One caveat: the external application signs remain unverified because they are outside the shown source.

## 3. Intentional asymmetries

Different outcomes are expected because each side has different:

- prompt-conditioned VJPs
- coordinate means \(\mu_{\text{side},l}\)
- coordinate noise estimates \(s^2_{\text{side},l}\)
- scalar layer signal estimates \(\tau^2_{\text{side},l}\)
- shrinkage weights
- token activation scales \(\sigma_{\text{side},l}\)
- resulting per-layer energy and global normalization

The shared cotangent does **not** make the sides symmetric. It only gives both VJP collections the same readout direction. Projecting different positive- and negative-prompt gradients onto that cotangent can legitimately produce different vectors, different shrinkage, and different behavioral dose-response curves.

Also, the old-to-EB cosines—0.887665 and 0.863008—only say that EB changed `-C` more geometrically. They do not establish better or worse behavior.

## 4. First missing measurement

Before claiming that **EB caused** the one-side improvement, run a matched behavioral ablation of:

- old/current direction versus EB direction
- separately for `+C` and `-C`
- on the same held-out prompts
- over the same coefficient grid, including the previously missing low-dose region
- with the same application convention and damage/effect metrics

The cheapest useful readout is the old-versus-EB `effect − damage` curve at matched \(C\), with prompt-level paired confidence intervals or bootstrap differences. Cosine distance is not a substitute for this.

### Cheap implementation-symmetry check

As a secondary null test, pass the **same prompt set as both `positive_prompts` and `negative_prompts`** while keeping the extraction code otherwise unchanged. The two returned side vectors should then match up to numerical nondeterminism. A mismatch would expose hidden side-dependent handling. Because the cotangent becomes zero under this null, a cleaner variant is to bypass cotangent computation and inject the normal fixed nonzero cotangent while retaining identical prompt sets for both side extractions.

**Bottom line:** the side difference can arise from the stated estimator without a bug. The current evidence does not yet show that EB caused the improvement; it only shows that the EB `-C` vector has a viable behavioral dose region and differs more from its old counterpart geometrically.

## Completion

- outcome: `complete`
- trace: `/workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-02_kimi-k3_per-side-eb-pseudocode.trace.jsonl`
