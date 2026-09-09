# Task 876 actual scope: calibrated 29-cell control, NOT the requested dose grid

## Requested vs actual (machine-checked 2026-09-09)

Requested (pueue 876 command line): DEV `j_lens_unit_direction` L16 with
`--coefficients-plus 0,0.25,0.5,1,2,4,8 --coefficients-minus 0,0.25,0.5,1,2,4,8`,
i.e. a 7-dose {0,.25,.5,1,2,4,8} diagnostic grid with a hooked C=0 in-pipeline control.

Actual (from `outputs/experiments/v14-dev-j-lens-unit-L16-corrected/manifest.json`):
- `grid["+C"]`: 14 doses `[1.0, 2.0, 4.0, 6.5255, 7.3536, 8.0, 8.1816, 9.0097, 9.8377, 9.8872, 10.6658, 11.4938, 12.3219, 13.1499]`
- `grid["-C"]`: 15 doses `[1.0, 2.0, 4.0, 8.0, 8.1355, 9.1679, 10.2002, 11.0713, 11.2326, 12.2649, 12.3266, 13.2973, 14.3296, 15.3620, 16.3943]`
- 29 calibrated cells + reused shared bare (`bare.jsonl`, coefficient 0.0 generation reuse, NOT a hooked C=0 steered cell).
- `data/dev/v14-dev-j-lens-unit-L16-corrected/results.csv`: 29 judged rows; `selected.json`: +C selected 9.0097 (1.277/0.743), -C selected 8.0 (-0.040/0.417).
- No cell at C=0, C=0.25, or C=0.5 was ever generated. Any "zero-intercept" claim about this run is withdrawn: there is no hooked zero-dose measurement, only the shared reused bare.

## Root cause

`scripts/experiment.py::gpu_stage`: for non-CONCEPT DEV methods the dose grid always comes from
`search_boundary`/`dev_grid` (manifest `boundaries`/`grid`); `args.coefficients_plus/minus` are only honored for the
full profile (`coefficients = manifest["grid"] if args.dev else {...}`) or for CONCEPT methods via `concept_grid`.
The 876 command line therefore supplied doses that DEV silently ignored, and the run expanded to the standard
29-cell calibrated control instead. This is a budget-expansion-shaped silent-ignore bug.

## Fix (this change)

- `reject_dev_supplied_grid()` in `scripts/experiment.py`: non-CONCEPT DEV with non-empty `--coefficients-plus/minus`
  now raises immediately with the full-profile-or-omit remedy. Called from both `parse_args` and `gpu_stage`.
- `self_test` regression: non-concept DEV + supplied doses must raise; empty/full/CONCEPT cases must not.
- Verified: `j_lens_concept --self-test` PASS; explicit `mean_diff --dev ... --coefficients-plus 0,1 ... --gpu-stage`
  raises `ValueError: DEV grid is calibrated ...`.

## Cost/runtime record

- Task 875: failed in 39s (packaging import, no result) — already recorded.
- Task 876: Success (29 cells + reused bare). Modal app id / wall duration not captured in this session
  (pueue daemon unavailable at audit time); spend held against the existing $1 `dev_repair_iteration2_unit_direction_L16`
  reserve, unreconciled — no new allocation, no repeat launched.
- Task 877 (judging): Success, `CACHE_CHECK required=718 cached=50 missing=668 API_calls=668`,
  `JUDGE_COMPLETE required=718 missing=0` (~15 min wall). Within the $2 paired-judging reserve; provider charge
  unknown, reserved conservatively.

## Interpretation (control, not repair)

Exported unit-control rows (`results/dev-comparison.csv`, method `j_lens_unit_L16`, 29 rows):
- -C2: effect -0.603 / damage 0.180 (accepted); +C7.3536: effect 1.480 / damage 0.283 (accepted).
- Table score +0.423 (above swap-L16 +0.130, below mean_diff +2.750; 17 not eligible).
- The purple curve is a fixed state-independent ActAdd control (`h + C·d̂`, `d̂ = normalize(v_target−v_source)`),
  distinctly labeled and NOT the paper coordinate swap. It measures what amplitude alone buys; it establishes
  no paper-method repair. Amplitude-state-dependence reading stays open; no further paid step on this evidence.

-- PI[Kimi K3]
