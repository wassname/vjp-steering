"""Fair-comparison plot: low_extension_0p40 five-seed rung vs paper-swap candidates.

x = intended-direction effect (+C as-is, -C negated so rightward = intended);
y = off-axis damage. Standalone audit figure; main DEV plots stay frozen.
"""
import plotly.graph_objects as go

# (label, intended_effect, damage, color, symbol, size)
ext_plus = [  # effects as measured
    ("s0", -0.260, 0.260), ("s1", 0.340, 0.107), ("s2", 0.540, 0.107),
    ("s3", 0.037, 0.260), ("s4", 0.837, 0.120),
]
ext_minus = [  # measured effects, negated below to intended direction
    ("s0", 0.157, 0.120), ("s1", -1.143, 0.373), ("s2", 1.037, 0.187),
    ("s3", 0.787, 0.317), ("s4", 0.213, 0.203),
]
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=[e for _, e, _ in ext_plus], y=[d for _, _, d in ext_plus],
    mode="markers+text", text=[l for l, _, _ in ext_plus], textposition="top center",
    marker={"color": "#777777", "size": 10}, name="random 0.40x +C (5 seeds)",
))
fig.add_trace(go.Scatter(
    x=[-e for _, e, _ in ext_minus], y=[d for _, _, d in ext_minus],
    mode="markers+text", text=[l for l, _, _ in ext_minus], textposition="top center",
    marker={"color": "#777777", "size": 10, "symbol": "diamond"}, name="random 0.40x -C intended (5 seeds)",
))
fig.add_trace(go.Scatter(
    x=[1.243], y=[0.163], mode="markers+text", text=["L16 swap +C8.14"],
    textposition="top center", marker={"color": "#009e73", "size": 14, "symbol": "star"},
    name="paper-swap candidate +C",
))
fig.add_trace(go.Scatter(
    x=[0.513], y=[0.130], mode="markers+text", text=["orig swap -C0.19"],
    textposition="top center", marker={"color": "#56b4e9", "size": 14, "symbol": "star"},
    name="paper-swap candidate -C (intended)",
))
fig.add_trace(go.Scatter(
    x=[0.0], y=[0.0], mode="markers+text", text=["bare"],
    textposition="bottom center", marker={"color": "black", "size": 12, "symbol": "diamond"},
    name="shared bare",
))
fig.update_layout(
    title="Fair low-damage comparison: 0.40xC_approx random rung vs paper-swap candidates (DEV15)",
    xaxis_title="intended-direction judge effect (larger rightward = stronger intended steer)",
    yaxis_title="off-axis damage (lower = cleaner)",
    width=1064, height=620,
    annotations=[{
        "x": 0.02, "y": 0.02, "xref": "paper", "yref": "paper", "showarrow": False,
        "xanchor": "left", "font": {"size": 11, "color": "#555555"},
        "text": "-C rung poorly damage-matched: only s0 (0.120) near candidate 0.130; s1-s4 at 0.187-0.373 (gap, not a bound).",
    }],
)
fig.write_image(
    "/workspace/2026/jspace/j-steer_pub/slop/audits/20260909_low_extension_fair_comparison.png",
    width=1064, height=620, scale=2,
)
print("FAIR_COMPARISON_PLOT_SAVED")
