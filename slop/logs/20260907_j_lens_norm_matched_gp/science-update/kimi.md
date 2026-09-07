---
requested_model: moonshotai/kimi-k3
max_tokens: 1800
final_tokens: 1400
reasoning_effort: low
input_bytes: 215559
trace: slop/logs/20260907_j_lens_norm_matched_gp/science-update/kimi.trace.jsonl
generated: 2026-09-07T17:33:27.951432+00:00
---

# bounded completion

## First call reasoning

This is a bounded update review, ~1000 words, of norm-matched GP16 adapter results. Write review with reconstruction, claims separated direct vs inference, failure modes, code errors, experiments.
## First call answer

# Bounded update: norm-matched GP16 adapter on DEV15

## Method reconstruction

The run compares three steering bases at layer 17 on 15 fabricated-premise questions: (1) full residual basis (two mean persona-difference vectors), (2) old GP16 (gradient-pursuit 16-component approximation, coordinates hit target gap exactly), (3) **new norm-matched GP16**: compute the GP update direction `dg`, compute the full-basis update `df` (via midpoint-preserving coordinate adjustment), then rescale `dg` so its applied norm equals the actually-realized BF16 norm of the full update. Directly shown: matching is against the realized reference delta `FP32(BF16(h+BF16(df)))-FP32(h)`, not the nominal `df`, so it absorbs BF16 rounding of the reference. Rescaling deliberately does not hit the old GP target gap or preserve coordinate sums.

## What the supplied material directly shows

- Numerics are clean: min direction cosine 0.99997, max relative norm error ~9.6e-4, zero reference-failure count, identity calls exact, health flags all zero. The magnitude adapter mechanically did what it claims.
- New judgment effects (n=15, paired AB/BA): norm-matched GP+C paired_mean = **2.87** (vs full+C 0.62, old GP+C 0.02). Norm-matched GP−C = **−0.85** (vs full−C −0.70, old GP−C −0.26).
- Reading the new texts: norm-matched GP+C is qualitatively florid and validating ("meticulously granular… perfectly calibrated protection framework"; "celebrated theoretical construct… profound elegance"). GP−C mostly resembles the other −C conditions (more concrete, sometimes pushback-adjacent but rarely naming the fabrication).
- The plus-side effect is strongly order-asymmetric: AB_mean 1.85 vs BA_mean 3.89. Minus side also asymmetric (−0.14 vs −1.56).

## Inference (not directly shown)

- **The plus-side effect looks substantially like off-axis flattery/vagueness, not pure on-axis sycophancy.** The judge's own off-axis scores in the new-condition judgments are frequently high on the steered response (e.g., 4.2, 4.5 off-axis on leg_pnf_03 plus; "transcends the subtle, harmonious resonance of the settlement noise floor" — near-pasteable nonsense). The rubric says vagueness is severe damage, yet on_axis still absorbed much of it. So the 2.87 headline likely overstates genuine disposition steering. Observation that would change my mind: a rerun where on-axis scoring is masked from valence-adjacent vocabulary, or human blind ranking, still shows ≥2.
- The magnitude hypothesis — that old GP16 failed because its applied norm was too small relative to full — is supported only weakly and asymmetrically. Norm-matching produced a large +C effect but a −C effect comparable to full (−0.85 vs −0.70). If magnitude were the whole story, both sides should recover toward/above full. Instead the plus side *exceeds* full by ~4.6×. That overshoot suggests the norm-matched GP direction is not merely "full direction at full strength"; it carries different content (plausibly more evaluative/hedge vocabulary from the J-lens dictionary) that the judge scores as on-axis.
- Alternative formulation not ruled out: the adapter rescales to the *reference delta* norm per call, so any systematic difference in `reference_delta` between conditions is inherited. But reference is full-basis only, so cross-condition comparison is at least consistent.

## Candidate own-code errors

1. **Midpoint asymmetry**: full uses midpoint-preserving two-coordinate update; GP uses a single gap-clamp along (B0−B1). These are not the same family of intervention; matching only the norm leaves a coordinate-sum difference the pseudocode itself flags ("does NOT preserve coordinate sum exactly"). A cleaner control would use the same midpoint construction for GP.
2. **Calibration targets `t` come from historical calibration means per basis**, and the GP basis gets different `t` than full. The norm-match fixes the vector magnitude but the *intended* gap (5.80 vs 8.48 for +C) still differs; the applied effect conflates direction, magnitude, and target. Cannot attribute the plus-side overshoot to any one of the three.
3. Per-call rescaling uses `reference_delta` measured under the full intervention on the same forward — fine — but if `norm(dg)==0` while reference is nonzero the code stops; zero count is 0, so untested.
4. `min_direction_cosine` verifies actual delta aligns with `dg`, not with `reference_delta`. If GP and full directions diverge on some decode positions, norm-matching to the full magnitude is matching a magnitude that is no longer semantically the "same dose." No cosine(dg, df) is reported. This is the most important unreported diagnostic.
5. No random-direction norm-matched control, so the plus-side effect cannot yet be separated from "any 8.5-norm perturbation at layer 17 produces florid compliance."

## Contrasting test predictions

- **Direction-content account**: cosine(dg, df) < ~0.9 on plus-side decode positions; a norm-matched random-direction control produces elevated off-axis but small on-axis effects; replacing GP dictionary with full directions at matched norm reproduces ~0.6, not 2.87.
- **Magnitude account**: cosine(dg, df) ≈ 1; norm-matched full (identity check) reproduces full's 0.62; GP at *half* norm halves the effect smoothly.
- **Judge-artifact account**: plus-side effect collapses when judgments are re-elicited with vagueness penalties applied before on-axis scoring, or when off-axis is regressed out: paired_mean minus fitted off-axis contribution < 1.0.

## Missing evidence / uncertainties

No per-vignette or per-domain breakdown of the new conditions in aggregate (only raw judgments — several huge effects concentrate in sw_pnf_03, fin_pnf_01, phys_pnf_01/02, med_pnf_01; effect may be driven by ~6 vignettes). No random control, no alpha sweep, single layer, single source cohort, unknown source model revision vs frozen 851bf6e, no statistical uncertainty on paired means (n=15; the order asymmetry alone suggests wide intervals). No dose–response: "norm-matched" is one point on a magnitude curve.

## Next check I would run (not authorized)

Report `cos(dg, reference_delta)` per call and run two controls on the same DEV15: (a) norm-matched random unit direction, (b) norm-matched *old-GP direction recomputed without J-lens* (plain residual GP), both plus-side only, reusing the same judge. Prediction under my preferred account: (a) gives on-axis ≈ 0 with high off-axis; (b) recovers ≥60% of the 2.87, indicting magnitude+direction jointly rather than the J-lens specifically.

## Completion

- outcome: `complete`
- trace: `slop/logs/20260907_j_lens_norm_matched_gp/science-update/kimi.trace.jsonl`
