"""Production-path CPU repair discriminators. -- PI/OpenAI"""

import copy
import importlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch
from steering_lite import MeanDiffC, Vector

sys.path.insert(0, str(Path("scripts").resolve()))
experiment = importlib.import_module("experiment")
vjp = importlib.import_module("vjp_steering.vjp")


def args_for(method="mean_diff", **changes):
    with patch.object(sys, "argv", ["experiment", method, "--dev", "--experiment-id", "repair-test"]):
        args = experiment.parse_args()
    for key, value in changes.items():
        setattr(args, key, value)
    return args


class Encoded(dict):
    def to(self, device):
        return Encoded({key: value.to(device) for key, value in self.items()})


class Tokenizer:
    def __call__(self, prompts, **kwargs):
        ids = torch.tensor([[int(prompt)] * 4 for prompt in prompts])
        return Encoded(input_ids=ids, attention_mask=torch.ones_like(ids))


class Square(torch.nn.Module):
    def forward(self, hidden):
        return hidden.square()


class TinyModel(torch.nn.Module):
    def __init__(self, square=True):
        super().__init__()
        self.embedding = torch.nn.Embedding(4, 2)
        with torch.no_grad():
            self.embedding.weight.copy_(torch.tensor([[0., 0.], [1., 2.], [2., 1.], [3., 3.]]))
        self.model = torch.nn.Module()
        self.model.layers = torch.nn.ModuleList([torch.nn.Identity(), Square() if square else torch.nn.Identity()])

    def forward(self, input_ids, attention_mask):
        hidden = self.embedding(input_ids)
        for layer in self.model.layers:
            hidden = layer(hidden)
        return hidden


class TestVjpRepairs(unittest.TestCase):
    def extract(self, model, positive, negative):
        return vjp.vjp_delta(model, Tokenizer(), positive, negative, (0,), target_layer=1,
                             batch_size=1, max_length=4, skip_first=0).stacked[0]["v"]

    def test_production_label_reversal(self):
        model = TinyModel()
        forward = self.extract(model, ["3"], ["1"])
        reverse = self.extract(model, ["1"], ["3"])
        self.assertTrue(torch.allclose(forward, -reverse))
        self.assertAlmostEqual(forward.norm().item(), 1., places=6)
        self.assertGreater(float(forward @ torch.tensor([2., 1.])), 0)

    def test_constant_jacobian_rejects_zero(self):
        with self.assertRaisesRegex(ValueError, "zero direction"):
            self.extract(TinyModel(False), ["2"], ["1"])

    def test_orthogonal_orientation_rejects_ambiguous_axis(self):
        with self.assertRaisesRegex(ValueError, "zero chosen/rejected orientation"):
            self.extract(TinyModel(), ["2"], ["1"])

    def test_nonfinite_raw_direction_rejected(self):
        model = TinyModel()
        with torch.no_grad():
            model.embedding.weight[3, 0] = torch.inf
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            self.extract(model, ["3"], ["1"])


