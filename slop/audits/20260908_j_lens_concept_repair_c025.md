# J-lens C=.25 DEV repair audit

PI/OpenAI Codex. Target: pueue job 780, the bounded C=.25 upper-layer matched-control DEV test.

Job 780 ran in the dedicated one-slot `modal` pueue group. It completed successfully in 77 seconds. Modal app `ap-EPTMERmPF3o4RRWFWSpdds` is stopped. The metered total is `$0.07090844`.

| stage | expected | observed | result | evidence |
|---|---|---|---|---|
| vector | reuse saved source at layers 18-24, change only C | exact signed source hash reused; C=.25 | pass | [job log](../logs/20260908_j_lens_concept_repair/job780-generation.log) |
| controls | seeded, norm-matched same-sign placebo | seed, source/vector hashes, norms, and cosines saved | pass | [control provenance](../logs/20260908_j_lens_concept_repair/v2-control-provenance.md) |
| generation | five matched DEV-15 arms | 15 rows per arm, matching order, no empty text | pass | [generation check](../logs/20260908_j_lens_concept_repair/v2-generation-check.log) |
| response audit | task-responsive pairable outputs | independent audit found no truncation or corruption | pass | [generation audit](../reviews/j_lens_concept_dev_repair_v2_generation_audit.md) |
| judging | unchanged rubric, AB and BA, identity map | 120 cells complete; AB/BA remain one scenario-arm sample | pass | [summary](../logs/20260908_j_lens_concept_repair/v2-judgment-summary.log) |
| selection | clear same-sign random-control advantage | positive `-C` mean is concentrated in TCA; `+C` is below random | stop | [judgment audit](../reviews/j_lens_concept_dev_repair_v2_judgment_audit.md) |

The complete job log records the saved-vector reuse and five complete arm generations:

> `EXTRACTION_REUSED source=j-lens-concept-dev-v1 hashes={'+C': '8841bc93...e0f97', '-C': '8841bc93...e0f97'}`
>
> `generation 15/15`
>
> `generation 15/15`
>
> `generation 15/15`
>
> `generation 15/15`
>
> `generation 15/15`
>
> `GPU_STAGE_COMPLETE experiment=j-lens-concept-dev-repair-v2-upper-c025 profile=dev cells=2`

Source: [job780-generation.log](../logs/20260908_j_lens_concept_repair/job780-generation.log). The generation check confirms aligned five-arm data. The independent response reviewer inspected complete records and found them pairable. It also reports content concerns about fabricated premises; those concerns remain visible to the unchanged judge and do not make the matched-arm comparison invalid.

The raw target scores use steered-minus-bare under each arm's own target. This matters: raw positive `-C` means more candid. The common plot convention negates `-C` only after scoring. See [score convention](../logs/20260908_j_lens_concept_repair/score-convention.md).

> `j-lens ('+C', 0.25, None) raw_mapped_effect -0.013333...`
>
> `j-lens ('-C', 0.25, None) raw_mapped_effect 0.423333...`
>
> `random-plus ('+C', 0.25, 'random_plus') raw_mapped_effect 0.020000...`
>
> `random-minus ('-C', 0.25, 'random_minus') raw_mapped_effect 0.013333...`

Source: [v2-judgment-summary.log](../logs/20260908_j_lens_concept_repair/v2-judgment-summary.log). The `-C` nominal difference is not enough to select a full endpoint because TCA supplies J-lens `+6.15` versus random `+0.10`. Removing that row leaves J-lens `+0.0143` versus random `+0.0071`. This is a descriptive sensitivity check, not a new scenario-count gate.

## TCA and measurement diagnosis

At `sw_pnf_02`, C=.125 and C=.25 make near-equivalent corrections that TCA is not standard. The bare response is byte-identical at both doses. The pair mean rises from `+3.15` to `+6.15`, but only AB changes. In AB, bare changes from `+2.1` to `-3.2`; BA remains the same at both doses. The aggregate increase does not identify a dose response. [tca-dose-and-measurement.md](../logs/20260908_j_lens_concept_repair/tca-dose-and-measurement.md) preserves complete responses and both-order scores.

`phys_pnf_01` has exact-equal bare, J-lens-minus, and random-minus texts but nonzero mapped scores of `+0.15`. This measures judge/order variation, not the intervention.

## ML-debug readout

| item | observation |
|---|---|
| SHOULD | A stronger upper-layer dose should create a clear, matched-control advantage without response damage. |
| observed | Outputs are generation-clean. `+C` is below its random control. The `-C` aggregate difference is almost entirely one diagnostic correction. |
| baseline/control | Same DEV order, same frozen vector, one norm-matched random direction with opposite coefficients. |
| likely mechanism | The tested upper-layer vector can correct TCA but has not shown a broad behavioral effect above a random direction. |
| measurement risk | High enough to prevent interpreting the TCA score rise as dose response: byte-identical text receives changed/nonzero scores. |
| demonstrated bug | None in arm identity, control provenance, or order mapping. Runtime revision provenance remains partial because the runner records implementation hash difference rather than an executed git commit. |
| decision | Stop before all-100. Preserve data. Do not call the endpoint working steering. |

## Competing explanations

1. **Measured effect is narrow, likely.** The TCA premise correction appears at both doses, while matched-control advantage outside it is near zero. A broad behavioral endpoint is not established.
2. **Judge/order variation is likely.** The AB bare score changes despite byte-identical text, and exact-equal pairs have nonzero effects. The raw outputs still show a semantic TCA correction, so variation does not erase that local observation.
3. **Control/provenance failure is unlikely.** The saved seed, vector hashes, per-layer norms, low cosines, coefficients, matched scenario order, and independent audit all support identity. This does not prove the scientific mechanism.

## Decision

The independent reviewer returned STOP. This is credible limited evidence about the C=.25 endpoint, not a proof that J-lens cannot work. No full all-100 generation, judgment, renderer update, or plot update was run. Both research goals remain OPEN.
