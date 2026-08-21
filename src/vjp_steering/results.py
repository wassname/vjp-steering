"""Render the public result table and the sycophancy Pareto plot from one CSV."""

import csv
import html
from statistics import mean, median
from html.parser import HTMLParser
from pathlib import Path

import plotly.graph_objects as go


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "results.csv"
METHODS = ("vjp_delta", "mean_diff", "pca", "random")
RANDOM_SEEDS = 10
NAMED_SEEDS = {0, 1, 2}
FIELDS = (
    "model", "tokenizer", "prompt_template", "data_hash", "eval_cohort", "layers",
    "batch_size", "date", "source_run", "method", "seed", "C", "side", "effect",
    "off_axis_perturbation", "admissible",
)
LABELS = {
    "vjp_delta": "vjp_delta (ours)",
    "mean_diff": "mean_diff (baseline)",
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
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or ()) != set(FIELDS):
            raise ValueError(f"results columns must be {FIELDS}")
        rows = list(reader)
    if {row["method"] for row in rows} != set(METHODS):
        raise ValueError("results must contain vjp_delta, mean_diff, pca, and random")
    for field in COHORT_FIELDS:
        values = {row[field] for row in rows}
        if len(values) != 1:
            raise ValueError(f"mixed {field}: {sorted(values)}")
    for row in rows:
        if not row["date"] or not row["source_run"]:
            raise ValueError("each measured row needs date and source_run")
        row["seed"] = int(row["seed"])
        row["C"] = float(row["C"])
        row["effect"] = float(row["effect"])
        row["off_axis_perturbation"] = float(row["off_axis_perturbation"])
        row["admissible"] = row["admissible"].lower() == "true"
    if len({row["seed"] for row in rows if row["method"] == "random"}) != RANDOM_SEEDS:
        raise ValueError(f"the random cone needs exactly {RANDOM_SEEDS} seeds")
    for method in METHODS[:-1]:
        if {row["seed"] for row in rows if row["method"] == method} != NAMED_SEEDS:
            raise ValueError(f"{method} needs exactly seeds {sorted(NAMED_SEEDS)}")
    return rows


def _means(rows: list[dict]) -> list[dict]:
    points = []
    for method in METHODS[:-1]:
        for C in sorted({row["C"] for row in rows if row["method"] == method}):
            for side in ("+C", "-C"):
                arms = [
                    row for row in rows
                    if row["method"] == method and row["C"] == C and row["side"] == side
                    and row["admissible"]
                ]
                if {row["seed"] for row in arms} == NAMED_SEEDS:
                    points.append({"method": method, "C": C, "side": side,
                                   "effect": mean(row["effect"] for row in arms),
                                   "off_axis_perturbation": mean(row["off_axis_perturbation"] for row in arms)})
    return points


