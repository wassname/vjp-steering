# Empirical-candor DEV launch contract

PI/OpenAI Codex, 2026-09-08. This is the authorized Goal 1 selection test. It is not an all-100 run, public update, or goal sign-off.

## Fixed generation contract

| field | value |
|---|---|
| experiment | `j-lens-components-empirical-candor-dev-v1` |
| source experiment | `j-lens-behavior-components-target-ordered-source-v8` |
| source vector SHA256 | `dd4e78e9c429e51e4fe2d4e70e0db28c96d5c4c218b5f317767393ac38883197` |
| source side | `+C`, retained as source provenance |
| behavior target | `candidness`, used by the unchanged judge rubric |
| operator | `mean100-gp16-reconstruction-target-ordered-coordinate-exchange-all-prefill-v8` |
| layers | 13 through 21 |
| alpha | `.5` |
| patch mask | all attended prefill positions |
| arms | fresh bare, source `+C`, seeded randomized target-order control |
| control | seed `20260909`, rank-two, source-Gram-preserving, target index 0 |
| cohort | unchanged DEV-15 in saved order |
| generation | greedy Qwen3.5-4B, maximum 512 tokens |
| remote limit | one H100 Modal container, 900 seconds, no automatic retry |
| queue | pueue `modal`, one slot |

## Required after generation

1. Save the full pueue and Modal output, task status, raw JSONL, manifest, and metered cost.
2. Audit every response and the source/control realized prefill diagnostics. Do not infer equal interventions from Gram matching.
3. Judge source and control with the unchanged candidness rubric in AB and BA. Map each order back to arm identity once.
4. Save reversals and tie disagreements as diagnostics, not extra samples, then obtain an independent endpoint review.

The full all-100 endpoint remains blocked. Any later full result is fresh generation on all 100 but includes the selection-exposed DEV-15, so its 85 non-DEV rows need a separate descriptive generalization readout.
