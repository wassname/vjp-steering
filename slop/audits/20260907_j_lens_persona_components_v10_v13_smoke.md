# Matched-persona J-lens component smoke: v10 failure and v13 repair

Target: verify matched-persona GP16 extraction, target-ordered coordinate intervention, artifact reload, judging, and export before a real-Qwen extraction.

Provenance: `dev3`; executed from an uncommitted worktree containing the matched-persona implementation later recorded by this change. The retained logs are complete: 31 lines for v10 and 35 lines for v13. This audit covers a random-model integration test, not behavioral evidence.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| source preparation | 200 aligned persona/baseline sources | `Loaded 200 branching suffixes` | yes | `component-persona-v13-final-smoke.log:6` | source examples are in metadata, not stdout | source count and persisted identities are checkable |
| extraction | two GP16 components with diagnostics | GP norms 172.79/287.00; split cosines .979/.985; component cosine .693; condition 2.349 | yes for a random smoke model | `component-persona-v13-final-smoke.log:7` | no real-Qwen measurements | validates code flow only |
| generation | bare plus four intervention cells | five `generation 15/15` lines | yes | `component-persona-v13-final-smoke.log:8-13` | random outputs are incoherent | cannot interpret behavior |
| artifact reload | fresh tokenizer and exact lens content accept compatible cache | reload and hook check passed | yes in v13; no in v10 | v10 `:16-31`; v13 `:14-17` | remote Modal reload not yet tested | local cache validation is valid |
| intervention | both directions alter logits, differ, and restore clean logits | all five checks true | yes | v13 `:17` | no BF16/Qwen measurement | sufficient for the integration test |
| judge/export | 60 pairs available and export completes | 60 cached, 0 missing; 4 treatment rows and 60 scenarios exported | yes | v13 `:18-35` | cached random-model judgments have no scientific value | verifies interfaces and answer-key cache key |
| public artifacts | smoke must not change public results | `public_outputs_untouched=true` | yes | v13 `:35` | none | safe to proceed to extraction-only |

## Chronology

The v10 run completed extraction and generation before failing during a fresh artifact reload:

> `GPU_STAGE_COMPLETE experiment=j-lens-persona-components-tiny-smoke-v10-final profile=dev cells=4`
>
> `ValueError: persona component source identity mismatch: ['tokenizer_content_sha256']`

Source: `slop/logs/20260906_j_lens_native/component-persona-v10-final-failed.log:13-31`.

The rejected hash used `tokenizer.backend_tokenizer.to_str()`. A direct reproduction changed that digest after padded tokenization even though vocabulary and chat behavior were unchanged:

> `old_before=41e00e...`
>
> `old_after=3288d9...`
>
> `old_stable=False`

Source: `slop/logs/20260906_j_lens_native/component-persona-v13-tokenizer-hash.log:1-3`.

The v13 fingerprint parses the complete tokenizer backend, removes only mutable padding/truncation runtime state, and adds the special-token map, chat template, padding side, and truncation side. It therefore includes BPE merges, normalizer, pre-tokenizer, post-processor, decoder, and AddedToken flags. It remained identical before use, after padded tokenization, and in a fresh tokenizer instance:

> `new_before=557378...`
>
> `new_after=557378...`
>
> `new_fresh=557378...`
>
> `new_stable=True`

Source: `slop/logs/20260906_j_lens_native/component-persona-v13-tokenizer-hash.log:4-7`; implementation: `src/vjp_steering/j_lens_concept.py` (`tokenizer_content_hash`). V13 also resolves and checks the actual default J-lens content on every cache validation, and its implementation hash covers both `j_lens_concept.py` and the `vjp.py` lens/hook implementation.

The clean v13 run repeated extraction and generation, loaded the saved vectors with a fresh model/tokenizer, changed both directions' logits, restored clean logits after hook removal, then exercised judge and export:

> `CONCEPT_REAL_HOOK_CHECK both_directions_changed_logits=true distinct=true restored_logits=true calls_once=true removed=true diagnostics=true`
>
> `CACHE_CHECK required=60 cached=60 missing=0 API_calls=0`
>
> `J_LENS_CONCEPT_PIPELINE_SMOKE_PASS ... public_outputs_untouched=true`

