# Concept-based J-lens DEV validation

— PI/OpenAI Codex

Scope: implement one signed additive concept contrast, then DEV-15 only. This is an adaptation of the paper's broader-concept representation, not the paper's coordinate swap. Operator and primary-source excerpts: [operator note](../plans/20260905_j_lens_concept_operator.md).

## Before DEV

Question: does adding the sparse concept contrast change judged agreement/flattery on the fixed DEV cohort, without obvious generation damage?

Only one new operator is tested. The old fixed-token run remains immutable. Adding its source-dependent overwrite is rejected here because it would reintroduce the unverified activity precondition. Full residual contrast or non-J remainder injection would test different representations; neither is run. The signed sparse contrast is chosen because it directly tests the authorized representation while using existing additive C units.

Predictions (not thresholds):
- Source/hook/cache bug, 20%: hashes disagree, hook/sign tests fail, or recorded +C/-C displacements are not opposites. Exact checks distinguish this from weak behavior.
- Topic-versus-behavior mismatch, 40%: decomposition names the concepts but outputs discuss agreement/criticism instead of adopting the intended behavior.
- Useful behavioral direction, 25%: paired judged effect has opposite intended signs with fluent answers at some tested C.
- Judge/benchmark confound, 10%: more disagreement or shorter answers score as success while raw answers are less useful.
- Unknown, 5%.

The fixed grid is C=1,4,16 on each side, one seed, greedy output, 512-token cap, 15 questions, AB once. Grid values are borrowed residual-norm units, not calibrated thresholds. Bare output is the behavioral control. A seeded 128-token-direction bank is a passive geometry null, not a behavioral placebo. No generalization claim follows from DEV.

SHOULD: ±C use the same vector hash and opposite coefficient signs; each layer hook fires once per generation batch and removes itself before continuation. Mathematical basis: h'=h+C*d, independent of source activity.
SHOULD: pursuit weights are nonnegative, at most 16 are nonzero, concept=j+remainder, and exact-fit/zero-residual inputs avoid 0/0.
TODO validate: the topic vectors actually influence style rather than topical language.

Diagnostic limitation: activity is measured at the final real chat-prompt token only, although intervention applies to all valid prompt tokens. It cannot rule out sign reversals or activity elsewhere. Unit-score vocabulary ranks and raw-score vocabulary ranks are saved separately. Raw small magnitude alone does not establish inactivity.

## Log

- Initial self-test: `J_LENS_CONCEPT_SELF_TEST_PASS nonnegative=true exact_fit=true zero_residual=true signed=true padding=true single_token=true cleanup=true reload=true cache_rejection=true` — [self-test.log](../logs/20260905_j_lens_concept/self-test.log).
- Tiny v1: actual autograd fit on one short prompt, six cells / 90 generated records; `JUDGE_COMPLETE required=45 missing=0`; `EXPERIMENT_EXPORT_COMPLETE ... arms=6 scenarios=90` — [tiny-smoke.log](../logs/20260905_j_lens_concept/tiny-smoke.log). This is pipeline proof, not model behavior evidence. The 45 unique calls reflect deduplicated repeated tiny-model responses, not missing cohort rows.
- Tiny v2 adds actual model hook verification: `CONCEPT_REAL_HOOK_CHECK changed_logits=true restored_logits=true calls_once=true removed=true` — [tiny-smoke-final.log](../logs/20260905_j_lens_concept/tiny-smoke-final.log).
- Current-code v3 and Qwen DEV: pending below.
