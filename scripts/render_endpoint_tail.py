"""Render independently selected judged endpoint doses without touching legacy results."""

import argparse
import csv
import html
from collections import defaultdict
from pathlib import Path
from statistics import mean

import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/endpoint_tail/selected.csv"
OUTPUT = ROOT / "results/endpoint_tail"
METHOD_SEEDS = {
    "vjp_delta": {0, 1, 2},
    "mean_diff": {0, 1, 2},
    "pca": {0, 1, 2},
    "J_word": {0},
    "vjp_mlp_up_shrink": {0, 1, 2},
}
LABELS = {
    "vjp_delta": "vjp_delta",
    "mean_diff": "mean_diff",
    "pca": "PCA",
    "J_word": "J-word",
    "vjp_mlp_up_shrink": "MLP-up VJP",
}
COLORS = {
    "vjp_delta": "#0072b2",
    "mean_diff": "#d55e00",
    "pca": "#cc79a7",
    "J_word": "#009e73",
    "vjp_mlp_up_shrink": "#e69f00",
}
HEADERS = ("method", "score", "-C effect", "-C damage", "-C selected C", "+C effect", "+C damage", "+C selected C", "seeds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def read_selected(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        rows = list(csv.DictReader(file))
    expected_fields = {
        "method", "seed", "side", "C", "source_kind", "source_run", "raw_steered_source",
        "effect", "off_axis_perturbation", "steered_off_axis", "health_clean", "accepted", "selected_reason",
    }
    assert set(rows[0]) == expected_fields
    for row in rows:
        row["seed"] = int(row["seed"])
        row["C"] = float(row["C"])
        row["effect"] = float(row["effect"])
        row["off_axis_perturbation"] = float(row["off_axis_perturbation"])
        assert row["side"] in {"-C", "+C"}
        assert row["health_clean"] == "True" and row["accepted"] == "True"
    expected_arms = {(method, seed, side) for method, seeds in METHOD_SEEDS.items() for seed in seeds for side in ("-C", "+C")}
    assert {(row["method"], row["seed"], row["side"]) for row in rows} == expected_arms
    assert len(rows) == len(expected_arms)
    return rows


def aggregate(rows: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["method"], row["side"]].append(row)
    summaries = []
    for method in METHOD_SEEDS:
        sides = {}
        for side in ("-C", "+C"):
            selected = grouped[method, side]
            assert {row["seed"] for row in selected} == METHOD_SEEDS[method]
            sides[side] = {
                "effect": mean(row["effect"] for row in selected),
                "damage": mean(row["off_axis_perturbation"] for row in selected),
                "C": [row["C"] for row in sorted(selected, key=lambda row: row["seed"])],
            }
        score = min(-sides["-C"]["effect"] - sides["-C"]["damage"], sides["+C"]["effect"] - sides["+C"]["damage"])
        summaries.append({"method": method, "score": score, **sides})
    return sorted(summaries, key=lambda row: row["score"], reverse=True)


def fmt_coefficients(values: list[float]) -> str:
    return ", ".join(f"{value:.4g}" for value in values)


def table(summaries: list[dict]) -> list[list[str]]:
    return [
        [
            LABELS[row["method"]], f"{row['score']:+.3f}",
            f"{-row['-C']['effect']:.3f}", f"{row['-C']['damage']:.3f}", fmt_coefficients(row["-C"]["C"]),
            f"{row['+C']['effect']:.3f}", f"{row['+C']['damage']:.3f}", fmt_coefficients(row["+C"]["C"]),
            str(len(METHOD_SEEDS[row["method"]])),
        ]
        for row in summaries
    ]


def markdown(rows: list[list[str]]) -> str:
    lines = [
        "# Independently judged endpoint comparison",
        "",
        "Each seed and sign uses its greatest tail coefficient that passed the health gate and had mean steered off-axis judge score at most 1.5. The table then averages those selected seed endpoints. It does not select the coefficient with the largest target effect.",
        "",
        "![Selected judged endpoints](plot.png)",
        "",
        "| " + " | ".join(HEADERS) + " |",
        "| " + " | ".join("---" for _ in HEADERS) + " |",
        *["| " + " | ".join(row) + " |" for row in rows],
    ]
    return "\n".join(lines) + "\n"


def figure(summaries: list[dict]) -> go.Figure:
    figure = go.Figure()
    for row in summaries:
        method = row["method"]
        points = [row["-C"], row["+C"]]
        figure.add_trace(go.Scatter(
            x=[-points[0]["effect"], points[1]["effect"]],
            y=[points[0]["damage"], points[1]["damage"]],
            mode="lines+markers+text",
            text=["-C", "+C"],
            textposition="top center",
            name=LABELS[method],
            marker={"size": 10, "color": COLORS[method]},
            line={"width": 2, "color": COLORS[method]},
            customdata=[fmt_coefficients(point["C"]) for point in points],
            hovertemplate="%{fullData.name} %{text}<br>effect=%{x:.3f}<br>damage=%{y:.3f}<br>selected C=%{customdata}<extra></extra>",
        ))
    figure.update_layout(
        title="Independently judged maximum coherent doses",
        xaxis_title="target-directed judge effect",
        yaxis_title="off-axis judge damage, lower is better",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=600,
        legend_title="method",
    )
    figure.update_xaxes(showline=True, linecolor="#333", gridcolor="#e5e5e5", zeroline=True)
    figure.update_yaxes(showline=True, linecolor="#333", gridcolor="#e5e5e5", rangemode="tozero")
    return figure


def html_page(rows: list[list[str]], figure_html: str) -> str:
    header = "".join(f"<th>{html.escape(value)}</th>" for value in HEADERS)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>" for row in rows)
    return (
        "<!doctype html><meta charset='utf-8'><title>Independently judged endpoint comparison</title>"
        "<style>body{font:16px system-ui;max-width:1200px;margin:2rem auto;padding:0 1rem}"
        "table{border-collapse:collapse;width:100%}th,td{padding:.35rem .7rem;border-bottom:1px solid #ccc;text-align:left}</style>"
        "<h1>Independently judged endpoint comparison</h1>"
        "<p>Each seed/sign uses its greatest judge-accepted tail coefficient, then the table averages seeds. It does not select maximum effect.</p>"
        + figure_html + f"<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>"
    )


def render(input_path: Path, output_dir: Path) -> None:
    summaries = aggregate(read_selected(input_path))
    rows = table(summaries)
    output_dir.mkdir(parents=True, exist_ok=True)
    plot = figure(summaries)
    plot.write_image(output_dir / "plot.png", width=1400, height=600, scale=2)
    (output_dir / "index.md").write_text(markdown(rows))
    (output_dir / "index.html").write_text(html_page(rows, plot.to_html(full_html=False, include_plotlyjs="cdn")))
    print(f"ENDPOINT_TAIL_RENDER methods={len(summaries)} output={output_dir}")


def self_test() -> None:
    rows = []
    for method, seeds in METHOD_SEEDS.items():
        for seed in seeds:
            for side in ("-C", "+C"):
                rows.append({"method": method, "seed": seed, "side": side, "C": float(seed + 1), "effect": -2.0 if side == "-C" else 2.0, "off_axis_perturbation": 0.5})
    summaries = aggregate(rows)
    assert len(summaries) == len(METHOD_SEEDS)
    assert all(row["score"] == 1.5 for row in summaries)
    assert "J-word" in markdown(table(summaries))
    print("ENDPOINT_TAIL_RENDER_SELF_TEST_PASS")


def main() -> None:
    args = parse_args()
    if args.self_test:
        self_test()
    else:
        render(args.input, args.output_dir)


if __name__ == "__main__":
    main()
