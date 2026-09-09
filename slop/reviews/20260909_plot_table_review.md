# Plot/table review — j_lens_swap_L16 (dev) — 20260909

**Verdict: NEEDS-FIX.** In `results/plot-dev.png` the green L16 **-C** X still sits on the wrong-direction point, not the selected one.

Pixel-calibrated against the gridlines (x: 149.5 px/unit about 0; y: 685 px/unit about 0, inverted):

- `plot-dev.png` shows a green X at data **(1.013, 0.223)** — the `j_lens_swap_L16,0,16.0,-C,1.0133...,0.2233...,True` row in `data/dev/v14-dev-j-lens-swap-L16/results.csv`. That is the **wrong-direction -C point (positive effect) at C=16**, exactly the bug called out in the task. No X marker is visible at the table's selected `-C on-axis 0.453 / -C damage 0.323` (C=11.9, admissible, correct sign) — only a plain green dot sits there.
- Green **+C** X in `plot-dev.png` is at **(1.787, 0.414)** — it marks the `C=12.3377, effect 1.7867, damage 0.4133` point, not the table's selected `C=12.276, damage 0.367` point. Same effect, but damage mismatches the table (0.413 vs 0.367); on the Pareto plot the X centroid resolves to (1.793, 0.414), again the .413 point. The claimed "same effect, lower damage" selection exists in the CSV but is not what the X marks.
- Table↔plot endpoints disagree as a consequence: `results/index-dev.md` says `-C 0.453/0.323` and `+C 1.787/0.367`; `plot-dev.png` marks `1.013/0.223` (-C) and `1.787/0.413` (+C).
- Pareto plot has the same defects (-C X at ≈(1.01, 0.23); +C X at the .413 point), so the smoothing did not fix the selection.
- Green (J-lens L16) and blue (J-lens coordinate swap, X at ≈(-0.12, 0.15) / ≈(-0.26, 0.16)) are visually distinct, so the series identity is fine — the issue is the -C point choice, not color confusion.
- Gray handling is OK: index-dev.md states the gray region/dots are "a descriptive reference, not a confidence interval," random points render as gray circles/dots, and raw random peaks are not marked as accepted.

**Fix:** mark the L16 -C selection at (0.453, 0.323) (C=11.9) and the +C selection at (1.787, 0.367) (C=12.276) in both PNGs, matching `dev-comparison.csv`/`results.csv` and `index-dev.md`.
