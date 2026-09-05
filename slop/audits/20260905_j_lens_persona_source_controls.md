# J-lens persona-source controls: DEV audit

— PI/OpenAI Codex

## Target and provenance

This audits four completed Qwen3.5-4B / DEV-15 jobs: pueue 137, 139, 141, and 142. All completed successfully, generated every requested arm, judged all required records, and exported CSV files. Full cleaned logs were read as `pqlog <id> 100000`: 101/101, 100/100, 97/97, and 93/93 lines respectively. The executed revisions are recorded at the top of each log: `bebee6306c5ddf20a4fbbe7bdb60cfa51be3c143`, `dd3e459b1786a303368622a28ddc732dd7a90a9e`, `80e4a0d86ff5d32df6028b205c540f9aba0f16c6`, and `22b8057b4f41caf69835e0d519f2da4854dc3e34`.

The question was whether replacing the failed topic vector with a matched sycophantic-minus-abrasive persona residual would make a signed J-space patch causally change agreement while preserving response quality. Jobs 139 and 142 were controls: same source/layers/patch scale as their J-projected counterpart, but use the complete paired residual rather than its GP16 J component.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| prompt-pair construction | 200 matched positive/negative source prompts | 200 pairs loaded in jobs 137/141 | yes | quoted logs below | direct prompt-persona behavior on DEV | source is reproducible, not yet causal |
| J projection | nonnegative GP16 component per layer | 15–16 selected rows per layer | yes | pueue 141 log | randomized direction geometry null | algebraic construction ran |
| patch application | same signed unit vector, prompt-only, measured realization | all cells have ratio and KL diagnostics | yes | manifests | BF16 coordinate fractions in these runs | nominal C is not the conclusion |
| generation | coherent task responses | no unfinished/repetition/role leak in all 12 audited cells of jobs 141/142 | yes | manifest `health` | human response-quality evaluation | result is not explained by visible collapse |
| behavior | `+C` moves agreement; `-C` moves critical assessment | positive direction is negative; negative direction is near zero or negative | no | results CSVs | second seed, direct-instruction positive control | no usable bipolar endpoint |
| projection control | full residual differs materially if GP16 projection lost a causal component | same qualitative sign pattern as GP16 | no | 141 versus 142 result table | second seed | source itself is insufficient at this locus/scale |
| persistence | source artifacts and judged outputs saved | all four exports completed | yes | quoted completion lines | git-tracked output directory | formative evidence is recoverable locally |

## Primary evidence

### Job 137 — teacher-forced answer-state J projection

`slop/logs/20260905_j_lens_concept/persona-jspace-dev.log` is the execution record for pueue 137. It states the prior failure and the source change:

> WHY: the Tell-me-about concept vector made both signs more skeptical in lower layers. This source uses matched prompts that differ only in the requested persona.
> SCALE: nominal values label unit per-layer additions only. The manifest records realized patch/residual ratios and final-token KL for every cell; interpret behavior against those measurements, not against coefficients from another representation.
> COMMAND: uv run python scripts/experiment.py j_lens_concept --dev --j-lens-source persona --experiment-id j-lens-persona-jspace-dev-v1 --coefficients-plus 0.03125,0.0625,0.125 --coefficients-minus 0.03125,0.0625,0.125

The source is a contemporaneous command log written by the run launcher; it reports intent and execution, not behavioral success.

> 2026-09-05 11:49:35.433 | INFO     | __main__:gpu_stage:766 - GPU_STAGE_COMPLETE experiment=j-lens-persona-jspace-dev-v1 profile=dev cells=6
> EXPERIMENT_GPU_COMPLETE id=j-lens-persona-jspace-dev-v1 profile=dev cells=6
> Stopping app - local entrypoint completed.

