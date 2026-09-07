"""One-layer minus donor transfer diagnostic, not a J-lens benchmark. PI/OpenAI Codex."""
import argparse
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import time

# PI/OpenAI Codex: Modal imports from /root; dependencies are mounted under /repo.
SCRIPT_ROOT = Path("/repo/scripts") if Path("/repo/scripts").is_dir() else Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT))
sys.path.insert(0, str(SCRIPT_ROOT / "scratch"))
import torch
import j_lens_gap_clamp as gap

LAYER = 17
CONDITIONS = ("bare", "direct_minus", "identity_minus", "donor_identity_minus", "full_minus", "projected_minus", "gap_minus")
ROOT = Path("slop/logs/20260907_j_lens_transfer_probe")


def replacement(h, donor, basis, dual, mode, target_gap):
    """h/donor [1,d]; project the donor-minus-recipient delta, not the whole state."""
    if mode in ("bare", "direct_minus"):
        return h
    if mode in ("identity_minus", "donor_identity_minus", "full_minus"):
        return donor.to(h)
    c = h.float() @ dual.T
    if mode == "projected_minus":
        desired = donor.float() @ dual.T
    elif mode == "gap_minus":
        midpoint = c.sum(-1) / 2
        desired = torch.stack((midpoint + target_gap / 2, midpoint - target_gap / 2), -1)
    else:
        raise ValueError(mode)
    return h + ((desired - c) @ basis).to(h)


@contextmanager
def observed_prefill(model, vector, mode, donor, target_gap, result, layer=LAYER):
    """Independent downstream pre-hook checks what the next block actually receives."""
    handles, captures, calls = [], {}, {}
    patch = {}
    basis, dual = (vector.shared[layer][k].to(model.device) for k in ("basis", "dual"))
    def output_hook(index):
        def hook(_module, _inputs, output):
            h = output[0] if isinstance(output, tuple) else output
            calls[index] = calls.get(index, 0) + 1
            if index == layer:
                before = h.detach().clone()
                actual = replacement(h[:, -1], donor, basis, dual, mode, target_gap)
                if mode not in ("bare", "direct_minus"):
                    h = h.clone()
                    h[:, -1] = actual
                delta = h.float() - before.float()
                patch.update({"all_position_patch_norms": delta[0].norm(dim=-1).tolist(),
                              "before": before[0, -1].float().cpu().tolist(),
                              "after": h[0, -1].float().cpu().tolist(),
                              "coordinates_before": (before[0, -1].float() @ dual.T).tolist(),
                              "coordinates_after": (h[0, -1].float() @ dual.T).tolist()})
                assert torch.equal(h[:, :-1], before[:, :-1])
            captures[index] = h[0, -1].detach().float().cpu()
            output_handles[index].remove()
            return (h, *output[1:]) if isinstance(output, tuple) else h
        return hook
    def next_input(_module, inputs, kwargs):
        h = kwargs.get("hidden_states", inputs[0] if inputs else None)
        assert h is not None
        received = h[0, -1].float().cpu()
        assert torch.equal(received, captures[layer])
        patch["next_block_input_exact"] = True
        next_handle.remove()
    output_handles = {}
    try:
        for index in range(layer, len(model.model.layers)):
            handle = model.model.layers[index].register_forward_hook(output_hook(index))
            output_handles[index] = handle
            handles.append(handle)
        next_handle = model.model.layers[layer + 1].register_forward_pre_hook(next_input, with_kwargs=True)
        handles.append(next_handle)
        yield captures
        assert all(n == 1 for n in calls.values()) and len(calls) == len(model.model.layers)-layer
        result.update({"patch": patch, "hook_calls": calls, "final_states": {str(k): v.tolist() for k, v in captures.items()}})
    finally:
        for handle in handles:
            handle.remove()


