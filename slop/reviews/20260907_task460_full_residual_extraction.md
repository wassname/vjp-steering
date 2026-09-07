## Review

### Correct

- **The saved vectors are full-residual, not GP16.**
  - Extraction constructs each signal as the fit-set mean of `condition - baseline`, then selects the complete `signal` when `projection == "full_residual"` and independently unit-normalizes it (`src/vjp_steering/j_lens_concept.py:641-697`).
  - GP16 is still computed, but only for diagnostics and comparison.
  - The saved-artifact check reports: `FULL_RESIDUAL_BASIS_CHECK_PASS projection=full_residual differs_from_gp=true exact_unit_full_signals=true` (`slop/logs/20260907_j_lens_full_residual/v16-basis-check.log:1`).
  - This distinction is material: across the 18 layer/direction components, GP16 has only `0.1984–0.3263` of the full-signal norm and cosine only `0.2028–0.3191` with it (`metadata.json:36014-36017`, continuing through `metadata.json:136834-136837`).
  - Both safetensor headers contain F32 `[2,2560]` bases and duals at layers 13–21. The `+C` target indices are 0 and the `-C` indices are 1; their basis/dual payloads are shared. This matches `validate_component_pair`, which requires exact equality between directions and verifies the dual/rank relationship (`src/vjp_steering/j_lens_concept.py:219-243`).

- **Nonzero and split-half stability criteria pass strongly.**
  - Raw positive/negative full-signal norms by layer are:

    | Layer | Positive | Negative | Split cosines (+/−) |
    |---|---:|---:|---:|
    | 13 | 5.1463 | 4.2525 | 0.98368 / 0.98079 |
    | 14 | 5.2652 | 4.1764 | 0.98390 / 0.97853 |
    | 15 | 7.2257 | 5.8152 | 0.98751 / 0.98308 |
    | 16 | 8.4320 | 6.6073 | 0.98734 / 0.98198 |
    | 17 | 9.0228 | 7.2937 | 0.98720 / 0.98340 |
    | 18 | 9.5639 | 8.5524 | 0.98304 / 0.98391 |
    | 19 | 10.9786 | 10.1666 | 0.97349 / 0.97304 |
    | 20 | 12.1067 | 11.1954 | 0.97175 / 0.97146 |
    | 21 | 13.7782 | 13.2569 | 0.97180 / 0.96901 |

    Evidence: `task460-extraction-summary.tsv:2-10` and extraction log lines 40–48.

- **Every layer is rank two and numerically well-conditioned.**
  - Condition numbers for layers 13–21 are `1.7531, 1.8819, 1.5269, 1.3683, 1.3019, 1.2212, 1.2174, 1.1678, 1.1573`.
  - The worst smallest singular value is still `0.663597` at layer 14; the full range of condition numbers is only `1.157–1.882` (`metadata.json:46477-46483`, `58429-58435`, continuing through `142066-142072`).

- **Held-out fixed-instruction separation passes completely.**
  - The split is deterministic: first 52 sources fit, last 13 held out, with 26/26 fit halves (`src/vjp_steering/j_lens_concept.py:625-634`).
  - All nine layers order all 13 positive held-outs as coordinate 0 > 1 and all 13 negative held-outs as coordinate 1 > 0: **13/13 in both directions at every layer**, or 234/234 layer/source/direction checks (`task460-extraction-summary.tsv:2-10`).
  - Held-out means are strongly separated. For example:
    - Layer 13: positive `[4.0574, -0.4992]`, negative `[-1.0265, 3.6704]` (`metadata.json:46648-46660`).
    - Layer 21: positive `[10.0524, -1.4811]`, negative `[-3.3211, 11.4785]` (`metadata.json:142237-142249`).

- **Sources match v15.**
  - There are the same 65 unique source IDs, same rendered prompts, same assistant suffix, and the same 52/13 split (`task460-extraction-summary.tsv:11`; v16 `metadata.json:302-327`; v15 `metadata.json:301-326`).
  - Corresponding full-signal and GP hashes also match v15 exactly, independently confirming the same model activations and source split.
  - The v16 source SHA (`f9391d…`) differs from v15 (`fe7dad…`) only because the source digest intentionally includes the projection-specific spec digest (`src/vjp_steering/j_lens_concept.py:59-82,601-603`). This prevents a v15 GP16 cache collision rather than indicating changed prompts.

