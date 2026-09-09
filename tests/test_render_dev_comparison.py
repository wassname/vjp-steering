import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


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
