import importlib.util
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch


sys.path.insert(0, str(Path("scripts").resolve()))
SPEC = importlib.util.spec_from_file_location("experiment", Path("scripts/experiment.py"))
experiment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(experiment)


class TestRandomExtraction(unittest.TestCase):
    def test_uses_persona_extraction_prompts_before_training_random_vector(self):
        args = SimpleNamespace(
            method="random",
            layers="6,7",
            dtype="float32",
            seed=3,
            extract_batch_size=4,
            max_length=99,
        )
        vector = object()
        with patch.object(experiment, "extraction_prompts", return_value=(["positive"], ["negative"])) as prompts, patch.object(
            experiment.Vector, "train", return_value=vector
        ) as train:
            vectors, metadata, n_pairs, sample_id = experiment.extract_vectors(args, object(), object())
        prompts.assert_called_once()
        self.assertIs(train.call_args.args[2], prompts.return_value[0])
        self.assertIs(train.call_args.args[3], prompts.return_value[1])
        self.assertEqual(vectors, {"+C": vector, "-C": vector})
        self.assertEqual(metadata["source_layers"], [6, 7])
        self.assertEqual(n_pairs, 0)
        self.assertEqual(sample_id, "random_seed:3")


if __name__ == "__main__":
    unittest.main()
