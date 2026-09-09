# V14 DEV queue handoff

## Current decision

`default` resumed at parallelism 1 on 2026-09-09T12:18:23+08:00. Task 815 from `/workspace/2026/LUCID3_wikit` remained running. It serializes only local work; the `modal run` commands for 816–823 dispatch H100 work through `run_experiment.remote` and do not allocate local CUDA. No task was force-started.

## Queued work

| tasks | work | next action after success |
|---|---|---|
| 816 → 825 | fixed-token J-lens adaptation, paired DEV generation | task 816 is stashed; task 825 is its one-at-a-time remote-dispatch replacement in existing `modal` group; pull artifact, validate exact shared bare and AB/BA cells, then judge/export |
| 817 → 827 | mean_diff baseline, paired DEV generation | task 817 is stashed; task 827 is its one-at-a-time remote-dispatch replacement after task825 completed in 329 seconds and passed provenance checks |
| 818 | vjp_delta baseline, paired DEV generation | stashed until task 825 runtime/output/cost is inspected |
| 819–823 | five seeded random baseline generations | stashed until task 825 runtime/output/cost is inspected; all five are required before the random region renders |
| 824 | vendored paper verbal-report smoke, raw prefill, two categories and one target each | remains queued on local `default`; inspect α=0 equality and rank movement; do not call it benchmark success |

Original commands/statuses for 816–823: `slop/logs/20260909_j_lens_dev/v14-reconcile-122445.log`. Migration snapshots and task-ID mappings: `slop/logs/20260909_j_lens_dev/v14-modal-migration-{before,stashed,map,817-map}.json`.
Paper command/status: `slop/logs/20260909_j_lens_dev/v14-paper-reproduction-queue.json`.

## Monitoring

Process-managed `pqf` followers exist for 816–824. The first batch lost tracking after its temporary process directory disappeared; the restored processes use `/tmp/pi-processes-k5PuOO/`. Recheck `process list` and `ps` before assuming a follower survived.

## Budget

`slop/logs/20260909_j_lens_dev/v14-budget.json`: v14 allocation `$20.00`; `$8.00` conservatively reserved for at-most-eight 900-second serial H100 generations and `$1.00` for paired AB/BA judging; carried `$12.00` review reserve is separate. No v14 scored result exists yet. Reconcile task 825's Modal cost before moving any later remote task.

## Required provenance before rendering

`scripts/render_dev_comparison.py` refuses a row unless it has: the frozen ordered DEV15 IDs, canonical shared bare-response hash, matching model/dtype/length configuration, full AB/BA cache coverage, and matching cohort hash. Run `uv run python tests/test_render_dev_comparison.py` after edits. Then run the renderer only after all eight generation artifacts were pulled, judged, and exported.

## Next action

When any generation task completes: save its full Pueue log; pull/inspect the experiment manifest and per-scenario records; use `scripts/judge.py --experiment-id ID --profile dev --refresh`, then `scripts/export.py --experiment-id ID --profile dev --all-generated`; record spending. When 816–823 all pass, run `scripts/render_dev_comparison.py`, inspect both PNGs, and request fresh-eyes image review.

-- PI/OpenAI
