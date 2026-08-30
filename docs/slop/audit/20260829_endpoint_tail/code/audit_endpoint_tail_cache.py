"""Write exact cache coverage for every endpoint-tail coefficient without API calls."""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import endpoint_tail_manifest
import judge


manifest_path = ROOT / "outputs/endpoint_tail_manifest.json"
cache_path = ROOT / "outputs/demo_judgments/judgments.jsonl"
csv_path = ROOT / "docs/slop/audit/20260829_endpoint_tail_cache_coverage.csv"
markdown_path = ROOT / "docs/slop/audit/20260829_endpoint_tail_cache_coverage.md"

manifest = json.loads(manifest_path.read_text())
cell_by_row = {
    (cell["method"], cell["sign"], cell["raw_steered_source"]): cell
    for cell in manifest["cells"]
}
rows = endpoint_tail_manifest.judge_rows(manifest_path)
required = judge.required_cells(rows)
cached = judge.cached_keys()

coverage = defaultdict(lambda: {"total": 0, "cached": 0})
for cache_key, (row, _order, _pass_index) in required.items():
    cell = cell_by_row[row["method"], row["side"], row["source"]]
    identity = (cell["method"], cell["seed"], cell["sign"], cell["C"])
    coverage[identity]["total"] += 1
    coverage[identity]["cached"] += cache_key in cached

csv_path.parent.mkdir(parents=True, exist_ok=True)
with csv_path.open("w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=["method", "seed", "side", "C", "cached_calls", "required_calls", "complete"])
    writer.writeheader()
    for (method, seed, side, C), counts in sorted(coverage.items()):
        writer.writerow({
            "method": method,
            "seed": seed,
            "side": side,
            "C": C,
            "cached_calls": counts["cached"],
            "required_calls": counts["total"],
            "complete": counts["cached"] == counts["total"],
        })

sides = defaultdict(lambda: {"coefficients": 0, "complete": 0, "cached": 0, "required": 0})
for (method, seed, side, _C), counts in coverage.items():
    aggregate = sides[method, seed, side]
    aggregate["coefficients"] += 1
    aggregate["complete"] += counts["cached"] == counts["total"]
    aggregate["cached"] += counts["cached"]
    aggregate["required"] += counts["total"]

complete_sides = sum(counts["complete"] == counts["coefficients"] for counts in sides.values())
lines = [
    "# Endpoint-tail judge cache coverage",
    "",
    "This report reads the existing JSONL cache only. It makes no API call.",
    "",
    f"- cache: [`judgments.jsonl`](../../../outputs/demo_judgments/judgments.jsonl)",
    f"- manifest: [`endpoint_tail_manifest.json`](../../../outputs/endpoint_tail_manifest.json)",
    f"- coefficient detail: [`20260829_endpoint_tail_cache_coverage.csv`](20260829_endpoint_tail_cache_coverage.csv)",
    "",
    f"The manifest requires {len(required):,} unique judge calls. The cache has {sum(counts['cached'] for counts in coverage.values()):,}. {complete_sides} of {len(sides)} sides have every required call.",
    "",
    "| method | seed | side | complete C / all C | cached / required calls |",
    "|---|---:|:---:|---:|---:|",
]
for (method, seed, side), counts in sorted(sides.items()):
    lines.append(
        f"| {method} | {seed} | {side} | {counts['complete']} / {counts['coefficients']} | "
        f"{counts['cached']} / {counts['required']} |"
    )
markdown_path.write_text("\n".join(lines) + "\n")

print(json.dumps({
    "required_calls": len(required),
    "cached_calls": sum(counts["cached"] for counts in coverage.values()),
    "complete_sides": complete_sides,
    "all_sides": len(sides),
    "csv": str(csv_path),
    "markdown": str(markdown_path),
}, sort_keys=True))
