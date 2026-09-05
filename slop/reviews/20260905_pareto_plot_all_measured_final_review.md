Read `results/plot.png`, `data/results.csv`, `data/dev/j-lens-transfer-formative-v2/results.csv`, and `src/vjp_steering/results.py`. No files edited.

## Your five checks

**1. Rejected per-side VJP -C, C=28.601877 — PASS.** CSV row 801 gives `effect=-0.6415, off_axis_perturbation=1.0225, admissible=False`. Crop at that location shows a purple open circle with the faint (`opacity 0.35, width 0.8`) segment running up to the per-side -C branch. Visible and connected.

**2. Off-scale ▲ not hidden by the "per-side VJP +C" label — PASS.** The label baseline sits ~0.4 damage units above the staggered band. Crop shows the yellow MLP-up ▲ at x≈2.42/2.48/2.57 and the green J-word ▲ at 2.38/2.88 fully clear of the text and its leader line. Stagger is real: `off_scale_row = damage_limit - 0.012 * method_index` (results.py:466), 7 distinct rows over 1.167–1.239.

**3. J-lens ▽ distinct — PASS.** Size 9 open down-triangle vs size 6 up-triangle, and the six ▽ (x = -3.25, -3.06, -1.64, -0.88, -0.88, -0.31) sit visually above the ▲ band with no marker overlap in any crop I pulled.

**4. Partial-seed ◇ "explained" — FAIL, see below.**

**5. All baselines/prior methods — PASS.** `mean_diff, pca, vjp_delta, J_word, random, vjp_mlp_up_shrink, vjp_mlp_up_left_right_shrink` all present in the CSV and all labelled on the plot (mean difference, PCA, VJP-delta, J-word ±C, MLP-up VJP ±C, per-side VJP ±C, null zone, bare).

## Material findings

**A. The ◇ key is colour-coded to the wrong method.** The only explanation of `◇ partial` lives inside the annotation that starts `"cyan J-lens DEV: solid +C · dotted -C"`, rendered in `J_LENS_COLOR` (results.py:604-608). But the J-lens overlay never emits a diamond — `_add_j_lens_dev_overlay` only uses `circle-open` and `triangle-down-open` (results.py:299). All five diamonds are `vjp_delta` partial-seed probes at C≈0.255–0.293, x = 3.04–3.28, damage 0.25–0.30. Colour-sampled the diamond stroke: darkest pixel (121,181,214) → alpha-unmixed direction (1, 0.552, 0.306), which matches `#0072b2` vjp_delta (1, 0.553, 0.302), not `#56b4e9` J-lens (1, 0.444, 0.130). And J-lens DEV has no data out there at all — its x range is -3.25 to **0.413**. A reader following the cyan key attributes those five points to a 15-question DEV overlay instead of to the main 3-seed vjp_delta method.

**B. The mean-difference × sits inside the cosmetic off-scale band and occludes its own ▲.** `mean_diff -C` endpoint is (-1.296, **1.198**) — a genuine in-range value, since `damage_limit = 1.2389`. The staggered off-scale rows span 1.167–1.239, so the × lands in the middle of them, and the `mean_diff` off-scale ▲ at x=-1.28 is directly under it (crop: the orange triangle's apex is swallowed by the ×). Two problems: the triangle is partly lost, and the × is indistinguishable in height from neighbouring markers whose y carries no information.

## Minor, not blocking

Off-scale magnitude is unrecoverable from the static PNG — it only exists in the plotly `hovertemplate` ("off scale: true damage=…"). The largest suppressed values are J-lens 4.61 and vjp_delta 4.13, both drawn at ~1.24. `J_LENS_PLOT_NOTE` says the triangles "retain off-scale doses" but never says the excursion reaches ~4×. Fine for the interactive `index.html`, lossy for anyone reading the PNG alone.

Crops I used, if you want to look: `/tmp/c_rejected.png`, `/tmp/c_diamonds.png`, `/tmp/c_psvjp_label.png`, `/tmp/c_meandiff.png`, `/tmp/c_bottom_full.png`.

— Claude Opus 5 (1M), `claude-opus-5[1m]`, via Claude Code
