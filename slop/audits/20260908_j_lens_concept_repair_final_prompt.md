# Final-prompt J-lens DEV repair audit

PI/OpenAI Codex. Target: pueue task 782, a three-arm final-prompt-only `-C=.25` test.

| stage | expected | observed | result | evidence |
|---|---|---|---|---|
| execution position | patch one final non-padding prompt token per row | 15 rows, one final selected position, zero padding | pass | [generation check](../logs/20260908_j_lens_concept_repair/final-prompt-generation-check.log) |
| vector/layers | reuse frozen vector at layers 18-24 | source SHA `8841bc...e0f97`, layers 18-24 | pass | [job log](../logs/20260908_j_lens_concept_repair/job782-generation.log) |
| controls | one seeded norm-matched random-minus | shared final-prompt execution mask and signed `-0.25` coefficient | pass | [generation audit](../reviews/j_lens_final_prompt_generation_audit.md) |
| generation health | three matched complete DEV-15 arms | no refusal, truncation, repetition, role leak, or task loss | pass | [generation audit](../reviews/j_lens_final_prompt_generation_audit.md) |
| unchanged judgment | AB and BA, one paired sample each | 60 required cells, 11 new calls, 49 cache hits | pass | [judging log](../logs/20260908_j_lens_concept_repair/final-prompt-judging.log) |
| endpoint selection | clear same-sign control advantage | `+0.2600` J-lens versus `+0.2267` random-minus; measurement-sensitive difference | stop | [judgment audit](../reviews/j_lens_final_prompt_judgment_audit.md) |

The job log shows the bounded run completed three 15-row generations:

> `EXTRACTION_REUSED source=j-lens-concept-dev-v1 hashes={'+C': '8841bc93...e0f97', '-C': '8841bc93...e0f97'}`
>
> `generation 15/15`
>
> `generation 15/15`
>
> `generation 15/15`
>
> `GPU_STAGE_COMPLETE experiment=j-lens-concept-dev-repair-v3-final-prompt-c025 profile=dev cells=1`

The execution manifest separates current implementation `448d8e69...39746` and `final_prompt` mask metadata from legacy reused extraction metadata. It reports one selected final non-padding token per each of 15 rows. J-lens and random-minus store that same mask metadata. This supports the mechanical application claim, not a behavioral mechanism claim.

Raw effects use steered-minus-bare under the `-C` candidness target. The complete order audit reports J-lens `+0.2600`, random-minus `+0.2267`, with three J-lens strict reversals. `phys_pnf_01` creates the visible difference, but its J-lens AB/BA values are `-0.3/+1.3`; the byte-identical random/bare pair has a nonzero `+0.15`. This is measurement evidence.

## ML-debug readout

| item | observation |
|---|---|
| SHOULD | Changing only application position should create a clear J-lens advantage over matched random, if this position is the repair. |
| observed | Generation is clean and mask execution is verified. The target difference is `+0.0333`, dominated by one order-sensitive row. |
| control | Random-minus shares coefficient magnitude, source-vector norms, final-prompt mask, cohort, and decoder. |
| likely interpretation | This final-prompt endpoint has no clear behavioral advantage over random. |
| not established | The older user-turn position did not cause the narrow TCA result. The current negative endpoint does not rule out every position or representation change. |
| decision | Stop before all-100 and public rendering. |

No all-100 generation, judging, table update, or plot update was run. Both research goals remain OPEN.
