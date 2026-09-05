from hashlib import sha256
from pathlib import Path

from vjp_steering.results import J_LENS_DEV_RESULTS, _rows, plot


rows = _rows()
j_lens_rows = _rows(J_LENS_DEV_RESULTS, ("j_lens_swap",), {"j_lens_swap": {0}})
figures = {
    "measured": plot([*rows, *j_lens_rows]),
    "pareto": plot([*rows, *j_lens_rows], pareto=True),
}
for name, figure in figures.items():
    traces = {trace.name: trace for trace in figure.data if trace.name}
    assert len(traces["J-lens DEV +C measured doses"].x) == 13
    assert len(traces["J-lens DEV -C measured doses"].x) == 13
    assert "random measured evaluations" not in traces
    print(f"{name}: J-lens +C=13 -C=13 random=cone-only")

results = Path("results")
measured_hash = sha256((results / "plot.png").read_bytes()).hexdigest()
pareto_hash = sha256((results / "plot_pareto.png").read_bytes()).hexdigest()
assert measured_hash != pareto_hash
markdown = (results / "index.md").read_text()
html = (results / "index.html").read_text()
assert "](plot.png)" in markdown and "](plot_pareto.png)" in markdown
assert "results-plot" in html and "results-pareto-plot" in html
print(f"TWO_PLOTS_PASS measured_sha256={measured_hash} pareto_sha256={pareto_hash}")
print("— PI/OpenAI Codex")
