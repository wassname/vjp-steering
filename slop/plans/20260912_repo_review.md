# Repository review

User: "review this repo for misconceptions and bugs please"

Scope: review and saved evidence only. No paid runs, GPU queues, production edits, publishing, or fixes.

1. [ ] goal: Review steering mathematics and reference fidelity
  - Deliverable: slop/reviews/20260912_steering_review.md with source lines and distinguishing tests.
  - Failure mode: treating an untested implementation assumption as a scientific null.
2. [ ] goal: Review evaluation, export, and publication figures
  - Deliverable: slop/reviews/20260912_results_review.md with source lines and reproductions.
  - Failure mode: calling a smooth curve or selected seed a measured comparison.
  - tasks:
    - [x] Read production judge/export/results code and both existing publication PNGs.
    - [/] Reproduce consequential failures with installed CPU environment.
    - [ ] Save signed report and send parent evidence.
  - Log (PI/gpt-6-astra): attached after parent added goal syntax; read-only CPU checks reproduce missing random seed map and legacy export diagnostics type mismatch. No production edits.
3. [ ] goal: Review reporting claims and consolidate verified findings
  - Deliverable: slop/reviews/20260912_repo_review.md, concise ranked findings in chat.
  - Failure mode: repeating stale audits or helper claims without inspecting evidence.

## Verification
Success: findings have inspectable code/artifact evidence and bounded impact; suspicions remain labeled.
Likely failure: reading only old reports; check production source and saved results directly.
Subtle failure: a test bypasses production behavior; inspect the exercised function and fixture assumptions.
CPU-only installed-environment checks allowed, without downloads or dependency resolution.

-- PI/OpenAI
