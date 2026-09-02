# Shared final-token EB VJP DEV audit

Target: `mlp-up-shared-last-token-eb-formative-v1`. This is the controlled follow-up to the shared all-token VJP. It changes the target cotangent mask only: `c` is now applied at the final real prompt token, where `c` was defined. Pair matching, EB coordinate weighting, pooled activation scale, source-token averaging, and opposite-sign application remain unchanged.

## Run record

[`dev.log`](/workspace/2026/jspace/j-steer_pub/slop/logs/20260902_shared_last_token/dev.log) begins with the exact DEV command. The first local judging attempt lacked the API key because direct Python did not load `.env`; no API request was made. `scripts/judge.py` now uses `load_dotenv(ROOT / ".env")`, and the same generated cells resumed.

> `GPU_STAGE_COMPLETE experiment=mlp-up-shared-last-token-eb-formative-v1 profile=dev cells=32 reused=true`
>
> `CACHE_CHECK required=413 cached=23 missing=390 API_calls=390`
>
> `JUDGE_COMPLETE required=413 missing=0`
>
> `EXPERIMENT_RENDER_COMPLETE id=mlp-up-shared-last-token-eb-formative-v1 profile=dev rows=32`

Epistemic context: machine-generated Modal generation and local judge log. The first attempt is retained in the log; the quoted successful sequence is the resumed run on the same cells.

## Judged DEV result

[`results.csv`](/workspace/2026/jspace/j-steer_pub/data/dev/mlp-up-shared-last-token-eb-formative-v1/results.csv) records +C rows with `admissible=True`:

> `1.0,+C,-0.4266666666666668,0.060000000000000005,True`
>
> `2.0,+C,-0.10666666666666673,0.08666666666666666,True`
>
> `4.0,+C,-0.24666666666666676,0.24,True`
>
> `16.0,+C,-2.44,0.3933333333333333,True`

Every +C row with `admissible=True` has the wrong judge direction. The selected -C endpoint is:

> `32.0,-C,-0.9266666666666665,0.2333333333333333,True`

[`selected.json`](/workspace/2026/jspace/j-steer_pub/data/dev/mlp-up-shared-last-token-eb-formative-v1/selected.json) records `+C: no_accepted_endpoint` and -C C=32. Since DEV did not select both directions, the code does not run full all-100 judgment and does not change public output. [`fresh-eyes review`](/workspace/2026/jspace/j-steer_pub/slop/reviews/20260902_shared_last_token_dev_plot_rerender_fresh_eyes.md) confirms that the rerender matches the rows, distinguishes the two sides, and does not imply +C success.

## Interpretation

The final-token change removes the earlier target-mask mismatch, and the new vector passes the held-out final-token mediation sign check in [`20260902_shared_last_token_eb_mediation.json`](/workspace/2026/jspace/j-steer_pub/slop/audits/20260902_shared_last_token_eb_mediation.json). It still fails +C behavior at C=1.

This rejects the narrow hypothesis that the all-token target mask was the main cause of the shared vector's +C failure. It does not show that EB weighting is harmful: the shared pair mean and per-side EB methods remain different interventions, and there is no matched hard-shrink versus EB behavioral comparison.

The remaining likely explanation is that one shared linear direction does not implement the judged trait on both prompt regions. The next method change should not be another coordinate weighting rule unless it has a new target behavior or a direct counterexample to this conclusion.

— PI/Codex
