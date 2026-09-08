"""PI/OpenAI Codex: fixed v3 closed-rule source-state diagnostic, not benchmark evaluation."""
import argparse
import hashlib
import json
import math
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import time

SCRIPT_ROOT = Path("/repo/scripts") if Path("/repo/scripts").is_dir() else Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SCRIPT_ROOT), str(SCRIPT_ROOT / "scratch")]

import torch

import j_lens_gap_clamp as gap

ROOT = Path("slop/logs/20260908_j_lens_task_validity_source_stage")
CORPUS = Path("slop/logs/20260908_j_lens_task_validity_corpus/v3/corpus.jsonl")
FREEZE = CORPUS.parent / "freeze.json"
CORPUS_SHA = "b4ef9920b02959e1204c0baa681fc5d402909af65ee676d120145468324f527e"
LAYER = 17
K = 25
MAX_NEW_TOKENS = 4
MODEL = "Qwen/Qwen3.5-4B"
REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
TOKENIZER_SHA = "0ef9d0923a6d6d8342cae2674ade04c07f12fd060a55f170b8cc9b89f9a822d4"
LENS_SHA = "1f9a8f8fd593f0ffec1a9640993257ca4560f8ae3e5602315643d5cc6818534e"
PROTECTED = [Path("results/plot.png"), Path("results/index.md"), Path("results/index.html"), Path("data/results.csv"), Path("scripts/judge.py")]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tensor_sha(tensor):
    x = tensor.detach().float().cpu().contiguous()
    return hashlib.sha256(str((str(x.dtype), tuple(x.shape))).encode() + x.numpy().tobytes()).hexdigest()


def load_rows():
    assert sha(CORPUS) == CORPUS_SHA
    freeze = json.loads(FREEZE.read_text())
    assert freeze["corpus_sha256"] == CORPUS_SHA and freeze["version"] == 3
    rows = [json.loads(line) for line in CORPUS.read_text().splitlines()]
    assert len(rows) == 384 and len({row["id"] for row in rows}) == 384
    return rows


def render(tokenizer, row):
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": row["prompt"]}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )


def semantic(row, text):
    letter = text.strip()
    if letter not in {"A", "B"}:
        return None
    action = row["options"]["AB".index(letter)]
    valid_action, invalid_action = row["actions_valid_invalid"]
    assert action in {valid_action, invalid_action}
    return "valid" if action == valid_action else "invalid"


def expected(row):
    return "valid" if row["valid"] else "invalid"


def source_gate(rows, records):
    by_id = {record["id"]: record for record in records}
    assert set(by_id) == {row["id"] for row in rows}
    cells = {"split": {}, "split_consumer": {}, "split_cue": {}}
    selectors = {
        "split": lambda row: row["split"],
        "split_consumer": lambda row: (row["split"], row["consumer"]),
        "split_cue": lambda row: (row["split"], row["cue_family"]),
    }
    for name, selector in selectors.items():
        groups = {}
        for row in rows:
            key = str(selector(row))
            groups.setdefault(key, []).append(semantic(row, by_id[row["id"]]["text"]) == expected(row))
        cells[name] = {key: sum(values) / len(values) for key, values in groups.items()}
    cases = {}
    for row in rows:
        cases.setdefault(row["semantic_case_id"], []).append(row)
    strict = {}
    for key, group in cases.items():
        assert len(group) == 4
        strict[key] = all(semantic(row, by_id[row["id"]]["text"]) == expected(row) for row in group)
    minimum = min(value for groups in cells.values() for value in groups.values())
    return {"pass": minimum >= 0.90 and all(strict.values()), "minimum_accuracy": minimum,
            "strict_semantic_cases": {"passed": sum(strict.values()), "total": len(strict)}, "cells": cells,
            "strict_case_failures": [key for key, value in strict.items() if not value]}


