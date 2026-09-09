# Fresh-eyes review: results/plot-dev.png + results/plot-pareto-dev.png vs index-dev.md

Reviewer: **fresh-eyes reviewer** (scout subagent; model: text-only pipeline — no native image vision this session, so the "eyes" are pixel forensics with PIL/numpy/scipy at full 2128x1180 resolution, plus geospatial reasoning).
Date: 2026-09-09. Files examined (and only these): `results/plot-dev.png`, `results/plot-pareto-dev.png`, `results/index-dev.md`.

Method note (so you can weight the verdict): all geometry below is measured from raw pixels; text content could NOT be OCR'd (no tesseract/cv2), so anything that lives in words (endpoint labels, legend captions, the teal header line) is checked for *existence/placement/color*, not *wording*. Axis directions are inferred from tick geometry + the note's numbers, not confirmed from labels. Where an inference matters, I say so.

---

## (a) Does either plot visually suggest J-lens outside the random region in the intended direction?

**No — not in the direction that would matter.** But the note's phrasing "endpoints sit inside/among random points" is looser than the geometry for two of the five colored elements.

Measured (dev, plot interior, x>130):
- Gray (random) dots: x 130-1547, y 190-1015. Main cloud y~190-590 (dense), plus sparse dots at y 693-743, 801-820, 900-991 (mostly x 173-828) and isolated dots at (~773,503), (~1546,538).
- All colored curves top out at y=183 — only 7 px above the topmost gray dot (y=190). Not an overclaim; a hair.
- Rightward extent: blue reaches x=1493 < gray x=1547 (dev); pareto blue x=1437 < gray x=1581. Inside.
- Endpoints (bottommost colored pixels, labels included):
  - Blue: the curve ends in a **thick horizontal blue bar at y≈901-905 spanning x≈494-1237** (~740 px/row, 3-4 px tall), fed by a thin blue trace (x 825-1201, y 880-899) and trailed by a big block of blue text (y 945-1015, x 534-1493). Nearest gray to the bar's bottom pixels: 13 px — the bar's left end literally collides with the gray bottom-row dots (x 494-828, y 900-991). So blue's endpoint IS among the sparse bottom gray dots — but only at its left end.
  - Orange: bottom y=902; some orange pixels sit 1 px from a gray dot (on/near one). Among random points ✓.
  - Pink: tip pixels at (x 925-930, y 1023-1025), nearest gray **152-156 px** — 8-10 px *below* the lowest gray pixel (y 1015), in empty space.
  - Purple: tip band (x 918-1171, y 1022-1034), nearest gray 97-151 px — **19 px below the lowest gray dot**.

Since "up/high-score" and "right/far-dose" are the directions in which an *advantage* would have to show, and nothing pokes out there, the plots are consistent with the at-boundary conclusion. The pink/purple tips breach the gray field only **downward** — i.e., further into the worse direction — which is the opposite of an overclaim.

**The visual caveat**: the single most salient feature of `plot-dev.png` is the thick blue bar pinned at the bottom of the panel for ~3/4 of the plot's width, with no gray dots along most of its length (gray bottom row stops at x~828; the bar runs to x~1237). A viewer's eye reads that as "blue sits on the floor across the whole dose/score range" — a systematic statement the sparse gray field does not mirror along its length. That is not an *advantage* claim (bottom = low score = worse), but "endpoints sit inside/among random points" is only true for blue in the bounding-box sense, not in the "surrounded by dots" sense most of the bar's length.

## (b) Do the color key, endpoint labels, annotations match the at-boundary conclusion?

Partial mismatch — three concrete problems:

