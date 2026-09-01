# Blind review, with parent-audit correction

The reviewer inspected the per-experiment formative plot. Its use of “public static plot” means `results/formative/mlp-up-left-right-formative-v7-eb-audited/plot.png`, not the global `results/plot.png`. The parent audit corrects that distinction.

## Review

- **Correct — full did evaluate a health-clean, directionally correct `-C` cell.**  
  `outputs/experiments/mlp-up-left-right-formative-v7-eb-audited/manifest.json:859-872` records `-C`, `C=28.60187715130719`, `rows: 100`, zero unfinished/role leaks/repetitions, and `"breakdown_reasons": []`. The exported full row is:
  > `...,28.60187715130719,-C,-0.6415000000000001,1.0225,False`  
  (`data/formative/mlp-up-left-right-formative-v7-eb-audited/results.csv:3`)

  Thus the cell is health-clean and has the required negative on-axis sign, but it is **not accepted**. `scripts/export.py:292-310` sets:
  > `"admissible": health_clean and steered_off_axis <= 1.5`

  Since health is clean but `admissible=False`, its mean `steered_off_axis` necessarily exceeded `1.5`. This is separate from the plotted `off_axis_perturbation=1.0225`.

- **Correct — no selection-sign bug found.** `scripts/export.py:342-359` uses `direction = -1` for `-C` and accepts only `direction * effect > 0`; the full `-C` effect is `-0.6415`, so it passes the sign test. Rejection is from admissibility, not a reversed sign or dropped row.

- **Correct, for the per-experiment plot — the formative plot contains the rejected `-C` point as a small purple open circle at `(-0.6415, 1.0225)`.** The generated Plotly payload in `results/formative/.../index.html:1` explicitly contains:
  > `"text":["bare","C=28.6019 (rejected)"]`  
  > `"x":[0,-0.6415000000000001],"y":[0,1.0225]`  
  > `"symbol":["circle","circle-open"]`

  `src/vjp_steering/results.py:95-107` retains rejected rows when `include_rejected=True`; `render_experiment()` supplies that flag at `:597-602`. The renderer withholds the large endpoint × and callout because full `selected.json` has no `selected_C` for `-C`; `results.py:570-572` turns that into `None`, and `:266-273` only records a displayed endpoint when one exists. This is consistent with:
  > `"status": "no_accepted_endpoint"`  
  (`data/formative/.../selected.json:13-17`).

- **Why exactly one public `+C` point exists — intended endpoint-confirmation flow, not decimation.**
  1. Dev produced five viable `+C` candidates, descending from `44.06369064172843` through `29.228176707076145` (`data/dev/.../selected.json`).
  2. Full generation created all six candidate cells (five `+C`, one `-C`): `slop/logs/20260901_goal3/just-experiment-v7-literal-command.log:54-55` says `profile=full cells=6`.
  3. `scripts/experiment.py:602-636` judges/exports candidates one at a time and stops on the first accepted candidate:
     > `if side in confirmed["sides"]:`  
     > `    ...`  
     > `    break`
  4. The first/highest `+C` candidate was accepted. Full `selected.json:5-11` therefore retains only `C=44.06369064172843`; full `results.csv` has only its accepted `+C` row. The four lower generated `+C` cells were intentionally not judged/exported after that success.

- **Ranked causes**
  1. **Primary:** `-C` failed the distinct `steered_off_axis <= 1.5` acceptance gate despite clean generation and correct direction.
  2. **Secondary:** Dev offered only one `-C` accepted candidate, so full had no fallback candidate after its rejection; the log records `FULL_SIDE_UNCONFIRMED ... [28.60187715130719]`.
  3. **Presentation:** The rejected `-C` mark is open and unlabeled in the formative PNG, so it can be perceived as absent.

- **Finding: P2 — rejection reason is not exposed beside the plotted point.** `scripts/export.py:292-310` gates on `steered_off_axis`, but public `results.csv`/plot shows only `off_axis_perturbation`; the rejected `-C` point has displayed damage `1.0225`, below the visually suggestive `1.5` threshold, while the hidden gate failed. Smallest fix: include `steered_off_axis` and/or the failed acceptance condition in the point hover text or rendered note.

- **Residual risk:** The full cell reuses the 15-row DEV prefix before appending FORMATIVE rows (`scripts/experiment.py:257-266`; cell records at lines 14-15 are `profile: "dev"` and line 16 onward is `profile: "full"`). This is compatible with deterministic prefix-resume generation, but the full artifact is not provenance-homogeneous by its per-row profile labels.

— reviewer subagent
