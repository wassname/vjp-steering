# j-steer

`j-steer` is a small VJP-delta activation-steering reference. The package contains one method. It uses [`steering-lite`](https://github.com/wassname/steering-lite) for the shared vector, hook, mean-difference, PCA, and random-direction code.

## Point

The experiment asks if pulling a persona contrast backward through a model makes a cleaner steering direction than the ordinary activation difference. This is a hypothesis, not a result.

The public comparison uses all 100 Bullshit Benchmark questions. It measures VJP-delta, mean difference, PCA, and ten seeded random directions. The key plot shows judged movement away from sycophancy against judged off-axis change. Output caps exclude degenerate text.

The hope is a VJP-delta curve outside the random band and not dominated by the baselines. A curve inside the band, or one dominated by a baseline, does not support the method.

## Method

$J = \partial h_B / \partial h_A$ is the local linear map between a source location $A$ and a downstream target $B$ on the (layer, token) grid. It summarises every route from $A$ to $B$ to first order, and it is never materialized: a VJP queries it with one backward pass. Contrastive pairs supply the direction to query it with.

![the routes from A to B, and the first-order map that stands in for them](jacobian_vjp_causal_graph.svg)

The left pane is drawn after [Janus's information-flow sketch](https://x.com/repligate/status/1965960676104712451). The approach also draws on [Anthropic's Jacobian lens](https://github.com/anthropics/jacobian-lens) and on [AntiPaSTO](https://github.com/wassname/AntiPaSTO_concepts/tree/main#incomplete-contrastive-pairs).

The VJP-delta method starts with the usual target-layer contrast:

$$c = \mathbb{E}[h_T^+] - \mathbb{E}[h_T^-].$$

Source layers precede the target layer.

It pulls that contrast back to each source layer and subtracts the two prompt classes:

$$v_L = \mathbb{E}_{x^+}[J_{L \to T}(x)^T c] - \mathbb{E}_{x^-}[J_{L \to T}(x)^T c].$$

```python
from jsteer import steer, vjp_delta

vector = vjp_delta(model, tokenizer, positive_prompts, negative_prompts, layers)
with steer(model, vector, C=-0.18):
    output = model.generate(**inputs)
```

No single C transfers across models, personas, and prompts, and the useful magnitude differs per method, so the notebook sweeps a log grid on both signs and you read the dose grid to pick one. The C above is the value that grid gave for this model and this persona pair.

Read [the notebook](nbs/demo.ipynb) on GitHub for the complete extract, steer, sweep, and plot example. `nbs/demo.py` is the jupytext source; `just notebook` syncs the two, and `just notebook-run` executes the notebook on a GPU and stores the outputs. `just notebook-smoke` runs every cell on the tiny random model on CPU in about 15 seconds. Run `just check` for the smoke run and generated results.

## Source inventory

| path | purpose |
| --- | --- |
| `src/jsteer/vjp.py` | VJP-delta extraction |
| `src/jsteer/__init__.py` | `with steer(...)` |
| `src/jsteer/results.py` | Markdown, HTML, and plot renderer |
| `src/jsteer/smoke.py` | small real-pipeline smoke run |
| `nbs/demo.py`, `nbs/demo.ipynb` | one jupytext-paired notebook, source and GitHub view |
| `jacobian_vjp_causal_graph.svg` | the method figure; source is `docs/explainers/*.tex` in the working repo |

The checked source inventory rejects extra Python files. Package and render code must stay below 2000 lines.
