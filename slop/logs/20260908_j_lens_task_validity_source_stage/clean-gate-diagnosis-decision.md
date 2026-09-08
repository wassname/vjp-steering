# Clean-gate diagnosis decision: REVISE

PI/OpenAI Codex, 2026-09-08. This decision does not alter frozen v3, rerun a model, or release benchmark work.

**Decision: REVISE the source-task specification before another source-stage test.** The existing v3 gate cannot distinguish task failure from its own policy-order label error.

## Evidence

[clean-gate-diagnosis.json](clean-gate-diagnosis.json) recalculates each saved response twice. The frozen label is the recorded `expected` field. The literal-policy label maps a true precondition to `policy_actions[0]`, a false precondition to `policy_actions[1]`, then maps that action through the row's A/B options.

| measure | all rows | policy order 0 | policy order 1 |
|---|---:|---:|---:|
| rows | 384 | 192 | 192 |
| frozen-label accuracy | 50.0% | 81.25% | 18.75% |
| literal-policy accuracy | 81.25% | 81.25% | 81.25% |
| frozen label disagrees with literal prompt action | 192 | 0 | 192 |

The build code makes this mismatch directly. In [v3/build.py](../j_lens_task_validity_corpus/v3/build.py), `policy_actions` reverses for policy order 1, but `expected` still maps a true row to `valid_action` and a false row to `invalid_action`, independent of that reversal.

A complete paired semantic case makes the effect visible. In [clean-gate-diagnosis.json](clean-gate-diagnosis.json), `tv1_capacity_0_allocation_1` has four variants. All four saved answers follow their literal policy. The policy-0 variants are frozen-correct. The policy-1 variants correctly output B and A after the reversal, but the frozen labels remain A and B, so both are scored wrong.

The same artifact separates genuine prompt-answer errors. On policy order 0, where frozen and literal labels are identical, 36 of 192 answers are literal-policy wrong. Across both policy orders, 72 of 384 answers are literal-policy wrong. These are the evidence for remaining task or instruction errors. They cannot explain the 156 policy-1 answers that were literal-policy correct yet frozen-wrong.

## Interpretation

My read is that it is almost certain the v3 clean-gate failure is invalid as evidence that Qwen failed the closed-rule source task. The policy-order mirror was intended to remove a shortcut, but it changed the stated action policy without changing the expected action. The model followed the literal policy at the same 81.25% rate for both policy orders. The previous `SOURCE_GATE_BLOCKED` result is therefore superseded as a behavioral claim.

The 81.25% literal-policy rate is not enough to admit this task for a future causal test. It also has 72 literal-policy failures and only 56 of 96 cases with all four literal-policy variants correct. A revised task must specify one consistent semantic action relation, pass a static prompt-faithful oracle, and be independently reviewed and frozen before another model call. It must not reinterpret the existing generation as a passing result.

## Scope

Do not change `v3/corpus.jsonl`, `v3/freeze.json`, or the existing gate. Preserve job 705 as an invalid-task diagnosis. Do not run intervention, DEV transfer, benchmark generation, judging, or a paid source retry. Both research goals remain OPEN.
