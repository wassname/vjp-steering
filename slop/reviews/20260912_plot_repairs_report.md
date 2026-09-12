# Plot repair report — goal2 (saved-data plots and tables)

Worker: PI/OpenAI via goals-worker ba544b70 · 2026-09-12 · parent session 01a09444-e901-76a7-9b48-72700f33ec6b.
Scope: `src/vjp_steering/results.py`, `scripts/render_dev_comparison.py`, result tests, generated results outputs, README generated table block only. No commits, installs, or paid calls.

## Repairs applied

1. **Primary seed map (review finding 1).** `METHOD_SEEDS` now includes `random: {0..9}`; the primary entry-point combination `_rows → _summary` no longer raises KeyError (was `PRIMARY_SUMMARY_FAIL`).
2. **Coherent-only Pareto anchors ending at the selected cross (finding 2).** Curve construction takes accepted dose means only; the selected endpoint is passed explicitly and the line's last control equals the × marker (probe assertion). Rejected points remain visible as open markers but are never line anchors.
3. **Random geometry sorted by actual calibration fraction (finding 4).** `calibrated_random_rungs` groups random rows into rungs (named calibration dose levels, as in the provenance manifest), each carrying the manifest-derived `dose_fraction`; dose levels sort by that fraction, so region vertices are ordered by fraction (id 9 fraction 0.40 plots first). Dose IDs are never treated as sortable doses.
4. **One filled descriptive region.** A single pooled gray polygon (trimmed effect bounds at median change per fraction/C) plus eligible measured random dots; `random_controls()` shares one eligible population between plot and table. Full: ≥5/10 coherent in both signs per C. DEV: 5/5 per side/rung.
5. **N defined as plotted dose/side means (finding 8).** `N` counts admissible dose/side means; `rejected` counts measured dose/side groups without an accepted mean. Score selection and crosses: J-lens peak accepted effect, baselines last accepted dose; `INDEX_NOTE` in results pages distinguishes table peak from final cross.
6. **Clipped labels/crowding.** `char_w`/`line_h` matched to the 13px label font, label boxes clamped inside the plot area, legend notes moved below the axis, DEV variant color key as a horizontal legend (title moved left to avoid overlap).
7. **Frozen-DEV v7 integrity (parent/worker coordination).** `verify_experiment` pins `rubric=LEGACY_RUBRIC` (`results-demo-perresponse-syco-v7`), binds every CSV row to its experiment/source-run/C/scenario set, recomputes effect and off-axis change from the existing v7 AB/BA judgments, and checks dose-level coherence against manifest health. All 12 experiments verify with zero drift; no new judgments.
8. **Old CI/power claims removed from DEV prose** (parent request, seq 18); generated DEV notes link `slop/logs/20260912_repairs/escape-bootstrap.log` and label intervals conditional.

## Verification (CPU, offline, saved data only)

- `slop/reviews/20260912_plot_repairs_render.log` — 7/7 renderer tests, rung-identity regression, full + DEV renders (`wrote 8 table rows and 2 plots from 801 measured evaluations`, `DEV_COMPARISON_RENDER_COMPLETE rows=279`).
- `slop/reviews/20260912_plot_repairs_checks.log` — source-trace assertions: no rejected anchor in any plotted line (71 full / 93 DEV rejected means exist as open dots only); every selected line ends exactly at its × and starts at bare; region vertices sorted by actual dose (DEV 0.40 first); input rows unchanged after render; exactly one filled region.
- PNGs rendered and inspected by this worker: `results/plot_pareto.png`, `results/plot-dev.png` (endpoint-anchored, one zone, no clipping seen). Main non-Pareto `results/plot.png` regenerated unchanged in structure.
- Pre-repair reference preserved at `slop/reviews/20260912_plot_repairs_main_reference.png`.

## Final rendered state

- `results/plot.png` + `results/plot_pareto.png` (full, no DEV content), `results/plot-dev.png` + `results/plot-pareto-dev.png` (DEV only), `results/index.md`, `results/index.html`, `results/dev-comparison.csv` (adds `normalized_dose_fraction` only; all prior fields byte-equal — verified in render via exact value recomputation), README generated table + 35-word `<sub>` note inside CODEX markers only.
- Full random row changed from the stale saved values (`-0.782`, -C `-0.425`) to `— / not confirmed`: the saved row reported a wrong-direction -C peak under a rule the current code excludes (review finding 8). Source CSV numbers untouched; only the summary changed, as instructed.

## Limits

- Fresh-eyes image review is the parent's; this worker's PNG read found no clipping or rejected anchors, but placement judgment needs the independent pass.
- `data/results.csv` and all raw CSVs untouched (sha256 recorded before/after in render log context); README human prose untouched; generated table + `<sub>` note replaced inside the CODEX markers.
- Historical rubric v7 strings are only verified against the local cache checkout; no claim about external artifacts.

-- PI/OpenAI
