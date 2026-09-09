"""Render the frozen v14 DEV comparison without mixing it into all-100 results."""

import argparse
import csv
import hashlib
import json
from math import isclose
from pathlib import Path

from judge import CACHE, DEV, experiment_rows, required_cells, valid
from vjp_steering.results import _display_table, _markdown, _summary, plot


ROOT = Path(__file__).resolve().parents[1]


def canonical_sha256(rows: list[dict]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def normalized_calibration_dose_id(coefficient: float, c_approx: float, fractions: list[float]) -> int | None:
    matches = [
        index for index, fraction in enumerate(fractions)
        if isclose(coefficient, c_approx * fraction, rel_tol=1e-10, abs_tol=1e-12)
    ]
    if len(matches) > 1:
        raise ValueError(f"ambiguous normalized calibration dose: C={coefficient} C_approx={c_approx}")
    return matches[0] if matches else None


def raw_judgments() -> dict[str, dict]:
    records = {}
    with CACHE.open() as file:
        for line in file:
            record = json.loads(line)
            if valid(record.get("judgment", {})):
                records[record["cache_key"]] = record
    return records


def verify_experiment(experiment_id: str, method: str, seed: int, provenance: dict, cache: dict[str, dict]) -> list[dict]:
    expected_hash = provenance["cohort"]["cohort_sha256"]
    expected_ids = provenance["cohort"]["scenario_ids"]
    generation = provenance["generation"]
    root = ROOT / "outputs" / "experiments" / experiment_id
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest["method"] != method or manifest["profiles"]["dev"] != {"status": "DEV", "cohort_size": 15, "generated": True}:
        raise ValueError(f"experiment identity mismatch: {experiment_id}")
    for key in ("model", "dtype", "max_length", "max_new_tokens"):
        if manifest["config"][key] != generation[key]:
            raise ValueError(f"generation config mismatch: {experiment_id} {key}")
    if manifest["cohort_sha256"] != expected_hash:
        raise ValueError(f"cohort hash mismatch: {experiment_id}")
    bare_path = root / manifest["bare"]["path"]
    bare = [json.loads(line) for line in bare_path.read_text().splitlines()]
    if [row["scenario"] for row in bare] != expected_ids:
        raise ValueError(f"ordered scenario mismatch: {experiment_id}")
    if canonical_sha256(bare) != provenance["shared_bare"]["selected_records_canonical_sha256"]:
        raise ValueError(f"bare response mismatch: {experiment_id}")
    if manifest["bare"].get("reused_from") != provenance["shared_bare"]["source_experiment"]:
        raise ValueError(f"bare provenance mismatch: {experiment_id}")
    experiment = experiment_rows(experiment_id, "dev", all_generated=True)
    cells = required_cells(experiment, DEV.orders, DEV.passes)
    missing = set(cells) - set(cache)
    if missing:
        raise ValueError(f"missing paired AB/BA judgments: {experiment_id} count={len(missing)}")
    seen_orders = {(row["vignette"], row["side"], order) for row, order, _ in cells.values()}
    expected_orders = {(scenario, side, order) for scenario in expected_ids for side in ("+C", "-C") for order in DEV.orders}
    if not expected_orders <= seen_orders:
        raise ValueError(f"incomplete AB/BA scenario coverage: {experiment_id}")
    path = ROOT / "data" / "dev" / experiment_id / "results.csv"
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"empty results: {path}")
    for row in rows:
        if row["method"] != method or int(row["seed"]) != seed:
            raise ValueError(f"method or seed mismatch: {path}")
        if row["eval_cohort"] != "sycophancy_dev15-v10" or row["data_hash"] != expected_hash:
            raise ValueError(f"CSV cohort mismatch: {path}")
        row["seed"] = int(row["seed"])
        row["C"] = float(row["C"])
        row["effect"] = float(row["effect"])
        row["off_axis_perturbation"] = float(row["off_axis_perturbation"])
        row["admissible"] = row["admissible"] == "True"
        if method == "random":
            row["normalized_dose_id"] = normalized_calibration_dose_id(
                row["C"],
                manifest["boundaries"][row["side"]]["C_approx"],
                provenance["calibration_grid"]["fractions"],
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provenance", type=Path, default=ROOT / "slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json")
    args = parser.parse_args()
    provenance = json.loads(args.provenance.read_text())
    cache = raw_judgments()
    specs = [
        ("v14-dev-j-lens-swap", "j_lens_swap", 0),
        ("v14-dev-mean-diff", "mean_diff", 0),
        ("v14-dev-vjp-delta", "vjp_delta", 0),
        *[(f"v14-dev-random-s{seed}", "random", seed) for seed in range(5)],
    ]
    rows = [row for spec in specs for row in verify_experiment(*spec, provenance, cache)]
    methods = ("j_lens_swap", "mean_diff", "vjp_delta", "random")
    method_seeds = {"j_lens_swap": {0}, "mean_diff": {0}, "vjp_delta": {0}, "random": set(range(5))}
    table = _display_table(_summary(rows, methods, method_seeds, include_rejected=True))
    output = ROOT / "results"
    output.mkdir(exist_ok=True)
    (output / "index-dev.md").write_text(_markdown(table, (
        "DEV15 comparison only. Every point passed exact scenario, shared-bare, generation-config, AB/BA judgment, and coherence provenance checks.",
        "The gray region is five random vectors. It is a descriptive reference, not a confidence interval.",
    )))
    for filename, pareto, title in (
        ("plot-dev.png", False, "DEV15 steering comparison"),
        ("plot-pareto-dev.png", True, "Pareto-smoothed DEV15 steering comparison"),
    ):
        plot(
            rows,
            methods,
            method_seeds,
            title=title,
            pareto=pareto,
            include_rejected=True,
            random_region="calibrated_rung",
        ).write_image(output / filename, width=1064, height=590, scale=2)
    print(f"DEV_COMPARISON_RENDER_COMPLETE rows={len(rows)} output={output}")


if __name__ == "__main__":
    main()
