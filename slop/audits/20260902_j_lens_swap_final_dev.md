# J-lens coordinate swap: final DEV audit

## Conclusion

This exact `abrasive` ↔ `flattering` coordinate swap does not produce useful judged sycophancy steering on the fixed DEV cohort.

- Paper strength alpha=1: judged effect -0.607, damage 0.140. It is fluent but moves slightly toward the left side of the judged axis, not toward sycophancy.
- Paper double strength alpha=2: judged effect -2.807, damage 4.593. All 15 responses are the same `flattering abrasive ...` repetition.
- The transition is abrupt. At alpha=1.125, 9/15 responses contain the literal target token, including two repetitive 512-token responses; at alpha>=1.25, all 15 collapse.
- Negative alpha is not a reverse swap. Every tested value from -0.5 to -2 produces the same `abrasive abrasive ...` repetition.

No full all-100 run follows: neither positive alpha nor the negative-alpha control has an accepted DEV dose.

## Judged measurements

| alpha | judged effect | damage | absolute steered damage | raw result |
|---:|---:|---:|---:|---|
| +0.500 | -0.180 | 0.147 | 0.533 | fluent; no consistent movement |
| +1.000 | -0.607 | 0.140 | 0.400 | fluent; wrong aggregate direction |
| +1.125 | +0.067 | 1.167 | 1.487 | 9/15 leak `flattering`; rejected |
| +1.250…+2.000 | -2.807 | 4.593 | 5.000 | identical alternating-token collapse |
| -0.500…-2.000 | +0.707 | 4.207 | 5.000 | identical `abrasive` collapse |

Sources: [`results.csv`](../../data/dev/j-lens-swap-formative-v1/results.csv), [`judged_scenarios.csv`](../../data/dev/j-lens-swap-formative-v1/judged_scenarios.csv), and [`manifest.json`](../../outputs/experiments/j-lens-swap-formative-v1/manifest.json).

The alpha=1.125 mean is not evidence of a small useful effect. Fresh-eyes review calculates sd=3.54, sem=0.92, range -7 to +7, and finds semantically equivalent response pairs assigned opposite extreme scores. The mean +0.067 is much smaller than judge variation and accompanies direct token leakage.

## Implementation evidence

The saved extraction records:

> `"paper_equation": "h + alpha V(swap(V^dagger h) - V^dagger h)"`
>
> `"normalization": "none"`
>
> `"source_token_text": " abrasive"`
>
> `"target_token_text": " flattering"`
>
> `"token_scope": "all_positions"`

Both saved sides have the same content hash `55a6a2b7...fa4044`, as required for one activation-dependent swap with signed alpha. Per-layer condition numbers are 1.22–1.36, so numerical rank is not the apparent failure.

[`self-test.log`](../logs/20260902_j_lens_swap/self-test.log) records alpha-zero identity, alpha-one coordinate exchange, and exact save/reload. [`modal-smoke.log`](../logs/20260902_j_lens_swap/modal-smoke.log) records the real model and lens path, layers 6–24, both token IDs, changed logits, and restored logits after hook removal. The original [`dev.log`](../logs/20260902_j_lens_swap/dev.log) records six generated cells and 53 new API judgments; [`dense-dev.log`](../logs/20260902_j_lens_swap/dense-dev.log) records the six additional interpolation cells and 15 new judgments. [`final-dev.log`](../logs/20260902_j_lens_swap/final-dev.log) rechecks all 12 cells and 72 cached judgments with no missing cells, then exports and renders.

## What this does and does not test

This tests the paper equation, its layer/token application policy, and one semantically chosen pair of single-token J-lens vectors. It does not show that every J-lens coordinate swap fails. The paper reports better swaps when a source concept is strongly present in the clean state. We did not establish that the benchmark prompts strongly load `abrasive`; lack of source loading and the diffuse nature of sycophancy remain plausible reasons for failure.

The separate “Tell me about {concept}” construction is not tested here. The paper mean-subtracts 100 other concept activations, then decomposes the resulting concept vector into J-space and non-J-space components for a causal comparison. It is a distinct experiment.

## Plot integration

The first render was a standalone J-lens figure. That did not satisfy the user's request to add the method to the existing comparison plot, and it removed the baselines needed to interpret the failure. It has been deleted.

The final [`results/plot.png`](../../results/plot.png) keeps the existing all-100 methods, random cone, and fixed axes. The cyan DEV overlay shows the three in-range positive-alpha measurements and clips both collapsed trajectories at the plot boundary. [`results/index.md`](../../results/index.md) states that the overlay uses 15 DEV questions, is excluded from the all-100 table, has no accepted dose, and reaches measured collapsed damage 4.59 for positive alpha and 4.21 for negative alpha. The final fresh-eyes review reconstructs those three points from the CSV and concludes: “Overlay matches the existing comparison plot without a material visual defect.”

— PI/OpenAI Codex
