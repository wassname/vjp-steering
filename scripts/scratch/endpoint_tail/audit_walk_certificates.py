"""Summarize the boundary evidence present in checked-out walk certificates."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "docs/slop/audit/20260829_existing_walk_coverage.md"


def bracket(rungs: list[dict], side: str) -> str:
    first_broken = next(
        (index for index, rung in enumerate(rungs) if rung[side]["breakdown_reasons"]),
        None,
    )
    if first_broken is None:
        return "not reached"
    assert first_broken > 0
    return f"C_lo={rungs[first_broken - 1]['coefficient']:g}; C_hi={rungs[first_broken]['coefficient']:g}"


def main() -> None:
    rows = []
    for path in sorted((ROOT / "outputs").glob("walk_*.json")):
        if path.name.endswith(".refined-demo.json"):
            continue
        certificate = json.loads(path.read_text())
        last = certificate["rungs"][-1]
        rows.append({
            "method": certificate["method"],
            "seed": certificate["seed"],
            "grid": certificate["grid"],
            "rungs": len(certificate["rungs"]),
            "plus": bracket(certificate["rungs"], "+C"),
            "minus": bracket(certificate["rungs"], "-C"),
            "last_C": last["coefficient"],
            "last_plus": ", ".join(last["+C"]["breakdown_reasons"]) or "coherent",
            "last_minus": ", ".join(last["-C"]["breakdown_reasons"]) or "coherent",
        })

    lines = [
        "# Checked-out walk coverage",
        "",
        "This report reads the existing certificates. It does not measure coherence again.",
        "",
        "| method | seed | grid | rungs | +C boundary | -C boundary | final C | final +C | final -C |",
        "| --- | ---: | --- | ---: | --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['method']} | {row['seed']} | {row['grid']} | {row['rungs']} | "
            f"{row['plus']} | {row['minus']} | {row['last_C']:g} | "
            f"{row['last_plus']} | {row['last_minus']} |"
        )
    lines.extend([
        "",
        "A `not reached` side has no first-failure health bracket. The shared walker stopped after the other side crossed its two-rung breakdown rule. `C_lo` is the last generated health-check-clean dose before the first failed health check; `C_hi` is that first failed dose.",
    ])
    OUTPUT.write_text("\n".join(lines) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
