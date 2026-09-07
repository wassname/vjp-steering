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
                "hook_calls": calls[layer], "changed_positions": int(changed.sum()), "positions": int(mask.sum()),
                "all_position_patch_norms": delta[0].norm(dim=-1).tolist(),
                "all_position_coordinates_before": c[0].tolist(), "all_position_coordinates_after": actual[0].tolist(),
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
    for side in ("+C", "-C"):
        assert mapped_effect({"on_axis_A": 1., "on_axis_B": 4.}, "AB", side) == mapped_effect({"on_axis_A": 4., "on_axis_B": 1.}, "BA", side)
    print("GAP_JUDGE_MAPPING_PASS AB_BA_same_contrast=true", flush=True)
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
    for mode in ("old", "gap", "gap_final"):
        measures = {}
        h = torch.randn(1, 3, vectors["-C"].shared[13]["basis"].shape[1])
        mask = torch.tensor([[0., 0., 1.]]) if mode == "gap_final" else torch.ones(1, 3)
        untouched = h[:, :2].clone()
        with measured_prefill(model, vectors["-C"], mask, "gap" if mode == "gap_final" else mode, gaps["-C"], measures):
            for layer in range(13, 22):
                h = model.model.layers[layer](h)
            second = h.clone()
            for layer in range(13, 22):
                second = model.model.layers[layer](second)
            assert torch.equal(second, h)
        assert len(measures) == 9
        if mode.startswith("gap"):
            assert all(item["final_gap_error"] < 1e-4 for item in measures.values())
        if mode == "gap_final":
            assert torch.equal(untouched, h[:, :2])
            assert all(item["changed_positions"] == 1 for item in measures.values())
            print("GAP_FINAL_MASK_CPU_PASS nonfinal_exact_identity=true nine_final_hooks=true", flush=True)
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
    reference = json.loads(args.reuse.read_text()) if args.reuse else None
    if args.placement == "final":
        assert reference is not None and reference["scenarios"] == SCENARIOS
        assert reference["model_revision"] == REVISION and reference["source_metadata_sha256"] == source_hash
        assert reference["settings"] == {"dtype": "bfloat16", "batch_size": 1, "layers": list(range(13,22)), "alpha": 1., "max_new_tokens": 512}
    payload = {"schema": "v16_gap_clamp_diagnostic_v1", "source_revision": args.source_revision,
               "implementation_sha256": sha(__file__), "model": MODEL, "model_revision": REVISION,
               "model_snapshot": str(snapshot), "model_config_sha256": sha(snapshot / "config.json"),
               "model_index_sha256": sha(snapshot / "model.safetensors.index.json"),
               "config_commit_hash": getattr(model.config, "_commit_hash", None),
               "source_metadata_sha256": source_hash, "source_recorded_model_revision": metadata["model_revision"], "vector_content_sha256": metadata["vector_content_sha256"],
               "cohort_sha256": cohort_hash, "source_gaps": gaps, "scenarios": SCENARIOS, "conditions": CONDITIONS,
               "settings": {"dtype": "bfloat16", "batch_size": 1, "layers": list(range(13,22)), "alpha": 1., "max_new_tokens": 512},
               "placement": args.placement, "records": [], "not_final_j_lens_method": True}
    if reference:
        payload["reference_sha256"] = sha(args.reuse)
        payload["reference_source_revision"] = reference["source_revision"]
        payload["records"] = [{**r, "reused_from": str(args.reuse)} for r in reference["records"]]
        payload["conditions"] = CONDITIONS + ["gap_final_plus", "gap_final_minus"]
    print("SHOULD: gap clamp edits final minus positions even where sorting is ineligible; target gaps fixed from source, not DEV", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for row in rows:
        for condition in (["gap_final_plus", "gap_final_minus"] if args.placement == "final" else CONDITIONS):
            side = "+C" if condition.endswith("plus") else "-C"
            name = "positive" if side == "+C" else "negative"
            persona = metadata["spec"][f"{name}_instruction"].removeprefix("Answer as someone who is ").removesuffix(".") if condition.startswith("direct") else None
            rendered = walk.generation_inputs(tokenizer, [row], persona)[0]
            encoded = tokenizer(rendered, return_tensors="pt", add_special_tokens=False).to(model.device)
            measures = {}
            mask = encoded.attention_mask
            if args.placement == "final":
                bare_ref = next(r for r in reference["records"] if r["scenario"] == row["scenario"] and r["condition"] == "bare")
                assert encoded.input_ids[0].tolist() == bare_ref["input_ids"] and rendered == bare_ref["rendered"]
                mask = torch.zeros_like(encoded.attention_mask)
                mask[:, -1] = 1
            if condition.startswith(("old", "gap")):
                context = measured_prefill(model, vectors[side], mask, condition.split("_")[0], gaps[side], measures)
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
                      "text": text, "health": walk.health(tokenizer, [text]), "patch_mask": mask[0].tolist(), "measurements": measures}
            payload["records"].append(record)
            args.output.write_text(json.dumps(payload, indent=2) + "\n")
            print("GAP_RESPONSE", json.dumps(record, ensure_ascii=False), flush=True)
    payload["runtime"] = {"seconds": time.monotonic()-started, "gpu": torch.cuda.get_device_name(),
                          "peak_memory_bytes": torch.cuda.max_memory_allocated(), "torch": torch.__version__}
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print("GAP_CLAMP_COMPLETE", json.dumps({"responses": len(payload["records"]), "runtime": payload["runtime"]}), flush=True)


