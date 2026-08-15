"""Render the public result table and the candour Pareto plot from one CSV."""

import csv
import html
from html.parser import HTMLParser
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "results.csv"
METHODS = ("vjp_delta", "mean_diff", "pca", "random")
COHORT_FIELDS = (
    "model",
    "tokenizer",
    "prompt_template",
    "data_hash",
    "eval_cohort",
    "layers",
    "batch_size",
)


def _rows(path: Path = DATA) -> list[dict]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if {row["method"] for row in rows} != set(METHODS):
        raise ValueError("results must contain vjp_delta, mean_diff, pca, and random")
    for field in COHORT_FIELDS:
        values = {row[field] for row in rows}
        if len(values) != 1:
            raise ValueError(f"mixed {field}: {sorted(values)}")
    for row in rows:
        row["seed"] = int(row["seed"])
        row["C"] = float(row["C"])
        row["effect"] = float(row["effect"])
        row["off_axis_perturbation"] = float(row["off_axis_perturbation"])
        row["admissible"] = row["admissible"].lower() == "true"
    if len({row["seed"] for row in rows if row["method"] == "random"}) < 3:
        raise ValueError("the random band needs at least three seeds")
    return rows


def _curve(rows: list[dict], grid: np.ndarray) -> np.ndarray:
    points = sorted(
        (
            (row["off_axis_perturbation"], row["effect"])
            for row in rows
            if row["admissible"] and row["effect"] > 0
        )
    )
    if not points:
        return np.full_like(grid, np.nan)
    damage = np.array([0.0, *(point[0] for point in points)])
    effect = np.maximum.accumulate([0.0, *(point[1] for point in points)])
    values = np.interp(grid, damage, effect)
    values[grid > damage[-1]] = np.nan
    return values


def plot(rows: list[dict], output: Path | None = None):
    side = "-C"
    selected = [row for row in rows if row["side"] == side]
    maximum = max(row["off_axis_perturbation"] for row in selected if row["admissible"])
    grid = np.linspace(0, maximum, 160)
    random_curves = np.array([
        _curve([row for row in selected if row["method"] == "random" and row["seed"] == seed], grid)
        for seed in sorted({row["seed"] for row in selected if row["method"] == "random"})
    ])

    figure, axis = plt.subplots(figsize=(7.2, 5.0))
    alive = np.isfinite(random_curves).sum(axis=0)
    low = np.nanmin(random_curves, axis=0)
    high = np.nanmax(random_curves, axis=0)
    mean = np.nanmean(random_curves, axis=0)
    axis.fill_betweenx(grid, low, high, where=alive > 0, color="0.82", label="random directions")
    axis.plot(mean, grid, color="0.35", linewidth=1.5)

    colors = {"vjp_delta": "#08519c", "mean_diff": "#111111", "pca": "#666666"}
    for method in METHODS[:-1]:
        curve = _curve([row for row in selected if row["method"] == method], grid)
        axis.plot(curve, grid, color=colors[method], linewidth=2.2)
        last = np.flatnonzero(np.isfinite(curve))[-1]
        axis.text(curve[last], grid[last], f" {method}", color=colors[method], va="center")

    axis.scatter([0], [0], marker="D", color="black", zorder=5)
    axis.text(0, 0, " bare", va="bottom")
    axis.text(np.nanmax(high), grid[np.nanargmax(high)], " random directions", color="0.35")
    axis.set(xlabel="judged on-axis change", ylabel="absolute judged off-axis change")
    axis.invert_yaxis()
    axis.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    if output is not None:
        figure.savefig(output, dpi=180)
    return figure


def _summary(rows: list[dict]) -> list[list[str]]:
    table = []
    for method in METHODS:
        for side in ("-C", "+C"):
            group = [row for row in rows if row["method"] == method and row["side"] == side]
            live = [row for row in group if row["admissible"]]
            peak = max(live, key=lambda row: row["effect"])
            table.append([
                method,
                side,
                str(len({row["seed"] for row in live})),
                str(len(live)),
                f"{peak['effect']:+.3f}",
                f"{peak['off_axis_perturbation']:.3f}",
            ])
    return table


HEADERS = ["method", "steer dir", "seeds", "arms", "peak on-axis", "damage at peak"]


def _markdown(table: list[list[str]]) -> str:
    lines = [
        "# Results",
        "",
        "All rows use the same all-100 evaluation cohort. The figure shows the candour direction.",
        "",
        "![Judged effect against off-axis change](results.svg)",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "| " + " | ".join("---" for _ in HEADERS) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in table)
    return "\n".join(lines) + "\n"


def _html(table: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(cell)}</th>" for cell in HEADERS)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>"
        for row in table
    )
    return (
        "<!doctype html><meta charset='utf-8'><title>j-steer results</title>"
        "<style>body{font:16px system-ui;max-width:900px;margin:2rem auto}"
        "table{border-collapse:collapse}th,td{padding:.35rem .7rem;border-bottom:1px solid #ccc}"
        "th{text-align:left}img{max-width:100%}</style>"
        "<h1>Results</h1><p>All rows use the same all-100 evaluation cohort. "
        "The figure shows the candour direction.</p><img src='results.svg'>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


class _Cells(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, _attrs):
        if tag == "tr":
            self.row = []
        elif tag in {"th", "td"}:
            self.cell = ""

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in {"th", "td"}:
            self.row.append(self.cell.strip())
            self.cell = None
        elif tag == "tr":
            self.rows.append(self.row)
            self.row = None


def _check_equivalent(markdown_text: str, html_text: str) -> None:
    markdown_rows = [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in markdown_text.splitlines()
        if line.startswith("|") and "---" not in line
    ]
    parser = _Cells()
    parser.feed(html_text)
    if markdown_rows != parser.rows:
        raise AssertionError("results.md and results.html table cells differ")


def main() -> None:
    rows = _rows()
    table = _summary(rows)
    markdown_text = _markdown(table)
    html_text = _html(table)
    _check_equivalent(markdown_text, html_text)
    (ROOT / "results.md").write_text(markdown_text)
    (ROOT / "results.html").write_text(html_text)
    plot(rows, ROOT / "results.svg")
    plot(rows, ROOT / "results.png")
    print(f"wrote {len(table)} table rows from {len(rows)} measured arms")


if __name__ == "__main__":
    main()
