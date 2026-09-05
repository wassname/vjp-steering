# J-lens paper-native diagnostic: pre-run predictions

## Decision being tested

The old `abrasive`↔`flattering` DEV run is not evidence against the paper intervention because it edited every continuation decode step and did not confirm an active source concept. This diagnostic uses baseline-correct country prompts, prompt-prefill-only hooks, and the official next-answer-token outcome.

## Candidates

| candidate | operator | prediction on 6 baseline-correct trials (2 items × 3 bands) |
|---|---|---|
| raw exchange | paper equation with raw rows of $W_UJ_l$ and a 2D pseudoinverse | target hits are plausible but uncertain; failure while unit transfer succeeds would isolate operator geometry |
| unit exchange | the same 2D exchange after row normalization | should improve over raw exchange if unequal row norms caused the old instability |
| unit transfer | $h' = h + (h\cdot d_s)(d_t-d_s)$, matching the working Qwen replication | highest prior for target hits; should not repeat literal tokens because hooks stop after prefill |

Each candidate is tested on layers 6–24, 9–30, and 4–13. Hooks must fire exactly once per selected layer. Alpha is fixed at 1 so band and operator are not mixed with dose selection.

## Diagnoses before the run

| probability | diagnosis of the old collapse |
|---:|---|
| 35% | hooks remained active during continuation and repeatedly wrote token directions into each generated token |
| 25% | fixed style-token source was not active in the benchmark prompts, unlike the paper protocol |
| 20% | raw symmetric exchange differs materially from the working normalized directed transfer |
| 10% | layers 6–24 miss the useful band |
| 5% | Qwen3.5-4B differs from the demonstrated Qwen3-4B/model family |
| 5% | unknown or evaluation confound |

## Discriminating observations

- If prompt-only country runs avoid repetition, continuation-hook accumulation explains the old collapse.
- If raw exchange works, the old result was principally a protocol/concept failure.
- If only unit transfer works, the implemented paper equation and working Qwen replication are behaviorally distinct.
- If no candidate works on either item or any band, inspect token orientation, lens/model compatibility, and exact pre/post coordinates before another behavioral sweep.

Sources: `slop/reviews/20260905_j_lens_swap_primary_evidence.md`, `docs/pseudocode/j_lens_coordinate_swap_debug.py`.

— PI/OpenAI Codex