def decoder_gate(rows, clean, direction):
    train = [row for row in rows if row["split"] == "train"]
    states = {record["id"]: torch.tensor(record["h17"], dtype=torch.float64) for record in clean}
    unit = direction.double() / direction.double().norm()
    means = {label: torch.stack([states[row["id"]] for row in train if row["valid"] == label]) @ unit for label in (False, True)}
    midpoint = float((means[False].mean() + means[True].mean()) / 2)
    invalid_high = bool(means[False].mean() > means[True].mean())
    values = []
    for row in rows:
        if row["split"] != "withheld_source":
            continue
        score = float(states[row["id"]] @ unit)
        prediction = (score > midpoint) if invalid_high else (score < midpoint)
        values.append((row, prediction == (not row["valid"])))
    groups = {}
    for keyfn in (lambda row: row["cue_family"], lambda row: row["consumer"]):
        result = {}
        for row, hit in values:
            result.setdefault(keyfn(row), []).append(hit)
        groups[str(len(groups))] = {key: sum(v) / len(v) for key, v in result.items()}
    return {"pass": all(value >= .75 for group in groups.values() for value in group.values()), "midpoint": midpoint,
            "invalid_high": invalid_high, "groups": groups}


def construct(model, rows, clean):
    lens, checkpoint = gap.concept._load_j_lens(model, [LAYER], None)
    assert sha(lens) == LENS_SHA
    raw = model.lm_head.weight.detach().float() @ checkpoint["J"][LAYER].float().to(model.device)
    dictionary = raw / raw.norm(dim=1, keepdim=True)
    assert torch.isfinite(dictionary).all() and torch.allclose(dictionary.norm(dim=1), torch.ones(len(dictionary), device=model.device), atol=1e-5)
    h = {record["id"]: torch.tensor(record["h17"], device=model.device) for record in clean}
    train = [row for row in rows if row["split"] == "train"]
    all_mean = torch.stack([h[row["id"]] for row in train]).mean(0)
    probes, components, details = {}, {}, {}
    for label, name in ((False, "invalid"), (True, "valid")):
        probe = torch.stack([h[row["id"]] for row in train if row["valid"] == label]).mean(0) - all_mean
        weights, component, selected, errors = gap.concept.gradient_pursuit(probe, dictionary, K)
        support = weights.nonzero().flatten()
        reconstruction = weights[support].double() @ dictionary[support].double()
        torch.testing.assert_close(component.double(), reconstruction, atol=1e-5, rtol=1e-4)
        probes[name], components[name] = probe, component
        details[name] = {"probe_norm": float(probe.norm()), "component_norm": float(component.norm()),
            "selected_ids": selected.tolist(), "nonzero_ids": support.tolist(), "weights": weights[support].tolist(),
            "reconstruction_max_error": float((component.double() - reconstruction).abs().max()), "errors": errors}
    d = probes["invalid"] - probes["valid"]
    g = components["invalid"] - components["valid"]
    r = d - g
    directions = {"full": d, "gp": g, "remainder": r}
    for name, vector in directions.items():
        assert torch.isfinite(vector).all() and vector.norm() > 0, name
    random = torch.randn(d.shape, generator=torch.Generator(device="cpu").manual_seed(20260908), dtype=torch.float32, device="cpu").to(model.device)
    random -= (random @ (g / g.norm())) * (g / g.norm())
    random /= random.norm()
    assert abs(float(random @ (g / g.norm()))) < 1e-5
    result = {"dictionary_rows": len(dictionary), "dictionary": "unit rows lm_head @ J17; vocabulary order unchanged", "lens_sha256": sha(lens),
              "k": K, "probes": details, "directions": {name: {"norm": float(vector.norm()), "unit": (vector / vector.norm()).float().cpu().tolist()} for name, vector in directions.items()},
              "random": {"seed": 20260908, "unit": random.float().cpu().tolist(), "orthogonal_to_gp_abs_dot": abs(float(random @ (g / g.norm())))}}
    return {name: vector / vector.norm() for name, vector in directions.items()}, random, result


