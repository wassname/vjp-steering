# Matched persona-component v9 preflight review

## Review

### Correct

- **Basis/dual algebra is correct.** The implementation uses the repository’s row-basis convention:
  - `basis: [2,d]`
  - `dual = pinv(basis).T: [2,d]`
  - `coords = h @ dual.T: [...,2]`
  - `delta = Δcoords @ basis: [...,d]`

  See `src/vjp_steering/j_lens_concept.py:647-657`, `:191-211`. `validate_component_pair()` also verifies rank and `basis @ dual.T ≈ I` at `:191-199`. BF16 application retains float32 basis/dual arithmetic before casting only the residual back to the hidden dtype (`:203-211`), and the precision-sensitive synthetic check is at `scripts/concept_checks.py:476-499`.

- **Fit and holdout data are separated.** The first 160 randomly permuted sources are used to fit signals and the remaining 40 only for held-out coordinates (`src/vjp_steering/j_lens_concept.py:578-612,660-662`). Tiny metadata confirms `source_fit_count=160` and `source_holdout_count=40` at `metadata.json:838-839`.

- **Split-half diagnostics are independently computed.** Each direction gets two disjoint halves of the fit subset, and both full-signal and independently reconstructed GP cosines are recorded (`src/vjp_steering/j_lens_concept.py:610-640`). Tiny values are stable: full cosines `0.9946/0.9975` and GP cosines `0.9788/0.9851` (`metadata.json:84409-84410,84646-84647`).

- **GP16 is genuinely nonnegative.** Coordinates are clamped nonnegative during every pursuit update (`src/vjp_steering/j_lens_concept.py:133-171`). Tiny metadata has 16 positive weights for each direction (`metadata.json:84373-84389,84610-84626`) and strong reconstruction diagnostics (`:84311-84317,84548-84554`).

- **Source and DEV diagnostics are calculated in the fitted coordinate system.** Held-out positive, negative, and baseline coordinates and DEV final-token coordinates are persisted (`src/vjp_steering/j_lens_concept.py:660-682`). Tiny held-out means separate strongly in the expected coordinates (`metadata.json:85282-85294`).

- **Prompt construction is matched by construction and fails on truncation.** All three conditions are rendered from the same sampled entry inside one loop, prompts and source IDs are persisted, and overlength inputs fail rather than truncate (`scripts/experiment.py:220-246`; `src/vjp_steering/j_lens_concept.py:706-725`).

- **Target ordering is implemented with the correct eligibility definition.** `+C` changes positions where coordinate 0 is lower and `-C` where coordinate 1 is lower (`src/vjp_steering/j_lens_concept.py:182-189,665-687`). Tiny aggregate eligibility is balanced, `0.482/0.518` (`metadata.json:85362-85371`).

- **Modal extraction argv propagation works.** The local entrypoint forwards model, dtype, prompt count, extraction batch size, maximum length, and `j_lens_source`; the remote function adds `--extract-only` and invokes `scripts/experiment.py` (`scripts/run_modal.py:66-83,346-365`).

- **The answer-key cache fix is present and successful.** `answer_key` is now a module-level function, and its content hash is part of every cache key (`scripts/judge.py:104-118`). `walk.answer_key_sha256()` hashes scenario plus `nonsensical_element` (`scripts/walk.py:86-93`). The first smoke failed at the former local-shadowing bug (`/tmp/jlens-persona-components-v9-smoke.log:52-62`); the fixed run judged all 60 cells and exported successfully (`/tmp/jlens-persona-components-v9-smoke-fixed.log:38-41`).

- **Smoke reuse did not conceal an unexecuted extraction in this specific sequence.** The failed run freshly executed `extract_persona_components` and logged the resulting norms, stability, condition number, and eligibility (`/tmp/jlens-persona-components-v9-smoke.log:8-11`). The subsequent successful run says `reused=true` (`smoke-fixed.log:6`), but then reloads and validates the vectors at `scripts/concept_checks.py:620-626`. The answer-key-only repair did not require recomputing extraction. This does not, however, eliminate the general cache weakness below.

### Findings