- **No silent GP16/operator cache collision was observed.**
  - Metadata identifies:
    - operator `matched-persona-prefill-full-residual-target-ordered-coordinate-exchange-control-v16`
    - representation `matched_persona_prefill_full_residual_components`
    - projection `full_residual`
    - spec SHA `7b702b…`
  - Cache loading verifies representation, operator, spec, implementation hash, source identity, vector configuration, logical vector hashes, and component-pair validity (`scripts/experiment.py:392-415,455-486`).
  - The extraction log contains fresh per-layer extraction messages before `EXTRACTION_COMPLETE`, so this run did not silently return an existing cache (`task-full-residual-source-v16.log:40-49`).
  - Logical vector hashes consistently agree:
    - `+C`: `1cb043932c0ddd676d1953ef5368fe9744f6878ed002f6c46cb730d9df4cc401`
    - `-C`: `313bf2a731baf804129cf4036d1321abe915b1abbb6e59870901c658779ce3a5`
    (`metadata.json:10-15`; summary line 12).

### Findings

- **Finding: P1 — The per-layer DEV eligibility is too asymmetric to demonstrate the stated “nontrivial” criterion for both directions.**
  - Exact bare-DEV eligibility over 981 attended positions per layer:

    | Layer | +C eligible | −C eligible |
    |---|---:|---:|
    | 13 | 549 (55.96%) | 432 (44.04%) |
    | 14 | 146 (14.88%) | 835 (85.12%) |
    | 15 | 915 (93.27%) | 66 (6.73%) |
    | 16 | 954 (97.25%) | 27 (2.75%) |
    | 17 | 954 (97.25%) | 27 (2.75%) |
    | 18 | 214 (21.81%) | 767 (78.19%) |
    | 19 | 979 (99.80%) | 2 (0.20%) |
    | 20 | 980 (99.90%) | 1 (0.10%) |
    | 21 | 966 (98.47%) | 15 (1.53%) |

    Evidence: `metadata.json:46728-46738`, `58680-58690`, continuing through `142317-142327`; also `task460-extraction-summary.tsv:2-10`.
  - Aggregated over layer-position pairs, eligibility is 6,657 versus 2,172 of 8,829, approximately 75.4% versus 24.6%. Thus `-C` is globally nonzero, but at layers 19–20 it is effectively identity on the bare DEV prompts.
  - This matters because target ordering is conditional: if the requested target coordinate is already larger, `component_target_coordinates` returns the existing order and the patch is zero (`src/vjp_steering/j_lens_concept.py:211-217,246-255`). Layer 20 therefore has a bare eligibility imbalance of **980:1**.
  - Neither the task nor code defines a numerical threshold for “nontrivial”; extraction only records eligibility and does not reject near-zero fractions (`src/vjp_steering/j_lens_concept.py:706-747`). Under an all-extracted-layers interpretation, 1/981 cannot substantiate that criterion.
  - Smallest resolution: predeclare an eligibility floor and permitted layer-selection rule before calibration, then either restrict to qualifying layers or redesign the source/operator. Do not post-hoc treat “nonzero” as equivalent to “nontrivial.”

- **Finding: P2 — Model revision provenance leaves a future stale-cache path.**
  - `model_revision` and `tokenizer_revision` are both `null`; only the tokenizer content and J-lens are content-addressed (`metadata.json:311-313,36006-36008`).
  - Model loading uses mutable name `Qwen/Qwen3.5-4B` without an explicit revision (`scripts/experiment.py:178-188`). Cache validation compares the recorded and newly loaded revision values, but `null == null` would not detect changed upstream weights (`scripts/experiment.py:275-299,455-470`).
  - Current-run evidence is reassuring: v16’s full and GP signal hashes exactly match v15, and implementation hash `ff42a271…` matches the current self-test record. This is therefore a reproducibility/cache risk, not evidence that task460 actually used wrong weights.
  - Smallest fix before relying on this beyond the diagnostic: pin and record the resolved model commit or model-weight content hash. A fresh `--verify-extraction` rerun would also strengthen the record; no `verification.json` is present.

### Resolve condition

Task460 passed the full-residual identity, nonzero, split-half stability, rank, conditioning, source matching, and complete held-out separation requirements. It **did not demonstrate the complete resolve condition conservatively**, because “nontrivial” eligibility is undefined and one direction falls to 2/981, 1/981, and 15/981 at layers 19–21.

This remains a **non-J diagnostic control**, exactly as metadata states, and is not paper-native evidence (`metadata.json:327-339`).

### Merge/calibration verdict

**BLOCK calibration** until a predeclared eligibility threshold and layer policy resolve the severe direction/layer asymmetry. The extraction artifact itself is internally coherent and correctly represents full residuals; the block concerns authorization of the next calibration stage, not artifact corruption.
— PI reviewer/OpenAI GPT-5.6 Sol
