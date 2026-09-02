## Review before side-label correction

- Curves match `results.csv`: plotted coordinates correspond to all 15 `+C` rows and all 17 `-C` rows, with x = `effect` and inverted y = `off_axis_perturbation`.
- No `+C` success is implied. `selected.json` records `+C.status` as `no_accepted_endpoint`; all plotted `+C` effects are negative.
- Finding: the plot did not distinguish the `+C` and `-C` curves. The renderer now labels an unselected curve as `+C (no accepted dose)`; a second review covers that rerender.
- Limitation: the black bare origin is the defined zero baseline, not a `results.csv` row.

— reviewer subagent, transcribed by PI/Codex
