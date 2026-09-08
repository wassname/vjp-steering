# Next J-lens repair decision

PI/OpenAI Codex, 2026-09-08. This is an offline decision. It does not launch a job.

## Observation

The two repair runs use the same saved behavior-described J-lens contrast. Its source states are measured at the `final_real_chat_prompt_token`, while the current implementation applies the contrast to the user turn only.

- Both repair manifests record `extraction_mask: final_real_chat_prompt_token` and `source_layers: 6..24`.
- Job 780 records current implementation hash `ff42a271...0b62a` in its `EXPLICIT_LEGACY_EXTRACTION_REUSE` warning.
- The current source that has this hash, `src/vjp_steering/j_lens_concept.py`, makes `concept_prefill_mask` call `user_turn_mask` for the signed concept contrast. `user_turn_mask` sets `positions < end`, where `end` is before the assistant-generation suffix. It therefore excludes the final real chat-prompt token from the patch.
- The saved extraction metadata still says `application_mask: all_valid_prefill_tokens_only`. That field came from the reused extraction artifact and conflicts with the current execution code. It is stale metadata, not evidence that the final prompt token was patched.

The observed C=.25 upper-layer patch is real but small: its median patch/residual ratio declines from `0.01690` at layer 18 to `0.00845` at layer 24, and final-token KL is about `0.0014`. Increasing C from .125 to .25 did not provide broad matched-control evidence. A third dose test would not separate this position mismatch.

## Hypothesis

The signed contrast may need to be applied at the same final chat-prompt state from which it was extracted. The present user-turn application perturbs earlier prompt states but never the measured source state. This is a testable application-position hypothesis. It is not a claim that final-position application will work.

Prior all-layer and lower/middle runs do not justify widening layers: at C=.125 their signed effects were negative for both requested directions, while the upper band was selected because it avoided that earlier non-bipolar behavior. The next test keeps the upper layer band and dose fixed.

## Proposed bounded test, not launched

| item | value |
|---|---|
| changed factor | application mask only: exactly the final real chat-prompt token, rather than the user-turn positions |
| saved vector | `j-lens-concept-dev-v1`, SHA256 `8841bc93cf13558a0b01c61d8fdeb737437ee82389754c786d4dd02f351e0f97` |
| application | layers 18-24, `-C=.25` |
| reason for one direction | `+C` is below its same-sign random control in both repair tests. Goal 1 needs one valid endpoint, so a fresh `-C` test is the smallest direct separator. |
| arms | fresh bare, J-lens `-C`, and seeded norm-matched random-minus on DEV-15 in the saved order |
| generation | one H100 container, 900 seconds, no retries |
| judging | unchanged rubric, AB and BA, mapped to arm identity once per scenario; raw-response audit before endpoint selection |
| preflight | host-only test must prove the mask selects one final prompt position per row, does not patch user tokens, preserves vector/hash/layers, and writes the actual application-mask field into the new manifest |
| selection | no all-100 run unless independent review finds task-responsive J-lens `-C` clearly better than random-minus. No DEV point enters the public plot. |

## Budget

The completed DEV judge records now report `$0.01622446` in provider usage. The $16.00 unknown-cost judge reserve is released only to that observed amount. The $18.00 conditional full-endpoint reserve stays retained.

Reserve `$3.00` for this next repair: `$2.00` Modal generation and `$1.00` unchanged-rubric judging. This leaves `$15.62737290` unallocated under the $40.00 whole-block cap after known Modal cost, the retained external-review reserve, completed judge cost, the next-test reserve, and the full-endpoint reserve. This reserve makes the test affordable. It is not a launch authorization.

## Decision

Prepare and review the final-prompt application preflight. Do not run it yet. Keep both research goals open. Do not alter `data/results.csv`, `results/index.md`, `results/index.html`, or `results/plot.png`.
