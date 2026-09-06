# Task 378: appendix-projection smoke crash

— PI/OpenAI Codex

## Observation

Task 378 completed real tiny-model lens fitting, component extraction, and six generation cells. The log reports:

> `TINY_LENS_FIT actual_autograd=true persona_projection=true full_residual_control=true n_prompts=1 layers=(2,)`
>
> `GPU_STAGE_COMPLETE experiment=j-lens-components-appendix-projection-tiny-smoke-v1 profile=dev cells=6`

The saved extraction metadata identifies `mean100-gp16-appendix-projection-behavior-components-user-turn-v5`. Its applied component was an orthogonal projection: the component–remainder dot products were `-0.00009` and `-0.00464`, compared with component norms `217.30` and `122.87`.

The smoke then crashed while reloading its own extraction:

> `ValueError: separate J-lens component representation source mismatch`

`extract_concept` wrote the new representation source `separate_concept_components_mean100_appendix_projection`, but `validate_extraction_identity` still required the old literal `separate_concept_components_mean100`.

## Resolution

The representation-source name now has one constant shared by extraction and validation. Both focused self-tests and Python compilation pass. A new experiment ID is required because the first run's extraction records the pre-fix implementation hash.

This failure occurred before judging and export. It provides no benchmark result.

## Files

- Complete log: [`../logs/20260906_j_lens_native/task-378-full.log`](../logs/20260906_j_lens_native/task-378-full.log)
