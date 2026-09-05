Read-only review. Nothing edited.

## 1. Still the all-method comparison plot — yes

`results/plot.png` (2128×1180) renders the same seven-series figure defined by `METHODS` in `src/vjp_steering/results.py:31`: VJP-delta, mean difference, PCA, J-word, MLP-up VJP, per-side VJP, plus the grey `random` null zone. Both sides (`+C`/`-C`) are labelled for the four methods that carry side labels, `bare` is the black filled diamond at the origin, and the cyan J-lens DEV overlay is layered on top (`_add_j_lens_dev_overlay`, `results.py:522`). Axis limits recomputed from the CSV match what is drawn: `x_limit=±4.711`, `y_range=(1.293, -0.07)`, `damage_limit=1.2286`.

## 2. The rejected per-side VJP −C point — found, drawn, connected

CSV row (`data/results.csv`), the only inadmissible per-side row in the file:

```
method=vjp_mlp_up_left_right_shrink  seed=0  C=28.60187715130719  side=-C
effect=-0.6415  off_axis_perturbation=1.0225  admissible=False
source_run=mlp-up-left-right-formative-v7-eb-audited
```

Through `_means(..., include_rejected=True)` it becomes `{complete: True, admissible: False, accepted: False}` → symbol `circle-open`, colour `#6f4aa8`. Crop at that location (`/tmp/c_target.png`) shows the purple open circle at ≈(−0.64, 1.02) with the thin `opacity=0.35, width=0.8` tail running up to the per-side VJP −C curve. Both marker and connector are legible at 100%.

## 3. Expanded coverage — visible, with two material defects

Recomputed symbol census (dose-level means, rejected included):

| symbol | meaning (`results.py:477-482`) | count |
|---|---|---|
| filled circle | accepted | 193 |
| open circle | rejected, in range | 25 |
| open diamond | incomplete seed | 5 |
| open ▽ | off-scale, `damage > 1.2286` | 41 main + 6 J-lens = 47 |

**(a) Label collision destroys ~9 off-scale triangles.** Pixel scan of the triangle row (rows 978–1018, x-calibrated from gridlines at px 283/471/658/846/1221 → 187.6 px per unit, x=0 at px 1033.4): every cluster from x≈+3.1 rightward is dominated by `#6f4aa8`, the *per-side VJP +C* label text, not by triangle stroke:

```
x=+3.21 w=16 [('#6f4aa8', 87), ...]
x=+3.92 w=27 [('#6f4aa8',136), ...]
x=+4.22 w=19 [('#6f4aa8', 53), ...]
```

The nine off-scale triangles at x = 3.14, 3.34 (vjp_delta), 3.54, 3.91 (pca), 3.73, 3.78, 4.05, 4.19, 4.21 (mean_diff) sit under the glyphs; only faint tips survive (`/tmp/c_br.png`, `/tmp/c_tri.png`). That is ~22% of the off-scale evidence, concentrated in the high-effect region the plot is arguing about.

**(b) Triangle overplotting merges neighbours.** 47 triangles resolve into ~20 clusters left of the label. Worst: one 82-px blob at x≈+2.55 covering six doses (2.42/2.48/2.57 mlp_up, 2.53/2.66 pca, 2.71 vjp_delta), and a 41-px blob at x≈+1.04 covering four (0.98/1.01/1.07 vjp_delta, 1.10 pca). Counting off-scale doses from the static PNG is not possible.

**(c) Rejected in-range open circles read fine.** The five that matter (near the axes and at the curve ends: mean_diff +C 4.45/1.176, pca −C −0.82/1.187, J_word +C 2.45/1.170, mlp_up +C 3.10/1.075, per-side −C −0.64/1.022) are all separated and each has its faint tail. The other 20 are clustered at |effect|<0.06, damage<0.22 near the origin and are unreadable individually — acceptable, since they are the "did nothing" doses.

**(d) Diamonds are drawn but unexplained and mis-cued.** All 5 are vjp_delta +C at x 3.04–3.28, damage 0.253–0.302 (`/tmp/c_diam.png`). Two problems: the in-figure legend has no diamond key at all (only `results/index.md:5` prose explains it), and the black filled diamond already means `bare` at the origin.

## 4. Encoding ambiguity: open-glyph colour collapse

Sampled diamond stroke pixels are core `#0072B2` (correct vjp_delta), but at `opacity=0.6` on a 1-px open outline the anti-aliased body is `#9BC8E1`/`#BCDAEA`. In the triangle row the same effect gives vjp_delta triangles as `#afd3e7`/`#cae2ef` against J-lens triangles as `#a6d8f3`/`#8cccf0`. Those are visually the same pale blue. Since the only in-figure key for `○` and `▽` sits inside the cyan block — "cyan J-lens DEV: solid +C · dotted −C · ▽ off-scale" — a reader will plausibly attribute vjp_delta's 14 off-scale triangles and all 5 diamonds to the DEV overlay. This is a rendering/perception issue, not a data issue.

Secondary: `circle-open` means *rejected dose* for main methods (`results.py:481`) but *every measured dose* for the J-lens overlay (`results.py:299`). Same glyph, opposite semantics, one legend line.

## 5. Clipping — none

Max `|effect|` = 4.497 (main) and −3.253 (DEV), both inside ±4.711. No point falls outside the x range. All damage above 1.2286 is deliberately clamped to the triangle row; true values reach 4.326 (main) and 4.613 (DEV), so the row compresses a 3.8× spread to a single line with no magnitude cue in the static PNG — by design, recoverable only via hover in the HTML. Top-left legend block, "null zone" text and the corner annotations overlap no data.

## Ranked

1. Off-scale triangles at x>3.1 occluded by the *per-side VJP +C* label (~9 markers). Fix is moving that one label, not changing the encoding.
2. No legend key for open diamond; diamond glyph already used for `bare`.
3. Pale anti-aliased `#0072b2` open glyphs read as J-lens cyan.
4. Triangle overplotting; ~47 markers in ~20 resolvable clusters.
5. `circle-open` carries two different meanings between the main series and the DEV overlay.

Open these:
- `/workspace/2026/jspace/j-steer_pub/results/plot.png`
- `/tmp/c_target.png` — the rejected per-side VJP −C point and its tail
- `/tmp/c_tri.png`, `/tmp/c_br.png` — the label-over-triangles collision
- `/tmp/c_diam.png` — the five incomplete-seed diamonds
- `/workspace/2026/jspace/j-steer_pub/src/vjp_steering/results.py:477` — symbol logic

— Claude Opus 5 (`claude-opus-5[1m]`), Claude Code