def plot(rows: list[dict]) -> go.Figure:
    figure = go.Figure()
    means = _means(rows)
    valid = means + [row for row in rows if row["method"] == "random" and row["admissible"]]
    x_limit = 1.08 * max(abs(row["effect"]) for row in valid)
    random = [row for row in rows if row["method"] == "random"]
    random_seeds = sorted({row["seed"] for row in random})
    random_arm = {(row["seed"], row["C"], row["side"]): row for row in random}
    cone = [(0.0, 0.0, 0.0, 0.0)]
    for C in sorted({row["C"] for row in random}):
        coherent = [
            seed for seed in random_seeds
            if (seed, C, "+C") in random_arm and (seed, C, "-C") in random_arm
            and random_arm[seed, C, "+C"]["admissible"] and random_arm[seed, C, "-C"]["admissible"]
        ]
        if len(coherent) < RANDOM_SEEDS // 2:
            break
        points = [random_arm[seed, C, side] for seed in coherent for side in ("+C", "-C")]
        effects = sorted(row["effect"] for row in points)
        cone.append((median(effects), median(row["off_axis_perturbation"] for row in points),
                     effects[len(effects) // 10], effects[-(len(effects) // 10) - 1]))
    figure.add_trace(go.Scatter(
        x=[point[2] for point in cone] + [point[3] for point in reversed(cone)],
        y=[point[1] for point in cone] + [point[1] for point in reversed(cone)],
        fill="toself", fillcolor="rgba(150,150,150,0.22)",
        line={"color": "rgba(150,150,150,0)", "width": 0}, line_shape="spline", line_smoothing=0.8,
        hoverinfo="skip", showlegend=False,
    ))
    figure.add_trace(go.Scatter(
        x=[0, *(point[0] for point in cone)], y=[0, *(point[1] for point in cone)], mode="lines",
        line={"color": "#999999", "width": 2}, line_shape="spline", line_smoothing=0.8,
        hoverinfo="skip", showlegend=False,
    ))

    colors = {"vjp_delta": "#0072b2", "mean_diff": "#d55e00", "pca": "#999999"}
    for method in METHODS[:-1]:
        method_rows = [row for row in means if row["method"] == method]
        if not method_rows:
            continue
        for side in ("+C", "-C"):
            points = sorted((row for row in method_rows if row["side"] == side), key=lambda row: row["C"])
            if points:
                figure.add_trace(go.Scatter(
                    x=[0, *(row["effect"] for row in points)], y=[0, *(row["off_axis_perturbation"] for row in points)],
                    mode="lines+markers", line={"color": colors[method], "width": 3}, marker={"color": colors[method], "size": 8},
                    text=["bare", *(f"C={row['C']:g}" for row in points)],
                    hovertemplate=f"{LABELS[method]}<br>%{{text}}<br>effect=%{{x:.3f}}<br>damage=%{{y:.3f}}<extra></extra>", showlegend=False,
                ))
        label = min(method_rows, key=lambda row: row["effect"]) if method == "mean_diff" else max(method_rows, key=lambda row: row["effect"])
        xshift = -20 if method == "vjp_delta" else 20 if method == "pca" else 8
        yshift = -8 if method == "pca" else 12
        figure.add_annotation(x=label["effect"], y=label["off_axis_perturbation"], text=LABELS[method], showarrow=False, xanchor="right" if xshift < 0 else "left", xshift=xshift, yshift=yshift, font={"color": colors[method], "size": 14})

    figure.add_trace(go.Scatter(x=[0], y=[0], mode="markers", marker={"color": "#333333", "size": 11, "symbol": "diamond"}, hoverinfo="skip", showlegend=False))
    figure.add_annotation(x=0, y=0, text="bare", showarrow=False, xshift=28, yshift=12, font={"color": "#333333", "size": 14})
    figure.add_annotation(x=cone[-1][0], y=cone[-1][1], text="random median and range", showarrow=False, xshift=12, yshift=12, font={"color": "#777777", "size": 14})
    figure.add_annotation(x=0, y=1, xref="paper", yref="paper", text="clean steer -> abrasive", showarrow=False, xanchor="left", font={"color": "#287a4d", "size": 12})
    figure.add_annotation(x=1, y=1, xref="paper", yref="paper", text="clean steer -> sycophantic", showarrow=False, xanchor="right", font={"color": "#287a4d", "size": 12})
    figure.update_layout(
        title={"text": "VJP steering on Bullshit Bench v2", "x": 0.5, "xanchor": "center"},
        width=1064, height=658, margin={"l": 90, "r": 15, "t": 45, "b": 70},
        font={"color": "#111"}, plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        xaxis={"title": "judge on-axis change", "range": [-x_limit, x_limit], "showline": True, "linecolor": "#333333", "gridcolor": "#e5e5e5", "zeroline": False},
        yaxis={"title": "off-axis damage (lower is better)", "showline": True, "linecolor": "#333333", "gridcolor": "#e5e5e5", "zeroline": False, "autorange": "reversed"},
    )
    return figure


def _summary(rows: list[dict]) -> list[list[str]]:
    means = _means(rows)
    table = []
    for method in METHODS:
        for side in ("-C", "+C"):
            group = [row for row in rows if row["method"] == method and row["side"] == side]
            live = [row for row in (means if method != "random" else group) if row["method"] == method and row["side"] == side]
            peak = max(live, key=lambda row: abs(row["effect"])) if live else None
            table.append([
                method,
                side,
                str(RANDOM_SEEDS if method == "random" else len(NAMED_SEEDS) if live else 0),
                str(len(live)),
                str(sum(not row["admissible"] for row in group)),
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
        "All rows use the same all-100 evaluation cohort. Named-method points are means over three seeds.",
        "The random cone shows ten vectors until fewer than half have two coherent arms. The table reports rejected arms.",
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
        "<!doctype html><meta charset='utf-8'><title>vjp-steering results</title>"
        "<style>body{font:16px system-ui;max-width:900px;margin:2rem auto}"
        "table{border-collapse:collapse}th,td{padding:.35rem .7rem;border-bottom:1px solid #ccc}"
        "th{text-align:left}img{max-width:100%}</style>"
        "<h1>Results</h1><p>All rows use the same all-100 evaluation cohort. Named-method points "
        "are means over three seeds. The figure shows both steering directions. The random cone shows ten vectors until fewer "
        f"than half have two coherent arms. The table reports rejected arms.</p>{figure_html}"
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
