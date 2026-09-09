# Paper-native coordinate diagnostic

- run: Pueue task 860, Modal app invocation through `paper_coordinate_diagnostic`, terminal `Success`; full log: `slop/logs/20260909_j_lens_dev/task860-paper-coordinate-full.log`.
- input: Qwen/Qwen3.5-4B chat prompt `Think of a country. Answer in one word:`, clean source France (token 47358), target Germany (48484), alpha 1, layers 13-21.
- artifact: `outputs/experiments/v14-paper-native-verbal-chat-country-swap-coordinate-diagnostic/results.json`.

## Observations

The saved result records the actual lens file as `neuronpedia/jacobian-lens@qwen-n1000`, file `qwen3.5-4b/jlens/Salesforce-wikitext/Qwen3.5-4B_jacobian_lens_n1000.pt`. The CLI `--source-revision=fc30…` remains result metadata, not the lens revision.

At all nine layers, the one-shot prefill hook ran once for alpha zero and once for alpha one. The alpha-one source/target coordinate means exchange to bfloat16-scale error: maximum coordinate-exchange errors range from 0.00223 (layer 19) to 0.00973 (layer 18); maximum residual errors range from 0.00765 to 0.01781. This directly supports a working hook and swap equation on the measured hidden states.

The fitted lens readout ranks Germany above France at several layers (Germany ranks 3 vs France 7 at layer 13, and 4 vs 5 at layer 19). This shows the checkpoint has a nonzero category signal at these layers. It does not establish a causal generation effect.

The final logits move away from the target: Germany is rank 14/logit 16.375 clean and rank 16/logit 15.5625 after the literal swap. France remains top 1 and rises from 21.5 to 21.875. Alpha zero is exactly identical to clean.

## Source-side comparison

Vendor `JacobianLens.transport` uses `residual @ J.T` (`docs/vendor/jacobian-lens/jlens/lens.py:135-142`). Our basis row is `unembedding[token] @ J`, the same row-vector orientation for the coordinate definition. Vendor `HFLensModel.unembed` applies final RMS normalization before the lm head (`docs/vendor/jacobian-lens/jlens/hf.py:167-171`), whereas the causal swap basis is raw `W_U @ J`; producer/reference code read does not establish that the published causal intervention includes a derivative through this nonlinear normalization.

## Layer-scope check and decision

The paper supports the full-band assumption, rather than a single selected layer: it says “all swaps are applied at the full workspace layer range” (Figure 62 caption) and describes swaps at every token position “across a band of intermediate layers.” It also says its default model is Claude Sonnet 4.5; our artifact is Qwen/Qwen3.5-4B. The paper therefore does not establish exact model transfer.

A same-basis alpha-one algebra check is an involution (maximum absolute return error `2.53e-07`; `slop/logs/20260909_j_lens_dev/j_lens_swap_involution.log`). It does not establish that swaps across different layer bases cancel. The alternating layer means in the real run are suggestive only.

The evidence rejects the current hypothesis that the alpha-one failure is a missing hook or a transposed coordinate operation. It leaves two live explanations: (1) repeated full-band writes weaken or cancel the source/target change before the final answer; (2) the fitted lens coordinate is only a readout, or Qwen/prompt/producer differs materially from the paper setting. One bounded alpha-one layer-19 versus existing full-band diagnostic is justified to distinguish the first explanation. Do not sweep alpha or call the fixed-token DEV J-lens method repaired from this result.

-- PI/OpenAI
