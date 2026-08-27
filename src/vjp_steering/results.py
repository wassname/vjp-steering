"""Render the public result table and the sycophancy Pareto plot from one CSV."""

import csv
import html
import math
from statistics import mean, median
from html.parser import HTMLParser
from typing import Iterable
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
)
# batch_size stays a reported column but not a cohort key: bare and steered always share a
# batch within a rung, so it only shifts padding numerics, and rungs ran at 4 and at 32


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
                rows_at_dose = [
                    row for row in rows
                    if row["method"] == method and row["C"] == C and row["side"] == side
                    and row["admissible"]
                ]
                if {row["seed"] for row in rows_at_dose} == NAMED_SEEDS:
                    points.append({"method": method, "C": C, "side": side,
                                   "effect": mean(row["effect"] for row in rows_at_dose),
                                   "off_axis_perturbation": mean(row["off_axis_perturbation"] for row in rows_at_dose)})
    return points


def place_labels(
    points: list[dict],
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    *,
    obstacles: Iterable[tuple[float, float]] = (),
    fig_w: int = 1240,
    fig_h: int = 640,
    margin: dict | None = None,
    char_w: float = 6.0,
    line_h: float = 15.0,
    radii: tuple = (40, 62, 88, 118),
    angles: tuple = (90, 45, 135, 0, 180, -45, -135, -90),
    font: dict | None = None,
    bgcolor: str = "rgba(253,250,244,0.72)",
    arrowcolor: str = "rgba(45,24,16,0.35)",
    overlap_cost: float = 50.0,
    overlap_cost_label: float = 1.0 / 50.0,
    pad: float = 7.0,
    edge_pad: float = 4.0,
) -> list[dict]:
    margin = margin or {"l": 90, "r": 90, "t": 70, "b": 70}
    plot_width = fig_w - margin["l"] - margin["r"]
    plot_height = fig_h - margin["t"] - margin["b"]
    (x0, x1), (y0, y1) = x_range, y_range

    def to_pixels(x: float, y: float) -> tuple[float, float]:
        x_pixel = margin["l"] + (x - x0) / (x1 - x0) * plot_width
        y_pixel = margin["t"] + (1 - (y - y0) / (y1 - y0)) * plot_height
        return x_pixel, y_pixel

    anchors = [to_pixels(point["x"], point["y"]) for point in points]
    obstacle_pixels = [to_pixels(x, y) for x, y in obstacles]
    placed = []
    annotations = []

    def cost(center_x: float, center_y: float, box_width: float, box_height: float) -> float:
        left = center_x - box_width / 2
        right = center_x + box_width / 2
        top = center_y - box_height / 2
        bottom = center_y + box_height / 2
        candidate_cost = 0.0
        candidate_cost += max(0.0, edge_pad - left) + max(0.0, right - (fig_w - edge_pad))
        candidate_cost += max(0.0, edge_pad - top) + max(0.0, bottom - (fig_h - edge_pad))
        for point_x, point_y in obstacle_pixels:
            if left - pad <= point_x <= right + pad and top - pad <= point_y <= bottom + pad:
                candidate_cost += overlap_cost
        for placed_x, placed_y, placed_width, placed_height in placed:
            overlap_x = max(0.0, min(right, placed_x + placed_width / 2) - max(left, placed_x - placed_width / 2))
            overlap_y = max(0.0, min(bottom, placed_y + placed_height / 2) - max(top, placed_y - placed_height / 2))
            candidate_cost += overlap_x * overlap_y * overlap_cost_label
        return candidate_cost

    font = font or {"size": 11}
    for point, (anchor_x, anchor_y) in zip(points, anchors, strict=True):
        lines = point["text"].split("<br>")
        box_width = max(len(line) for line in lines) * char_w + 10
        box_height = len(lines) * line_h + 6
        best = None
        for radius in radii:
            for angle in point.get("angles", angles):
                center_x = anchor_x + radius * math.cos(math.radians(angle))
                center_y = anchor_y - radius * math.sin(math.radians(angle))
                candidate = (cost(center_x, center_y, box_width, box_height), center_x, center_y)
                if best is None or candidate[0] < best[0]:
                    best = candidate
                if candidate[0] == 0:
                    break
            if best[0] == 0:
                break
        _, center_x, center_y = best
        placed.append((center_x, center_y, box_width, box_height))
        annotations.append({
            "x": point["x"], "y": point["y"], "text": point["text"], "showarrow": True,
            "ax": center_x - anchor_x, "ay": center_y - anchor_y, "axref": "pixel", "ayref": "pixel",
            "font": {**font, "color": point["color"]}, "align": "center", "bgcolor": bgcolor,
            "arrowhead": 0, "arrowwidth": 1, "arrowcolor": arrowcolor,
        })
    return annotations


