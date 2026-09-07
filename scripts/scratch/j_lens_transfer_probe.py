"""One-layer minus donor transfer diagnostic, not a J-lens benchmark. PI/OpenAI Codex."""
import argparse
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
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


def self_test():
    from types import SimpleNamespace
    from transformers import Qwen3_5TextConfig, Qwen3_5ForCausalLM
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
    print("TRANSFER_CPU_PASS Gram_FP32_BF16=true tiny_Qwen_cached_generate=true identity_ids_exact=true next_block_exact=true one_shot=true", flush=True)


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
        await asyncio.gather(*(one(r,o) for r in data["records"] if r["condition"] in ("direct_minus", "full_minus", "projected_minus", "gap_minus") for o in ("AB", "BA")))
    finally:
        await client.close()


# Standalone entrypoint reuses the existing pinned project image without editing run_modal.py.
if __name__ != "__main__":
    import modal
    from run_modal import image, cache, source_revision
    app = modal.App("jsteer-transfer-probe", image=image)
    @app.function(gpu="H100", volumes={"/cache": cache}, timeout=900)
    def remote(revision: str):
        destination = Path("/cache/outputs/audits/20260907_j_lens_transfer_probe/generation.json")
        try:
            subprocess.run([sys.executable, "scripts/scratch/j_lens_transfer_probe.py", "--source-root", "/cache/outputs/experiments",
                "--output", str(destination), "--source-revision", revision], cwd="/repo", check=True)
            return destination.read_text()
        finally:
            cache.commit()
    @app.local_entrypoint()
    def launch():
        destination = ROOT / "generation.json"
        assert not destination.exists()
        result = remote.remote(source_revision())
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(result)
        print("TRANSFER_DOWNLOADED", destination, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--source-root", type=Path, default=Path("outputs/experiments"))
    parser.add_argument("--output", type=Path, default=ROOT/"generation.json")
    parser.add_argument("--source-revision", default="unknown")
    parser.add_argument("--judge", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.judge:
        asyncio.run(judge_run(args))
    else:
        run(args)
