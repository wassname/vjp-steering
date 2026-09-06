# Task 417: real-Qwen target-ordered J-lens extraction

Target: pueue task 417, `j-lens-behavior-components-target-ordered-source-v8`, run in `/workspace/2026/jspace/j-steer_pub` from the committed v8 code at `f7e4ee4`/`f169927`. The pueue command, label, timestamps, and status are in task 417. The complete local log has 386,071 lines because Modal printed the full extraction arrays; it was parsed as one valid JSON object. A bounded committed view is [`component-target-ordered-v8-source-summary.json`](../logs/20260906_j_lens_native/component-target-ordered-v8-source-summary.json). The 11.8 MB full log remains local at `slop/logs/20260906_j_lens_native/component-target-ordered-v8-source.log`.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| model and J-lens load | Qwen3.5-4B BF16 and 1,000-prompt lens | loaded | yes | metadata: `model=Qwen/Qwen3.5-4B`, `dtype=bfloat16`, `lens_n_prompts=1000` | peak GPU memory | intended model and lens executed |
| concept extraction | non-negative GP16 reconstruction for both concepts at layers 13–21 | complete | yes | each layer reports 15–16 active coefficients and `reconstruction_error=0` | alternate prompt wording | the specified components were formed |
| pair geometry | finite numerical rank two; condition close to preceding extraction | condition 2.198–3.070 | yes | layer 15 is largest at `3.0703`; layer 21 is smallest at `2.1979` | perturbation sensitivity | rank does not prevent the test |
| persistence | distinct side hashes and validated targets | complete | yes | `+C=dd4e78...`, `-C=eb2f58...`; `EXTRACTION_COMPLETE` | downloaded local reload | calibration will load the saved Modal vectors and recheck hashes, targets, basis, and dual |
| unsteered DEV coordinates | each requested direction should affect some final prompt positions | +C affects 0/15 and -C affects 15/15 at every layer | no | summary fields `plus_target_changed_final_positions=0` for all nine layers | all-token changed fractions | +C may be weak because final prompt coordinates are already positive-ordered |
| behavior | not part of extraction | absent | unclear | no generations or judges in this task | DEV dose grid | no sycophancy claim follows |

## Chronology

The task waited in the shared queue, then Modal executed for 52 seconds. It loaded Qwen and the J-lens without an exception. The prompt consumed by extraction was:

> `Tell me about sycophantic agreement and flattery toward the user`

The nine layer rows were finite. For example:

> `concept layer=13 j_norms=[0.837653..., 1.081595...] remainder_norms=[3.473032..., 4.194505...] contrast_norm=0.6945`

> `concept layer=21 j_norms=[4.395890..., 3.625978...] remainder_norms=[15.061822..., 13.190500...] contrast_norm=3.3953`

The observed condition-number range, 2.198–3.070, matches the prior expectation of about 2.2–3.2. Both decompositions have non-negative GP support and reconstruction error zero. The implementation and specification hashes match v8.

The main anomaly appears in the unsteered DEV coordinate inventory. At every layer and for every one of the 15 final prompt positions, the positive component coordinate already exceeds the negative coordinate. Median positive-minus-negative differences rise from `0.502` at layer 13 to about `1.29` at layer 21. Therefore +C target ordering is identity at those final positions, while -C exchanges all of them. This does not show that +C is globally identity because the intervention covers every attended prefill position. Calibration must report each side's changed-position fraction and KL.

## ML-debug form

| row | answer |
|---|---|
| log length and config | 386,071 lines; Qwen3.5-4B, BF16, layers 13–21, GP16, all attended prefill positions |
| `SHOULD:` lines | none |
| null and baseline | expected geometry came from v7b on the same extracted components: condition 2.20–3.07; task 417 reproduces it |
| before intervention | extraction only; unsteered final coordinates are positive-ordered on 135/135 layer-scenario pairs |
| dummy comparison | neutral concept baselines are used for mean subtraction; no behavioral dummy occurs here |
| held-out baseline | DEV prompts are separate from the two concept prompts but were recorded in extraction metadata |
| schedule | no training |
| complete sample | the exact concept prompt and all 15 unsteered coordinate pairs per layer are retained in the full metadata |
| worst step | no numerical failure; the strongest concern is zero +C final-position changes |
| surprise | `plus_target_changed_final_positions=0` at every layer; explained at the measured final prompt positions, still chasing all-token behavior |
| evidence still needed | all-token changed fractions, BF16 residuals, coherent generations, judged effects, random-region comparison |
| diagnoses | valid extraction 95%; +C remains behaviorally weak 65%; other token positions provide +C signal 35%; concept wording measures discussion rather than enacted behavior 55%; unknown 10% |
| fresh review | preflight reviewer required rank/cache checks and adaptation labeling; both are present in this extraction |
| cheapest next test | the existing two-direction α=0,.25,.5,.75,1,1.25,1.5,2 calibration |
| wall time | 52 s Modal execution after shared-queue wait; GPU memory was not logged |

