# Upper-layer C=.25 DEV repair protocol

PI/OpenAI Codex, 2026-09-08.

## Measured reason

At layers 18-24 and C=.125, J-lens `-C` corrected the fabricated TCA premise in `sw_pnf_02`, but eight of fifteen `-C` responses were byte-identical to bare and the apparent control advantage was concentrated in that one scenario. The existing all-layer C=.25 run was generation-clean, but it did not test the 18-24 layer band with same-sign random controls. Therefore this test changes one measured factor: coefficient `.125` to `.25` at the same saved vector, layers, cohort, decoder, and judge.

## Prediction and rejection readouts

| hypothesis | predicted `-C=.25` result | readout that weakens it |
|---|---|---|
| Upper-layer dose is too weak | more scenario-level candid corrections than random-minus, without added response damage | most rows remain identical or random has comparable changes |
| Vector is not broad behavior steering | the TCA-like correction remains isolated or output changes have no control advantage | broad control-beating changes across several scenarios |
| Higher dose damages generation | unfinished, repetition, task loss, or off-axis increase | raw audit remains task-responsive |

## Frozen run

- New experiment: `j-lens-concept-dev-repair-v2-upper-c025`.
- Saved vector: `j-lens-concept-dev-v1`, exact source hash `8841bc93cf13558a0b01c61d8fdeb737437ee82389754c786d4dd02f351e0f97`.
- Application layers: 18-24.
- Coefficient: `.25` for J-lens plus/minus and same-sign random controls.
- Cohort: existing DEV-15 and its existing order.
- Generation: bare, J-lens plus/minus, random-plus/minus in one 900-second H100 container, no retry.
- Judgment: unchanged rubric, AB and BA, arm-mapped order audit. AB/BA is one scenario-arm pair, not two samples.
- Selection: no full endpoint unless an independent audit finds a task-responsive J-lens arm clearly better than its same-sign random control under unchanged-rubric AB/BA accounting. The outlier is diagnostic evidence, not an automatic pass or failure rule. No DEV plot.

## Exact command

```sh
uv run modal run scripts/run_modal.py::j_lens_concept_repair_dev \
  --experiment-id j-lens-concept-dev-repair-v2-upper-c025 \
  --coefficient 0.25
```
