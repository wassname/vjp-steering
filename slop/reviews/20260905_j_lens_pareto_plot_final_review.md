Read `results/plot.png`. Still the same all-method comparison: title "VJP steering on Bullshit Bench v2", judge on-axis change vs off-axis damage, black `bare` diamond at origin, grey null zone, and all the existing methods (mean difference, PCA, VJP-delta, per-side VJP ±C, MLP-up VJP ±C, J-word ±C) plus the cyan J-lens DEV overlay. Nothing was swapped or dropped.

**Prior ambiguity: resolved.** Both cyan X marks now carry inline labels with leaders — "J-lens +C DEV" pointing at the X just below `bare` (~0.1, 0.06), "J-lens -C DEV" pointing at the X at (~-0.25, 0.31). No more guessing which cyan X is which sign.

Three things I still see, in order of how much they matter:

1. **Text collision (material).** The second key line, `open cyan dots: measured doses · faint line: dominated final dose`, runs its tail directly into the dense data cluster at x≈0, y≈0.13–0.18. The words "final dose" sit on top of the orange/yellow/blue lines and the `J-lens +C DEV` leader line. Both remain legible, but this is a real overlap, not just close spacing — shortening that line or moving it left ~0.5 x-units would clear it.
2. **Solid vs dotted is not readable (ambiguous encoding).** The key promises `solid +C · dotted -C`, but at this line width the cyan traces all read as thin solid. I cannot distinguish the two by dash pattern; I can only tell them apart via the new inline labels. The labels currently carry the whole burden the linestyle was meant to share.
3. **No clipping.** The off-scale ▽ markers at the bottom (y≈1.24) sit inside the axes with margin to spare, and all edge labels (`per-side VJP +C`, `PCA`, `mean difference`) are fully inside the frame.

Point 1 is the only one I'd call worth a fix pass; point 2 is a redundancy loss rather than an error, since the labels disambiguate.

No edits made — read-only as asked.

-- Claude Opus 5 (1M context), `claude-opus-5[1m]`, via Claude Code