def mapped_effect(score, order, side):
    difference = score["on_axis_B"] - score["on_axis_A"] if order == "AB" else score["on_axis_A"] - score["on_axis_B"]
    return difference * (1 if side == "+C" else -1)


async def judge_results(args):
    import os
    import judge
    from openai import AsyncOpenAI
    assert not args.output.exists(), args.output
    data = json.loads(args.judge.read_text())
    client = AsyncOpenAI(api_key=os.environ["OPENROUTER_API_KEY"], base_url="https://openrouter.ai/api/v1", timeout=60., max_retries=0)
    semaphore = asyncio.Semaphore(3)
    records = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    async def one(record):
        bare = next(r for r in data["records"] if r["scenario"] == record["scenario"] and r["condition"] == "bare")
        row = {"bare": bare["text"], "steered": record["text"], "prompt": record["prompt"],
               "vignette": record["scenario"], "side": "+C" if record["condition"].endswith("plus") else "-C",
               "run": "v16-gap-clamp-diagnostic", "method": "full_residual_gap_control", "source": str(args.judge)}
        async with semaphore:
            result = await asyncio.wait_for(judge.judge_one(client, row, args.judge_order, 0), timeout=240)
        result["condition"] = record["condition"]
        score = result["judgment"]
        result["exported_effect"] = mapped_effect(score, args.judge_order, row["side"])
        records.append(result)
        with args.output.open("a") as file:
            file.write(json.dumps(result, ensure_ascii=False) + "\n")
        print("GAP_JUDGMENT", json.dumps(result, ensure_ascii=False), flush=True)
    try:
        await asyncio.gather(*(one(record) for record in data["records"] if record["condition"] != "bare" and not record.get("reused_from")))
    finally:
        await client.close()
    print("GAP_JUDGE_COMPLETE", json.dumps({"records": len(records), "model": judge.MODEL, "rubric": judge.RUBRIC,
                                           "reported_cost_usd": sum(r["cost_usd"] for r in records)}), flush=True)


