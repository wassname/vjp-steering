import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from vjp_steering.results import calibrated_random_rungs, plot


sys.path.insert(0, str(Path("scripts").resolve()))
SPEC = importlib.util.spec_from_file_location("render_dev_comparison", Path("scripts/render_dev_comparison.py"))
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


def provenance():
    return {
        "cohort": {"cohort_sha256": "cohort", "scenario_ids": ["s1"]},
        "generation": {"model": "m", "dtype": "d", "max_length": 1, "max_new_tokens": 2},
        "shared_bare": {"selected_records_canonical_sha256": "expected", "source_experiment": "shared"},
    }


def write_experiment(root: Path, bare: list[dict]) -> None:
    experiment = root / "outputs/experiments/x"
    experiment.mkdir(parents=True)
    (experiment / "bare.jsonl").write_text("".join(json.dumps(row) + "\n" for row in bare))
    (experiment / "manifest.json").write_text(json.dumps({
        "method": "random", "profiles": {"dev": {"status": "DEV", "cohort_size": 15, "generated": True}},
        "config": {"model": "m", "dtype": "d", "max_length": 1, "max_new_tokens": 2}, "cohort_sha256": "cohort",
        "bare": {"path": "bare.jsonl", "reused_from": "shared"},
    }))


class TestCalibratedRandomRegion(unittest.TestCase):
    def test_uses_calibration_rank_without_relabeling_actual_coefficients(self):
        seeds = set(range(5))
        rows = []
        for seed in seeds:
            for side, coefficients in (("+C", [0.11 + seed / 100, 0.31 + seed / 100]), ("-C", [0.04 + seed / 100, 0.18 + seed / 100, 0.42 + seed / 100])):
                for normalized_dose_id, coefficient in enumerate(coefficients):
                    rows.append({
                        "method": "random", "seed": seed, "side": side, "C": coefficient,
                        "normalized_dose_id": normalized_dose_id,
                        "effect": (1 if side == "+C" else -1) * (normalized_dose_id + 1) / 10,
                        "off_axis_perturbation": coefficient, "admissible": True,
                    })
        rows.append({"method": "random", "seed": 2, "side": "+C", "C": 0.99, "normalized_dose_id": None, "effect": 0.8, "off_axis_perturbation": 0.99, "admissible": True})
        rungs = calibrated_random_rungs(rows, seeds)
        self.assertEqual([rung["rung"] for rung in rungs["+C"]], [0, 1])
        self.assertEqual([rung["rung"] for rung in rungs["-C"]], [0, 1, 2])
        self.assertEqual([point["C"] for point in rungs["+C"][0]["points"]], [0.11, 0.12, 0.13, 0.14, 0.15])
        self.assertEqual({point["seed"] for point in rungs["-C"][2]["points"]}, seeds)
        rows = [row for row in rows if not (row["seed"] == 4 and row["side"] == "+C" and row.get("normalized_dose_id") == 1)]
        next(row for row in rows if row["seed"] == 3 and row["side"] == "-C" and row.get("normalized_dose_id") == 1)["admissible"] = False
        rungs = calibrated_random_rungs(rows, seeds)
        self.assertEqual([rung["rung"] for rung in rungs["+C"]], [0])
        self.assertEqual([rung["rung"] for rung in rungs["-C"]], [0, 2])
        figure = plot(rows, ("random",), {"random": seeds}, random_region="calibrated_rung")
        self.assertTrue(any(trace.fill == "toself" and len(trace.x) > 2 for trace in figure.data))
        trace = next(trace for trace in figure.data if trace.name == "random measured DEV doses")
        self.assertEqual(len(trace.x), sum(row["admissible"] for row in rows))


class TestDevComparisonProvenance(unittest.TestCase):
    def test_rejects_mismatched_shared_bare(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(renderer, "ROOT", Path(directory)):
            write_experiment(Path(directory), [{"scenario": "s1", "text": "wrong"}])
            with self.assertRaisesRegex(ValueError, "bare response mismatch"):
                renderer.verify_experiment("x", "random", 0, provenance(), {})

    def test_rejects_missing_ba_order(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(renderer, "ROOT", Path(directory)):
            bare = [{"scenario": "s1", "text": "bare"}]
            contract = provenance()
            contract["shared_bare"]["selected_records_canonical_sha256"] = renderer.canonical_sha256(bare)
            write_experiment(Path(directory), bare)
            with patch.object(renderer, "experiment_rows", return_value=[{}]), patch.object(
                renderer, "required_cells", return_value={"only": ({"vignette": "s1", "side": "+C"}, "AB", 0)}
            ):
                with self.assertRaisesRegex(ValueError, "incomplete AB/BA scenario coverage"):
                    renderer.verify_experiment("x", "random", 0, contract, {"only": {}})


if __name__ == "__main__":
    unittest.main()
