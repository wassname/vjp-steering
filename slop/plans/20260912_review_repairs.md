# Action the repository review

User: "ok lets wrap up and action those if you agree"
Constraints: CPU-only repairs and saved-data rendering. No new generation, judging, GPU queues, or paid calls. Preserve raw historical results and current human README edits (origin/dev3 532ca36). Commit locally; no force pushes.
Parent session: 01a09444-e901-76a7-9b48-72700f33ec6b.

1. [ ] goal: Extraction honors requested inputs and rejects invalid vectors
  - Scope: scripts/experiment.py, src/vjp_steering/vjp.py, steering tests, production readout test.
  - Tasks: validate cache identity before reuse; forward/reject CLI inputs; reject zero/nonfinite directions; specify VJP orientation and source-format limitations without silently redefining the method.
  - Failure mode: configuration-only test passes but cached or completed-cell path bypasses validation.
  - Evidence: production-path CPU regressions with changed identity, nonsymmetric J, zero norm, label reversal and actual normalized readout helper.
2. [ ] goal: Saved-data plots and tables regenerate with coherent endpoints and valid random geometry
  - Scope: src/vjp_steering/results.py, scripts/render_dev_comparison.py, result tests, generated results files (README generated table only).
  - Tasks: repair canonical seed map/export counting; coherent-only curve anchors ending at selected endpoints; sort random geometry by actual calibration fraction; unclipped labels; smooth endpoint-anchored full plot stays in README.
  - Failure mode: a pretty PNG still includes rejected points in its line or mixes DEV with full.
  - Evidence: plotted-array assertions, successful CPU render, parent PNG inspection and fresh image review.
3. [ ] goal: Judge/export enforce explicit contracts and bounded retries
  - Scope: scripts/judge.py, scripts/export.py and tests only.
  - Tasks: bound transient retries; pass records to diagnostics; fail on missing required judgments; fix contradictory target wording under a new rubric identity without rerating historical data.
  - Failure mode: helper test passes while production caller still fails or old cache is relabeled as new judgments.
  - Evidence: mocked request exhaustion, caller-level export checks, target wording and cache-version tests; no real requests.
4. [ ] goal: Correct statistical reporting and close with verified evidence
  - Parent owns bootstrap script/tests, journal/audit corrections, integration and commits.
  - Tasks: report observed damage directly; use stated paired-scenario uncertainty; withdraw stale causal/null/power claims; inspect all diffs and test outputs.
  - Failure mode: new documentation repeats stale evidence or calls a historical result invalid without reconstruction.
  - Evidence: final repair report, saved CPU logs, clean tracked source diff, remaining limitations listed explicitly.

## Verification
Success: current production tests fail on the reviewed defects and pass after fixes; saved raw CSVs/generations remain unchanged.
Likely failure: tests patch out the buggy caller; inspect which production functions execute.
Subtle failure: old cached vectors/judgments satisfy the new contract only by missing-field defaults; require explicit identities or fail with actionable diagnostics.
No new scientific success claim or paid experiment is part of completion.

-- PI/OpenAI
