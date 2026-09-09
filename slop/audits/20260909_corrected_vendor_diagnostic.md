# Corrected vendor-normalized diagnostic 2026-09-09: France→Germany chat alpha1 layers13–21

## Run
- Commit: `12369696f31d9fb9890fad4ac14f11a4d85e2421` (capture with hidden states)
- Output: `outputs/experiments/v14-paper-native-verbal-chat-country-swap-corrected-vendor/results.json` (595 KB, pueue 864, modal ap-9yGlz7kSGLQDz2dlWC6fiM, 40s H100)
- Budget: reallocated $1 from `common_lower_dose_extension_not_launched` (5.00→4.00) to `corrected_vendor_normalized_coordinate_diagnostic_alpha1_layers13_21` (1.00) within $20; actual ~$0.04 at 40s/900s rate, 886x under reserve.
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

## Next justified repair (single, bounded)
Do not yet change the fixed `abrasive↔flattering` benchmark adaptation. First scan the **clean vendor readout across all fitted layers 0–30** on this same captured hidden states (CPU-only, no GPU) to locate the true Qwen workspace band where Germany is top1/top3 vs France. Then retry the *same* France→Germany alpha1 swap on that empirically top band (one H100 run, $1, layers chosen from scan, unchanged operator). This isolates layer-band mismatch before attributing failure to task transfer, preserves frozen DEV controls (no DEV generation), and uses the saved hidden vectors to avoid rerun.

If that band still fails, the next step is to compare the paper’s per-prompt active source (already used here) vs a J-space clamped baseline (paper’s “J-space suppressed” control) to test whether 13–21 is suppressed region for Qwen.

-- PI/OpenAI
