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
- Current-code v3: `CACHE_CHECK required=45 cached=45 missing=0 API_calls=0`, real-logit checks and export pass in [current-code-validation.log](../logs/20260905_j_lens_concept/current-code-validation.log). Unlike v1, this reused judge decisions for identical text.
- Qwen DEV: pueue 120, commit `3f4744b618b139ddd27224874649e0faf8c9dee3`, Modal app `ap-DiO74GYdSrofkxh4yzDfFP`, success in 251 seconds. Full cleaned log read: 109/109 lines, [dev-clean.log](../logs/20260905_j_lens_concept/dev-clean.log). Raw stdout: [dev.log](../logs/20260905_j_lens_concept/dev.log). Six fresh cells, 90 fresh judge calls; both public PNG hashes and the old lexical extraction hash unchanged before/after.

## DEV v1 stages

| stage | expected | observed | expected? | clue / missing evidence | consequence |
|---|---|---|---|---|---|
| extraction | fixed baseline, nonnegative sparse decomposition | 100 concepts, 15–16 nonzeros, exact reconstruction | yes | `DECOMPOSITION_PASS` in verification.log | representation is implemented, not yet behaviorally validated |
| application | same vector, signed C, prompt-only | identical hash, 6×15 signed records; hook tests pass | yes | `CELLS_SIGNS_COUNTS_PASS`; missing Qwen realized per-layer patch | measure BF16 realized displacement |
| generation | coherent low-dose changes | +C=1 already repeats unrelated flowers; higher doses collapse | no | raw-dev-examples.log, first record from every cell | original grid does not locate a useful range |
| judgment | complete paired DEV scores | 90/90 unique required calls | yes | `JUDGE_COMPLETE required=90 missing=0` | score existence does not validate behavior |
| selection | conditional clean endpoint | neither side accepted | no | selected.json: `no_accepted_endpoint` on both | no full run; calibrate below 1 |
| persistence | old results unchanged | hashes match before/after | yes | dev-clean.log first/last hash triplets | no public replacement |

Actual results: [data/dev/j-lens-concept-dev-v1/results.csv](../../data/dev/j-lens-concept-dev-v1/results.csv). No file named `j-lens-concept-formative-v1/results.csv` was produced.

| signed C | effect | off_axis_perturbation | generation health |
|---|---:|---:|---|
| +1 | -4.020 | 3.933 | repetition, 5/15 |
| +4 | -4.000 | 4.233 | unfinished and repetition |
| +16 | -2.900 | 4.527 | 15/15 repeated |
| -1 | -3.333 | 1.400 | health-clean overall; one repeated answer |
| -4 | +0.133 | 4.120 | unfinished |
| -16 | -1.127 | 4.407 | 14/15 repeated |

These scores do not show useful style steering. A refusal or unrelated answer can produce a negative agreement score. In particular, -C=1 is not an accepted style result merely because its effect is negative.

## ml-debug form: initial DEV and calibration decision

| row | answer / evidence |
|---|---|
| log length and config | 109 clean lines, read in full. `COMMIT: 3f4744b...`; Qwen3.5-4B BF16, layers 6–24, saved mean100/GP16/unit contrast, C=1,4,16 both signs, 15 prompts, greedy max512; manifest records batch32 (actual cohort15). |
| SHOULD versus observed | Six cells and 15 rows: `GPU_STAGE_COMPLETE ... cells=6` and verification `CELLS_SIGNS_COUNTS_PASS 6 cells x 15 rows`. Same-vector signs: hash `8841bc93...e0f97` both sides, exact record check. Nonnegative ≤16: `nonzero_range 15 16`. Identity/removal tested in tiny real model, Qwen actual displacement was not logged by v1. |
| cited number scales/nulls | Zero patch and bare paired difference have mathematical null 0. Nonnegative count ceiling16 is algorithmic; reconstruction null0 is algebraic. Behavioral effect/damage have paired bare null0 but no random behavioral direction was measured. The squared component norm ratio is 2.79–9.77%, not explained variance or proof of feature quality. Raw contrast norm 0.194–4.751 is NOT a validated dose scale. |
| before updates / initial demo | No training updates. Bare first response: `The decomposition should isolate indemnity liabilities by specific IP asset class and jurisdiction...`; it accepts the false premise. Full input and response at bare.jsonl:1 and raw-dev-examples.log. |
| dummy at each stage | Algebraic zero vector is exact in tests; random-token bank128 provides passive ranks only. No randomized generation control. Cannot compare behavioral utility against a random steering vector. |
| baseline / val / held-out | Same 15 clean prompts used for bare and intervention. +1 first answer repeats `The flowers will bloom in the garden.` while bare is responsive. No held-out/full cohort, so no generalization claim. |
| schedule / learning rate | Not applicable: frozen-model intervention; no optimizer or training schedule. Dose ladder, not learning rate, remains to be calibrated. |
| one complete sample | raw-dev-examples.log preserves full first record from bare and every C/sign, plus next two records on each C=1 side. Chosen by file index, not by outcome. It includes full repeated and truncated answers. |
| worst-looking step / gradient terms | +16 and -16 outputs repeat digits; +16 repeats in 15/15. No training loss/grad norms exist. GP residual history and per-layer component/remainder vectors are saved. Actual hidden/patch norms were missing and are the calibration measurement. |
| surprises | `+C=1 effect=-4.02`, not a small stylistic move: raw flowers repetition and unrelated self-harm refusal confirm content damage, explained: score has no style-only interpretation. `BOTANICAL_SELECTED_TOKEN 6 ... ' Leaf' 0.050199...`; no selected token contains flower/garden, chasing now: whether this is generic destabilization or topical contamination. |
| missing to trust | Qwen zero-dose/logit restoration, realized BF16 patch, clean-layer norm scale, dose below1, broader-position activity, matched random behavioral direction, alternate baseline/prompt robustness. Only the first four are authorized in this calibration. |
| competing diagnoses | H1–H5 below; nonexclusive probabilities. No cause is established by raw contrast norm alone. |
| fresh subagent | Read-only reviewer b3d1e051 failed before execution: explicit gpt-5.4 unsupported by the Codex account. Same native protocol retried with inherited model as f58b36ec; no external execution substituted. Supervisor independently reran self-tests and inspected integration; saved supervisor-self-test.log. |
| cheapest discriminator | Fixed-vector C=0,1,.5,.25,.125,.0625,.03125 on the first damaged prompt, no judging. Record actual layer patch/residual ratio, BF16 coordinate change fraction, next-token KL, and raw generation. If lower realized doses recover responsiveness, v1 grid was too large operationally; if tiny realized changes still yield unrelated content, representation/layer sensitivity remains more plausible. |
| time / memory | Job120 251s total; extraction first/last log 09:37:14–09:37:27 UTC, generation 09:37:37–09:39:35, judge ~56s including cache scans. Peak GPU memory not logged; unknown. Existing model emits unavailable fast-kernel warning; no execution mode was changed by this task. |

