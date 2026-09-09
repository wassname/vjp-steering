"""Local CPU preflight for the low_extension_0p40 ten-cell random extension.

Checks, without GPU: exact 0.40xC_approx doses from live manifests, frozen
DEV15/bare/settings provenance per seed, no cell-key collisions, arg validation
of the exact dispatch commands (parse-only, no --gpu-stage), manifest-update
simulation (grid/boundaries byte-identical, extensions identity correct), and
the guard negative control (DEV --coefficients-plus must still raise).
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

EXT_ID = "low_extension_0p40"
LAYERS = "6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24"
BASE = ("uv run modal run scripts/run_modal.py::experiment --profile dev --model Qwen/Qwen3.5-4B "
        "--dtype bfloat16 --n-pairs 200 --batch-size 32 --extract-batch-size 8 --max-length 384 "
        "--max-new-tokens 512 --reuse-bare-from j-lens-paper-native-sycophancy-v1 --method random "
        f"--layers {LAYERS}").split()


def main() -> None:
    from experiment import (
        extension_cells_complete,
        record_extension_identity,
        validate_extension_args,
    )
    provenance = json.loads((ROOT / "slop/logs/20260909_j_lens_dev/dev-comparison-provenance.json").read_text())
    expected_cohort = provenance["cohort"]["cohort_sha256"]
    expected_ids = provenance["cohort"]["scenario_ids"]
    gen = provenance["generation"]
    commands = []
    for seed in range(5):
        exp_id = f"v14-dev-random-s{seed}-r2"
        root = ROOT / "outputs" / "experiments" / exp_id
        manifest = json.loads((root / "manifest.json").read_text())
        assert manifest["method"] == "random", exp_id
        assert manifest["cohort_sha256"] == expected_cohort, f"{exp_id} cohort drift"
        for key in ("model", "dtype", "max_length", "max_new_tokens"):
            assert manifest["config"][key] == gen[key], f"{exp_id} generation config drift {key}"
        bare = [json.loads(line) for line in (root / manifest["bare"]["path"]).read_text().splitlines()]
        assert [r["scenario"] for r in bare] == expected_ids, f"{exp_id} bare order drift"
        assert all(r["coefficient"] == 0.0 for r in bare), f"{exp_id} bare not coefficient 0"
        doses: dict[str, list[float]] = {}
        for side in ("+C", "-C"):
            dose = 0.40 * manifest["boundaries"][side]["C_approx"]
            assert dose > 0
            key = f"{dose:.12g}"
            assert key not in manifest.get("cells", {}).get(side, {}), f"{exp_id} {side} dose collision {key}"
            doses[side] = [dose]
        # manifest-update simulation on a copy: grid/boundaries untouched, identity recorded
        before_grid = json.dumps(manifest["grid"], sort_keys=True)
        before_bound = json.dumps(manifest["boundaries"], sort_keys=True)
        sim = copy.deepcopy(manifest)
        recorded = record_extension_identity(sim, EXT_ID, doses)
        assert json.dumps(sim["grid"], sort_keys=True) == before_grid, "grid mutated"
        assert json.dumps(sim["boundaries"], sort_keys=True) == before_bound, "boundaries mutated"
        assert recorded == doses, "identity mismatch"
        assert not extension_cells_complete(sim, root, EXT_ID, doses, 15), "fresh extension must be incomplete"
        cmd = BASE + ["--experiment-id", exp_id, "--seed", str(seed),
                      "--extension-id", EXT_ID,
                      "--extension-plus", repr(doses["+C"][0]),
                      "--extension-minus", repr(doses["-C"][0])]
        flat = {side: values[0] for side, values in doses.items()}
        commands.append((exp_id, flat, cmd))
        print(f"PREFLIGHT {exp_id}: +C={doses['+C'][0]:.6f} -C={doses['-C'][0]:.6f} keys=+{doses['+C'][0]:.12g}/-{doses['-C'][0]:.12g} OK")
    # arg validation of the exact dispatch argv, in-process via parse_args (no side effects).
    import experiment as experiment_module
    saved_argv = sys.argv
    try:
        for exp_id, doses, cmd in commands:
            sys.argv = ["experiment.py", "random", "--dev",
                        "--experiment-id", exp_id, "--model", "Qwen/Qwen3.5-4B", "--dtype", "bfloat16",
                        "--n-pairs", "200", "--batch-size", "32", "--extract-batch-size", "8",
                        "--max-length", "384", "--max-new-tokens", "512",
                        "--reuse-bare-from", "j-lens-paper-native-sycophancy-v1",
                        "--layers", LAYERS, "--seed", exp_id.split("-s")[1][0],
                        "--extension-id", EXT_ID,
                        "--extension-plus", repr(doses["+C"]), "--extension-minus", repr(doses["-C"])]
            args = experiment_module.parse_args()
            assert args.extension_id == EXT_ID and args.dev and args.method == "random"
    finally:
        sys.argv = saved_argv
    print("PREFLIGHT arg validation: 5/5 extension commands accepted (parse_args, no side effects)")
    # negative control: the new reject guard still fires on DEV --coefficients-plus
    try:
        sys.argv = ["experiment.py", "random", "--dev",
                    "--experiment-id", "v14-dev-random-s0-r2", "--coefficients-plus", "0,1",
                    "--coefficients-minus", "0,1"]
        experiment_module.parse_args()
    except ValueError as error:
        assert "DEV grid is calibrated" in str(error), f"wrong rejection: {error}"
    else:
        raise AssertionError("guard negative control failed: DEV --coefficients-plus accepted")
    finally:
        sys.argv = saved_argv
    print("PREFLIGHT guard negative control: DEV --coefficients-plus still rejected")
    print("PREFLIGHT ALL CHECKS PASS")
    for _, _, cmd in commands:
        print("DISPATCH-CMD: " + " ".join(cmd))


if __name__ == "__main__":
    main()