@contextmanager
def final_prefill_patch(model, input_length, patch, measurement):
    handles = []
    state = {}
    def layer_hook(_module, _inputs, output):
        hidden = output[0] if isinstance(output, tuple) else output
        if hidden.shape[:2] == (1, input_length):
            assert "prefill" not in state
            state["prefill"] = 1
            before = hidden.detach().clone()
            after = before if patch is None else patch(before)
            assert torch.equal(after[:, :-1], before[:, :-1])
            measurement["h17"] = before[0, -1].float().cpu().tolist()
            measurement["h17_sha256"] = tensor_sha(before[0, -1])
            measurement["prefill_nonfinal_exact"] = True
            if patch is not None:
                delta = after[0, -1].float() - before[0, -1].float()
                measurement["actual_update_norm"] = float(delta.norm())
                measurement["actual_update"] = delta.cpu().tolist()
            state["after"] = after[0, -1].detach().clone()
            return after
        assert hidden.shape[:2] == (1, 1)
        state["decode_calls"] = state.get("decode_calls", 0) + 1
        return None
    def next_block(_module, args, kwargs):
        hidden = kwargs.get("hidden_states", args[0] if args else None)
        if hidden.shape[:2] == (1, input_length):
            assert torch.equal(hidden[0, -1], state["after"])
            measurement["next_block_prefill_exact"] = True
    try:
        handles.append(model.model.layers[LAYER].register_forward_hook(layer_hook))
        handles.append(model.model.layers[LAYER + 1].register_forward_pre_hook(next_block, with_kwargs=True))
        yield state
    finally:
        for handle in handles:
            handle.remove()
        assert not model.model.layers[LAYER]._forward_hooks and not model.model.layers[LAYER + 1]._forward_pre_hooks


@torch.inference_mode()
def generate(model, tokenizer, row, patch=None):
    rendered = render(tokenizer, row)
    encoded = tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to(model.device)
    assert encoded.input_ids.shape[0] == 1 and bool((encoded.attention_mask == 1).all())
    measurement = {}
    with final_prefill_patch(model, encoded.input_ids.shape[1], patch, measurement) as state:
        output = model.generate(**encoded, do_sample=False, temperature=None, top_p=None, top_k=None,
            pad_token_id=tokenizer.eos_token_id, max_new_tokens=MAX_NEW_TOKENS, use_cache=True,
            return_dict_in_generate=True, output_logits=True)
    ids = output.sequences[0, encoded.input_ids.shape[1]:].tolist()
    assert state.get("prefill") == 1 and measurement["next_block_prefill_exact"]
    record = {"id": row["id"], "semantic_case_id": row["semantic_case_id"], "split": row["split"], "consumer": row["consumer"],
              "cue_family": row["cue_family"], "valid": row["valid"], "expected_semantic_action": expected(row), "rendered": rendered,
              "input_ids": encoded.input_ids[0].tolist(), "generated_ids": ids, "text": tokenizer.decode(ids, skip_special_tokens=True).strip(),
              "first_logits_sha256": tensor_sha(output.logits[0][0]), "measurement": measurement}
    return record


def patch_for(row, mode, units, random_unit, train_means):
    target_label = not row["valid"]
    if mode == "identity":
        return None, {"mode": mode}
    if mode == "random":
        gp = units["gp"]
        source = train_means["gp"][row["valid"]]
        target = train_means["gp"][target_label]
        unit, requested = random_unit, None
    else:
        unit = units[mode]
        source = train_means[mode][row["valid"]]
        target = train_means[mode][target_label]
        requested = None
    def patch(hidden):
        coordinate = hidden[0, -1].float() @ (gp if mode == "random" else unit)
        delta = target - coordinate
        if mode == "random":
            requested = delta
        after = hidden.clone()
        after[0, -1] = hidden[0, -1] + (unit * delta).to(hidden.dtype)
        return after
    return patch, {"mode": mode, "source_mean": float(source), "target_mean": float(target), "requested_from": "gp" if mode == "random" else mode}