Source: `slop/logs/20260906_j_lens_native/component-persona-v13-final-smoke.log:17-35`.

I inspected the first and last complete response in the bare and each of the four intervention files. They are long multilingual repetitions from the tiny random model. The manifest marks every treatment cell unfinished and repetitive. This is expected for the random-model smoke and explicitly prevents semantic interpretation. The relevant control is execution through the real loaders, vectors, hooks, files, judge rows, and exporter—not response quality.

The standalone self-tests also passed:

> `J_LENS_SWAP_SELF_TEST_PASS alpha0=identity alpha1=coordinate_exchange transfer=exact prompt_only=exact reload=exact`
>
> `EXPERIMENT_SELF_TEST_PASS quick_calls=270 full_calls=400 resume_cells=18`
>
> `J_LENS_CONCEPT_SELF_TEST_PASS nonnegative=true exact_fit=true ... reload=true cache_rejection=true`

Source: `slop/logs/20260906_j_lens_native/component-persona-v13-self-test.log:2-4`.

## ML-debug form

| row | answer |
|---|---|
| log length; config | v10: 31 lines; v13: 35 lines. Tiny random Qwen, CPU float32, layer 2, 200 sources, GP16, alpha .25/1 for each direction. |
| `SHOULD:` lines | None were emitted. The explicit expected terminal line was `J_LENS_CONCEPT_PIPELINE_SMOKE_PASS`; it appears at v13 line 35 and is absent from v10. |
| numbers and null | Behavioral scores use a random model and are null-quality by construction. Extraction diagnostics are liveness checks, not scientific baselines. |
| before intervention | Bare outputs are incoherent and repetitive. This establishes only that the random model is unsuitable for behavior measurement. |
| dummy/control | Alpha-zero identity is covered by the self-test; the clean logits are restored after hook removal. |
| baseline model | Hook check compares intervention logits with clean logits and reports both directions changed and restoration succeeded. |
| schedule | No training or schedule. |
| full sample | First and last records in all five JSONLs were inspected; examples are under `outputs/experiments/j-lens-persona-components-tiny-smoke-v13/`. |
| worst step | v10 artifact reload failed before judge. No gradients or losses exist. |
| surprise | v10: `tokenizer_content_sha256` differed after a fresh load despite the same tokenizer. Explained: the old serialization includes mutable runtime padding state. |
| absent evidence | Real-Qwen layerwise extraction diagnostics and held-out separation; these require the extraction-only run. |
| diagnoses | H1 below 99%; H2 15%; H3 10%; unknown 5%. |
| fresh review | The preflight, follow-up, and v11 cache review are saved under `slop/reviews/`. The v11 review identified omitted tokenizer internals and default-lens content; both are addressed in v13. |
| cheapest discriminator | Hash one tokenizer before/after padding and compare with a fresh instance. The old hash changed; the new hash did not. |
| wall-clock/GPU | v13 took 61 seconds on CPU. Stage GPU memory was not logged; no GPU was used. |

## Hypotheses

### H1 [harness | Almost Certain | 99%]

- **Mechanism:** `backend_tokenizer.to_str()` serializes mutable runtime padding/truncation configuration, so extraction and reload hashed operational state rather than tokenizer content.
- **Evidence:** `old_stable=False` with two different hashes after only padded tokenization (`component-persona-v13-tokenizer-hash.log:1-3`).
- **Contrary evidence:** none after direct reproduction; package-version differences could also alter backend serialization but are not needed to explain this failure.
- **Discriminating test:** compare old and new hashes before/after padding and across fresh loads. Old should differ while the content hash should remain equal; observed exactly.
- **Fix/action:** canonicalize the complete backend tokenizer while excluding mutable padding/truncation state; use the same helper when persisting and validating metadata.
- **Interpretability:** yes for the smoke failure; no behavioral claim is made.

### H2 [bug | Remote | 3%]

