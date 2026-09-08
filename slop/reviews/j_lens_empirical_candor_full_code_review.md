# Selected empirical-candor full code review

- reviewer: `researcher`, Fireworks DeepSeek V4 Flash
- verdict before remediation: `REVISE`
- authoritative artifact: `/home/code/.pi/agent/sessions/--workspace-2026-jspace-j-steer_pub--/subagent-artifacts/outputs/0c55518e-396c-4a34-bd9d-ab8e70fa186f/slop/reviews/j_lens_empirical_candor_full_code_review.md`

## Finding fixed

The reviewer found that `--selected-empirical-candor-full` could bypass generic full-mode locks when supplied without `--component-empirical-candor`. The selected full route itself was frozen correctly, but a hand-written `j_lens_concept` or `j_lens_swap` command could use the flag to bypass DEV-only and DEV-accepted-candidate checks.

`scripts/experiment.py` now raises `ValueError("selected empirical candidness full requires the component-pair route")` before any full-mode guard can observe the flag. `j_lens_empirical_candor_full_preflight.py` now verifies that a non-component command with that flag fails.

## Additional fixed promotion checks

`promote_selected_full` now requires:

- promoted result `source_run` equals its experiment id;
- generated `profiles.full` has `FORMATIVE` status, `generated=true`, and cohort size 100;
- the temporary renderer preflight rejects duplicate promotion as well as a 99-row judgment file.

## Retained review limits

- The selected row is candidness, so its common sycophancy-axis effect is negative. The primary table needs its existing source-side/behavior-target provenance to make this readable.
- The full id must be unused for first generation. A rerun resumes its own artifacts by design.
- Full judging, raw-response audit, 85-row descriptive readout, and result review remain required before promotion.

## Verification after remediation

`empirical-candor-full-preflight-rerun.log` and `empirical-candor-full-renderer-preflight.log` pass after the fix. The latter uses temporary paths and asserts the public `data/results.csv` hash is unchanged.
