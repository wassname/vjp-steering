You are the independent source-gate reviewer for a frozen J-lens diagnostic. Do not propose a new experiment, change the frozen corpus, or authorize benchmark transfer.

Question: Does job 705 provide valid evidence that its *clean* source task fails the predeclared gate, and was the stop-before-intervention rule applied correctly? Check only this conclusion. Identify any concrete bug that could invalidate it.

Frozen protocol:
- Corpus is frozen v3. Its clean gate requires all 96 semantic-case mirror groups to be fully correct and at least 90% aggregate accuracy in every predeclared cell.
- The causal intervention loop may run only if that clean gate passes.
- Benchmark generation and judging are forbidden in this stage.

Read these complete artifacts:
- `scripts/scratch/j_lens_task_validity_source_stage.py`
- `slop/logs/20260908_j_lens_task_validity_corpus/v3/{freeze.json,spec.md,test-proposal.md}`
- `slop/logs/20260908_j_lens_task_validity_source_stage/{generation.json,mounted-preflight.json,pueue-705-clean.log,retry-budget.json,job705-billing-report.log}`
- `slop/audits/20260908_task_validity_source_stage_job704.md`

Return exactly: `SOURCE_GATE_BLOCKED`, `SOURCE_GATE_INVALID`, or `INSUFFICIENT_EVIDENCE`; then quote the decisive artifact evidence and list only concrete validity bugs.
