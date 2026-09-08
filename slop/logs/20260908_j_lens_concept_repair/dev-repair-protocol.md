# DEV repair protocol

PI/OpenAI Codex

## Measured bottleneck

The saved J-lens DEV evidence did not have a matched random behavioral direction. The old low-dose upper-layer result can therefore be a change caused by any same-size residual edit or by judge variation. This protocol fixes that control gap. It does not change the J-lens extraction, benchmark cohort, prompt order, decoder, or judge rubric.

## Fixed repair run

- New experiment: `j-lens-concept-dev-repair-v1`.
- Cohort: existing DEV-15 in its existing order.
- Base extraction: `j-lens-concept-dev-v1`, reused with its recorded vector hash `8841bc93cf13558a0b01c61d8fdeb737437ee82389754c786d4dd02f351e0f97`.
- Application layers: 18 through 24. The old upper-layer evidence used these layers.
- J-lens cells: `+C=.125` and `-C=.125`. This is the already measured low-dose range. The protocol does not repeat the completed lower-dose calibration.
- Fresh arms in one actual runner call: bare, both J-lens cells, and a seeded random direction for each sign.
- Random control: seed `20260908`; it has the same per-layer norm as the reused J-lens vector. The runner saves per-layer norm and cosine checks, vector hashes, raw responses, health, and realized prefill diagnostics.
- Judge: existing `scripts/judge.py` rubric, with both `AB` and `BA` order presentations for each J-lens and matched random arm. It uses no new metric or rubric.
- Order accounting: map each judgment through its order back to the steered arm. Treat AB and BA as two order views of one scenario-arm pair, not two samples. Save strict sign reversals separately from disagreements where one order is a tie. Do not choose the favorable order.

## Intended command

```sh
uv run modal run scripts/run_modal.py::j_lens_concept_repair_dev
```

This dedicated entrypoint fixes the complete runner contract above. It limits the one H100 container to 900 seconds and has no retry loop. The $2.00 Modal reserve includes 900 H100 seconds plus startup, CPU, memory, storage, and late-billing allowance.

After generation, run the unchanged judge for J-lens arms and each random control with `--orders AB,BA`. Then write one order audit with `scripts/scratch/j_lens_concept_dev_order_audit.py`. It saves each order's arm-mapped effect, the one-pair mean, strict reversals, and tie disagreements. A zero exit code is only pipeline evidence. Do not generate the all-100 endpoint or edit the public plot before a reviewer finds a task-responsive J-lens arm that beats its same-sign random control without response damage and has reviewed the order audit.
