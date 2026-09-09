# J-lens paper/reference fidelity audit

## Sources read

- Vendored paper: `/workspace/2026/jspace/jsteer/docs/papers/jacobian_lens_workspace.md`, source URL recorded at its first line as Transformer Circuits, July 6 2026.
- Vendored reference: `/workspace/2026/jspace/jsteer/docs/vendor/jacobian-lens/data/experiments/README.md`.
- Our implementation: `src/vjp_steering/vjp.py`, `scripts/reproduce_paper_j_lens.py`, and queued v14 command for `j_lens_swap`.

## Comparison

| part | reference | our code | read |
|---|---|---|---|
| coordinate operation | Swap replaces one lens coordinate with another across the workspace band. | `_swap_lens_coordinates` computes `h + α V(swap(V†h) - V†h)`. `j_lens_coordinate_swap` uses raw J-lens rows and `pinv`. | Same equation, subject to the lens file and selected band. |
| source and target | `verbal-report` takes the prompt's greedy answer as the swap-out token and swaps it to a candidate. | `scripts/reproduce_paper_j_lens.py` does this per prompt. `j_lens_swap` instead fixes `abrasive` -> `flattering` for every Bullshit Bench prompt. | The benchmark adaptation is not the paper's verbal-report intervention. |
| prompt positions | Reference applies the swap at every prompt position. | `j_lens_coordinate_prefill` uses the attended prompt mask and removes each hook after one prefill call. | Likely same position scope. |
| layer band | Reference describes a model-specific workspace band. | The reproduction script uses layers 13–21. The queued fixed-token adaptation uses the current `j_lens_swap` implementation, which selects 13–21 when available. | The old paper-native-sycophancy artifact used 6–24, so it cannot be mixed with v14. |
| reported success | Reference grades rank-1 of a specific swapped-in candidate. | The DEV benchmark grades behavior under a fixed-token adaptation. | Paper success does not predict that this adaptation beats random. |

## Finding

The coordinate-swap math and prompt-prefill hook match the reference description. The active-token condition does not: the reference swaps a token selected from each prompt's answer context, while the benchmark path swaps fixed `abrasive` and `flattering` coordinates. The latter is a new transfer hypothesis. It can fail without showing a math bug in the J-lens operator.

## Current operator check (before task 858)

| item | paper/reference | current reproduction |
|---|---|---|
| orientation | Vendor `JacobianLens.transport` computes `h @ J.T`; a candidate readout is then its unembedding row dotted with `J h` (`docs/vendor/jacobian-lens/jlens/lens.py:139-142`). | `j_lens_coordinate_swap` sets each basis row to `unembedding[token] @ J[layer]` (`src/vjp_steering/vjp.py:496-500`), the same row-vector orientation `h · J.T · unembedding[token]`. |
| layer mapping | Vendor lens rejects a layer outside recorded `source_layers` (`lens.py:150-155`). | `_load_j_lens` asserts `set(layers) <= set(checkpoint["source_layers"])` (`vjp.py:428-434`); current 13–21 is accepted. |
| final normalization | Vendor lens readout applies final norm before its lm head (`docs/vendor/jacobian-lens/jlens/hf.py:166-171`). | The real Qwen forward still applies `model.model.norm` after patched blocks. The swap basis is the linear `W_U @ J` row and has no local derivative of final norm. The source code read here does not establish whether the reference causal swap uses one. |
| revision provenance | Vendor `from_pretrained` accepts a revision (`lens.py:87-110`). | Reproduction resolves the lens through `J_WORD_LENS_REVISION="qwen-n1000"`; CLI `--source-revision` is output metadata only, not a lens-load argument. This is a provenance limitation, not yet orientation evidence. |

The paper says it measures a colon-position J-lens readout and applies the swap “at all token positions” (`docs/papers/jacobian_lens_workspace.md:195-203`). The local task858 was stashed behind unrelated default-queue work and task860 ran the identical alpha-one diagnostic remotely; no judge call was involved.

## Coordinate diagnostic result

`outputs/experiments/v14-paper-native-verbal-chat-country-swap-coordinate-diagnostic/results.json` records task860's Qwen chat `country` trial: France→Germany at alpha 1 on layers13–21. All hooks ran exactly once. Layer coordinate exchange errors are 0.00223–0.00973 and orthogonal residual errors 0.00765–0.01781, consistent with bfloat16 implementation error. The literal operator therefore executed.

The lens has category signal: Germany ranks above France in its candidate readout at layer13 (3 vs7) and layer19 (4 vs5). Yet the final Germany token worsened from rank14/logit16.375 to rank16/logit15.5625 while France stayed top1 and rose from21.5 to21.875. Alpha zero was exactly identical to clean. This rejects a missing-hook or transposed-coordinate explanation for this trial, while it does not identify the remaining source/target/producers mismatch.

## Next discriminating test

Do not sweep alpha. Compare the paper's prompt-active source-token choice and producer/checkpoint/final-norm treatment with the fixed `abrasive`→`flattering` benchmark adaptation. A repair test is justified only when that comparison states one concrete changed component and preserves the frozen DEV cohort and matched controls.

-- PI/OpenAI
