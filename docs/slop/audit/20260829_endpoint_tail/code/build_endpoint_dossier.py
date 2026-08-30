"""Write a side-by-side health-bracket dossier for checked-out walks."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "docs/slop/audit/20260829_existing_endpoint_dossier.md"


def first_broken_index(rungs: list[dict], side: str) -> int | None:
    return next(
        (index for index, rung in enumerate(rungs) if rung[side]["breakdown_reasons"]),
        None,
    )


def demo(run_dir: Path, side: str) -> dict:
    rows = [json.loads(line) for line in (run_dir / "moral_demos.jsonl").read_text().splitlines()]
    arms = {row["steer_direction"]: row for row in rows if row["scenario"] == rows[0]["scenario"]}
    assert set(arms) == {"", "+C", "-C"}
    return arms[side]


def link(path: Path) -> str:
    return "../../../" + path.relative_to(ROOT).as_posix()


def main() -> None:
    certificates = []
    for path in sorted((ROOT / "outputs").glob("walk_*.json")):
        certificate = json.loads(path.read_text())
        if "rungs" in certificate and "state" in certificate:
            certificates.append(certificate)

    lines = [
        "# Checked-out endpoint dossier",
        "",
        "This report reads checked-out artifacts. It does not claim that a health-check-clean output is a semantically coherent answer.",
        "",
        "`C_lo` is the last generated rung before the first health failure. `C_hi` is that first failure. This first-failure rule migrates the historical two-failure-stop certificates into one rule that future independent walks will use.",
        "",
        "## Continuation status",
        "",
        "| method | seed | side | status | health bracket |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for certificate in certificates:
        for side in ("+C", "-C"):
            index = first_broken_index(certificate["rungs"], side)
            if index is None:
                lines.append(f"| {certificate['method']} | {certificate['seed']} | {side} | needs continuation | no health failure before shared stop |"); continue
            assert index > 0
            lo = certificate["rungs"][index - 1]["coefficient"]
            hi = certificate["rungs"][index]["coefficient"]
            lines.append(f"| {certificate['method']} | {certificate['seed']} | {side} | complete | `C_lo={lo:g}`, `C_hi={hi:g}` |")

    for certificate in certificates:
        tier = "old refined" if certificate["grid"] == "refined" else "new plain log"
        for side in ("+C", "-C"):
            first_failed = first_broken_index(certificate["rungs"], side)
            if first_failed is None:
                continue
            assert first_failed > 0
            coherent_rung = certificate["rungs"][first_failed - 1]
            failed_rung = certificate["rungs"][first_failed]
            coherent_dir = ROOT / coherent_rung["run_dir"]
            failed_dir = ROOT / failed_rung["run_dir"]
            health_clean = demo(coherent_dir, side)
            failed = demo(failed_dir, side)
            assert health_clean["prompt"] == failed["prompt"]
            lines.extend([
                "",
                f"## {certificate['method']} / seed {certificate['seed']} / {side} ({tier})",
                "",
                f"- `C_lo={coherent_rung['coefficient']:g}` last health-check-clean rung: [all outputs]({link(coherent_dir / 'moral_demos.jsonl')})",
                f"- `C_hi={failed_rung['coefficient']:g}` first health-failing rung: [all outputs]({link(failed_dir / 'moral_demos.jsonl')})",
                "",
                "### Prompt",
                "",
                "```text",
                health_clean["prompt"],
                "```",
                "",
                "### Last health-check-clean output",
                "",
                "```text",
                health_clean["text"],
                "```",
                "",
                "### First health-failing output",
                "",
                "```text",
                failed["text"],
                "```",
            ])
    OUTPUT.write_text("\n".join(lines) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