> 2026-09-05 19:50:26.350 | INFO     | __main__:main:683 - JUDGE_COMPLETE required=83 missing=0
> 2026-09-05 19:50:28.472 | INFO     | judge:experiment_rows:297 - experiment manifest id=j-lens-persona-jspace-dev-v1 profile=dev cells=6 demo_sides=90
> EXPERIMENT_EXPORT_COMPLETE id=j-lens-persona-jspace-dev-v1 profile=dev arms=6 scenarios=90

These establish that the requested pipeline completed. They do not establish that the score measures useful behavior.

At the lowest J-projected perturbation, `data/dev/j-lens-persona-jspace-dev-v1/results.csv` records `+C=-1.1` and `-C=-0.6` at `C=0.03125`. The corresponding mean final-token KLs are 0.00581 and 0.00677, with per-layer median patch/residual ratios 0.0009–0.0044 (`outputs/experiments/j-lens-persona-jspace-dev-v1/manifest.json`). Thus responses changed under a small measured perturbation, but neither sign moved in the intended opposing direction.

### Job 139 — teacher-forced full-residual control

The pueue label tests whether the projection was the missing causal component:

> QUESTION: did the sparse J projection, rather than the matched persona residual source, remove the causal style signal?
> CONTROL: normalize and apply the complete paired residual difference at each layer. The source prompts, layer set, signed additive operator, generation, cohort, and nominal scales match j-lens-persona-jspace-dev-v1.

Source: `slop/logs/20260905_j_lens_concept/persona-full-residual-control.log`; it is a direct run record.

> 2026-09-05 11:56:23.012 | INFO     | __main__:gpu_stage:777 - GPU_STAGE_COMPLETE experiment=persona-full-residual-control-dev-v1 profile=dev cells=4
> EXPERIMENT_GPU_COMPLETE id=persona-full-residual-control-dev-v1 profile=dev cells=4

> 2026-09-05 19:56:55.773 | INFO     | __main__:main:683 - JUDGE_COMPLETE required=51 missing=0
> 2026-09-05 19:56:58.127 | INFO     | judge:experiment_rows:297 - experiment manifest id=persona-full-residual-control-dev-v1 profile=dev cells=4 demo_sides=60
> EXPERIMENT_EXPORT_COMPLETE id=persona-full-residual-control-dev-v1 profile=dev arms=4 scenarios=60

At the matched smallest scale, its result is `+C=-0.3133`, `-C=+0.0200` (`data/dev/persona-full-residual-control-dev-v1/results.csv`); KL is 0.00551 and 0.00610 respectively. The full direction therefore did not recover a positive sycophantic response.

### Jobs 141 and 142 — matched generation-prefill source and full-residual control

Job 141 moves extraction to the same final prompt position that later receives the patch:

> WHY: the teacher-forced answer-state persona contrast failed both as a GP16 J projection and as its full residual control. This run measures the final prompt state immediately before the model begins its response, matching the patched position.
> METHOD: 200 paired generic user prompts differ only in sycophantic versus abrasive instruction. GP16 J projection, all layers, signed additive patch, and DEV-15 are otherwise unchanged.

Source: `slop/logs/20260905_j_lens_concept/persona-prefill-jspace-dev.log`; this is execution intent, not an outcome claim.

> 2026-09-05 12:01:11.974 | INFO     | vjp_steering.j_lens_concept:extract_persona_contrast:341 - persona layer=6 direction=j_gp16 applied_norm=0.0692 j_norm=0.0692 remainder_norm=0.3619 selected=16
> 2026-09-05 12:01:14.538 | INFO     | vjp_steering.j_lens_concept:extract_persona_contrast:341 - persona layer=24 direction=j_gp16 applied_norm=6.2371 j_norm=6.2371 remainder_norm=24.9579 selected=16

This observation shows that the sparse J component is substantially smaller than the paired full difference before either is normalized. The saved geometry has full/J cosine 0.182, 0.239, 0.279, and 0.236 at layers 6, 12, 18, and 24 (`outputs/experiments/j-lens-persona-prefill-jspace-dev-v1/manifest.json`). That is evidence of a major directional change, not proof that the discarded residual is causal.

