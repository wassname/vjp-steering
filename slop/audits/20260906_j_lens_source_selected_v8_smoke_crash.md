# J-lens source-selected v8 smoke crash

Target: local process `proc_9b05`, run from `/workspace/2026/jspace/j-steer_pub` at HEAD `269a2607e72b2ed65adddec7460f5dc2d9be76eb` plus the uncommitted v8 diff. The exact command is preserved in the process event and the complete 35-line log is [`component-source-selected-v8-smoke-crash.log`](../logs/20260906_j_lens_native/component-source-selected-v8-smoke-crash.log). Runtime: PyTorch 2.13.0+cu130, safetensors 0.8.0, transformers 5.14.1.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| tiny J-lens construction | actual autograd lens and two controls complete | completed | yes | log line 4: `TINY_LENS_FIT actual_autograd=true persona_projection=true full_residual_control=true` | none | the shared setup executed |
| component extraction | two non-negative GP16 components | extraction reached both components | yes | line 15: `j_norms=[214.392..., 120.989...] remainder_norms=[43.944..., 25.820...]` | persisted metadata | extraction values were computed but the run stopped before metadata |
| vector hashing | hash tensors of any rank | scalar `target_index` caused `Tensor.view(torch.uint8)` to fail | no | lines 29–35: `RuntimeError: self.dim() cannot be 0 to view Long as Byte` | reload hash | no generated result is interpretable |
| generation and hook checks | both target directions change logits and restore clean logits | not reached | unclear | traceback starts at line 16 | logits, exchange residuals, text | operator execution remains untested by this process |
| judge and export | complete tiny judge and export | not reached | unclear | no completion markers after line 35 | all judged metrics | no behavioral claim follows |
| persistence | save extraction, responses, and DEV export | vector files were written; metadata was not | no | failure occurred while constructing `vector_content_sha256` | complete extraction metadata | partial output must be removed before rerun |

## Chronology

The run loaded the tiny model and built an autograd J-lens. The first pipeline checkpoint passed:

> `TINY_LENS_FIT actual_autograd=true persona_projection=true full_residual_control=true n_prompts=1 layers=(2,)`

The consumed concept prompt was visible in lines 7–14:

> `<|im_start|>user`
> `Tell me about sycophantic agreement and flattery toward the user<|im_end|>`
> `<|im_start|>assistant`
> `<think>`

Extraction then reported finite component and remainder norms. The first unsupported operation was hashing the new rank-zero integer `target_index`. `vector_sha256()` called `value.view(torch.uint8)`; PyTorch rejects changing the element size of a rank-zero tensor. This occurred before generation, judging, or export. There are therefore no positive, negative, or bare generated outputs to compare.

## Hypotheses

### H1 [bug | Almost Certain | 99%]

- **Mechanism:** v8 added scalar integer metadata to vector state, while `vector_sha256()` assumed tensors had at least one dimension.
- **Evidence:** lines 29–35 identify `vector_sha256()` and report `self.dim() cannot be 0 to view Long as Byte`.
- **Contrary evidence:** no competing traceback or earlier failure appears in the complete log.
- **Discriminating test:** reshape each tensor to one dimension before the byte view, then hash, save, reload, and compare the component vector. A pass supports this diagnosis; another failure localizes the next unsupported serialization operation.
- **Fix/action:** change to `value.reshape(-1).view(torch.uint8)` and add scalar-state hash/reload coverage.
- **Interpretability:** partial; setup and extraction executed, but no steering result did.

### H2 [harness | Remote | 5%]

- **Mechanism:** safetensors may reject or alter the rank-zero `target_index` even after hashing is fixed.
- **Evidence:** the crash happened immediately after vector save, before a reload test in this pipeline.
- **Contrary evidence:** the traceback is in local hashing, not `Vector.save()`, so rank-zero save itself already returned successfully.
- **Discriminating test:** compare `vector_sha256(component_vector)` before save and after `Vector.load()`.
- **Fix/action:** if reload changes rank or value, store a one-element integer tensor; otherwise retain the scalar.
- **Interpretability:** no for persistence until tested.

### H3 [method | Likely | 60%]

- **Mechanism:** even after the harness fix, source-selected behavioral coordinates may not move both benchmark directions outside the random-direction region.
- **Evidence:** this process produced no behavioral output; the preceding fixed exchange DEV result moved strongly in only the critical direction.
- **Contrary evidence:** v8 differs exactly where fixed exchange was structurally one-directional: it puts the larger coordinate on the requested component and leaves already-targeted positions unchanged.
- **Discriminating test:** complete this smoke, then run the preregistered two-direction DEV α grid and compare each judged direction with the existing random-direction region.
- **Fix/action:** do not enable the standard all-100 path until both DEV directions are coherent and outside that region.
- **Interpretability:** yes for the future DEV test; unresolved here.

## Decision

1. **Resolve-condition verdict:** not met. The intended condition was an end-to-end tiny run through generation, judging, and export; the last line is the hashing exception.
2. **Prediction check:** actual J-lens construction was supported; scalar vector persistence, generation, judging, and export were contradicted or unresolved because execution stopped at hashing.
3. **Earliest unsupported link:** content hashing of persisted side-specific vector state. A successful pre-save/post-load hash comparison supports it.
4. **Validity:** “invalid” means the process cannot test the source-selected steering behavior. `P(result is invalid) >99%`; this is an invalid behavioral result and a credible harness failure.
5. **Highest-information clues:** (1) the exact rank-zero byte-view exception localizes the failure; (2) `TINY_LENS_FIT` separates it from lens construction; (3) vector save returned before hashing, reducing the probability that safetensors rejected the scalar.
6. **Missing metrics:** pre/post-load hash equality; per-direction coordinate residual; logits-restored check; generated text; judge/export completion.
7. **Bugs requiring code changes:** H1 requires flattening before byte view and a scalar serialization regression test. H2 requires a one-element tensor only if reload changes the scalar.
8. **Misconceptions requiring reinterpretation:** none from this crash. It contains no evidence about sycophancy steering quality.
9. **What would change the verdict:** an otherwise identical rerun with matching vector hashes and the final pipeline completion marker.
10. **Recommended sequence:** fix and test hashing, remove only this process's partial output, rerun the same smoke, then inspect every stage. Do not start the real-Qwen extraction before it passes.

— PI/OpenAI Codex