def causal_gate(rows, intervention):
    withheld = [row for row in rows if row["split"] == "withheld_source"]
    by_mode = {}
    for mode in ("gp", "random"):
        values = []
        records = {record["id"]: record for record in intervention[mode]}
        for row in withheld:
            values.append((row, semantic(row, records[row["id"]]["text"]) == ("invalid" if row["valid"] else "valid")))
        groups = {}
        for selector in (lambda row: row["valid"], lambda row: row["cue_family"], lambda row: row["consumer"]):
            result = {}
            for row, value in values:
                result.setdefault(str(selector(row)), []).append(value)
            groups[str(len(groups))] = {key: sum(items) / len(items) for key, items in result.items()}
        by_mode[mode] = {"overall": sum(value for _, value in values) / len(values), "groups": groups,
                         "minimum_group": min(value for group in groups.values() for value in group.values())}
    gp, random = by_mode["gp"], by_mode["random"]
    return {"gp": gp, "random": random, "pass": gp["minimum_group"] >= .50 and gp["overall"] - random["overall"] >= .20}


def self_test():
    from transformers import Qwen3_5ForCausalLM, Qwen3_5TextConfig
    torch.manual_seed(20260908)
    config = Qwen3_5TextConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=19,
        num_attention_heads=2, num_key_value_heads=1, head_dim=16, layer_types=["linear_attention"] * 18 + ["full_attention"],
        linear_num_key_heads=2, linear_num_value_heads=2, linear_key_head_dim=8, linear_value_head_dim=8,
        pad_token_id=0, eos_token_id=63)
    model = Qwen3_5ForCausalLM(config).eval().bfloat16()
    with torch.no_grad():
        model.lm_head.weight.zero_()
    model.config.eos_token_id = None
    model.generation_config.eos_token_id = None
    model.generation_config.forced_eos_token_id = None
    row = {"id": "fixture", "semantic_case_id": "fixture", "split": "train", "consumer": "routing", "cue_family": "seal_match", "valid": True,
           "actions_valid_invalid": ["gate", "bypass"], "options": ["gate", "bypass"], "prompt": "fixture"}
    class Tokenizer:
        eos_token_id = 63
        def apply_chat_template(self, _messages, **_kwargs): return "fixture"
        def __call__(self, _text, **_kwargs):
            from transformers import BatchEncoding
            return BatchEncoding({"input_ids": torch.tensor([[1, 2, 3, 4]]), "attention_mask": torch.ones(1, 4, dtype=torch.long)})
        def decode(self, ids, **_kwargs): return "A" if ids else ""
    tokenizer = Tokenizer()
    clean = generate(model, tokenizer, row)
    def mutate(hidden):
        after = hidden.clone(); after[0, -1, 0] += 1; return after
    changed = generate(model, tokenizer, row, mutate)
    assert clean["measurement"]["prefill_nonfinal_exact"] and clean["measurement"]["next_block_prefill_exact"]
    assert changed["measurement"]["actual_update_norm"] > 0 and changed["measurement"].get("h17_sha256") == clean["measurement"]["h17_sha256"]
    assert len(clean["generated_ids"]) == MAX_NEW_TOKENS
    assert semantic(row, "A") == "valid" and semantic(row, "B") == "invalid" and semantic(row, "C") is None
    print("TASK_VALIDITY_RUNNER_FIXTURE_PASS", json.dumps({"generated_tokens": len(clean["generated_ids"]), "layer17_decode_hook_calls": clean["measurement"].get("decode_calls", 0), "hook_cleanup": True, "prefill_only": True, "semantic_mapping": True}), flush=True)


