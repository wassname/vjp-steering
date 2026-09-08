"""PI/OpenAI Codex: audit whether job 705 selected the first policy action."""
import json
from pathlib import Path

CORPUS = Path("slop/logs/20260908_j_lens_task_validity_corpus/v3/corpus.jsonl")
GENERATION = Path("slop/logs/20260908_j_lens_task_validity_source_stage/generation.json")
OUTPUT = Path("slop/logs/20260908_j_lens_task_validity_source_stage/first-policy-check.json")


rows = [json.loads(line) for line in CORPUS.read_text().splitlines()]
records = json.loads(GENERATION.read_text())["clean"]
rows_by_id = {row["id"]: row for row in rows}
assert set(rows_by_id) == {record["id"] for record in records}

mismatches = []
for record in records:
    row = rows_by_id[record["id"]]
    first_policy_letter = "AB"[row["options"].index(row["policy_actions"][0])]
    if record["text"] != first_policy_letter:
        mismatches.append(
            {
                "id": record["id"],
                "semantic_case_id": row["semantic_case_id"],
                "first_policy_letter": first_policy_letter,
                "actual_letter": record["text"],
            }
        )

OUTPUT.write_text(
    json.dumps(
        {
            "method": "map each row's first policy action through that row's A/B option order, then compare with saved greedy output",
            "records": len(records),
            "first_policy_matches": len(records) - len(mismatches),
            "first_policy_match_rate": (len(records) - len(mismatches)) / len(records),
            "mismatches": mismatches,
        },
        indent=2,
    )
    + "\n"
)
