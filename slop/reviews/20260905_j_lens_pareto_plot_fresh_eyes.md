Read-only review, no edits made.

## 1. Same comparison plot? Yes

Title, axes, corner annotations, grey null zone, black `bare` diamond, and all seven prior series are unchanged, with final-dose `×` markers landing in the same places as the reference:

| series | reference `×` (x, y) | current `×` |
|---|---|---|
| per-side VJP +C | ~3.45, 1.13 | same |
| PCA | ~4.05, 1.03 | same |
| mean difference | ~4.35, 0.89 | same |
| VJP-delta | ~3.7, 0.70 | same |
| MLP-up VJP +C | ~3.5, 0.62 | same |
| J-word +C / -C | ~2.1, 0.65 / ~0.2, 0.37 | same |
| -C side (MLP-up, per-side, PCA, mean-diff, VJP-delta) | present | present |

Nothing was dropped. The lines are now monotone frontiers instead of raw dose polylines, which is the requested change; the discarded (non-Pareto) points survive as faint small dots.

## 2. Encoding problems

- **+C vs -C cyan is not readable.** Every light-blue J-lens trace I can see is dashed. I cannot find a solid cyan line anywhere, so the intended "solid = +C, dotted = -C" contrast does not exist on the page. The one cyan-ish solid line (upper right, ~y=0.2) reads as VJP-delta blue, not J-lens. This is the requested distinction and it is currently absent.
- **Dashes now mean two things.** Each prior method's final dose is attached by a dashed connector in its own colour (orange down to `mean difference`, blue up to VJP-delta, gold, pink). Same dash pattern as the J-lens series, so "dashed" reads as both "off-frontier jump to final dose" and "J-lens -C".
- **Triangles are unexplained.** Five open downward triangles sit on the bottom frame at x ≈ −3.3, −3.0, −1.65, −0.9, −0.35. The reference captioned them (`J-lens DEV: no accepted dose; both collapse off-scale ↓`); the current caption is only `directed J-lens transfer (DEV)`, floating mid-plot with no leader line and no "off-scale" wording. A reader has no way to know the triangles are clipped high-dose points.
- **Clipping/overlap.** The triangles are flush against the axis frame (glyph half-cut). `mean difference` text overlaps the orange dashed connector and collides with `mostly side effects` in red. `MLP-up VJP -C` sits well right of its `×` and crosses the pink PCA frontier. `per-side VJP -C` leader line runs into the `null zone` label block.
- Reference had `× = final plotted dose`; current says `× final dose` bottom-left — fine, but it no longer says *plotted*, which mattered given off-scale points exist.

## 3. Single most important fix

Make the two cyan J-lens series distinguishable and self-labelling: draw +C solid and −C dotted, label each at its line end (not one shared floating caption), and change the other methods' final-dose connectors to a different idiom (thin solid, or drop them) so dash is reserved for −C. Fold the "no accepted dose; collapses off-scale ↓" wording back in next to the triangles.

---
Claude Opus 5 (`claude-opus-5[1m]`), Claude Code.
