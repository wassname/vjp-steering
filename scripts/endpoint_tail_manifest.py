"""Build and validate the raw endpoint-tail cells for the later coherence judge."""

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "endpoint_tail_manifest_v1"
TAIL_FRACTION = 0.66
COHORT_PATH = Path("data/bullshit_bench_v2.jsonl")
METHOD_SEEDS = {
    "vjp_delta": (0, 1, 2),
    "mean_diff": (0, 1, 2),
    "pca": (0, 1, 2),
    "J_word": (0,),
    "vjp_mlp_up_shrink": (0, 1, 2),
}
CONTINUATION_SIDES = tuple(
    (method, seed, "+C")
    for method, seeds in METHOD_SEEDS.items()
    for seed in seeds
    if method != "pca"
)
HISTORICAL_SIDES = tuple(
    (method, seed, sign)
    for method, seeds in METHOD_SEEDS.items()
    for seed in seeds
    for sign in (("-C", "+C") if method == "pca" else ("-C",))
)
GRID = tuple(2.0 ** (n / 6) for n in range(-30, 85))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/endpoint_tail_manifest.json")
    parser.add_argument("--allow-missing-continuations", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bare_digest(rows: list[dict]) -> str:
    return hashlib.sha256(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows).encode()
    ).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def resolve(path: str) -> Path:
    candidate = ROOT / path
    assert candidate.is_file(), f"missing manifest source: {path}"
    return candidate


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def cohort() -> tuple[list[dict], str]:
    rows = read_jsonl(ROOT / COHORT_PATH)
    assert len(rows) == 100
    assert len({row["scenario"] for row in rows}) == len(rows)
    digest = hashlib.sha256(
        json.dumps(
            [[row["scenario"], row["prompt"]] for row in rows],
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    return rows, digest


def tail_members(c_lo: float) -> tuple[list[float], int, list[float]]:
    grid = [coefficient for coefficient in GRID if coefficient < c_lo]
    grid.append(c_lo)
    assert grid == sorted(set(grid))
    tail_start = math.ceil(TAIL_FRACTION * len(grid))
    tail = grid[tail_start:]
    assert tail and tail[-1] == c_lo
    return grid, tail_start, tail


def first_failure(certificate: dict, sign: str) -> int:
    indices = [index for index, rung in enumerate(certificate["rungs"]) if rung[sign]["breakdown_reasons"]]
    assert indices, f"historical {certificate['method']} s{certificate['seed']} {sign} has no first failure"
    failure_index = indices[0]
    assert failure_index > 0, f"historical {certificate['method']} s{certificate['seed']} {sign} has no clean lower rung"
    return failure_index


def artifact_path(run_dir: str, method: str) -> Path:
    path = resolve(f"{run_dir}/{method}.json")
    return path


def validate_artifact(artifact: dict, method: str, seed: int, coefficient: float) -> None:
    assert artifact["status"] == "RESULT"
    assert artifact["method"] == method and artifact["seed"] == seed
    assert math.isclose(artifact["fixed_coefficient_magnitude"], coefficient, rel_tol=1e-12)
    assert artifact["cohort_size"] == 100
    assert artifact["persona"] == "sycophancy_abrasive"
    assert artifact["axis"] == "sycophancy"
    assert artifact["demo_set"] == "sycophancy_all100"
    assert artifact["eval_version"] == 10


def rows_for_side(source: Path, side: str, cohort_rows: list[dict]) -> dict[str, dict]:
    records = read_jsonl(source)
    selected = [row for row in records if row.get("steer_direction") == side]
    assert len(selected) == 100, f"expected 100 {side} rows in {relative(source)}"
    by_scenario = {row["scenario"]: row for row in selected}
    assert len(by_scenario) == len(selected)
    assert set(by_scenario) == {row["scenario"] for row in cohort_rows}
    for cohort_row in cohort_rows:
        assert by_scenario[cohort_row["scenario"]]["prompt"] == cohort_row["prompt"]
    return by_scenario


def canonical_bare(source: Path, cohort_rows: list[dict]) -> tuple[list[dict], str]:
    records = read_jsonl(source)
    bare = [row for row in records if row.get("label") == "bare"]
    assert len(bare) == 100, f"expected 100 bare rows in {relative(source)}"
    by_scenario = {row["scenario"]: row for row in bare}
    assert len(by_scenario) == len(bare)
    assert set(by_scenario) == {row["scenario"] for row in cohort_rows}
    for cohort_row in cohort_rows:
        assert by_scenario[cohort_row["scenario"]]["prompt"] == cohort_row["prompt"]
    return bare, bare_digest(bare)


def historical_endpoint(method: str, seed: int, sign: str, cohort_rows: list[dict], cohort_sha256: str) -> dict:
    certificate_path = ROOT / "outputs" / f"walk_{method}_s{seed}.json"
    certificate = read_json(certificate_path)
    assert certificate["schema"] == "dose_walk_v1" and certificate["status"] == "COMPLETE"
    assert certificate["method"] == method and certificate["seed"] == seed
    failure_index = first_failure(certificate, sign)
    lo_rung = certificate["rungs"][failure_index - 1]
    hi_rung = certificate["rungs"][failure_index]
    assert lo_rung["coefficient"] < hi_rung["coefficient"]
    assert not lo_rung[sign]["breakdown_reasons"]
    assert hi_rung[sign]["breakdown_reasons"]
    canonical_certificate = read_json(ROOT / "outputs" / f"walk_{method}_s{seed}.json")
    minus_failure_index = first_failure(canonical_certificate, "-C")
    minus_lo_rung = canonical_certificate["rungs"][minus_failure_index - 1]
    minus_hi_rung = canonical_certificate["rungs"][minus_failure_index]
    assert not minus_lo_rung["-C"]["breakdown_reasons"]
    assert minus_hi_rung["-C"]["breakdown_reasons"]
    canonical_source = resolve(f"{minus_lo_rung['run_dir']}/moral_demos.jsonl")
    bare, bare_sha256 = canonical_bare(canonical_source, cohort_rows)
    source_artifact_path = artifact_path(lo_rung["run_dir"], method)
    source_artifact = read_json(source_artifact_path)
    validate_artifact(source_artifact, method, seed, lo_rung["coefficient"])
    assert source_artifact["cohort_sha256"] == cohort_sha256
    rows_for_side(source_artifact_path.parent / "moral_demos.jsonl", sign, cohort_rows)
    _, _, tail = tail_members(lo_rung["coefficient"])
    return {
        "method": method,
        "seed": seed,
        "sign": sign,
        "source_kind": "historical_bracket",
        "tail": tail,
        "raw_steered_artifacts": {
            rung["coefficient"]: artifact_path(rung["run_dir"], method)
            for rung in certificate["rungs"]
            if any(math.isclose(rung["coefficient"], tail_coefficient, rel_tol=1e-12) for tail_coefficient in tail)
        },
        "canonical_bare_source": canonical_source,
        "canonical_bare_sha256": bare_sha256,
        "first_failure": {
            "certificate": relative(certificate_path),
            "certificate_sha256": sha256_bytes(certificate_path),
            "sign": sign,
            "C_lo": lo_rung["coefficient"],
            "C_hi": hi_rung["coefficient"],
            "C_lo_run": lo_rung["run_dir"],
            "C_hi_run": hi_rung["run_dir"],
            "canonical_minus_C_lo": minus_lo_rung["coefficient"],
            "canonical_minus_C_hi": minus_hi_rung["coefficient"],
            "canonical_minus_C_lo_run": minus_lo_rung["run_dir"],
            "canonical_minus_C_hi_run": minus_hi_rung["run_dir"],
        },
    }


def continuation_endpoint(path: Path, cohort_rows: list[dict], cohort_sha256: str) -> dict:
    certificate = read_json(path)
    assert certificate["schema"] == "continuation_side_health_v1"
    assert certificate["status"] == "COMPLETE"
    method, seed, sign = certificate["method"], certificate["seed"], certificate["generated_side"]
    assert (method, seed, sign) in CONTINUATION_SIDES
    search = certificate["search"]
    c_lo, c_hi = search["C_lo"], search["C_hi"]
    trace = search["trace"]
    assert c_lo < c_hi
    trace_by_coefficient = {entry["coefficient"]: entry for entry in trace}
    assert len(trace_by_coefficient) == len(trace)
    assert trace_by_coefficient[c_lo]["health_clean"]
    assert not trace_by_coefficient[c_hi]["health_clean"]
    ordered_trace = sorted(trace, key=lambda entry: entry["coefficient"])
    health = [entry["health_clean"] for entry in ordered_trace]
    assert health == sorted(health, reverse=True), f"nonmonotone continuation health trace: {relative(path)}"
    assert all(entry["health_clean"] for entry in trace if entry["coefficient"] <= c_lo)
    assert all(not entry["health_clean"] for entry in trace if entry["coefficient"] >= c_hi)
    grid, tail_start, tail = tail_members(c_lo)
    assert certificate["tail"] == {"grid": grid, "tail_start": tail_start, "members": tail}
    rungs = certificate["rungs"]
    assert len(rungs) == len(tail)
    assert [rung["coefficient"] for rung in rungs] == tail
    assert [rung["tail_index"] for rung in rungs] == list(range(len(tail)))
    assert all(rung["health_clean"] and not rung["breakdown_reasons"] for rung in rungs)
    provenance = certificate["provenance"]
    historical_certificate_path = resolve(provenance["historical_certificate"])
    assert sha256_bytes(historical_certificate_path) == provenance["historical_certificate_sha256"]
    historical = read_json(historical_certificate_path)
    assert historical["method"] == method and historical["seed"] == seed
    minus_failure_index = first_failure(historical, "-C")
    minus_lo_rung = historical["rungs"][minus_failure_index - 1]
    minus_hi_rung = historical["rungs"][minus_failure_index]
    assert provenance["reused_minus_health_clean_C_lo"] == minus_lo_rung["coefficient"]
    assert provenance["reused_minus_health_failing_C_hi"] == minus_hi_rung["coefficient"]
    assert provenance["reused_minus_health_clean_run"] == minus_lo_rung["run_dir"]
    assert provenance["reused_minus_health_failing_run"] == minus_hi_rung["run_dir"]
    canonical_source = resolve(provenance["bare_source"])
    bare, bare_sha256 = canonical_bare(canonical_source, cohort_rows)
    canonical_bare_provenance = {"source": provenance["bare_source"], "sha256": provenance["bare_sha256"]}
    assert bare_sha256 == canonical_bare_provenance["sha256"]
    raw_steered_artifacts = {}
    for rung in rungs:
        source_artifact_path = artifact_path(rung["run_dir"], method)
        source_artifact = read_json(source_artifact_path)
        validate_artifact(source_artifact, method, seed, rung["coefficient"])
        assert source_artifact["schema"] == "continuation_side_health_v1"
        assert source_artifact["generated_side"] == sign
        assert source_artifact["canonical_bare"] == canonical_bare_provenance
        assert source_artifact["cohort_sha256"] == cohort_sha256
        rows_for_side(source_artifact_path.parent / "moral_demos.jsonl", sign, cohort_rows)
        raw_steered_artifacts[rung["coefficient"]] = source_artifact_path
    return {
        "method": method,
        "seed": seed,
        "sign": sign,
        "source_kind": "continuation_certificate",
        "tail": tail,
        "raw_steered_artifacts": raw_steered_artifacts,
        "canonical_bare_source": canonical_source,
        "canonical_bare_sha256": bare_sha256,
        "first_failure": {
            "certificate": relative(path),
            "certificate_sha256": sha256_bytes(path),
            "sign": sign,
            "C_lo": c_lo,
            "C_hi": c_hi,
            "C_lo_run": trace_by_coefficient[c_lo]["run_dir"],
            "C_hi_run": trace_by_coefficient[c_hi]["run_dir"],
            "canonical_minus_C_lo": minus_lo_rung["coefficient"],
            "canonical_minus_C_hi": minus_hi_rung["coefficient"],
            "canonical_minus_C_lo_run": minus_lo_rung["run_dir"],
            "canonical_minus_C_hi_run": minus_hi_rung["run_dir"],
        },
    }


def cells(endpoint: dict, cohort_rows: list[dict]) -> list[dict]:
    result = []
    for coefficient in endpoint["tail"]:
        raw_artifact_path = endpoint["raw_steered_artifacts"][coefficient]
        raw_source = raw_artifact_path.parent / "moral_demos.jsonl"
        raw_artifact = read_json(raw_artifact_path)
        validate_artifact(raw_artifact, endpoint["method"], endpoint["seed"], coefficient)
        rows_for_side(raw_source, endpoint["sign"], cohort_rows)
        result.append({
            "method": endpoint["method"],
            "seed": endpoint["seed"],
            "sign": endpoint["sign"],
            "C": coefficient,
            "tail_member": True,
            "source_kind": endpoint["source_kind"],
            "raw_steered_source": relative(raw_source),
            "raw_steered_artifact": relative(raw_artifact_path),
            "canonical_bare_source": relative(endpoint["canonical_bare_source"]),
            "canonical_bare_sha256": endpoint["canonical_bare_sha256"],
            "first_failure": endpoint["first_failure"],
        })
    return result


def build_manifest(allow_missing_continuations: bool) -> dict:
    cohort_rows, cohort_sha256 = cohort()
    endpoints = [
        historical_endpoint(method, seed, sign, cohort_rows, cohort_sha256)
        for method, seed, sign in HISTORICAL_SIDES
    ]
    continuation_paths = sorted((ROOT / "outputs").glob("continuation_*_plusC_*.json"))
    continuations = [continuation_endpoint(path, cohort_rows, cohort_sha256) for path in continuation_paths]
    continuation_sides = {(endpoint["method"], endpoint["seed"], endpoint["sign"]) for endpoint in continuations}
    assert len(continuation_sides) == len(continuations), "duplicate continuation certificate side"
    missing = sorted(set(CONTINUATION_SIDES) - continuation_sides)
    unexpected = continuation_sides - set(CONTINUATION_SIDES)
    assert not unexpected, f"unexpected continuation sides: {unexpected}"
    if not allow_missing_continuations:
        assert not missing, f"missing continuation certificates: {missing}"
    manifest_cells = [cell for endpoint in endpoints + continuations for cell in cells(endpoint, cohort_rows)]
    manifest_cells.sort(key=lambda row: (row["method"], row["seed"], row["sign"], row["C"]))
    assert all(row["tail_member"] for row in manifest_cells)
    assert not any(row["method"] == "random" for row in manifest_cells)
    return {
        "schema": SCHEMA,
        "status": "COMPLETE" if not missing else "STAGED",
        "cohort": {"source": str(COHORT_PATH), "sha256": cohort_sha256, "size": len(cohort_rows)},
        "expected_continuation_sides": [
            {"method": method, "seed": seed, "sign": sign}
            for method, seed, sign in CONTINUATION_SIDES
        ],
        "missing_continuation_sides": [
            {"method": method, "seed": seed, "sign": sign}
            for method, seed, sign in missing
        ],
        "cells": manifest_cells,
    }


def validate_manifest(manifest: dict, allow_missing_continuations: bool = False) -> None:
    assert manifest["schema"] == SCHEMA
    cohort_rows, cohort_sha256 = cohort()
    assert manifest["cohort"] == {"source": str(COHORT_PATH), "sha256": cohort_sha256, "size": len(cohort_rows)}
    expected = [
        {"method": method, "seed": seed, "sign": sign}
        for method, seed, sign in CONTINUATION_SIDES
    ]
    assert manifest["expected_continuation_sides"] == expected
    cells_by_side: dict[tuple[str, int, str], list[dict]] = {}
    for cell in manifest["cells"]:
        assert set(cell) == {
            "method", "seed", "sign", "C", "tail_member", "source_kind", "raw_steered_source",
            "raw_steered_artifact", "canonical_bare_source", "canonical_bare_sha256", "first_failure",
        }
        assert cell["tail_member"] is True
        side = (cell["method"], cell["seed"], cell["sign"])
        assert side in set(HISTORICAL_SIDES) | set(CONTINUATION_SIDES)
        assert cell["source_kind"] in {"historical_bracket", "continuation_certificate"}
        raw_artifact_path = resolve(cell["raw_steered_artifact"])
        raw_source = resolve(cell["raw_steered_source"])
        assert raw_artifact_path.parent / "moral_demos.jsonl" == raw_source
        artifact = read_json(raw_artifact_path)
        validate_artifact(artifact, cell["method"], cell["seed"], cell["C"])
        rows_for_side(raw_source, cell["sign"], cohort_rows)
        bare, bare_sha256 = canonical_bare(resolve(cell["canonical_bare_source"]), cohort_rows)
        assert bare_sha256 == cell["canonical_bare_sha256"]
        first = cell["first_failure"]
        certificate_path = resolve(first["certificate"])
        assert sha256_bytes(certificate_path) == first["certificate_sha256"]
        certificate = read_json(certificate_path)
        assert first["sign"] == cell["sign"]
        assert first["C_lo"] < first["C_hi"]
        cells_by_side.setdefault(side, []).append(cell)
    historical_sides = set(HISTORICAL_SIDES)
    assert historical_sides <= set(cells_by_side)
    actual_continuation_sides = set(cells_by_side) & set(CONTINUATION_SIDES)
    missing = sorted(set(CONTINUATION_SIDES) - actual_continuation_sides)
    expected_missing = [
        {"method": method, "seed": seed, "sign": sign}
        for method, seed, sign in missing
    ]
    assert manifest["missing_continuation_sides"] == expected_missing
    assert manifest["status"] == ("COMPLETE" if not missing else "STAGED")
    if not allow_missing_continuations:
        assert not missing, f"missing continuation cells: {missing}"
    for side, side_cells in cells_by_side.items():
        endpoint = historical_endpoint(*side, cohort_rows, cohort_sha256) if side in historical_sides else continuation_endpoint(
            resolve(side_cells[0]["first_failure"]["certificate"]), cohort_rows, cohort_sha256
        )
        expected_tail = endpoint["tail"]
        assert [cell["C"] for cell in sorted(side_cells, key=lambda row: row["C"])] == expected_tail


def judge_rows(manifest_path: Path) -> list[dict]:
    manifest = read_json(manifest_path)
    validate_manifest(manifest)
    cohort_rows, _ = cohort()
    return materialize_judge_rows(manifest, cohort_rows)


def materialize_judge_rows(manifest: dict, cohort_rows: list[dict]) -> list[dict]:
    bare_by_source = {}
    rows = []
    for cell in manifest["cells"]:
        bare_source = cell["canonical_bare_source"]
        if bare_source not in bare_by_source:
            bare_rows, bare_sha256 = canonical_bare(resolve(bare_source), cohort_rows)
            assert bare_sha256 == cell["canonical_bare_sha256"]
            bare_by_source[bare_source] = {row["scenario"]: row for row in bare_rows}
        steered_by_scenario = rows_for_side(resolve(cell["raw_steered_source"]), cell["sign"], cohort_rows)
        for cohort_row in sorted(cohort_rows, key=lambda row: row["scenario"]):
            scenario = cohort_row["scenario"]
            bare = bare_by_source[bare_source][scenario]
            steered = steered_by_scenario[scenario]
            rows.append({
                "run": cell["raw_steered_artifact"],
                "method": cell["method"],
                "side": cell["sign"],
                "vignette": scenario,
                "prompt": cohort_row["prompt"],
                "bare": bare["text"],
                "steered": steered["text"],
                "source": cell["raw_steered_source"],
                "canonical_bare_source": bare_source,
            })
    return rows


def self_test() -> None:
    manifest = build_manifest(allow_missing_continuations=True)
    validate_manifest(manifest, allow_missing_continuations=True)
    historical_sides = {(row["method"], row["seed"], row["sign"]) for row in manifest["cells"] if row["source_kind"] == "historical_bracket"}
    continuation_sides = {(row["method"], row["seed"], row["sign"]) for row in manifest["cells"] if row["source_kind"] == "continuation_certificate"}
    assert historical_sides == set(HISTORICAL_SIDES)
    assert continuation_sides == {("J_word", 0, "+C")}
    assert len(manifest["missing_continuation_sides"]) == 9
    assert manifest["status"] == "STAGED"
    cohort_rows, _ = cohort()
    judgeable_rows = materialize_judge_rows(manifest, cohort_rows)
    assert len(judgeable_rows) == 100 * len(manifest["cells"])
    historical_bare_differences = 0
    for cell in manifest["cells"]:
        if cell["source_kind"] != "historical_bracket":
            continue
        own_bare, own_bare_sha256 = canonical_bare(resolve(cell["raw_steered_source"]), cohort_rows)
        if own_bare_sha256 != cell["canonical_bare_sha256"]:
            historical_bare_differences += 1
            scenario = own_bare[0]["scenario"]
            judged = next(row for row in judgeable_rows if row["run"] == cell["raw_steered_artifact"] and row["vignette"] == scenario)
            canonical_by_scenario = {row["scenario"]: row for row in canonical_bare(resolve(cell["canonical_bare_source"]), cohort_rows)[0]}
            assert judged["bare"] == canonical_by_scenario[scenario]["text"]
    assert historical_bare_differences > 0
    print(f"ENDPOINT_TAIL_SELF_TEST_PASS historical_sides={len(historical_sides)} J_word_tail_cells={sum(row['method'] == 'J_word' and row['sign'] == '+C' for row in manifest['cells'])} historical_bare_differences={historical_bare_differences} missing_continuations=9")


def main() -> None:
    args = parse_args()
    if args.self_test:
        self_test()
        return
    manifest = build_manifest(args.allow_missing_continuations)
    validate_manifest(manifest, allow_missing_continuations=args.allow_missing_continuations)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"ENDPOINT_TAIL_MANIFEST_WRITE status={manifest['status']} cells={len(manifest['cells'])} path={args.output}")


if __name__ == "__main__":
    main()
