# j-steer

`j-steer` is a small VJP-delta activation-steering reference. The package contains one method. It uses [`steering-lite`](https://github.com/wassname/steering-lite) for the shared vector, hook, mean-difference, PCA, and random-direction code.

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
