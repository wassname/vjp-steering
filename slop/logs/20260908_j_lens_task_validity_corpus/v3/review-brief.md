Review frozen task-validity corpus v3 as a skeptical independent ML researcher. You have read-only repository access. Do not edit files, run model inference, call APIs, or propose launching work.

Read these actual files first:
- slop/logs/20260908_j_lens_task_validity_corpus/v3/spec.md
- slop/logs/20260908_j_lens_task_validity_corpus/v3/corpus.jsonl
- slop/logs/20260908_j_lens_task_validity_corpus/v3/build.py
- slop/logs/20260908_j_lens_task_validity_corpus/v3/validate.py
- slop/logs/20260908_j_lens_task_validity_corpus/v3/validation.log
- slop/logs/20260908_j_lens_task_validity_corpus/v3/validation.json
- slop/logs/20260908_j_lens_task_validity_corpus/v3/test-proposal.md
- slop/logs/20260908_j_lens_task_validity_corpus/v3/review-pending.md
- slop/logs/20260908_j_lens_task_validity_corpus/spec.md for the quote-anchored paper mechanism and earlier limits.

Question: Does v3 provide a falsifiable source-state test for a task-validity intermediate, while keeping the existing continuous sycophancy/off-axis benchmark as the only transfer endpoint?

Verify from code and data, not declarations:
1. V1/v2 are preserved, and v3 changes only policy-clause order from v2.
2. A/B answer position and policy-clause order are balanced within relevant task and label cells. Storage/notification remain absent from training and source-calibration.
3. The proposed gate maps letters to semantic actions, and always-A, always-B, opposite-letter, and first-policy-branch controls truly fail while the semantic oracle passes. Look for remaining simple shortcut false positives, including policy wording, action lexical preference, invalid-evidence artifacts, split/cue confounding, and a gate that is too strict or too weak for a model test.
4. The corpus measures closed-world precondition satisfaction. Decide whether the proposal keeps distinct the two claims: a source-state effect and transfer to the unchanged benchmark. It must not substitute factual-existence rejection or a new binary metric.

Return one decision: TEST or REVISE. TEST means the offline design is sufficient to authorize only the already described source-state experiment, subject to the separate budget and no automatic benchmark stage. REVISE means name the smallest concrete offline correction and quote the exact row/code behavior that requires it. State what v3 can and cannot establish. Do not broaden this into a layer/dose/source search.
