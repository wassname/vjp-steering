"""Render the public result table and the sycophancy Pareto plot from one CSV."""

import csv
import html
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import plotly.graph_objects as go


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "results.csv"
METHODS = ("vjp_delta", "mean_diff", "pca", "random")
LABELS = {
    "vjp_delta": "VJP-delta",
    "mean_diff": "mean difference",
    "pca": "PCA",
}
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


def plot(rows: list[dict]) -> go.Figure:
    side = "-C"
    selected = [row for row in rows if row["side"] == side]
    maximum = max(row["off_axis_perturbation"] for row in selected if row["admissible"])
    grid = np.linspace(0, maximum, 160)
    random_curves = np.array([
        _curve([row for row in selected if row["method"] == "random" and row["seed"] == seed], grid)
        for seed in sorted({row["seed"] for row in selected if row["method"] == "random"})
    ])

    alive = np.isfinite(random_curves).sum(axis=0)
    low = np.array([np.min(column[np.isfinite(column)]) if count else np.nan for column, count in zip(random_curves.T, alive)])
    high = np.array([np.max(column[np.isfinite(column)]) if count else np.nan for column, count in zip(random_curves.T, alive)])
    mean = np.array([np.mean(column[np.isfinite(column)]) if count else np.nan for column, count in zip(random_curves.T, alive)])
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=high, y=grid, mode="lines", line={"width": 0}, hoverinfo="skip", showlegend=False))
    figure.add_trace(go.Scatter(
        x=low, y=grid, mode="lines", fill="tonextx", fillcolor="rgba(130, 130, 130, 0.25)",
        line={"width": 0}, hoverinfo="skip", showlegend=False,
    ))
    figure.add_trace(go.Scatter(x=mean, y=grid, mode="lines", line={"color": "#666666", "width": 1.5}, hoverinfo="skip", showlegend=False))

    colors = {"vjp_delta": "#0072b2", "mean_diff": "#d55e00", "pca": "#666666"}
    for method in METHODS[:-1]:
        method_rows = [row for row in selected if row["method"] == method]
        curve = _curve(method_rows, grid)
        if not np.isfinite(curve).any():
            continue
        figure.add_trace(go.Scatter(
            x=curve, y=grid, mode="lines", line={"color": colors[method], "width": 3},
            hoverinfo="skip", showlegend=False,
        ))
        points = sorted((row for row in method_rows if row["admissible"] and row["effect"] > 0), key=lambda row: row["off_axis_perturbation"])
        figure.add_trace(go.Scatter(
            x=[row["effect"] for row in points], y=[row["off_axis_perturbation"] for row in points],
            mode="markers", marker={"color": colors[method], "size": 8},
            text=[f"C={row['C']:g}" for row in points], hovertemplate=f"{LABELS[method]}<br>%{{text}}<br>effect=%{{x:.3f}}<br>damage=%{{y:.3f}}<extra></extra>",
            showlegend=False,
        ))
        last = np.flatnonzero(np.isfinite(curve))[-1]
        figure.add_annotation(x=curve[last], y=grid[last], text=LABELS[method], showarrow=False, xshift=8, font={"color": colors[method], "size": 14})

    figure.add_trace(go.Scatter(x=[0], y=[0], mode="markers", marker={"color": "#333333", "size": 11, "symbol": "diamond"}, hoverinfo="skip", showlegend=False))
    figure.add_annotation(x=0, y=0, text="bare", showarrow=False, xshift=28, yshift=12, font={"color": "#333333", "size": 14})
    figure.add_annotation(x=np.nanmax(high), y=grid[np.nanargmax(high)], text="random mean and range", showarrow=False, xshift=12, font={"color": "#666666", "size": 14})
    figure.update_layout(
        title="Sycophancy reduction: 100 Bullshit Benchmark questions",
        width=900, height=550, margin={"l": 80, "r": 30, "t": 65, "b": 70},
        plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        xaxis={"title": "judged movement away from sycophancy", "showline": True, "linecolor": "#333333", "gridcolor": "#e5e5e5", "zeroline": False},
        yaxis={"title": "absolute judged off-axis change (lower is better)", "showline": True, "linecolor": "#333333", "gridcolor": "#e5e5e5", "zeroline": False, "autorange": "reversed"},
    )
    return figure


def _summary(rows: list[dict]) -> list[list[str]]:
    table = []
    for method in METHODS:
        for side in ("-C", "+C"):
            group = [row for row in rows if row["method"] == method and row["side"] == side]
            live = [row for row in group if row["admissible"]]
            peak = max(live, key=lambda row: row["effect"]) if live else None
            table.append([
                method,
                side,
                str(len({row["seed"] for row in live})),
                str(len(live)),
                str(len(group) - len(live)),
                f"{peak['effect']:+.3f}" if peak else "-",
                f"{peak['off_axis_perturbation']:.3f}" if peak else "-",
            ])
    return table


HEADERS = [
    "method",
    "steer dir",
    "seeds",
    "arms",
    "rejected",
    "peak on-axis",
    "damage at peak",
]


def _markdown(table: list[list[str]]) -> str:
    lines = [
        "# Results",
        "",
        "All rows use the same all-100 evaluation cohort. The figure shows the sycophancy-reducing direction.",
        "The curve uses arms that pass output caps. The table reports rejected arms.",
        "",
        "![Judged effect against off-axis change](results.svg)",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "| " + " | ".join("---" for _ in HEADERS) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in table)
    return "\n".join(lines) + "\n"


def _html(table: list[list[str]], figure_html: str) -> str:
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
        "The figure shows the sycophancy-reducing direction. The curve uses arms that pass "
        f"output caps. The table reports rejected arms.</p>{figure_html}"
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
    figure = plot(rows)
    html_text = _html(table, figure.to_html(full_html=False, include_plotlyjs="cdn"))
    _check_equivalent(markdown_text, html_text)
    (ROOT / "results.md").write_text(markdown_text)
    (ROOT / "results.html").write_text(html_text)
    figure.write_image(ROOT / "results.svg")
    figure.write_image(ROOT / "results.png", scale=2)
    print(f"wrote {len(table)} table rows from {len(rows)} measured arms")


if __name__ == "__main__":
    main()
