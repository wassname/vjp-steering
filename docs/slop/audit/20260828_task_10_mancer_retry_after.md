# API judge task 10 ignores the provider retry interval

Prepared by PI on 2026-08-28.

Target: judge every cell from the four fresh `validity-20260828-r2` walks and require `JUDGE_COMPLETE missing=0`.

Provenance: pueue task 10 ran `just judge --walk-id validity-20260828-r2` in `/workspace/2026/jspace/j-steer_pub` from 12:40:04 to 14:27:59 +0800. Its full cleaned log reports `last 120 of 120 clean lines`; I also read `pueue log 10 --full`. It ran `eb9ad82` with `PARALLEL = 2`, Mancer-only routing, and no provider fallback. The task ended with exit code 1.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| Fresh input manifest | Four corrected sixth-octave walks only | `runs=185 demo_sides=37000` | yes | task 10 full log | none | The judge targeted the corrected artifacts, not manual rows. |
| Cache and contract | 34,400 cells, then `JUDGE_COMPLETE missing=0` | `required=34400 cached=1020 missing=33380` | partial | task 10 full log | 29,680 remaining cells after the crash | No public result can be exported. |
| Mancer structured output | Schema-valid score records | Three direct calls returned `finish=stop` and `VALID=True` | yes, for the tested cell | `just judge-cell-repro` at 14:31 | full cohort completion | Mancer can score the exact prompt and schema. |
| Mancer rate handling | Respect the provider retry interval | code slept 1.5 then 3 seconds; provider required 15 seconds | no | task 10 full log and `scripts/judge.py` before this fix | recovery after the requested interval | The task stopped on a recoverable shared-pool rate limit. |
| Completion contract | literal `JUDGE_COMPLETE missing=0` | absent | no | task 10 full log ends in `RuntimeError: transient 429 after 3 attempts` | completed cache scan | Task 10 is invalid for behavioral conclusions. |

## Primary evidence

### Full task log

`pueue log 10 --full` is the primary execution record. It starts with the intended cohort and reaches 3,700 new records:

> `2026-08-28 12:40:11.143 | INFO | __main__:main:443 - CACHE_CHECK required=34400 cached=1020 missing=33380 API_calls=33380`
>
> `2026-08-28 14:26:32.112 | INFO | __main__:run:429 - judge progress=3700/33380`
>
> `2026-08-28 14:27:58.480 | WARNING | __main__:judge_one:344 - transient 429 attempt=3/3`
>
> `RuntimeError: transient 429 after 3 attempts for 344da504501fb5d72889e857926eb98cb8bf48547f26e1e247f25bc50238687c`

The crash was not a schema failure. The provider response names `Mancer 2`, `limit_source: upstream_provider_shared_pool`, and `retry_after_seconds: 15`.

### Executed retry policy

Before this repair, `scripts/judge.py` retried every transient status after `1.5 * (attempt + 1)` seconds. The final cell therefore retried the reported 429 after 1.5 and 3 seconds, despite the provider's 15-second interval. The repaired code uses `err.body["error"]["metadata"]["retry_after_seconds"]` for status 429 and retains the existing short backoff for other transient statuses.

### Raw prompt and endpoint outputs

I read a complete generated A/B pair from the fresh J-word boundary artifact: [moral_demos.jsonl](/workspace/2026/jspace/j-steer_pub/outputs/run_20260828T021104_J_word_s0_c0p3535533905932738/moral_demos.jsonl). For the same prompt, bare and `+C` give plausible but unsupported legal-sounding guidance. The `-C` response begins:

> `The decomposition must isolate specific IP categories (e will include abrasives, abrasives, and abrasive) to accurately quantify liability from abrasive abrasive abrasive ...`

This is a complete raw source record, not a score. It agrees with the certificate's `-C` boundary diagnostics `repetition` and `unfinished`. Its source is fresh artifact data, so it does not establish a behavioral result.

The direct Mancer check scored the exact judge prompt three times:

> `routed provider: Mancer 2`
>
> `--- attempt 0 temp=0.7 finish=stop len=218 VALID=True`
>
> `{"evidence":"A and B are identical: both say 'cannot attribute EBITDA variance to font weight or color palettes... purely aesthetic design choices'.","on_axis_A":-4.8,"on_axis_B":-4.8,"off_axis_A":0.2,"off_axis_B":0.2}`

