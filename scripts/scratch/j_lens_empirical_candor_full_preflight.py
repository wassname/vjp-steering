"""Validate the selected empirical-candor full runner without loading a model. — PI/OpenAI Codex"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from experiment import parse_args
from vjp_steering.experiment import FULL, behavior_axis_direction


FULL_ARGS = (
    "j_lens_concept_components",
    "--gpu-stage",
    "--experiment-id", "j-lens-components-empirical-candor-full-v1",
    "--model", "Qwen/Qwen3.5-4B",
    "--dtype", "bfloat16",
    "--n-pairs", "200",
    "--batch-size", "32",
    "--extract-batch-size", "8",
    "--max-length", "384",
    "--max-new-tokens", "512",
    "--coefficients-plus", "0.5",
    "--concept-sides=+C",
    "--component-empirical-candor",
    "--selected-empirical-candor-full",
    "--behavior-target", "candidness",
    "--reuse-component-extraction-from", "j-lens-behavior-components-target-ordered-source-v8",
)


def parsed(argv: tuple[str, ...]):
    previous = sys.argv
    try:
        sys.argv = ["experiment.py", *argv]
        return parse_args()
    finally:
        sys.argv = previous


def main() -> None:
    args = parsed(FULL_ARGS)
    assert not args.dev
    assert args.selected_empirical_candor_full
    assert args.component_empirical_candor
    assert args.concept_sides == ("+C",)
    assert args.coefficients_plus == "0.5"
    assert args.coefficients_minus == ""
    assert args.behavior_target == "candidness"
    assert args.reuse_component_extraction_from == "j-lens-behavior-components-target-ordered-source-v8"
    assert args.random_control_seed is None
    assert args.random_control_coefficient is None
    assert FULL.cohort_size == 100 and FULL.orders == ("AB", "BA") and FULL.passes == 1
    assert behavior_axis_direction("+C", "candidness") == -1

    try:
        parsed(tuple(value for value in FULL_ARGS if value != "--selected-empirical-candor-full"))
    except ValueError as error:
        assert "requires DEV or explicit selected full" in str(error)
    else:
        raise AssertionError("unapproved component full contract parsed")

    runner = (ROOT / "scripts/run_modal.py").read_text()
    assert "def j_lens_component_empirical_candor_full(" in runner
    assert "J_LENS_COMPONENT_EMPIRICAL_CANDOR_FULL_COMPLETE" in runner
    assert 'timeout=15 * 60' in runner

    renderer = (ROOT / "src/vjp_steering/results.py").read_text()
    assert "def render_experiment(experiment_id: str, profile_name: str)" in renderer
    assert "data_dir(profile_, experiment_id) / \"results.csv\"" in renderer
    assert "results_dir(profile_, experiment_id)" in renderer
    assert "data/results.csv" not in renderer

    print(
        "EMPIRICAL_CANDOR_FULL_PREFLIGHT_PASS "
        "cohort=100 orders=AB,BA passes=1 source_side=+C behavior_target=candidness "
        "C=0.5 layers=13-21 mask=all_attended_prefill_positions random_arm=absent "
        "modal_timeout_seconds=900 renderer=formative_experiment_only primary_merge=not_implemented"
    )


if __name__ == "__main__":
    main()
