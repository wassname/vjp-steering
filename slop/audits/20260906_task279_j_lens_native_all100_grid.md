# Task 279: paper-native J-lens all-100 grid

— PI/OpenAI Codex

Task 279 extended all 22 calibrated DEV doses to the 100-scenario cohort, judged each distinct response pair in AB and BA order, exported the dose curve, and completed after 2,160 seconds. The first judge attempt stopped when OpenRouter returned a transient 404 for `deepseek/deepseek-v4-flash-0731`; the resumable runner retained completed cache records and the second attempt reached zero missing judgments. Evidence: [complete 214-line log](../logs/20260906_j_lens_native/task-279-clean.log), [raw pueue log](../logs/20260906_j_lens_native/task-279-raw.log), [task metadata](../logs/20260906_j_lens_native/task-279-metadata.json), [first response and health counts at every dose](../logs/20260906_j_lens_native/task-279-first-every-cell.txt), [all-100 result rows](../../data/formative/j-lens-paper-native-sycophancy-v1/results.csv), [scenario scores](../../data/formative/j-lens-paper-native-sycophancy-v1/judged_scenarios.csv), and [public render log](../logs/20260906_j_lens_native/task-279-public-render.log).

## Result

| direction | coherent C range | best intended effect (C) | damage | highest-C coherent effect (C) | damage |
|---|---:|---:|---:|---:|---:|
| +C, toward flattering | 0.7242–1.0973 | +0.1330 (1.0918) | 0.1620 | +0.1105 (1.0973) | 0.1750 |
| -C, away from exchange / toward abrasive | 0.0900–0.1242 | -0.4415 (0.0900) | 0.1530 | -0.0900 (0.1242) | 0.2595 |

The public comparison summarizes J-lens as score **-0.029**, with a best coherent -C magnitude of **0.442 at 0.153 damage** and +C magnitude of **0.133 at 0.162 damage**. It ranks below every named steering method and above the random aggregate. Its low damage is partly because its useful on-axis movement is small. Public artifacts: [table and plots](../../results/index.md), [measured paths](../../results/plot.png), and [Pareto-smoothed paths](../../results/plot_pareto.png).

The response boundary is sharp and dominated by the literal lens words:

- +C is clean through 1.0973. At 1.1837, 96/100 responses contain a lens token. At 1.2756, all 100 contain one and 42 are unfinished.
- -C is clean through 0.1242. At 0.125, 1/100 contains a lens token and is rejected. At 0.1356, 4/100 contain one; at 0.1813, 94/100 contain one and 85 are unfinished/repetitive.

The full-grid curve is not monotone. For +C, four lower doses have wrong-sign effects (-.184 to -.1215), near-identical C=.99989 and C=1 produce -.1575 and -.0075, then C=1.0918 becomes +.133. For -C, the smallest dose has the largest intended effect (-.4415), which weakens toward -.09 at C=.1242 and reverses sign just above the generation-health boundary. Generation is greedy, so this is not sampling noise; small logit changes can cross argmax boundaries and produce different continuations.

## ml-debug form

| check | observation |
|---|---|
| complete log | 214/214 cleaned lines read. DEV reused 22 cells; full extended 18 remaining cells by 85 rows each; all 22 cells contain 100 rows. |
| judge completeness | 2,878 distinct required keys, rather than 4,400 nominal cells, because identical generated pairs share cache keys. Final check: `JUDGE_COMPLETE required=2878 missing=0`. |
| retry | First attempt cached 499 new calls before a provider 404. Second attempt resumed 1,655 missing calls and completed. This changes availability, not scoring policy. |
| baseline/null | Each cell uses the same paired bare response. Random directions are present in the public plot, but no matched random J-lens token pair was run. |
| generation health | 11/22 doses admissible: seven +C and four -C. Every admissible cell has 100 complete responses and zero repetition, role leaks, or lens-token leaks. |
| judge diagnostics | At the four reported doses, 0/100 scenario aggregates have opposite-sign AB/BA means. Mean within-scenario score spread ranges .384–.896; medians are zero because many responses are unchanged or judged tied. |
| scale | Useful J-lens effects are .09–.44. Existing named methods reach roughly 1–4 on the same axis. Damage is .15–.26 at reported J-lens endpoints. |
| raw samples | Task 278 inspected eight fixed all-100 rows per endpoint. Task 279 preserved the first response from every grid cell. Some coherent responses change factual content despite passing lexical generation checks. |
| visual check | Both PNGs were ingested directly after rendering. Cyan points cluster near bare; direct +C/-C labels and a solid/dotted key were added. A fresh reviewer recognized the small effect but reported clipping in the Pareto PNG; direct inspection of the 2128×1180 file shows its title, axes, ticks, and boundary labels inside the canvas. |
| missing evidence | repeated judge passes, uncertainty intervals, matched random token pairs, and exact causal decomposition of style versus sycophancy. |

## Competing explanations

1. **The coordinate pair transfers weakly to substantive sycophancy — Likely (65%).** Both directions contain coherent intended-sign points on all 100 scenarios. Against: effect is nonmonotone and several +C doses move the wrong way.
2. **Most useful movement is generic style/factual disruption — Likely (60%).** Damage is comparable to or larger than target effect, and raw responses sometimes change factual stance. Against: signed directions produce opposite intended changes in their best coherent regions.
3. **The coordinate pair chiefly controls its source words — Highly Likely (85%).** Breakdown occurs through literal `flattering`/`abrasive` emission and repetition immediately above the coherent region. Against: intended-sign judge movement exists below lexical leakage.
4. **Judge variance explains the entire signal — Unlikely (35%).** Scenario medians are zero and magnitudes are small. Against: both directions retain intended signs on the all-100 aggregate and AB/BA aggregated signs do not conflict at the reported doses.

## Decision

The goal is met narrowly: the paper-native operator now appears on the same all-100 public comparison under the label **J-lens coordinate swap**. The evidence does not support calling it competitive for sycophancy steering. The strongest fair statement is: this lexical coordinate pair reproduces coordinate control, produces small signed behavioral changes below a sharp lexical-repetition boundary, and ranks below the other named methods on this benchmark.
