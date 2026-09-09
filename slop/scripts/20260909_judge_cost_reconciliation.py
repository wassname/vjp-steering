"""Reconcile judge API spend from cost_usd records in judgments.jsonl.

Method: rebuild content-addressed cache keys for every judged v14 DEV cell via
judge.experiment_rows + judge.cache_key, then stream judgments.jsonl once and
collect cost_usd per key. Per-key paid-known = max nonzero record (conservative);
keys with only zero records are UNKNOWN (zeros do not establish free calls);
failed/retried attempts without records remain reserved (unmeasurable here).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from judge import cache_key, experiment_rows  # noqa: E402

EXPERIMENTS = [
    "v14-dev-random-s0-r2", "v14-dev-random-s1-r2", "v14-dev-random-s2-r2",
    "v14-dev-random-s3-r2", "v14-dev-random-s4-r2",
    "v14-dev-mean-diff", "v14-dev-vjp-delta-r2",
    "v14-dev-j-lens-swap", "v14-dev-j-lens-swap-L16",
    "v14-dev-j-lens-unit-L16-corrected",
]
EXTENSION_IDS = {f"v14-dev-random-s{s}-r2" for s in range(5)}


def main() -> None:
    wanted: dict[str, tuple[str, str, float]] = {}  # key -> (exp, side, coeff)
    for exp in EXPERIMENTS:
        rows = experiment_rows(exp, "dev")
        for row in rows:
            for order in ("AB", "BA"):
                key = cache_key(row, order, 0)
                wanted.setdefault(key, (exp, row["side"], row["coefficient"]))
    print(f"v14 keys wanted: {len(wanted)}")
    costs: dict[str, list[float]] = {}
    lines = 0
    with open(ROOT / "outputs/demo_judgments/judgments.jsonl") as f:
        for line in f:
            lines += 1
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = r.get("cache_key")
            if k in wanted:
                costs.setdefault(k, []).append(float(r.get("cost_usd") or 0))
    print(f"scanned lines: {lines}; wanted keys found: {len(costs)}/{len(wanted)}")
    missing = [k for k in wanted if k not in costs]
    print(f"wanted keys with no record: {len(missing)}")
    paid, zero_only = {}, []
    for k, vals in costs.items():
        nz = [v for v in vals if v > 0]
        if nz:
            paid[k] = max(nz)
        else:
            zero_only.append(k)
    print(f"paid-known keys: {len(paid)}; zero-only (UNKNOWN, not free): {len(zero_only)}")
    total = sum(paid.values())
    print(f"v14 paid-known total: ${total:.4f} over {len(paid)} keys")
    ext_keys = [k for k in wanted if wanted[k][0] in EXTENSION_IDS]
    # extension cells: the two 0.40x doses per seed (recompute from manifests)
    ext_set = set()
    for s in range(5):
        m = json.load(open(ROOT / f"outputs/experiments/v14-dev-random-s{s}-r2/manifest.json"))
        for side in ("+C", "-C"):
            ext_set.add((side, m["extensions"]["low_extension_0p40"]["side_coeffs"][side][0]))
    ext_paid, ext_zero, ext_missing = [], [], 0
    for k in wanted:
        exp, side, coeff = wanted[k]
        if exp in EXTENSION_IDS and any(
            s == side and abs(coeff - c) < 1e-9 for s, c in ext_set
        ):
            if k not in costs:
                ext_missing += 1
            elif k in paid:
                ext_paid.append(paid[k])
            else:
                ext_zero.append(k)
    print(f"extension: keys={len(ext_paid)+len(ext_zero)+ext_missing} paid-known={len(ext_paid)} "
          f"zero-only={len(ext_zero)} missing={ext_missing}")
    print(f"extension paid-known total: ${sum(ext_paid):.4f}")
    if ext_paid:
        print(f"extension per-call paid-known: min=${min(ext_paid):.6f} max=${max(ext_paid):.6f}")
    print("RECONCILIATION_DONE")


if __name__ == "__main__":
    main()
