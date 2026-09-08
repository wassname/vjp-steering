# J-lens repair runner preflight

PI/OpenAI Codex

This preflight checks the actual Modal volume input and the local Modal entrypoint. It does not start a GPU container, generate an answer, or call the judge.

## Reused extraction input

Command run on 2026-09-08:

```sh
uv run modal volume ls jsteer-pub-cache outputs/experiments/j-lens-concept-dev-v1
```

Observed output:

```text
outputs/experiments/j-lens-concept-dev-v1/extraction
outputs/experiments/j-lens-concept-dev-v1/cells
outputs/experiments/j-lens-concept-dev-v1/manifest.json
outputs/experiments/j-lens-concept-dev-v1/bare.jsonl
```

The real generation container exposes this volume as `/cache`. The runner makes `/repo/outputs` a link to `/cache/outputs`, so `--reuse-extraction-from j-lens-concept-dev-v1` resolves the listed extraction in the actual generation environment.

## New control arguments

Command run on 2026-09-08:

```sh
uv run modal run scripts/run_modal.py::experiment --help
```

Observed options include:

```text
--random-control-coefficient FLOAT
--random-control-seed INTEGER
--reuse-extraction-from TEXT
--concept-layers TEXT
```

The real runner accepts the matched random-control arguments before any paid launch.

## New output identity

The local path `outputs/experiments/j-lens-concept-dev-repair-v1` was absent. Modal reported `No such file or directory` for `outputs/experiments/j-lens-concept-dev-repair-v1` in the cache volume. The first run will not overwrite an old repair artifact.

## Local unit checks

See [runner-preflight.log](runner-preflight.log). The test passed the seeded norm-match check and the existing concept hook checks. This is code-path evidence only. It does not show a Qwen response or useful steering.
