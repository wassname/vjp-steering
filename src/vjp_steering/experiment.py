"""Shared experiment profiles and artifact paths."""

from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
METHOD = "vjp_mlp_up_left_right_shrink"
SHARED_METHOD = "vjp_mlp_up_shared_eb"
METHODS = (METHOD, SHARED_METHOD)
DEFAULT_EXPERIMENT_IDS = {
    METHOD: "mlp-up-left-right-formative-v7-eb-audited",
    SHARED_METHOD: "mlp-up-shared-eb-formative-v1",
}
DEFAULT_EXPERIMENT_ID = DEFAULT_EXPERIMENT_IDS[METHOD]


@dataclass(frozen=True)
class ExperimentProfile:
    name: str
    cohort_size: int
    orders: tuple[str, ...]
    passes: int
    status: str
    data_subdir: str
    results_subdir: str


DEV = ExperimentProfile(
    name="dev",
    cohort_size=15,
    orders=("AB",),
    passes=1,
    status="DEV",
    data_subdir="dev",
    results_subdir="dev",
)
FULL = ExperimentProfile(
    name="full",
    cohort_size=100,
    orders=("AB", "BA"),
    passes=1,
    status="FORMATIVE",
    data_subdir="formative",
    results_subdir="formative",
)


def profile(dev: bool) -> ExperimentProfile:
    return DEV if dev else FULL


def experiment_dir(experiment_id: str) -> Path:
    return ROOT / "outputs" / "experiments" / experiment_id


def manifest_path(experiment_id: str) -> Path:
    return experiment_dir(experiment_id) / "manifest.json"


def data_dir(profile_: ExperimentProfile, experiment_id: str) -> Path:
    return ROOT / "data" / profile_.data_subdir / experiment_id


def results_dir(profile_: ExperimentProfile, experiment_id: str) -> Path:
    return ROOT / "results" / profile_.results_subdir / experiment_id
