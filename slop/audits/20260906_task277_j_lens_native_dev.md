# Task 277: paper-native J-lens DEV

— PI/OpenAI Codex

Target: task 277 ran the paper-native `abrasive`/`flattering` coordinate exchange through calibration and the 15-question judged DEV cohort. It started 2026-09-06 12:21:32 +0800 and exited 1 after 422 seconds because the renderer lacked a color for `j_lens_swap`. Generation, judging, and export completed first. The relevant implementation was committed before the job, but the run does not record its git revision. Evidence: [complete 142-line log](../logs/20260906_j_lens_native/task-277-clean.log), [raw log](../logs/20260906_j_lens_native/task-277-raw.log), [task metadata](../logs/20260906_j_lens_native/task-277-metadata.json), [first full response from every dose](../logs/20260906_j_lens_native/task-277-first-every-cell.txt), [all responses at the selected doses](../logs/20260906_j_lens_native/task-277-selected-all-responses.txt), and [corrected DEV results](../../data/dev/j-lens-paper-native-sycophancy-v1/results.csv).

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| extraction | paper raw-basis pseudoinverse exchange | `h + alpha V(swap(V†h)-V†h)` at layers 6–24 | yes | manifest operator and task log | exact git revision | intended method ran |
| +C calibration | coherent range below lexical leakage/repetition | clean through 1.097; 1.204 leaks `flattering`; 2.0 repeats | yes | `C_approx=1.097277609...`, `C_hi=1.204018152...` | random-direction calibration | boundary located |
| -C calibration | alpha1 is broken; search downward to coherent range | 1,.5,.25 repeat `abrasive`; .125 and .136 are clean; .149 leaks | yes | `C_approx=.1363134666`, `C_hi=.1486508894` | repeated-seed uncertainty | boundary located sharply |
| generation grid | 22 cells × 15 complete responses | 330 responses, full raw first response per cell inspected | yes | `GPU_STAGE_COMPLETE ... cells=22` | peak GPU memory | generation complete |
| judge | one AB judgment per DEV pair | 223 unique required keys, 172 new API calls, zero missing | yes | `JUDGE_COMPLETE required=223 missing=0` | order reversal / second pass | DEV estimate is noisy |
| export | signed plot axis and admissibility | initial export failed to negate the -C bluntness score; corrected re-export now selects +1.097 and -.1128 | no, then fixed | [fixed-sign re-export](../logs/20260906_j_lens_native/task-277-reexport-fixed-sign.log) | regression test over full export fixture | original -C table was sign-inverted |
| rendering | standalone DEV plot | initial `KeyError: 'j_lens_swap'`; color added and render now completes | no, then fixed | [fixed render](../logs/20260906_j_lens_native/task-277-render-fixed-sign.log) | fresh-eyes subagent | task exit failure was downstream of DEV |
| all-100/public plot | accepted DEV candidates confirmed and merged | not reached | no | task stopped at renderer | full-cohort judgments | goal remains open |

## Chronology and metrics

The boundary search behaved as the smoke predicted. The positive coordinate exchange remained fluent until it began emitting the target token itself:

> `+C C=1.2040181522159161 ... breakdown_reasons=["lens_token_leak"]`

The first response starts `flattering the decomposition...`. At alpha 2, 13/15 outputs were unfinished, 14/15 repeated, and 15/15 leaked a lens token.

The negative direction had a much narrower scale. Alpha 1, .5, and .25 each produced 15/15 unfinished, 15/15 repeated outputs containing the lens token. Alpha .125 was clean on all 15. Alpha .14865 leaked on 5/15. This supports a coherent boundary near .14, not alpha 1.

All 330 grid responses were judged. The initial exported -C sign was wrong: the judge rubric for `-C` asks for more bluntness, so a positive judge delta must become a negative x-axis value. The old walk exporter did this conversion, but `export_experiment` did not. After the shared `signed_axis_effect` fix, selected DEV rows are:

| direction | C | on-axis plot change | off-axis change | generation checks |
|---|---:|---:|---:|---|
| +C | 1.0972776095 | +0.020 | 0.160 | accepted |
| -C | 0.1127993936 | -0.180 | 0.320 | accepted |

The +C result is approximately null: most lower coherent doses point in the wrong direction (-0.72 to -0.12), and only the last clean point is +0.02. The -C result is small but has the intended sign after correction. At both selected doses, the 15 raw answers remain responsive; no selected response repeats the lens words or refuses generically. Several responses change factual stance, so the off-axis score is not zero.

## ml-debug form

