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
5. Obtain the required result audit and review before any primary public rendering.

## Offline preflight result

`empirical-candor-full-preflight.log` reports that the full command accepts only the explicit selected-full flag, the frozen +C/candidness/.5/source parameters, no full random arm, FULL=100 with AB/BA, and the 900-second Modal function.

Current guards were checked explicitly:

- generic concept full remains blocked;
- component empirical-candor full requires `--selected-empirical-candor-full` and fails without it;
- the full route rejects a random arm;
- behavior direction for source `+C` with `candidness` is `-1` on the common sycophancy axis.

## Renderer finding: public update remains blocked

`src/vjp_steering/results.py::render_experiment` can render the full experiment's isolated formative artifacts from `data/formative/<experiment>/results.csv` to `results/formative/<experiment>/`.

It does not merge that result into `data/results.csv`, `results/index.md`, `results/index.html`, or `results/plot.png`. No existing primary-renderer promotion path was found. This is an explicit Goal 2 implementation item after full generation and review, not a reason to put DEV output on the primary plot.

## Budget and limits

`budget.json` validates after correction. It retains the full conditional reserve at $18.00. The all-100 run is still not authorized. Both research goals remain OPEN.