- **Mechanism:** the replacement fingerprint could still omit a high-level tokenizer setting that changes extraction token IDs.
- **Evidence:** generic `init_kwargs` are not hashed because they include local paths and runtime settings.
- **Contrary evidence:** the canonical backend includes segmentation and AddedToken behavior; the hash also includes chat and padding settings. Exact rendered prompts, source IDs, assistant suffix IDs, revisions, and spec hashes are independently compared.
- **Discriminating test:** alter BPE merges, AddedToken behavior, or the chat template and require cache rejection; compare the 600 stored final-token records on reload if a mismatch is suspected.
- **Fix/action:** retain all independent identity checks. Add another stable field only if a concrete mismatch escapes them.
- **Interpretability:** yes for the observed run; a hypothetical omitted setting would affect cache reuse only.

### H3 [method | Highly Likely | 80%]

- **Mechanism:** a successful random-model smoke says nothing about whether real-Qwen persona residuals form stable causal components or change judged sycophancy.
- **Evidence:** every inspected random-model response is incoherent, and every treatment cell has `unfinished` and `repetition` breakdown reasons.
- **Contrary evidence:** the extraction diagnostics are finite and the hook behavior is correct, so the engineering path is exercised.
- **Discriminating test:** run extraction-only on Qwen3.5-4B and inspect split-half stability, held-out coordinates, conditioning, and DEV target-order eligibility before calibration.
- **Fix/action:** proceed only to extraction, not directly to public evaluation.
- **Interpretability:** yes as integration evidence; no as behavioral evidence.

### H4 [bug | Remote | 5%]

- **Mechanism:** a stale vector could pass metadata checks while its tensor payload differs.
- **Evidence:** metadata and vector files are separate artifacts.
- **Contrary evidence:** reload compares `vector_content_sha256` and calls `validate_component_pair` (`scripts/experiment.py:447-455`); the smoke reports `reload=true` and `cache_rejection=true`.
- **Discriminating test:** modify a saved tensor and require reload rejection; existing cache-rejection self-test covers the relevant path.
- **Fix/action:** no change unless the fresh review identifies a missing payload field.
- **Interpretability:** yes.

## Decision

1. **Resolve-condition verdict: met.** The requested integration condition was a clean extraction, intervention, reload, judging, and export sequence with stable source identity. V13 ends with `J_LENS_CONCEPT_PIPELINE_SMOKE_PASS`; the tokenizer reproduction isolates the v10 false mismatch, while v13 also validates exact lens content.
2. **Prediction check:** fresh reload acceptance was supported; both directions changing logits was supported; public outputs remaining unchanged was supported; real-Qwen semantic separation remains unresolved.
3. **Earliest unsupported link:** the real Qwen persona-conditioned final-prefill residual must yield stable, distinct GP16 components. The extraction-only diagnostics are the next evidence.
4. **Validity:** invalid would mean the smoke failed to exercise the production interfaces or accepted mismatched artifacts. Estimated `P(smoke conclusion is invalid) = 5%`. Classification: credible positive integration result, not a scientific result.
5. **Highest-information clues:** (1) old hash changes after padding; (2) the canonical backend hash is stable across state change and reload; (3) v13 fresh reload, lens identity, and hook checks pass.
6. **Missing metrics:** real-Qwen split-half cosines; held-out source-coordinate separation; layerwise condition numbers; DEV eligibility; Modal download/reload evidence.
7. **Bugs requiring code changes:** H1 is fixed by `tokenizer_content_hash`. The review's default-lens identity issue is fixed by unconditional resolved-file hashing and by including `vjp.py` in the implementation digest.
8. **Misconceptions requiring reinterpretation:** the random-model component metrics and judge values must not be treated as evidence that J-lens steers sycophancy.
9. **What would change the verdict:** a reviewer finding that the fingerprint omits tokenization behavior not already fixed by exact prompt/suffix comparisons, or a clean run that fails on a fresh tokenizer, would reopen the cache bug.
10. **Recommended sequence:** obtain a focused review of the v13 cache fixes, commit the bounded change, then run real-Qwen extraction-only. Do not calibrate until the extraction diagnostics are audited.

— PI/OpenAI Codex