| row | answer |
|---|---|
| log length/config | 142/142 cleaned lines read. Qwen3.5-4B BF16, layers6–24, 15 prompts, 512 tokens, 22 grid cells; raw manifest contains the operator and grids. |
| SHOULD versus observed | Native operator logged. +C leakage starts above 1.097; -C repetition disappears below .149. Judge reports 223/223 keys. The original export sign violated the x-axis contract and was corrected. |
| number scales/nulls | Paired bare null is 0 for both metrics. +C selected effect +.02 is near null; -C -.18 is small. Random behavioral directions are not in this DEV artifact. The all-100 public random cone is not evidence for this 15-row uncertainty. |
| before update/demo | Frozen model, no training. Bare and every selected response are preserved in the all-response log. |
| dummy/baseline | Bare is the direct paired baseline. There is no matched random coordinate pair. |
| baseline/held-out | DEV uses 15 fixed rows. No held-out or all-100 result yet. |
| schedule | No learning rate. Calibration searched alpha by generation checks, then evaluated ±33% local grids. |
| one full sample | First response from all 22 cells is in `task-277-first-every-cell.txt`; all 30 selected-dose responses plus bare are in `task-277-selected-all-responses.txt`. Selection was by dose and scenario order, not outcome. |
| worst step | +2 and negative -.25 or stronger repeat lens words. No losses or gradients exist. |
| surprises | Initial -C selected effect was -0.427 at C=.136, but this meant less bluntness under the judge rubric. Explained: experiment exporter omitted the sign conversion. `+C=.02` is much weaker than the category-token reproduction; chasing with all-100 confirmation, not a new operator. |
| missing to trust | all-100 AB/BA judgments, repeated seed, random token-pair control, exact revision, peak memory. |
| competing diagnoses | H1–H4 below. |
| fresh subagent | unavailable because the configured subagent registry reports a `goal-worker` name collision. The plot was inspected directly. |
| cheapest discriminator | resume the existing pipeline: all generation and DEV judging are cached; render then all-100 only the corrected accepted candidates. |
| wall time/memory | 422 seconds. GPU stage about 261 seconds; judge about 100 seconds including cache scans. Peak GPU memory absent. |

## Hypotheses

### H1 [method | Highly Likely | 80%]
- **Mechanism:** the raw lexical coordinate pair controls token-level `abrasive`/`flattering` content more strongly than substantive sycophancy.
- **Evidence:** just above the coherent boundary, outputs literally begin with `flattering` or repeat `abrasive`; within the coherent region, +C effects are mostly negative and the selected +C effect is only +.02.
- **Contrary evidence:** selected outputs are fluent and -C=.1128 has an intended-sign -.18 effect.
- **Discriminating test:** all-100 confirmation. A stable substantive effect without lens-token leakage supports behavioral transfer; near-zero or wrong-sign estimates support lexical control.
- **Fix/action:** run the predefined full confirmation before changing representation.
- **Interpretability:** partial; coordinate control is real, sycophancy control is weak.

### H2 [measurement | Almost Certain | 99%]
- **Mechanism:** `export_experiment` initially treated the bluntness-target judge delta as the signed plot coordinate without negating it.
- **Evidence:** code used `effect = mean(cell[0]...)`; `TARGET['-C']` asks for more bluntness, while the plot defines bluntness as negative x. The corrected helper changes selected -C from C=.136/effect -.427 to C=.1128/effect -.180.
- **Contrary evidence:** raw judge values were intact; only the coordinate conversion was wrong.
- **Discriminating test:** self-test asserts a +3 bluntness-target delta maps to -3 on the plot.
- **Fix/action:** use `signed_axis_effect` in both exporters and rerun export from cached judgments.
- **Interpretability:** yes after re-export; the original -C table is invalid.

### H3 [harness | Almost Certain | 99%]
- **Mechanism:** standalone rendering omitted a color for `j_lens_swap`.
- **Evidence:** `KeyError: 'j_lens_swap'` at `colors[method]` after `EXPERIMENT_EXPORT_COMPLETE`.
- **Contrary evidence:** none; adding the existing J-lens cyan color makes rendering complete.
- **Discriminating test:** the same render command now prints `EXPERIMENT_RENDER_COMPLETE`.
- **Fix/action:** add `j_lens_swap: J_LENS_COLOR`.
- **Interpretability:** yes; this did not affect generation or judgment.

### H4 [data | Chances a little better than even | 55%]
- **Mechanism:** one AB judgment over 15 rows makes +.02 and -.18 unstable enough to change sign on all-100.
- **Evidence:** neighboring coherent +C doses range from -.72 to +.02 without a monotone behavioral trend; DEV has no BA order or repeat.
- **Contrary evidence:** -C has several low-dose values with the intended corrected sign, though not monotonically.
- **Discriminating test:** all-100 AB+BA confirmation with the same cached vectors and selected candidate ladder.
- **Fix/action:** continue the existing pipeline; do not report DEV as final.
- **Interpretability:** DEV is formative only.

## Decision

1. **Resolve-condition verdict: not met.** DEV calibration and judging completed; all-100 and public rendering did not run.
2. **Predictions:** coherent ranges were found; +C useful effect is contradicted/approximately null; -C useful effect has weak support; all-100 remains unresolved.
3. **Earliest unsupported link:** stable sycophancy behavior on data not used for dose selection. All-100 AB/BA scores support it.
4. **Validity:** invalid means the corrected DEV rows do not represent the generated/judged operator. `P(corrected DEV artifact is invalid) ≈ 15%`; credible calibration, weak and inconclusive efficacy.
5. **Highest-information clues:** lexical leakage at both boundaries; corrected sign conversion; selected +C effect +.02.
6. **Missing metrics:** all-100 effect and damage, order sensitivity, repeated seed, random coordinate-pair control, exact revision.
7. **Code changes:** H2 → shared signed-axis helper; H3 → J-lens color mapping.
8. **Reinterpretation:** the pre-fix -C table and selected C=.136 are invalid; the corrected selected C is .1128.
9. **What would change the verdict:** all-100 intended-sign effects materially separated from zero would support adding the method; wrong-sign or near-zero effects would show that the paper operator works mechanically but this lexical pair does not steer sycophancy.
10. **Recommended sequence:** commit the two deterministic fixes and corrected DEV evidence; rerun task 277 so cached DEV work resumes; confirm all-100 candidates; only then merge comparable rows into the public plot.
