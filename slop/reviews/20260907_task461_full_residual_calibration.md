## Review

### Correct

- **Calibration completed cleanly.** The complete Modal log reaches `CONCEPT_CALIBRATION_COMPLETE ... cells=16`, downloads the artifact, and exits successfully with no runtime error (`slop/logs/20260907_j_lens_full_residual/task-full-residual-calibration-v16.log`).
- **240 generations verified:** 2 directions × 8 doses × 15 prompts. `calibration.json` contains 16 observations, each with `answers: 15` (`calibration.json:40,123954,...,1858752`), and both output directories contain all eight JSONL files.
- **Zero-dose identity verified.**
  - Both zero-dose observations have exactly zero logit delta and KL (`calibration.json:123910-123911,1115224-1115225`).
  - The calibration code enforces bit-exact zero-dose logits with `rtol=0, atol=0` (`scripts/concept_checks.py:147-148`).
  - The response comparison reports `ZERO_TEXT_DIFFERENCES 0` (`task461-calibration-summary.tsv:18`).
- **Health passes in all cells.** All 16 observations have 15 answers and empty breakdown reasons (`calibration.json:40-47` and corresponding entries through `1858752-1858759`). Independent inspection of all 240 displayed responses found:
  - no incoherence, unfinished answers, role leakage, refusals, or within-response loops;
  - no high-dose repetitive-garbage collapse;
  - all outputs remain grammatical, responsive, and bounded in length.
- **Hook execution is correct.** Every observation records exactly one call for each layer 13–21 (`calibration.json:123899-123907` and 15 corresponding blocks through `1982611-1982619`). The code asserts this and removes hooks in `finally` (`scripts/concept_checks.py:135-146`); the hook is also self-removing after its first forward (`src/vjp_steering/j_lens_concept.py:263-285`).
- **Layer and position accounting is internally consistent.**
  - Nine treated layers, 13–21, are recorded (`extraction/metadata.json:319-328`).
  - Each layer sees 981 attended positions and 15 final positions, hence 8,829 and 135 aggregate opportunities.
  - Initial per-layer +C eligibility is `[549,146,915,954,954,214,979,980,966]`; -C is the complementary `[432,835,66,27,27,767,2,1,15]`.
  - At every nonzero layer/dose, changed positions equal treated-forward eligible positions, including final positions. At zero, eligible positions correctly remain diagnostic-only while changed counts are zero. The aggregate dose totals confirm this invariant (`task461-calibration-summary.tsv:2-17`); eligibility and change definitions are adjacent in `scripts/concept_checks.py:102-130`.
  - Aggregate final-position changes are +C `134,114,83,49,32,30,30` over increasing nonzero doses, and -C `0` at every dose (`task461-calibration-summary.tsv:3-9,11-17`). The -C effect therefore propagates from earlier attended positions rather than direct final-position patches; this is consistent with the all-prefill intervention, not a failed hook.
- **BF16 and coordinate realization are healthy.**
  - All recorded layer outputs are `torch.bfloat16` (for example `calibration.json:13808` and the corresponding entries throughout).
  - Coordinates and deltas are computed in float32 before the delta is cast into the hidden dtype (`src/vjp_steering/j_lens_concept.py:248-257`).
  - On active positions, absolute coordinate residual p95 stays at or below approximately `0.00504` for +C and `0.00386` for -C. Relative p95 decreases to `0.0278` and `0.00679` respectively at alpha 2; the larger -C alpha-0.25 relative p95 (`0.2346`) accompanies only a `0.00386` absolute residual and very small requested exchanges (`task461-active-residual-summary.tsv:2-17`).
- **Numerical exposure is monotonic and sufficient in both directions.**
  - +C alpha 2: logit norm `578.243`, KL `1.72170`, 15/15 outputs changed.
  - -C alpha 2: logit norm `144.471`, KL `0.061076`, 12/15 outputs changed.
  - Against v15 GP16, +C is about 2.52× in logit norm and 6.15× in KL; -C is about 1.90× and 3.50×, with 12 rather than 10 changed outputs. Thus -C exposure is **above**, not below, the preregistered v15 comparator.
- **Hash/source chain is internally consistent.**
  - Calibration names source `j-lens-persona-full-components-source-v16` and records source-metadata SHA `aa054e...321d`.
  - The copied extraction metadata records the same source and digest (`extraction/metadata.json:143554-143555`).
  - Source, calibration, and manifest agree on vector hashes `1cb043...c401` and `313bf2...3a5` (`manifest.json:1734251-1734259`).
  - The recorded implementation hash `ff42a2...b62a` matches the contemporaneous self-test (`v16-self-test.log:1`), and the operator/source labels explicitly identify the v16 full-residual control (`src/vjp_steering/j_lens_concept.py:27-28`).
  - The source additionally records prompt/source, spec, tokenizer-content, and lens hashes; the lens hash is `1f9a8f...534e` (`extraction/metadata.json:36006-36008`).

### Response audit: visible patterns, without scoring

- **+C:** increasingly forceful/granular language is visible in legal and financial answers. Some fabricated-method endorsement appears at higher doses—for example, positive claims about “Convergent Schema Normalization” at `task461-plus-responses.md:163,349,411,473`. This is not universal: the Drexler–Nussbaum item is explicitly corrected at every dose (`task461-plus-responses.md:59,121,...,493`). Several prompts plateau or repeat nearly identical answers across adjacent high doses despite continued numerical growth.
- **-C:** responses are more stable across the grid and repeatedly reject Convergent Schema Normalization (`task461-minus-responses.md:39,101,...,473`). Higher doses introduce firmer wording such as “must first standardize” (`task461-minus-responses.md:321,383,445`). However, -C still accepts several other fabricated premises, so it is not visibly a universal candor switch. This semantic sparsity is exactly what blinded judging should measure rather than a reason to extend dose after the numerical gate has passed.
- Cross-dose reuse/plateau is present in both directions, especially -C, but there is no pathological saturation, repetition loop, or coherence breakdown.

### Findings

- **Finding: P2 — misleading calibration-level pair count.** `manifest.json:16` reports `config.n_pairs: 200`, while the embedded extraction correctly reports `n_pairs: 65` (`manifest.json:1734249`) and `source_unique_count: 65` (`manifest.json:1734559`). This comes from serializing the calibration CLI value rather than reused extraction metadata (`scripts/concept_checks.py:224-230`). Smallest fix: omit `config.n_pairs` for reused calibration or populate it from extraction metadata. It does not invalidate these generations because the extraction block and hashes identify the actual 65-source vectors.
- **Finding: P2 — model revision provenance is nullable.** Both `model_revision` and `tokenizer_revision` are null (`extraction/metadata.json:311-313`) because the code accepts missing `_commit_hash` values (`src/vjp_steering/j_lens_concept.py:793-799`). Tokenizer content and resulting vector hashes are preserved, but immutable model-weight identity is not independently recorded. Smallest fix for future runs: require a resolved HF commit or model artifact hash.

### Resolved verdict

**PASS the preregistered calibration gate. Judge now; do not extend either direction.** Both fixed targets are coherent and numerically active, +C is substantially larger as expected, and -C alpha-2 exposure exceeds the v15 GP16 comparator on logit norm, KL, and changed-output count. Extending only -C would contradict the stated “extend only if below v15” rule.

This remains a **non-J diagnostic control** and should not be presented as paper-native evidence.

### Merge verdict

**OK with notes.** The two P2 provenance/metadata issues should be cleaned up for future reproducibility but do not block blinded DEV judging of the completed task-461 artifacts.
— PI reviewer/OpenAI GPT-5.6 Sol
