"""Audit AB/BA DEV judgments without treating order as extra samples. — PI/OpenAI Codex"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).parents[1]))

from export import score_cell
from judge import CACHE, cache_key, experiment_rows, valid


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--experiment-id")
    parser.add_argument("--profile", choices=("dev", "full"), default="dev")
    parser.add_argument("--control", choices=("random_plus", "random_minus"))
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def classify_orders(ab_effect: float, ba_effect: float) -> str:
    if ab_effect * ba_effect < 0:
        return "strict_reversal"
    if (ab_effect == 0) != (ba_effect == 0):
        return "tie_disagreement"
    return "same_side_or_double_tie"


def cache_records(keys: set[str]) -> dict[str, dict]:
    records = {}
    with CACHE.open() as handle:
        for line in handle:
            record = json.loads(line)
            if record["cache_key"] in keys and valid(record.get("judgment", {})):
                records.setdefault(record["cache_key"], record)
    missing = keys - records.keys()
    if missing:
        raise ValueError(f"order audit missing {len(missing)} judged cells")
    return records


def audit_rows(rows: list[dict]) -> list[dict]:
    keys = {
        cache_key(row, order, 0)
        for row in rows
        for order in ("AB", "BA")
    }
    cache = cache_records(keys)
    audited = []
    for row in rows:
        ab = score_cell(cache[cache_key(row, "AB", 0)])
        ba = score_cell(cache[cache_key(row, "BA", 0)])
        classification = classify_orders(ab[0], ba[0])
        audited.append({
            "arm": {
                "side": row["side"],
                "coefficient": row["coefficient"],
                "control": row.get("control"),
            },
            "scenario": row["vignette"],
            "source": row["source"],
            "AB": {"effect": ab[0], "off_axis_delta": ab[1], "steered_off_axis": ab[2]},
            "BA": {"effect": ba[0], "off_axis_delta": ba[1], "steered_off_axis": ba[2]},
            "mapped_pair_effect": mean((ab[0], ba[0])),
            "order_result": classification,
        })
    return audited


def summarize(audited: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in audited:
        arm = row["arm"]
        groups[(arm["side"], arm["coefficient"], arm["control"])].append(row)
    summary = {}
    for arm, rows in groups.items():
        classes = defaultdict(int)
        for row in rows:
            classes[row["order_result"]] += 1
        summary[str(arm)] = {
            "scenarios": len(rows),
            "mapped_pair_effect_mean": mean(row["mapped_pair_effect"] for row in rows),
            "strict_reversals": classes["strict_reversal"],
            "tie_disagreements": classes["tie_disagreement"],
            "same_side_or_double_tie": classes["same_side_or_double_tie"],
        }
    return summary


def self_test() -> None:
    assert classify_orders(0.1, -0.1) == "strict_reversal"
    assert classify_orders(0.0, 0.1) == "tie_disagreement"
    assert classify_orders(0.0, 0.0) == "same_side_or_double_tie"
    assert classify_orders(0.1, 0.2) == "same_side_or_double_tie"
    print("J_LENS_DEV_ORDER_AUDIT_SELF_TEST_PASS reversal=true tie=true pair_mean=one_per_scenario")


def main() -> None:
    args = parse_args()
    if args.self_test:
        self_test()
        return
    if args.experiment_id is None or args.output is None:
        raise ValueError("--experiment-id and --output are required unless --self-test")
    rows = experiment_rows(
        args.experiment_id,
        args.profile,
        all_generated=args.control is None,
        control=args.control,
    )
    audited = audit_rows(rows)
    payload = {
        "schema": "j_lens_concept_dev_order_audit_v1",
        "experiment_id": args.experiment_id,
        "control": args.control,
        "profile": args.profile,
        "orders": ["AB", "BA"],
        "sampling": "AB and BA are two order presentations of one scenario-arm pair. mapped_pair_effect is their mean. The pair remains one sample.",
        "summary": summarize(audited),
        "records": audited,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"J_LENS_DEV_ORDER_AUDIT_COMPLETE output={args.output} arms={len(payload['summary'])}")


if __name__ == "__main__":
    main()
