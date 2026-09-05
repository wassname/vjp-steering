Read the PNG, cropped six regions at 3–4× and calibrated the axis from the gridline pixels (y=0 at py 129.5, y=1.2 at py 986.5 → 714.2 px/unit), then recomputed the layout constants from `data/results.csv` + `data/random_results.csv`.

## The five items — all resolved

**(1) Rejected per-side VJP −C point — present.** `data/results.csv` row: `method=vjp_mlp_up_left_right_shrink, C=28.60187715130719, side=-C, effect=-0.6415, off_axis_perturbation=1.0225, admissible=False`. Rendered as a purple (`#6f4aa8`) open circle at py≈(915, 860) → (−0.64, 1.02), joined to the accepted endpoint by the faint `width=0.8, opacity=0.35` extension line (`results.py:461`). Visible in the crop, clearly not clipped.

**(2) Marker key no longer reads as cyan.** Two separate legend lines: cyan `cyan J-lens DEV: solid +C · dotted -C`, then a dark-gray `● accepted · ○ rejected/DEV · ◇ partial · △/▽ off-scale`. The ◇ glyph is gray, not cyan.

**(3) Off-scale △ staggered, below all X markers, not covered.** Computed rows from `results.py:468` with y_range[0]=1.2933:

| method | △ row (damage units) | py |
|---|---|---|
| vjp_delta | 1.2739 | 1039 |
| mean_diff | 1.2669 | 1034 |
| pca | 1.2599 | 1029 |
| J_word | 1.2529 | 1024 |
| MLP-up VJP | 1.2459 | 1019 |
| per-side VJP | 1.2389 | 1014 |

Measured pixel centres match (pca band 1025–1033, mean_diff 1029–1038). Lowest X marker is mean_diff at y=1.20 (py 986); every △ row is below it. Nearest text (`mostly side effects` py≈880, `mean difference` py≈810) is well clear.

**(4) J-lens ▽ distinct.** `results.py:530` now passes the overlay its own limit `y_range[0]*0.985 - 0.007*6 = 1.2319` (py 1009). Measured cyan ▽ span 1005–1019 → centre ≈1010. They sit on their own row above all six △ rows, size 9 vs 5–6, downward, cyan. Six of them, matching the six `off_axis_perturbation > limit` rows in `data/dev/j-lens-transfer-formative-v2/results.csv` (4.61, 4.59, 4.53, 4.23, 3.93, 3.93).

**(5) All baselines/prior methods present.** Labeled X markers for VJP-delta, mean difference, PCA, J-word ±C, MLP-up VJP ±C, per-side VJP ±C, J-lens ±C DEV, plus the bare diamond and the random null zone. Nothing dropped.

## One material finding

**A real data point is drawn at the exact height of a placeholder row.**

`vjp_delta, C=0.7071067811865476, +C` — seed-mean `effect=3.337, off_axis_perturbation=1.2454`, all three seeds `admissible=False`. It is ≤ the main `damage_limit` (1.2545), so it renders as a true-position open circle at py 1019.0. The MLP-up VJP placeholder row is at py 1019.4 — a 0.4 px collision. It also sits *below* the cyan ▽ row (1.2319) and below the per-side △ row (1.2389).

Two ways that misleads:
- Vertical position inside the strip y∈[1.2319, 1.2739] is meaningless for triangles (parking rows) but meaningful for this circle. Nothing in the encoding distinguishes them.
- It reads as "more damaging than the J-lens ▽", but those ▽ have true damage 3.93–4.61 — roughly 3.5× worse. The comparison is inverted.

Visible in the crop: the dark-blue open circle at x≈3.3 hovering between a light-blue △ and a pink △.

## Two minor residuals (not blocking)

- **Two different off-scale thresholds on one axis.** Main methods clip at 1.2545 (`results.py:362`); the J-lens overlay clips at 1.2319 (`results.py:533`). No J-lens point currently falls in the 0.023-wide gap, so it is cosmetic today — but the vjp_delta point above lands inside it, which is what produces the inverted read.
- **Gray open circles are unexplained.** The two `#888888` `circle-open` markers (`results.py:406`, random ±C table peaks) at ≈(0.45, 0.36) and ≈(2.98, 0.55) match the key's `○ rejected/DEV` glyph but are neither. Also, the partial-seed ◇ are stroked in vjp_delta `#0072b2` at 1 px, which antialiases to ≈(172,209,230) — perceptually close to J-lens cyan `#56b4e9` at 0.75 opacity ≈(128,199,238), and they sit in the same region. The legend fix addressed the key, not the stroke color.

Files: `results/plot.png`, `src/vjp_steering/results.py:362`, `src/vjp_steering/results.py:468`, `src/vjp_steering/results.py:530`

— Claudy[opus-5-1m], review only, no edits made
