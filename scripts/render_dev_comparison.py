"""Render the frozen v14 DEV comparison without mixing it into all-100 results."""

import argparse
import csv
import json
from pathlib import Path

from vjp_steering.results import _display_table, _markdown, _summary, plot


ROOT = Path(__file__).resolve().parents[1]


def read_rows(experiment_id: str, method: str, seed: int, expected_cohort: str, expected_hash: str) -> list[dict]:
    path = ROOT / "data" / "dev" / experiment_id / "results.csv"
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"empty results: {path}")
    for row in rows:
        if row["method"] != method or int(row["seed"]) != seed:
            raise ValueError(f"method or seed mismatch: {path}")
        if row["eval_cohort"] != expected_cohort or row["data_hash"] != expected_hash:
            raise ValueError(f"cohort mismatch: {path}")
        row["seed"] = int(row["seed"])
        row["C"] = float(row["C"])
        row["effect"] = float(row["effect"])
        row["off_axis_perturbation"] = float(row["off_axis_perturbation"])
        row["admissible"] = row["admissible"] == "True"
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provenance", type=Path, default=ROOT / "slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json")
    args = parser.parse_args()
    provenance = json.loads(args.provenance.read_text())
    expected_hash = provenance["cohort"]["cohort_sha256"]
    expected_cohort = "sycophancy_dev15-v10"
    specs = [
        ("v14-dev-j-lens-swap", "j_lens_swap", 0),
        ("v14-dev-mean-diff", "mean_diff", 0),
        ("v14-dev-vjp-delta", "vjp_delta", 0),
        *[(f"v14-dev-random-s{seed}", "random", seed) for seed in range(5)],
    ]
    rows = [row for spec in specs for row in read_rows(*spec, expected_cohort, expected_hash)]
    methods = ("j_lens_swap", "mean_diff", "vjp_delta", "random")
    method_seeds = {"j_lens_swap": {0}, "mean_diff": {0}, "vjp_delta": {0}, "random": set(range(5))}
    table = _display_table(_summary(rows, methods, method_seeds, include_rejected=True))
    output = ROOT / "results"
    output.mkdir(exist_ok=True)
    (output / "index-dev.md").write_text(_markdown(table, (
        "DEV15 comparison only. Every row uses the frozen cohort, shared bare responses, AB/BA judging, and coherence rule in slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json.",
        "The gray region is five random vectors. It is a descriptive reference, not a confidence interval.",
    )))
    for filename, pareto, title in (
        ("plot-dev.png", False, "DEV15 steering comparison"),
        ("plot-pareto-dev.png", True, "Pareto-smoothed DEV15 steering comparison"),
    ):
        plot(rows, methods, method_seeds, title=title, pareto=pareto, include_rejected=True).write_image(output / filename, width=1064, height=590, scale=2)
    print(f"DEV_COMPARISON_RENDER_COMPLETE rows={len(rows)} output={output}")


if __name__ == "__main__":
    main()
