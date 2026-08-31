## Review
- Correct: `results/plot.png` remains an all-method figure: it shows VJP-delta, mean difference, PCA, J-word, MLP-up VJP, the random-direction null cone, and the purple per-side VJP addition. Title and axes are readable: “judge on-axis change” and “off-axis damage (lower is better).”
- Correct: `results/index.md:16` accurately records the EB per-side result as `-C: not confirmed`, `+C: 3.161`, `+C damage: 0.649`, `seeds: 1`, `N: 1`, `rejected: 1`. This matches `data/formative/mlp-up-left-right-formative-v5-eb/results.csv:2-3`: the +C record is admissible `True`; the -C record is `False`.
- Correct: The plot shows exactly one purple `per-side VJP +C` point at approximately `(3.161, 0.649)` and does not depict a successful -C endpoint. Thus it does not visually claim bidirectional confirmation.
- Residual risk: The rejected -C result is communicated only by the table, not a dedicated plot annotation; plot-only readers may miss that limitation. This is not a misleading claim because the plotted label explicitly says `+C`.
- No issues found.
- Merge verdict: OK with notes.

— PI reviewer subagent
