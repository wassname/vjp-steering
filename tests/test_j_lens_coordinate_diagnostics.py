import unittest

import torch
from steering_lite import Vector

from vjp_steering.vjp import JLensCoordinateSwapC, j_lens_coordinate_prefill


class TestJLensCoordinateDiagnostics(unittest.TestCase):
    def test_alpha_one_exchanges_coordinates_and_preserves_residual(self):
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.model = torch.nn.Module()
                self.model.layers = torch.nn.ModuleList([torch.nn.Identity()])

        basis = torch.tensor([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        dual = torch.linalg.pinv(basis).T
        vector = Vector(
            JLensCoordinateSwapC(layers=(0,), coeff=1.0, source_token_id=1, target_token_id=2),
            {0: {"basis": basis, "dual": dual}}, {0: {}},
        )
        model = Model()
        hidden = torch.tensor([[[2.0, -3.0, 7.0], [5.0, 11.0, 13.0]]])
        diagnostics = {}
        with j_lens_coordinate_prefill(model, vector, torch.ones((1, 2), dtype=torch.bool), diagnostics) as calls:
            edited = model.model.layers[0](hidden)
        self.assertEqual(calls, {0: 1})
        torch.testing.assert_close(edited, torch.tensor([[[-3.0, 2.0, 7.0], [11.0, 5.0, 13.0]]]))
        self.assertEqual(diagnostics[0]["selected_positions"], 2)
        self.assertLess(diagnostics[0]["coordinate_exchange_max_abs_error"], 1e-6)
        self.assertLess(diagnostics[0]["orthogonal_residual_max_abs_error"], 1e-6)


if __name__ == "__main__":
    unittest.main()
