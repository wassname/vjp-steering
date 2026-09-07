# Correct J-lens readout and rerun

User: “please code it properly and run it”; “don't use claude to review”; “use subagents trivially”.

- [ ] goal: activity scores match the pinned official J-lens
  - [x] Correct transport → final normalization → unembedding in the primary diagnostic and bridge; isolate companion dependencies.
  - [x] CPU companion parity passes; native reviewer confirms formula. Existing experiment regression rerun is running.
    - Evidence: slop/logs/20260907_j_lens_prompt_span_activity/corrected-readout-supervisor-cpu.log reports `CORRECTED_COMPANION_APPLY_CPU_PASS primary=all_cells bridge=all_cells model=tiny_random_Qwen3_5 layers=13-21` and `J_LENS_CORRECTED_READOUT_SELF_TEST_PASS`; command exited zero.
  - [ ] Run one explicit prompt on Modal and compare full-vocabulary scores, top-1, ranks, tokenization and positions against official apply.
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
