# V14 DEV queue handoff

## Current decision

`default` resumed at parallelism 1 on 2026-09-09T12:18:23+08:00. Task 815 from `/workspace/2026/LUCID3_wikit` remained running. The queue serializes all later tasks. No task was force-started.

## Queued work

| tasks | work | next action after success |
|---|---|---|
| 816 | fixed-token J-lens adaptation, paired DEV generation | pull artifact; validate exact shared bare and AB/BA cells; judge/export |
| 817 | mean_diff baseline, paired DEV generation | same |
| 818 | vjp_delta baseline, paired DEV generation | same |
| 819–823 | five seeded random baseline generations | same; all five are required before the random region renders |
| 824 | vendored paper verbal-report smoke, raw prefill, two categories and one target each | inspect α=0 equality and rank movement; do not call it benchmark success |

Exact commands and queued statuses for 816–823: `slop/logs/20260909_j_lens_dev/v14-reconcile-122445.log`.
Paper command/status: `slop/logs/20260909_j_lens_dev/v14-paper-reproduction-queue.json`.

## Monitoring

Process-managed `pqf` followers exist for 816–824. The first batch lost tracking after its temporary process directory disappeared; the restored processes use `/tmp/pi-processes-k5PuOO/`. Recheck `process list` and `ps` before assuming a follower survived.

## Budget

`slop/logs/20260909_j_lens_dev/v14-budget.json`: v14 allocation `$20.00`; `$1.00` reserved for paired AB/BA judging; carried `$12.00` review reserve is separate. No v14 scored result exists yet. Reconcile each Modal and judge cost before scheduling more work.

## Required provenance before rendering

`scripts/render_dev_comparison.py` refuses a row unless it has: the frozen ordered DEV15 IDs, canonical shared bare-response hash, matching model/dtype/length configuration, full AB/BA cache coverage, and matching cohort hash. Run `uv run python tests/test_render_dev_comparison.py` after edits. Then run the renderer only after all eight generation artifacts were pulled, judged, and exported.

## Next action

When any generation task completes: save its full Pueue log; pull/inspect the experiment manifest and per-scenario records; use `scripts/judge.py --experiment-id ID --profile dev --refresh`, then `scripts/export.py --experiment-id ID --profile dev --all-generated`; record spending. When 816–823 all pass, run `scripts/render_dev_comparison.py`, inspect both PNGs, and request fresh-eyes image review.

-- PI/OpenAI
