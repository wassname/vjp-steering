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


def comparison_specs(provenance: dict) -> list[tuple[str, str, int, str | None]]:
    methods = provenance["methods"]
    specs = [
        (methods["j_lens_swap"]["experiment_id"], "j_lens_swap", methods["j_lens_swap"]["seed"], None),
        (methods["mean_diff"]["experiment_id"], "mean_diff", methods["mean_diff"]["seed"], None),
        (methods["vjp_delta"]["experiment_id"], "vjp_delta", methods["vjp_delta"]["seed"], None),
        *[(entry["experiment_id"], "random", entry["seed"], None) for entry in methods["random"]["selected_experiments"]],
    ]
    if "j_lens_swap_L16" in methods:
        specs.append((methods["j_lens_swap_L16"]["experiment_id"], "j_lens_swap", methods["j_lens_swap_L16"]["seed"], "j_lens_swap_L16"))
    if "j_lens_unit_L16" in methods:
        specs.append((methods["j_lens_unit_L16"]["experiment_id"], "j_lens_unit_direction", methods["j_lens_unit_L16"]["seed"], "j_lens_unit_L16"))
    if "j_lens_injection_L16" in methods:
        specs.append((methods["j_lens_injection_L16"]["experiment_id"], "j_lens_injection", methods["j_lens_injection_L16"]["seed"], "j_lens_injection_L16"))
    if "j_lens_injection_doubt_L16" in methods:
        specs.append((methods["j_lens_injection_doubt_L16"]["experiment_id"], "j_lens_injection", methods["j_lens_injection_doubt_L16"]["seed"], "j_lens_injection_doubt_L16"))
    return specs


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
    specs = comparison_specs(provenance)
    # Handle display remapping for L16 (verified as j_lens_swap but displayed as j_lens_swap_L16)
    rows = []
    for spec in specs:
        exp_id, verify_method, seed, display_method = spec
        verified_rows = verify_experiment(exp_id, verify_method, seed, provenance, cache)
        if display_method:
            for r in verified_rows:
                r["method"] = display_method
        rows.extend(verified_rows)
    present = [m for m in ("j_lens_swap_L16", "j_lens_unit_L16", "j_lens_injection_L16", "j_lens_injection_doubt_L16") if any(r["method"] == m for r in rows)]
    methods = ("j_lens_swap", *present, "mean_diff", "vjp_delta", "random")
    method_seeds = {"j_lens_swap": {0}, "j_lens_swap_L16": {0}, "j_lens_unit_L16": {0}, "j_lens_injection_L16": {0}, "j_lens_injection_doubt_L16": {0}, "mean_diff": {0}, "vjp_delta": {0}, "random": set(range(5))}
    methods = tuple(m for m in methods if any(r["method"] == m for r in rows))
    method_seeds = {k: v for k, v in method_seeds.items() if k in methods}
    table = _display_table(
        _summary(rows, methods, method_seeds, include_rejected=True, random_region="calibrated_rung")
    )
    output = ROOT / "results"
    output.mkdir(exist_ok=True)
    source_columns = (
        "method", "seed", "C", "side", "effect", "off_axis_perturbation", "admissible",
        "normalized_dose_id", "source_run", "eval_cohort", "data_hash",
    )
    with (output / "dev-comparison.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=source_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    markdown = _markdown(table, (
        "DEV15 comparison only. Every point passed exact scenario, shared-bare, generation-config, AB/BA judgment, and coherence provenance checks.",
        "The gray region and measured gray dots are five random vectors. It is a descriptive reference, not a confidence interval. This first comparison does not show J-lens outside the measured random points in either direction. Paired two-level bootstrap over the 15 scenarios with AB/BA resampling (B=20000, exact sign-flip p): doubt -C4 margin vs best -C rung seed +0.017, 95% CI [-1.88,+1.88], p=0.98; swap-L16 +C margin vs best +C rung seed +0.41, CI [-0.71,+2.31], p=0.45. Both margins sit inside judge noise: the frozen DEV15 cohort cannot statistically resolve the two-direction discriminator (see audit). Against the stronger +C id0 rung the swap-L16 point leans loss (point -0.853, CI [-2.24,+0.24] crossing zero, p=0.049 borderline) — not robust either. Power extrapolation (audit, labeled): resolving the +C margin at 3 SE would take ~130 scenarios; the -C margin (~473k) needs a better repair, not more data. `not eligible` means an incoherent or wrong-direction measured point; raw rows are in `dev-comparison.csv`.",
    ), extra_pareto_plot=True)
    markdown = (
        markdown.replace("plot.png", "plot-dev.png")
        .replace("plot_pareto.png", "plot-pareto-dev.png")
        .replace("rejected↓", "not eligible↓")
    )
    (output / "index-dev.md").write_text(markdown)
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
            smooth=pareto,
            include_rejected=True,
            random_region="calibrated_rung",
            damage_headroom=1.20,
        ).write_image(output / filename, width=1064, height=590, scale=2)
    print(f"DEV_COMPARISON_RENDER_COMPLETE rows={len(rows)} output={output}")


if __name__ == "__main__":
    main()
