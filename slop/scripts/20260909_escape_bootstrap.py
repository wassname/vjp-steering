"""Bootstrap/permutation uncertainty for the two escape margins (CPU-only, no new API calls).

Uses saved paired AB/BA judgments from outputs/demo_judgments/judgments.jsonl.
Comparisons (all on the frozen DEV15 scenarios, paired by scenario):
  (a) doubt -C4 mean vs -C id9 rung (all five seeds; primary escape margin vs
      best seed s1, plus median context);
  (b) L16 swap +C8.14 mean vs +C id9 rung best and +C id0 rung best (effect and
      damage margins).
Method per margin: paired scenario differences, two-level bootstrap (resample
15 scenarios with replacement; within each drawn scenario resample its two
order cells with replacement, keeping the published mean-then-abs estimator
form), B=20000, 95% percentile CIs; two-sided exact sign-flip permutation
p-value over the 15 paired differences (2^15 = 32768 enumerations).
Intended-direction margin is signed positive-when-candidate-wins.
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
from export import score_cell, signed_axis_effect  # noqa: E402
from render_dev_comparison import normalized_calibration_dose_id  # noqa: E402

B = 20000
RNG = np.random.default_rng(20260909)

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


def load_cell_orders(exp: str, side: str, coeff: float):
    """scenario -> {AB: (eff, dmg_signed), BA: (eff, dmg_signed)}, signed by axis."""
    rows = [r for r in experiment_rows(exp, "dev")
            if r["side"] == side and abs(r["coefficient"] - coeff) < 1e-9]
    assert len(rows) == 15, f"{exp} {side} {coeff}: {len(rows)} rows"
    keys = {(r["vignette"], o): cache_key(r, o, 0) for r in rows for o in ("AB", "BA")}
    recs = {}
    with open(ROOT / "outputs/demo_judgments/judgments.jsonl") as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("cache_key") in keys.values():
                recs[r["cache_key"]] = r
    assert len(recs) == len(keys), f"{exp} {side} {coeff}: {len(recs)}/{len(keys)} records"
    sign = -1.0 if side == "-C" else 1.0
    out = {}
    for r in rows:
        per_order = {}
        for o in ("AB", "BA"):
            cell = score_cell(recs[keys[(r["vignette"], o)]])
            per_order[o] = (sign * cell[0], cell[1])
        out[r["vignette"]] = per_order
    return out


def boot_margin(cand, rung, damage=False, b=B):
    """Paired TWO-LEVEL bootstrap mean difference (candidate wins positive).

    Level 1 resamples scenarios with replacement (the dominant uncertainty);
level 2 resamples the two order cells within each drawn scenario. (A prior
draft averaged over all 15 scenarios every replicate — order noise only —
which understated the CIs; fixed 2026-09-09.)
    """
    scens = sorted(cand.keys())
    assert sorted(rung.keys()) == scens
    n = len(scens)
    diffs = np.zeros((b, n))
    for i, sc in enumerate(scens):
        draws = RNG.integers(0, 2, size=(b, 2))  # order resample per replicate
        ce = np.array([cand[sc]["AB"][0], cand[sc]["BA"][0]])
        re_ = np.array([rung[sc]["AB"][0], rung[sc]["BA"][0]])
        if damage:
            # Published estimator (export.py judged_scenarios / dev-comparison.csv
            # off_axis_perturbation) is abs(mean of order damages), NOT mean of abs:
            # damage can partially cancel across orders before the abs. Match it here.
            cd = np.array([cand[sc]["AB"][1], cand[sc]["BA"][1]])
            rd = np.array([rung[sc]["AB"][1], rung[sc]["BA"][1]])
            diffs[:, i] = np.abs(cd[draws].mean(axis=1)) - np.abs(rd[draws].mean(axis=1))
        else:
            diffs[:, i] = ce[draws].mean(axis=1) - re_[draws].mean(axis=1)
    scen_idx = RNG.integers(0, n, size=(b, n))  # level-1 scenario resample
    means = diffs[np.arange(b)[:, None], scen_idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(means.mean()), float(lo), float(hi), diffs.mean(axis=0)


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
    cand_a = load_cell_orders(*CAND_A)
    cand_b = load_cell_orders(*CAND_B)
    rung_a = {s: load_cell_orders(f"v14-dev-random-s{s}-r2", "-C",
              json.load(open(ROOT / f"outputs/experiments/v14-dev-random-s{s}-r2/manifest.json"))
              ["extensions"]["low_extension_0p40"]["side_coeffs"]["-C"][0]) for s in range(5)}
    rung_b9 = {s: load_cell_orders(f"v14-dev-random-s{s}-r2", "+C",
               json.load(open(ROOT / f"outputs/experiments/v14-dev-random-s{s}-r2/manifest.json"))
               ["extensions"]["low_extension_0p40"]["side_coeffs"]["+C"][0]) for s in range(5)}
    rung_b0 = {s: load_cell_orders(f"v14-dev-random-s{s}-r2", "+C", id0_plus_dose(s, fractions))
               for s in range(5)}
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
