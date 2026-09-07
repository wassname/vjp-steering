# Task 450 fresh-eyes extraction audit

## Review

### Correct

- **Execution completed successfully.** I read all 68 lines of `/tmp/task450.clean`. The run reports:
  > `EXTRACTION_COMPLETE id=j-lens-persona-components-source-v15 hash_plus=bb0529...7191`
  > `✓ Finished downloading files to local!`
  > `✓ App completed.`
  (`/tmp/task450.clean:49-68`)

- **The task-447 source-leakage defect is fixed.** The current constructor deduplicates by the actual rendered user message before seeded ordering (`scripts/experiment.py:232-241`). The extractor then requires exactly 65 unique source IDs (`src/vjp_steering/j_lens_concept.py:582-585`). Metadata records:
  > `"source_unique_count": 65`
  > `"source_fit_count": 52`
  > `"source_holdout_count": 13`
  > `"source_identity": "sha256(user_msg); duplicate rendered messages removed before seeded ordering"`
  (`extraction/metadata.json:314-317`)

  `/tmp/task450-extraction-summary.log` independently reports 65 source IDs, 65 unique IDs, and 65 unique prompts in each condition. Because fit is indices `[0:52]` and holdout `[52:65]` over this unique ordered list (`src/vjp_steering/j_lens_concept.py:610-616`), fit/holdout source-ID overlap is zero.

- **Prompt triples and assistant suffix align.** Construction renders all three conditions from the same `entry["user_msg"]` (`scripts/experiment.py:242-249`). Every prompt is checked against the exact assistant suffix (`src/vjp_steering/j_lens_concept.py:589-595`), which metadata records as:
  > `[248045, 74455, 198, 248068, 271, 248069, 271]`
  (`extraction/metadata.json:301-309`)

  First/middle/last inspection at indices 0, 32, and 64 found the same underlying Gatsby, snack-arithmetic, and turtle messages in all three conditions. All end with:
  > `<|im_start|>assistant\n<think>\n\n</think>\n\n`

  and final token ID 271 (`/tmp/task450-extraction-summary.log`, positive/negative/baseline samples).

- **Split-half stability is strong.** Independent 26/26 fit halves are reconstructed separately (`src/vjp_steering/j_lens_concept.py:642-648`). Across 18 components, GP split-half cosine ranges from `0.9403` to `0.9912`; full-signal split cosine ranges approximately `0.9690–0.9875`. The weakest result is:
  > `layer=16 ... split_gp_cosines=[0.9520993, 0.9403297]`
  (`/tmp/task450.clean:43`)

- **GP16 executed as a non-negative sparse reconstruction.** Coordinates are clamped non-negative during pursuit (`src/vjp_steering/j_lens_concept.py:154-190`). All 18 layer/direction components achieved 16 active items, finite nonzero norms, and monotonically decreasing residual histories. For example, layer-13 negative uses 16 positive weights and decreases residual norm from `4.1799` to `4.1158` (`extraction/metadata.json:41242-41341`).

- **The unexpectedly low reconstruction alignment is real but not an algebraic failure.** Across layers:
  - GP/full norm ratio: `0.198–0.326`
  - full-to-GP cosine: `0.203–0.319`
  - absolute GP norm: `1.02–4.10`

  Thus GP16 retains only about 20–33% of the full residual norm and lies roughly 71–78° from the full signal. The remainder retains approximately 94–98% of the full signal norm. This is a narrow, constrained dictionary reconstruction—not a close approximation of the complete instruction-induced residual. It is nevertheless far from numerical zero and is highly split-stable.

- **The two-component bases are well conditioned and distinct.**
  - component cosine: `0.468–0.685`
  - condition number: `1.661–2.312`
  - selected-support overlap: one token at layer 13 (`2362`, `<<`), zero at layers 14–21

  These comfortably pass the recorded review triggers of condition below 10 and absolute cosine below `.98`. The singular values remain separated; for example layer 13 has `[1.2942, 0.5702]` (`extraction/metadata.json:46470-46481`).

- **Held-out messages separate perfectly under the fixed instructions.** Both positive and negative conditions are target-ordered on all 13 held-out messages at every layer. Minimum mean margins are `1.512` for positive and `1.221` for negative (`/tmp/task450-extraction-summary.log`). At layer 13, for example:
  > positive mean `[1.3324, -0.1800]`
  > negative mean `[-0.3502, 1.4856]`
  (`extraction/metadata.json:46646-46659`)

  This demonstrates generalization across unseen source messages. It does **not** demonstrate generalization across instruction paraphrases or causal behavior.

