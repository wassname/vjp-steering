## Review

### Correct

- The core one-layer operator implements target sorting and interpolation as intended: coordinates are computed in float32, sorted toward the side-specific target, reconstructed through the basis, and rounded only when added back to the hidden dtype (`src/vjp_steering/j_lens_concept.py:172-181`).
- Positive alpha is correctly used for both sides (`scripts/experiment.py:149-152`, with an explicit assertion at `scripts/experiment.py:1199`). Toy checks cover swap-versus-identity behavior for both targets (`scripts/concept_checks.py:287-301`).
- The component mask is all attended prefill tokens, excluding padding (`src/vjp_steering/j_lens_concept.py:104-108`; test at `scripts/concept_checks.py:327-333`).
- Float32 basis/dual arithmetic is intentionally preserved for bfloat16 hidden states, and the test distinguishes it from prematurely rounded basis arithmetic (`scripts/concept_checks.py:305-326`). Safetensor round-trip hashing and target-index restoration are checked at `scripts/concept_checks.py:365-375`.
- The supplied tiny smoke completed generation, judging, and export (`slop/logs/20260906_j_lens_native/component-source-selected-v8-smoke.log:54`). Its diagnostics show both sides changed activations and logits, with coordinate residuals near zero (`outputs/experiments/j-lens-components-source-selected-tiny-smoke-v8/manifest.json:27324-27473`). Its extracted basis was healthy in this particular random run: cosine `0.5198` and condition number `1.779` (`outputs/experiments/j-lens-components-source-selected-tiny-smoke-v8/extraction/metadata.json:8499-8508`).
- Metadata correctly states the behavioral qualification that the operation is identity when the requested component is already active (`src/vjp_steering/j_lens_concept.py:461-463`).

### Findings

- **Finding: P1 — Later layers do not select using clean coordinates.**
  `concept_patch` determines the larger coordinate from the hidden state passed into each hook (`src/vjp_steering/j_lens_concept.py:177-180`), and hooks execute sequentially over all configured layers (`src/vjp_steering/j_lens_concept.py:189-205`). Consequently, layer 14 and later see activations already modified by earlier layers, so their source selection can depend on side and alpha rather than the bare-model coordinate ordering. Diagnostics likewise call the locally pre-patch, already-upstream-steered state “clean” (`src/vjp_steering/j_lens_concept.py:226-248`). This matters on Qwen because the real configuration uses layers 13–21 (`scripts/experiment.py:215-219`); the smoke uses only layer 2 (`outputs/experiments/j-lens-components-source-selected-tiny-smoke-v8/manifest.json:170-172`) and cannot expose it.
  **Smallest fix:** capture bare per-layer/token coordinate ordering once, then pass that fixed selector into every layer’s intervention and diagnostics. Add a multi-layer test where an early patch reverses a later layer’s current ordering but the requested target must still follow the cached clean ordering.

- **Finding: P1 — The basis is not formed from the GP16 reconstructions specified by the adaptation.**
  The extracted reconstructions are independently unit-normalized before stacking into `basis` (`src/vjp_steering/j_lens_concept.py:395-400`). Independent row scaling does not generally cancel under a pseudoinverse when the behavior compares the two coordinate magnitudes; it rescales the two coordinates differently and can change which one is considered larger. The smoke demonstrates that the discarded scales are materially unequal: reconstruction norms are `214.392` and `120.989` (`outputs/experiments/j-lens-components-source-selected-tiny-smoke-v8/extraction/metadata.json:7796,8203`). The metadata claim that scale cancels (`src/vjp_steering/j_lens_concept.py:465`) is therefore only true for a common scale, not these independent scales.
  **Smallest fix:** stack the raw GP16 reconstruction vectors as `V`, compute its dual, and update the operator/spec version and normalization metadata so old caches are rejected.

