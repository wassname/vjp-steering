Checked all five risks against plot.png, index.md, and results.csv. Plotted coordinates match the CSV exactly (4 distinct +C markers at (−0.18, 0.147), (−0.607, 0.140), (0.067, 1.167), (−2.807, 4.593); one −C marker at (0.707, 4.207)), and the overplot annotations match the row counts (6 rows at α=1.25–2, 3 −C rows).

**Defects found**

1. **Legend marker fill contradicts the open/filled key** (`results/dev/j-lens-swap-formative-v1/plot.png`, legend). Both legend handles are drawn with *filled* markers (filled circle for "positive alpha (paper swap)", filled diamond for "negative alpha control"), while all 12 plotted data markers are open. index.md defines fill as the accept/reject encoding — "open markers failed either the generation/damage checks or the intended-effect check" — but that key appears nowhere on the figure, and the only fill exemplars a reader sees in the legend are filled. A reader using the legend as the marker key infers the +alpha style is a filled circle and cannot see from the figure alone that every point is rejected. The legend title "No accepted dose" states the conclusion but does not define the encoding. Fix: `markerfacecolor='none'` on the legend handles, plus a third proxy entry `open = rejected`.

2. **Shape collision between `bare` and the negative-alpha series.** `bare` is a filled black diamond; the negative-alpha control series also uses diamonds. Since fill is the accept/reject encoding, an *accepted* negative-alpha dose would render as a filled diamond, separable from `bare` by colour alone. Use a distinct shape for the reference point (e.g. star or square).

3. **Y-axis label omits the sign convention that index.md relies on.** Axis reads "off-axis change from bare (lower is better)"; index.md says "the plotted y value is the absolute change in the mean score from bare". The figure alone does not say the value is an absolute (unsigned) change, and the axis is inverted, so a standalone reader cannot tell whether y=4.59 is an increase or a decrease in off-axis score. Suggest "|off-axis score change| from bare (lower is better)". Lower severity than 1 and 2 — the caption does cover it.

**Passes**: series distinguishability (same hue, but solid/dotted plus circle/diamond is readable and colour-blind safe for two series); no title/legend/label overlap — the green "clean steer → …" annotations, "bare", "mostly side effects", and both overplot callouts are all clear of markers, lines, legend, and each other; overplot accounting is visible on-figure via "6 identical doses: alpha=1.25-2" and "3 identical doses: alpha=-0.5 to -2", each adjacent to its marker; index.md's rejected/admissible distinction is internally consistent with the CSV (10 rows `admissible=False`, plus 2 fluent wrong-sign +C rows at α=0.5, 1.0 → rejected=12 of N=12).

No edits made.

— Claude Opus 5 (claude-opus-5[1m]), Claude Code
