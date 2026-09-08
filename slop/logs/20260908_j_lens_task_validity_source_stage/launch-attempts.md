# Source-stage launch attempts

PI/OpenAI Codex, 2026-09-08. This file records both shown `pueue add` calls before any continuation.

| attempt | returned result | pueue task | Modal app | final status |
|---|---|---:|---|---|
| 1 | `error: the following required arguments were not provided: --immediate` from `pueue add --follow ...` | none | none | rejected before enqueue or launch |
| 2 | `New task added (id 704).` | 704 | `ap-FAW0E4RXpgmbCm1yMZPYnL` | task failed exit 1; app stopped, tasks 0 |

Evidence:

- `pueue-status-after-704.json` has exactly one task whose label contains `frozen v3 closed-rule source states`: ID 704, command `uv run modal run scripts/scratch/j_lens_task_validity_source_stage.py::launch`, status `Done.result.Failed: 1`, start `2026-09-08T10:20:23.323770792+08:00`, end `2026-09-08T10:21:05.812759296+08:00`.
- `modal-app-list-after-704.json` has exactly one `jsteer-task-validity-source-stage` app: `ap-FAW0E4RXpgmbCm1yMZPYnL`, state `stopped`, tasks `0`, created `2026-09-08 10:20:31+08:00`, stopped `2026-09-08 10:21:04+08:00`.
- No duplicate task or app exists, so no stop action was necessary.

The sole job has finished. Its complete cleaned and raw logs are `pueue-704-clean.log` and `pueue-704-raw.log`. The failure audit continues without a new launch.
