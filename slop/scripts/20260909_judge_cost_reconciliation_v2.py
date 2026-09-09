"""Judge cost reconciliation v2 (supervisor-corrected methodology).

- Duplicate proof: only byte-identical full lines count as duplicate copies of
  one request (two separate API calls never return byte-identical raw text).
  All other same-key records are separately paid requests: summed, not maxed.
- Extension membership built directly from extension cell rows (not via the
  shared wanted dict): a key may coincide with an earlier cell's key.
- Historical vs newly incurred: a key serving only extension cells has all its
  records newly incurred; a key also serving earlier cells keeps its minimum
  record as historical floor, extras as additional paid calls. Zero-only keys
  are UNKNOWN (never free); unrecorded retries stay reserved.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from judge import cache_key, experiment_rows  # noqa: E402

EXPERIMENTS = [
    "v14-dev-random-s0-r2", "v14-dev-random-s1-r2", "v14-dev-random-s2-r2",
    "v14-dev-random-s3-r2", "v14-dev-random-s3-r2".replace("s3", "s3"),
    "v14-dev-random-s4-r2",
    "v14-dev-mean-diff", "v14-dev-vjp-delta-r2",
    "v14-dev-j-lens-swap", "v14-dev-j-lens-swap-L16",
    "v14-dev-j-lens-unit-L16-corrected",
]
EXPERIMENTS = [
    "v14-dev-random-s0-r2", "v14-dev-random-s1-r2", "v14-dev-random-s2-r2",
    "v14-dev-random-s3-r2", "v14-dev-random-s4-r2",
    "v14-dev-mean-diff", "v14-dev-vjp-delta-r2",
    "v14-dev-j-lens-swap", "v14-dev-j-lens-swap-L16",
    "v14-dev-j-lens-unit-L16-corrected",
]


def main() -> None:
    ext_coeffs: dict[str, set[float]] = {}
    for s in range(5):
        m = json.load(open(ROOT / f"outputs/experiments/v14-dev-random-s{s}-r2/manifest.json"))
        ext_coeffs[f"v14-dev-random-s{s}-r2"] = {
            m["extensions"]["low_extension_0p40"]["side_coeffs"][side][0] for side in ("+C", "-C")
        }
    # cell membership oracle: key -> all (exp, side, coeff) judged cells it serves
    cells_of_key: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for exp in EXPERIMENTS:
        for row in experiment_rows(exp, "dev"):
            for order in ("AB", "BA"):
                cells_of_key[cache_key(row, order, 0)].append((exp, row["side"], row["coefficient"]))
    # extension membership directly from extension rows
    ext_keys: set[str] = set()
    for exp, coeffs in ext_coeffs.items():
        for row in experiment_rows(exp, "dev"):
            if any(abs(row["coefficient"] - c) < 1e-9 for c in coeffs):
                for order in ("AB", "BA"):
                    ext_keys.add(cache_key(row, order, 0))
    print(f"extension content keys (directly from extension rows): {len(ext_keys)}")
    print(f"v14 keys wanted: {len(cells_of_key)}")
    records: dict[str, list[float]] = defaultdict(list)
    line_seen: dict[str, int] = defaultdict(int)
    lines = 0
    with open(ROOT / "outputs/demo_judgments/judgments.jsonl") as f:
        for line in f:
            lines += 1
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = r.get("cache_key")
            if k in cells_of_key:
                records[k].append(float(r.get("cost_usd") or 0))
                line_seen[line] += 1
    print(f"scanned {lines} lines; wanted keys with records: {len(records)}/{len(cells_of_key)}")
    byte_dup = sum(c - 1 for c in line_seen.values() if c > 1)
    print(f"byte-identical duplicate lines (provable copies, excluded): {byte_dup}")
    total, npos, nkeys, zero_only, multi = 0.0, 0, 0, 0, 0
    for vals in records.values():
        pos = [v for v in vals if v > 0]
        if pos:
            total += sum(pos)
            npos += len(pos)
            nkeys += 1
            if len(pos) > 1:
                multi += 1
        else:
            zero_only += 1
    print(f"v14 conservative recorded bound: ${total:.4f} across {npos} positive records "
          f"({nkeys} keys); keys with >1 paid record: {multi}; zero-only (unknown): {zero_only}")
    ext_new, ext_hist, ext_new_keys, ext_hist_keys, ext_zero = 0.0, 0.0, 0, 0, 0
    for k in ext_keys:
        vals = [v for v in records.get(k, []) if v > 0]
        if not vals:
            ext_zero += 1
            continue
        earlier = any(
            exp2 not in ext_coeffs or not any(abs(c2 - c) < 1e-9 for c in ext_coeffs[exp2])
            for exp2, _, c2 in cells_of_key.get(k, [])
        )
        if earlier:
            ext_hist += min(vals)
            ext_new += sum(vals) - min(vals)
            ext_hist_keys += 1
        else:
            ext_new += sum(vals)
            ext_new_keys += 1
    print(f"extension newly incurred (conservative): ${ext_new:.4f} over {ext_new_keys} extension-only keys")
    print(f"extension historical floor on shared keys: ${ext_hist:.4f} over {ext_hist_keys} keys")
    print(f"extension zero-only keys (unknown): {ext_zero}")
    print("RECONCILIATION_V2_DONE")


if __name__ == "__main__":
    main()
