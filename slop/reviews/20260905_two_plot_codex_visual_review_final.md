Inspected only:

- `results/plot.png`
- `results/plot_pareto.png`

Both images render correctly. I found no corruption, clipping, stray connectors, or illegible annotations. Text is dense near the origin and gray null region, but remains readable; white annotation backgrounds help. The pale cyan and gray legends have lower contrast but are still legible.

All visible marker types are explained or directly labeled: measured-dose circles, selected/final crosses, random-peak open circles, high-damage triangles, the black “bare” diamond, and the shaded random-direction null zone. Connector lines terminate at the intended labeled markers.

Confirmed:

- `results/plot.png` is the measured dose-order/reference-style comparison. Its legend says measured doses and that `C` increases from bare; it includes labeled baselines and prior methods such as mean difference, PCA, VJP-delta, J-word, and per-side/MLP-up VJP.
- `results/plot_pareto.png` is a separate Pareto-smoothed view. Its legend explicitly states: “small dots: measured doses · lines: Pareto-efficient means.” The selected/final, random-peak, and high-damage marker semantics are also stated.

— Codex / GPT-5