"""One deterministic check for VJP reductions, steering hooks, and repository scope."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import torch
from torch import nn

from . import steer
from .vjp import _batch_gradients, _target_mean, _valid_mask, vjp_delta


ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILES = {
    "nbs/demo.py",
    "src/jsteer/__init__.py",
    "src/jsteer/results.py",
    "src/jsteer/smoke.py",
    "src/jsteer/vjp.py",
}


class Batch(dict):
    def to(self, device):
        return Batch({key: value.to(device) for key, value in self.items()})


class Tokenizer:
    values = {
        "p0": [1, 2, 3, 4],
        "p1": [1, 5, 6],
        "n0": [7, 2, 8, 4],
        "n1": [7, 5, 9],
    }

    def __call__(self, prompts, **_kwargs):
        width = max(len(self.values[prompt]) for prompt in prompts)
        ids = [self.values[prompt] + [0] * (width - len(self.values[prompt])) for prompt in prompts]
        mask = [[1] * len(self.values[prompt]) + [0] * (width - len(self.values[prompt])) for prompt in prompts]
        return Batch(input_ids=torch.tensor(ids), attention_mask=torch.tensor(mask))


class Block(nn.Module):
    def __init__(self, width: int):
        super().__init__()
        self.linear = nn.Linear(width, width)

    def forward(self, hidden):
        return hidden + torch.tanh(self.linear(hidden))


class Model(nn.Module):
    def __init__(self):
        super().__init__()
        torch.manual_seed(0)
        self.embedding = nn.Embedding(10, 5)
        self.model = nn.Module()
        self.model.layers = nn.ModuleList(Block(5) for _ in range(5))
        self.config = SimpleNamespace(num_hidden_layers=5)

    def forward(self, input_ids, attention_mask):
        hidden = self.embedding(input_ids)
        for block in self.model.layers:
            hidden = block(hidden)
        return hidden


def _manual_states(model, input_ids, graph_root=None):
    hidden = model.embedding(input_ids)
    states = []
    for layer, block in enumerate(model.model.layers):
        hidden = block(hidden)
        if layer == graph_root:
            hidden = hidden.detach().requires_grad_(True)
        states.append(hidden)
    return states


def _manual_target_mean(model, tokenizer, prompts, target):
    encoded = tokenizer(prompts)
    states = _manual_states(model, encoded["input_ids"])
    last = encoded["attention_mask"].sum(1) - 1
    return states[target][torch.arange(len(prompts)), last].mean(0)


def _manual_gradients(model, tokenizer, prompts, layers, target, cotangent, skip_first):
    encoded = tokenizer(prompts)
    valid = _valid_mask(encoded["attention_mask"], skip_first)
    states = _manual_states(model, encoded["input_ids"], min(layers))
    gradients = torch.autograd.grad(
        states[target],
        [states[layer] for layer in layers],
        grad_outputs=cotangent.view(1, 1, -1) * valid.unsqueeze(-1),
    )
    return dict(zip(layers, gradients, strict=True)), valid


def _source_inventory() -> None:
    files = set(
        subprocess.check_output(
            ["git", "ls-files", "*.py"], cwd=ROOT, text=True
        ).splitlines()
    )
    if files != SOURCE_FILES:
        raise AssertionError(f"source inventory differs: {sorted(files ^ SOURCE_FILES)}")
    text = "\n".join((ROOT / path).read_text() for path in files)
    forbidden_text = (
        "../" + "j-steer-dev",
        "edit" + "able =",
        "pa" + "th =",
        "def " + "mean_diff",
        "def " + "pca",
    )
    for forbidden in forbidden_text:
        if forbidden in text:
            raise AssertionError(f"forbidden source text: {forbidden}")


def main() -> None:
    _source_inventory()
    model = Model().eval().requires_grad_(False)
    tokenizer = Tokenizer()
    positive, negative = ["p0", "p1"], ["n0", "n1"]
    layers, target, skip_first = (0, 1), 3, 1

    cotangent = _target_mean(model, tokenizer, positive, target, 2, 16) - _target_mean(
        model, tokenizer, negative, target, 2, 16
    )
    expected_cotangent = _manual_target_mean(model, tokenizer, positive, target) - _manual_target_mean(
        model, tokenizer, negative, target
    )
    torch.testing.assert_close(cotangent, expected_cotangent)

    class_means = {}
    for name, prompts in (("positive", positive), ("negative", negative)):
        actual, valid = _batch_gradients(
            model, tokenizer, prompts, layers, target, cotangent, skip_first, 16
        )
        expected, expected_valid = _manual_gradients(
            model, tokenizer, prompts, layers, target, cotangent, skip_first
        )
        torch.testing.assert_close(valid, expected_valid)
        for layer in layers:
            torch.testing.assert_close(actual[layer], expected[layer])
        counts = valid.sum(1, keepdim=True).float()
        class_means[name] = {
            layer: (actual[layer] * valid.unsqueeze(-1)).sum(1).div(counts).mean(0)
            for layer in layers
        }

    vector = vjp_delta(
        model,
        tokenizer,
        positive,
        negative,
        layers,
        target_layer=target,
        batch_size=2,
        max_length=16,
        skip_first=skip_first,
    )
    for layer in layers:
        expected = class_means["positive"][layer] - class_means["negative"][layer]
        expected = expected / expected.norm()
        torch.testing.assert_close(vector.stacked[layer]["v"][0], expected)

    encoded = tokenizer(["p0"])
    bare = model(**encoded)
    with steer(model, vector, C=0.2):
        steered = model(**encoded)
    restored = model(**encoded)
    if torch.equal(bare, steered):
        raise AssertionError("steering hook changed no activations")
    torch.testing.assert_close(bare, restored)
    print("SMOKE_PASS: token gradients, reductions, sign, hook, detach, and source inventory")


if __name__ == "__main__":
    main()
