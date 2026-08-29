"""Select independent maximum judge-accepted endpoint doses from the tail cache."""

import argparse
import csv
import hashlib
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import endpoint_tail_manifest
from judge import MODEL, RUBRIC, cache_key, valid

CACHE = ROOT / "outputs/demo_judgments/judgments.jsonl"
MANIFEST = ROOT / "outputs/endpoint_tail_manifest.json"
OUTPUT = ROOT / "data/endpoint_tail"
ORDERS = ("AB", "BA")
PASSES = range(2)
CELL_FIELDS = (
    "method", "seed", "side", "C", "source_kind", "source_run", "raw_steered_source",
    "effect", "off_axis_perturbation", "steered_off_axis", "health_clean", "accepted",
)
SELECTED_FIELDS = CELL_FIELDS + ("selected_reason",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def score(record: dict) -> tuple[float, float, float]:
    judgment = record["judgment"]
    if record["order"] == "AB":
        return (
            judgment["on_axis_B"] - judgment["on_axis_A"],
            judgment["off_axis_B"] - judgment["off_axis_A"],
            judgment["off_axis_B"],
        )
    return (
        judgment["on_axis_A"] - judgment["on_axis_B"],
        judgment["off_axis_A"] - judgment["off_axis_B"],
        judgment["off_axis_A"],
    )


def cached_records(expected: dict[str, tuple[dict, str, int]]) -> dict[str, dict]:
    records = {}
    with CACHE.open() as file:
        for line in file:
            record = json.loads(line)
            key = record["cache_key"]
            if key not in expected or not valid(record.get("judgment", {})):
                continue
            _, order, pass_index = expected[key]
            assert record["model"] == MODEL
            assert record["rubric_version"] == RUBRIC
            assert record["order"] == order and record["pass"] == pass_index
            previous = records.setdefault(key, record)
            assert previous["judgment"] == record["judgment"], f"conflicting cached judgment: {key}"
    missing = set(expected) - records.keys()
    assert not missing, f"endpoint cache incomplete: missing={len(missing)}"
    return records


def logical_cells(manifest_path: Path) -> tuple[dict, list[dict], dict[str, tuple[dict, str, int]]]:
    manifest = json.loads(manifest_path.read_text())
    endpoint_tail_manifest.validate_manifest(manifest)
    assert manifest["status"] == "COMPLETE"
    expected_sides = set(endpoint_tail_manifest.HISTORICAL_SIDES) | set(endpoint_tail_manifest.CONTINUATION_SIDES)
    manifest_sides = {(cell["method"], cell["seed"], cell["sign"]) for cell in manifest["cells"]}
    assert manifest_sides == expected_sides
    judge_rows = endpoint_tail_manifest.materialize_judge_rows(manifest, endpoint_tail_manifest.cohort()[0])
    cell_by_source = {
        (cell["method"], cell["sign"], cell["raw_steered_source"]): cell
        for cell in manifest["cells"]
    }
    rows_by_cell = defaultdict(list)
    expected = {}
    for row in judge_rows:
        key = (row["method"], row["side"], row["source"])
        assert key in cell_by_source
        rows_by_cell[key].append(row)
        for order in ORDERS:
            for pass_index in PASSES:
                expected[cache_key(row, order, pass_index)] = (row, order, pass_index)
    assert len(rows_by_cell) == len(manifest["cells"])
    assert all(len(rows) == 100 for rows in rows_by_cell.values())
    return manifest, [cell_by_source[key] for key in rows_by_cell], expected


def summarize(manifest_path: Path) -> tuple[dict, list[dict], list[dict]]:
    manifest, manifest_cells, expected = logical_cells(manifest_path)
    cache = cached_records(expected)
    judge_rows = endpoint_tail_manifest.materialize_judge_rows(manifest, endpoint_tail_manifest.cohort()[0])
    rows_by_cell = defaultdict(list)
    for row in judge_rows:
        rows_by_cell[row["method"], row["side"], row["source"]].append(row)
    cells = []
    for manifest_cell in manifest_cells:
        key = manifest_cell["method"], manifest_cell["sign"], manifest_cell["raw_steered_source"]
        prompt_scores = []
        for row in rows_by_cell[key]:
            records = [cache[cache_key(row, order, pass_index)] for order in ORDERS for pass_index in PASSES]
            prompt_scores.append(tuple(mean(values) for values in zip(*(score(record) for record in records))))
        health_clean = manifest_cell["C"] <= manifest_cell["first_failure"]["C_lo"]
        assert health_clean
        steered_off_axis = mean(values[2] for values in prompt_scores)
        cells.append({
            "method": manifest_cell["method"],
            "seed": manifest_cell["seed"],
            "side": manifest_cell["sign"],
            "C": manifest_cell["C"],
            "source_kind": manifest_cell["source_kind"],
            "source_run": manifest_cell["raw_steered_artifact"],
            "raw_steered_source": manifest_cell["raw_steered_source"],
            "effect": mean(values[0] for values in prompt_scores),
            "off_axis_perturbation": abs(mean(values[1] for values in prompt_scores)),
            "steered_off_axis": steered_off_axis,
            "health_clean": health_clean,
            "accepted": health_clean and steered_off_axis <= 1.5,
        })
    selected = []
    for side, rows in defaultdict(list, {
        key: [cell for cell in cells if (cell["method"], cell["seed"], cell["side"]) == key]
        for key in {(cell["method"], cell["seed"], cell["side"]) for cell in cells}
    }).items():
        accepted = [row for row in rows if row["accepted"]]
        assert accepted, f"no judge-accepted dose: {side}"
        endpoint = max(accepted, key=lambda row: row["C"]).copy()
        endpoint["selected_reason"] = "greatest C with health_clean and mean_steered_off_axis <= 1.5"
        selected.append(endpoint)
    assert len(selected) == len(endpoint_tail_manifest.HISTORICAL_SIDES) + len(endpoint_tail_manifest.CONTINUATION_SIDES)
    return manifest, cells, sorted(selected, key=lambda row: (row["method"], row["seed"], row["side"]))


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def export(manifest_path: Path, output_dir: Path) -> None:
    manifest, cells, selected = summarize(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "cells.csv", CELL_FIELDS, cells)
    write_csv(output_dir / "selected.csv", SELECTED_FIELDS, selected)
    provenance = {
        "schema": "endpoint_tail_selection_v1",
        "manifest": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "cache": str(CACHE.relative_to(ROOT)),
        "cache_sha256": hashlib.sha256(CACHE.read_bytes()).hexdigest(),
        "judge_model": MODEL,
        "rubric": RUBRIC,
        "cohort": manifest["cohort"],
        "acceptance_rule": "health_clean and mean_steered_off_axis <= 1.5",
        "cells": len(cells),
        "selected_arms": len(selected),
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(f"ENDPOINT_TAIL_EXPORT cells={len(cells)} selected_arms={len(selected)} output={output_dir}")


def self_test() -> None:
    global CACHE
    judgment = {"on_axis_A": 2.0, "on_axis_B": -1.0, "off_axis_A": 0.5, "off_axis_B": 2.5}
    assert score({"order": "AB", "judgment": judgment}) == (-3.0, 2.0, 2.5)
    assert score({"order": "BA", "judgment": judgment}) == (3.0, -2.0, 0.5)
    rows = [
        {"C": 1.0, "health_clean": True, "steered_off_axis": 1.4, "accepted": True, "effect": 10.0},
        {"C": 2.0, "health_clean": True, "steered_off_axis": 1.3, "accepted": True, "effect": 1.0},
        {"C": 3.0, "health_clean": True, "steered_off_axis": 1.6, "accepted": False, "effect": 20.0},
    ]
    assert max((row for row in rows if row["accepted"]), key=lambda row: row["C"])["C"] == 2.0
    original_cache = CACHE
    with tempfile.TemporaryDirectory() as temporary_directory:
        CACHE = Path(temporary_directory) / "empty.jsonl"
        CACHE.touch()
        try:
            cached_records({"missing": ({}, "AB", 0)})
        except AssertionError as error:
            assert str(error) == "endpoint cache incomplete: missing=1"
        else:
            raise AssertionError("missing judge cell did not fail")
    CACHE = original_cache
    print("ENDPOINT_TAIL_EXPORT_SELF_TEST_PASS")


def main() -> None:
    args = parse_args()
    if args.self_test:
        self_test()
    else:
        export(args.manifest, args.output_dir)


if __name__ == "__main__":
    main()
