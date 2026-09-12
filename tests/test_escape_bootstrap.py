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

if __name__ == "__main__":
    unittest.main()