class TestExtractionIdentity(unittest.TestCase):
    def make_cache(self, root, args):
        vector = Vector(MeanDiffC(layers=(0,), dtype=torch.float32), {}, {0: {"v": torch.tensor([[1., 0.]])}})
        with patch.object(experiment, "extract_vectors", return_value=({"+C": vector, "-C": vector}, {"source_layers": [0]}, 2, "test")):
            return experiment.load_or_extract(args, root, None, None)[1]

    def test_load_or_extract_rejects_one_changed_input_at_a_time(self):
        changes = dict(layers="1", n_pairs=3, seed=1, max_length=22, extract_batch_size=2,
                       model="different", dtype="float32")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = args_for()
            self.make_cache(root, args)
            before = {path: path.read_bytes() for path in root.rglob("*") if path.is_file()}
            with patch.object(experiment, "extract_vectors", side_effect=AssertionError("must not re-extract")):
                experiment.load_or_extract(args, root, None, None)
                for key, value in changes.items():
                    changed = copy.copy(args)
                    setattr(changed, key, value)
                    with self.subTest(key=key), self.assertRaisesRegex(ValueError, "request mismatch"):
                        experiment.load_or_extract(changed, root, None, None)
            self.assertEqual(before, {path: path.read_bytes() for path in root.rglob("*") if path.is_file()})

    def test_target_and_lens_and_concepts_are_in_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            lens = Path(directory) / "lens.pt"
            lens.write_bytes(b"lens version one")
            for method, changes in (
                ("vjp_delta", dict(target_layer=2)),
                ("j_lens_injection", dict(injection_plus_concept="other", injection_minus_concept="another")),
            ):
                args = args_for(method, target_layer=1 if method == "vjp_delta" else None,
                                lens_file=lens if method == "j_lens_injection" else None,
                                injection_plus_concept="flattering" if method == "j_lens_injection" else "",
                                injection_minus_concept="abrasive" if method == "j_lens_injection" else "")
                metadata = dict(method=method, model=args.model, dtype=args.dtype,
                                extraction_request=experiment.extraction_request(args))
                experiment.validate_extraction_identity(args, metadata)
                for key, value in changes.items():
                    changed = copy.copy(args)
                    setattr(changed, key, value)
                    with self.subTest(key=key), self.assertRaisesRegex(ValueError, "request mismatch"):
                        experiment.validate_extraction_identity(changed, metadata)
                if method == "j_lens_injection":
                    lens.write_bytes(b"lens version two")
                    with self.assertRaisesRegex(ValueError, "lens_sha256"):
                        experiment.validate_extraction_identity(args, metadata)

    def test_legacy_identity_fails_without_modifying_cache(self):
        args = args_for()
        with self.assertRaisesRegex(ValueError, "lacks extraction_request"):
            experiment.validate_extraction_identity(args, dict(method=args.method, model=args.model, dtype=args.dtype))

    def test_completed_profile_checks_identity_before_shortcut(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = args_for()
            metadata = self.make_cache(root, args)
            manifest = dict(method=args.method, profiles={"dev": {}}, extraction=metadata)
            manifest_path = root / "manifest.json"
            experiment.atomic_json(manifest_path, manifest)
            with patch.object(experiment, "experiment_dir", return_value=root), patch.object(
                experiment, "manifest_path", return_value=manifest_path
            ), patch.object(experiment, "completed_profile_cell_count", return_value=2), patch.object(
                experiment, "load_model", side_effect=AssertionError("must not load model")
            ):
                experiment.gpu_stage(args)
                args.seed += 1
                with self.assertRaisesRegex(ValueError, "request mismatch"):
                    experiment.gpu_stage(args)

    def test_invalid_vectors_never_saved(self):
        for value in (0., float("nan"), float("inf")):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                vector = Vector(MeanDiffC(layers=(0,)), {}, {0: {"v": torch.tensor([[value, 0.]])}})
                with patch.object(experiment, "extract_vectors", return_value=({"+C": vector, "-C": vector}, {"source_layers": [0]}, 1, "invalid")):
                    with self.assertRaisesRegex(ValueError, "zero|nonfinite"):
                        experiment.load_or_extract(args_for(), root, None, None)
                self.assertFalse((root / "extraction").exists())


class TestExtractionDispatch(unittest.TestCase):
    def test_explicit_missing_lens_reaches_production_extractor(self):
        for method in ("j_lens_swap", "j_lens_unit_direction", "j_lens_injection"):
            args = args_for(method, lens_file=Path("/explicit/missing/lens.pt"), layers="16")
            with self.subTest(method=method), patch.object(experiment.walk, "resolve_layers", return_value=tuple(range(25))):
                with self.assertRaisesRegex(FileNotFoundError, "/explicit/missing/lens.pt"):
                    tokenizer = lambda *args, **kwargs: SimpleNamespace(input_ids=[0])
                    experiment.extract_vectors(args, None, tokenizer)

    def test_mlp_target_forwarded_and_incompatible_layers_rejected(self):
        model = SimpleNamespace(model=SimpleNamespace(layers=[None] * 8))
        for method in experiment.EXTRACTORS:
            args = args_for(method, target_layer=5, layers="0,1,2,3,4")
            def extractor(*positional, **kwargs):
                self.assertEqual(kwargs["target_layer"], 5)
                return {}, {}
            with patch.dict(experiment.EXTRACTORS, {method: extractor}), patch.object(
                experiment, "extraction_prompts", return_value=(["p"], ["n"])
            ):
                experiment.extract_vectors(args, model, None)
                args.layers = "3"
                with self.assertRaisesRegex(ValueError, "all layers preceding"):
                    experiment.extract_vectors(args, model, None)

    def test_unsupported_flags_fail(self):
        for changes in (dict(lens_file=Path("unused")), dict(target_layer=2)):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "not used"):
                experiment.extract_vectors(args_for(**changes), None, None)

    def test_persona_source_uses_supported_nonthinking_and_seed(self):
        tokenizer = lambda prompts, **kwargs: {"input_ids": [[1] for _ in prompts]}
        args = args_for(seed=42)
        with patch.object(experiment, "make_persona_pairs", return_value=(["p"], ["n"])) as pairs:
            experiment.extraction_prompts(args, tokenizer)
            self.assertIs(pairs.call_args.kwargs["thinking"], False)
            self.assertEqual(pairs.call_args.kwargs["seed"], 42)
        for prompt in ("<think></think><think>reopened", "<think>reasoning</think>"):
            with patch.object(experiment, "make_persona_pairs", return_value=([prompt], ["n"])):
                with self.assertRaisesRegex(ValueError, "thinking|non-thinking"):
                    experiment.extraction_prompts(args, tokenizer)

    def test_j_word_rejects_subtokens_and_zero_lens(self):
        with tempfile.TemporaryDirectory() as directory:
            lens = Path(directory) / "lens.pt"
            torch.save(dict(J={0: torch.zeros(2, 2)}, n_prompts=1, source_layers=[0], d_model=2), lens)
            model = SimpleNamespace(config=SimpleNamespace(hidden_size=2), lm_head=SimpleNamespace(weight=torch.eye(2)))
            for token_ids, error in (([0, 1], "single-token"), ([0], "zero direction")):
                tokenizer = lambda *args, **kwargs: SimpleNamespace(input_ids=token_ids)
                with self.assertRaisesRegex(ValueError, error):
                    vjp.j_word(model, tokenizer, (0,), lens_file=lens)


if __name__ == "__main__":
    unittest.main(verbosity=2)
