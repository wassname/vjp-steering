# Task-validity source-state stage

PI/OpenAI Codex, 2026-09-08.

## Goal

Run exactly one reviewed source-state diagnostic on frozen v3. It can establish whether the pinned model both solves the closed-rule corpus under the strict mirrored semantic gate and changes withheld semantic actions under the fixed full/GP/remainder/random rank-one interventions. It cannot establish transfer to the sycophancy benchmark.

## Scope

In: frozen v3 source prompts, layer17 final-prefill state collection, fixed k25 GP decomposition, withheld-source rank-one controls, saved outputs and offline gate audit.

Out: DEV/full generation, judging, rubric changes, dose/layer/source/dictionary-k sweep, retry, and public results.

## Requirements

- [x] R1: Freeze the exact source protocol and cost reservation.
  - verify: `budget.json` records one $2.00 Modal allocation from the $5.22509672744 balance.
  - likely failure: spending more or silently authorizing transfer. Catch with fixed run scope and no judge code.
  - sneaky failure: a stale corpus or revised gate. Catch with source hashes and copied strict-gate checks.
- [x] R2: Implement one runner and a CPU preflight for the actual hook route and pinned tokenizer.
  - verify: `preflight.py` must exercise the runner's final-prefill hook on a tiny cached Qwen3.5 model, verify hook removal and decode non-intervention, and verify all frozen v3 rendered inputs through the real pinned tokenizer.
  - likely failure: wrong hook row or tokenizer drift. Catch with exact sequence-length/hook and tokenizer-hash assertions.
  - sneaky failure: clean results are correct due letters, but semantic mapping is wrong. Catch with the frozen semantic gate and deterministic shortcut controls.
- [x] R3: Queue a bounded Modal H100 source run with no automatic retry and one completion follower.
  - verify: app settings have max_containers1, retries0, timeout900; complete raw source records and fixed gate output are saved.
  - likely failure: clean gate fails. The runner saves clean records and stops before any intervention.
  - sneaky failure: rank-one hook changes decode or nonfinal prefill positions. Catch per-record first-prefill-only hook counters, identity tokens/logit hashes, and no decode hook calls.
- [x] R4: Audit results offline and stop before transfer.
  - verify: the audit accepts hashes and counts, checks the clean mirror gate, and writes a decision with `BENCHMARK_RELEASED=false`.
  - likely failure: partial output interpreted as causal evidence. Catch expected complete counts and explicit incomplete status.
  - sneaky failure: GP and random differ in delivered norm. Catch the fixed 5% per-row matching bound.

## Fixed predictions

| Result | Meaning |
|---|---|
| Clean strict gate fails | No model-inferred task-validity source is admitted. Stop. |
| Clean passes; GP causal gate passes over random | Supports a synthetic source-state handle only. Review before any transfer. |
| Full passes but GP fails | The selected J-space component is not the useful source handle. Stop. |
| GP matches random | General perturbation, not GP specificity. Stop. |

## Log

- External DeepSeek review decision is TEST for the source stage only. It confirms the strict semantic gate and warns that its all-mirror clause is effectively a 100% correctness gate. The gate remains fixed.
- Task 704 failed before source generation because the remote image attempted a host-only protected-output check. [job704 audit](../../audits/20260908_task_validity_source_stage_job704.md) preserves this failure. The explicit, budgeted task 705 repair moved that check to the host and passed an actual-mounted-input preflight.
- Task 705 saved all 384 clean outputs, failed the frozen gate with 1/96 strict semantic cases and a 42.5% lowest cell, and stopped before intervention. [source-gate-decision.md](source-gate-decision.md) and [job705 audit](../../audits/20260908_task_validity_source_stage_job705.md) record the contemporaneous evidence and benchmark block.
- Offline paired-output diagnosis found a frozen-v3 label defect: policy order 1 reverses the stated action relation but preserves the old expected answer. [clean-gate-diagnosis-decision.md](clean-gate-diagnosis-decision.md) supersedes the behavioral interpretation. The frozen stage is invalid for causal admission, so no source retry or transfer is authorized.
