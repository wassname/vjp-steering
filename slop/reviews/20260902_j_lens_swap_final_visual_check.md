Looked at `results/dev/j-lens-swap-formative-v1/plot.png`.

**Visual defects found**

1. **Right corner label touches/overruns the frame.** "clean steer -> sycophantic" ends flush at the right axis spine (x=3); the final "c" sits on the frame line. The left twin has clear margin. Right-aligned text with no pad — trim or nudge inward.
2. **Both series share one colour.** Positive-alpha and negative-alpha are the same blue, distinguished only by dash + marker shape (small open circle vs small open diamond). At this marker size the shapes are hard to tell apart; the encoding difference is essentially the dash pattern. The two series mean opposite things — they should differ in hue.
3. **Overlapping markers at (0.05, 1.15).** Two circles are drawn nearly on top of each other, offset by a couple of pixels. Unclear whether this is two distinct doses or a rendering artefact; nothing in the annotations covers it.
4. **Legend title "No accepted dose" reads as a category header.** It sits where a legend title goes, so it looks like it labels the two entries below it (i.e. "these are the no-accepted-dose series") rather than being a result about the run. Ambiguous placement.
5. **"mostly side effects" (red, bottom centre) has no anchor.** It floats between the two series with no arrow, bracket or shaded region — the reader can't tell if it describes the lower half of the plot, the bottom-left point, or the whole figure.
6. **Y axis is inverted with no cue.** 0 at top, 4+ at bottom. "(lower is better)" is in the label, but nothing signals that the axis runs downward, so a fast reader can misread the bottom-left point as the best one.
7. **Line order is unexplained.** The solid series zigzags (top-left → top-centre → down-right → far bottom-left) and there's no arrow or per-point alpha label, so the dose sequence along the path can't be recovered. The two range annotations ("alpha=1.25-2", "alpha=-0.5 to -2") don't map onto individual markers.

No clipping of tick labels, title, or axis titles; the "bare" label does not collide with the star or the dotted line.

Most worth fixing first: (1) the frame overrun, (2) same-colour series, (5) unanchored red annotation.

-- Claudy[opus-5] / ponytail full
