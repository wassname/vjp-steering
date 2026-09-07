# Decision review: task 465

## Inherited decisions

- Task 462 permanently stops matched final-prefill source plus target-order steering. No dose extension, sign inversion, post-hoc layer selection, or relabeling.
- The task-465 lexicon, leading-space token IDs, layers 13–21, exact rank-1 criterion, request span, and 10/15 threshold were frozen.
- Failure of explicit-control activity was preregistered as `INVALID_DIAGNOSTIC_NO_GENERATION`, requiring one distinction between behavioral classification failure and a token/readout/span failure.
- No causal generation is allowed unless the explicit control and both original directions pass.

## Diagnosis

**Current classification: (b), a protocol/token-boundary validity failure requiring exactly one bounded explicit-control diagnostic.** A software indexing or span bug is unlikely, but task 465 is not yet a valid demonstration of latent-label absence under its preregistered contract.

Evidence:

- Behavioral classification works: 14/15 controls emit bare `false` (ID 3721); CSN alone emits bare `true` (ID 1802).
- The frozen activity candidates are different, leading-space tokens: ` false` is ID 867 and ` true` is ID 804. Prior Qwen chat reproduction already established that answer-slot concepts can require bare rather than leading-space IDs.
- This boundary mismatch does **not** rescue coverage. Full-artifact inspection shows neither bare ID 3721 nor bare ID 1802 appears among rank-1 tokens in any of the 6,264 explicit request-span cells. Thus changing only the token boundary cannot satisfy the frozen stimulus-span criterion.
- The null is not marginal: leading-space `false` has best explicit rank 18 and median prompt-best rank 459; no frozen semantic candidate reaches top 10 in explicit context. Semantic coverage is zero while size-seven random sets reach three prompts.
- Span and algebra look correct. The implementation scores exactly the request characters, captures block outputs at the checkpoint’s layer indices, and computes
  `hidden @ (W_U @ J).T`, which is algebraically identical to the companion implementation’s `unembed(J @ h)`.
- The companion protocols differ materially:
  - `top-down-summoning` reads property labels over a stimulus span under alternative preceding questions.
  - `verbal-report` uses the actual greedy answer token as the source and applies swaps across the whole prompt.

  Task 465 matches the former span policy but uses behavioral emission of `false` as if it automatically validated a stimulus-span lexical label. That implication was an untested assumption.

The punctuation/underscore-heavy top-1 distribution is concerning but not proof of a transpose or masking bug: 36–41% of top-1 cells still contain alphabetic text, the span records are internally aligned, and both contexts show similar behavior. It does justify an official-implementation parity check.

## Drift / contradiction check

The quiet assumption that changed was:

> “If Qwen answers `false`, the leading-space ` false` J-lens row should become rank 1 somewhere over the preceding request span.”

Neither the paper protocol nor causal language-model tokenization guarantees that. The actual emitted token is bare, and even that bare token has zero request-span rank-1 hits.

This does not permit substituting bare IDs into the original method, lowering the rank threshold, adding synonyms, or searching other layers. Those would violate the frozen design. The debug may inspect bare IDs only to diagnose the explicit control.

## Recommendation

Run **one explicit-only answer-seam/readout bridge diagnostic** on the same DEV-15 prompts:

1. Do not score or reconsider original-context eligibility.
2. Reproduce the 15 explicit prompts and their greedy first tokens.
3. At the final assistant-prefill position, record:
   - ordinary final-model ranks for IDs 3721, 1802, 867, and 804;
   - J-lens ranks/top-1 IDs at the unchanged layers 13–21.
4. For the explicit request span, summarize exact ranks for the same four IDs, without making any of them eligible candidates.
5. On at least one complete explicit prompt, compare local scores/ranks against the pinned companion `JacobianLens.apply` implementation; require matching top-1 IDs and candidate ranks at every compared cell.
6. Persist only this compact explicit-control audit. Do not generate interventions or edit the frozen diagnostic.

### Exact predicted outcomes

Most likely:

- Greedy output and final-model logits agree on all 15 prompts: bare `false` rank 1 on 14 and bare `true` rank 1 on CSN.
- Leading-space IDs are not the answer-slot rank-1 tokens.
- Local and official J-lens implementations agree exactly in ranks/top-1 IDs.
- Bare answer tokens remain at **0/15 request-span rank-1 coverage**, reproducing what task 465’s stored rank-1 IDs already establish.
- Bare answer-token activity at the assistant-prefill seam reaches at least 10/15 prompts somewhere in layers 13–21.

If those predictions hold, reinterpret task 465 as a **valid narrow negative**: the fixed Qwen J-lens can read the explicit answer at its output seam, but neither leading-space nor output-compatible assessment labels are rank-1 over the question-conditioned request span. Stop the assessment-token route.

### Failure branches

- **Official/local parity fails:** a mechanical readout or layer-index defect exists. Fix only that defect and rerun the unchanged frozen diagnostic once.
- **Final logits do not reproduce the emitted IDs:** the answer-token extraction/ranking seam is wrong. Fix it and rerun once.
- **Parity and final logits pass, but assistant-prefill J-lens activity is below 10/15:** the saved J-lens/fixed band fails even this output-aligned positive control. Record the diagnostic as invalid/unusable under this lens and stop; do not search layers or ranks.
- **Bare IDs unexpectedly become request-span rank 1 despite the stored artifact showing none:** treat that as a provenance/reproducibility failure, not as permission to redefine the method.

## Risks

- An assistant-prefill hit validates readout/token alignment, not causal relevance to open-ended benchmark answering.
- A parity pass rules out implementation drift but cannot distinguish genuine representational absence from limitations of the WikiText-fitted average J-lens. The defensible claim is therefore “absent under this fixed Qwen J-lens,” not “absent from the model.”
- CSN’s `true` answer is a model classification error, but 14/15 still satisfies the behavioral control threshold.

## Need from main agent

None. The inherited contract already determines the action and branches.

## Suggested execution prompt

Implementation/execution handoff is warranted, but no production code change is needed:

> Run one compact, explicit-control-only DEV-15 readout bridge. Preserve model/lens revisions, layers 13–21, rank 1, and existing prompts. Compare bare answer IDs 3721/1802 and frozen leading-space IDs 867/804 over (a) the existing request span and (b) the final assistant-prefill position. Record ordinary final-model ranks and J-lens ranks/top-1 IDs. On one complete prompt, assert rank/top-1 parity with the pinned Anthropic `JacobianLens.apply` implementation. Do not inspect original coverage for selection, add tokens, change layers/ranks, or generate interventions. Stop the assessment-token route after this audit whenever parity passes; only a concrete parity or answer-seam mismatch permits one mechanical fix and exact rerun.