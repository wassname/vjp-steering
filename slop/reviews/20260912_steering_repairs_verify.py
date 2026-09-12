"""CPU-only verification and source inspection. -- PI/OpenAI"""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import unittest

sys.path[:0] = [str(Path("scripts").resolve()), str(Path("tests").resolve())]
import experiment
from transformers import AutoTokenizer
from steering_lite.data import make_persona_pairs
from steering_lite.data.personas import load_suffixes

print("SHOULD: production cache, orientation, normalization and dispatch discriminators reject the reviewed defects", flush=True)
suite = unittest.TestSuite()
for name in ("test_steering_repairs", "test_vjp_delta_target_layer", "test_random_extraction"):
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(importlib.import_module(name)))
for name in ("test_j_lens_injection", "test_j_lens_unit_direction"):
    module = importlib.import_module(name)
    for key, function in vars(module).items():
        if key.startswith("test_") and callable(function):
            suite.addTest(unittest.FunctionTestCase(function, description=f"{name}.{key}"))
module = importlib.import_module("test_j_lens_vendor_readout_regression")
suite.addTest(unittest.FunctionTestCase(module.test_production_readout_with_nonuniform_weight))
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)

print("SHOULD: supported thinking=False retains 200 source pairs while removing reopened thinking tags", flush=True)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3.5-4B", local_files_only=True)
args = importlib.import_module("test_steering_repairs").args_for(seed=0)
before = make_persona_pairs(tokenizer, n_pairs=args.n_pairs, thinking=True,
                            persona_pairs=experiment.walk.PERSONAS, template=experiment.walk.PERSONA_TEMPLATE, seed=args.seed)
after = experiment.extraction_prompts(args, tokenizer)
entries = load_suffixes(thinking=False)
assert len(entries) == 200 and len(after[0]) == len(after[1]) == 200
print("source_pool_count", len(entries), "unique_user_messages", len({row["user_msg"] for row in entries}))
for name, pairs in (("before", before), ("after", after)):
    digest = hashlib.sha256(json.dumps(pairs, separators=(",", ":")).encode()).hexdigest()
    print(name, "pairs", len(pairs[0]), "source_sha256", digest)
    for side, prompts in zip(("positive", "negative"), pairs):
        ids = tokenizer(prompts[0], add_special_tokens=False)["input_ids"]
        print(name, side, "full_prompt", repr(prompts[0]))
        print(name, side, "token_ids", ids)
        print(name, side, "decoded", repr(tokenizer.decode(ids)))
        print(name, side, "thinking_counts", prompts[0].count("<think>"), prompts[0].count("</think>"))
assert before != after
assert all(prompt.count("<think>") <= 1 and prompt.count("<think>") == prompt.count("</think>") for prompts in after for prompt in prompts)
print("PASS source-format repair changes recorded prompt identity; no model loaded or generation performed", flush=True)
