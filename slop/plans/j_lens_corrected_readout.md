# Correct J-lens readout and rerun

User: “please code it properly and run it”; “don't use claude to review”; “use subagents trivially”.

- [x] goal: activity scores match the pinned official J-lens using validated single-prompt execution
  - [x] Correct transport → final normalization → unembedding in the primary diagnostic and bridge; isolate companion dependencies.
  - [x] CPU companion parity and existing experiment regression pass; native reviewer confirms formula.
    - Evidence: slop/logs/20260907_j_lens_prompt_span_activity/corrected-readout-supervisor-cpu.log reports `CORRECTED_COMPANION_APPLY_CPU_PASS primary=all_cells bridge=all_cells model=tiny_random_Qwen3_5 layers=13-21` and `J_LENS_CORRECTED_READOUT_SELF_TEST_PASS`; command exited zero.
  - [x] One explicit prompt on Modal: 333 cells and 1,332 bridge ranks match official apply exactly (4ac6ef8).
  - [x] Test primary padded batch: failed 0/4; not a pass. Single-primary controls pass 4/4 with exactly zero score difference.
    - c880976 and c0e9285: batch repeat cells/hidden states identical; single mask present/absent identical. Batch shape changes BF16 exact ranks deterministically.
  - [x] Supervisor approved production batch_size=1; enforce and record execution correction. Keep batch2 only in explicit diagnostic; no scientific selection rule changed.
    - CPU companion/comparison, CLI rejection, frozen-function AST and experiment regression checks pass.
  - failure mode: corrected helper passes while the actual diagnostic still uses raw scores.
  - deliverable: saved parity output and implementation hashes.
- [ ] goal: measure the unchanged DEV-15 diagnostic correctly
  - [ ] After parity passes, rerun fixed prompts, tokens, layers, masks, exact-rank criterion, threshold and random sets on Modal.
  - [ ] Preserve task465; save a new artifact. Audit results and diagnose discrepancies before interpreting negatives.
  - failure mode: changed selection rules create an apparent improvement.
  - deliverable: new artifact and concise comparison with historical task465.
- [ ] goal: evaluate steering only if diagnostic eligibility passes
  - [ ] If eligible, use existing Modal generation and OpenRouter judging; produce the existing DEV table/plot with random comparison.
  - failure mode: changed text mistaken for broad judged effects.
  - deliverable: judged DEV results, or documented failed eligibility with no steering launched.

## Verification
Save test commands and complete outputs under slop/logs/. Review the actual primary readout, not only a test helper. Commit only task files, preserving unrelated changes. No public publication. Inspect any generated plot locally and with a fresh reviewer.

— PI/OpenAI Codex