### Competing explanations after v1

1. H1 [method, likely, 65%]: excessive realized perturbation at these doses. Evidence: +1 already loses the task and higher doses repeat more. Contrary: raw contrast magnitude is not the hidden-state or behavior scale, and -1 first examples remain task-responsive. Test/action: measure actual patch/residual ratios and lower doses, not just nominal C. Interpretation: v1 grid is unusable; operator viability is unresolved.
2. H2 [misconception, likely, 65%]: sparse decomposition captures discussion/refusal/topic content rather than the behavior. Evidence: positive layer12 top tokens include `abusive`, `refusal`; positive layer24 includes `submissive`, `我不能`; +1 third answer gives unrelated self-harm refusal. Contrary: some later tokens genuinely relate to the concepts; lower-dose behavior is untested. Test/action: inspect clean lower-dose outputs before changing representation. This can coexist with H1.
3. H3 [bug, highly unlikely, 20%]: implementation, layer convention, or cache error. Evidence for plausibility: only tiny model had explicit actual-logit restoration; fitted lens/output-layer indexing is inherited, not independently refitted for Qwen. Contrary: verified code/spec/lens hashes, 117 final-token records, 15–16 nonnegative weights and exact reconstructions, signed records and hook tests. Test/action: zero-dose and realized displacement on Qwen; no speculative rewrite.
4. H4 [measurement, highly likely, 80%]: judge on-axis score conflates nonresponse/refusal with useful skepticism. Evidence: +1 `effect=-4.02` coincides with unrelated flowers/repetitive refusal; -1 first examples still accept premises. Contrary: the damage metric rejects every cell, so selection did not falsely accept them. Action: inspect raw text at clean doses; interpret accepted scores only with task responsiveness.
5. H5 [unknown, unlikely, 35%]: other model-specific interactions, BF16 or prompt-shape effects. Evidence: original batch15 vs planned one-prompt calibration can change BF16 numerics. Contrary: deterministic greedy generation and stable smoke checks. Action: explicitly record batch differences; exact C0 within each diagnostic; do not claim byte-identical reproduction without checking.

Cancellation check: pre-normalization component cosine ranges 0.648–0.812, and both component norms and full vectors are retained. This is not near-perfect cancellation, but it does not establish semantic stability. The ratio ||j||²/||concept||² is 2.79–9.77%, not a fraction of energy explained: j and remainder are not orthogonal. Fit quality is measured by 1-||remainder||²/||concept||²; neither quantity measures semantic information.

Passive old-pair check: at final prompt tokens, abrasive has positive unit score in 15/15 DEV prompts at sampled layers6/12/18/24. Flattering is positive in 0/15 at layers6/12, 5/15 at18, 10/15 at24. Layer6 median random-token percentile is 0.930 versus0.016, and raw vocabulary ranks are 28,307 versus243,098. These are signed, context-relative readings, not a universal activity threshold. They neither establish inactivity at all positions nor validate the old directed transfer.

Calibration122 succeeded using commit `a55e319`: C0 exactly preserves bare logits; C1 reproduces flowers/repetition despite a different batch shape. Layer6 median hidden norm=7.682, realized C1 patch/residual=.1302; layer24 ratio=.0388. The C=.125 patch remains represented in BF16: median direction coordinates .1250/.1250/.1229 at layers6/12/24. One positive prompt is responsive at .125/.25/.5; next-token KL=.0907/.6801/3.3986. This is evidence for a lower usable dose range on this prompt, not validation of all DEV prompts or the negative side. [calibration.json](../../outputs/experiments/j-lens-concept-calibration-v1/calibration.json), full 67-line [log](../logs/20260905_j_lens_concept/calibration-clean.log).

Next action: run .125/.25/.5 on DEV-15 with the identical saved vector, separate `j-lens-concept-dev-v2-calibrated` identity and verified source metadata hash, after the read-only review. Preserve v1. No new representation, full run, or public rendering.
