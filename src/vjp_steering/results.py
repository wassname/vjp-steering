"""Render the public result table and the sycophancy Pareto plot from one CSV."""

import csv
import hashlib
import html
import json
import math
from statistics import mean, median
from html.parser import HTMLParser
from typing import Iterable
from pathlib import Path

import plotly.graph_objects as go


ROOT = Path(__file__).resolve().parents[2]
RANDOM_DATA = ROOT / "data" / "random_results.csv"
RANDOM_PROVENANCE = ROOT / "data" / "random_provenance.json"
SELECTED_DATA = ROOT / "data" / "endpoint_tail" / "selected.csv"
METHODS = ("vjp_delta", "mean_diff", "pca", "J_word", "vjp_mlp_up_shrink", "random")
RANDOM_SEEDS = 10
METHOD_SEEDS = {
    "vjp_delta": {0, 1, 2},
    "mean_diff": {0, 1, 2},
    "pca": {0, 1, 2},
    "J_word": {0},
    "vjp_mlp_up_shrink": {0, 1, 2},
}
RANDOM_FIELDS = (
    "model", "tokenizer", "prompt_template", "data_hash", "eval_cohort", "layers",
    "batch_size", "date", "source_run", "method", "seed", "C", "side", "effect",
    "off_axis_perturbation", "admissible",
)
SELECTED_FIELDS = (
    "method", "seed", "side", "C", "source_kind", "source_run", "raw_steered_source",
    "effect", "off_axis_perturbation", "steered_off_axis", "health_clean", "accepted",
    "selected_reason",
)
LABELS = {
    "vjp_delta": "vjp_delta (ours)",
    "mean_diff": "mean_diff (baseline)",
    "pca": "PCA",
    "J_word": "J-word",
    "vjp_mlp_up_shrink": "MLP-up VJP",
}
COHORT_FIELDS = (
    "model",
    "tokenizer",
    "prompt_template",
    "data_hash",
    "eval_cohort",
)
# Layers and batch size are reported per method. They differ between method implementations but
# do not change the prompts, model, or judge cohort being compared.


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _random_rows(path: Path = RANDOM_DATA) -> list[dict]:
    provenance = json.loads(RANDOM_PROVENANCE.read_text())
    if _sha256(path) != provenance["results_sha256"]:
        raise ValueError("random_results.csv hash disagrees with random_provenance.json")
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or ()) != set(RANDOM_FIELDS):
            raise ValueError(f"random results columns must be {RANDOM_FIELDS}")
        rows = list(reader)
    if {row["method"] for row in rows} != {"random"}:
        raise ValueError("random_results.csv must contain only random controls")
    for field in COHORT_FIELDS:
        values = {row[field] for row in rows}
        if len(values) != 1:
            raise ValueError(f"mixed random {field}: {sorted(values)}")
    for row in rows:
        row["seed"] = int(row["seed"])
        row["C"] = float(row["C"])
        row["effect"] = float(row["effect"])
        row["off_axis_perturbation"] = float(row["off_axis_perturbation"])
        row["admissible"] = row["admissible"].lower() == "true"
    if {row["seed"] for row in rows} != set(range(RANDOM_SEEDS)):
        raise ValueError(f"the random cone needs exactly seeds 0 through {RANDOM_SEEDS - 1}")
    return rows


def _endpoint_rows(path: Path = SELECTED_DATA) -> list[dict]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != SELECTED_FIELDS:
            raise ValueError(f"selected endpoint columns must be {SELECTED_FIELDS}")
        rows = list(reader)
    expected = {(method, seed, side) for method, seeds in METHOD_SEEDS.items() for seed in seeds for side in ("+C", "-C")}
    found = {(row["method"], int(row["seed"]), row["side"]) for row in rows}
    if found != expected or len(rows) != len(expected):
        raise ValueError("selected endpoints must contain exactly one row for every method, seed, and sign")
    endpoint_rows = []
    for row in rows:
        if row["accepted"] != "True" or row["health_clean"] != "True":
            raise ValueError("primary results require accepted health-clean endpoints")
        endpoint_rows.append({
            "method": row["method"], "seed": int(row["seed"]), "C": float(row["C"]),
            "side": row["side"], "effect": float(row["effect"]),
            "off_axis_perturbation": float(row["off_axis_perturbation"]), "admissible": True,
        })
    return endpoint_rows


def _rows() -> list[dict]:
    return _endpoint_rows() + _random_rows()


