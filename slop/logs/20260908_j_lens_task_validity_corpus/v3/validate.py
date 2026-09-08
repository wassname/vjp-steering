"""PI/OpenAI Codex: offline v3 integrity, balance, shortcut-control, and overlap audit."""
import collections
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
V2 = ROOT.parent / "v2"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def norm(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))

def grams(text, n=5):
    words = norm(text).split()
    return {" ".join(words[idx:idx + n]) for idx in range(len(words) - n + 1)}

freeze = json.loads((ROOT / "freeze.json").read_text())
assert sha(ROOT / "corpus.jsonl") == freeze["corpus_sha256"]
assert sha(ROOT / "build.py") == freeze["generator_sha256"]
v2_freeze = json.loads((V2 / "freeze.json").read_text())
assert sha(V2 / "corpus.jsonl") == v2_freeze["corpus_sha256"] == freeze["parent_corpus_sha256"]
rows = [json.loads(line) for line in (ROOT / "corpus.jsonl").read_text().splitlines()]
parents = {row["id"]: row for row in map(json.loads, (V2 / "corpus.jsonl").read_text().splitlines())}
assert len(rows) == freeze["rows"] == 2 * len(parents)
assert len({row["id"] for row in rows}) == len(rows)

for row in rows:
    parent = parents[row["v2_parent_id"]]
    assert all(row[key] == parent[key] for key in ("rule", "evidence", "facts", "valid", "split", "cue_family", "consumer", "options", "expected", "option_order"))
    assert row["expected_semantic_action"] == ("valid" if row["valid"] else "invalid")
    valid_action, invalid_action = row["actions_valid_invalid"]
    assert row["options"]["AB".index(row["expected"])] == (valid_action if row["valid"] else invalid_action)
    expected_policy = [valid_action, invalid_action] if row["policy_order"] == 0 else [invalid_action, valid_action]
    assert row["policy_actions"] == expected_policy
    assert f"When the requirement holds, {expected_policy[0]}; otherwise, {expected_policy[1]}." in row["prompt"]
    assert row["rule"] in row["prompt"] and row["evidence"] in row["prompt"]

by_parent = collections.defaultdict(list)
by_case = collections.defaultdict(list)
for row in rows:
    by_parent[row["v2_parent_id"]].append(row)
    by_case[row["semantic_case_id"]].append(row)
for group in by_parent.values():
    assert len(group) == 2
    assert {row["policy_order"] for row in group} == {0, 1}
    assert len({row["prompt"] for row in group}) == 2
for group in by_case.values():
    assert len(group) == 4
    assert {row["option_order"] for row in group} == {0, 1}
    assert {row["policy_order"] for row in group} == {0, 1}
    assert len({row["expected_semantic_action"] for row in group}) == 1

