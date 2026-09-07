# Bounded batch and mask controls: before execution

First run c880976 (Modal ap-jJtDYTZNkN2odUQu50qKFu) failed: batch 0/4, single 4/4 exact. Tokens, request positions and offsets agree. BF16 batch score differences reach 0.125–0.25; all 36 single layer records have zero difference. No DEV15 launched. Artifact recovered unchanged from Volume.

Supervisor approved exactly one same-two-row control run, without changing thresholds, tokens, layers, dtype or model. Add repeated batches and single all-ones mask absent/present comparisons. Production defaults unchanged. CPU tests pass, including identical single masked/unmasked hidden states and rejection of mask omission on padded inputs.

| Option | Prediction | Distinguishes |
|---|---|---|
| Repeat same batch | Identical hidden states and scored primary cells | Deterministic batch-shape effects versus nondeterministic execution |
| Single prompt, all-ones mask versus omitted mask | Identical hidden states and primary cells; both match official | Shape-dependent numerical effects versus presence of mask path |
| Change dtype or score/rank tolerance | Not run | Would change diagnostic contract |

Rough diagnosis priorities: deterministic BF16 batch-shape effects 85%; mask-path bug 7%; nondeterministic kernel 3%; unknown 5%. Batch-shape effects predict exact repeats and mask equivalence, but recurring batch/reference rank disagreements. This does not by itself isolate the responsible GEMM/attention/linear-attention kernel. Source implementation hashes and complete differences/margins persist. Planning cost under 10 min H100 ≈ $0.66; actual first parity compute stage was 23.44s, peak 13.85GB. Full DEV15 remains prohibited on mismatch. Next production option, only after reporting controls and receiving approval: batch_size=1 to match official apply, not looser ranks.

— PI/OpenAI Codex
