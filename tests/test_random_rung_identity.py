"""Regression: low_extension_0p40 enters the random region without renumbering.

Proves against the committed canonical CSV + live provenance + live manifests:
(a) every pre-existing random row keeps its committed normalized_dose_id
    (append-only fractions, no renumbering);
(b) all 10 extension cells (2 per seed x 5 seeds) map to the single new dose id;
(c) the new rung satisfies the all-five coherence rule per side
    (all seeds measured, all admissible) via calibrated_random_rungs.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from render_dev_comparison import normalized_calibration_dose_id  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
from vjp_steering.results import calibrated_random_rungs  # noqa: E402

NEW_ID = 9
EXT_ID = "low_extension_0p40"


def main() -> None:
    provenance = json.loads((ROOT / "slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json").read_text())
    fractions = provenance["calibration_grid"]["fractions"]
    assert fractions[:9] == [0.66, 0.74375, 0.8275, 0.91125, 0.995, 1.07875, 1.1625, 1.24625, 1.33], "old fractions moved"
    assert fractions[9] == 0.40, "extension fraction must be append-only at id 9"
    assert provenance["calibration_grid"]["extension_rungs"][EXT_ID]["dose_id"] == NEW_ID
    # (a) committed rows keep their ids
    committed = list(csv.DictReader(open(ROOT / "results/dev-comparison.csv")))
    old_random = [r for r in committed if r["method"] == "random"]
    assert old_random, "no random rows in committed CSV"
    for row in old_random:
        exp = row["source_run"]
        manifest = json.loads((ROOT / "outputs/experiments" / exp / "manifest.json").read_text())
        recomputed = normalized_calibration_dose_id(
            float(row["C"]), manifest["boundaries"][row["side"]]["C_approx"], fractions)
        stored = row["normalized_dose_id"]
        stored_id = None if stored in ("", "None") else int(stored)
        assert recomputed == stored_id, f"renumbered {exp} {row['side']} C={row['C']}: {stored_id} -> {recomputed}"
    print(f"RUNG_REGRESSION old ids stable: {len(old_random)} random rows unchanged")
    # (b) extension cells map to the new id, all seeds both sides
    seen = {side: set() for side in ("+C", "-C")}
    for seed in range(5):
        exp = f"v14-dev-random-s{seed}-r2"
        manifest = json.loads((ROOT / "outputs/experiments" / exp / "manifest.json").read_text())
        recorded = manifest["extensions"][EXT_ID]["side_coeffs"]
        for side in ("+C", "-C"):
            assert len(recorded[side]) == 1, f"{exp} {side} rung identity drift"
            got = normalized_calibration_dose_id(
                recorded[side][0], manifest["boundaries"][side]["C_approx"], fractions)
            assert got == NEW_ID, f"{exp} {side} maps to {got}, not {NEW_ID}"
            seen[side].add(seed)
    assert seen == {"+C": {0, 1, 2, 3, 4}, "-C": {0, 1, 2, 3, 4}}, "rung lost seeds"
    print("RUNG_REGRESSION new id 9: 10/10 extension cells, 5/5 seeds per side")
    # (c) rung enters the random region under the all-five coherence rule
    data_rows = []
    for seed in range(5):
        data_rows.extend(
            r for r in csv.DictReader(open(ROOT / f"data/dev/v14-dev-random-s{seed}-r2/results.csv")))
    random_rows = [dict(r, method="random", seed=int(r.get("seed", 0)),
                        C=float(r["C"]), effect=float(r["effect"]),
                        off_axis_perturbation=float(r["off_axis_perturbation"]),
                        admissible=r["admissible"] == "True") for r in data_rows]
    for r in random_rows:
        manifest = json.loads((ROOT / "outputs/experiments" / r["source_run"] / "manifest.json").read_text())
        r["normalized_dose_id"] = normalized_calibration_dose_id(
            r["C"], manifest["boundaries"][r["side"]]["C_approx"], fractions)
    rungs = calibrated_random_rungs(random_rows, {0, 1, 2, 3, 4})
    for side in ("+C", "-C"):
        ids = [rg["rung"] for rg in rungs[side]]
        assert NEW_ID in ids, f"new rung missing from {side} region (ids {ids})"
        rung = next(rg for rg in rungs[side] if rg["rung"] == NEW_ID)
        assert len(rung["points"]) == 5, f"{side} rung has {len(rung['points'])} points, not 5"
    print(f"RUNG_REGRESSION region: +C rungs {[r['rung'] for r in rungs['+C']]}; -C rungs {[r['rung'] for r in rungs['-C']]}")
    print("RUNG_REGRESSION ALL CHECKS PASS")


if __name__ == "__main__":
    main()
