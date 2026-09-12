"""Paired-scenario uncertainty for fixed DEV15 comparisons. Author: PI/OpenAI.

Average the saved AB/BA judgments within each scenario, then resample paired
scenarios. Presentation orders are fixed design conditions, not independent
replicate judgments. Damage is abs(mean signed order differences). This does
not estimate new-judge sampling or repeat candidate/dose/comparator selection,
so intervals are conditional comparisons, not confidence bands for a random
region. Positive effect margins favor the candidate; negative damage margins
mean less off-axis change. No new API calls.
"""
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from judge import cache_key, experiment_rows  # noqa: E402
from export import cache_records, score_cell  # noqa: E402
from render_dev_comparison import normalized_calibration_dose_id  # noqa: E402

B = 20000
RNG = np.random.default_rng(20260909)
HISTORICAL_RUBRIC = "results-demo-perresponse-syco-v7"

CAND_A = ("v14-dev-j-lens-injection-L16-doubt", "-C", 4.0)
CAND_B = ("v14-dev-j-lens-swap-L16", "+C", 8.142873158153925)


def id0_plus_dose(seed: int, fractions: list[float]) -> float:
    exp = f"v14-dev-random-s{seed}-r2"
    manifest = json.load(open(ROOT / "outputs/experiments" / exp / "manifest.json"))
    out = []
    for row in experiment_rows(exp, "dev"):
        if row["side"] != "+C":
            continue
        did = normalized_calibration_dose_id(
            row["coefficient"], manifest["boundaries"]["+C"]["C_approx"], fractions)
        if did == 0:
            out.append(row["coefficient"])
    assert len({round(c, 9) for c in out}) == 1, f"seed{seed} id0 ambiguous: {sorted(set(out))}"
    return out[0]


def load_cells(specs):
    """Read all requested cells with one scan of the historical judge cache."""
    rows_by_spec = {}
    for exp, side, coeff in specs:
        rows = [r for r in experiment_rows(exp, "dev")
                if r["side"] == side and abs(r["coefficient"] - coeff) < 1e-9]
        assert len(rows) == len({r["vignette"] for r in rows}) == 15
        rows_by_spec[exp, side, coeff] = rows
    keys = {cache_key(r, o, 0, rubric=HISTORICAL_RUBRIC)
            for rows in rows_by_spec.values() for r in rows for o in ("AB", "BA")}
    records = cache_records(keys, rubric=HISTORICAL_RUBRIC)
    assert keys == records.keys(), f"missing {len(keys - records.keys())} historical judgments"
    cells = {}
    for spec, rows in rows_by_spec.items():
        sign = -1.0 if spec[1] == "-C" else 1.0
        cells[spec] = {}
        for row in rows:
            cells[spec][row["vignette"]] = {}
            for order in ("AB", "BA"):
                effect, damage, _ = score_cell(records[cache_key(row, order, 0, rubric=HISTORICAL_RUBRIC)])
                cells[spec][row["vignette"]][order] = (sign * effect, damage)
    return cells