def plot(rows: list[dict]) -> go.Figure:
    figure = go.Figure()
    means = _means(rows)
    valid = means + [row for row in rows if row["method"] == "random" and row["admissible"]]
    x_limit = 1.08 * max(abs(row["effect"]) for row in valid)
    y_range = (1.08 * max(row["off_axis_perturbation"] for row in valid), -0.07)
    margin = {"l": 75, "r": 10, "t": 40, "b": 58}
    obstacles = [(0.0, 0.0)]
    random = [row for row in rows if row["method"] == "random"]
    random_seeds = sorted({row["seed"] for row in random})
    random_point = {(row["seed"], row["C"], row["side"]): row for row in random}
    cone = [(0.0, 0.0, 0.0, 0.0)]
    for C in sorted({row["C"] for row in random}):
        coherent = [
            seed for seed in random_seeds
            if (seed, C, "+C") in random_point and (seed, C, "-C") in random_point
            and random_point[seed, C, "+C"]["admissible"] and random_point[seed, C, "-C"]["admissible"]
        ]
        if len(coherent) < RANDOM_SEEDS // 2:
            break
        points = [random_point[seed, C, side] for seed in coherent for side in ("+C", "-C")]
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
    colors = {"vjp_delta": "#0072b2", "mean_diff": "#d55e00", "pca": "#cc79a7"}
    displayed_endpoints = {}
    for method in METHODS[:-1]:
        method_rows = [row for row in means if row["method"] == method]
        if not method_rows:
            continue
        for side in ("+C", "-C"):
            points = sorted((row for row in method_rows if row["side"] == side), key=lambda row: row["C"])
            # log-kernel median: window is fixed in log-C (comparable on coarse vs dense tail)
            if len(points) >= 5:
                import math
                logC = [math.log(row["C"]) for row in points]
                # half-window ~0.15 in log (about one half-octave / log(2)/4) so kernel comparable across grids
                hw = 0.15
                smoothed = []
                for i, row in enumerate(points):
                    win = [points[j] for j, lc in enumerate(logC) if abs(lc - logC[i]) <= hw]
                    if len(win) < 3:
                        win = points[max(0, i - 2):i + 3]
                    smoothed.append({**row,
                                     "effect": median(r["effect"] for r in win),
                                     "off_axis_perturbation": median(r["off_axis_perturbation"] for r in win)})
                points = smoothed
            # do not decimate below dense resolution near the tip; keep all if tail is dense
            if len(points) > 16:
                idx = sorted({round(i * (len(points) - 1) / 15) for i in range(16)} | {len(points) - 1})
                points = [points[i] for i in idx]
            if points:
                displayed_endpoints[method, side] = (points[-1]["effect"], points[-1]["off_axis_perturbation"])
                figure.add_trace(go.Scatter(
                    x=[0, *(row["effect"] for row in points)], y=[0, *(row["off_axis_perturbation"] for row in points)],
                    mode="lines+markers", line={"color": colors[method], "width": 3},
                    marker={"color": colors[method], "size": [0, *([8] * (len(points) - 1)), 12], "symbol": ["circle"] * len(points) + ["x"]},
                    line_shape="spline", line_smoothing=0.6,
                    text=["bare", *(f"C={row['C']:g}" for row in points)],
                    hovertemplate=f"{LABELS[method]}<br>%{{text}}<br>effect=%{{x:.3f}}<br>damage=%{{y:.3f}}<extra></extra>",
                    showlegend=False,
                ))
                series = [(0.0, 0.0), *((row["effect"], row["off_axis_perturbation"]) for row in points)]
                for start, end in zip(series, series[1:]):
                    obstacles.extend(
                        (start[0] + fraction * (end[0] - start[0]), start[1] + fraction * (end[1] - start[1]))
                        for fraction in (0.25, 0.5, 0.75, 1.0)
                    )

    figure.add_trace(go.Scatter(x=[0], y=[0], mode="markers", marker={"color": "#333333", "size": 11, "symbol": "diamond"}, hoverinfo="skip", showlegend=False))
    figure.add_annotation(x=0, y=0, text="bare", showarrow=False, xshift=28, yshift=12, font={"color": "#333333", "size": 14})
    labels = [
        {"x": displayed_endpoints["pca", "+C"][0], "y": displayed_endpoints["pca", "+C"][1], "text": "PCA", "color": colors["pca"]},
        {"x": displayed_endpoints["mean_diff", "-C"][0], "y": displayed_endpoints["mean_diff", "-C"][1], "text": "mean difference", "color": colors["mean_diff"]},
        {"x": displayed_endpoints["vjp_delta", "+C"][0], "y": displayed_endpoints["vjp_delta", "+C"][1], "text": "VJP-delta", "color": colors["vjp_delta"]},
        {"x": displayed_endpoints["vjp_delta", "-C"][0], "y": displayed_endpoints["vjp_delta", "-C"][1], "text": "x = last coherent dose<br>later doses rejected", "color": "#777777", "angles": (180, 0, 135, -135, 45, -45, 90, -90)},
    ]
    for annotation in place_labels(
        labels, (-x_limit, x_limit), y_range, obstacles=obstacles,
        fig_w=1064, fig_h=590, margin=margin, font={"size": 15},
        bgcolor="rgba(255,255,255,0.9)", arrowcolor="rgba(45,24,16,0.6)",
    ):
        figure.add_annotation(**annotation)
    figure.add_annotation(
        x=1.8, y=0.55, text="null zone of<br>random directions", showarrow=False,
        align="center", font={"color": "#666666", "size": 14},
    )
    figure.add_annotation(x=0, y=1, xref="paper", yref="paper", text="clean steer -> abrasive", showarrow=False, xanchor="left", font={"color": "#287a4d", "size": 14})
    figure.add_annotation(x=1, y=1, xref="paper", yref="paper", text="clean steer -> sycophantic", showarrow=False, xanchor="right", font={"color": "#287a4d", "size": 14})
    figure.add_annotation(x=0.5, y=0, xref="paper", yref="paper", text="mostly side effects", showarrow=False, yshift=18, font={"color": "#c44e52", "size": 14})
    figure.update_layout(
        title={"text": "VJP steering on Bullshit Bench v2", "x": 0.5, "xanchor": "center"},
        height=590, margin=margin,
        font={"color": "#111", "size": 15}, plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        xaxis={"title": "judge on-axis change", "range": [-x_limit, x_limit], "showline": True, "linecolor": "#333333", "gridcolor": "#e5e5e5", "zeroline": False},
        yaxis={"title": "off-axis damage (lower is better)", "range": y_range, "showline": True, "linecolor": "#333333", "gridcolor": "#e5e5e5", "zeroline": False},
    )
    return figure


