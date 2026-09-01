## Review
- Correct: Purple ±C markers in `results/plot.png` match the measured single-seed rows in `data/results.csv:790-801`; table values `0.968/0.416` and `3.466/1.129` in `results/index.md:12` occur at purple markers.
- Correct: Deterministic decimation explicitly retains each side’s table peak (`src/vjp_steering/results.py:270-276`).
- Correct: Gray open markers equal the random-table peak calculation; both use admissible dose means and the same signed maximum (`src/vjp_steering/results.py:234-255,386-401`). They match `results/index.md:16`.
- Correct: `× = final plotted dose` is accurate: the endpoint is selected as the final retained sorted dose (`src/vjp_steering/results.py:280-287`), and the plotted figure marks those endpoints with ×.
- No issues found.
- Merge verdict: OK

— PI reviewer subagent