def preflight():
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    rows = load_rows()
    snapshot = Path(snapshot_download(MODEL, revision=REVISION, local_files_only=True))
    assert snapshot.name == REVISION
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    source_tokenizer_sha = gap.concept.tokenizer_content_hash(tokenizer)
    assert source_tokenizer_sha == TOKENIZER_SHA
    tokenizer.pad_token = tokenizer.eos_token
    generation_tokenizer_sha = gap.concept.tokenizer_content_hash(tokenizer)
    rendered = [render(tokenizer, row) for row in rows]
    ids = [tokenizer(item, add_special_tokens=False).input_ids for item in rendered]
    duplicate_groups = {}
    for row, item in zip(rows, rendered, strict=True):
        duplicate_groups.setdefault(item, []).append(row)
    assert all(ids)
    assert all(len({expected(row) for row in group}) == 1 for group in duplicate_groups.values())
    result = {"corpus_sha256": sha(CORPUS), "model": MODEL, "revision": REVISION, "snapshot": str(snapshot),
              "source_tokenizer_sha256": source_tokenizer_sha, "generation_tokenizer_sha256": generation_tokenizer_sha, "rendered_inputs": len(rendered),
              "unique_rendered_inputs": len(duplicate_groups), "duplicate_rendered_inputs": sum(len(group) - 1 for group in duplicate_groups.values()),
              "input_id_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(), "protected_sha256": {str(path): sha(path) for path in PROTECTED}}
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "preflight.json").write_text(json.dumps(result, indent=2) + "\n")
    print("TASK_VALIDITY_TOKENIZER_PREFLIGHT_PASS", json.dumps(result), flush=True)


def run(args):
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    assert not args.output.exists()
    rows = load_rows()
    preflight_data = json.loads((ROOT / "preflight.json").read_text())
    assert preflight_data["corpus_sha256"] == CORPUS_SHA and preflight_data["source_tokenizer_sha256"] == TOKENIZER_SHA
    snapshot = Path(snapshot_download(MODEL, revision=REVISION))
    assert snapshot.name == REVISION
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    assert gap.concept.tokenizer_content_hash(tokenizer) == TOKENIZER_SHA
    tokenizer.pad_token = tokenizer.eos_token
    assert gap.concept.tokenizer_content_hash(tokenizer) == preflight_data["generation_tokenizer_sha256"]
    model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.bfloat16).to("cuda").eval()
    started = time.monotonic()
    data = {"schema": "task_validity_source_stage_v1", "source_revision": args.source_revision, "implementation_sha256": sha(__file__),
        "corpus_sha256": CORPUS_SHA, "model": MODEL, "model_revision": REVISION, "tokenizer_sha256": TOKENIZER_SHA,
        "lens_sha256": LENS_SHA, "settings": {"layer": LAYER, "k": K, "batch": 1, "max_new_tokens": MAX_NEW_TOKENS, "one_shot_final_prefill": True, "retries": 0},
        "protected_sha256": {str(path): sha(path) for path in PROTECTED}, "clean": [], "interventions": {}, "benchmark_released": False}
    for index, row in enumerate(rows):
        record = generate(model, tokenizer, row)
        data["clean"].append(record)
        args.output.write_text(json.dumps(data) + "\n")
        print("CLEAN_RESPONSE", json.dumps({key: record[key] for key in ("id", "split", "expected_semantic_action", "text")}), flush=True)
    data["clean_gate"] = source_gate(rows, data["clean"])
    print("CLEAN_GATE", json.dumps(data["clean_gate"]), flush=True)
    if not data["clean_gate"]["pass"]:
        data["decision"] = "CLEAN_GATE_BLOCKED_NO_INTERVENTION"
        data["runtime"] = {"seconds": time.monotonic() - started, "gpu": torch.cuda.get_device_name(), "peak_memory_bytes": torch.cuda.max_memory_allocated()}
        args.output.write_text(json.dumps(data) + "\n")
        return
    units, random_unit, construction = construct(model, rows, data["clean"])
    data["construction"] = construction
    data["decoder_gates"] = {name: decoder_gate(rows, data["clean"], unit) for name, unit in units.items() if name in {"full", "gp"}}
    if not all(gate["pass"] for gate in data["decoder_gates"].values()):
        data["decision"] = "DECODER_GATE_BLOCKED_NO_INTERVENTION"
        data["runtime"] = {"seconds": time.monotonic() - started, "gpu": torch.cuda.get_device_name(), "peak_memory_bytes": torch.cuda.max_memory_allocated()}
        args.output.write_text(json.dumps(data) + "\n")
        return
    train = [row for row in rows if row["split"] == "train"]
    h = {record["id"]: torch.tensor(record["h17"], device=model.device) for record in data["clean"]}
    means = {name: {label: float((torch.stack([h[row["id"]] for row in train if row["valid"] == label]) @ unit).mean()) for label in (False, True)} for name, unit in units.items()}
    withheld = [row for row in rows if row["split"] == "withheld_source"]
    for mode in ("identity", "full", "gp", "remainder", "random"):
        data["interventions"][mode] = []
        for row in withheld:
            patch, requested = patch_for(row, mode, units, random_unit, means)
            record = generate(model, tokenizer, row, patch)
            record["requested"] = requested
            if mode == "identity":
                clean = next(item for item in data["clean"] if item["id"] == row["id"])
                assert record["generated_ids"] == clean["generated_ids"] and record["first_logits_sha256"] == clean["first_logits_sha256"] and record["measurement"]["h17_sha256"] == clean["measurement"]["h17_sha256"]
                record["identity_exact"] = True
            data["interventions"][mode].append(record)
            args.output.write_text(json.dumps(data) + "\n")
            print("INTERVENTION_RESPONSE", json.dumps({"mode": mode, "id": row["id"], "text": record["text"]}), flush=True)
    gp_by_id = {record["id"]: record for record in data["interventions"]["gp"]}
    random_by_id = {record["id"]: record for record in data["interventions"]["random"]}
    for row in withheld:
        gp_norm = gp_by_id[row["id"]]["measurement"]["actual_update_norm"]
        random_norm = random_by_id[row["id"]]["measurement"]["actual_update_norm"]
        assert abs(gp_norm - random_norm) / max(gp_norm, 1e-30) <= .05
    data["causal_gate"] = causal_gate(rows, data["interventions"])
    data["decision"] = "SOURCE_STAGE_COMPLETE_REVIEW_REQUIRED"
    data["runtime"] = {"seconds": time.monotonic() - started, "gpu": torch.cuda.get_device_name(), "peak_memory_bytes": torch.cuda.max_memory_allocated(), "torch": torch.__version__}
    args.output.write_text(json.dumps(data) + "\n")
    print("TASK_VALIDITY_SOURCE_COMPLETE", json.dumps({"decision": data["decision"], "clean_gate": data["clean_gate"]["pass"], "causal_gate": data["causal_gate"]["pass"], "runtime": data["runtime"]}), flush=True)


