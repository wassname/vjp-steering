import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
EXPERIMENT = ROOT / "outputs/experiments/mlp-up-left-right-formative-v1"
SOURCES = {
    "metadata": EXPERIMENT / "extraction/metadata.json",
    "verification": EXPERIMENT / "extraction/verification.json",
    "manifest": EXPERIMENT / "manifest.json",
    "dev_selected": ROOT / "data/dev/mlp-up-left-right-formative-v1/selected.json",
    "production_log": ROOT / "slop/logs/20260830_goal2/dev-production.attributed.log",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


metadata = json.loads(SOURCES["metadata"].read_text())
verification = json.loads(SOURCES["verification"].read_text())
manifest = json.loads(SOURCES["manifest"].read_text())
selected = json.loads(SOURCES["dev_selected"].read_text())
production_log = SOURCES["production_log"].read_text()

sides = {}
for side in ("+C", "-C"):
    verified = verification["sides"][side]
    endpoint = selected["sides"][side]
    sides[side] = {
        "conditioning_class": verified["conditioning_class"],
        "vector_content_sha256": verification["vector_content_sha256"][side],
        "shrinkage_weight_sha256": verified["shrinkage_weight_sha256"],
        "activation_scale_sha256": verified["activation_scale_sha256"],
        "live_coordinates": sum(verified["live_coordinates"].values()),
        "top_coordinate_energy_share": verified["top_coordinate_energy"]["top1"],
        "top_coordinate_activation_scale": verified["top_coordinate_activation_scale"],
        "top_coordinate_activation_scale_percentile": verified[
            "top_coordinate_activation_scale_percentile"
        ],
        "C_approx": manifest["boundaries"][side]["C_approx"],
        "health_probes": len(manifest["boundaries"][side]["trace"]),
        "grid": manifest["grid"][side],
        "selected_C": endpoint["selected_C"],
        "selected_effect": endpoint["effect"],
        "selected_off_axis_perturbation": endpoint["off_axis_perturbation"],
    }

artifact = {
    "status": "FORMATIVE_CALIBRATION_EVIDENCE",
    "producing_command": "uv run python scripts/scratch/audit_mlp_up_calibration.py",
    "source_paths": {name: str(path.relative_to(ROOT)) for name, path in SOURCES.items()},
    "source_sha256": {name: sha256(path) for name, path in SOURCES.items()},
    "n_pairs": verification["n_pairs"],
    "hashes_match_generation": verification["hashes_match_generation"],
    "production_extraction_log_count": len(
        re.findall(r"vjp_mlp_up_left_right_shrink target=", production_log)
    ),
    "completed_generation_cells": len(
        re.findall(r"walk:generate:.*generation 15/15", production_log)
    ),
    "stored_ray_cosine_descriptive_only": verification["stored_ray_cosine_descriptive_only"],
    "sides": sides,
}

assert artifact["n_pairs"] == 200
assert artifact["hashes_match_generation"] is True
assert artifact["production_extraction_log_count"] == 1
assert artifact["completed_generation_cells"] >= 18
assert len({entry["vector_content_sha256"] for entry in sides.values()}) == 2
assert len({entry["shrinkage_weight_sha256"] for entry in sides.values()}) == 2
assert len({entry["activation_scale_sha256"] for entry in sides.values()}) == 2
assert all(entry["health_probes"] <= 10 for entry in sides.values())
assert all(len(entry["grid"]) == 9 for entry in sides.values())
assert sides["+C"]["selected_effect"] > 0
assert sides["-C"]["selected_effect"] < 0
assert all(entry["top_coordinate_activation_scale_percentile"] > 0.99 for entry in sides.values())

print(json.dumps(artifact, indent=2))
