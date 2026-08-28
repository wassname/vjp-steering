# Corrected walk completion

- [x] goal: Recover four fresh dose-walk certificates, each with the sixth-octave grid and `validity-20260828-r2` artifacts.
  - UAT: [the four certificate headers](../../../outputs/) state `COMPLETE` and `grid: 2^(n/6), n=-30..84`; their rung artifacts assert the exact walk ID.
- [ ] goal: Judge every arm in the four fresh walks without reading manual artifacts.
  - UAT: [the pueue task log](../audit/20260828_task_5_api_judge_credential_failure.md) ends `JUDGE_COMPLETE required=34400 missing=0` for `--walk-id validity-20260828-r2`.
  - Current blocker: pueue task 5 has no `OPENROUTER_API_KEY`; the audit documents the exact pre-request failure.
- [ ] goal: Export only fresh J-word and MLP-up rows, inspect complete raw A/B outputs, and update the public table and plot.
  - UAT: `data/results.csv`, `data/judged_scenarios.csv`, and `results/` contain only fresh source runs for these two methods; the audit links complete A/B raw records and the renderer succeeds.

## Log

- 2026-08-28 PI: The fresh walk certificates are complete. The first API judge did not send a request because its worker lacked the scoped OpenRouter credential. Manual rows remain excluded.