> 2026-09-05 12:01:49.080 | INFO     | __main__:gpu_stage:811 - GPU_STAGE_COMPLETE experiment=j-lens-persona-prefill-jspace-dev-v1 profile=dev cells=6
> EXPERIMENT_GPU_COMPLETE id=j-lens-persona-prefill-jspace-dev-v1 profile=dev cells=6
>
> 2026-09-05 20:02:34.096 | INFO     | __main__:main:683 - JUDGE_COMPLETE required=80 missing=0
> 2026-09-05 20:02:36.492 | INFO     | judge:experiment_rows:297 - experiment manifest id=j-lens-persona-prefill-jspace-dev-v1 profile=dev cells=6 demo_sides=90
> EXPERIMENT_EXPORT_COMPLETE id=j-lens-persona-prefill-jspace-dev-v1 profile=dev arms=6 scenarios=90

At `C=.03125,.0625,.125`, the J-projected `+C` effect is `-0.5067,-1.4000,-0.5667`; `-C` is `-0.0867,-0.0467,-0.1000` (`data/dev/j-lens-persona-prefill-jspace-dev-v1/results.csv`). Its KL range is 0.00563–0.09766. All six arms have zero unfinished, role-leak, and repeated records, e.g. the `.125` positive arm records `"unfinished": 0, "role_leaks": 0, "repeated": 0` in `outputs/experiments/j-lens-persona-prefill-jspace-dev-v1/manifest.json`.

Job 142 tests the full residual under the same source and nominal scale:

> QUESTION: does the full persona difference at the response-prefill state steer behavior when its GP16 J projection does not?
> CONTROL: same 200 matched persona-prefill prompts, layers, additive signed patch, DEV cohort, and scales as j-lens-persona-prefill-jspace-dev-v1. Only replace unit(GP16 J component) with unit(full paired residual difference).

Source: `slop/logs/20260905_j_lens_concept/persona-prefill-full-residual-control.log`; it is the job's direct record.

> 2026-09-05 12:05:12.934 | INFO     | __main__:gpu_stage:811 - GPU_STAGE_COMPLETE experiment=persona-prefill-full-residual-control-dev-v1 profile=dev cells=6
> EXPERIMENT_GPU_COMPLETE id=persona-prefill-full-residual-control-dev-v1 profile=dev cells=6
>
> 2026-09-05 20:05:57.294 | INFO     | __main__:main:683 - JUDGE_COMPLETE required=74 missing=0
> 2026-09-05 20:05:59.671 | INFO     | judge:experiment_rows:297 - experiment manifest id=persona-prefill-full-residual-control-dev-v1 profile=dev cells=6 demo_sides=90
> EXPERIMENT_EXPORT_COMPLETE id=persona-prefill-full-residual-control-dev-v1 profile=dev arms=6 scenarios=90

Its `+C` effects are `-0.5867,-0.6067,-1.1133`; its `-C` effects are `-0.0067,-0.0600,0.0000` at the same three scale labels (`data/dev/persona-prefill-full-residual-control-dev-v1/results.csv`). Final-token KL is 0.00847–0.16178. Thus the control has the same qualitative outcome: positive direction decreases the benchmark score, and negative direction does not supply an opposing positive behavioral effect.

Raw outputs were inspected in every side at the largest scale. For example, both J and full-control `.125` legal/medical samples stay topical and grammatical in their corresponding JSONL files. This was a fixed selection rule: first four records in each side, not outcome-chosen examples. It does not prove all 15 answers are equally useful; automated health misses subtle factual or behavioral failure.

## ML-debug form