- **Finding: P1 — The negative instruction is not the instruction approved by the design review.**
  `src/vjp_steering/j_lens_concept.py:60-63` uses:

  > “bluntly candid; states plainly when the named method, framework, factor, or threshold does not exist; …”

  The design review’s **Minimum source construction** mandates:

  > “Answer as someone who is bluntly candid, explicitly identifies false or incoherent premises, provides a useful correction, and does not insult or refuse.”

  The incompatible string is already embedded in the smoke artifact (`metadata.json:22,84547`). This changes the extracted causal source and breaks the requested attribution-preserving experiment.
  **Smallest fix:** restore the approved exact string, bump `PERSONA_COMPONENT_PAIR_VERSION`, regenerate under a fresh/empty experiment ID, and keep the resulting exact string in metadata.

- **Finding: P1 — Required target-order eligibility by benchmark position is missing.**
  `attended_residuals()` flattens all attended tokens across all DEV prompts (`src/vjp_steering/j_lens_concept.py:360-372`). Eligibility is consequently emitted only as one aggregate count/fraction per side and layer (`:665-687`; `metadata.json:85362-85371`). The design review explicitly requires eligibility “by side, layer, and benchmark position.” The artifact does not retain the all-position coordinates needed to derive this later, so a real extraction would have to be rerun.
  **Smallest fix:** retain prompt/position structure and persist eligibility per DEV scenario and attended position, with final-token and aggregate summaries.

- **Finding: P1 — Persona source identity and exact 200-source contract are not enforced on cache reuse.**
  Source creation samples `min(args.n_pairs, len(entries))` instead of requiring exactly 200 (`scripts/experiment.py:224-225`), while extraction accepts any 20 or more sources (`src/vjp_steering/j_lens_concept.py:558-562`). More importantly, component cache validation checks method/model/dtype, representation, operator, spec, and the hash of only `j_lens_concept.py`, but neither `n_pairs` nor `source_sha256` (`scripts/experiment.py:336-359`). Source rendering itself lives in `scripts/experiment.py:220-246`, outside `implementation_hash()` (`src/vjp_steering/j_lens_concept.py:75-76`). Thus a changed source dataset/rendering path or changed requested count can silently reuse an old extraction at `scripts/experiment.py:403-419`. Model/tokenizer revisions are also unpinned behind the same repository name.

  **Smallest fix:** require exactly 200 sources; regenerate current prompts/source IDs during cache validation and compare `n_pairs`, `source_sha256`, source IDs, and prompt hash; persist and validate resolved model/tokenizer revisions. Add persona-component-specific cache rejection tests.

- **Finding: P2 — Triple alignment checks only lengths and final token IDs, not the mandated identical assistant suffix.**
  The extractor checks condition lengths and only each triple’s final token ID (`src/vjp_steering/j_lens_concept.py:555-573`). Current internal construction is aligned, but a tokenizer/template change or direct caller could supply mismatched suffixes that share the same final token.
  **Smallest fix:** persist per-condition source IDs and assert identical source order plus exact tokenized assistant-generation suffix for every triple.

- **Finding: P2 — Custom calibration coefficients can violate the stated nonnegative protocol.**
  The component method advertises “non-negative target-exchange calibration only” (`scripts/experiment.py:1314-1317`), but calibration parses arbitrary floats without finite or nonnegative validation (`scripts/concept_checks.py:65-70`). Defaults are compatible and include alpha zero, but a negative custom coefficient moves away from the target ordering.
  **Smallest fix:** reject nonfinite or negative coefficients and normalize duplicate alpha-zero entries.

### Tests and evidence status

- Fresh tiny extraction and generation ran before the judge failure.
- The fixed resumed smoke passed real hooks, 60-cell judging, and export.
- The successful smoke was not a clean extraction rerun.
- No command was executed during this review. After fixes, the supervisor should run the component self-test and a clean smoke using a new experiment ID, then verify cache rejection with changed source count/hash.

### Real extraction-only decision

**Not safe to run yet.** The computation likely executes, but it would extract from the wrong negative instruction and would omit the required per-benchmark-position eligibility diagnostic. Cache/source identity also remains insufficient if the Modal experiment ID already exists.

**Merge verdict: BLOCK.** No P0 findings; the three P1 findings should be fixed before spending the real GPU extraction run.