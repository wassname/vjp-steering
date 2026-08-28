# Comparison validity audit

- [ ] Determine whether every displayed method used the same sixth-octave dose sampling near its coherence boundary.
  - Trace each displayed row to source runs, coefficients, and seed rule.
  - failure modes: equal cohorts hide unequal dose resolution or seed support.
  - deliverable: a source-run and coefficient table in the audit.
- [ ] Read complete final-dose outputs from each method and side.
  - Use the same benchmark scenarios and show bare versus steered text.
  - failure modes: a health gate accepts a different visible failure mode.
  - deliverable: linked raw-output excerpt with source paths.
- [ ] Obtain an independent code-and-artifact review and decide each finding.
  - failure modes: the audit copies the pipeline's own wrong assumptions.
  - deliverable: external review and a claim-by-claim triage.
- [ ] Remove or correct unsupported published claims.
  - Do not replace results with a different sampling rule without generated and judged runs.
  - failure modes: a polished table remains despite an invalid comparison.
  - deliverable: corrected public result artifact, or an explicit invalidation notice.

## UAT / Verification

| Scenario | What it looks like | Evidence |
| --- | --- | --- |
| Success | All rows share the sampling and endpoint rule, and raw outputs support the gate. | Audit source table, complete raw excerpts, and reviewer triage. |
| Likely failure | New rows have a coarser or manually selected dose set. | Audit lists unequal coefficients and public table is withdrawn or marked. |
| Sneaky failure | The last visible output is incoherent although the health gate is clear. | Complete bare/+C/-C samples at each endpoint expose it. |

## Log

- 2026-08-28: Initial code read finds `scripts/run_modal.py` defaults `refine_around_cstar=False`; new MLP-up and J-word publication rows came from `descending`, not `walk`.
- 2026-08-28: Audit found unequal sampling. Started Modal app `ap-c8wV0flWrodaoxL0nChKOu` for a sixth-octave `walk` rerun of J-word seed 0 and MLP-up seeds 0, 1, and 2. [Launch evidence](../audit/20260828_modal_validity_rerun.log).