- **Finding: P1 — Rank collapse and behavioral side collapse are not robustly rejected or tested.**
  Extraction checks each row is nonzero but only rejects an exactly nonpositive smallest singular value (`src/vjp_steering/j_lens_concept.py:397-403`). Near-identical rows can have a small positive singular value, be truncated by `torch.linalg.pinv`, and yield equal coordinates; both target sorts then become identity. The smoke merely requires condition number `>= 1`, which even infinity satisfies (`scripts/concept_checks.py:451-453`). It exercises nonzero end-to-end behavior only for `+C` (`scripts/concept_checks.py:454-468`). The final hash inequality and target-index checks (`scripts/concept_checks.py:478-480`) catch literally identical serialized side vectors or duplicated target indices, but not identical/near-identical basis rows: the files still hash differently solely because `target_index` differs. Cached vectors are likewise returned after config and content-hash checks without component-specific rank, shared-basis, or distinct-target validation (`scripts/experiment.py:347-359`).
  **Smallest fix:** require numerical rank two with a documented condition-number ceiling, validate those invariants after extraction and cache loading, and assert nonzero and distinct realized behavior for both sides. Add a duplicate/near-duplicate basis regression test.

- **Finding: P1 — Calibration manifests are not self-contained and omit their source provenance.**
  Calibration loads vectors from `source_experiment` (`scripts/concept_checks.py:36-38`) but writes the source extraction metadata unchanged into the new target manifest (`scripts/concept_checks.py:172-203`). It never copies the safetensors or rewrites `vector_files`, so paths such as `extraction/plusC.safetensors` resolve under the new experiment even though those files remain under the source experiment. `load_or_extract` elsewhere explicitly interprets those paths relative to the experiment root (`scripts/experiment.py:345-352`). `source_experiment` and `source_metadata_sha256` are written only to the incremental `calibration.json` (`scripts/concept_checks.py:129-132`), not the authoritative manifest. Judge/export can still succeed because they do not load vectors, leaving an apparently valid but unreproducible manifest.
  **Smallest fix:** either copy and hash the vectors into the calibration experiment and rewrite `vector_files`, or define explicit external-source fields in the manifest and teach all readers to resolve them. Include the source experiment and source metadata hash in the manifest.

- **Finding: P1 — User-facing evidence labeling still describes this adaptation as a coordinate swap.**
  Although extraction metadata is appropriately qualified, the ordinary manifest path hard-codes both boundaries as `"signed unit concept contrast"` (`scripts/experiment.py:772-775`; visible in the smoke manifest at lines 24-31), which is false for this operator. The renderer labels the method `"J-lens concept-coordinate swap"` (`src/vjp_steering/results.py:55`), omitting “source-selected,” “behavioral adaptation,” and the fact that it is not paper evidence of sycophancy. This directly conflicts with the required evidence labeling.
  **Smallest fix:** use component-specific boundary meanings and rename the rendered method to an explicit source-selected behavioral adaptation, accompanied by a “not paper evidence” note.

### Merge verdict: BLOCK

The tiny smoke establishes one-layer mechanical operation, mask handling, serialization, and both positive-alpha semantics, but it does not validate the real nine-layer clean-source-selection contract, raw reconstruction basis, rank robustness, calibration provenance, or required evidence label.

— reviewer subagent, inherited model

## Main-agent resolution

1. The method is now named **target-ordered exchange**, not clean-source selection. Each layer orders its current coordinates toward the requested component. A two-layer test checks that an earlier exchange is not undone.
2. Independent unit normalization remains an explicit convention. The paper states that “every perturbation [was] rescaled to the same magnitude” but does not specify the normalization procedure. Metadata no longer claims that independent scaling cancels under the pseudoinverse.
3. Extraction and cache loading now reject numerical rank deficiency, mismatched bases or duals, and incorrect side targets. The smoke checks that both sides change logits and differ from each other.
4. Calibration now copies both vectors, writes relative vector paths, and records the source experiment plus source metadata hash. The calibration smoke confirmed byte-identical copies and completed judge/export.
5. The result label is now `J-lens target-ordered exchange (adaptation)`, and boundary descriptions state which component receives the larger coordinate.

The final v8b smoke and calibration smoke passed after these changes. A condition-number ceiling was not invented without a scale; singular values and condition number remain recorded for the real run.

— PI/OpenAI Codex