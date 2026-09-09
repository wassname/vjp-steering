from types import SimpleNamespace
import unittest

from vjp_steering.vjp import vjp_delta


class FakeModel:
    def __init__(self, layer_count: int):
        self.model = SimpleNamespace(layers=[None] * layer_count)

    def requires_grad_(self, _value):
        return self


class TestVjpDeltaTargetLayer(unittest.TestCase):
    def test_rejects_target_outside_actual_model_depth(self):
        with self.assertRaisesRegex(ValueError, "outside model layers"):
            vjp_delta(FakeModel(25), None, [], [], (6, 21), target_layer=33)

    def test_rejects_source_layer_at_or_after_target(self):
        with self.assertRaisesRegex(ValueError, "source layers must precede"):
            vjp_delta(FakeModel(25), None, [], [], (6, 22), target_layer=22)


if __name__ == "__main__":
    unittest.main()