def _means(rows: list[dict]) -> list[dict]:
    points = []
    for method in METHODS[:-1]:
        for side in ("+C", "-C"):
            endpoints = [row for row in rows if row["method"] == method and row["side"] == side]
            if {row["seed"] for row in endpoints} != METHOD_SEEDS[method]:
                raise ValueError(f"{method} {side} needs every selected seed")
            points.append({
                "method": method, "side": side,
                "C": tuple(row["C"] for row in sorted(endpoints, key=lambda row: row["seed"])),
                "effect": mean(row["effect"] for row in endpoints),
                "off_axis_perturbation": mean(row["off_axis_perturbation"] for row in endpoints),
            })
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
    colors = {
        "vjp_delta": "#0072b2", "mean_diff": "#d55e00", "pca": "#cc79a7",
        "J_word": "#009e73", "vjp_mlp_up_shrink": "#e69f00",
    }
    displayed_endpoints = {}
    for method in METHODS[:-1]:
        method_rows = [row for row in means if row["method"] == method]
        if not method_rows:
            continue
        for side in ("+C", "-C"):
            endpoint = next(row for row in method_rows if row["side"] == side)
            displayed_endpoints[method, side] = (endpoint["effect"], endpoint["off_axis_perturbation"])
            coefficients = ", ".join(f"{C:g}" for C in endpoint["C"])
            figure.add_trace(go.Scatter(
                x=[0, endpoint["effect"]], y=[0, endpoint["off_axis_perturbation"]],
                mode="lines+markers", line={"color": colors[method], "width": 3},
                marker={"color": colors[method], "size": [0, 12], "symbol": ["circle", "x"]},
                text=["bare", f"selected C={coefficients}"],
                hovertemplate=f"{LABELS[method]}<br>%{{text}}<br>effect=%{{x:.3f}}<br>damage=%{{y:.3f}}<extra></extra>",
                showlegend=False,
            ))
            start, end = (0.0, 0.0), (endpoint["effect"], endpoint["off_axis_perturbation"])
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
        {"x": displayed_endpoints["vjp_delta", "-C"][0], "y": displayed_endpoints["vjp_delta", "-C"][1], "text": "x = judged endpoint<br>next dose rejected", "color": "#777777", "angles": (180, 0, 135, -135, 45, -45, 90, -90)},
    ]
    labels.extend(
        {
            "x": displayed_endpoints[method, side][0],
            "y": displayed_endpoints[method, side][1],
            "text": f"{LABELS[method]} {side}",
            "color": colors[method],
        }
        for method in ("J_word", "vjp_mlp_up_shrink")
        for side in ("+C", "-C")
        if (method, side) in displayed_endpoints
    )
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
        if method == "random":
            peaks = {}
            for side, sign in (("-C", -1), ("+C", 1)):
                live = [
                    {
                        "effect": mean(row["effect"] for row in rows_at_dose),
                        "off_axis_perturbation": mean(row["off_axis_perturbation"] for row in rows_at_dose),
                    }
                    for C in sorted({row["C"] for row in rows if row["method"] == method})
                    if (rows_at_dose := [row for row in rows if row["method"] == method and row["C"] == C and row["side"] == side and row["admissible"]])
                ]
                peaks[side] = max(live, key=lambda row: sign * row["effect"])
            evidence = "frozen control"
            seed_count = RANDOM_SEEDS
            arm_count = len([row for row in rows if row["method"] == method])
        else:
            peaks = {side: next(row for row in means if row["method"] == method and row["side"] == side) for side in ("-C", "+C")}
            evidence = "judged endpoint"
            seed_count = len(METHOD_SEEDS[method])
            arm_count = len([row for row in rows if row["method"] == method])
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
            str(seed_count), str(arm_count), evidence,
        ]))
    return [row for _, row in sorted(scored_rows, key=lambda item: item[0], reverse=True)]


HEADERS = [
    "method", "score↑", "-C on-axis↑", "-C damage↓", "+C on-axis↑", "+C damage↓",
    "seeds", "arms", "evidence",
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
        "Named rows are each seed/sign's greatest health-clean, judge-accepted tail coefficient. They are not peak target-effect doses.",
        "The frozen random cone shows ten vectors until fewer than half have two coherent directions.",
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
        "<h1>Results</h1><p>Each named row is the greatest health-clean, judge-accepted tail coefficient for that seed and sign, not a peak target-effect dose. "
        "The figure shows both steering directions. The frozen random cone shows ten vectors until fewer "
        f"than half have two coherent directions.</p>{figure_html}"
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


def self_test() -> None:
    rows = _rows()
    endpoints = _endpoint_rows()
    means = _means(rows)
    assert len(endpoints) == 26
    assert len(means) == 10
    mean_negative = next(row for row in means if row["method"] == "mean_diff" and row["side"] == "-C")
    assert mean_negative["effect"] > 0
    assert len(mean_negative["C"]) == 3
    figure = plot(rows)
    assert figure.data[0].fill == "toself"
    mean_negative_trace = next(trace for trace in figure.data if trace.name is None and trace.x[-1] == mean_negative["effect"])
    assert mean_negative_trace.x[-1] > 0
    table = _summary(rows)
    assert all(row[-1] == "judged endpoint" for row in table if row[0] != "random")
    print("PRIMARY_ENDPOINT_RESULTS_SELF_TEST_PASS")


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
    print(f"wrote {len(table)} table rows from {len(rows)} endpoint and random-control rows")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    self_test() if args.self_test else main()
