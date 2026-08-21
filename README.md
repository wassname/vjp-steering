# vjp-steering

**Work in progress.** Final results in the next couple of months.

I'm turning Anthropic's [J-lens](https://github.com/anthropics/jacobian-lens) work into contrastive steering. Instead of a full Jabobian (5 hours on a 4B model) I use vjp (20mins), and instead of wikitext I use persona paris. The hope is that adapting the J-lens work to steering gives a stronger more reliable steering method than can be used for interp and alignment.

## Measuring it

Here's a nice way of measuring it: sweep the doses and plot the Pareto frontier.

![Judged on-axis change against off-axis damage, for VJP-delta, mean difference, PCA, and a random cone](results.png)

In case it's not clear, good steering methods are high and horizontal, since they can be steered left and right. Bad steering methods fall down as side effects accumulate, and then the line disappears as they fall off into incoherence.

The Jacobian (`vjp_delta`) methods have a better profile than the controls here.

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

This uses petergpt's great [Bullshit Benchmark v2](https://github.com/petergpt/bullshit-benchmark) for measuring sycophancy. Qwen3.5-4B, all 100 questions, means over three seeds. The random cone is ten vectors, drawn until fewer than half have two coherent arms.

Doses are not comparable across methods. These are fixed-C arms; the final export re-walks each method to its own incoherence boundary.

## What J is

I like [Janus's view](https://x.com/repligate/status/1965960676104712451) of the transformer as a causal lens. Here you can see that $J$ is a local linear approximation, summarising many branching paths into one sensitivity.

![the routes from A to B, and the first-order map that stands in for them](jacobian_vjp_causal_graph.svg)

$J = \partial h_B / \partial h_A$ is the local linear map between a source location $A$ and a downstream target $B$ on the (layer, token) grid. It is never materialized: a VJP queries it with one backward pass, and contrastive pairs supply the direction to query it with.

Start with the usual target-layer contrast, where source layers precede the target layer:

$$c = \mathbb{E}[h_T^+] - \mathbb{E}[h_T^-].$$

Pull that contrast back to each source layer and subtract the two prompt classes:

$$v_L = \mathbb{E}_{x^+}[J_{L \to T}(x)^T c] - \mathbb{E}_{x^-}[J_{L \to T}(x)^T c].$$

This also draws on [AntiPaSTO](https://github.com/wassname/AntiPaSTO_concepts/tree/main#incomplete-contrastive-pairs). The shared vector, hook, mean-difference, PCA, and random-direction code comes from [`steering-lite`](https://github.com/wassname/steering-lite).

## Using it

```python
from vjp_steering import steer, vjp_delta

vector = vjp_delta(model, tokenizer, positive_prompts, negative_prompts, layers)
with steer(model, vector, C=-0.18):
    output = model.generate(**inputs)
```

No single C transfers across models, personas, and prompts, and the useful magnitude differs per method, so the notebook sweeps a log grid on both signs and you read the dose grid to pick one. The C above is what that grid gave for this model and this persona pair.

Read [the notebook](nbs/demo.ipynb) on GitHub for the complete extract, steer, sweep, and plot example. `nbs/demo.py` is the jupytext source; `just notebook` syncs the two, and `just notebook-run` executes the notebook on a GPU and stores the outputs. `just notebook-smoke` runs every cell on the tiny random model on CPU in about 15 seconds. Run `just check` for the smoke run and generated results.

## Where the numbers come from

`data/results.csv` is exported from the working research repo, which owns the runner, judging, and audits. Each row is one measured arm of the all-100 cohort, eval cohort v10.

| column | meaning |
| --- | --- |
| `effect` | judged on-axis movement vs bare, -5..+5 Likert, blinded judge, averaged over two presentation orders and two passes (`deepseek/deepseek-v4-flash-0731`, sycophancy rubric `results-demo-perresponse-syco-v7`). Positive is less sycophantic. |
| `off_axis_perturbation` | judged off-axis change vs bare, same judge protocol. Lower is better. |
| `admissible` | the arm passed all the deterministic text-quality gates (deterministic code on the generated demos, not the judge): >=50% demos reach EOS, <25% role-token leak, <25% over worst-window repetition 0.5, per-pole coherence >=0.5, prefill-NLL <=1.0 over bare. A `false` arm is discarded from the plot. |
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
