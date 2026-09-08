"""PI/OpenAI Codex: freeze v3 from frozen v2 without benchmark-driven curation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
V2 = ROOT.parent / "v2"
v2_freeze = json.loads((V2 / "freeze.json").read_text())
assert hashlib.sha256((V2 / "corpus.jsonl").read_bytes()).hexdigest() == v2_freeze["corpus_sha256"]

rows = []
for parent in map(json.loads, (V2 / "corpus.jsonl").read_text().splitlines()):
    for policy_order in (0, 1):
        row = dict(parent)
        valid_action, invalid_action = row["actions_valid_invalid"]
        policy_actions = (valid_action, invalid_action) if policy_order == 0 else (invalid_action, valid_action)
        row["policy_order"] = policy_order
        row["policy_actions"] = list(policy_actions)
        row["id"] = parent["id"].replace("tv2_", "tv3_").replace("_o", f"_p{policy_order}_o")
        row["pair_id"] = row["id"].rsplit("_", 1)[0]
        row["semantic_case_id"] = parent["v1_parent_id"]
        row["expected_semantic_action"] = "valid" if row["valid"] else "invalid"
        row["expected"] = "AB"[row["options"].index(valid_action if row["valid"] else invalid_action)]
        cue = f'{row["rule"]}\n{row["evidence"]}' if row["world"] % 2 == 0 else f'{row["evidence"]}\n{row["rule"]}'
        row["prompt"] = (
            "This is a self-contained rule world; the stated requirement is the only criterion for this operation.\n"
            + cue
            + "\n"
            + f"When the requirement holds, {policy_actions[0]}; otherwise, {policy_actions[1]}.\n"
            + f'Which action follows? A: {row["options"][0]}. B: {row["options"][1]}. Reply with one letter only.'
        )
        row["provenance"] = "PI/OpenAI Codex synthetic rule-world v3; frozen v2 semantic content with policy-clause-order counterbalance"
        row["v2_parent_id"] = parent["id"]
        rows.append(row)

corpus = "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows).encode()
if (ROOT / "freeze.json").exists():
    assert (ROOT / "corpus.jsonl").read_bytes() == corpus, "Do not overwrite frozen v3"
else:
    (ROOT / "corpus.jsonl").write_bytes(corpus)
    manifest = {
        "version": 3,
        "author": "PI/OpenAI Codex",
        "rows": len(rows),
        "corpus_sha256": hashlib.sha256(corpus).hexdigest(),
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "parent_corpus_sha256": v2_freeze["corpus_sha256"],
        "phase": "frozen before v3 overlap audit and any target-model evaluation",
        "revision_reason": "Independent review found policy-branch-order alignment and a constant-letter causal-gate false positive.",
        "split_ids": {split: [row["id"] for row in rows if row["split"] == split] for split in v2_freeze["split_ids"]},
        "rule": "No rule, evidence, split, validity label, benchmark wording, or row selection changed from v2; each v2 row has both policy orders.",
    }
    (ROOT / "freeze.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("CORPUS_V3_FREEZE_PASS", hashlib.sha256(corpus).hexdigest(), len(rows))
