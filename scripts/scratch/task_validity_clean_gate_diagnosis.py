"""PI/OpenAI Codex: audit frozen-v3 prompt answers against frozen and literal policy labels."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

CORPUS = Path("slop/logs/20260908_j_lens_task_validity_corpus/v3/corpus.jsonl")
GENERATION = Path("slop/logs/20260908_j_lens_task_validity_source_stage/generation.json")
OUTPUT = Path("slop/logs/20260908_j_lens_task_validity_source_stage/clean-gate-diagnosis.json")
CORPUS_SHA = "b4ef9920b02959e1204c0baa681fc5d402909af65ee676d120145468324f527e"

assert hashlib.sha256(CORPUS.read_bytes()).hexdigest() == CORPUS_SHA
rows_by_id = {row["id"]: row for row in map(json.loads, CORPUS.read_text().splitlines())}
records = json.loads(GENERATION.read_text())["clean"]
assert set(rows_by_id) == {record["id"] for record in records}

by_case = defaultdict(list)
counts = Counter()
for record in records:
    row = rows_by_id[record["id"]]
    literal_action = row["policy_actions"][0 if row["valid"] else 1]
    literal_expected = "AB"[row["options"].index(literal_action)]
    frozen_correct = record["text"] == row["expected"]
    literal_correct = record["text"] == literal_expected
    policy_label_agrees = row["expected"] == literal_expected
    counts["records"] += 1
    counts[f"policy_{row['policy_order']}_records"] += 1
    counts[f"policy_{row['policy_order']}_frozen_correct"] += frozen_correct
    counts[f"policy_{row['policy_order']}_literal_correct"] += literal_correct
    counts["frozen_correct"] += frozen_correct
    counts["literal_correct"] += literal_correct
    counts["label_disagrees_with_prompt"] += not policy_label_agrees
    counts["prompt_correct_but_frozen_wrong"] += literal_correct and not frozen_correct
    counts["prompt_wrong"] += not literal_correct
    by_case[row["semantic_case_id"]].append(
        {
            "id": row["id"],
            "policy_order": row["policy_order"],
            "option_order": row["option_order"],
            "valid": row["valid"],
            "frozen_expected_letter": row["expected"],
            "literal_policy_expected_letter": literal_expected,
            "actual_letter": record["text"],
            "frozen_correct": frozen_correct,
            "literal_policy_correct": literal_correct,
        }
    )

cases = []
for case_id, variants in sorted(by_case.items()):
    assert len(variants) == 4
    cases.append(
        {
            "semantic_case_id": case_id,
            "frozen_correct": sum(item["frozen_correct"] for item in variants),
            "literal_policy_correct": sum(item["literal_policy_correct"] for item in variants),
            "variants": sorted(variants, key=lambda item: (item["policy_order"], item["option_order"])),
        }
    )

summary = {
    "corpus_sha256": CORPUS_SHA,
    "method": "The literal policy label maps valid worlds to policy_actions[0] and invalid worlds to policy_actions[1], then maps that action through each row's A/B option order.",
    "records": counts["records"],
    "frozen_accuracy": counts["frozen_correct"] / counts["records"],
    "literal_policy_accuracy": counts["literal_correct"] / counts["records"],
    "policy_orders": {
        str(order): {
            "records": counts[f"policy_{order}_records"],
            "frozen_accuracy": counts[f"policy_{order}_frozen_correct"] / counts[f"policy_{order}_records"],
            "literal_policy_accuracy": counts[f"policy_{order}_literal_correct"] / counts[f"policy_{order}_records"],
        }
        for order in (0, 1)
    },
    "label_disagrees_with_prompt": counts["label_disagrees_with_prompt"],
    "prompt_correct_but_frozen_wrong": counts["prompt_correct_but_frozen_wrong"],
    "prompt_wrong": counts["prompt_wrong"],
    "cases_all_literal_policy_correct": sum(case["literal_policy_correct"] == 4 for case in cases),
    "cases_all_frozen_correct": sum(case["frozen_correct"] == 4 for case in cases),
}
OUTPUT.write_text(json.dumps({"summary": summary, "cases": cases}, indent=2) + "\n")
print("TASK_VALIDITY_CLEAN_GATE_DIAGNOSIS", json.dumps(summary))
