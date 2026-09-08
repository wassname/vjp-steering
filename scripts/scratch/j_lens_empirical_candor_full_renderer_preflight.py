"""Exercise selected-full promotion without touching public artifacts. — PI/OpenAI Codex"""

import csv
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from vjp_steering import results


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def source_rows(source_run: str, count: int) -> tuple[dict, list[dict]]:
    with results.DATA.open(newline="") as handle:
        baseline = next(csv.DictReader(handle))
    selected = {
        **baseline,
        "source_run": source_run,
        "method": "j_lens_concept_components",
        "seed": "0",
        "C": "0.5",
        "side": "+C",
        "effect": "-0.68",
        "off_axis_perturbation": "0.10",
        "admissible": "true",
    }
    scenarios = [{"source_run": source_run, "scenario": str(index)} for index in range(count)]
    return selected, scenarios


def source_root(directory: Path, source_run: str, count: int) -> tuple[Path, Path]:
    root = directory / "formative"
    root.mkdir(parents=True)
    selected, scenarios = source_rows(source_run, count)
    write_csv(root / "results.csv", results.FIELDS, [selected])
    write_csv(root / "judged_scenarios.csv", ("source_run", "scenario"), scenarios)
    (root / "selected.json").write_text(json.dumps({"sides": {"+C": {"selected_C": 0.5}}}))
    manifest = directory / "manifest.json"
    manifest.write_text(json.dumps({
        "profiles": {"full": {"status": "FORMATIVE", "generated": True, "cohort_size": 100}},
        "candidate": {"source_side": "+C", "behavior_target": "candidness"},
    }))
    return root, manifest


def main() -> None:
    primary_before = sha256(results.DATA)
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        primary = directory / "results.csv"
        primary.write_bytes(results.DATA.read_bytes())
        source, manifest = source_root(directory / "complete", "selected-full-test", 100)
        results.promote_selected_full(
            "selected-full-test", primary_path=primary, source_root=source, manifest_file=manifest,
        )
        methods, method_seeds = results.primary_methods(primary)
        assert methods[-1] == "j_lens_concept_components"
        rows = results._rows(primary, methods, method_seeds)
        selected_row = next(row for row in rows if row["method"] == "j_lens_concept_components")
        assert results._behavior_target(selected_row, manifest_file=manifest) == "candidness"
        assert results.behavior_axis_direction("+C", results._behavior_target(selected_row, manifest_file=manifest)) == -1
        results._summary(rows, methods, method_seeds)
        results.plot(rows, methods, method_seeds, include_rejected=True)
        try:
            results.promote_selected_full(
                "selected-full-test", primary_path=primary, source_root=source, manifest_file=manifest,
            )
        except ValueError as error:
            assert "already contain" in str(error)
        else:
            raise AssertionError("promotion accepted a duplicate selected method")

        incomplete, incomplete_manifest = source_root(directory / "incomplete", "incomplete-full-test", 99)
        try:
            results.promote_selected_full(
                "incomplete-full-test", primary_path=directory / "unmodified.csv",
                source_root=incomplete, manifest_file=incomplete_manifest,
            )
        except ValueError as error:
            assert "100 judged scenario rows" in str(error)
        else:
            raise AssertionError("promotion accepted incomplete full judgments")

    assert sha256(results.DATA) == primary_before
    print(
        "EMPIRICAL_CANDOR_FULL_RENDERER_PREFLIGHT_PASS "
        "temporary_primary_only=true full_scenarios=100 source_side=+C behavior_target=candidness "
        "common_axis_direction=-1 incomplete_judgments=rejected public_artifacts_unchanged=true"
    )


if __name__ == "__main__":
    main()
