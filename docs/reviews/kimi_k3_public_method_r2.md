# Re-evaluation with corrected implementation

## 1. Batch weighting — **withdrawn**

Per-prompt accumulation followed by division by `len(P)` is a proper prompt-level mean. Partial batches contribute their actual prompt count; the two classes are weighted identically regardless of batching. The within-prompt reduction (mean over valid tokens per prompt, then mean over prompts) is now a consistent prompt-weighted estimator. No residual concern here.

## 2. Normalization — **withdrawn as stated; one weakened residual**

Dividing by `‖q_pos − q_neg‖` makes every layer vector unit norm. Label-swapping now flips only the sign, and per-layer effective steering strength is symmetric across `+C`/`−C` sides. The "arbitrary per-layer scale ratio" finding is withdrawn.

Residual, restated: the near-cancellation case no longer produces *amplified* noise, but it still produces a *pure-noise direction* — when `q_pos ≈ q_neg`, the unit vector is whatever the gradient noise happens to point at. However, this now fails **gracefully rather than silently**: a noise direction should behave like a seeded random direction and land inside the random band, which is exactly what your falsification criterion is built to detect. So this is no longer a silent failure mode — the design absorbs it. A logged per-layer `‖q_pos − q_neg‖` diagnostic would still be cheap insurance, but it is not a blocker.

## 3. Target-layer no-op — **withdrawn**

If source layers strictly precede the target layer, the degenerate `G[T] = c·M ⇒ v[T] = 0` case cannot occur. Worth one sentence in the README stating the constraint, since the renderer checks metadata but not layer ordering — but the finding itself is withdrawn.

## 4. Coefficient grids — **largely withdrawn; one restated fragment**

Since the x-axis is measured judged damage rather than nominal C, and frontier selection is best-effect-at-or-below-damage *within* each method, grids no longer confer a cross-method advantage in axis units, and grid density only affects how finely a method's own curve is traced. The comparability finding is withdrawn.

Restated fragment: best-at-or-below-damage is a **maximum over noisy judged points**, and the expected max of noise grows with the number of evaluated arms. If VJP-delta runs more (C, layer-set) arms than mean difference or PCA, it gets more draws at lucky judge noise near the frontier. The random band handles this correctly *for the random comparison* (same max-statistic per seed — see §5), but the baseline curves must be constructed with a comparable number of evaluated arms, or the max-statistic must be corrected. This is a design-constraint restatement, not a fatal flaw.

## 5. Random band — **withdrawn**

Applying the same per-seed best-effect-at-or-below-damage frontier construction to each random seed is precisely the correct max-statistic band. Combined with unit-norm layer vectors (§2), the norm-matching concern also collapses: all methods now steer in units of unit-norm vectors, and any residual difference in effective steering strength per unit C is absorbed by the fact that comparison happens on the measured-damage axis, not the C axis. Withdrawn in full.

(Note on the cosine-similarity point: dropping it as *evidence* is fine. It was proposed as a diagnostic, not a claim; the shuffled-label control below covers the mechanism question more directly anyway.)

---

## Strongest remaining publication blocker

**Output-cap censoring is still unaddressed, and it biases the exact frontier the claim rests on.**

The validity caps reject rows exhibiting repetition, loops, length distortion, answer failure, echo, unfinished text, or excess prefill NLL. Two problems compound:

1. **Rejection is method- and coefficient-correlated.** Steering-induced degeneration is precisely what the damage axis is supposed to capture. A method that breaks outputs at moderate C has those arms silently removed; its surviving conditional frontier looks clean exactly where its unconditional behavior is catastrophic. Worse, the prefill-NLL cap is mechanistically coupled to steering itself — steered models shift NLL — so censoring rates differ across methods *by construction*, not just by accident.
2. **The frontier is a max.** Censoring removes points asymmetrically from the high-damage region, and best-at-or-below-damage then interpolates over a survivorship-filtered set. This directly inflates the apparent damage-efficiency of whichever method trips the caps most.

**Concrete UAT condition:** every evaluated arm — including cap-rejected ones — must appear in the CSV with a rejection flag, and the published frontier must be computed with rejected rows counted as worst-case damage (or equivalently, reported as a per-arm rejection-rate curve alongside the frontier, with the claim shown to survive both treatments). If VJP-delta's frontier dominance holds only when rejected rows are dropped, publication of the dominance claim is blocked.

**Runner-up (fix before running, it's cheap):** the on-axis orientation sign per direction side must be fixed *before* the judge sees any outputs, and bare/steered presentation order within each judged pair must be randomized. A post-hoc sign choice is a researcher degree of freedom applied at the final measurement step, and unlike the caps it costs nothing to pre-register.