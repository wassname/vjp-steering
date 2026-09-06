# Task 278: paper-native J-lens all-100 endpoint check

— PI/OpenAI Codex

Task 278 resumed the cached DEV experiment and tested the DEV-selected endpoints on the 100-scenario cohort with AB and BA judging. It completed in 408 seconds. Evidence: [complete log](../logs/20260906_j_lens_native/task-278-clean.log), [raw pueue log](../logs/20260906_j_lens_native/task-278-raw.log), [task metadata](../logs/20260906_j_lens_native/task-278-metadata.json), [stratified raw samples](../logs/20260906_j_lens_native/task-278-selected-samples.txt), [endpoint results](../../data/formative/j-lens-paper-native-sycophancy-v1/results.csv), and [endpoint plot](../../results/formative/j-lens-paper-native-sycophancy-v1/plot.png).

| direction | DEV C | DEV effect / damage | all-100 effect / damage | generation checks |
|---|---:|---:|---:|---|
| +C | 1.09728 | +0.020 / 0.160 | +0.1105 / 0.175 | 100 complete; no repetition, role leak, or lens-token leak |
| -C | 0.11280 | -0.180 / 0.320 | -0.1375 / 0.158 | 100 complete; no repetition, role leak, or lens-token leak |

Both directions kept their intended sign on all-100. The endpoint effect sizes are modest and their damage is larger than their on-axis movement. A visible example of off-axis change is `syco_bullshit_v2_sw_cds_01`: +C changes a correct refusal of the physical analogy into a fabricated calculation. The judge damage aggregates capture such cases only imperfectly.

## ml-debug form

- **Complete log:** 156/156 clean lines inspected. DEV generation reused 22 cells. Full generation extended bare plus four candidate cells from 15 to 100 rows. The two endpoint cells were judged, each with 200 required AB/BA keys and zero missing.
- **Expected versus observed:** expected intended-sign effects if the lexical coordinate generalizes. Observed +.1105 and -.1375, both intended-sign. Expected clean generation below the DEV boundary; both endpoint cells have zero unfinished, repeated, role-leaked, or lens-token-leaked outputs.
- **Null and scale:** bare paired null is zero. Random-direction null distribution is not recomputed here. Damage (.175/.158) exceeds absolute on-axis effect (.1105/.1375).
- **Baseline:** the same 100 bare generations are paired with each intervention. No training or updates occur.
- **Samples:** eight fixed scenario indices per side were inspected, including legal, physics, medical, and software prompts. They remain responsive, but some answers change factual content.
- **Surprise:** +C grew from DEV +.02 to all-100 +.1105. This may be cohort noise rather than a stronger population effect. The -C damage fell from .32 to .158.
- **Missing evidence:** all-100 dose-response grid, judge-repeat uncertainty, and matched random coordinate pairs.

## Competing explanations

1. **Behavioral transfer is real but weak — Likely (60%).** Both independently signed endpoints retain the intended sign on 100 prompts, and neither leaks the lens words. Against: damage is larger than effect and the DEV +C estimate was near zero.
2. **General perturbation/style change explains much of the judge effect — Likely (65%).** Raw samples change wording and sometimes factual stance; off-axis scores exceed effect. Against: the two signed directions move the target score in opposite intended directions.
3. **Cohort/judge noise materially affects the magnitude — Chances a little better than even (55%).** +C moves from +.02 on 15 to +.1105 on 100; there is one AB and one BA judgment rather than repeated passes. Against: signs are stable.

## Decision

The endpoint check supports continuing. It is not yet the final comparable public result: project protocol requires the all-100 dose grid around the calibrated boundary, not only the DEV-selected endpoints. Generate and judge the complete calibrated grid, then add its admissible rows to the public results. Do not describe the method as Pareto-efficient unless the full curve supports that comparison.
