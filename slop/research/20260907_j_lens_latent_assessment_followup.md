# J-lens latent-assessment follow-up

— PI/OpenAI Codex

## New primary-source distinction

## Anthropic companion repository — commit `581d398613e5602a5af361e1c34d3a92ea82ba8e` — [`data/experiments/README.md`](https://github.com/anthropics/jacobian-lens/blob/581d398613e5602a5af361e1c34d3a92ea82ba8e/data/experiments/README.md)

- epistemic context: Anthropic’s reference repository for the paper; this README specifies the released experiment prompts and scoring, but does not include the private intervention runner.

> **top-down-summoning** [...] `expected` / `foil` are the property-label vs contrastive-label word sets tracked in the lens over the stimulus span. Metric: Q2 − Q1 fraction of stimulus positions where any `expected` word is in lens top-k. Causal test: swap each `swaps[*]` token pair (label↔foil single-token forms) at every stimulus position and measure the answer shift under each question.

> **verbal-report** [...] the model's greedy next token at the final `:` is taken as the answer and used as the swap-out target. [...] swap answer→candidate across the band at every prompt position.

Observation: these are distinct source-activity protocols. Verbal report uses the actual next token as the source item. Top-down summoning instead finds latent property labels in J-lens readouts over the stimulus span; those labels need not be likely next tokens.

Task 345 checked the candidate assessment tokens only at the final assistant-prefill position. It therefore rules out the verbal-report adaptation, but it does not test the top-down-summoning analogue across prompt positions.

## Paper — Gurnee et al. — [project page](https://transformer-circuits.pub/2026/workspace/index.html)

- epistemic context: authors’ own paper page.

> “In every condition, we apply a J-lens swap across the question tokens, replacing the lens vector for the passage's true language with that of an alternative.”

> “In the explicit report task, the model says ‘Spanish’ unmodified and ‘French’ under the swap. The flexible inference task outputs are also sensitive to J-lens swaps [...] However, in the continuation and anomaly detection tasks, the swap has no effect.”

Inference: causal effect depends on whether downstream computation uses the verbalizable label. Even a strong lens readout can be behaviorally inert for a task that does not consume it.

## Candidate diagnostic

Before another steering run, scan the fixed assessment pairs over every attended prompt position and layers 13–21 on DEV-15:

- `false ↔ true`
- `incorrect ↔ correct`
- `invalid ↔ valid`
- `impossible ↔ possible`
- `nonsense ↔ reasonable`
- `unrelated ↔ related`
- `unsupported ↔ supported`

For each prompt and direction, record:

1. best full-vocabulary J-lens rank over layer × position for each source token;
2. number of positions where a source reaches rank ≤10 and ≤25;
3. paired source-minus-target coordinate margin at those positions;
4. the same readout after appending an explicit one-word “real or fabricated?” question as a positive control.

Decision:

- If original prompts contain active labels on at least 10/15 scenarios in both directions, test a fixed-label, per-prompt active-source coordinate swap without changing the lexicon after results.
- If labels appear only under the explicit classification question, the paper’s selectivity result predicts that this benchmark does not expose a usable latent assessment item. Stop the token-pair route.
- If neither condition exposes the labels, the lens/token convention or lexicon is wrong; do not generate a dose grid.

This is a diagnostic proposal, not evidence that assessment-token swaps control sycophancy.