@contextmanager
def persistent_gap(model, vector, target_gap, coefficient, measurements, layer=LAYER):
    """PI/OpenAI Codex: patch current final position on every cached forward, including prefill."""
    basis, dual = (vector.shared[layer][key].to(model.device) for key in ("basis", "dual"))
    inserted = None
    def patch(_module, _inputs, output):
        nonlocal inserted
        h = output[0] if isinstance(output, tuple) else output
        before = h.detach().clone()
        if coefficient:
            h = h.clone()
            h[:, -1] = replacement(h[:, -1], None, basis, dual, "gap_minus", target_gap)
        actual = h[0, -1].float() @ dual.T
        delta = h.float()-before.float()
        assert torch.equal(h[:, :-1], before[:, :-1])
        error = float(abs(actual[0]-actual[1]-target_gap))
        if coefficient:
            assert error < .05, error
        else:
            assert torch.equal(h, before)
        measurements.append({"call": len(measurements), "sequence_length": h.shape[1],
            "position_in_forward": h.shape[1]-1, "coordinates_before": (before[0, -1].float() @ dual.T).tolist(),
            "coordinates_after": actual.tolist(), "target_gap": target_gap, "target_gap_error": error,
            "all_position_patch_norms": delta[0].norm(dim=-1).tolist(), "next_block_input_exact": False})
        inserted = h[:, -1].detach().clone()
        return (h, *output[1:]) if isinstance(output, tuple) else h
    def check(_module, inputs, kwargs):
        h = kwargs.get("hidden_states", inputs[0] if inputs else None)
        assert torch.equal(h[:, -1], inserted)
        measurements[-1]["next_block_input_exact"] = True
    handle = model.model.layers[layer].register_forward_hook(patch)
    next_handle = model.model.layers[layer+1].register_forward_pre_hook(check, with_kwargs=True)
    try:
        yield
    finally:
        handle.remove()
        next_handle.remove()


def self_test():
    from types import SimpleNamespace
    from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM
    import export
    for order, values in (("AB", (1., 3.)), ("BA", (3., 1.))):
        score = {"on_axis_A": values[0], "on_axis_B": values[1], "off_axis_A": .2, "off_axis_B": .4}
        result = {"order": order, "judgment": score}
        assert export.signed_axis_effect("-C", [export.score_cell(result)]) == gap.mapped_effect(score, order, "-C") == -2.
    torch.manual_seed(7)
    b = torch.randn(2, 32)
    b = b / b.norm(dim=-1, keepdim=True)
    d = torch.linalg.pinv(b).T
    h, donor = torch.randn(1, 32), torch.randn(1, 32)
    for dtype, atol in ((torch.float32, 1e-5), (torch.bfloat16, .03)):
        hd, dd = h.to(dtype), donor.to(dtype)
        for mode in CONDITIONS:
            actual = replacement(hd, dd, b, d, mode, -3.)
            if mode in ("bare", "direct_minus"):
                assert torch.equal(actual, hd)
            elif mode in ("identity_minus", "donor_identity_minus", "full_minus"):
                assert torch.equal(actual, dd)
            elif mode == "projected_minus":
                independent = hd.double() + ((dd.double()-hd.double()) @ torch.linalg.solve(b.double() @ b.double().T, b.double()).T) @ b.double()
                torch.testing.assert_close(actual.double(), independent, atol=atol, rtol=atol)
                torch.testing.assert_close(actual.float() @ d.T, dd.float() @ d.T, atol=atol, rtol=atol)
            else:
                coords = actual.float() @ d.T
                torch.testing.assert_close(coords[:, 0]-coords[:, 1], torch.tensor([-3.]), atol=atol, rtol=atol)
    config = Qwen3_5TextConfig(vocab_size=64, hidden_size=32, intermediate_size=64, num_hidden_layers=3,
        num_attention_heads=2, num_key_value_heads=1, head_dim=16, layer_types=["linear_attention", "full_attention", "linear_attention"],
        linear_num_key_heads=2, linear_num_value_heads=2, linear_key_head_dim=8, linear_value_head_dim=8,
        pad_token_id=0, eos_token_id=63)
    model = Qwen3_5ForCausalLM(config).eval()
    vector = SimpleNamespace(shared={1: {"basis": b, "dual": d}})
    inp = {"input_ids": torch.tensor([[1, 2, 3, 4]]), "attention_mask": torch.ones(1, 4, dtype=torch.long)}
    def generate(mode, state=None):
        record = {}
        with torch.inference_mode(), observed_prefill(model, vector, mode, state, -3., record, layer=1):
            ids = model.generate(**inp, max_new_tokens=3, do_sample=False, use_cache=True)
        return ids, record
    base_ids, base = generate("bare")
    state = torch.tensor(base["patch"]["after"]).unsqueeze(0)
    ident_ids, ident = generate("identity_minus", state)
    assert torch.equal(base_ids, ident_ids) and not any(ident["patch"]["all_position_patch_norms"])
    for mode in ("full_minus", "projected_minus", "gap_minus"):
        _, record = generate(mode, donor)
        assert record["patch"]["next_block_input_exact"]
        assert record["patch"]["all_position_patch_norms"][:-1] == [0.]*3
    for coefficient in (0., 1.):
        measurements = []
        with torch.inference_mode(), persistent_gap(model, vector, -3., coefficient, measurements, layer=1):
            ids = model.generate(**inp, max_new_tokens=3, do_sample=False, use_cache=True)
        assert len(measurements) == ids.shape[1]-inp["input_ids"].shape[1]
        assert [m["sequence_length"] for m in measurements] == [4]+[1]*(len(measurements)-1)
        assert all(m["next_block_input_exact"] for m in measurements)
        if coefficient == 0:
            assert torch.equal(ids, base_ids)
            assert all(not any(m["all_position_patch_norms"]) for m in measurements)
    after_ids, _ = generate("bare")
    assert torch.equal(after_ids, base_ids)
    print("TRANSFER_CPU_PASS Gram_FP32_BF16=true tiny_Qwen_cached_generate=true identity_ids_exact=true next_block_exact=true one_shot=true", flush=True)
    print("PERSISTENCE_CPU_PASS every_cached_forward=true alpha0_exact=true target_gap=true cleanup_exact=true", flush=True)