- **DEV target-order eligibility is nontrivial at all layers.** All-position eligibility over the 981 attended positions ranges:
  - `+C`: `.525–.757`
  - `-C`: `.243–.475`

  Exact per-prompt eligible-position lists are persisted for all 15 prompts (`src/vjp_steering/j_lens_concept.py:692-739`). Prompt lengths are:
  > `55, 52, 59, 49, 59, 59, 77, 72, 69, 75, 61, 70, 73, 80, 71`

  summing to 981. Final-position eligibility is more asymmetric:

  | layer | final +C eligible | final -C eligible |
  |---:|---:|---:|
  | 13 | 15/15 | 0/15 |
  | 14 | 15/15 | 0/15 |
  | 15 | 15/15 | 0/15 |
  | 16 | 14/15 | 1/15 |
  | 17 | 5/15 | 10/15 |
  | 18 | 14/15 | 1/15 |
  | 19 | 12/15 | 3/15 |
  | 20 | 13/15 | 2/15 |
  | 21 | 12/15 | 3/15 |

  Therefore `-C` is not inert—it patches many earlier attended positions and several final positions, especially at layer 17—but equal effective strength between directions must not be assumed.

- **Saved vectors have the intended common basis and opposite targets.** Metadata hashes are:
  > `+C bb0529b0cc08b21ec8b7ffe9109e980ce841363dc8aaafb8d41e82fe6c737191`
  > `-C 123f56b3986e270779ca66c92b9d962d9059c0fcb4014bf935ab47b4fe65b0e0`
  (`extraction/metadata.json:12-15`)

  Both safetensor headers contain the same nine `[2,2560]` float32 basis/dual pairs. The `+C` target indices are all 0 and the `-C` indices all 1. `validate_component_pair()` requires exact basis and dual equality, target indices `0/1`, numerical rank two, and `basis @ dual.T ≈ I` (`src/vjp_steering/j_lens_concept.py:216-238`). The distinct whole-vector hashes are expected because target indices are included in `vector_sha256` (`scripts/experiment.py:163-171`).

### Findings

- **Finding: P2 — `reconstruction_error: 0.0` is a tautological closure check, not reconstruction quality.**
  The code defines `remainder = signal - component` and then records:
  > `"reconstruction_error": (signal - component - remainder).norm()`

  (`src/vjp_steering/j_lens_concept.py:649-661`). It must therefore be zero by construction. Quality must be assessed using the low GP/full ratios, cosine, remainder norm, and pursuit error history—not this field.
  **Smallest fix:** rename it to `decomposition_closure_error`, or add an explicitly named relative approximation error. Existing diagnostics are sufficient for the present calibration decision.

- **Finding: P2 — publication-grade model provenance is incomplete.**
  Metadata content-hashes the exact source, specification, implementation, tokenizer behavior, lens, components, and saved vectors, but records:
  > `"model_revision": null`
  > `"tokenizer_revision": null`

  (`extraction/metadata.json:310-312`). The 68-line execution log also does not print the command or commit; the separate audit’s `366242c` claim is not independently anchored in that log. No post-download verification-extraction artifact exists.
  **Smallest fix:** resolve and persist the HF model/tokenizer commit or model-weight hash before all-100/public reuse. Immediate DEV calibration can safely re-load and validate the source hash, vector hashes, basis, and dual through `load_or_extract()` (`scripts/experiment.py:448-466`).

### Interpretation boundary

This extraction combines a paper-matching non-negative GP16 routine with a new behavior-conditioned source and target-order adaptation. Metadata accurately calls it:

> `"paper_protocol_relation": "behavior-conditioned source adaptation using the paper GP16 reconstruction and target-order coordinate exchange"`

(`extraction/metadata.json`, emitted by `src/vjp_steering/j_lens_concept.py:783`).

The paper-style part establishes sparse reconstruction mechanics. It does **not** establish that the components control sycophancy or candid correction. In particular:

- the negative GP support includes tokens such as `" stupid"`, `" bitch"`, `" bastard"`, and `" screaming"` at layer 13 (`extraction/metadata.json:41242-41341`), despite the source instruction saying not to insult;
- held-out separation repeats the same fixed instruction wording;
- baseline ordering is biased toward the positive component on some layers;
- no generation, coherence, judged intended effect, off-axis damage, or dose response exists yet.

These are reasons to interpret DEV behavior empirically, not reasons to relabel or reject the extraction algebraically.

## Resolve and calibration verdict

**Recorded extraction resolve condition: MET, with interpretation caveats.**

The repaired unique 52/13 split has zero source-ID overlap, minimum split-half GP cosine `.940`, perfect 13/13 held-out target ordering in both directions at every layer, maximum condition `2.312`, maximum absolute component cosine `.685`, and nontrivial DEV eligibility minima `.525/.243`. The low full-to-GP cosine is concerning evidence that the component is narrow, but it was not an explicit failure threshold, is not numerically tiny, and is counterbalanced by independent split stability and held-out separation.

**Proceed with the fixed non-negative DEV calibration. Do not block calibration.**

Conditions:

1. Reuse these exact vector hashes, source experiment, layers, instructions, and target labels.
2. Keep alpha finite and non-negative; the calibration code already enforces this (`scripts/concept_checks.py:66-77`).
3. Inspect raw first/middle/last generations, generation health, per-side realized patch norms, coordinate residuals, changed-position counts, final-token KL/logit changes, and blinded judge signs.
4. Treat wrong-sign, null/random-region, or incoherent behavior as rejection of this component instance. Do not sign-flip or relabel after observing DEV.
5. Do not describe this extraction result itself as behavioral evidence or advance it to all-100/public results without successful DEV behavior and stronger model provenance.

**Merge verdict: OK with notes.**