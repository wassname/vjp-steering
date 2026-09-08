"""Check final-prompt J-lens patch mechanics. - PI/OpenAI Codex"""

import sys
from pathlib import Path

import torch
from torch import nn
from steering_lite import Vector

sys.path.insert(0, str(Path(__file__).parents[1]))

from vjp_steering.j_lens_concept import (
    JLensConceptC,
    concept_prefill,
    concept_prefill_mask,
    final_prompt_mask,
    mask_metadata,
)


class TinyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Module()
        self.model.layers = nn.ModuleList((nn.Identity(),))

    def forward(self, hidden):
        return self.model.layers[0](hidden)


def vector(value: float) -> Vector:
    return Vector(
        JLensConceptC(layers=(0,)),
        {0: {}},
        {0: {"v": torch.tensor([[value, value, value]])}},
    )


def main() -> None:
    attention_mask = torch.tensor(((False, True, True, True), (True, True, False, False)))
    input_ids = torch.zeros_like(attention_mask, dtype=torch.long)
    mask = final_prompt_mask(attention_mask)
    expected_mask = torch.tensor(((False, False, False, True), (False, True, False, False)))
    torch.testing.assert_close(mask, expected_mask)
    metadata = mask_metadata(mask, attention_mask, "final_prompt")
    assert metadata == {
        "application_mask": "final_prompt",
        "rows": 2,
        "selected_positions_per_row": [1, 1],
        "all_rows_select_one": True,
        "selected_final_positions": True,
        "selected_padding_positions": 0,
    }
    j_lens_mask = concept_prefill_mask(None, input_ids, attention_mask, vector(1.0), "final_prompt")
    random_mask = concept_prefill_mask(None, input_ids, attention_mask, vector(-1.0), "final_prompt")
    torch.testing.assert_close(j_lens_mask, random_mask)

    model = TinyModel()
    hidden = torch.arange(24, dtype=torch.float32).reshape(2, 4, 3)
    bare = model(hidden)
    with concept_prefill(model, vector(1.0), mask, 0.0) as calls:
        zero = model(hidden)
    torch.testing.assert_close(zero, bare)
    assert calls == {0: 1}

    with concept_prefill(model, vector(1.0), mask, 0.25) as calls:
        prefill = model(hidden)
        decode = model(hidden)
    expected_prefill = hidden + expected_mask.unsqueeze(-1) * 0.25
    torch.testing.assert_close(prefill, expected_prefill)
    torch.testing.assert_close(decode, bare)
    assert calls == {0: 1}

    print("FINAL_PROMPT_PREFLIGHT_PASS rows=2 selected_per_row=1 padding=0 c0_identity=true decode_patch=false masks_identical=true")


if __name__ == "__main__":
    main()
