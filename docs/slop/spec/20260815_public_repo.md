# Small public j-steer repo

## Goal

Publish one readable VJP-delta method and one notebook. Compare the VJP-delta method with mean difference, PCA, and a random-direction distribution. Keep the package below 2000 source lines.

## Scope

In: VJP-delta extraction, additive steering, four-method evaluation data, Markdown and HTML results, and one key plot.

Out: the method search, forced-choice moral evaluation, old variants, the selected 20-question claim, and a new evaluation framework.

## Requirements

- R1: Reimplement only VJP-delta extraction. Done means the public vector differs from the saved reference by less than `1e-4` in every element. A tiny-model check also compares the unreduced token gradients, valid-position mean, class subtraction, and sign.
- R2: Reuse `steering-lite` for mean difference, PCA, random directions, vector storage, and hooks. Done means the public repo has no copied baseline or hook implementation.
- R3: One notebook extracts all four vector types, generates bare and `+C`/`-C` text, and displays the shared plot function. A tiny random model is the default execution path.
- R4: The renderer is the only writer of persistent results. One measured data file generates `results.md`, `results.html`, and the key plot. The plot shows judged on-axis change against absolute judged off-axis change. The random-direction distribution is a band. Each row carries model, tokenizer, template, data hash, evaluation cohort, layer scope, batch size, date, seed, and source run.
- R5: Package and render code stay below 2000 lines. A source-file allowlist excludes old variants and evaluation code. A fresh clone installs in an isolated environment and runs with no development repo on `PYTHONPATH`.

## Tasks

- [/] T1 (R1-R5): Review the design before code.
  - verify: external plan review finds no dropped requirement or silent dependency on `j-steer-dev`.
  - likely failure: the public repo imports a local path.
  - sneaky failure: the plot uses the selected 20 questions and repeats the winner's curse.
- [ ] T2 (R1-R2): Write the VJP-delta extraction and use `steering-lite` for the shared runtime.
  - verify: a deterministic tiny-model check compares token gradients and each reduction with an independent reference calculation. Search for copied baseline or hook functions and local path dependencies.
  - likely failure: a hook returns detached activations, so the VJP fails.
  - sneaky failure: token masks or class subtraction differ while the output shape still passes.
- [ ] T3 (R3): Write one notebook for extract, steer, generate, and plot.
  - verify: execute the tiny-model notebook from start to finish in a new output directory. Assert that no development vector or output path appears in the notebook or execution record. The notebook displays but does not write the persistent result plot.
  - likely failure: the notebook needs an unlisted package or local data file.
  - sneaky failure: the displayed text comes from cached development artifacts instead of the notebook model.
- [ ] T4 (R4): Export measured four-method points and write one renderer.
  - verify: the renderer asserts one model, tokenizer, prompt template, data hash, evaluation cohort, layer scope, and batch size. It writes both result formats and the key plot from one CSV file. A parser compares every Markdown and HTML table cell.
  - likely failure: Markdown and HTML disagree.
  - sneaky failure: method curves and the random band use different evaluation cohorts.
- [ ] T5 (R5): Run the fresh-clone UAT, count lines, commit, and push.
  - verify: clone to a temporary directory outside the two worktrees. Clear `PYTHONPATH`, create a new uv environment from the lock, confirm no prior outputs, then run the source inventory, smoke check, renderer, result-equivalence check, and tiny-model notebook. Record lock resolution and commands in `docs/slop/uat/fresh_clone.md`.
  - likely failure: an editable local dependency makes the clone fail.
  - sneaky failure: generated files exist in the source repo but the renderer cannot recreate them.

## Context

The VJP-delta method uses a target contrast `c = mean(h_pos) - mean(h_neg)`. It averages `J(x)^T c` over valid token positions for each class, subtracts the class means, and normalizes each source-layer vector. `+C` follows the positive persona. The public data uses all 100 questions when available. The selected 20-question set is out of scope.

## Log

- 2026-08-15 CODEX: Use the existing `steering-lite` vector and hook runtime. This removes copied baseline and hook code.

## TODO

None.

## Errors

| Task | Error | Resolution |
| --- | --- | --- |
