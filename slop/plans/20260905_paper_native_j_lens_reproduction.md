- [/] goal: reproduce the vendored paper's verbal-report coordinate swap on Qwen3.5-4B
  - use vendored `verbal-report.json` and its literal prompt; use raw single-token J-lens rows, pseudoinverse coordinates, and a complete source↔target swap
  - use layers 13–21: paper's workspace starts after roughly one third and ends before late layers dominated by the imminent output token; this is a model-matched approximation from fitted Qwen layers 6–24, not a claimed paper layer range
  - failure modes: current directed transfer is mistaken for a swap; chat formatting or token IDs differ; a swap changes output through incoherence
  - deliverable: saved clean/swap next-token ranks, raw vectors and token IDs, per-layer condition numbers, and first examples
- [ ] goal: decide whether an adaptation to sycophancy is justified
  - read full GPU/judge-independent native log and inspect raw outputs
  - if native swaps work, preserve the same coordinate clamp and change one feature at a time; if they fail, compare lens/version/model and patch implementation before behavior experiments
  - failure modes: a low score comes from candidates that do not tokenize to one token; a late motor layer makes a trivial output edit look like workspace steering
  - deliverable: audit with a clear native-reproduction verdict and next discriminating test

## UAT / Verification

| Scenario | What it looks like | How we catch it |
|---|---|---|
| success | swapped-in category candidate improves from clean rank and reaches rank 1 on some valid trials | saved per-trial clean/swapped rank table plus raw logits |
| likely failure | no target improves, or clean baselines are not valid | table separates invalid clean rows from valid swaps |
| sneaky failure | intervention changes output by breaking prompt handling or by late output-token editing | exact C=0/null, per-layer hook counts, prompt-token-only hooks, and workspace-layer diagnostics |
