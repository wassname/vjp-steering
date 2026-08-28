# API judge task 9 DeepInfra structured-output failure

Prepared by PI on 2026-08-28.

Target: judge every cell from the four fresh `validity-20260828-r2` walks and require `JUDGE_COMPLETE missing=0`.

Provenance: pueue task 9 ran `just judge --walk-id validity-20260828-r2` in `/workspace/2026/jspace/j-steer_pub`. Its full cleaned log reports `last 2143 of 2143 clean lines`. It used commit `4babef2`, whose provider was `deepinfra`; task 9 was killed after the fault was localized.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| Fresh input manifest | Four corrected sixth-octave walks only | `runs=185 demo_sides=37000` | yes | task 9 log | none | Manual rows remain absent. |
| Cache check | Score all missing fresh cells | `required=34400 cached=1020 missing=33380` | yes | task 9 log | 33,380 valid records | The task had the right target cohort. |
| Structured judge call | Schema-valid JSON from fp8 provider | 1,596 invalid-JSON retries and 529 exhausted cells, no progress record | no | full task 9 log | valid judgment JSON | Task 9 cannot support a behavioral result. |
| Provider reproduction | Same request finishes as valid JSON | DeepInfra returned `finish=error` and truncated text in all three attempts; Mancer 2 returned three valid JSON objects | yes for diagnosis | `just judge-cell-repro` output | full cohort run through Mancer | The fault is specific to DeepInfra structured output. |
| Completion contract | `JUDGE_COMPLETE missing=0` | absent | no | task 9 log ends before completion | all fresh judgments | Do not export or update the public results. |

## Primary evidence

### Task 9 full log

> `2026-08-28 12:26:36.412 | INFO | __main__:main:446 - CACHE_CHECK required=34400 cached=1020 missing=33380 API_calls=33380`
>
> `2026-08-28 12:26:42.112 | ERROR | __main__:judge_one:400 - skipping invalid JSON cell a3d24f... after 3 tries`
>
> `[pq] task 9: last 2143 of 2143 clean lines -- /home/code/.local/share/pueue/task_logs/9.log`

The complete log contains 1,596 `retry invalid JSON` lines and 529 exhausted-cell lines. It contains zero `judge progress=` lines. The process was killed at 12:35:14 after the repeated contract breach was established.

### DeepInfra reproduction

> `routed provider: DeepInfra`
>
> `--- attempt 0 temp=0.7 finish=error len=142 VALID=False`
>
> `'{"evidence":"A and B are identical: both say \\'cannot attribute EBITDA variance to font weight or color palettes\\' and name operational factors.'`

The `evidence` JSON string is unfinished and lacks all four score fields. The second and third attempts also ended with `finish=error` and incomplete strings. This is primary output from the exact request shape in `scripts/judge.py`.

### Mancer reproduction

> `routed provider: Mancer 2`
>
> `--- attempt 0 temp=0.7 finish=stop len=186 VALID=True`
>
> `'{"evidence":"A and B are identical, both saying \\'cannot attribute EBITDA variance to font weight or color palettes\\'.","on_axis_A":-4.2,"on_axis_B":-4.2,"off_axis_A":0.2,"off_axis_B":0.2}'`

This establishes that the prompt, schema, credential path, and model can produce a complete record when routed through Mancer. It does not establish a score for the full fresh cohort.

## Hypotheses

### H1 [harness | Almost Certain | 98%]

- Mechanism: DeepInfra returns provider-error partial text despite the requested JSON schema.
- Evidence: all three DeepInfra reproductions have `finish=error` and incomplete JSON; task 9 has 529 cells exhausted after identical parse failures.
- Contrary evidence: the test covers one cell and three samples, not every provider endpoint.
- Discriminating test: run the same cell through Mancer. A `finish=stop` valid object supports this hypothesis. This occurred.
- Fix/action: pin the judge to Mancer and lower concurrency from six to two. Raise after three failed requests instead of silently omitting a cell.
- Interpretability: no, task 9 scores are unusable.

### H2 [harness | Probable | 80%]

- Mechanism: six concurrent Mancer requests caused the task 7 `429`, not a permanent Mancer incompatibility.
- Evidence: task 7 recorded Mancer 2 `429` before fallback to Morph. The sequential reproduction later gave three valid Mancer records.
- Contrary evidence: two-request concurrency has not yet run the full cohort.
- Discriminating test: Mancer with `PARALLEL=2` records progress without a `429`; a `429` now stops the job with its exact cell and status.
- Fix/action: use `PARALLEL=2` and monitor the restarted job.
- Interpretability: partial, for route selection only.

### H3 [measurement | Unlikely | 10%]

- Mechanism: some generated answers cause a valid provider to fail the rubric.
- Evidence: task 9 was built from diverse generated answers and had repeated invalid output.
- Contrary evidence: the reproduced failure occurs before any score fields and Mancer scores the selected row.
- Discriminating test: inspect any Mancer failure raw text. Valid JSON refutes this as a broad cause.
- Fix/action: retain full failing raw output in the raised error; do not score or skip it.
- Interpretability: no effect unless a Mancer run exposes it.

## Decision

- Resolve-condition verdict: **not met**. The label requires `JUDGE_COMPLETE missing=0`; task 9 contains no completion record.
- Prediction check: the corrected manifest should contain only fresh artifacts. Supported. DeepInfra should return schema-valid records. Contradicted.
- Earliest unsupported link: provider-conformant structured output.
- Validity: task 9 is **invalid** as a judge run. `P(task-9 judged result is invalid)=1` because it has no valid progress and no completion record.
- Highest-information clues: DeepInfra `finish=error`; 529 exhausted cells; Mancer `finish=stop` valid JSON on the same request.
- Missing evidence: a Mancer full-cohort `JUDGE_COMPLETE missing=0`, then complete raw A/B records and exported artifacts.
- Recommended sequence: commit the Mancer route, two-request limit, and fail-fast completion contract. Requeue only the judge. Export only after the new log states `JUDGE_COMPLETE missing=0`.
