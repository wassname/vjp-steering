"""Render the frozen v14 DEV comparison without mixing it into all-100 results."""

import argparse
import csv
import hashlib
import json
from math import isclose
from pathlib import Path
from statistics import mean

from judge import CACHE, DEV, LEGACY_RUBRIC, experiment_rows, required_cells, valid
from export import score_cell, signed_axis_effect
from vjp_steering.results import INDEX_NOTE, SUMMARY_NOTE, _display_table, _markdown, _summary, plot


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
    cells = required_cells(experiment, DEV.orders, DEV.passes, rubric=LEGACY_RUBRIC)
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
        if row["method"] != method or int(row["seed"]) != seed or row["source_run"] != experiment_id:
            raise ValueError(f"method or seed mismatch: {path}")
        if row["eval_cohort"] != "sycophancy_dev15-v10" or row["data_hash"] != expected_hash:
            raise ValueError(f"CSV cohort mismatch: {path}")
        row["seed"] = int(row["seed"])
        row["C"] = float(row["C"])
        row["effect"] = float(row["effect"])
        row["off_axis_perturbation"] = float(row["off_axis_perturbation"])
        if row["admissible"] not in {"True", "False"}:
            raise ValueError(f"invalid coherence flag: {path}")
        row["admissible"] = row["admissible"] == "True"
        selected = [entry for entry in experiment if entry["side"] == row["side"] and entry["coefficient"] == row["C"]]
        if sorted(entry["vignette"] for entry in selected) != sorted(expected_ids):
            raise ValueError(f"CSV dose lacks exact generated cohort: {path} {row['side']} C={row['C']}")
        scores = []
        for entry in selected:
            entry_keys = required_cells([entry], DEV.orders, DEV.passes, rubric=LEGACY_RUBRIC)
            judgments = [score_cell(cache[key]) for key in entry_keys]
            scores.append((signed_axis_effect(entry.get("behavior_target") or row["side"], judgments),
                           abs(mean(score[1] for score in judgments)), mean(score[2] for score in judgments)))
        for field, column in (("effect", 0), ("off_axis_perturbation", 1)):
            if not isclose(row[field], mean(score[column] for score in scores), abs_tol=1e-9):
                raise ValueError(f"CSV {field} differs from frozen v7 judgments: {path} {row['side']} C={row['C']}")
        health = [cell for cell in manifest["cells"][row["side"]].values() if cell["coefficient"] == row["C"]]
        if len(health) != 1:
            raise ValueError(f"CSV dose lacks exact manifest health: {path} {row['side']} C={row['C']}")
        admissible = not health[0]["breakdown_reasons"] and mean(score[2] for score in scores) <= 1.5
        if row["admissible"] != admissible:
            raise ValueError(f"CSV coherence differs from manifest/v7 judgments: {path} {row['side']} C={row['C']}")
        if method == "random":
            row["normalized_dose_id"] = normalized_calibration_dose_id(
                row["C"],
                manifest["boundaries"][row["side"]]["C_approx"],
                provenance["calibration_grid"]["fractions"],
            )
            row["normalized_dose_fraction"] = (
                provenance["calibration_grid"]["fractions"][row["normalized_dose_id"]]
                if row["normalized_dose_id"] is not None else None
            )
    print(f"VERIFIED_FROZEN_DEV id={experiment_id} rows={len(rows)} rubric={LEGACY_RUBRIC}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provenance", type=Path, default=ROOT / "slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json")
    args = parser.parse_args()
    provenance = json.loads(args.provenance.read_text())
    cache = raw_judgments()
    specs = comparison_specs(provenance)
    # Display names distinguish verified L16 variants. -- PI/OpenAI
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
        "normalized_dose_id", "normalized_dose_fraction", "source_run", "eval_cohort", "data_hash",
    )
    with (output / "dev-comparison.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=source_columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    markdown = _markdown(table, (
        f"DEV15 comparison only, frozen historical rubric `{LEGACY_RUBRIC}`. Exact scenario/shared-bare and generation settings checked; CSV effects, changes and dose-level coherence recomputed against existing AB/BA judgments and manifest health. No new judgments.",
        "The figures are separate from the all-100 results. Smooth lines are visual guides with exact bare and selected-dose endpoints, not measured intermediate doses. Open dots are rejected; triangles are off-scale. Selection uses peak accepted effect for J-lens and last accepted dose for the baselines. The table uses peak accepted effect. Raw measured values remain in `dev-comparison.csv`.",
        SUMMARY_NOTE,
        INDEX_NOTE,
        "[Paired scenario uncertainty for the selected comparisons](../slop/logs/20260912_repairs/escape-bootstrap.log); these intervals are conditional on dose and seed selection.",
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
