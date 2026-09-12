"""Regression checks for the saved-judgment analysis. Author: PI/OpenAI."""

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

PATH = Path(__file__).resolve().parents[1] / "slop/scripts/20260909_escape_bootstrap.py"
spec = importlib.util.spec_from_file_location("escape_bootstrap", PATH)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def cell(values):
    return {str(i): {"AB": pair[0], "BA": pair[1]} for i, pair in enumerate(values)}


class EscapeBootstrapTests(unittest.TestCase):
    def test_orders_are_averaged_before_sampling_scenarios(self):
        candidate = cell([((-1.0, -1.0), (1.0, 1.0))] * 15)
        comparator = cell([((0.0, 0.0), (0.0, 0.0))] * 15)
        for damage in (False, True):
            point, lower, upper, differences = analysis.boot_margin(candidate, comparator, damage, b=100)
            self.assertEqual((point, lower, upper), (0.0, 0.0, 0.0))
            np.testing.assert_array_equal(differences, np.zeros(15))

    def test_observed_point_does_not_depend_on_bootstrap_draws(self):
        candidate = cell([((x, 0.0), (x, 0.0)) for x in (1.0, 3.0, -1.0)])
        comparator = cell([((0.0, 0.0), (0.0, 0.0))] * 3)
        with patch.object(analysis, "RNG") as rng:
            rng.integers.return_value = np.array([[1, 1, 1]] * 4)
            point, lower, upper, differences = analysis.boot_margin(candidate, comparator, b=4)
        self.assertEqual(point, 1.0)
        self.assertEqual((lower, upper), (3.0, 3.0))
        np.testing.assert_array_equal(differences, [1.0, 3.0, -1.0])

    def test_damage_is_absolute_order_mean_not_mean_absolute(self):
        candidate = cell([((0.0, -1.0), (0.0, 3.0))] * 3)
        comparator = cell([((0.0, -0.5), (0.0, -0.5))] * 3)
        self.assertEqual(analysis.boot_margin(candidate, comparator, damage=True, b=20)[:3], (0.5, 0.5, 0.5))

    def test_scenario_keys_must_match(self):
        candidate = cell([((0.0, 0.0), (0.0, 0.0))])
        with self.assertRaises(AssertionError):
            analysis.boot_margin(candidate, {}, b=2)

    def test_historical_loader_pins_rubric_and_handles_three_score_fields(self):
        rows = [{"side": "-C", "coefficient": 1.0, "vignette": str(i)} for i in range(15)]
        records = {f"{i}:{order}": {"order": order, "judgment": {
            "on_axis_A": 1.0 if order == "AB" else 3.0,
            "on_axis_B": 3.0 if order == "AB" else 1.0,
            "off_axis_A": 0.5, "off_axis_B": 0.5,
        }} for i in range(15) for order in ("AB", "BA")}

        def key(row, order, pass_index, *, rubric):
            self.assertEqual(rubric, "results-demo-perresponse-syco-v7")
            self.assertEqual(pass_index, 0)
            return f"{row['vignette']}:{order}"

        with patch.object(analysis, "experiment_rows", return_value=rows), \
                patch.object(analysis, "cache_key", side_effect=key), \
                patch.object(analysis, "cache_records", return_value=records) as cache:
            loaded = analysis.load_cells([("fixture", "-C", 1.0)])
        cache.assert_called_once_with(set(records), rubric="results-demo-perresponse-syco-v7")
        self.assertEqual(loaded["fixture", "-C", 1.0]["0"]["AB"], (-2.0, 0.0))
        self.assertEqual(loaded["fixture", "-C", 1.0]["0"]["BA"], (-2.0, 0.0))


if __name__ == "__main__":
    unittest.main()
