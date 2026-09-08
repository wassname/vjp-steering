# Audit: source-stage retry job 705

Target: frozen v3 clean source gate only. Pueue job 705 ran `uv run modal run scripts/scratch/j_lens_task_validity_source_stage.py::launch` from the repository at `1aefb5b9ccb042e8bb7ee14d837379ff8e427872`.

| stage | expected | observed | result |
|---|---|---|---|
| CPU actual-mounted preflight | frozen files, corpus, tokenizer, model revision | two passing receipts, 384 rows | pass |
| H100 clean source run | 384 greedy A/B outputs | 384 outputs | pass |
| clean semantic gate | 96/96 mirrors and >=90% each cell | 1/96 mirrors; lowest cell 42.5% | fail |
| causal intervention | only after clean-gate pass | none | correctly blocked |
| benchmark/judging | forbidden | none | pass |
| comparison output preservation | host checks protected hashes | exact match | pass |

## Evidence

## Pueue job 705 / [pueue-705-clean.log](../logs/20260908_j_lens_task_validity_source_stage/pueue-705-clean.log)
- context: complete 427-line pueue log for the only retry; process exit success means the runner completed its planned stop, not that the gate passed.

> TASK_VALIDITY_MOUNTED_PREFLIGHT_PASS {"corpus_sha256": "b4ef9920b02959e1204c0baa681fc5d402909af65ee676d120145468324f527e", ... "rows": 384, "model": "Qwen/Qwen3.5-4B", "revision": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a", "source_tokenizer_sha256": "0ef9d0923a6d6d8342cae2674ade04c07f12fd060a55f170b8cc9b89f9a822d4"}
> TASK_VALIDITY_MOUNTED_PREFLIGHT_PASS {"corpus_sha256": "b4ef9920b02959e1204c0baa681fc5d402909af65ee676d120145468324f527e", ... "rows": 384, "model": "Qwen/Qwen3.5-4B", "revision": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a", "source_tokenizer_sha256": "0ef9d0923a6d6d8342cae2674ade04c07f12fd060a55f170b8cc9b89f9a822d4"}

The first receipt is the CPU preflight. The second is in the H100 container before model load. They prove the actual mounted inputs, not only the local source files.

> CLEAN_GATE {"pass": false, "minimum_accuracy": 0.425, "strict_semantic_cases": {"passed": 1, "total": 96}, "cells": {"split": {"train": 0.5104166666666666, "source_calibration": 0.5178571428571429, "withheld_source": 0.48295454545454547}, ...}}
> TASK_VALIDITY_SOURCE_DOWNLOADED slop/logs/20260908_j_lens_task_validity_source_stage/generation.json
> Stopping app - local entrypoint completed.

The source gate failed both independent predeclared conditions. The log contains `CLEAN_RESPONSE` entries and no `INTERVENTION_RESPONSE` entry. This is consistent with the generated artifact's `CLEAN_GATE_BLOCKED_NO_INTERVENTION` decision.

## [generation.json](../logs/20260908_j_lens_task_validity_source_stage/generation.json)
- context: full saved output of the H100 run. It contains every rendered prompt, output token, semantic mapping, and layer-17 activation receipt for the 384 clean records.

The first four mirror variants are a readable complete A/B check. Their rendered prompts change policy order and option order while retaining the valid semantic target. The observed outputs are `A`, `B`, `B`, `A`, which are all semantically valid. Other semantic cases fail, producing the aggregate gate result above. The complete records preserve the evidence instead of relying on the aggregate alone.

The artifact records:

> `"decision": "CLEAN_GATE_BLOCKED_NO_INTERVENTION"`
> `"benchmark_released": false`
> `"causal_gate": null`
> `"host_protected_paths_exact": true`

## Independent review / [j_lens_task_validity_source_gate_705_r2.md](../reviews/j_lens_task_validity_source_gate_705_r2.md)
- context: independent DeepSeek V4 Pro reviewer, after a factual correction to its first response.

> **SOURCE_GATE_BLOCKED**
>
> The `first-policy-check.json` shows only 248/384 (64.58%) matches to the first-policy-branch action, so the output is not explained by that simple heuristic alone.
>
> That correction does **not** affect the clean-gate block. ... `"pass": false`, `"minimum_accuracy": 0.425` (required >=0.90), and `"strict_semantic_cases": {"passed": 1, "total": 96}` (required 96/96).

The reviewer initially over-attributed the failure to first-policy selection. [first-policy-check.json](../logs/20260908_j_lens_task_validity_source_stage/first-policy-check.json) disproved that claim, and the reviewer withdrew it. This makes the gate decision more reliable because it is based on the frozen semantic checks rather than a guessed failure mechanism.

## Cost

[final-budget-reconciliation.json](../logs/20260908_j_lens_task_validity_source_stage/final-budget-reconciliation.json) records $0.02227301 for job 704 and $0.19453738 for job 705, totaling $0.21681039 of Modal metered cost. This is below the $2 retained source-stage allocation and the $40 cap. The unused $1.78318961 source-stage reservation is released. Modal charges remain metered, not final invoice values.

## Decision

**Source-stage result: blocked.** This is not evidence for or against the GP causal handle because no intervention ran. It is evidence that the frozen v3 source task is not a valid clean prerequisite for this model and prompting setup under its strict protocol.

**Do not run:** any causal retry, DEV transfer, benchmark generation, judging, score update, or corpus edit under this stage. The benchmark has not been touched. Both research goals remain OPEN.

## Epistemic summary

- The run log and JSON are direct runtime artifacts. The gate check follows the frozen protocol.
- The independent review agrees with the block after correcting an unsupported mechanism claim.
- One H100 run does not establish why the source task failed. The low performance is enough to block this planned intervention, not enough to diagnose a representation cause.
- A future task would need a separately designed and authorized source task. It must be specified before reading a new result and must not use benchmark performance to select examples.