## Hypotheses

### H1 [method | Likely | 65%]

- **Mechanism:** +C target ordering changes too few relevant positions because unsteered benchmark prompts are already more active on the positive component.
- **Evidence:** all 135 final layer-scenario coordinate pairs have positive greater than negative; layer-13 median difference is `0.502` and layer-21 median is `1.290`.
- **Contrary evidence:** only final prompt positions were measured; the method patches all attended positions, and earlier tokens can alter downstream computation.
- **Discriminating test:** calibration should report a much smaller +C changed-hidden fraction and KL than -C if this is the main limitation. Similar fractions and KL would favor earlier-token mediation.
- **Fix/action:** run calibration unchanged; do not infer failure from final positions alone.
- **Interpretability:** yes for the coordinate inventory, no for behavior.

### H2 [data | Likely | 55%]

- **Mechanism:** “Tell me about sycophantic agreement…” elicits a critical discussion of sycophancy, so its J-space component may not represent enacted agreement.
- **Evidence:** the positive component is already stronger than the negative component on all neutral benchmark final positions, despite the benchmark containing both false and true premises.
- **Contrary evidence:** this ordering could reflect basis scaling or a shared positive offset rather than semantic inversion.
- **Discriminating test:** if +C target ordering is active but judges move critical, inspect the component's selected tokens and replace descriptive prompts with matched enacted behavioral responses.
- **Fix/action:** wait for judged direction signs before changing extraction prompts.
- **Interpretability:** partial; extraction is valid for the written phrase, not necessarily the intended behavior.

### H3 [bug | Remote | 8%]

- **Mechanism:** side target indices or vectors were serialized incorrectly despite distinct hashes.
- **Evidence:** hashes differ and extraction returned only after `validate_component_pair()` checked targets, shared bases, duals, and numerical rank.
- **Contrary evidence:** local vector files were not downloaded in this task.
- **Discriminating test:** calibration reloads the remote source and fails before generation if any invariant differs.
- **Fix/action:** treat successful calibration startup as the reload check.
- **Interpretability:** yes if reload succeeds.

### H4 [measurement | Unlikely | 30%]

- **Mechanism:** aggregate judged effects can look strong because a few false-premise corrections dominate.
- **Evidence:** this occurred in v7b fixed exchange; no behavioral distribution exists yet for v8.
- **Contrary evidence:** target ordering separates position subsets and may distribute effects differently.
- **Discriminating test:** compare aggregate effect, median scenario effect, and complete raw responses after judging.
- **Fix/action:** retain all responses and report concentration before dose selection.
- **Interpretability:** unresolved.

## Decision

1. **Resolve-condition verdict:** met. The label required finite rank-two bases, distinct target hashes, and valid metadata; all are present.
2. **Prediction check:** condition 2.2–3.2 supported; nine layers supported; distinct hashes supported; BF16 extraction completion supported.
3. **Earliest unsupported link:** the phrase-derived component pair corresponds to enacted sycophancy and critical assessment. Judged DEV response changes are required.
4. **Validity:** invalid means the saved vectors do not implement the declared extraction. `P(result is invalid) ≈5%`; this is a credible positive extraction result with a substantive behavioral warning.
5. **Highest-information clues:** condition numbers reproduce; distinct hashes validate direction state; zero +C final-position exchanges predicts asymmetric behavior.
6. **Missing metrics:** all-token side fractions, BF16 coordinate residuals, generation coherence, judge effects, scenario concentration, random-region status.
7. **Bugs requiring code changes:** none observed in task 417.
8. **Misconceptions requiring reinterpretation:** successful extraction is not successful steering, and the paper did not test sycophancy.
9. **What would change the verdict:** cache-validation failure would invalidate persistence; coherent opposite-sign DEV effects outside random would establish a working adaptation.
10. **Recommended sequence:** run the unchanged calibration, inspect all generated responses and intervention diagnostics, judge DEV, then decide whether the extraction prompts or operator need the next change. Do not start all-100 yet.

— PI/OpenAI Codex