1. **The legend is incomplete for the two most/least visible variants.** The single-row legend band (y~124-153) contains colored swatches only for: **teal-green (74,143,105) @ x751-765, orange @ x1263-1276, pink @ x1654-1667** — plus gray text/line handles. There is **no blue swatch and no purple swatch**. The dominant visual element (blue curve/bar) and the purple elements are unkeyed within the figure. If the intended key is blue=13-21 / purple=unit control (as the note's framing suggests), the figure's own key does not confirm it.
2. **Teal-green is promised and never delivered.** The legend has a teal-green swatch, there is a full-width teal-green text block at y 88-109 (two text groups, x 155-479 and x 1539-1911), and small teal-green in-plot labels at (x 993-1257, y 263-298) — but there is **no teal-green curve, marker, or line anywhere in the data area of either PNG**. Either the green "L16" entity is drawn in a different color (then the key mislabels it — e.g., it may be hiding among the blue or orange curves), or it is missing from the renders entirely. This is the sharpest (b) finding: the key advertises a green element the plots do not contain. Check the generating code.
3. **Endpoint-label checks are limited to placement/color** (text unreadable without OCR): blue text under the blue bar (y 945-1015), orange text at three spots (x 45-387 y 657-679 — far from the orange curve at x 990-1130, placement quirk; x 1468-1725 y 503-525; x 1047-1306 y 924-951), green in-plot text (x 993-1257 y 263-298), purple glyphs. Nothing's position implies a ranking (no arrows, no corner annotations, no "best" markers). The wording of the teal header line and the numeric labels (e.g., +0.017 CI, -0.853) could not be verified — flag for a human pass.

Also worth recording: there is **no shaded gray "region"** in either plot — only gray dots (the light-gray (204,204,204) backdrop is the legend strip, not a confidence band). The note says the gray region + dots are five random vectors / descriptive reference — the figure renders exactly dots, so no mismatch there.

## (c) Rendering flaws that overclaim (or could be read as overclaiming)

1. **The thick blue bar is the loudest object in the figure** (row count ~741 px/row × 3 rows, spanning x 494-1237) — an order of magnitude more ink than the entire gray-dot field. It reads as a deliberate floor-line. If it is just many overplotted per-scenario paths, it is honest data but presented with false weight; a thinner/dashed render would prevent over-reading. Recommend rendering per-scenario paths with low alpha or single-pixel width.
2. **The bottom ~200 px of the data area is numerically unlabeled.** Y-axis tick labels stop at ~y 840-860; every figure of merit (the endpoints, the blue bar, pink/purple tips, the blue text block) sits at y 880-1034. Viewers cannot read endpoint scores off the axis. Nothing is *clipped* (all content ≥20 px from panel edges; the note's clipped-damage-axis worry is not borne out in the PNGs), but the axis coverage ends right above the region reviewers care about.
3. **Pareto plot tells a different story for pink than the measured plot.** Dev pink runs y 183 → 899 (pixels to 1025); pareto pink **ends at y 473**, inside the gray cloud (nearest gray 11-17 px). Under "Pareto-smoothed," pink's entire plunging lower half is trimmed. A reader of the pareto figure alone sees pink stopping mid-scatter; the measured figure shows it hitting the floor. If down = worse, this *hides* the bad tail (under-claim, not over-claim) — but the two figures disagree on where pink ends, and that deserves a callout in the caption or a consistent endpoint marker.
4. **Blue also shifts between figures**: dev blue x 494-1493 vs pareto blue x 571-1437 (compressed/shifted right). Minor, but the "same" variant occupies different territory in the two renders.
5. **Pink/purple tips breach the gray field downward** (8-19 px below the lowest gray dot, dev) into empty space — benign for *advantage* claims but it does undercut the literal "inside/among random points" wording in the note.

**Blunt bottom line: the plots do NOT overclaim an advantage for J-lens.** The geometry supports the at-boundary conclusion in both interesting directions. What the plots DO get wrong is honesty-by-completeness: an unkeyed blue/purple, a legend that promises a green entity that does not render, a pink story that changes between measured and smoothed figures, an unnumbered bottom zone, and a blue bar with far more visual weight than the reference field warrants. Fix the legend, confirm where the green L16 paths are (or delete the green swatch), and annotate/depict the endpoints consistently.

— fresh-eyes reviewer (pixel-forensic; text unverifiable without OCR)
