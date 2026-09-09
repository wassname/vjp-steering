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

## Next discriminating test

Run the existing `scripts/reproduce_paper_j_lens.py` with the vendored verbal-report data, raw colon prefill, a small fixed category/target subset, and the same Qwen model/lens file as v14. It must show exact α=0 logits and a swapped candidate rank improvement before modifying the behavior adaptation. If it fails, inspect token IDs, lens revision, and the 13–21 band. If it passes, compare a prompt-active source-token adaptation against the fixed-token adaptation on the frozen DEV cohort.

-- PI/OpenAI
