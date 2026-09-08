# Source-gate decision: BLOCK

PI/OpenAI Codex, 2026-09-08.

The frozen v3 source stage is **BLOCKED**. This is a clean-task failure, not an intervention result.

| check | required | observed | result |
|---|---:|---:|---|
| all semantic mirror cases | 96 / 96 | 1 / 96 | fail |
| lowest predeclared cell accuracy | >= 0.90 | 0.425 | fail |
| intervention generation after clean failure | 0 | 0 | pass |
| benchmark generation or judging | 0 | 0 | pass |
| actual mounted-input preflight | pass | pass | pass |
| host comparison-output preservation | exact hashes | exact hashes | pass |

Evidence:

- [generation.json](generation.json) records `"decision": "CLEAN_GATE_BLOCKED_NO_INTERVENTION"`, 384 clean records, no intervention modes, and `"benchmark_released": false`.
- [pueue-705-clean.log](pueue-705-clean.log) prints `CLEAN_GATE {"pass": false, "minimum_accuracy": 0.425, "strict_semantic_cases": {"passed": 1, "total": 96}}` after all clean outputs.
- [mounted-preflight.json](mounted-preflight.json) records the frozen corpus SHA, model revision, tokenizer hash, runner SHA, and 384 mounted rows.
- `generation.json` records `"host_protected_paths_exact": true` after the host compared the protected output hashes with `preflight.json`.
- The independent review in [j_lens_task_validity_source_gate_705_r2.md](../../reviews/j_lens_task_validity_source_gate_705_r2.md) returns `SOURCE_GATE_BLOCKED` after correcting its earlier overclaim.

The reviewer first said the output was a first-policy heuristic. The independent data check disproved that specific explanation: [first-policy-check.json](first-policy-check.json) finds 248/384 matches, 64.58%, with 136 mismatches. Its corrected review withdraws that mechanism. This does not change the gate result, because the frozen gate is evaluated from semantic correctness and mirrors, not a diagnosis of the failure pattern.

No causal intervention, DEV transfer, benchmark generation, judging, score update, or public comparison is authorized by this decision. Both research goals remain OPEN.
