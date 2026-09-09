# Corrected vendor-normalized diagnostic 2026-09-09: France→Germany chat alpha1 layers13–21

## Run
- Commit: `12369696f31d9fb9890fad4ac14f11a4d85e2421` (capture with hidden states)
- Output: `outputs/experiments/v14-paper-native-verbal-chat-country-swap-corrected-vendor/results.json` (595 KB, pueue 864, modal ap-9yGlz7kSGLQDz2dlWC6fiM, 40s H100)
- Budget: reallocated $1 from `common_lower_dose_extension_not_launched` (5.00→4.00) to `corrected_vendor_normalized_coordinate_diagnostic_alpha1_layers13_21` (1.00) within $20; estimate ~$0.04 at 40s vs 900s reference ($0.0997/101s), ~25× under $1 reserve (not 886×; estimate, no receipt, keep $1 reserved).
- Hidden capture: per-layer `hidden_sha256`/`mean`/`norm` (d_model 2560) plus `hidden_vectors` (9×2560 floats) and `lens_sha256=1f9a8f8fd593f0ffec1a9640993257ca4560f8ae3e5602315643d5cc6818534e` (qwen-n1000), `model=Qwen/Qwen3.5-4B`. Enables CPU regression without GPU rerun.

## Raw vs vendor readouts (this prompt, final token)
| L | raw src rank / tgt | vendor src / tgt | raw scores src/tgt | vendor src/tgt |
|---|---|---|---|---|
|13|7/3|8/3|0.348/0.424|3.453/4.344|
|14|7/6|7/6|0.390/0.438|3.938/4.375|
|15|9/4|9/3|0.389/0.480|3.828/4.625|
|16|6/7|4/9|0.539/0.500|5.812/4.938|
|17|7/9|3/9|0.696/0.658|7.125/6.344|
|18|6/7|5/8|0.753/0.750|7.188/6.781|
|19|5/4|4/4|1.223/1.263|9.250/9.250|
|20|8/5|6/5|1.445/1.510|9.875/10.000|
|21|4/5|3/6|1.815/1.800|10.938/10.562|

Vendor differs from raw on L13,15,16,17,18,19,21 (source rank shifts), but ordering stays mixed: target not consistently dominant. Both agree target is only modestly favored at L13/L15, source favored at L16-18, tie at L19.

## Final logits (unchanged by logging fix)
- Clean: France top1 logit21.5, Germany rank14 logit16.375
- Swapped alpha1: France 21.875 (still top1), Germany rank16 logit15.5625 (worse), n_top1=0, median_clean 14→16
- Coordinate diagnostics: exchange max_abs_error 0.0047 (L13), orthogonal residual 0.0178, all hooks 1× — operator mathematically active, alpha0 identical to clean.

## Interpretation
- Normalization logging bug is **not** root cause: vendor-normalized ranks track raw closely and both show the same mixed signal; correcting norm does not rescue the swap. Final logit failure persists.
- The hidden capture regression `tests/test_j_lens_vendor_readout_regression.py` passes: hidden vectors saved, raw vs vendor differ, final rank still 16.
- The failure therefore is not “wrong readout math” but either: (a) Qwen workspace band ≠13–21, (b) lens checkpoint lacks strong Germany direction for this prompt despite raw/vendor rank3, or (c) prompt-only prefill vs paper’s “all token positions” already matches (22/22 prompt tokens, same as full prompt), so not position scope.

## Next justified repair (single, bounded) — corrected per supervisor
Do not claim CPU scan of 0–30: only layers13–21 were captured. Do not select a Germany-dominant band (would swap Germany OUT); source France should supply the coordinate being transferred.

Use the nine existing clean final-position states for a CPU counterfactual (no new GPU): at each available layer compute exact pseudoinverse source/target coordinates `c = V† h`, apply unchanged alpha1 swap `h' = h + V(swap(c)-c)`, and compare vendor-normalized Germany-minus-France readout before/after. Report coordinate delta alongside readout delta; this separates absent/reversed source coordinate from downstream final-logit failure without another model run. Results from `slop/scripts/20260909_cpu_counterfactual.py` (see `slop/logs/.../cpu-counterfactual.json`):
- L13: c [0.116,0.483] delta +0.367/-0.367, vendor diff 0.903→-1.221 delta -2.124
- L15: c [0.102,0.513] delta +0.411/-0.411, vendor diff 0.801→-1.460 delta -2.260
- L16: c [0.454,0.273] delta -0.181/+0.181, vendor diff -0.877→0.032 delta +0.910
- L19: tie vendor 9.25/9.25 both, delta -1.326 (target not dominant; clean winner France is not the dominant concept at L19, so swapping there is not expected to move final logit).

Layers13–15 and19–21 DECREASE Germany's coordinate/readout (e.g., L13 vendor diff 0.903→-1.221, L15 0.801→-1.460, L19 -0.031→-1.357) combined with final Germany rank14→16 (full 13–21 margin -5.125→-5.312) does NOT establish 'failure downstream of lens readout' — it is also consistent with writing the wrong direction (Germany OUT). Only layer16's positive local change (L16 final-position c 0.454>0.273, vendor diff -0.877→0.032 delta +0.910, France-dominant; cf. task865 all-position means 0.348/0.172 are **not** final-position coordinates) followed by measured downstream response (single-layer L16: rank14→11, margin -5.125→-4.25, Germany logit 16.375→17.0, France 21.5→21.25, top Japan) can test the downstream explanation. Preserve original failed full-band results and distinguish readout changes from causal final-logit success.

Independent mechanism review `slop/reviews/20260909_cpu_counterfactual_mechanism.md` (pass, $0) verified the counterfactual math and L16 selection as France-dominant; next single paid repair remains bounded within the $1 layer16 reserve already allocated.

If that band still fails, the next step is to compare the paper’s per-prompt active source (already used here) vs a J-space clamped baseline (paper’s “J-space suppressed” control) to test whether 13–21 is suppressed region for Qwen.

-- PI/OpenAI
