# J-lens paper/reference fidelity audit

## Sources read

- Vendored paper: `/workspace/2026/jspace/jsteer/docs/papers/jacobian_lens_workspace.md`, source URL recorded at its first line as Transformer Circuits, July 6 2026. Correct path includes `jspace`; `/workspace/2026/jsteer/...` is missing it.
- Vendored reference: `/workspace/2026/jspace/jsteer/docs/vendor/jacobian-lens/` (`jlens/lens.py`, `jlens/hf.py:166-171`, `jlens/fitting.py`).
- Our implementation: `src/vjp_steering/vjp.py`, `scripts/reproduce_paper_j_lens.py::clean_layer_lens_readouts`, and v14 `j_lens_swap`.

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
| final normalization | Vendor lens readout is `softmax(W_U norm(J h))` (paper Methods \& `hf.py:166-171` via `model.unembed`: `lm_head(final_norm(J h))`). JacobianLens.transport is bare `J h` (`lens.py:139`), then `apply` calls `model.unembed` which adds norm. | Our swap basis is raw rows `W_U @ J` (`vjp.py:496-500`), which matches paper's `V=[v_s v_t]` where `v_t` are rows of `W_U J` (no norm). The causal intervention is in residual space before the final norm; the full forward still applies `model.model.norm` (Qwen3_5RMSNorm eps1e-6, weight mean ~2.19, verified via `uv run` inspection on Qwen/Qwen3.5-4B) after patched blocks, so the swap survives through norm. The readout ranking, however, must include norm to be vendor-faithful. |
| revision provenance | Vendor `from_pretrained` accepts a revision (`lens.py:87-110`). | Reproduction resolves the lens through `J_WORD_LENS_REVISION="qwen-n1000"`; CLI `--source-revision` is output metadata only, not a lens-load argument. This is a provenance limitation, not yet orientation evidence. |

The paper says it measures a colon-position J-lens readout and applies the swap “at all token positions” (`docs/papers/jacobian_lens_workspace.md:195-203`). The local task858 was stashed behind unrelated default-queue work and task860 ran the identical alpha-one diagnostic remotely; no judge call was involved.

## Coordinate diagnostic result

`outputs/experiments/v14-paper-native-verbal-chat-country-swap-coordinate-diagnostic/results.json` records task860's Qwen chat `country` trial: France→Germany at alpha 1 on layers13–21. All hooks ran exactly once. Layer coordinate exchange errors are 0.00223–0.00973 and orthogonal residual errors 0.00765–0.01781, consistent with bfloat16 implementation error. The literal operator therefore executed.

The local lens checkpoint records 1,000 fitting prompts and source layers0–30 (`slop/logs/20260909_j_lens_dev/qwen_lens_checkpoint_metadata.log`); it does not record a Qwen workspace band. Layers13–21 were a compatible subset, not a producer-attested workspace selection. The paper supports full-band clamping for its models, but it defaults to Claude Sonnet4.5. This does not establish that 13–21 is the right Qwen band.

The saved `clean_layer_lens_readouts` in `v14-paper-native-verbal-chat-country-swap-coordinate-diagnostic` and its layer19 single-layer variant used raw `hidden @ (W_U @ J).T` without final RMSNorm. Their reported ranks (Germany above France at layer13 3 vs7 and layer19 4 vs5) are therefore not vendor-normalized J-lens ranks and must not be cited as reference fidelity. The vendor-faithful ranking is `W_U @ norm(J @ hidden)` with Qwen3.5's `model.model.norm` (RMSNorm) and `lm_head`; raw ranks differ by the per-dim learned weight scaling and RMS normalization. The final-logit outcome is independent of this readout bug: Germany worsened from rank14/logit16.375 to rank16/logit15.5625 while France stayed top1 (21.5→21.875) at alpha1, with alpha0 exactly identical to clean, rejecting a missing-hook or transposed-coordinate explanation for this trial while not identifying the remaining source/target mismatch.

## Normalization check — single corrected diagnostic (no new alpha sweep)

- Paper: `lens(h)=softmax(W_U norm(J h))` (Methods). `J` is `mean d h_final / d h_layer` (`fitting.py`); vendor `transport` is `h @ J.T` and `apply` composes it with `model.unembed` (norm+lm_head+softcap).
- Qwen3.5: `model.model.norm` is `Qwen3_5RMSNorm((2560,), eps=1e-06)` with learned weight mean ~2.19 (verified `uv run` load of Qwen/Qwen3.5-4B). `final_logit_softcapping` is None. Vendor `HFLensModel` for this family resolves to `Layout("model")` with `layers=model.layers`, `norm=model.norm`, `lm_head=lm_head`.
- Conclusion: Intervention basis stays raw `W_U @ J` (paper's `V`). Readout for fidelity grading must be vendor-normalized. The fix is to keep the swap unchanged and make `clean_layer_lens_readouts` emit both raw and vendor-normalized ranks, teaching that raw must not be labeled fidelity.
- Existing `paper-native-verbal-report-chat-alpha2-v1` has no `clean_layer_lens_readouts` at all; the two coordinate diagnostics have only raw ranks. No numeric conclusion about normalized ranks can be drawn until the single corrected diagnostic runs.
- Next run, if any, is one local or remote diagnostic: `scripts/reproduce_paper_j_lens.py` with `--coordinate-diagnostics` on the frozen France→Germany chat trial (single layer19 or 13–21), saving both raw and `source_vendor_*`/`target_vendor_*` ranks. It preserves frozen DEV controls and counts within the existing $20 v14 allocation; no DEV generation or judging is launched, and no DEV vs FULL mix.

## Next discriminating test

Do not sweep alpha. Compare the paper's prompt-active source-token choice and producer/checkpoint/final-norm treatment with the fixed `abrasive`→`flattering` benchmark adaptation. A repair test is justified only when that comparison states one concrete changed component and preserves the frozen DEV cohort and matched controls. The just-added vendor-normalized field is the prerequisite before any such repair test is judged.

-- PI/OpenAI
