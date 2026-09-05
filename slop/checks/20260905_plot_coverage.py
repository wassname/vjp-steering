from vjp_steering.results import (
    J_LENS_DEV_RESULTS,
    METHODS,
    METHOD_SEEDS,
    _means,
    _pareto_curve_parts,
    _rows,
    plot,
)

rows = _rows()
j_lens_rows = _rows(
    J_LENS_DEV_RESULTS,
    methods=("j_lens_swap",),
    method_seeds={"j_lens_swap": {0}},
)
points = _means(rows, METHODS, METHOD_SEEDS, include_rejected=True)
figure = plot([*rows, *j_lens_rows], include_rejected=True)
traces = {trace.name: trace for trace in figure.data if trace.name}

for method in (method for method in METHODS if method != "random"):
    for side in ("+C", "-C"):
        csv_doses = {
            row["C"] for row in rows
            if row["method"] == method and row["side"] == side
        }
        plotted = traces[f"{method} {side} measured doses"]
        assert len(plotted.x) - 1 == len(csv_doses)
        print(f"{method} {side}: measured_doses={len(csv_doses)} markers={len(plotted.x) - 1}")

random_rows = [row for row in rows if row["method"] == "random"]
assert len(traces["random measured evaluations"].x) == len(random_rows)
print(f"random: measured_evaluations={len(random_rows)} markers={len(random_rows)}")

for side in ("+C", "-C"):
    expected = sum(row["side"] == side for row in j_lens_rows)
    actual = len(traces[f"J-lens DEV {side} measured doses"].x)
    assert actual == expected
    print(f"J-lens DEV {side}: measured_doses={expected} markers={actual}")

v7 = next(
    point for point in points
    if point["method"] == "vjp_mlp_up_left_right_shrink"
    and point["side"] == "-C"
    and abs(point["C"] - 28.60187715130719) < 1e-9
)
assert not v7["admissible"]
assert v7["effect"] == -0.6415000000000001
assert v7["off_axis_perturbation"] == 1.0225
v7_group = sorted(
    (
        point for point in points
        if point["method"] == "vjp_mlp_up_left_right_shrink"
        and point["side"] == "-C"
        and point["complete"]
        and point["off_axis_perturbation"] <= 1.21
    ),
    key=lambda point: point["C"],
)
_, extension = _pareto_curve_parts(v7_group, "-C")
assert extension and extension[-1] is v7
print("V7_REJECTED_FINAL_VISIBLE C=28.601877 effect=-0.6415 damage=1.0225 faint_tail=true")
print("ALL_MEASURED_PLOT_COVERAGE_PASS")

# PI/OpenAI Codex
