# Action the repository review

User: "ok lets wrap up and action those if you agree"
Constraints: CPU-only repairs and saved-data rendering. No new generation, judging, GPU queues, or paid calls. Preserve raw historical results and current human README edits (origin/dev3 532ca36). Commit locally; no force pushes.
Parent session: 01a09444-e901-76a7-9b48-72700f33ec6b.
Future helper launches: `fireworks/accounts/fireworks/models/glm-5p3-flash`, thinking `high`, as requested by the user. -- PI/OpenAI

1. [/] goal: Extraction honors requested inputs and rejects invalid vectors
  - Scope: scripts/experiment.py, src/vjp_steering/vjp.py, steering tests, production readout test.
  - Tasks: validate cache identity before reuse; forward/reject CLI inputs; reject zero/nonfinite directions; specify VJP orientation and source-format limitations without silently redefining the method.
  - Failure mode: configuration-only test passes but cached or completed-cell path bypasses validation.
  - Evidence: production-path CPU regressions with changed identity, nonsymmetric J, zero norm, label reversal and actual normalized readout helper.
    - [x] Strict versioned extraction_request identity checked on all reuse paths incl. completed-profile shortcut; one-field-at-a-time rejection tested. -- PI/OpenAI
    - [x] lens-file/target-layer forwarded and unsupported flags fail; zero/nonfinite/ambiguous directions rejected before saving. -- PI/OpenAI
    - [x] VJP global orientation via installed orient_vjp_delta, label reversal on production vjp_delta; thinking=False + seed persona source verified on cached tokenizer; J_word single-token enforced; production readout test calls clean_layer_lens_readouts. -- PI/OpenAI
    - Evidence: slop/reviews/20260912_steering_repairs.md + _verification.log (23/23 OK, CPU offline). Handover sent to parent; parent owns approval/commit.
2. [ ] goal: Saved-data plots and tables regenerate with coherent endpoints and valid random geometry
  - Scope: src/vjp_steering/results.py, scripts/render_dev_comparison.py, result tests, generated results files (README generated table only).
  - Tasks: repair canonical seed map/export counting; coherent-only curve anchors ending at selected endpoints; sort random geometry by actual calibration fraction; unclipped labels; smooth endpoint-anchored full plot stays in README.
    - [x] Implement shared random eligibility, dose-mean N, accepted-only endpoint controls and fraction ordering. -- PI/OpenAI
    - [x] Pin frozen DEV to v7 and compare CSV scores/coherence with saved judgments and manifest health. -- PI/OpenAI
    - [x] Verify plotted source arrays and raw-input invariance; inspect full/DEV PNGs.
    - [ ] Parent/fresh reviewer inspect final PNGs.
    - Evidence: slop/reviews/20260912_plot_repairs_checks.log (no rejected anchors, exact endpoint equalities, fraction-sorted regions, input invariance), 20260912_plot_repairs_render.log (7/7 tests, rung regression, both renders), 20260912_plot_repairs_report.md, repaired results/plot_pareto.png + plot-pareto-dev.png inspected; data/results.csv sha unchanged.
  - Failure mode: a pretty PNG still includes rejected points in its line or mixes DEV with full.
  - Evidence: plotted-array assertions, successful CPU render, parent PNG inspection and fresh image review.
3. [ ] goal: Judge/export enforce explicit contracts and bounded retries
  - Scope: scripts/judge.py, scripts/export.py and tests only.
  - Tasks: bound transient retries; pass records to diagnostics; fail on missing required judgments; fix contradictory target wording under a new rubric identity without rerating historical data.
    - [x] Implement separate transient counter, complete cache requirement and records diagnostics caller.
    - [x] Coordinate explicit v7/v8 selection with parent/plot worker; preserve v7 prompt and prevent mixed-version exports.
    - [x] Verify production callers with mocked client and temporary on-disk cache/artifacts.
  - Failure mode: helper test passes while production caller still fails or old cache is relabeled as new judgments.
  - Evidence: mocked request exhaustion, caller-level export checks, target wording and cache-version tests; no real requests.
  - Log (PI/gpt-6-astra, 2026-09-12): captured original four v7 prompt hashes in `slop/reviews/20260912_judge_repairs_original_hashes.log`; dedicated caller regressions running to `slop/reviews/20260912_judge_repairs_tests.log`. Parent owns approval.
  - Evidence (PI/gpt-6-astra, 2026-09-12): final suite `Ran 14 tests ... OK` in `slop/reviews/20260912_judge_repairs_tests.log`; report `slop/reviews/20260912_judge_repairs_report.md`. Initial 6-failure run (`_tests_initial.log`) was a worker-introduced variable shadowing bug, fixed and re-run. Awaiting parent review/approval.
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
