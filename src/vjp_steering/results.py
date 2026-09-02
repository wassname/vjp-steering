"""Render the public result table and the sycophancy Pareto plot from one CSV."""

import argparse
import csv
import html
import json
import math
from statistics import mean, median
from html.parser import HTMLParser
from typing import Iterable
from pathlib import Path

import plotly.graph_objects as go

from vjp_steering.experiment import DEV, FULL, data_dir, results_dir


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "results.csv"
METHODS = (
    "vjp_delta",
    "mean_diff",
    "pca",
    "J_word",
    "vjp_mlp_up_shrink",
    "vjp_mlp_up_left_right_shrink",
    "vjp_mlp_up_shared_eb",
    "vjp_mlp_up_shared_last_token_eb",
    "random",
)
RANDOM_SEEDS = 10
METHOD_SEEDS = {
    "vjp_delta": {0, 1, 2},
    "mean_diff": {0, 1, 2},
    "pca": {0, 1, 2},
    "J_word": {0},
    "vjp_mlp_up_shrink": {0, 1, 2},
    "vjp_mlp_up_left_right_shrink": {0},
    "vjp_mlp_up_shared_eb": {0},
    "vjp_mlp_up_shared_last_token_eb": {0},
}
FIELDS = (
    "model", "tokenizer", "prompt_template", "data_hash", "eval_cohort", "layers",
    "batch_size", "date", "source_run", "method", "seed", "C", "side", "effect",
    "off_axis_perturbation", "admissible",
)
LABELS = {
    "vjp_delta": "vjp_delta (ours)",
    "mean_diff": "mean_diff (baseline)",
    "pca": "PCA",
    "J_word": "J-word",
    "vjp_mlp_up_shrink": "MLP-up VJP",
    "vjp_mlp_up_left_right_shrink": "per-side VJP",
    "vjp_mlp_up_shared_eb": "shared-pair VJP",
    "vjp_mlp_up_shared_last_token_eb": "shared-pair last-token VJP",
}
COHORT_FIELDS = (
    "model",
    "tokenizer",
    "prompt_template",
    "eval_cohort",
)
# data_hash tracks bench version (old 28aa vs new c0b64) but both are sycophancy_all100-v10;
# keep cohort check on eval_cohort, allow bench hash migration without bypassing cohort validation.
# Layers and batch size are reported per method. They differ between method implementations but
# do not change the prompts, model, or judge cohort being compared.


def _rows(
    path: Path = DATA,
    methods: tuple[str, ...] = METHODS,
    method_seeds: dict[str, set[int]] = METHOD_SEEDS,
) -> list[dict]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or ()) != set(FIELDS):
            raise ValueError(f"results columns must be {FIELDS}")
        rows = list(reader)
    if {row["method"] for row in rows} != set(methods):
        raise ValueError(f"results methods differ from expected {methods}")
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
    if "random" in methods and len({row["seed"] for row in rows if row["method"] == "random"}) != RANDOM_SEEDS:
        raise ValueError(f"the random cone needs exactly {RANDOM_SEEDS} seeds")
    for method, seeds in method_seeds.items():
        if {row["seed"] for row in rows if row["method"] == method} != seeds:
            raise ValueError(f"{method} needs exactly seeds {sorted(seeds)}")
    return rows


def _means(
    rows: list[dict],
    methods: tuple[str, ...] = METHODS,
    method_seeds: dict[str, set[int]] = METHOD_SEEDS,
    include_rejected: bool = False,
) -> list[dict]:
    points = []
    for method in (method for method in methods if method != "random"):
        for C in sorted({row["C"] for row in rows if row["method"] == method}):
            for side in ("+C", "-C"):
                rows_at_dose = [
                    row for row in rows
                    if row["method"] == method and row["C"] == C and row["side"] == side
                    and (include_rejected or row["admissible"])
                ]
                if {row["seed"] for row in rows_at_dose} == method_seeds[method]:
                    effect = mean(row["effect"] for row in rows_at_dose)
                    admissible = all(row["admissible"] for row in rows_at_dose)
                    points.append({"method": method, "C": C, "side": side,
                                   "effect": effect,
                                   "off_axis_perturbation": mean(row["off_axis_perturbation"] for row in rows_at_dose),
                                   "admissible": admissible,
                                   "accepted": admissible and (effect > 0 if side == "+C" else effect < 0)})
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


