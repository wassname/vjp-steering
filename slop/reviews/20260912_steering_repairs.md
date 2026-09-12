# Goal1 extraction repairs — handover (PI/gpt-6-astra → finished under GLM-5.3-flash, 2026-09-12)

Scope: scripts/experiment.py, src/vjp_steering/vjp.py, tests/test_steering_repairs.py (new),
tests/test_j_lens_vendor_readout_regression.py, tests/test_random_extraction.py. No commits, no GPU, no generation.

## Changes

1. Strict extraction identity. `extraction_request()` (experiment.py) hashes the resolved
   request: a stored format-version label `EXTRACTION_CONTRACT = "nonthinking_persona_global_oriented_vjp_v1"`, method, model, dtype,
   n_pairs, seed, max_length, extract_batch_size, requested layers (None sentinel = default),
   target_layer, j_lens_source, persona_direction, injection concepts (with defaults filled),
   lens path + SHA256. `validate_extraction_identity` requires and compares it on every reuse;
   missing identity → "lacks extraction_request … use a new --experiment-id" (old caches
   preserved, never relabeled). New extractions store the request; partial caches are rejected.
   Completed-profile early return in `gpu_stage` now validates identity first (manifest copy
   cross-checked against extraction metadata); manifests with profiles but no extraction identity
   are rejected.
2. Dropped flags fixed. `--lens-file` now reaches j_lens_swap / j_lens_unit_direction /
   j_lens_injection via the real dispatcher; a missing explicit lens fails with that exact path.
   MLP extractors receive `target_layer`; `--layers` that are not all layers before target are
   rejected (documented method constraint). Unsupported `--lens-file`/`--target-layer` on methods
   that ignore them fail fast (`validate_extraction_args`, also enforced inside extract_vectors).
3. Zero/nonfinite rejection. `_unit_direction()` in vjp.py rejects zero/nonfinite before
   normalizing: vjp_delta per-layer directions, activation axis, J_word layer directions,
   injection and unit-direction vectors. `validate_vector_values` guards every saved/reloaded
   Vector (zero check limited to direction methods; stacked multi-row concept tensors only need
   finiteness). Constant-Jacobian extractions now raise instead of saving NaNs.
4. VJP sign contract (approved by parent in intercom). Estimator unchanged
   (positive − negative class-mean pullbacks). Global orientation uses installed
   `steering_lite.variants.vjp_delta.orient_vjp_delta` against the positive−negative
   activation-mean axis, pooled at valid-position quantiles (0.25,0.5,0.75,1.0) — mirrors the
   library's axis, no extra forwards. Zero/ambiguous (orthogonal) orientation score is rejected,
   not silently kept. Label swap reverses the signed axis (tested on production `vjp_delta`).
   Logged as a heuristic, NOT behavioral validation.
5. Source format. `extraction_prompts` uses `thinking=False` (removes the manual `<think>`
   prefix; no more closed-then-reopened marker) and `seed=args.seed` (was hardcoded 0).
   Guards reject duplicated/unclosed/reopened `<think>` markers and nonempty think content.
   Verified on the actual cached Qwen tokenizer: 200/200 pairs retained, prompt identity changes
   (sha 1521e0fb… vs ab3adaa1…), single closed empty think block remains (Qwen template renders
   it for assistant continuations), matching eval's thinking-disabled rendering.
   Before/after full prompts + token IDs in the verification log.
6. J_word. Single-token concepts enforced (`' sycophantic'` is 4 subtokens on the cached
   tokenizer → rejects instead of averaging subtoken rows); zero lens direction rejects.
   Limitation on record: J_word's abrasive/candidness mismatch stands until a representation is
   chosen; method still not in experiment.py METHODS.
7. Vendor readout regression now calls the production `clean_layer_lens_readouts`
   (reproduce_paper_j_lens.py) on a nonuniform-norm fixture and compares independently computed
   RMSNorm arithmetic; identity-norm and uniform-norm mutations both fail the test.

## Verification

- `slop/reviews/20260912_steering_repairs_verification.log`: 23/23 unittest OK, CPU-only,
  offline, `uv run --no-sync` (14 new repair tests + existing vjp_delta/random/injection/
  unit-direction tests + production readout test), then tokenizer source-format check.
- `slop/reviews/20260912_steering_repairs_tests.log`: earlier run of the new suite.
- Discriminator lineage: slop/reviews/20260912_steering_evidence/discriminators.{py,log} (before).

## Unresolved / for parent

- Old extraction caches are intentionally incompatible; first rerun per experiment must use a
  new --experiment-id (or accept losing the old request identity). Historical results untouched.
- Orientation is the library heuristic; held-out behavioral sign validation still unmeasured.
- Source-fix changes prompt identity ⇒ prior persona-source extractions cannot be reused.
- v14 metadata has no implementation revision; historical provenance remains open (review §3).
- Concept `--layers` reuse flag: concept methods reject `--layers` (fixed source layers,
  `--concept-layers` owns application); this was chosen over silently ignoring the flag.
- pytest still absent; tests run via unittest.