if __name__ != "__main__":
    import modal
    from run_modal import REPO, cache, j_lens_diagnostic_image, source_revision
    source_image = j_lens_diagnostic_image.add_local_file(str(CORPUS), "/repo/" + str(CORPUS)).add_local_file(str(FREEZE), "/repo/" + str(FREEZE)).add_local_file(str(ROOT / "preflight.json"), "/repo/" + str(ROOT / "preflight.json"))
    app = modal.App("jsteer-task-validity-source-stage", image=source_image)
    @app.function(gpu="H100", volumes={"/cache": cache}, timeout=900, max_containers=1, retries=0)
    def remote(revision):
        destination = Path("/cache/outputs/audits/20260908_task_validity_source_stage/generation.json")
        if destination.exists():
            raise FileExistsError(destination)
        try:
            subprocess.run([sys.executable, "scripts/scratch/j_lens_task_validity_source_stage.py", "--output", str(destination), "--source-revision", revision], cwd="/repo", check=True)
            return destination.read_text()
        finally:
            cache.commit()
    @app.local_entrypoint()
    def launch():
        output = ROOT / "generation.json"
        assert not output.exists()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(remote.remote(source_revision()))
        print("TASK_VALIDITY_SOURCE_DOWNLOADED", output, flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "generation.json")
    parser.add_argument("--source-revision", default="unknown")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.preflight:
        preflight()
    else:
        run(args)