answer_balance = []
policy_balance = []
for split in freeze["split_ids"]:
    subset = [row for row in rows if row["split"] == split]
    for consumer in sorted({row["consumer"] for row in subset}):
        for valid in (False, True):
            for policy_order in (0, 1):
                cell = [row for row in subset if row["consumer"] == consumer and row["valid"] == valid and row["policy_order"] == policy_order]
                counts = collections.Counter(row["expected"] for row in cell)
                answer_balance.append({"split": split, "consumer": consumer, "valid": valid, "policy_order": policy_order, "counts": dict(counts), "balanced": counts == {"A": len(cell) // 2, "B": len(cell) // 2}})
            for option_order in (0, 1):
                cell = [row for row in subset if row["consumer"] == consumer and row["valid"] == valid and row["option_order"] == option_order]
                counts = collections.Counter(row["policy_order"] for row in cell)
                policy_balance.append({"split": split, "consumer": consumer, "valid": valid, "option_order": option_order, "counts": dict(counts), "balanced": counts == {0: len(cell) // 2, 1: len(cell) // 2}})
assert all(cell["balanced"] for cell in answer_balance)
assert all(cell["balanced"] for cell in policy_balance)
held_consumers = {"storage", "notification"}
assert not [row["id"] for row in rows if row["consumer"] in held_consumers and row["split"] != "withheld_source"]

# The proposed Stage A admission gate evaluates selected semantic action, never just the A/B token.
def selected_semantic(row, answer):
    if answer not in {"A", "B"}:
        return None
    action = row["options"]["AB".index(answer)]
    valid_action, invalid_action = row["actions_valid_invalid"]
    return "valid" if action == valid_action else "invalid" if action == invalid_action else None

def gate(responder):
    report = {}
    for key, selector in {
        "split": lambda row: row["split"],
        "split_consumer": lambda row: (row["split"], row["consumer"]),
        "split_cue": lambda row: (row["split"], row["cue_family"]),
    }.items():
        cells = collections.defaultdict(list)
        for row in rows:
            cells[str(selector(row))].append(selected_semantic(row, responder(row)) == row["expected_semantic_action"])
        report[key] = {cell: sum(values) / len(values) for cell, values in cells.items()}
    policy_mirror = {}
    for parent, group in by_parent.items():
        semantic = [selected_semantic(row, responder(row)) for row in group]
        policy_mirror[parent] = len(set(semantic)) == 1 and semantic[0] == group[0]["expected_semantic_action"]
    full_mirror = {}
    for case, group in by_case.items():
        semantic = [selected_semantic(row, responder(row)) for row in group]
        full_mirror[case] = len(set(semantic)) == 1 and semantic[0] == group[0]["expected_semantic_action"]
    min_accuracy = min(value for groups in report.values() for value in groups.values())
    return {"pass": min_accuracy >= 0.90 and all(policy_mirror.values()) and all(full_mirror.values()), "min_semantic_accuracy": min_accuracy, "semantic_policy_mirror_pass_rate": sum(policy_mirror.values()) / len(policy_mirror), "semantic_option_policy_mirror_pass_rate": sum(full_mirror.values()) / len(full_mirror), "groups": report}

controls = {
    "semantic_oracle": lambda row: row["expected"],
    "always_A": lambda row: "A",
    "always_B": lambda row: "B",
    "opposite_letter": lambda row: "B" if row["expected"] == "A" else "A",
    "first_policy_branch": lambda row: "AB"[row["options"].index(row["policy_actions"][0])],
}
gate_controls = {name: gate(responder) for name, responder in controls.items()}
assert gate_controls["semantic_oracle"]["pass"]
assert not gate_controls["always_A"]["pass"]
assert not gate_controls["always_B"]["pass"]
assert not gate_controls["opposite_letter"]["pass"]
assert not gate_controls["first_policy_branch"]["pass"]

cohort_path = Path("data/bullshit_bench_v2.jsonl")
cohort = [{"id": record["scenario"], "prompt": record["prompt"]} for record in map(json.loads, cohort_path.read_text().splitlines())]
assert len(cohort) == 100
comparison = [{**record, "dataset": "full"} for record in cohort]
input_hashes = [{"role": "full", "path": str(cohort_path), "sha256": sha(cohort_path), "ids": [record["id"] for record in cohort]}, {"role": "DEV", "path": str(cohort_path), "sha256": sha(cohort_path), "ids": [record["id"] for record in cohort[:15]]}]
missing = []
for version in ("components-source-v13", "components-source-v15", "full-components-source-v16"):
    path = Path("outputs/experiments/j-lens-persona-" + version + "/extraction/metadata.json")
    if not path.exists():
        missing.append(str(path))
        continue
    metadata = json.loads(path.read_text())
    nfit = metadata["source_fit_count"]
    assert len(metadata["source_ids"]) == nfit + metadata["source_holdout_count"]
    for role, start, end in (("historical_fit", 0, nfit), ("historical_source_holdout", nfit, len(metadata["source_ids"]))):
        input_hashes.append({"role": role, "path": str(path), "sha256": sha(path), "ids": metadata["source_ids"][start:end]})
        for condition, prompts in metadata["source_prompts"].items():
            comparison.extend({"id": item_id, "prompt": prompt, "dataset": version + "/" + role + "/" + condition} for item_id, prompt in zip(metadata["source_ids"][start:end], prompts[start:end]))
for version in ("components-calibration-v15", "full-components-calibration-v16"):
    path = Path("outputs/experiments/j-lens-persona-" + version + "/calibration.json")
    if not path.exists():
        missing.append(str(path))
        continue
    input_hashes.append({"role": "historical_calibration", "path": str(path), "sha256": sha(path), "ids": [record["id"] for record in cohort[:15]]})

findings = {"exact_id": [], "normalized_content": [], "substring_40_chars": [], "shared_5grams": [], "entities": [], "relation_templates": []}
relations = {"capacity": ("capacity", "at least"), "roster": ("member", "roster"), "seal_match": ("seal", "requires"), "parity": ("odd", "even"), "precedence": ("before", "event"), "link": ("directed", "connection")}
for row in rows:
    source_text = norm(row["prompt"])
    source_grams = grams(row["prompt"])
    for other in comparison:
        other_text = norm(other["prompt"])
        ref = {"corpus_id": row["id"], "other_id": other["id"], "dataset": other["dataset"]}
        if row["id"] == other["id"]:
            findings["exact_id"].append(ref)
        if source_text == other_text:
            findings["normalized_content"].append(ref)
        if min(len(source_text), len(other_text)) >= 40 and (source_text in other_text or other_text in source_text):
            findings["substring_40_chars"].append(ref)
        shared = sorted(source_grams & grams(other["prompt"]))
        if shared:
            findings["shared_5grams"].append({**ref, "phrases": shared})
        entities = [entity for entity in row["entities"] if re.search(r"\\b" + re.escape(entity) + r"\\b", other["prompt"], re.I)]
        if entities:
            findings["entities"].append({**ref, "entities": entities})
        terms = relations[row["cue_family"]]
        if all(re.search(r"\\b" + re.escape(term) + r"\\b", other_text) for term in terms):
            findings["relation_templates"].append({**ref, "terms": terms})
assert not missing
assert not any(findings.values())
protected_paths = [Path("results/plot.png"), Path("results/index.md"), Path("results/index.html"), Path("data/results.csv"), Path("scripts/judge.py")]
result = {"frozen_corpus_sha256": sha(ROOT / "corpus.jsonl"), "parent_v2_sha256": v2_freeze["corpus_sha256"], "rows": len(rows), "answer_position_balance": answer_balance, "policy_clause_order_balance": policy_balance, "withheld_consumer_leaks": [], "gate_controls": gate_controls, "overlap_inputs": input_hashes, "missing_inputs": missing, "comparison_records": len(comparison), "overlap_findings": findings, "overlap_counts": {kind: len(hits) for kind, hits in findings.items()}, "protected_sha256": {str(path): sha(path) for path in protected_paths}, "limits": ["The gate controls are simulations, not target-model evidence.", "Lexical and template overlap checks do not prove semantic independence.", "The corpus tests closed-world precondition satisfaction, not the benchmark's real-world-existence claims.", "The unchanged benchmark rubric is the sole future transfer outcome; no binary existence-rejection score is added."]}
(ROOT / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
assert sha(ROOT / "corpus.jsonl") == freeze["corpus_sha256"]
print("TASK_VALIDITY_V3_CORPUS_PASS", json.dumps({"rows": len(rows), "answer_position_balance_pass": True, "policy_clause_order_balance_pass": True, "withheld_consumers_absent_train_calibration": True, "gate_controls": {name: report["pass"] for name, report in gate_controls.items()}, "overlap_counts": result["overlap_counts"], "comparison_records": len(comparison)}))
