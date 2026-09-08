# Conditional all-100 contract: selected empirical-candor endpoint

This contract is prepared after Goal 1 selection. It does not authorize a paid launch, judging call, renderer update, or public result.

## Frozen generation contract

| field | value |
|---|---|
| experiment | `j-lens-components-empirical-candor-full-v1` |
| source experiment | `j-lens-behavior-components-target-ordered-source-v8` |
| source vector SHA256 | `dd4e78e9c429e51e4fe2d4e70e0db28c96d5c4c218b5f317767393ac38883197` |
| source side | `+C`, provenance only |
| behavior target | `candidness`, used by judge and export direction |
| operator | `mean100-gp16-reconstruction-target-ordered-coordinate-exchange-all-prefill-v8` |
| layers | 13-21 |
| alpha | `.5` |
| application mask | all attended prefill positions |
| arms | fresh bare and selected source only |
| cohort | unchanged all-100, in canonical order |
| model / decoding | Qwen3.5-4B, bfloat16, greedy, 512 new tokens |
| Modal | one H100 container, 900 seconds |
| retries | none in the entrypoint or pueue launch |
| queue | existing `modal` pueue group, one parallel slot |
| generation reserve | at most the existing $18 conditional-full reserve |

The full generation has no random arm. Goal 1 already used the fresh DEV bare/source/seeded-control comparison to select this endpoint. The full run answers the public all-100 question for the selected source endpoint.

## Intended one-shot command after approval

```sh
pueue add --immediate --group modal -w "$PWD" \
  -l "why: Goal 1 selected the frozen empirical-candor +C endpoint; resolve: obtain fresh all-100 source and bare records before unchanged AB/BA judgment" -- \
  uv run modal run scripts/run_modal.py::j_lens_component_empirical_candor_full
```

Attach exactly one `pqf <task-id> 100000` follower after the returned task ID is saved. Do not requeue it automatically. Save full pueue log, final task JSON, Modal app status, manifest, and provider billing snapshot.

## Required post-generation sequence

1. Independently audit all 100 bare/source pairs, source metadata, mask, and realized source patch diagnostics.
2. Run unchanged candidness AB/BA judging with the existing FULL profile: 100 rows, orders `AB,BA`, one pass, 200 required cells. Preserve complete cache records and API usage.
3. Export source rows with `scripts/export.py`; source `+C` remains provenance while `behavior_target=candidness` maps its common-axis sign.
4. Report all 100 rows as fresh generation with 15 selection-exposed rows. Report the remaining 85 rows as a descriptive generalization readout, not an independent held-out confirmation.
5. Obtain the required result audit and review before primary promotion. Then run `uv run python -m vjp_steering.results --promote-selected-full --experiment-id j-lens-components-empirical-candor-full-v1 --profile full`, followed by `uv run python -m vjp_steering.results` to render the primary table and plot.

## Offline preflight result

`empirical-candor-full-preflight.log` reports that the full command accepts only the explicit selected-full flag, the frozen +C/candidness/.5/source parameters, no full random arm, FULL=100 with AB/BA, and the 900-second Modal function.

Current guards were checked explicitly:

- generic concept full remains blocked;
- component empirical-candor full requires `--selected-empirical-candor-full` and fails without it;
- the full route rejects a random arm;
- behavior direction for source `+C` with `candidness` is `-1` on the common sycophancy axis.

## Renderer preflight: public update remains blocked until post-full review

`results.py` now has an explicit `--promote-selected-full` path. It refuses DEV data, non-all-100 cohort rows, incomplete judged scenarios, wrong source side/behavior target, missing accepted `+C=.5`, duplicate selected method rows, and schema drift. It appends only the reviewed selected full row to `data/results.csv`; the main renderer dynamically includes that method only after promotion.

`empirical-candor-full-renderer-preflight.log` exercises promotion into a temporary primary CSV, verifies source `+C` plus `candidness` maps to common-axis direction `-1`, requires 100 scenario rows, rejects a 99-row source, constructs the primary plot in memory, and asserts the real `data/results.csv` bytes remain unchanged.

Do not invoke promotion or the main renderer until the full run, full judging, audit, and review are complete.

## Budget and limits

`budget.json` validates after correction. It retains the full conditional reserve at $18.00. The all-100 run is still not authorized. Both research goals remain OPEN.