| row | answer |
|---|---|
| log length and config | Full cleaned logs: 137=101, 139=100, 141=97, 142=93 lines. All use Qwen3.5-4B, DEV-15, greedy responses, all layers 6–24; source and projection differ as shown above. |
| `SHOULD` / observed | Expected signed bipolar behavior was absent. `JUDGE_COMPLETE required=80 missing=0` and `EXPERIMENT_EXPORT_COMPLETE ... arms=6 scenarios=90` show complete evaluation for the two prefill runs, not behavioral success. |
| cited-number null | Behavioral effect has paired bare null 0. KL and patch/residual have mathematical zero-patch null 0. No random direction, shuffled source, or prompt-persona positive control was measured, so no calibrated behavioral threshold exists. |
| before updates | Frozen-model intervention; bare DEV responses are stored in every experiment's `bare.jsonl`. No optimizer/schedule exists. |
| dummy / baseline | Bare generation is the matched behavioral baseline. Full residual is the novel-part-removed control for GP16 projection. Neither is a random behavioral control. |
| val / held-out | Same DEV-15 cohort measures bare and intervention; no held-out cohort or second seed. No generalization claim is supported. |
| full sample | First four `.125` records per side were read from each `cells/{plus,minus}/c0p125.jsonl`; these are task-responsive paraphrases, linked above. |
| worst-looking result | J prefill `+C=.0625` has `effect=-1.4000`; full prefill `+C=.125` has `effect=-1.1133`, but generation health remains clean. No gradients/losses exist for this frozen intervention. |
| surprise | Changing from GP16 to full residual raises KL at `.125` from 0.09766 to 0.14670 (+) and 0.09335 to 0.16178 (−), yet does not reverse the behavioral direction. Explained: full residual changes logits more, but not toward the desired behavior. |
| needed to trust | direct literal-persona prompt control on DEV; random/shuffled direction at matched ratio; second seed; held-out set; manual/blind review of all answers; BF16 coordinate-survival field for each arm. |
| competing diagnoses | H1–H5 below. |
| fresh review | No fresh external review ran after job 142. This is missing evidence, not a clean review. |
| cheapest discriminator | Directly prepend the same literal persona instructions to DEV prompts and judge them against bare. If this does not score with opposite signs, the benchmark/judge sign is unsuitable; if it does, source-vector construction or application remains the likely fault. |
| time / memory | Jobs took 135 s (137), 114 s (139), 141 s (141), and 162 s (142) including judging. Peak GPU memory is not logged. |

## Hypotheses

### H1 [method | Likely | 65%]

- **Mechanism:** Mean residual differences from literal persona instructions are not a context-independent causal steering direction when added across all layers/tokens.
- **Evidence:** The full prefill control reports `+C=-0.5867,-0.6067,-1.1133` and `-C=-0.0067,-0.0600,0.0000` (`data/dev/persona-prefill-full-residual-control-dev-v1/results.csv`), despite the job completing all 90 judged records: `JUDGE_COMPLETE required=74 missing=0`.
- **Contrary evidence:** One seed and 15 prompts are not enough to eliminate a weak effect or judge variance.
- **Discriminating test:** literal prompt-persona positive control. Opposing useful prompt effects would make this construction/application failure more likely.
- **Fix/action:** do that positive control before another J decomposition or dose/layer sweep.
- **Interpretability:** partial; this exact all-layer additive construction is tested, not J-lens methods in general.

### H2 [method | Likely | 60%]

- **Mechanism:** GP16 projection drops most of the prefill direction, but this alone cannot explain the failure because the complete residual also fails.
- **Evidence:** Saved prefill cosines are 0.182–0.279; job 142's full residual still yields no positive `+C` effect.
- **Contrary evidence:** J and full directions could differ in a way that masks an otherwise useful localized subspace.
- **Discriminating test:** only after prompt-positive-control passes, compare localized full versus J directions at matched realized ratios.
- **Fix/action:** do not claim sparse projection is the sole cause.
- **Interpretability:** yes for rejecting the claim that full residual already rescues this all-layer construction.

### H3 [measurement | Likely | 65%]