def _summary(rows: list[dict]) -> list[list[str]]:
    means = _means(rows)
    scored_rows = []
    for method in METHODS:
        peaks = {}
        candidate_count = 0
        rejected = 0
        for side, sign in (("-C", -1), ("+C", 1)):
            group = [row for row in rows if row["method"] == method and row["side"] == side]
            if method == "random":
                live = [
                    {
                        "C": C,
                        "effect": mean(row["effect"] for row in rows_at_dose),
                        "off_axis_perturbation": mean(row["off_axis_perturbation"] for row in rows_at_dose),
                    }
                    for C in sorted({row["C"] for row in group})
                    if (rows_at_dose := [row for row in group if row["C"] == C and row["admissible"]])
                ]
            else:
                live = [row for row in means if row["method"] == method and row["side"] == side]
            peaks[side] = max(live, key=lambda row: sign * row["effect"])
            candidate_count += len(live)
            rejected += sum(not row["admissible"] for row in group)

        score = min(
            sign * peaks[side]["effect"] - peaks[side]["off_axis_perturbation"]
            for side, sign in (("-C", -1), ("+C", 1))
        )
        scored_rows.append((score, [
            method,
            f"{score:+.3f}",
            f"{-peaks['-C']['effect']:.3f}",
            f"{peaks['-C']['off_axis_perturbation']:.3f}",
            f"{peaks['+C']['effect']:.3f}",
            f"{peaks['+C']['off_axis_perturbation']:.3f}",
            str(RANDOM_SEEDS if method == "random" else len(NAMED_SEEDS)),
            str(candidate_count),
            str(rejected),
        ]))
    return [row for _, row in sorted(scored_rows, key=lambda item: item[0], reverse=True)]


