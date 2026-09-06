"""Check task 333 selected points against the renderer's random-cone vertices. — PI/OpenAI Codex"""

import csv
import json
from pathlib import Path
from statistics import median

from matplotlib.path import Path as Polygon


rows = []
with Path("data/results.csv").open() as handle:
    for row in csv.DictReader(handle):
        if row["method"] != "random":
            continue
        rows.append({
            **row,
            "seed": int(row["seed"]),
            "C": float(row["C"]),
            "effect": float(row["effect"]),
            "off_axis_perturbation": float(row["off_axis_perturbation"]),
            "admissible": row["admissible"] == "True",
        })
seeds = sorted({row["seed"] for row in rows})
by_cell = {(row["seed"], row["C"], row["side"]): row for row in rows}
cone = [(0.0, 0.0, 0.0, 0.0)]
for coefficient in sorted({row["C"] for row in rows}):
    coherent = [
        seed for seed in seeds
        if all(
            (seed, coefficient, side) in by_cell
            and by_cell[seed, coefficient, side]["admissible"]
            for side in ("+C", "-C")
        )
    ]
    if len(coherent) < len(seeds) // 2:
        break
    points = [by_cell[seed, coefficient, side] for seed in coherent for side in ("+C", "-C")]
    effects = sorted(point["effect"] for point in points)
    cone.append((
        median(effects),
        median(point["off_axis_perturbation"] for point in points),
        effects[len(effects) // 10],
        effects[-(len(effects) // 10) - 1],
    ))
vertices = (
    [(lower, damage) for _, damage, lower, _ in cone]
    + [(upper, damage) for _, damage, _, upper in reversed(cone)]
)
polygon = Polygon(vertices)
selected = json.loads(Path(
    "data/dev/j-lens-paper-workspace-sycophancy-dev-v1/selected.json"
).read_text())["sides"]
print("random_cone_vertices", vertices)
for side, row in selected.items():
    point = (row["effect"], row["off_axis_perturbation"])
    print(side, "point", point, "inside_random_cone", polygon.contains_point(point))