def run(args):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from huggingface_hub import snapshot_download
    started = time.monotonic()
    assert not args.output.exists()
    vectors, meta, gaps, source_hash = gap.load_source(args.source_root)
    vector = vectors["-C"]
    snapshot = Path(snapshot_download(gap.MODEL, revision=gap.REVISION))
    assert snapshot.name == gap.REVISION
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.bfloat16).to("cuda").eval()
    rows, cohort_hash = gap.walk.read_cohort(15)
    rows = [next(r for r in rows if r["scenario"] == s) for s in gap.SCENARIOS]
    persona = meta["spec"]["negative_instruction"].removeprefix("Answer as someone who is ").removesuffix(".")
    data = {"schema": "v16_transfer_probe_v1", "source_revision": args.source_revision,
        "implementation_sha256": gap.sha(__file__), "argv": sys.argv, "model": gap.MODEL,
        "model_revision": gap.REVISION, "snapshot": str(snapshot), "model_config_sha256": gap.sha(snapshot/"config.json"),
        "model_index_sha256": gap.sha(snapshot/"model.safetensors.index.json"),
        "source_metadata_sha256": source_hash, "source_recorded_model_revision": meta["model_revision"],
        "vector_content_sha256": meta["vector_content_sha256"], "cohort_sha256": cohort_hash,
        "settings": {"layer": LAYER, "alpha": 1., "dtype": "bfloat16", "batch": 1, "max_new_tokens": 512, "use_cache": True},
        "source_gap": gaps["-C"][LAYER], "conditions": CONDITIONS, "records": [],
        "scope": "three selected diagnostic questions, not DEV15 or final J-lens", "cache_caveat": "Recipient retains its own prefill history/cache and positions; full donor null is inconclusive."}
    print("TRANSFER_CONFIG", json.dumps({k:v for k,v in data.items() if k != "records"}), flush=True)
    print("SHOULD: identities exact tokens/states; nonfinal patch norms0; next block sees inserted state exactly; projected matches donor coordinates; full matches donor residual. Null full transfer does not prove source defect.", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for row in rows:
        records, logits = {}, {}
        for condition in CONDITIONS:
            direct = condition in ("direct_minus", "donor_identity_minus")
            rendered = gap.walk.generation_inputs(tokenizer, [row], persona if direct else None)[0]
            encoded = tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to(model.device)
            donor = None
            if condition not in ("bare", "direct_minus"):
                source = records["bare" if condition == "identity_minus" else "direct_minus"]
                donor = torch.tensor(source["patch"]["after"], device=model.device, dtype=torch.bfloat16).unsqueeze(0)
            record = {"scenario": row["scenario"], "prompt": row["prompt"], "condition": condition,
                      "rendered": rendered, "input_ids": encoded.input_ids[0].tolist()}
            with torch.inference_mode(), observed_prefill(model, vector, condition, donor, gaps["-C"][LAYER], record):
                generated = model.generate(**encoded, do_sample=False, temperature=None, top_p=None, top_k=None,
                    pad_token_id=tokenizer.eos_token_id, max_new_tokens=512, use_cache=True,
                    return_dict_in_generate=True, output_logits=True)
            ids = generated.sequences[0, encoded.input_ids.shape[1]:].tolist()
            first_logits = generated.logits[0][0].float().cpu()
            logits[condition] = first_logits
            text = tokenizer.decode(ids, skip_special_tokens=True).strip()
            record.update({"generated_ids": ids, "text": text, "health": gap.walk.health(tokenizer, [text])})
            if condition.endswith("identity_minus"):
                baseline = "bare" if condition == "identity_minus" else "direct_minus"
                assert ids == records[baseline]["generated_ids"]
                assert torch.equal(first_logits, logits[baseline])
                assert record["final_states"] == records[baseline]["final_states"]
                assert not any(record["patch"]["all_position_patch_norms"])
                record["identity_exact"] = True
            if condition in ("full_minus", "projected_minus"):
                desired = torch.tensor(records["direct_minus"]["patch"]["coordinates_after"])
                actual = torch.tensor(record["patch"]["coordinates_after"])
                record["donor_coordinate_error_max"] = float((desired-actual).abs().max())
                assert record["donor_coordinate_error_max"] < .05
            if condition == "full_minus":
                assert record["patch"]["after"] == records["direct_minus"]["patch"]["after"]
            if condition == "gap_minus":
                c = record["patch"]["coordinates_after"]
                record["target_gap_error"] = abs(c[0]-c[1]-gaps["-C"][LAYER])
                assert record["target_gap_error"] < .05
            records[condition] = record
            data["records"].append(record)
            args.output.write_text(json.dumps(data, indent=2)+"\n")
            print("TRANSFER_RESPONSE", json.dumps({k:v for k,v in record.items() if k not in ("final_states", "patch", "input_ids", "generated_ids")}, ensure_ascii=False), flush=True)
            del generated
        for condition, record in records.items():
            downstream = {}
            for key, state in record["final_states"].items():
                h = torch.tensor(state)
                bare, direct_state = (torch.tensor(records[c]["final_states"][key]) for c in ("bare", "direct_minus"))
                delta = direct_state-bare
                downstream[key] = {"distance_to_bare": float((h-bare).norm()), "distance_to_donor": float((h-direct_state).norm()),
                    "donor_bare_distance": float(delta.norm()), "donor_delta_coefficient": float((h-bare) @ delta / delta.square().sum().clamp_min(1e-12))}
                if int(key) in vector.shared:
                    dual = vector.shared[int(key)]["dual"].cpu()
                    downstream[key]["coordinates"] = (h @ dual.T).tolist()
            record["downstream"] = downstream
            logp = logits[condition].log_softmax(-1)
            record["first_token"] = {"id": int(logits[condition].argmax()), "top20_ids": logits[condition].topk(20).indices.tolist()}
            for control in ("bare", "direct_minus"):
                q = logits[control].log_softmax(-1)
                record["first_token"]["kl_from_"+control] = float((q.exp()*(q-logp)).sum())
            print("TRANSFER_MEASUREMENT", json.dumps({"scenario": row["scenario"], "condition": condition,
                "patch_norm": record["patch"]["all_position_patch_norms"][-1], "next_block_exact": record["patch"]["next_block_input_exact"],
                "downstream": downstream, "first_token": record["first_token"]}), flush=True)
    data["runtime"] = {"seconds": time.monotonic()-started, "gpu": torch.cuda.get_device_name(),
        "peak_memory_bytes": torch.cuda.max_memory_allocated(), "torch": torch.__version__}
    args.output.write_text(json.dumps(data, indent=2)+"\n")
    print("TRANSFER_COMPLETE", json.dumps(data["runtime"]), flush=True)


def run_persistence(args):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from huggingface_hub import snapshot_download
    started = time.monotonic()
    assert not args.output.exists()
    reference_path = args.output.parent.parent / "generation.json"
    reference = json.loads(reference_path.read_text())
    assert gap.sha(reference_path) == "b69925310ad2b2744e107442b1d283569d106365fda73c5a1ec98f857bf169e9"
    vectors, meta, gaps, source_hash = gap.load_source(args.source_root)
    assert reference["source_metadata_sha256"] == source_hash and reference["model_revision"] == gap.REVISION
    snapshot = Path(snapshot_download(gap.MODEL, revision=gap.REVISION))
    assert snapshot.name == gap.REVISION
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.bfloat16).to("cuda").eval()
    data = {"schema": "v16_decode_persistence_v1", "source_revision": args.source_revision, "implementation_sha256": gap.sha(__file__),
        "reference_sha256": gap.sha(reference_path), "reference_source_revision": reference["source_revision"],
        "model_revision": gap.REVISION, "source_metadata_sha256": source_hash, "settings": reference["settings"],
        "schedule": "current final position on every cached forward,prefill and decode", "records": [], "argv": sys.argv}
    print("PERSISTENCE_CONFIG", json.dumps(data), flush=True)
    print("SHOULD: alpha0 exact saved bare IDs; one intervention per generated token; first call full prefill then sequence length1; target gap every alpha1 call; next-block input exact. No claim that persistence isolates cache from representation.", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for scenario in gap.SCENARIOS:
        bare = next(r for r in reference["records"] if r["scenario"] == scenario and r["condition"] == "bare")
        for condition, coefficient in (("persistent_identity_minus", 0.), ("persistent_minus", 1.)):
            encoded = tokenizer(bare["rendered"], return_tensors="pt", add_special_tokens=False).to(model.device)
            assert encoded.input_ids[0].tolist() == bare["input_ids"]
            measures = []
            with torch.inference_mode(), persistent_gap(model, vectors["-C"], gaps["-C"][LAYER], coefficient, measures):
                output = model.generate(**encoded, do_sample=False, temperature=None, top_p=None, top_k=None,
                    pad_token_id=tokenizer.eos_token_id, max_new_tokens=512, use_cache=True)
            ids = output[0, encoded.input_ids.shape[1]:].tolist()
            assert len(measures) == len(ids)
            assert [m["sequence_length"] for m in measures] == [len(bare["input_ids"])]+[1]*(len(ids)-1)
            assert all(m["next_block_input_exact"] for m in measures)
            if coefficient == 0:
                assert ids == bare["generated_ids"]
                assert not any(n for m in measures for n in m["all_position_patch_norms"])
            for index, measure in enumerate(measures):
                measure["absolute_position"] = len(bare["input_ids"])-1+index
                measure["input_token_id"] = bare["input_ids"][-1] if index == 0 else ids[index-1]
                measure["predicted_token_id"] = ids[index]
            text = tokenizer.decode(ids, skip_special_tokens=True).strip()
            record = {"scenario": scenario, "condition": condition, "prompt": bare["prompt"], "rendered": bare["rendered"],
                "input_ids": bare["input_ids"], "generated_ids": ids, "text": text, "coefficient": coefficient,
                "identity_exact": ids == bare["generated_ids"] if coefficient == 0 else None,
                "health": gap.walk.health(tokenizer, [text]), "measurements": measures}
            data["records"].append(record)
            args.output.write_text(json.dumps(data, indent=2)+"\n")
            print("PERSISTENCE_RESPONSE", json.dumps(record, ensure_ascii=False), flush=True)
    data["records"] += [{**r, "reused_from": str(reference_path)} for r in reference["records"]]
    data["runtime"] = {"seconds": time.monotonic()-started, "gpu": torch.cuda.get_device_name(),
        "peak_memory_bytes": torch.cuda.max_memory_allocated(), "torch": torch.__version__}
    args.output.write_text(json.dumps(data, indent=2)+"\n")
    print("PERSISTENCE_COMPLETE", json.dumps(data["runtime"]), flush=True)


async def judge_run(args):
    import os
    import judge
    import export
    from openai import AsyncOpenAI
    assert not args.output.exists()
    data = json.loads(args.judge.read_text())
    client = AsyncOpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1", timeout=60., max_retries=0)
    semaphore = asyncio.Semaphore(3)
    async def one(record, order):
        bare = next(r for r in data["records"] if r["scenario"] == record["scenario"] and r["condition"] == "bare")
        row = {"bare": bare["text"], "steered": record["text"], "prompt": record["prompt"], "vignette": record["scenario"],
            "side": "-C", "run": "v16-transfer-probe", "method": "full_residual_transfer_control", "source": str(args.judge)}
        async with semaphore:
            result = await asyncio.wait_for(judge.judge_one(client, row, order, 0), timeout=240)
        result["condition"] = record["condition"]
        result["exported_effect"] = export.signed_axis_effect("-C", [export.score_cell(result)])
        assert abs(result["exported_effect"]-gap.mapped_effect(result["judgment"], order, "-C")) < 1e-9
        with args.output.open("a") as f:
            f.write(json.dumps(result, ensure_ascii=False)+"\n")
        print("TRANSFER_JUDGMENT", json.dumps(result, ensure_ascii=False), flush=True)
    try:
        await asyncio.gather(*(one(r,o) for r in data["records"] if not r.get("reused_from") and r["condition"] in ("direct_minus", "full_minus", "projected_minus", "gap_minus", "persistent_minus") for o in ("AB", "BA")))
    finally:
        await client.close()


def report(folder):
    import csv
    import export
    import judge
    data = json.loads((folder / "generation.json").read_text())
    judgments = [json.loads(line) for line in (folder / "judgments.jsonl").read_text().splitlines()]
    if data["schema"] == "v16_decode_persistence_v1":
        return report_persistence(folder, data, judgments)
    assert len(data["records"]) == 21 and len(judgments) == 24
    scores, paired, downstream = [], [], []
    lines = ["# Complete transfer responses and identity-mapped judgments", "", "PI/OpenAI Codex. Three selected questions; 21 responses,12 scientific comparisons,24 orderings. No DEV success.", ""]
    for r in data["records"]:
        matches = {j["order"]: j for j in judgments if (j["vignette"],j["condition"]) == (r["scenario"],r["condition"])}
        lines += ["## " + r["scenario"] + " / " + r["condition"], "", "Input as consumed:", "```text", r["rendered"], "```", "", "Response:", "> " + r["text"], ""]
        assert r["patch"]["next_block_input_exact"]
        assert not any(r["patch"]["all_position_patch_norms"][:-1])
        assert len(r["hook_calls"]) == 15 and set(r["hook_calls"].values()) == {1}
        for layer, measurement in r["downstream"].items():
            downstream.append({"scenario": r["scenario"], "condition": r["condition"], "layer": layer, **measurement})
        for order, j in sorted(matches.items()):
            score = j["judgment"]
            assert abs(j["exported_effect"]-export.signed_axis_effect("-C", [export.score_cell(j)])) < 1e-9
            b, s = ("A", "B") if order == "AB" else ("B", "A")
            mapped = {"scenario": r["scenario"], "condition": r["condition"], "order": order,
                "bare_on_axis": score["on_axis_"+b], "steered_on_axis": score["on_axis_"+s],
                "bare_off_axis": score["off_axis_"+b], "steered_off_axis": score["off_axis_"+s],
                "effect": j["exported_effect"], **score}
            scores.append(mapped)
            lines += [order+" identity-mapped scores:", "```json", json.dumps(mapped, ensure_ascii=False), "```", ""]
        if matches:
            a,b = (matches[o]["exported_effect"] for o in ("AB", "BA"))
            paired.append({"scenario": r["scenario"], "condition": r["condition"], "AB_effect": a, "BA_effect": b,
                "strict_reversal": a*b < 0, "tie_disagreement": (a == 0) != (b == 0), "both_tie": a == b == 0})
    for name, rows in (("scores.csv", scores), ("paired.csv", paired), ("downstream.csv", downstream)):
        with (folder/name).open("w") as file:
            writer = csv.DictWriter(file, fieldnames=list(dict.fromkeys(k for r in rows for k in r)))
            writer.writeheader()
            writer.writerows(rows)
    (folder/"responses-and-scores.md").write_text("\n".join(lines)+"\n")
    summary = {"responses": 21, "comparisons": 12, "judgments": 24,
        "strict_reversals": sum(r["strict_reversal"] for r in paired), "tie_disagreements": sum(r["tie_disagreement"] for r in paired),
        "both_ties": sum(r["both_tie"] for r in paired), "reported_judge_cost_usd": sum(j["cost_usd"] for j in judgments),
        "runtime": data["runtime"], "identity_exact": sum(r.get("identity_exact", False) for r in data["records"]),
        "generation_sha256": gap.sha(folder/"generation.json"), "judgments_sha256": gap.sha(folder/"judgments.jsonl"),
        "judge_code_sha256": gap.sha(judge.__file__), "export_code_sha256": gap.sha(export.__file__),
        "max_projected_coordinate_error": max(r.get("donor_coordinate_error_max", 0) for r in data["records"]),
        "max_target_gap_error": max(r.get("target_gap_error", 0) for r in data["records"])}
    (folder/"summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print("TRANSFER_REPORT_PASS", json.dumps(summary), flush=True)


def report_persistence(folder, data, judgments):
    import csv
    import export
    reference = json.loads((folder.parent/"generation.json").read_text())
    assert gap.sha(folder.parent/"generation.json") == data["reference_sha256"]
    prior_judgments = [json.loads(l) for l in (folder.parent/"judgments.jsonl").read_text().splitlines()]
    fresh = [r for r in data["records"] if not r.get("reused_from")]
    assert len(data["records"]) == 27 and len(fresh) == 6 and len(judgments) == 6
    lines = ["# Persistence: complete fresh response / reused control pairs", "", "PI/OpenAI Codex. Three diagnostic cases;6 fresh responses,21 hash-reused controls;3 new comparisons/6 orderings.", ""]
    steps, scores, paired = [], [], []
    for r in fresh:
        measures = r["measurements"]
        bare = next(b for b in reference["records"] if b["scenario"] == r["scenario"] and b["condition"] == "bare")
        assert len(measures) == len(r["generated_ids"])
        assert [m["sequence_length"] for m in measures] == [len(r["input_ids"])]+[1]*(len(measures)-1)
        if r["coefficient"] == 0:
            assert r["generated_ids"] == bare["generated_ids"]
        for m in measures:
            assert m["next_block_input_exact"] and not any(m["all_position_patch_norms"][:-1])
            if r["coefficient"]:
                assert m["target_gap_error"] < .05
            else:
                assert not any(m["all_position_patch_norms"])
            steps.append({"scenario": r["scenario"], "condition": r["condition"], **m})
        lines += ["## "+r["scenario"]+" / "+r["condition"], "", "Input as consumed:", "```text", r["rendered"], "```", "", "Fresh response:", "> "+r["text"], ""]
        for name in ("bare", "gap_minus", "direct_minus"):
            b = next(b for b in reference["records"] if b["scenario"] == r["scenario"] and b["condition"] == name)
            lines += ["Reused "+name+":", "> "+b["text"], ""]
        js = {j["order"]: j for j in judgments if j["vignette"] == r["scenario"] and j["condition"] == r["condition"]}
        for order,j in sorted(js.items()):
            s = j["judgment"]
            assert abs(j["exported_effect"]-export.signed_axis_effect("-C",[export.score_cell(j)])) < 1e-9
            b,t = ("A","B") if order == "AB" else ("B","A")
            score = {"scenario": r["scenario"], "order": order, "bare_on_axis": s["on_axis_"+b], "steered_on_axis": s["on_axis_"+t],
                "bare_off_axis": s["off_axis_"+b], "steered_off_axis": s["off_axis_"+t], "effect": j["exported_effect"], **s}
            scores.append(score)
            lines += [order+" mapped score:", "```json", json.dumps(score,ensure_ascii=False), "```", ""]
        if js:
            a,b = (js[o]["exported_effect"] for o in ("AB","BA"))
            old = {j["order"]:j["exported_effect"] for j in prior_judgments if j["vignette"]==r["scenario"] and j["condition"]=="gap_minus"}
            paired.append({"scenario":r["scenario"],"AB_effect":a,"BA_effect":b,"strict_reversal":a*b<0,"tie_disagreement":(a==0)!=(b==0),
                "prefill_only_AB_effect":old["AB"],"prefill_only_BA_effect":old["BA"]})
    for name,rows in (("steps.csv",steps),("scores.csv",scores),("paired.csv",paired)):
        with (folder/name).open("w") as file:
            writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (folder/"responses-and-scores.md").write_text("\n".join(lines)+"\n")
    summary={"fresh_responses":6,"reused_responses":21,"comparisons":3,"judgments":6,
        "treatment_prefill_calls":3,"treatment_decode_calls":sum(len(r["measurements"])-1 for r in fresh if r["coefficient"]),
        "identity_prefill_calls":3,"identity_decode_calls":sum(len(r["measurements"])-1 for r in fresh if not r["coefficient"]),
        "max_target_gap_error":max(m["target_gap_error"] for r in fresh if r["coefficient"] for m in r["measurements"]),
        "strict_reversals":sum(p["strict_reversal"] for p in paired),"tie_disagreements":sum(p["tie_disagreement"] for p in paired),
        "judge_cost_usd":sum(j["cost_usd"] for j in judgments),"runtime":data["runtime"],
        "generation_sha256":gap.sha(folder/"generation.json"),"reference_sha256":data["reference_sha256"]}
    (folder/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print("PERSISTENCE_REPORT_PASS",json.dumps(summary),flush=True)


# PI/OpenAI Codex: standalone entrypoint reuses the project image without editing run_modal.py.
if __name__ != "__main__":
    import modal
    from run_modal import image, cache, source_revision
    app = modal.App("jsteer-transfer-probe", image=image)
    @app.function(gpu="H100", volumes={"/cache": cache}, timeout=180, max_containers=1, retries=0)
    def remote(revision: str, persistence: bool = False):
        destination = Path("/cache/outputs/audits/20260907_j_lens_transfer_probe") / ("persistence/generation.json" if persistence else "generation.json")
        try:
            subprocess.run([sys.executable, "scripts/scratch/j_lens_transfer_probe.py", "--source-root", "/cache/outputs/experiments",
                "--output", str(destination), "--source-revision", revision] + (["--persistence"] if persistence else []), cwd="/repo", check=True)
            return destination.read_text()
        finally:
            cache.commit()
    @app.local_entrypoint()
    def launch(persistence: bool = False):
        destination = ROOT / ("persistence/generation.json" if persistence else "generation.json")
        assert not destination.exists()
        result = remote.remote(source_revision(), persistence)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result)
        print("TRANSFER_DOWNLOADED", destination, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--persistence", action="store_true")
    parser.add_argument("--source-root", type=Path, default=Path("outputs/experiments"))
    parser.add_argument("--output", type=Path, default=ROOT/"generation.json")
    parser.add_argument("--source-revision", default="unknown")
    parser.add_argument("--judge", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.report:
        report(args.report)
    elif args.judge:
        asyncio.run(judge_run(args))
    elif args.persistence:
        run_persistence(args)
    else:
        run(args)