HEADERS = [
    "method",
    "score↑",
    "-C on-axis↑",
    "-C damage↓",
    "+C on-axis↑",
    "+C damage↓",
    "seeds",
    "N",
    "rejected↓",
]
README_TABLE_START = "<!-- CODEX: generated results table starts -->"
README_TABLE_END = "<!-- CODEX: generated results table ends -->"


def _display_table(table: list[list[str]]) -> list[list[str]]:
    display = [row.copy() for row in table]
    for column, reverse in ((1, True), (2, True), (3, False), (4, True), (5, False)):
        best = sorted(display, key=lambda row: float(row[column]), reverse=reverse)[0][column]
        for row in display:
            if row[column] == best:
                row[column] = f"**{row[column]}**"
    for row in display:
        if row[0] == "random":
            row[0] = "*random*"
    return display


def _markdown_table(table: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(HEADERS) + " |",
        "| " + " | ".join("---" for _ in HEADERS) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in table)
    return "\n".join(lines)


def _markdown(table: list[list[str]]) -> str:
    lines = [
        "# Results",
        "",
        "All rows use the same all-100 evaluation cohort. Named-method points are means over three seeds.",
        "The random cone shows ten vectors until fewer than half have two coherent directions. The table reports rejected evaluations.",
        "",
        "![Judged effect against off-axis change](plot.png)",
        "",
        _markdown_table(table),
    ]
    return "\n".join(lines) + "\n"


def _update_readme(table: list[list[str]]) -> None:
    path = ROOT / "README.md"
    text = path.read_text()
    start = text.index(README_TABLE_START)
    end = text.index(README_TABLE_END) + len(README_TABLE_END)
    generated = f"{README_TABLE_START}\n{_markdown_table(table)}\n{README_TABLE_END}"
    path.write_text(text[:start] + generated + text[end:])


def _html(table: list[list[str]], figure_html: str) -> str:
    def cell(cell: str) -> str:
        if cell.startswith("**") and cell.endswith("**"):
            return f"<strong>{html.escape(cell[2:-2])}</strong>"
        if cell.startswith("*") and cell.endswith("*"):
            return f"<em>{html.escape(cell[1:-1])}</em>"
        return html.escape(cell)

    head = "".join(f"<th>{html.escape(cell)}</th>" for cell in HEADERS)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell(value)}</td>" for value in row) + "</tr>"
        for row in table
    )
    return (
        "<!doctype html><meta charset='utf-8'><title>vjp-steering results</title>"
        "<style>body{font:16px system-ui;max-width:1064px;margin:2rem auto;padding:0 1rem}"
        ".plotly-graph-div{width:100%!important}table{border-collapse:collapse;width:100%}"
        "th,td{padding:.35rem .7rem;border-bottom:1px solid #ccc}"
        "th{text-align:left}img{max-width:100%}</style>"
        "<h1>Results</h1><p>All rows use the same all-100 evaluation cohort. Named-method points "
        "are means over three seeds. The figure shows both steering directions. The random cone shows ten vectors until fewer "
        f"than half have two coherent directions. The table reports rejected evaluations.</p>{figure_html}"
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
        [cell.strip().strip("*") for cell in line.strip("|").split("|")]
        for line in markdown_text.splitlines()
        if line.startswith("|") and "---" not in line
    ]
    parser = _Cells()
    parser.feed(html_text)
    if markdown_rows != parser.rows:
        raise AssertionError("results/index.md and results/index.html table cells differ")


def main() -> None:
    rows = _rows()
    table = _display_table(_summary(rows))
    markdown_text = _markdown(table)
    figure = plot(rows)
    figure_html = figure.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        default_width="100%",
        config={"responsive": True},
        div_id="results-plot",
    )
    html_text = _html(table, figure_html)
    _check_equivalent(markdown_text, html_text)
    _update_readme(table)
    results_dir = ROOT / "results"
    results_dir.mkdir(exist_ok=True)
    (results_dir / "index.md").write_text(markdown_text)
    (results_dir / "index.html").write_text(html_text)
    figure.write_image(results_dir / "plot.png", width=1064, height=590, scale=2)
    print(f"wrote {len(table)} table rows from {len(rows)} measured evaluations")


if __name__ == "__main__":
    main()
