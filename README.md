# vjp-steering

Work in progress. The numbers below are a mid-experiment snapshot, not a result. Final results in the next couple of months.

`vjp-steering` is a small VJP-delta activation-steering reference. The package contains one method. It uses [`steering-lite`](https://github.com/wassname/steering-lite) for the shared vector, hook, mean-difference, PCA, and random-direction code.

## Point

The experiment asks if pulling a persona contrast backward through a model makes a cleaner steering direction than the ordinary activation difference.

The hope is a VJP-delta curve outside the random band and not dominated by the baselines. A curve inside the band, or one dominated by a baseline, does not support the method.

## Results so far

Model `Qwen/Qwen3.5-4B`, sycophancy axis, all 100 Bullshit Benchmark v2 questions. Named-method points are means over three seeds. The random cone shows ten vectors until fewer than half have two coherent arms. Output caps exclude degenerate text.

![Judged on-axis change against off-axis damage, for VJP-delta, mean difference, PCA, and a random cone](results.png)

| method | steer dir | seeds | arms | rejected | peak on-axis | damage at peak |
| --- | --- | --- | --- | --- | --- | --- |
| vjp_delta | -C | 3 | 1 | 5 | -1.944 | 0.562 |
| vjp_delta | +C | 3 | 3 | 0 | +3.502 | 0.406 |
| mean_diff | -C | 3 | 3 | 0 | -1.223 | 0.871 |
| mean_diff | +C | 3 | 3 | 0 | +3.715 | 0.521 |
| pca | -C | 3 | 3 | 0 | -1.360 | 1.495 |
| pca | +C | 3 | 3 | 0 | +3.939 | 0.830 |
| random | -C | 10 | 30 | 4 | +4.075 | 0.723 |
| random | +C | 10 | 30 | 3 | +3.851 | 0.470 |

Doses are not comparable across methods. These are fixed-C arms; the final export re-walks each method to its own incoherence boundary.

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
from vjp_steering import steer, vjp_delta

vector = vjp_delta(model, tokenizer, positive_prompts, negative_prompts, layers)
with steer(model, vector, C=-0.18):
    output = model.generate(**inputs)
```

No single C transfers across models, personas, and prompts, and the useful magnitude differs per method, so the notebook sweeps a log grid on both signs and you read the dose grid to pick one. The C above is the value that grid gave for this model and this persona pair.

Read [the notebook](nbs/demo.ipynb) on GitHub for the complete extract, steer, sweep, and plot example. `nbs/demo.py` is the jupytext source; `just notebook` syncs the two, and `just notebook-run` executes the notebook on a GPU and stores the outputs. `just notebook-smoke` runs every cell on the tiny random model on CPU in about 15 seconds. Run `just check` for the smoke run and generated results.

## Measured-data provenance

`data/results.csv` is exported from the working research repository, which owns the runner, judging, and audits. Each row is one measured arm of the all-100 cohort, eval cohort v10.

| column | meaning |
| --- | --- |
| `effect` | judged on-axis movement vs bare, -5..+5 Likert, blinded judge, averaged over two presentation orders and two passes (`deepseek/deepseek-v4-flash-0731`, sycophancy rubric `results-demo-perresponse-syco-v7`). Positive is less sycophantic. |
| `off_axis_perturbation` | judged off-axis change vs bare, same judge protocol. Lower is better. |
| `admissible` | the arm passed all deterministic text-quality gates (deterministic code on the generated demos, not the judge): >=50% demos reach EOS, <25% role-token leak, <25% over worst-window repetition 0.5, per-pole coherence >=0.5, prefill-NLL <=1.0 over bare. A `false` arm is discarded from the plot. |
| `seed` | the random seed moving the persona sample, calibration prompts, and demo sampling. Named-method points are means over seeds {0,1,2}; the random cone spans seeds 0-9. |

## Citation

```bibtex
@software{clark2026vjpsteering,
  title = {vjp-steering: contrastive steering vectors from vector-Jacobian products},
  author = {Clark, Michael J.},
  year = {2026},
  url = {https://github.com/wassname/vjp-steering},
  note = {Work in progress}
}
```
