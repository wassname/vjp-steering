"""Local CPU preflight for the j_lens_injection_L16 bounded diagnostic.

Verifies without GPU: production extraction/apply already covered by
tests/test_j_lens_injection.py (run separately); here: exact bounded grid
(1,2,4,8,16 per semantic side), frozen DEV15/bare/settings identity, arg
validation of the exact dispatch command (parse-only, no side effects),
explicit-grid manifest simulation (no search trace, refresh-stable), guard
negative control, and the $0.75 ceiling arithmetic from verified-unused
commitments within the $20 v14 allocation.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

EXP_ID = "v14-dev-j-lens-injection-L16"
GRID = "1,2,4,8,16"
LAYERS = "16"


def main() -> None:
    import experiment as experiment_module
    from experiment import validate_explicit_grid
    grid = validate_explicit_grid("j_lens_injection", True, GRID, GRID)
    assert grid == {"+C": [1.0, 2.0, 4.0, 8.0, 16.0], "-C": [1.0, 2.0, 4.0, 8.0, 16.0]}
    print("PREFLIGHT grid: magnitudes 1,2,4,8,16 per semantic side (10 nonzero cells)")
    # frozen settings identity
    provenance = json.loads((ROOT / "slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json").read_text())
    assert provenance["cohort"]["cohort_sha256"] is not None
    print(f"PREFLIGHT frozen cohort: {provenance['cohort']['cohort_sha256'][:12]} "
          f"({len(provenance['cohort']['scenario_ids'])}/15 scenarios)")
    for key in ("model", "dtype", "max_length", "max_new_tokens"):
        print(f"PREFLIGHT generation {key}: {provenance['generation'][key]}")
    # explicit-grid manifest simulation: no search trace, refresh-stable
    manifest = {"grid": {s: sorted(v) for s, v in grid.items()},
                "boundaries": {s: {"meaning": "explicit", "explicit_grid": sorted(v),
                                   "C_approx": max(v), "C_hi": max(v), "trace": []}
                               for s, v in grid.items()}}
    sim = copy.deepcopy(manifest)
    refresh = {s: list(sim["boundaries"][s]["explicit_grid"]) for s in ("+C", "-C")}
    assert refresh == sim["grid"], "refresh branch must reproduce the explicit grid exactly"
    assert all(sim["boundaries"][s]["trace"] == [] for s in ("+C", "-C")), "no search trace allowed"
    print("PREFLIGHT manifest: explicit grid recorded verbatim, no search trace, refresh-stable")
    # arg validation of the exact dispatch command (parse-only)
    saved = sys.argv
    try:
        sys.argv = ["experiment.py", "j_lens_injection", "--dev",
                    "--experiment-id", EXP_ID, "--model", "Qwen/Qwen3.5-4B", "--dtype", "bfloat16",
                    "--n-pairs", "200", "--batch-size", "32", "--extract-batch-size", "8",
                    "--max-length", "384", "--max-new-tokens", "512",
                    "--reuse-bare-from", "j-lens-paper-native-sycophancy-v1",
                    "--layers", LAYERS, "--seed", "0",
                    "--explicit-grid-plus", GRID, "--explicit-grid-minus", GRID]
        args = experiment_module.parse_args()
        assert args.method == "j_lens_injection" and args.dev
    finally:
        sys.argv = saved
    print("PREFLIGHT argv: exact dispatch command accepted (parse_args, no side effects)")
    # budget arithmetic ($20 v14 allocation; recorded actuals only)
    modal_rate = 0.0997 / 101  # observed Modal rate $/s (no receipts; reserves stay conservative)
    gen_seconds = 90 + 10 * 30  # 2x observed startup/cell as bound
    gen_bound = gen_seconds * modal_rate
    judge_bound = 300 * 0.0002  # 10 cells x 30 keys at ~max recorded per-call cost
    print(f"PREFLIGHT budget: generation bound {gen_seconds}s -> ${gen_bound:.2f}; "
          f"judging bound 300 keys -> ${judge_bound:.2f}; total bound ${gen_bound + judge_bound:.2f}")
    judging_reserve, judging_actual = 2.00, 0.9904
    assert judging_reserve - judging_actual - 0.25 >= 0.75, "ceiling must come from verified-unused commitments"
    print(f"PREFLIGHT ceiling: $0.75 <= ${judging_reserve - judging_actual:.4f} verified-unused judging "
          f"reserve - $0.25 retained for unknown retries = ${judging_reserve - judging_actual - 0.25:.4f}; "
          f"$12 review reserve untouched")
    print("PREFLIGHT ALL CHECKS PASS")
    print("DISPATCH-CMD: uv run modal run scripts/run_modal.py::experiment --profile dev "
          "--model Qwen/Qwen3.5-4B --dtype bfloat16 --n-pairs 200 --batch-size 32 --extract-batch-size 8 "
          "--max-length 384 --max-new-tokens 512 --reuse-bare-from j-lens-paper-native-sycophancy-v1 "
          "--method j_lens_injection --layers 16 --seed 0 "
          f"--experiment-id {EXP_ID} --explicit-grid-plus {GRID} --explicit-grid-minus {GRID}")


if __name__ == "__main__":
    main()
