import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
EXPERIMENT_ID = "mlp-up-left-right-formative-v1"
PATHS = {
    "selected": ROOT / f"data/formative/{EXPERIMENT_ID}/selected.json",
    "results": ROOT / f"data/formative/{EXPERIMENT_ID}/results.csv",
    "scenarios": ROOT / f"data/formative/{EXPERIMENT_ID}/judged_scenarios.csv",
    "manifest": ROOT / f"outputs/experiments/{EXPERIMENT_ID}/manifest.json",
    "report": ROOT / f"results/formative/{EXPERIMENT_ID}/index.md",
    "plot": ROOT / f"results/formative/{EXPERIMENT_ID}/plot.png",
    "full_log": ROOT / "slop/logs/20260830_goal3/full-completion.log",
    "minus_judge_log": ROOT / "slop/logs/20260830_goal3/full-minus-judge.log",
    "primary_report": ROOT / "results/index.md",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


selected = json.loads(PATHS["selected"].read_text())
manifest = json.loads(PATHS["manifest"].read_text())
result_lines = PATHS["results"].read_text().splitlines()
scenario_lines = PATHS["scenarios"].read_text().splitlines()
full_log = PATHS["full_log"].read_text()
judge_log = PATHS["minus_judge_log"].read_text()
report = PATHS["report"].read_text()
primary_report = PATHS["primary_report"].read_text()

rows = [
    {"C": float(row["C"]), "side": row["side"], "effect": float(row["effect"]),
     "off_axis_perturbation": float(row["off_axis_perturbation"]),
     "health_admissible": row["admissible"] == "True"}
    for row in csv.DictReader(result_lines)
]

artifact = {
    "status": "FORMATIVE_FULL_ENDPOINT_AUDIT",
    "producing_command": "uv run python scripts/scratch/audit_mlp_up_full.py",
    "source_sha256": {name: sha256(path) for name, path in PATHS.items()},
    "profile": {"questions": 100, "orders": ["AB", "BA"], "passes": 1},
    "gpu_cells_reused": "profile=full cells=5 reused=true" in full_log,
    "minus_judge_complete": "JUDGE_COMPLETE required=200 missing=0" in judge_log,
    "full_command_exit_zero": "EXIT_STATUS: 0" in full_log,
    "scenario_rows": len(scenario_lines) - 1,
    "results": rows,
    "selection": selected["sides"],
    "report_states_unconfirmed_plus": "No accepted endpoint was confirmed for +C." in report,
    "report_rejected_count": 2 if "| 3 | 2 |" in report else None,
    "primary_published_row": next(line for line in primary_report.splitlines() if "vjp_mlp_up_shrink" in line),
}

plus = [row for row in rows if row["side"] == "+C"]
minus = [row for row in rows if row["side"] == "-C"]
assert len(rows) == 3 and len(plus) == 2 and len(minus) == 1
assert all(row["health_admissible"] and row["effect"] < 0 for row in plus)
assert minus[0]["health_admissible"] and minus[0]["effect"] < 0
assert artifact["selection"]["+C"]["status"] == "no_accepted_endpoint"
assert artifact["selection"]["-C"]["status"] == "accepted"
assert artifact["gpu_cells_reused"] and artifact["minus_judge_complete"] and artifact["full_command_exit_zero"]
assert artifact["scenario_rows"] == 300
assert artifact["report_states_unconfirmed_plus"] and artifact["report_rejected_count"] == 2

print(json.dumps(artifact, indent=2))