def report_results(args):
    import csv
    import io
    import export
    data = json.loads(args.report.read_text())
    folder = args.output
    folder.mkdir(parents=True, exist_ok=True)
    judge_paths = [folder / name for name in ("judgments.jsonl", "judgments-ba.jsonl")] + args.prior_judgments
    judgments = [json.loads(line) for path in judge_paths for line in path.read_text().splitlines()]
    expected_pairs = sum(r["condition"] != "bare" for r in data["records"])
    assert len(judgments) == 2 * expected_pairs and len({(r["vignette"], r["condition"], r["order"]) for r in judgments}) == 2 * expected_pairs
    for result in judgments:
        assert abs(result["exported_effect"] - mapped_effect(result["judgment"], result["order"], result["side"])) < 1e-9
        assert abs(result["exported_effect"] - export.signed_axis_effect(result["side"], [export.score_cell(result)])) < 1e-9
    (folder / "generation.json").write_text(json.dumps(data, indent=2) + "\n")
    lines = ["# Gap clamp complete response and measurement record", "", "PI/OpenAI Codex. Three diagnostic cases, not representative DEV evidence. AB/BA are two orderings of each comparison, not extra scenarios.", "", "|scenario|condition|final changed /9|final gap error max|AB effect|BA effect|", "|---|---|---:|---:|---:|---:|"]
    coordinates, scores = [], []
    for record in data["records"]:
        js = {r["order"]: r for r in judgments if (r["vignette"], r["condition"]) == (record["scenario"], record["condition"])}
        measures = record["measurements"]
        values = [record["scenario"], record["condition"], sum(m["final_changed"] for m in measures.values()), max([m["final_gap_error"] for m in measures.values()] or [0])]
        lines.append("|" + "|".join(map(str, values + [js[o]["exported_effect"] if o in js else "n/a" for o in ("AB", "BA")])) + "|")
        for layer, measurement in measures.items():
            coordinates.append({"scenario": record["scenario"], "condition": record["condition"], "layer": layer, **measurement})
        for order, result in js.items():
            j = result["judgment"]
            bare_key, steered_key = ("A", "B") if order == "AB" else ("B", "A")
            scores.append({"scenario": record["scenario"], "condition": record["condition"], "order": order, "exported_effect": result["exported_effect"],
                           "bare_on_axis": j[f"on_axis_{bare_key}"], "steered_on_axis": j[f"on_axis_{steered_key}"],
                           "bare_off_axis": j[f"off_axis_{bare_key}"], "steered_off_axis": j[f"off_axis_{steered_key}"], **j})
    for record in data["records"]:
        lines += ["", f"## {record['scenario']} / {record['condition']}", "", "Input as consumed:", "", "```text", record["rendered"], "```", "", "Response:", "", "> " + record["text"], ""]
        for result in judgments:
            if (result["vignette"], result["condition"]) == (record["scenario"], record["condition"]):
                lines += [f"{result['order']} effect={result['exported_effect']:.3f}; raw per-response scores:", "```json", json.dumps(result["judgment"], ensure_ascii=False), "```"]
    paired = []
    for record in data["records"]:
        if record["condition"] == "bare":
            continue
        pair = {s["order"]: s for s in scores if (s["scenario"], s["condition"]) == (record["scenario"], record["condition"])}
        a, b = pair["AB"]["exported_effect"], pair["BA"]["exported_effect"]
        paired.append({"scenario": record["scenario"], "condition": record["condition"], "AB_effect": a, "BA_effect": b,
                       "paired_mean_effect": (a+b)/2, "strict_sign_reversal": a*b < 0,
                       "either_tie": a == 0 or b == 0, "both_tie": a == b == 0,
                       "absolute_order_gap": abs(a-b)})
    assert len(paired) == expected_pairs
    for name, rows in (("coordinates.csv", coordinates), ("scores.csv", scores), ("paired.csv", paired)):
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
        writer.writeheader()
        writer.writerows(rows)
        (folder / name).write_text(stream.getvalue())
    (folder / "responses-and-scores.md").write_text("\n".join(lines) + "\n")
    print("GAP_REPORT_PASS", json.dumps({"responses": len(data["records"]), "coordinate_rows": len(coordinates), "judge_rows": len(scores), "reported_judge_cost_usd": sum(r["cost_usd"] for r in judgments), "generation_seconds": data["runtime"]["seconds"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--judge", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--prior-judgments", type=Path, action="append", default=[])
    parser.add_argument("--placement", choices=("all", "final"), default="all")
    parser.add_argument("--reuse", type=Path)
    parser.add_argument("--judge-order", choices=("AB", "BA"), default="AB")
    parser.add_argument("--source-root", type=Path, default=Path("outputs/experiments"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    torch.set_num_threads(1)
    if args.self_test:
        self_test(args.source_root)
    elif args.judge:
        asyncio.run(judge_results(args))
    elif args.report:
        report_results(args)
    else:
        assert args.output and args.source_revision
        run(args)


if __name__ == "__main__":
    main()