def plot(
    rows: list[dict],
    methods: tuple[str, ...] = METHODS,
    method_seeds: dict[str, set[int]] = METHOD_SEEDS,
    title: str = "VJP steering on Bullshit Bench v2",
    endpoint_coefficients: dict[str, float | None] | None = None,
    smooth: bool = True,
    include_rejected: bool = False,
) -> go.Figure:
    figure = go.Figure()
    means = _means(rows, methods, method_seeds, include_rejected=include_rejected)
    valid = means + [row for row in rows if row["method"] == "random" and row["admissible"]]
    x_limit = 1.08 * max(abs(row["effect"]) for row in valid)
    y_range = (1.08 * max(row["off_axis_perturbation"] for row in valid), -0.07)
    margin = {"l": 75, "r": 10, "t": 40, "b": 58}
    obstacles = [(0.0, 0.0)]
    random = [row for row in rows if row["method"] == "random"]
    if random:
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
        random_peaks = []
        for side, sign in (("+C", 1), ("-C", -1)):
            candidates = [
                {
                    "effect": mean(row["effect"] for row in rows_at_dose),
                    "off_axis_perturbation": mean(row["off_axis_perturbation"] for row in rows_at_dose),
                }
                for C in sorted({row["C"] for row in random})
                if (rows_at_dose := [
                    row for row in random
                    if row["side"] == side and row["C"] == C and row["admissible"]
                ])
            ]
            random_peaks.append(max(candidates, key=lambda row: sign * row["effect"]))
        figure.add_trace(go.Scatter(
            x=[row["effect"] for row in random_peaks],
            y=[row["off_axis_perturbation"] for row in random_peaks],
            mode="markers", marker={"color": "#888888", "size": 8, "symbol": "circle-open"},
            text=["random +C table peak", "random -C table peak"],
            hovertemplate="%{text}<br>effect=%{x:.3f}<br>damage=%{y:.3f}<extra></extra>",
            showlegend=False,
        ))
    colors = {
        "vjp_delta": "#0072b2", "mean_diff": "#d55e00", "pca": "#cc79a7",
        "J_word": "#009e73", "vjp_mlp_up_shrink": "#e69f00",
        "vjp_mlp_up_left_right_shrink": "#6f4aa8",
        "vjp_mlp_up_shared_eb": "#a64d79",
        "vjp_mlp_up_shared_last_token_eb": "#a64d79",
    }
    displayed_endpoints = {}
    for method in (method for method in methods if method != "random"):
        method_rows = [row for row in means if row["method"] == method]
        if not method_rows:
            continue
        for side in ("+C", "-C"):
            points = sorted((row for row in method_rows if row["side"] == side), key=lambda row: row["C"])
            # do not decimate below dense resolution near the tip; keep all if tail is dense
            if len(points) > 16:
                table_peak = max(
                    range(len(points)),
                    key=lambda index: (1 if side == "+C" else -1) * points[index]["effect"],
                )
                idx = sorted(
                    {round(i * (len(points) - 1) / 15) for i in range(16)}
                    | {len(points) - 1, table_peak}
                )
                points = [points[i] for i in idx]
            if points:
                endpoint_C = endpoint_coefficients[side] if endpoint_coefficients is not None else points[-1]["C"]
                endpoint_index = (
                    min(range(len(points)), key=lambda index: abs(points[index]["C"] - endpoint_C))
                    if endpoint_C is not None else None
                )
                if endpoint_index is not None:
                    endpoint = points[endpoint_index]
                    displayed_endpoints[method, side] = (endpoint["effect"], endpoint["off_axis_perturbation"])
                figure.add_trace(go.Scatter(
                    x=[0, *(row["effect"] for row in points)], y=[0, *(row["off_axis_perturbation"] for row in points)],
                    mode="lines+markers", line={"color": colors[method], "width": 3},
                    marker={
                        "color": colors[method],
                        "size": [0, *(12 if index == endpoint_index else 8 for index in range(len(points)))],
                        "symbol": [
                            "circle",
                            *(
                                "x" if index == endpoint_index
                                else "circle" if points[index]["accepted" if include_rejected else "admissible"]
                                else "circle-open"
                                for index in range(len(points))
                            ),
                        ],
                    },
                    line_shape="spline" if smooth else "linear", line_smoothing=0.6 if smooth else 0,
                    text=[
                        "bare",
                        *(f"C={row['C']:g}" + (
                            "" if row["accepted" if include_rejected else "admissible"] else " (rejected)"
                        ) for row in points),
                    ],
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
    if methods == METHODS:
        labels = [
            {"x": displayed_endpoints["pca", "+C"][0], "y": displayed_endpoints["pca", "+C"][1], "text": "PCA", "color": colors["pca"]},
            {"x": displayed_endpoints["mean_diff", "-C"][0], "y": displayed_endpoints["mean_diff", "-C"][1], "text": "mean difference", "color": colors["mean_diff"]},
            {"x": displayed_endpoints["vjp_delta", "+C"][0], "y": displayed_endpoints["vjp_delta", "+C"][1], "text": "VJP-delta", "color": colors["vjp_delta"]},
            {"x": displayed_endpoints["vjp_delta", "-C"][0], "y": displayed_endpoints["vjp_delta", "-C"][1], "text": "× = final plotted dose", "color": "#777777", "angles": (180, 0, 135, -135, 45, -45, 90, -90)},
        ]
        label_methods = (
            "J_word",
            "vjp_mlp_up_shrink",
            "vjp_mlp_up_left_right_shrink",
            "vjp_mlp_up_shared_eb",
            "vjp_mlp_up_shared_last_token_eb",
        )
    else:
        labels = []
        label_methods = tuple(method for method in methods if method != "random")
    labels.extend(
        {
            "x": displayed_endpoints[method, side][0],
            "y": displayed_endpoints[method, side][1],
            "text": f"{LABELS[method]} {side}",
            "color": colors[method],
            "angles": (0, -45, 45, -90, 90, -135, 135, 180)
            if method == "vjp_mlp_up_left_right_shrink" else (90, 45, 135, 0, 180, -45, -135, -90),
        }
        for method in label_methods
        for side in ("+C", "-C")
        if (method, side) in displayed_endpoints
    )
    for annotation in place_labels(
        labels, (-x_limit, x_limit), y_range, obstacles=obstacles,
        fig_w=1064, fig_h=590, margin=margin, font={"size": 15},
        bgcolor="rgba(255,255,255,0.9)", arrowcolor="rgba(45,24,16,0.6)",
    ):
        figure.add_annotation(**annotation)
    if random:
        figure.add_annotation(
            x=1.8, y=0.55, text="null zone of<br>random directions", showarrow=False,
            align="center", font={"color": "#666666", "size": 14},
        )
    figure.add_annotation(x=0, y=1, xref="paper", yref="paper", text="clean steer -> abrasive", showarrow=False, xanchor="left", font={"color": "#287a4d", "size": 14})
    figure.add_annotation(x=1, y=1, xref="paper", yref="paper", text="clean steer -> sycophantic", showarrow=False, xanchor="right", font={"color": "#287a4d", "size": 14})
    figure.add_annotation(x=0.5, y=0, xref="paper", yref="paper", text="mostly side effects", showarrow=False, yshift=18, font={"color": "#c44e52", "size": 14})
    figure.update_layout(
        title={"text": title, "x": 0.5, "xanchor": "center"},
        height=590, margin=margin,
        font={"color": "#111", "size": 15}, plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        xaxis={"title": "judge on-axis change", "range": [-x_limit, x_limit], "showline": True, "linecolor": "#333333", "gridcolor": "#e5e5e5", "zeroline": False},
        yaxis={"title": "off-axis damage (lower is better)", "range": y_range, "showline": True, "linecolor": "#333333", "gridcolor": "#e5e5e5", "zeroline": False},
    )
    return figure


def _summary(
    rows: list[dict],
    methods: tuple[str, ...] = METHODS,
    method_seeds: dict[str, set[int]] = METHOD_SEEDS,
    endpoint_coefficients: dict[str, float | None] | None = None,
    include_rejected: bool = False,
) -> list[list[str]]:
    means = _means(rows, methods, method_seeds, include_rejected=include_rejected)
    scored_rows = []
    for method in methods:
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
            if not live or (endpoint_coefficients is not None and endpoint_coefficients[side] is None):
                peaks[side] = None
            elif endpoint_coefficients is None:
                peaks[side] = max(live, key=lambda row: sign * row["effect"])
            else:
                peaks[side] = min(live, key=lambda row: abs(row["C"] - endpoint_coefficients[side]))
            candidate_count += len(live)
            rejected += (
                sum(not row["accepted"] for row in live)
                if include_rejected else sum(not row["admissible"] for row in group)
            )

        if None in peaks.values():
            score = float("-inf")
            score_text = "—"
        else:
            score = min(
                sign * peaks[side]["effect"] - peaks[side]["off_axis_perturbation"]
                for side, sign in (("-C", -1), ("+C", 1))
            )
            score_text = f"{score:+.3f}"
        scored_rows.append((score, [
            method,
            score_text,
            f"{-peaks['-C']['effect']:.3f}" if peaks["-C"] is not None else "not confirmed",
            f"{peaks['-C']['off_axis_perturbation']:.3f}" if peaks["-C"] is not None else "—",
            f"{peaks['+C']['effect']:.3f}" if peaks["+C"] is not None else "not confirmed",
            f"{peaks['+C']['off_axis_perturbation']:.3f}" if peaks["+C"] is not None else "—",
            str(RANDOM_SEEDS if method == "random" else len(method_seeds[method])),
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
        numeric = [(float(row[column]), row[column]) for row in display if row[column] not in {"—", "not confirmed"}]
        if not numeric:
            continue
        best = sorted(numeric, key=lambda item: item[0], reverse=reverse)[0][1]
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


def _markdown(
    table: list[list[str]],
    intro: tuple[str, ...] = (
        "All rows use the same all-100 evaluation cohort. The table reports each named method's seed count.",
        "The random cone shows ten vectors until fewer than half have two coherent directions. The table reports rejected evaluations.",
    ),
) -> str:
    lines = [
        "# Results",
        "",
        *intro,
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


def _html(
    table: list[list[str]],
    figure_html: str,
    intro: str = (
        "All rows use the same all-100 evaluation cohort. The table reports each named method's seed count. "
        "The figure shows both steering directions. The random cone shows ten vectors until fewer "
        "than half have two coherent directions. The table reports rejected evaluations."
    ),
) -> str:
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
        f"<h1>Results</h1><p>{intro}</p>{figure_html}"
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id")
    parser.add_argument("--profile", choices=("dev", "full"))
    return parser.parse_args()


def render_experiment(experiment_id: str, profile_name: str) -> None:
    profile_ = DEV if profile_name == "dev" else FULL
    results_path = data_dir(profile_, experiment_id) / "results.csv"
    with results_path.open(newline="") as handle:
        methods_found = {row["method"] for row in csv.DictReader(handle)}
    if len(methods_found) != 1:
        raise ValueError(f"experiment results need one method, got {sorted(methods_found)}")
    method = methods_found.pop()
    methods = (method,)
    method_seeds = {method: {0}}
    rows = _rows(results_path, methods, method_seeds)
    selected = json.loads((data_dir(profile_, experiment_id) / "selected.json").read_text())
    endpoint_coefficients = {
        side: selected["sides"][side].get("selected_C")
        for side in ("+C", "-C")
    }
    table = _display_table(_summary(
        rows, methods, method_seeds, endpoint_coefficients, include_rejected=True
    ))
    status = "DEV" if profile_name == "dev" else "FORMATIVE"
    intro_line = (
        f"{status} evidence for {LABELS[method]}: {profile_.cohort_size} questions, "
        f"orders={','.join(profile_.orders)}, passes={profile_.passes}."
    )
    unconfirmed = [side for side, coefficient in endpoint_coefficients.items() if coefficient is None]
    confirmation_note = (
        " No accepted endpoint was confirmed for " + ", ".join(unconfirmed) + "."
        if unconfirmed else ""
    )
    path_note = (
        "Markers are evaluated doses; open markers were rejected; straight connectors show dose order, "
        "not interpolation." + confirmation_note
    )
    markdown_text = _markdown(
        table,
        (intro_line, "This output is separate from the primary publication result.", path_note),
    )
    figure = plot(
        rows,
        methods,
        method_seeds,
        title=f"{status}: {LABELS[method]}",
        endpoint_coefficients=endpoint_coefficients,
        smooth=False,
        include_rejected=True,
    )
    figure_html = figure.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        default_width="100%",
        config={"responsive": True},
        div_id=f"{profile_name}-results-plot",
    )
    html_text = _html(
        table,
        figure_html,
        intro_line + " This output is separate from the primary publication result. " + path_note,
    )
    _check_equivalent(markdown_text, html_text)
    output = results_dir(profile_, experiment_id)
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.md").write_text(markdown_text)
    (output / "index.html").write_text(html_text)
    figure.write_image(output / "plot.png", width=1064, height=590, scale=2)
    print(
        f"EXPERIMENT_RENDER_COMPLETE id={experiment_id} profile={profile_name} "
        f"rows={len(rows)} output={output}"
    )


def main() -> None:
    args = parse_args()
    if args.experiment_id is not None:
        if args.profile is None:
            raise ValueError("experiment render needs --experiment-id and --profile")
        render_experiment(args.experiment_id, args.profile)
        return
    if args.profile is not None:
        raise ValueError("--profile requires --experiment-id")
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
    output = ROOT / "results"
    output.mkdir(exist_ok=True)
    (output / "index.md").write_text(markdown_text)
    (output / "index.html").write_text(html_text)
    figure.write_image(output / "plot.png", width=1064, height=590, scale=2)
    print(f"wrote {len(table)} table rows from {len(rows)} measured evaluations")


if __name__ == "__main__":
    main()