- **Mechanism:** The judge score is sensitive to factual/assertion changes that do not equal useful sycophancy control.
- **Evidence:** Several per-scenario records show large negative effects, e.g. `-8.1`, alongside clean generation health; the result files retain these values.
- **Contrary evidence:** the consistent lack of an opposite `-C` effect survives aggregation and is not only one outlier.
- **Discriminating test:** direct persona instruction plus blinded manual annotation of agreement, challenge, factuality, and usefulness.
- **Fix/action:** calibrate the benchmark before interpreting a small score difference as behavioral steering.
- **Interpretability:** partial; raw outputs establish coherence, not the judge's construct validity.

### H4 [bug | Unlikely | 35%]

- **Mechanism:** A sign, chat-template, or patch-location bug could make the source direction misaligned with intended behavior.
- **Evidence:** Both sources show positive direction moving negative, which is compatible with a sign mismatch.
- **Contrary evidence:** signed patches, cached provenance, real-hook checks, and full-vs-GP controls ran; the code path is less likely to be wholly inert.
- **Discriminating test:** literal-persona prompt control first, then compare direct induced residual direction to extracted direction at the same final prompt position.
- **Fix/action:** do not flip signs blindly; measure direction alignment to the literal behavioral control.
- **Interpretability:** partial.

### H5 [data | Unlikely | 40%]

- **Mechanism:** Generic factual source prompts do not span the adversarial false-premise behavior measured by DEV-15.
- **Evidence:** The source uses 200 generic branching prompts while DEV uses legal, medical, software, finance, and physics false-premise prompts.
- **Contrary evidence:** broad persona traits could reasonably generalize; this was not tested on a held-out, domain-matched source set.
- **Discriminating test:** source directions from disjoint, domain-matched non-DEV prompts versus generic prompts, after the prompt-control test validates the benchmark.
- **Fix/action:** avoid reusing DEV questions as source prompts; construct a separately authored domain-matched source set only if H3 is cleared.
- **Interpretability:** partial.

## Decision

1. **Resolve-condition verdict: not met.** Job 142 asked whether full prefill residual would steer behavior when GP16 did not. It did not: `+C` stayed negative and `-C` near zero at all three scales.
2. **Prediction check:** source-position matching predicted a possible recovery; contradicted by jobs 141/142. Projection-loss-only predicted full residual recovery; contradicted by job 142. Coherence predicted at low scale; supported by all recorded health fields.
3. **Earliest unsupported link:** “literal persona prompt residual difference is a transferable causal persona direction.” The full prefill control fails to support it.
4. **Validity:** define invalid as a wrong output source, broken patch, missing judged arms, or widespread generation collapse. `P(invalid)≈0.20–0.35`; this is a credible negative for these two residual-source implementations, not a negative result for J-lens broadly.
5. **Highest-information clues:** (1) full residual fails with same sign pattern as GP16; isolates source/application beyond sparsity. (2) source moved to actual response prefill and still fails; isolates teacher forcing as insufficient explanation. (3) clean outputs at KL 0.006–0.162; not obvious collapse.
6. **Missing metrics, ordered:** literal-persona prompt behavioral control; random/shuffled direction control; second-seed score spread; held-out cohort; blind manual labels; coordinate survival.
7. **Bugs requiring code changes:** none established. Do not make a sign flip or new dose change without the direct prompt control.
8. **Misconceptions requiring reinterpretation:** a residual difference caused by a persona instruction is not thereby a portable behavior direction; a sparse component's semantic token list is not behavioral validation.
9. **What changes the verdict:** a clean direct prompt control with opposite intended scores would make source/application failure likely; a failed direct prompt control would make the current evaluator unsuitable for this goal.
10. **Recommended sequence:** first add the direct literal-persona prompt positive/negative control to the existing DEV evaluation path, with raw outputs and current judge. Wait for that readout. If it passes, use its induced final-prefill residual as a measured directional reference before any new J operator. If it fails, repair the behavioral metric before any further steering run. Do not combine source redesign, layer localization, and dose changes in the next run.
