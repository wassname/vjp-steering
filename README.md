# j-steer

`j-steer` is a small VJP-delta activation-steering reference. The package contains one method. It uses [`steering-lite`](https://github.com/wassname/steering-lite) for the shared vector, hook, mean-difference, PCA, and random-direction code.

## Point

The experiment asks if pulling a persona contrast backward through a model makes a cleaner steering direction than the ordinary activation difference. This is a hypothesis, not a result.

The public comparison uses all 100 Bullshit Benchmark questions. It measures VJP-delta, mean difference, PCA, and three seeded random directions. The key plot shows judged movement away from sycophancy against judged off-axis change. Output caps exclude degenerate text.

The hope is a VJP-delta curve outside the random band and not dominated by the baselines. A curve inside the band, or one dominated by a baseline, does not support the method.

The VJP-delta method starts with the usual target-layer contrast:

$$c = \mathbb{E}[h_T^+] - \mathbb{E}[h_T^-].$$

It pulls that contrast back to each source layer and subtracts the two prompt classes:

$$v_L = \mathbb{E}_{x^+}[J_{L \to T}(x)^T c] - \mathbb{E}_{x^-}[J_{L \to T}(x)^T c].$$

```python
from jsteer import steer, vjp_delta

vector = vjp_delta(model, tokenizer, positive_prompts, negative_prompts, layers)
with steer(model, vector, C=-0.18):
    output = model.generate(**inputs)
```

Run `just notebook` for the complete extract, steer, generate, and plot example. Run `just check` for the deterministic VJP check and generated results.

## Source inventory

| path | purpose |
| --- | --- |
| `src/jsteer/vjp.py` | VJP-delta extraction |
| `src/jsteer/__init__.py` | `with steer(...)` |
| `src/jsteer/results.py` | Markdown, HTML, and plot renderer |
| `src/jsteer/smoke.py` | one deterministic check |
| `nbs/demo.py` | one notebook |

The checked source inventory rejects extra Python files. Package and render code must stay below 2000 lines.
