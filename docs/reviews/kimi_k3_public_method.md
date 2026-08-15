# Review: VJP-delta steering method

## 1. Central assumption and how it fails silently

The load-bearing assumption is that **the mean difference of per-prompt VJPs recovers a causally usable direction**: i.e., that the direction by which a perturbation at layer `l` increases the last-layer projection onto `c` is (a) stable across prompts (so averaging is meaningful) and (b) the direction in which you should *add* activation to move behavior toward/away from the contrast.

This can fail silently in several ways:

- **Gradient magnitude confound.** A VJP is a local linear sensitivity, not a feature direction. Prompts with large local Jacobian norm dominate the mean, so `q[P, l]` may reflect *which prompts are sensitive*, not *what direction encodes sycophancy*. The resulting vector can steer fluently (judged on-axis movement) by exploiting output-distribution sensitivity rather than by removing the target behavior — the judge sees change, the mechanism is wrong.
- **Near-cancellation blow-up.** `v[l] = (q_pos − q_neg) / ‖q_pos‖` divides by the norm of one term only. If `q_pos ≈ q_neg` (plausible if the contrast is weak at layer `l`), the difference is noise amplified by `1/‖q_pos‖`, and the noise inherits a large, layer-varying scale. Nothing in the pipeline detects this; the renderer checks metadata, not geometry.
- **Position/direction mismatch.** `c` is computed from *last-token* hidden states, but the loss `sum(H[T]·M·c)` applies `c` to every masked mid-sequence position. If `c` is only a meaningful contrast direction at the final position, the VJP measures sensitivity of arbitrary token positions to a direction that may not be expressed there — and no error is raised.
- **Recovery of the baselines.** If the model's Jacobian is approximately prompt-independent, the VJP-delta reduces to a fixed linear preimage of `c` — a rescaled, smeared version of mean difference. The method then "works" but the claim that VJP adds anything over mean difference is false, and a frontier plot alone won't reveal the equivalence without a cosine-similarity check between vectors across methods.

## 2. Do the cohort, seeds, and caps address the major confounds?

Partially.

- **All-100** correctly removes the selected-20 cherry-pick. Good.
- **Seeds on random directions** are necessary but insufficient as specified. The band must be over the *same max-statistic* used for the real methods — "best on-axis effect at each damage budget" is a maximum over C-values, layers, and seeds, which inflates upward. If the random band is computed per-point while the VJP curve is a max over arms, the comparison is rigged in VJP's favor. Equally: random directions must be **norm-matched per layer** to the VJP/baseline vectors, otherwise coefficient grids are not comparable across methods and the "same damage budget" axis is meaningless.
- **Coefficient grids.** "Several fixed coefficients per method" with best-at-budget selection means the method with the densest or luckiest grid wins. The comparison should be damage-matched by interpolation, or the grid must be pre-registered and identical in effect-relevant units (e.g., multiples of vector norm / residual-stream RMS), which it currently is not because of the asymmetric normalization (§3).
- **Output caps introduce the confound they claim to remove.** Rejecting broken rows and recording only passing rows is **survivorship bias**: a method that destroys outputs at moderate C gets its failures censored, so its *conditional* effect/damage looks clean exactly where it should look catastrophic. Rejected rows must enter the record as maximal damage (or as a separate reported rejection rate per arm), not be filtered. "Excess prefill NLL" is additionally method-correlated — steering changes NLL — so the cap censors asymmetrically across methods.
- **Not addressed:** judge effects. A "blinded judge's difference from bare" requires that bare and steered be presented in randomized order within a pair, that the orientation sign be fixed *before* seeing results (a post-hoc sign flip per side is a researcher degree of freedom), and ideally that all methods for a question be judged in one blinded batch to prevent cross-arm drift. None of this is specified.
- **Not addressed:** multiple comparisons across methods × layers × C × sides. One pre-registered damage budget, or a max-statistic band, is needed.

## 3. Is the VJP reduction and normalization internally consistent?

No. Three concrete defects:

1. **Batch-weighting bug.** `q[P,l] += batch_mean(...)` followed by `q[P] /= len(P)` divides by the *number of prompts*, not the number of batches. If `|P_pos| ≠ |P_neg|` or the last partial batch differs, each batch mean gets equal weight regardless of how many prompts it contains — partial batches are overweighted, and the two classes are averaged under different effective weights. The scale only cancels in `v` if batching is identical across classes; the design doesn't enforce that.
2. **Token- vs prompt-weighting inconsistency.** Within a batch, the reduction is a mean over valid tokens; across batches, a mean of batch means. Long sequences are underweighted relative to a per-prompt mean. Either weighting is defensible; mixing them silently is not, and it interacts with bug (1).
3. **Asymmetric, degenerate normalization.** Dividing `q_pos − q_neg` by `‖q_pos‖` alone means swapping class labels changes the vector's *magnitude*, not just its sign — the steering scale per layer is an arbitrary ratio, so a single global C applies different effective strengths per layer in a way that differs between the `+C` and `−C` sides only through noise. And there is no unit-norm guarantee feeding into the coefficient grid, which undermines cross-method comparability (§2). If `T ∈ L`, note also that `G[T] = c·M` exactly, so `q_pos[T] = q_neg[T]` and `v[T] = 0` — a silent no-op layer that the metadata renderer will happily certify.

## 4. Smallest additional control that materially improves the claim

**Label-shuffled VJP**: run the identical VJP-delta pipeline — same prompts, layers, masks, C grid, judge — with `P_pos`/`P_neg` assignments randomly permuted (or equivalently with `c` replaced by a random direction of the same norm at layer `T`). 

This is the cheapest control that separates "the contrast signal is doing the work" from "the gradient machinery itself produces high-utility steering directions" (e.g., via gradient-magnitude weighting of intrinsically sensitive tokens). If shuffled-label VJP also lands outside the random band or dominates mean difference, the paper's mechanism claim is dead even if the headline curve looks good. Without it, the result is uninterpretable at the mechanism level.

## 5. One concrete UAT condition that blocks publication

**Pre-registered frontier test with failure counted:** On the full all-100 × 3-seed run, at one pre-registered damage budget (fixed before unblinding, e.g., the median damage of mean difference at its best C), VJP-delta's on-axis effect must exceed (a) the mean-difference and PCA frontiers interpolated to that budget, and (b) the *maximum over the three seeds* of the norm-matched random-direction frontier — with cap-rejected rows counted as worst-case damage rather than dropped, and the shuffled-label VJP control required to fall inside the random band. Failure of any clause — including "the VJP vectors turn out to have cosine similarity > 0.9 with the mean-difference vectors" — blocks publication of the claim that VJP-delta improves on the baselines.