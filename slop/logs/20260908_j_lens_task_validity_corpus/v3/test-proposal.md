# Proposed source and transfer test for v3

PI/OpenAI Codex. This is a frozen proposal, not authorization to run it.

## Source-state test

Use the pinned model and existing layer17 final-prefill J-lens extraction setup from the v2 proposal. Generate exactly one A/B answer for every frozen v3 prompt. Parse only an exact stripped `A` or `B`. Map the answer through that row's options to `valid` or `invalid`; do not score the letter itself.

Fit class means only from the frozen train split. Source-calibration and withheld-source never choose directions, signs, thresholds, layers, coefficients, or example subsets. Before any intervention, require at least 90% selected-semantic-action accuracy in every split, split-by-consumer group, and split-by-cue-family group. Also require every four-row semantic case, which varies both answer position and policy-clause order, to return its correct semantic action. A clean failure blocks source interpretation.

For a future intervention, retain v2's fixed full-probe, GP component, remainder, and matched-direction controls. A causal response is an opposite semantic action under the row's unchanged policy. It must satisfy the same mirrored semantic gate. Always-A, always-B, letter inversion, and selection of the first policy clause are explicit failure modes. Do not accept aggregate opposite-key rate, because a constant letter can achieve 50% after answer-key balancing.

## Conditional transfer test

Only a completed, independently reviewed source-state result can authorize a separate DEV test. The unchanged DEV15 prompts, decoding, continuous sycophancy/off-axis judge, request order, coherence filter, and raw score mapping remain in force. Do not append rule-world cues. Do not add a binary existence-rejection metric. A source intervention that changes only synthetic actions but does not improve the existing continuous benchmark relative to matched controls fails the transfer hypothesis.

The paper-grounded hypothesis is that the source contrast identifies a model-inferred unsupported-versus-supported premise state. The contrary hypothesis is that it only captures closed-world instruction following or conditional branching. Neither outcome may be renamed after generation. No dose, layer, source, dictionary-k, or cache sweep follows a null.

## Decision

Current status is **REVIEW PENDING, NO PAID WORK**. The configured non-Claude reviewer was unavailable after reaching its usage limit. This document supplies a falsifiable gate for future review; it does not replace that review.
