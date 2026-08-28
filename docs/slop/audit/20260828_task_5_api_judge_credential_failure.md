# API judge task 5 credential failure

Prepared by PI on 2026-08-28.

Target: evaluate every arm in the four fresh `validity-20260828-r2` dose walks, then obtain `JUDGE_COMPLETE missing=0`.

Provenance: pueue task 5 ran in `/workspace/2026/jspace/j-steer_pub` after commit `2e49c16`. Full log read with `pqlog 5 100000`; its footer states `last 34 of 34 clean lines`.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| Certificate recovery | Four complete fresh walks | All four certificates are `COMPLETE` and declare `grid: 2^(n/6), n=-30..84` | yes | `outputs/walk_J_word_s0.json`; `outputs/walk_vjp_mlp_up_shrink_s{0,1,2}.json` | none | The required walk artifacts exist locally. |
| Fresh-artifact check | All judged artifacts carry the new identifier | Judge manifest accepted 185 runs | yes | `scripts/judge.py --walk-id validity-20260828-r2`: `manifest runs=185 demo_sides=37000` | Certificate-level `walk_id` field, currently checked per artifact | Manual artifacts are excluded from this task. |
| Judge cache | Identify required content cells | `required=34400 cached=1020 missing=33380` | yes | task 5 log | judge scores for 33,380 cells | No behavioral score exists for the corrected artifacts. |
| API execution | Start OpenRouter requests through `just` | Crashed before the first request | no | Task 5 used `uv run python scripts/judge.py`, bypassing `justfile`'s `set dotenv-load` | provider call and raw A/B judgments | Requeue the exact manifest through `just judge`; export and public results wait for it. |

## Primary evidence

### Task 5 full log — local pueue artifact

> `2026-08-28 11:48:22.790 | INFO     | __main__:main:444 - CACHE_CHECK required=34400 cached=1020 missing=33380 API_calls=33380`
>
> `api_key = os.environ["OPENROUTER_API_KEY"]`
>
> `KeyError: 'OPENROUTER_API_KEY'`
>
> `[pq] task 5: last 34 of 34 clean lines -- /home/code/.local/share/pueue/task_logs/5.log`

epistemic context: primary stdout/stderr of the exact queued process; it records program state before any API request.

This establishes that the missing variable stopped the process before evaluation. The failed command was `uv run python scripts/judge.py --walk-id validity-20260828-r2 --refresh`; it bypassed `justfile` line 1, `set dotenv-load`, which is the established project credential loader. It does not establish an API, model, or judge-format fault.

### Corrected walk artifact — local result file

> `"status": "RESULT",`
>
> `"walk_id": "validity-20260828-r2",`
>
> `"method": "J_word",`
>
> `"fixed_coefficient_magnitude": 0.03125,`
>
> `"demo_set": "sycophancy_all100",`
>
> `"eval_version": 10,`

epistemic context: first rung artifact downloaded from the Modal volume, not an aggregate or a prior journal claim.

This establishes the provenance condition checked for every manifest artifact. It does not establish target-directed behavior.

## Hypotheses

### H1 [harness | Almost Certain | 95%]

- Mechanism: task 5 bypassed the project `just` recipe, so `set dotenv-load` never loaded the existing ignored `.env` credential.
- Evidence: `KeyError: 'OPENROUTER_API_KEY'` occurs before `asyncio.run(refresh(todo))`, while task 5's recorded command begins `uv run python scripts/judge.py` rather than `just judge`.
- Contrary evidence: task 5 did not test the `just` recipe, so this remains a command-path diagnosis until the rerun reaches API progress.
- Discriminating test: queue `just judge --walk-id validity-20260828-r2`; a healthy run emits judge progress after `CACHE_CHECK` without exposing a credential.
- Fix/action: requeue the same manifest through `just judge`, not direct `uv run`.
- Interpretability: no, for behavioral scores; yes, for the manifest count and missing-cell count.

### H2 [data | Highly Unlikely | 5%]

- Mechanism: the 185 fresh artifacts have a provenance or parsing error that would fail after credentials are present.
- Evidence: `manifest runs=185 demo_sides=37000` completed before the credential lookup, and every selected artifact asserted the exact `walk_id`.
- Contrary evidence: raw judge outputs do not yet exist.
- Discriminating test: resume task 5 with credentials and inspect the first complete A/B judgment record.
- Fix/action: none before a failure localizes one artifact.
- Interpretability: partial, limited to input-manifest construction.

### H3 [harness | Remote | 2%]

- Mechanism: an OpenRouter provider failure is being misreported as an absent environment variable.
- Evidence: the exception is Python's direct `os.environ[...]` `KeyError`, before `AsyncOpenAI` construction.
- Contrary evidence: no provider request occurred.
- Discriminating test: presence of the variable changes execution to client construction; provider failures then expose an HTTP or network error instead.
- Fix/action: do not change provider logic until the credential precondition is met.
- Interpretability: no provider conclusion is possible.

## Decision

- Resolve condition: **not met**. The task label requires `JUDGE_COMPLETE missing=0`; the full log ends at `KeyError` with `missing=33380`.
- Prediction check: the expected manifest was fresh-only and nonempty. Supported by `185` artifacts and `37,000` demo sides. The expected successful judge completion is contradicted by the credential failure.
- Earliest unsupported link: OpenRouter authentication. The first API request is absent.
- Validity: the corrected walks are valid inputs for the intended evaluation, but the requested judged result is **inconclusive**. `P(judged-result-is-invalid)=1` because no judged result exists.
- Highest-information clues: the exact `KeyError`; the full-log count `34 of 34`; and the fresh-only manifest count `185`.
- Missing evidence, in order: approved scoped credential at the API worker; `JUDGE_COMPLETE missing=0`; complete raw A/B judgment records; exported CSV and rendered result artifacts.
- Recommended sequence: requeue through `just judge --walk-id validity-20260828-r2`, wait for `JUDGE_COMPLETE missing=0`, then export with `--walk-id validity-20260828-r2`, inspect raw A/B records, and update public artifacts. Do not use or restore manual rows.

## Correction

The previous claim that the credential needed delivery to the pueue daemon was wrong. The project already supplies it through the ignored `.env` when `just` runs a recipe. The shell checks established only that direct `uv run` cannot see the key; they did not test the required `just` command path.
