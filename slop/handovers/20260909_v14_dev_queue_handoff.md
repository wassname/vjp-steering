# V14 DEV queue handoff

## Current decision

`default` resumed at parallelism 1 on 2026-09-09T12:18:23+08:00. Task 815 from `/workspace/2026/LUCID3_wikit` remained running. It serializes only local work; the `modal run` commands for 816–823 dispatch H100 work through `run_experiment.remote` and do not allocate local CUDA. No task was force-started.

## Queued work

| tasks | work | next action after success |
|---|---|---|
| 816 → 825 | fixed-token J-lens adaptation, paired DEV generation | task 816 is stashed; task 825 is its one-at-a-time remote-dispatch replacement in existing `modal` group; pull artifact, validate exact shared bare and AB/BA cells, then judge/export |
| 817 → 827 | mean_diff baseline, paired DEV generation | task 817 is stashed; task 827 is its one-at-a-time remote-dispatch replacement after task825 completed in 329 seconds and passed provenance checks |
| 818 → 829 → 830 → 837 | vjp_delta baseline, paired DEV generation | task 818 is stashed; task829 failed before extraction because target layer33 is outside this 25-layer Qwen model. Task830 succeeded in 631 seconds with layers6-21 and target22. Task837 completed paired AB/BA judging with `required=560 missing=0`; its export is durable in `data/dev/v14-dev-vjp-delta-r2/`. |
| 819–823 → 831–835 → 836 → 839–842 | five seeded random baseline generations | originals remain stashed. Task831 ran for 42 seconds then failed before random-vector construction because `positive`/`negative` were initialized after the random branch. Tasks832-835 are `DependencyFailed`, with no remote dispatch. `tests/test_random_extraction.py` covers the repair. Explicit retry task836 succeeded in 445 seconds and passed exact DEV15/shared-bare provenance. Tasks839-842 are the seed1-4 serial replacement; task843 is the seed0 paired AB/BA judge. |
| 824 | vendored paper verbal-report smoke, raw prefill, two categories and one target each | failed in 27 seconds: Qwen’s raw clean tokens for `country` and `color` were not listed category answers, so no source/target pair existed. `slop/audits/20260909_v14_paper_verbal_task824.md` retains the log and defers a clean-only raw/chat category search until it cannot delay remote DEV comparison. |

Original commands/statuses for 816–823: `slop/logs/20260909_j_lens_dev/v14-reconcile-122445.log`. Migration snapshots and task-ID mappings: `slop/logs/20260909_j_lens_dev/v14-modal-migration-{before,stashed,map,817-map,818-map,random-migration-map}.json`. Task829 failure and its one corrected retry: `slop/logs/20260909_j_lens_dev/task829-full.log`, `task829-final-status.json`, and `task829-corrected-retry.json`.
Paper command/status: `slop/logs/20260909_j_lens_dev/v14-paper-reproduction-queue.json`.

## Monitoring

Process-managed `pqf` followers exist for 816–824. The first batch lost tracking after its temporary process directory disappeared; the restored processes use `/tmp/pi-processes-k5PuOO/`. Recheck `process list` and `ps` before assuming a follower survived.

## Budget

`slop/logs/20260909_j_lens_dev/v14-budget.json`: v14 allocation `$20.00`; `$9.00` conservatively reserves ten 900-second H100 attempts, including corrected VJP and random retries, and `$2.00` reserves paired AB/BA judging. The carried `$12.00` review reserve remains separate. Tasks825,827,830 completed in329,411,631 seconds; task829 failed in29 seconds and task831 failed in42 seconds before random-vector construction. Tasks832-835 did not dispatch remotely. The Modal CLI exposes no billing receipt, so reserves remain retained. J-lens task825 and mean_diff task827 have paired results.

## Required provenance before rendering

`scripts/render_dev_comparison.py` refuses a row unless it has: the frozen ordered DEV15 IDs, canonical shared bare-response hash, matching model/dtype/length configuration, full AB/BA cache coverage, and matching cohort hash. Run `uv run python tests/test_render_dev_comparison.py` after edits. Then run the renderer only after all eight generation artifacts were pulled, judged, and exported.

## Next action

For every successful random generation: save its full Pueue log; pull/inspect manifest and records; run paired AB/BA `scripts/judge.py`, then `scripts/export.py --all-generated`; record the retained cost reserve. When tasks825,827,830 and all five corrected random tasks pass, run `scripts/render_dev_comparison.py`, inspect both PNGs, and request fresh-eyes image review. Task824 is separately blocked behind local default task802 and older queued work; `task824-scheduler-status.log` records that scheduler dependency.

-- PI/OpenAI
