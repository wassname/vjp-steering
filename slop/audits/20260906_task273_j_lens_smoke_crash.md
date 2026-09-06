# Task 273: paper-native J-lens real-Qwen smoke crash

— PI/OpenAI Codex

Target: task 273, `uv run modal run scripts/run_modal.py::smoke_j_lens_swap`, `/workspace/2026/jspace/j-steer_pub`, 2026-09-06 12:08:13–12:08:50 +0800, exit 1. The relevant implementation was committed as `ce027f8`; the Modal log does not print a revision, so exact whole-worktree provenance is incomplete. Full evidence: [clean 162-line log](../logs/20260906_j_lens_native/task-273-clean.log), [raw pueue log](../logs/20260906_j_lens_native/task-273-raw.log), and [task metadata](../logs/20260906_j_lens_native/task-273-metadata.json).

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| model and data | Qwen3.5-4B loads; two paired smoke prompts | model loaded and one complete POS/NEG pair was printed | yes | `resolved method=j_lens_swap ... cohort=2/100`; full prompt in the clean log | exact source revision | extraction path was reached |
| extraction | raw `abrasive`/`flattering` J-lens basis and pseudoinverse dual | all 19 layers were constructed twice | yes | `operator=paper_native_pseudoinverse_coordinate_swap ... layers=(6, ... 24)` | basis/dual numeric diagnostics | the new operator was selected |
| persistence | both vectors save and reload | safetensors rejected `shared.layer6.dual` because it was non-contiguous | no | `ValueError: You are trying to save a non contiguous tensor: shared.layer6.dual` | reload hash | no generation could start |
| generation | two short steered generations | not reached | no | traceback begins in `vector.save` | all generation diagnostics | no behavioral result exists |
| resolve condition | serialization and generation complete | neither completed | no | exit status 1 | none | task 273 did not meet its stated condition |

## Chronology

The model and the real extraction input loaded normally. The first complete smoke pair differs only in `Answer as someone who is sycophantic.` versus `Answer as someone who is abrasive.` The shared suffix is `Tell me a story.`

The intended operator was reached:

> `04:08:43 | j_lens_swap operator=paper_native_pseudoinverse_coordinate_swap source=abrasive id=90474 target=flattering id=80238 layers=(6, ... 24)`

The first persistence operation then failed:

> `ValueError: You are trying to save a non contiguous tensor: shared.layer6.dual`

`torch.linalg.pinv(basis).T` returns a transposed view. Safetensors requires packed contiguous tensor storage. The error occurs before any intervention or generation, so it says nothing about J-lens behavioral performance.

## ml-debug form

| row | answer |
|---|---|
| log length; config | 162/162 cleaned lines read; Qwen3.5-4B, BF16, layers 6–24, C=1, two prompts, eight output tokens. |
| SHOULD lines | Prompt pairing SHOULD line is followed by the full pair and the suffix matches. No coordinate or generation SHOULD could run. |
| null and baseline | Not measured. Serialization failed before C=0 or bare generation. |
| initial demo | The full extraction pair is in the log; model outputs are not present. |
| dummy and baseline | Not reached. |
| schedule | No optimization schedule; fixed intervention smoke. |
| worst step | Persistence. No losses or gradients exist. |
| surprise | The algebraic self-test saved a contiguous pseudoinverse produced by a different expression, so it did not reproduce the production tensor layout. Explained by transpose contiguity, not the operator math. |
| missing to trust | successful save/reload, C=0 identity on Qwen, generated samples, hook counts, DEV judge output. |
| cheapest discriminator | call `.contiguous()` after transpose and rerun the identical smoke. Success predicts save/reload and generation; another failure localizes a second integration issue. |
| time and memory | 37 seconds wall-clock. Peak GPU memory was not logged. |

## Hypotheses

### H1 [bug | Almost Certain | 99%]

- **Mechanism:** the transposed pseudoinverse is a non-contiguous view that safetensors refuses.
- **Evidence:** `ValueError: ... non contiguous tensor: shared.layer6.dual` in the complete log; production used `torch.linalg.pinv(basis).T`.
- **Contrary evidence:** none for persistence; the local self-test saved a differently constructed contiguous tensor.
- **Discriminating test:** pack the tensor with `.contiguous()` and repeat task 273.
- **Fix/action:** save `torch.linalg.pinv(basis).T.contiguous()` and make the self-test use the same expression.
- **Interpretability:** yes, for the software failure only; no behavioral interpretation.

### H2 [method | Remote | 10%]

- **Mechanism:** the paper-native coordinate exchange could still fail behaviorally after persistence is fixed.
- **Evidence:** no task-273 generation exists; earlier category swaps did not uniformly work.
- **Contrary evidence:** earlier paper-native category trials reached the intended top token in 13/18 cases.
- **Discriminating test:** complete the smoke, then run the predeclared DEV boundary search and inspect raw responses.
- **Fix/action:** do not change the method before the serialization rerun.
- **Interpretability:** no behavioral result yet.

### H3 [harness | Highly Unlikely | 5%]

- **Mechanism:** Modal or safetensors version differences could impose a runtime-only constraint.
- **Evidence:** the error originates in the installed safetensors package.
- **Contrary evidence:** contiguous tensor storage is an explicit safetensors requirement and the tensor layout is directly observable.
- **Discriminating test:** local vector save with the production expression, then Modal rerun.
- **Fix/action:** change tensor layout, not dependency versions.
- **Interpretability:** yes for the integration failure.

## Decision

1. **Resolve-condition verdict: not met.** The label required “coordinate-swap vector serialization and generation”; the log stops at `vector.save`.
2. **Prediction check:** operator selection was supported; serialization and generation were contradicted; behavioral change remains unresolved.
3. **Earliest unsupported link:** vector persistence. A successful save/reload hash supports it.
4. **Validity:** `P(the crash diagnosis is invalid) ≈ 1%`. This is a credible software failure, not a method result.
5. **Highest-information clues:** the exact safetensors tensor name; failure before generation; the self-test/production pseudoinverse-expression mismatch.
6. **Missing metrics:** save/reload hash, Qwen C=0 identity, raw steered generation, hook counts, DEV judge scores.
7. **Bug requiring code change:** H1 → append `.contiguous()` and align the self-test.
8. **Misconception requiring reinterpretation:** none; do not interpret this crash as negative J-lens evidence.
9. **What would change the verdict:** failure after packing would indicate a second persistence or vector-schema issue.
10. **Recommended sequence:** fix only contiguity; rerun the identical smoke; only then run DEV calibration. Do not change tokens, layers, or α at the same time.
