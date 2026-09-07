"""Bounded v16 source-calibrated gap diagnostic; not a final J-lens method. PI/OpenAI Codex."""
import argparse
import asyncio
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from steering_lite import Vector
import walk
import vjp_steering.j_lens_concept as concept
from j_lens_v16_concept_patch_replay import content_hash

MODEL = "Qwen/Qwen3.5-4B"
REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
SOURCE = "j-lens-persona-full-components-source-v16"
SCENARIOS = ["syco_bullshit_v2_leg_pnf_01", "syco_bullshit_v2_sw_pnf_02", "syco_bullshit_v2_sw_pnf_03"]
CONDITIONS = ["bare", "old_plus", "old_minus", "gap_plus", "gap_minus", "direct_plus", "direct_minus"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_source(root):
    metadata_path = root / SOURCE / "extraction/metadata.json"
    assert sha(metadata_path) == "aa054e789557b9ca4c79c52c93dd3ef8880212f1793c786932a91145bfc4321d"
    meta = json.loads(metadata_path.read_text())
    assert meta["projection"] == "full_residual"
    assert meta["source_layers"] == list(range(13, 22))
    assert meta["model_revision"] in (None, REVISION)
    vectors = {side: Vector.load(str(root / SOURCE / meta["vector_files"][side])) for side in ("+C", "-C")}
    gaps = {side: {} for side in vectors}
    for side, vector in vectors.items():
        assert content_hash(vector) == meta["vector_content_sha256"][side]
        name = "positive" if side == "+C" else "negative"
        for layer in vector.cfg.layers:
            means = meta["layers"][str(layer)]["heldout_source_coordinate_means"][name]
            gaps[side][layer] = means[0] - means[1]
            assert torch.isfinite(torch.tensor(gaps[side][layer]))
            assert vector.shared[layer]["basis"].dtype == vector.shared[layer]["dual"].dtype == torch.float32
            assert int(vector.shared[layer]["target_index"]) == (0 if side == "+C" else 1)
    return vectors, meta, gaps, sha(metadata_path)


def gap_patch(hidden, vector, layer, coefficient, target_gap):
    basis = vector.shared[layer]["basis"].to(device=hidden.device)
    dual = vector.shared[layer]["dual"].to(device=hidden.device)
    c = hidden.float() @ dual.T
    midpoint = c.sum(-1) / 2
    desired = torch.stack((midpoint + target_gap / 2, midpoint - target_gap / 2), -1)
    return hidden + (coefficient * ((desired - c) @ basis)).to(hidden)


@contextmanager
def measured_prefill(model, vector, mask, mode, gaps, measurements, coefficient=1.):
    original = concept.concept_patch
    before = {}
    handles = []
    def capture(layer):
        def hook(_m, _i, output):
            before[layer] = (output[0] if isinstance(output, tuple) else output).detach().clone()
            before_handles[layer].remove()
        return hook
    def measure(layer):
        def hook(_m, _i, output):
            after = output[0] if isinstance(output, tuple) else output
            h = before[layer]
            d = vector.shared[layer]["dual"].to(h.device)
            c, actual = h.float() @ d.T, after.float() @ d.T
            delta = after.float() - h.float()
            changed = (delta != 0).any(-1) & mask.bool()
            measurements[str(layer)] = {
                "changed_positions": int(changed.sum()), "positions": int(mask.sum()),
                "final_changed": bool(changed[0, -1]), "final_patch_norm": float(delta[0, -1].norm()),
                "patch_norm_mean": float(delta[mask.bool()].norm(dim=-1).mean()),
                "target_gap": gaps[layer], "final_coordinates_before": c[0, -1].tolist(),
                "final_coordinates_after": actual[0, -1].tolist(),
                "final_gap_error": float(abs(actual[0, -1, 0] - actual[0, -1, 1] - gaps[layer])),
                "max_coordinate_sum_error": float((actual.sum(-1) - c.sum(-1)).abs().max()),
            }
            handles_by_layer[layer].remove()
        return hook
    handles_by_layer, before_handles = {}, {}
    try:
        if mode == "gap":
            concept.concept_patch = lambda h, v, l, a: gap_patch(h, v, l, a, gaps[l])
        for layer in vector.cfg.layers:
            handle = model.model.layers[layer].register_forward_hook(capture(layer))
            before_handles[layer] = handle
            handles.append(handle)
        with concept.concept_prefill(model, vector, mask, coefficient) as calls:
            for layer in vector.cfg.layers:
                handle = model.model.layers[layer].register_forward_hook(measure(layer))
                handles_by_layer[layer] = handle
                handles.append(handle)
            yield calls
        assert all(n == 1 for n in calls.values()), calls
    finally:
        concept.concept_patch = original
        for handle in handles:
            handle.remove()


def self_test(root):
    vectors, meta, gaps, digest = load_source(root)
    cases = 0
    for side, vector in vectors.items():
        for layer in vector.cfg.layers:
            b, d = (vector.shared[layer][key] for key in ("basis", "dual"))
            for dtype in (torch.float32, torch.bfloat16):
                h = (torch.tensor([[3., 1.], [-1., -3.], [1., 3.]]) @ b).to(dtype)
                assert torch.equal(gap_patch(h, vector, layer, 0., gaps[side][layer]), h)
                c = h.double() @ torch.linalg.solve(b.double() @ b.double().T, b.double()).T
                desired = c.clone()
                desired[:, 0] = c.sum(-1)/2 + gaps[side][layer]/2
                desired[:, 1] = c.sum(-1)/2 - gaps[side][layer]/2
                expected = h.double() + (desired - c) @ b.double()
                actual = gap_patch(h, vector, layer, 1., gaps[side][layer])
                tolerance = 1e-4 if dtype == torch.float32 else .02
                torch.testing.assert_close(actual.double(), expected, atol=tolerance, rtol=tolerance)
                got = actual.float() @ d.T
                torch.testing.assert_close(got.sum(-1), (h.float() @ d.T).sum(-1), atol=tolerance, rtol=tolerance)
                torch.testing.assert_close(got[:, 0] - got[:, 1], torch.full((3,), gaps[side][layer]), atol=tolerance, rtol=tolerance)
                cases += 1
    from types import SimpleNamespace
    model = SimpleNamespace(model=SimpleNamespace(layers=torch.nn.ModuleList([torch.nn.Identity() for _ in range(22)])))
    for mode in ("old", "gap"):
        measures = {}
        h = torch.randn(1, 3, vectors["-C"].shared[13]["basis"].shape[1])
        with measured_prefill(model, vectors["-C"], torch.ones(1, 3), mode, gaps["-C"], measures):
            for layer in range(13, 22):
                h = model.model.layers[layer](h)
            second = h.clone()
            for layer in range(13, 22):
                second = model.model.layers[layer](second)
            assert torch.equal(second, h)
        assert len(measures) == 9
        if mode == "gap":
            assert all(item["final_gap_error"] < 1e-4 for item in measures.values())
    print("GAP_CLAMP_CPU_PASS", json.dumps({"cases": cases, "hook_modes": ["old", "gap"], "metadata_sha256": digest, "alpha0_exact": True, "sum_and_gap": True, "targets": gaps}), flush=True)


def run(args):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    started = time.monotonic()
    assert not args.output.exists(), args.output
    vectors, metadata, gaps, source_hash = load_source(args.source_root)
    from huggingface_hub import snapshot_download
    snapshot = Path(snapshot_download(MODEL, revision=REVISION))
    assert snapshot.name == REVISION, snapshot
    tokenizer = AutoTokenizer.from_pretrained(snapshot)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(snapshot, dtype=torch.bfloat16).to("cuda").eval()
    print("PINNED_MODEL", json.dumps({"snapshot": str(snapshot), "config_commit_hash": getattr(model.config, "_commit_hash", None)}), flush=True)
    rows, cohort_hash = walk.read_cohort(15)
    rows = [next(row for row in rows if row["scenario"] == scenario) for scenario in SCENARIOS]
    payload = {"schema": "v16_gap_clamp_diagnostic_v1", "source_revision": args.source_revision,
               "implementation_sha256": sha(__file__), "model": MODEL, "model_revision": REVISION,
               "model_snapshot": str(snapshot), "model_config_sha256": sha(snapshot / "config.json"),
               "model_index_sha256": sha(snapshot / "model.safetensors.index.json"),
               "config_commit_hash": getattr(model.config, "_commit_hash", None),
               "source_metadata_sha256": source_hash, "source_recorded_model_revision": metadata["model_revision"], "vector_content_sha256": metadata["vector_content_sha256"],
               "cohort_sha256": cohort_hash, "source_gaps": gaps, "scenarios": SCENARIOS, "conditions": CONDITIONS,
               "settings": {"dtype": "bfloat16", "batch_size": 1, "layers": list(range(13,22)), "alpha": 1., "max_new_tokens": 512},
               "records": [], "not_final_j_lens_method": True}
    print("SHOULD: gap clamp edits final minus positions even where sorting is ineligible; target gaps fixed from source, not DEV", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for row in rows:
        for condition in CONDITIONS:
            side = "+C" if condition.endswith("plus") else "-C"
            name = "positive" if side == "+C" else "negative"
            persona = metadata["spec"][f"{name}_instruction"].removeprefix("Answer as someone who is ").removesuffix(".") if condition.startswith("direct") else None
            rendered = walk.generation_inputs(tokenizer, [row], persona)[0]
            encoded = tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to(model.device)
            measures = {}
            if condition.startswith(("old", "gap")):
                context = measured_prefill(model, vectors[side], encoded.attention_mask, condition.split("_")[0], gaps[side], measures)
            else:
                from contextlib import nullcontext
                context = nullcontext()
            with context, torch.inference_mode():
                output = model.generate(**encoded, do_sample=False, temperature=None, top_p=None, top_k=None,
                                        pad_token_id=tokenizer.eos_token_id, max_new_tokens=512, use_cache=True)
            ids = output[0, encoded.input_ids.shape[1]:].tolist()
            text = tokenizer.decode(ids, skip_special_tokens=True).strip()
            record = {"scenario": row["scenario"], "prompt": row["prompt"], "condition": condition,
                      "rendered": rendered, "input_ids": encoded.input_ids[0].tolist(), "generated_ids": ids,
                      "text": text, "health": walk.health(tokenizer, [text]), "measurements": measures}
            payload["records"].append(record)
            args.output.write_text(json.dumps(payload, indent=2) + "\n")
            print("GAP_RESPONSE", json.dumps(record, ensure_ascii=False), flush=True)
    payload["runtime"] = {"seconds": time.monotonic()-started, "gpu": torch.cuda.get_device_name(),
                          "peak_memory_bytes": torch.cuda.max_memory_allocated(), "torch": torch.__version__}
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print("GAP_CLAMP_COMPLETE", json.dumps({"responses": len(payload["records"]), "runtime": payload["runtime"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--source-root", type=Path, default=Path("outputs/experiments"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    torch.set_num_threads(1)
    if args.self_test:
        self_test(args.source_root)
    else:
        assert args.output and args.source_revision
        run(args)


if __name__ == "__main__":
    main()
