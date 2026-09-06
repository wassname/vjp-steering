from hashlib import sha256
from math import isclose
from pathlib import Path

from vjp_steering.results import (
    METHODS,
    METHOD_SEEDS,
    _means,
    _pareto_curve_anchors,
    _pareto_curve_parts,
    _rows,
    plot,
)


rows = _rows()
measured = plot(rows)
pareto = plot(rows, pareto=True)
measured_traces = {trace.name: trace for trace in measured.data if trace.name}
pareto_traces = {trace.name: trace for trace in pareto.data if trace.name}
assert all("J-lens DEV" not in name for name in measured_traces)
assert all("J-lens DEV" not in name for name in pareto_traces)
assert "random measured evaluations" not in measured_traces
assert "random measured evaluations" not in pareto_traces

main_means = _means(rows, METHODS, METHOD_SEEDS)
for method in (method for method in METHODS if method != "random"):
    for side in ("+C", "-C"):
        points = sorted(
            (row for row in main_means if row["method"] == method and row["side"] == side),
            key=lambda row: row["C"],
        )
        frontier, _ = _pareto_curve_parts(points, side)
        anchors = _pareto_curve_anchors(points, side)
        trace = pareto_traces[f"{method} {side} Pareto path"]
        assert isclose(trace.x[0], 0.0) and isclose(trace.y[0], 0.0)
        assert isclose(trace.x[-1], points[-1]["effect"])
        assert isclose(trace.y[-1], points[-1]["off_axis_perturbation"])
        assert len(trace.x) == max(128, 32 * len(anchors)) + 1
        assert all((1 if side == "+C" else -1) * point["effect"] >= 0 for point in frontier)
        assert min(trace.x) >= min(point["effect"] for point in anchors) - 1e-12
        assert max(trace.x) <= max(point["effect"] for point in anchors) + 1e-12
        assert min(trace.y) >= min(point["off_axis_perturbation"] for point in anchors) - 1e-12
        assert max(trace.y) <= max(point["off_axis_perturbation"] for point in anchors) + 1e-12

results = Path("results")
measured_hash = sha256((results / "plot.png").read_bytes()).hexdigest()
pareto_hash = sha256((results / "plot_pareto.png").read_bytes()).hexdigest()
assert measured_hash != pareto_hash
markdown = (results / "index.md").read_text()
html = (results / "index.html").read_text()
assert "](plot.png)" in markdown and "](plot_pareto.png)" in markdown
assert "results-plot" in html and "results-pareto-plot" in html
print("PARETO_PATH_PASS start=bare controls=all_pareto end=selected/final smoothing=clamped-cubic-bspline")
print("PUBLIC_J_LENS_DEV_OVERLAY_REMOVED")
print(f"TWO_PLOTS_PASS measured_sha256={measured_hash} pareto_sha256={pareto_hash}")
print("— PI/OpenAI Codex")
