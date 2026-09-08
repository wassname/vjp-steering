# Independent v3 review decision

PI/OpenAI Codex, 2026-09-08. Review artifact: [DeepSeek V4 Pro review](../../../reviews/j_lens_task_validity_v3_deepseek.md), SHA256 `1c2dd57e00e6700985104d4c68fa05f2aea63a5f4e05d8602962476566dadeb5`. Provider/model: `fireworks/accounts/fireworks/models/deepseek-v4-pro-0813`, low thinking, read-only repository tools. The complete provider reasoning and session marker are saved beside it. The `.err.txt` file contains only the expected new-session warning.

## Decision: TEST, source-state stage only

The external reviewer returned **TEST**. It verified that v3 derives each row from frozen v2 and changes only policy-clause order; that answer position and clause order are balanced in the declared cells; and that `selected_semantic` maps a letter through row options before scoring valid/invalid actions. It directly reported: “semantic_oracle passes (1.0), always-A/B (0.5), opposite-letter (0.0), first-policy-branch (0.5) all fail.” This matches [validation.json](validation.json) and [validation.log](validation.log).

PI accepts this decision for the offline protocol. A future source-state test can be considered. This decision does not authorize a GPU run. A separate explicit authorization is still required.

The reviewer also found a real power risk: the current gate requires every two-row policy pair and every four-row option-and-policy semantic case to be correct. This makes the gate effectively 100% correct across the frozen corpus, even though its aggregate threshold is 90%. PI accepts the description and keeps the strict gate. It is a predeclared conservative blocker, not evidence of a source state. It should not be relaxed after a failed model run without a new versioned design review.

## Transfer boundary

The review confirms that the corpus can only test closed-world precondition satisfaction. It cannot establish model-inferred task validity, J-space causality, or transfer to sycophancy. The existing continuous sycophancy/off-axis benchmark remains the only future transfer endpoint. No factual-existence rejection score or new binary rubric is authorized.

## Cost reconciliation

The external review was the only paid action in this task. The recorded reservation is $0.50 in [review-reservation.md](review-reservation.md), reducing the currently unreserved accounting balance from $5.72509672744 to $5.22509672744 while the reservation is retained. `pirev` did not emit a provider usage or dollar receipt, so actual Fireworks cost is unknown and must not be fabricated. No GPU, target-model inference, benchmark generation, or judging was launched.

Both research goals remain OPEN.
