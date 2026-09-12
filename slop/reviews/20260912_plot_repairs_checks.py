"""CPU probe: plotted-array source traces against the repaired renderer. -- PI/OpenAI"""
import csv, sys
from pathlib import Path

sys.path.insert(0, "src")
from vjp_steering.results import _means, _pareto_curve_anchors, _pareto_curve_parts, plot

ROOT = Path(".")


def load(path, cohort=None):
    rows = []
    for row in csv.DictReader(open(path)):
        row["seed"] = int(row["seed"]); row["C"] = float(row["C"])
        row["effect"] = float(row["effect"]); row["off_axis_perturbation"] = float(row["off_axis_perturbation"])
        row["admissible"] = row["admissible"] == "True"
        if row.get("normalized_dose_id") in ("", None):
            row["normalized_dose_id"] = None
        elif not isinstance(row["normalized_dose_id"], int):
            row["normalized_dose_id"] = int(row["normalized_dose_id"])
        if row.get("normalized_dose_fraction") in ("", None):
            row["normalized_dose_fraction"] = None
        elif not isinstance(row["normalized_dose_fraction"], float):
            row["normalized_dose_fraction"] = float(row["normalized_dose_fraction"])
        rows.append(row)
    return rows


failures = []
def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + (f" {detail}" if detail else ""))
    if not condition:
        failures.append(name)


# ---- FULL plot ----
from vjp_steering.results import METHODS, METHOD_SEEDS, SELECTED_FULL_METHOD, SELECTED_FULL_SEEDS, primary_methods
methods, method_seeds = primary_methods()
rows = load("data/results.csv", methods)
figure = plot(rows, methods, method_seeds, pareto=True)

# 1. rejected exclusion: every plotted line anchor comes from accepted means only
accepted = {(p["method"], p["C"], p["side"]) for p in _means(rows, methods, method_seeds) if p["accepted"]}
rejected_keys = {(p["method"], p["C"], p["side"]) for p in _means(rows, methods, method_seeds, include_rejected=True) if not p["accepted"]}
plotted_anchors = set()
for trace in figure.data:
    for anchor in (trace.meta or {}).get("controls", []) if isinstance(trace.meta, dict) else []:
        if isinstance(anchor, dict) and "method" in anchor:
            plotted_anchors.add((anchor["method"], anchor["C"], anchor["side"]))
check("no rejected anchor in any plotted line", not (plotted_anchors & rejected_keys), f"{len(rejected_keys)} rejected means exist")

# 2. endpoint equality: each line's last anchor equals its selected × marker
endpoint_mismatches = []
for trace in figure.data:
    if not isinstance(trace.meta, dict) or "controls" not in trace.meta:
        continue
    anchors = trace.meta["controls"]; endpoint = trace.meta["endpoint"]
    if endpoint is None:
        continue
    last = anchors[-1]
    if not (abs(last["effect"] - endpoint["effect"]) < 1e-12 and abs(last["off_axis_perturbation"] - endpoint["off_axis_perturbation"]) < 1e-12):
        endpoint_mismatches.append((trace.name, last["C"], endpoint["C"]))
check("every selected line ends at its selected marker", not endpoint_mismatches, str(endpoint_mismatches))
# line start is bare
starts = [trace.meta["controls"][0] for trace in figure.data if isinstance(trace.meta, dict) and trace.meta.get("endpoint") is not None]
check("every line starts at bare", starts and all(abs(a["effect"]) < 1e-12 and abs(a["off_axis_perturbation"]) < 1e-12 for a in starts), f"{len(starts)} lines")

# 3. region sorting: gray region vertices increase in damage (fraction order)
region = next(trace for trace in figure.data if trace.name == "random descriptive region")
region_sources = region.meta["sources"] if isinstance(region.meta, dict) else []
check("random region vertices sorted by actual dose", [s["dose"] for s in region_sources] == sorted(s["dose"] for s in region_sources), str([round(s["dose"], 4) for s in region_sources]))
check("random region reports seeds per side", all(sum(s["seeds_per_side"]) > 0 for s in region_sources))

# 4. input-row invariance: rendering must not mutate row dicts
snapshot = [(r["method"], r["seed"], r["C"], r["side"], r["effect"], r["off_axis_perturbation"], r["admissible"]) for r in rows]
plot(rows, methods, method_seeds, pareto=True)
check("input rows unchanged after render", snapshot == [(r["method"], r["seed"], r["C"], r["side"], r["effect"], r["off_axis_perturbation"], r["admissible"]) for r in rows])

# ---- DEV plot ----
dev_rows = load("results/dev-comparison.csv")
dev_methods = ("j_lens_swap", "j_lens_swap_L16", "j_lens_unit_L16", "j_lens_injection_L16", "j_lens_injection_doubt_L16", "mean_diff", "vjp_delta", "random")
dev_seeds = {"j_lens_swap": {0}, "j_lens_swap_L16": {0}, "j_lens_unit_L16": {0}, "j_lens_injection_L16": {0}, "j_lens_injection_doubt_L16": {0}, "mean_diff": {0}, "vjp_delta": {0}, "random": set(range(5))}
dev_fig = plot(dev_rows, dev_methods, dev_seeds, pareto=True, smooth=True, include_rejected=True, random_region="calibrated_rung", damage_headroom=1.20)
dev_rejected = {(p["method"], p["C"], p["side"]) for p in _means(dev_rows, dev_methods, dev_seeds, include_rejected=True) if not p["accepted"]}
dev_anchors = set()
for trace in dev_fig.data:
    if isinstance(trace.meta, dict):
        for anchor in trace.meta.get("controls", []):
            if isinstance(anchor, dict) and "method" in anchor:
                dev_anchors.add((anchor["method"], anchor["C"], anchor["side"]))
check("DEV: no rejected anchor in plotted lines", not (dev_anchors & dev_rejected), f"{len(dev_rejected)} rejected DEV means")
dev_region = next(trace for trace in dev_fig.data if trace.name == "random descriptive region")
dev_sources = dev_region.meta["sources"]
check("DEV region sorted by calibration fraction, id-9 low dose first", [round(s["dose"], 2) for s in dev_sources][0] == 0.40 and [round(s["dose"], 2) for s in dev_sources] == sorted(round(s["dose"], 2) for s in dev_sources), str([round(s["dose"], 4) for s in dev_sources]))

print("FAILURES" if failures else "ALL_PLOT_SOURCE_CHECKS_PASS", failures if failures else "")
sys.exit(1 if failures else 0)
