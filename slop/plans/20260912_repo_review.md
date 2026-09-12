# Repository review

User: "review this repo for misconceptions and bugs please"

Scope: review and saved evidence only. No paid runs, GPU queues, production edits, publishing, or fixes.

1. [x] goal: Review steering mathematics and reference fidelity
  - Deliverable: slop/reviews/20260912_steering_review.md with source lines and distinguishing tests.
  - Failure mode: treating an untested implementation assumption as a scientific null.
  - tasks:
    - [x] Inspect production extraction/apply paths, installed steering-lite and supplied paper/vendor source.
    - [x] Run bounded CPU checks and preserve direct discriminators.
    - [x] Save signed report with historical-impact limits and repair order.
  - evidence:
    - slop/reviews/20260912_steering_review.md
    - slop/reviews/20260912_steering_evidence/discriminators.log
    - slop/reviews/20260912_steering_evidence/existing_cpu_tests.log
    - slop/reviews/20260912_steering_evidence/data_and_lens.log
  - Log (PI/OpenAI gpt-6-astra, 2026-09-12): Source review and CPU checks complete. Current local VJP label invariance and zero-norm NaNs reproduced; argument/cache omissions reproduced. Historical published extraction implementation remains unknown. Cached tokenizer observations printed completely, but that command timed out; recorded as observations, not successful exit. Parent owns approval.
2. [x] goal: Review evaluation, export, and publication figures
  - Deliverable: slop/reviews/20260912_results_review.md with source lines and reproductions.
  - Failure mode: calling a smooth curve or selected seed a measured comparison.
  - tasks:
    - [x] Read production judge/export/results code and both existing publication PNGs.
    - [x] Reproduce consequential failures with installed CPU environment.
    - [x] Save signed report and send parent evidence.
  - evidence:
    - slop/reviews/20260912_results_review.md
    - slop/reviews/20260912_results_review_checks.log
    - slop/reviews/20260912_results_review_cache_check.log
    - slop/reviews/20260912_results_review_tests.log
  - Log (PI/gpt-6-astra): final CPU checks completed successfully; reproduced missing random seed map, legacy export diagnostics type mismatch, inadmissible DEV Pareto anchors, random polygon order error, and unbounded HTTP500 retries. Selected full score reconstructed from 200/200 current keys. Historical C4 cache lineage remains unresolved. Report sent to parent; no production edits or goal approval.
3. [x] goal: Review reporting claims and consolidate verified findings
  - Deliverable: slop/reviews/20260912_repo_review.md, concise ranked findings in chat.
  - Failure mode: repeating stale audits or helper claims without inspecting evidence.
  - Evidence: slop/reviews/20260912_repo_review.md; parent inspected both helper reports, saved probes, raw sample, and decisive production source. Reporting fixture executed separately. No scientific success or production repair claimed. -- PI/OpenAI

## Verification
Success: findings have inspectable code/artifact evidence and bounded impact; suspicions remain labeled.
Likely failure: reading only old reports; check production source and saved results directly.
Subtle failure: a test bypasses production behavior; inspect the exercised function and fixture assumptions.
CPU-only installed-environment checks allowed, without downloads or dependency resolution.

-- PI/OpenAI