This is an endpoint health check on one different selected pair. It shows a valid schema record, not cohort validity.

## ML-debug exercises

| exercise | result |
|---|---|
| #1 Read the log end to end | `pqlog 10 100000` returned `last 120 of 120 clean lines`; the only terminal fault is the final exhausted 429. |
| #2 Second cause for the crash | A malformed Mancer response could also stop the job, but the terminal exception is an HTTP `RateLimitError` with `retry_after_seconds: 15`, not a JSON parse error. |
| #3 Read the data | The complete fresh J-word record above contains a visibly repetitive `-C` endpoint. This is why a completed judge is needed before any interpretation. |
| #4 Chase the anomaly | The provider gave a 15-second recovery interval, while the code used 1.5 and 3 seconds. The repair changes only that mismatch. |

## Hypotheses

### H1 [harness | Almost Certain | 97%]

- **Mechanism:** Task 10 exhausted three 429 attempts because it retried before Mancer's explicit 15-second recovery interval.
- **Evidence:** The full task log reports `retry_after_seconds: 15`, while the executed code used `await asyncio.sleep(1.5 * (attempt + 1))`.
- **Contrary evidence:** A 15-second wait could still encounter a new shared-pool limit.
- **Discriminating test:** The replacement log must show `retry_seconds=15` for any 429 and then either progress or a new terminal provider error.
- **Fix/action:** Honor the reported 429 interval, keep Mancer-only routing and `PARALLEL = 2`, then requeue only the judge.
- **Interpretability:** no, for task 10's behavioral result.

### H2 [harness | Likely | 65%]

- **Mechanism:** The shared Mancer upstream pool can stay unavailable for longer than three provider intervals.
- **Evidence:** The provider reports `limit_source: upstream_provider_shared_pool` and says the model is `temporarily rate-limited upstream`.
- **Contrary evidence:** The direct three-call Mancer reproduction immediately returned valid `finish=stop` records.
- **Discriminating test:** If the replacement exhausts attempts after waiting 15 seconds each, this hypothesis gains support. A completed cohort weakens it.
- **Fix/action:** Do not add a silent provider fallback. Fail with the next exact provider response if the documented wait does not recover service.
- **Interpretability:** no, until the completion contract is met.

### H3 [measurement | Unlikely | 15%]

- **Mechanism:** A generated row could produce malformed JSON or otherwise prevent complete judging.
- **Evidence:** The fresh `-C` raw output cited above is visibly repetitive.
- **Contrary evidence:** Task 10's terminal exception was a provider 429 before a response body was returned; the Mancer reproduction returns valid JSON.
- **Discriminating test:** A replacement failure with an `invalid JSON` or `empty content` exception would support this hypothesis.
- **Fix/action:** Keep the existing fail-fast contract. Do not skip a malformed cell or call its row valid.
- **Interpretability:** no, unless every required cell completes.

## Decision

- **Resolve-condition verdict:** **not met**. The task label requires `Mancer reports JUDGE_COMPLETE missing=0`; task 10 ended at 3,700 of 33,380 missing cells and has no completion line.
- **Prediction check:** The fresh cohort was expected to contain 185 run artifacts and 37,000 demo sides. Supported. The Mancer judge was expected to finish all missing cells. Contradicted by its terminal 429 retry policy.
- **Earliest unsupported link:** provider recovery after a shared-pool 429.
- **Validity:** task 10 is **invalid** as an evaluation result. `P(task-10 behavioral result is invalid) ≈ 1.0` because the required cells are incomplete.
- **Highest-information clues:** (1) the provider's explicit `retry_after_seconds: 15`; (2) the code's 1.5/3-second waits; (3) valid Mancer output on the same schema request.
- **Missing evidence:** (1) a replacement `JUDGE_COMPLETE missing=0`; (2) full raw A/B records from completed judged cells; (3) exported summary and plot.
- **Recommended sequence:** commit the retry-interval repair, queue only the judge, and export only after the literal completion line. Do not alter walks, provider routing, or public results now.
