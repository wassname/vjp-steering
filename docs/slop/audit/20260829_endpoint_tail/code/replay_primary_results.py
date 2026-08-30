"""Append continuation sweep rows to the legacy primary-plot data."""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "data" / "results.csv"
CELLS = ROOT / "docs/slop/audit/20260829_endpoint_tail/data/cells.csv"
FIELDS = (
    "model", "tokenizer", "prompt_template", "data_hash", "eval_cohort", "layers",
    "batch_size", "date", "source_run", "method", "seed", "C", "side", "effect",
    "off_axis_perturbation", "admissible",
)


def main() -> None:
    with RESULTS.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("unexpected primary results schema")
        old_rows = list(reader)
    with CELLS.open(newline="") as handle:
        continuation_rows = [
            row for row in csv.DictReader(handle)
            if row["source_kind"] == "continuation_certificate"
        ]

    continuation_runs = {row["source_run"] for row in continuation_rows}
    old_rows = [row for row in old_rows if row["source_run"] not in continuation_runs]
    templates = {}
    for row in old_rows:
        if row["method"] != "random":
            templates.setdefault((row["method"], row["seed"]), row)

    added_rows = []
    for row in continuation_rows:
        template = templates[row["method"], row["seed"]]
        added_rows.append({
            **{field: template[field] for field in FIELDS[:7]},
            "date": "20260829",
            "source_run": row["source_run"],
            "method": row["method"],
            "seed": row["seed"],
            "C": row["C"],
            "side": row["side"],
            "effect": row["effect"],
            "off_axis_perturbation": row["off_axis_perturbation"],
            "admissible": row["accepted"],
        })

    with RESULTS.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(old_rows + added_rows)
    print(f"PRIMARY_RESULTS_REPLAY old_rows={len(old_rows)} continuation_rows={len(added_rows)}")


if __name__ == "__main__":
    main()
