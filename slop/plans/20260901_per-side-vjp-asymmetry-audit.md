# Per-side VJP asymmetry audit

- [x] goal: establish why the public per-side VJP trace has one visible `+C` endpoint and no visible `-C` endpoint
  - inspect DEV selection, full candidate generation, full judging, acceptance, and global renderer
  - keep the current vector fixed; do not claim that `-C` is a method failure before checking omitted doses
  - failure modes: treating a hidden acceptance metric as the plotted damage; confusing an endpoint-confirmation run with a full dose trace
  - deliverable: `slop/audits/20260901_per-side-vjp-asymmetry.md` with raw rows, code paths, hypotheses, and one next test

- [x] goal: replace the endpoint-only public row with an all-100 measured curve for each per-side VJP direction
  - user correction: “why does the vald side only have one point? don't you see that's a bug”
  - use the v7 vector unchanged; judge the prespecified low-dose `-C` grid C=4,8,12,16,20,24,28.6019 on all 100 questions, AB and BA
  - failure modes: adding DEV rows to an all-100 public plot, or changing the vector while changing selection
  - deliverable: same public PNG and table, with coverage and rejected endpoints legible

## UAT / verification

| Scenario | What it looks like | How we catch it |
|---|---|---|
| success | audit names every full generated and judged coefficient, and the `steered_off_axis <= 1.5` acceptance gate | artifact manifest, scenario CSV, and code quotes agree |
| likely failure | the one visible point is mistaken for a full sweep | count full judged rows by side and compare with generated cells |
| sneaky failure | displayed damage differs from the acceptance metric | compare `off_axis_perturbation` with `steered_off_axis` for each selected cell |

- Evidence: [audit](../audits/20260901_per-side-vjp-asymmetry.md) records the selection-to-full gate crossing `1.4733 -> 1.6460`, the missing low-dose grid, and its all-100 follow-up. `data/results.csv` has 12 v7 rows; `slop/logs/20260901_goal3/v7-full-dose-curve-all-generated-judge.log` ends `JUDGE_COMPLETE required=2296 missing=0`; `slop/logs/20260901_goal3/results-render-v7-table-points.log` says `wrote 7 table rows from 800 measured evaluations`; `slop/reviews/2026-09-01_fresh-eyes-v7-full-dose-curve-final-table-points.md` says the purple table values occur at markers.

— PI/Codex