def boot_margin(cand, rung, damage=False, b=B):
    """Observed difference and paired-scenario percentile interval. PI/OpenAI."""
    scens = sorted(cand)
    assert sorted(rung) == scens and scens
    metric = 1 if damage else 0
    candidate_means = scenario_means(cand)[metric]
    comparator_means = scenario_means(rung)[metric]
    diffs = np.array([candidate_means[sc] - comparator_means[sc] for sc in scens])
    scen_idx = RNG.integers(0, len(scens), size=(b, len(scens)))
    means = diffs[scen_idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(diffs.mean()), float(lo), float(hi), diffs


def perm_paired(mean_diffs):
    """Exact two-sided sign-flip p-value for paired differences."""
    n = len(mean_diffs)
    obs = abs(mean_diffs.mean())
    count = 0
    total = 0
    for signs in itertools.product((-1.0, 1.0), repeat=n):
        total += 1
        if abs((mean_diffs * np.array(signs)).mean()) >= obs - 1e-12:
            count += 1
    return count / total


def scenario_means(cell):
    eff = {sc: (cell[sc]["AB"][0] + cell[sc]["BA"][0]) / 2 for sc in cell}
    dmg = {sc: abs(cell[sc]["AB"][1] + cell[sc]["BA"][1]) / 2 for sc in cell}
    return eff, dmg


def main() -> None:
    fractions = json.load(open(
        ROOT / "slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json"))["calibration_grid"]["fractions"]
    extension_specs = {}
    original_specs = {}
    for seed in range(5):
        exp = f"v14-dev-random-s{seed}-r2"
        manifest = json.loads((ROOT / "outputs/experiments" / exp / "manifest.json").read_text())
        for side in ("-C", "+C"):
            dose = manifest["extensions"]["low_extension_0p40"]["side_coeffs"][side][0]
            extension_specs[seed, side] = (exp, side, dose)
        original_specs[seed] = (exp, "+C", id0_plus_dose(seed, fractions))
    cells = load_cells([CAND_A, CAND_B, *extension_specs.values(), *original_specs.values()])
    cand_a, cand_b = cells[CAND_A], cells[CAND_B]
    rung_a = {seed: cells[extension_specs[seed, "-C"]] for seed in range(5)}
    rung_b9 = {seed: cells[extension_specs[seed, "+C"]] for seed in range(5)}
    rung_b0 = {seed: cells[original_specs[seed]] for seed in range(5)}
    print(f"rubric={HISTORICAL_RUBRIC}; paired scenario bootstrap B={B}; AB/BA averaged before resampling")
    print("Conditional on observed candidate/dose/comparator selection; not random-region confidence bands.")
    print(f"cells loaded: doubt-C4, swapL16+C8.14, 5x-C-ext, 5x+C-ext, 5x+C-id0")
    for name, cell in [("doubt-C4", cand_a), ("swapL16+C8.14", cand_b)]:
        eff, dmg = scenario_means(cell)
        print(f"{name}: mean_eff={np.mean(list(eff.values())):+.4f} mean_dmg={np.mean(list(dmg.values())):.4f}")
    # (a) doubt -C4 vs -C id9 seeds; intended margin = seed_mean - cand_mean (negative side)
    print("--- (a) doubt -C4 vs -C id9 rung ---")
    a_diffs = {}
    for s in range(5):
        ce, _ = scenario_means(cand_a)
        se, _ = scenario_means(rung_a[s])
        a_diffs[s] = np.array([se[sc] - ce[sc] for sc in sorted(ce)])
        print(f"  vs s{s}: point margin={a_diffs[s].mean():+.4f} (seed mean {np.mean(list(se.values())):+.4f})")
    # intended margin positive-when-candidate-wins: seed - cand (candidate wins if LOWER)
    best_a = min(range(5), key=lambda s: a_diffs[s].mean())
    print(f"  primary comparator: seed{best_a} (strongest rung point)")
    # paired bootstrap with negated signs so generic boot_margin (cand - rung) yields intended margin
    ce, _ = scenario_means(cand_a)
    se, _ = scenario_means(rung_a[best_a])
    scens = sorted(ce)
    diff = np.array([se[sc] - ce[sc] for sc in scens])  # positive when candidate more negative
    ce_ord = {sc: cand_a[sc] for sc in scens}
    se_ord = {sc: rung_a[best_a][sc] for sc in scens}
    # negate both sides so the generic boot_margin (cand - rung) yields intended margin
    neg_c = {sc: {"AB": (-ce_ord[sc]["AB"][0], ce_ord[sc]["AB"][1]),
                   "BA": (-ce_ord[sc]["BA"][0], ce_ord[sc]["BA"][1])} for sc in scens}
    neg_r = {sc: {"AB": (-se_ord[sc]["AB"][0], se_ord[sc]["AB"][1]),
                   "BA": (-se_ord[sc]["BA"][0], se_ord[sc]["BA"][1])} for sc in scens}
    m, lo, hi, _ = boot_margin(neg_c, neg_r)
    p = perm_paired(diff)
    print(f"  MARGIN vs best seed{best_a}: point={diff.mean():+.4f} 95%CI=[{lo:+.4f},{hi:+.4f}] perm p={p:.4f}")
    med = np.median([np.mean(list(scenario_means(rung_a[s])[0].values())) for s in range(5)])
    print(f"  rung median context: {med:+.4f} (candidate {np.mean(list(ce.values())):+.4f})")
    # (b) swapL16 +C8.14 vs +C id9 best and id0 best
    print("--- (b) swapL16 +C8.14 vs +C id9 / id0 rungs ---")
    be, bd = scenario_means(cand_b)
    for rung_name, rung in (("id9", rung_b9), ("id0", rung_b0)):
        seed_means = {s: np.mean(list(scenario_means(rung[s])[0].values())) for s in range(5)}
        best = max(range(5), key=lambda s: seed_means[s])
        print(f"  {rung_name} seed means: " + " ".join(f"s{s}={seed_means[s]:+.3f}" for s in range(5)))
        m, lo, hi, _ = boot_margin(cand_b, rung[best])
        diff_b = np.array([be[sc] - scenario_means(rung[best])[0][sc] for sc in sorted(be)])
        p = perm_paired(diff_b)
        print(f"  MARGIN vs best ({rung_name} seed{best}): point={diff_b.mean():+.4f} "
              f"95%CI=[{lo:+.4f},{hi:+.4f}] perm p={p:.4f}")
        md_, lo_d, hi_d, _ = boot_margin(cand_b, rung[best], damage=True)
        print(f"  DAMAGE margin (cand - rung, negative = cleaner): point={md_:+.4f} 95%CI=[{lo_d:+.4f},{hi_d:+.4f}]")
    print("BOOTSTRAP_DONE")


if __name__ == "__main__":
    main()
