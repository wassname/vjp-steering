---
requested_model: anthropic/claude-fable-5.1
max_tokens: 20000
final_tokens: 20000
reasoning_effort: low
input_bytes: 9441
trace: /workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-02_claude-fable-5.1_per-side-eb-pseudocode-fable51.trace.jsonl
generated: 2026-09-02T03:52:15.410071+00:00
---

# bounded completion

## First call reasoning

I'm comparing the source implementation against the pseudocode formulas for signal variance, activation norm, and directions, and confirming they match term by term.

One asymmetry I'm noting is that scales[side] uses per-side σ statistics computed independently for positive and negative prompts, so each side's direction gets standardized by different activation stats — that seems intentional but worth flagging. For sign convention, +C's gradient is computed at the positive-prompt linearization point while -C's gradient uses the negative-prompt point, which are genuinely different Jacobians rather than a bug, though it raises the question of whether the resulting signal variance τ² could differ in magnitude between sides if gradient scales aren't symmetric.

I'm also noticing that the "current_weights" audit formula uses a coordinate-wise variance ratio without dividing by n, unlike the EB estimator which does divide by n — so comparing the two cosines (0.887 vs 0.863) is comparing against an estimator with mismatched noise scaling, confounding that particular audit check even though it doesn't affect the actual vector construction. The file also appears to cut off mid-metadata, but since the vector is already fully built before that point, the truncation doesn't affect the result.

The pseudocode looks faithful to the source, modulo that truncation and a couple unseen helper functions. Any side-to-side asymmetry (different cosines, different effect magnitudes at +3.466 vs -0.968, different max dose ranges of 16 vs 44) looks intentional rather than buggy — arising from per-side linearization points, per-side variance/shrinkage, and simply non-comparable dose ranges rather than a mismatch in the code itself. The next useful check would be a behavioral ablation comparing the old non-EB vector against the same held-out prompt set.

I should also try flipping the sign, applying the negative of the +C vector on the -C side, to check whether the discrepancy stems from the vector itself or the side it's applied on. Now I need to settle on a decision, note any objections, and lay out what to check next.


## First call answer

**Decision:** The pseudocode faithfully represents the visible source, and I find no accidental +C/−C asymmetry. The side difference (cosines 0.888 vs 0.863; effect +3.47 vs −0.97) is fully explainable by the stated estimator plus dose mismatch, so no EB-caused one-side improvement can be claimed yet.

**1. Pseudocode vs source.** Match on every line that matters: `noise_variance = var(unbiased)/n` = `s2`; `signal_variance = (μ² − s2).mean().clamp(0)` = scalar `τ2`; `w = τ2/(τ2+s2)` per coordinate; `raw = μ·w`; `Z = ‖stack(‖σ·r‖_layer)‖`; `d = σ²·r/Z`. Both sides go through identical closures with `samples[side]`, `scales[side]`. Omissions from pseudocode are benign: `skip_first=16` token skip, `unbiased=True`, `clamp(min=1e-30)` (only in the old comparator), and the file truncates mid-metadata after `vectors[side]` is already built. `_class_prompt_vjp_scale` is not shown, so sign/indexing inside the VJP itself is unverified from this file — but it's called with identical arguments except the prompt list, so any bug there would be side-symmetric.

**2. Accidental asymmetry.** None in the shrink/normalize path. Sign: `+d["+C"]` and `-d["-C"]` are both correct given a shared `c = pos − neg` (gradient on negative prompts pushes toward `c`; negating pushes away). Prompts: n=200 both sides. Variance: same formula. One real confound, not a bug in the vector: the "old" comparator uses `1 − var/μ²` (per-coordinate, *not* divided by n) while EB uses `var/n`. The old-to-EB cosine therefore mixes "EB effect" with "n-fold noise-scale change" and cannot be read as EB changing −C more in any meaningful sense.

**3. Intentional asymmetries that predict different outcomes.**
- Different linearization points: −C VJPs are Jacobians evaluated on negative prompts, +C on positive. The model is nonlinear; gradient magnitude and SNR differ by side.
- Per-side `σ[side]` (from each side's own activations) enters both `Z` and `d`.
- Per-side `τ2`: the scalar is set by `mean(μ²)` relative to `s2`. Whichever side has lower gradient SNR gets more shrinkage → larger geometric change from raw mean → lower cosine. 0.863 < 0.888 is exactly this.
- Dose: −C best point is at C=16, +C endpoint at C=44. Effect magnitudes at unequal C are not comparable evidence of side asymmetry.

So yes: the side difference can arise from the stated estimator with no bug.

**4. Strongest objection to my reading:** `_class_prompt_vjp_scale` is unseen; a hidden per-class sign or skip-token difference there would be side-symmetric only if `positive_prompts`/`negative_prompts` have similar length distributions. If negative prompts are systematically shorter (fewer tokens after `skip_first=16`), effective n per side differs and `σ` estimates differ — still "intentional" in code but unstated.

**Cheapest discriminating measurement:** Run the *old* (non-EB) −C vector on the same all-100 AB/BA set at exactly C=16 (and the two neighboring accepted doses). If effect/damage ≈ −0.97/0.42, the −C "improvement" was the dose-grid fix, not EB; only if old-−C is clearly worse at matched C does EB get credit. This is one extra ablation reusing existing vectors and grid — no new extraction.

## Completion

- outcome: `complete`
- trace: `/workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-02_claude-fable-5.1_per-side-eb-pseudocode-fable51.trace.jsonl`
