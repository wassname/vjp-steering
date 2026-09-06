# Fresh independent audit: task 447 persona-component extraction

## Review

### Scope and provenance

- The paths named in the request are not present in the current checkout:
  - `docs/plans/2026-09-06-j-lens-persona-component-extraction.md`
  - `outputs/logs/persona-component-extraction.log`
  - `outputs/experiments/j-lens-persona-components-candid-correction-v1/`
- Task 447 actually records experiment ID `j-lens-persona-components-source-v13`; its retained evidence is:
  - `slop/logs/20260907_j_lens_native/task447-selected.log`
  - `slop/logs/20260907_j_lens_native/task447-extraction-summary.log`
  - `slop/logs/20260907_j_lens_native/task447-source-samples.log`
  - `outputs/experiments/j-lens-persona-components-source-v13/extraction/`
- Consequently, this review applies to that task-447 artifact. A `candid-correction-v1` alias should not be treated as audited unless it matches:
  - source hash `5537c326...d6a`
  - `+C` hash `a3f76d9e...fd96`
  - `-C` hash `a7443aed...5f50`

### Correct

- The remote extraction itself completed successfully despite the pueue wrapper reporting exit 1. Modal emitted `EXTRACTION_COMPLETE` and `✓ App completed`; the failure came from a missing local `tee` directory (`task447-selected.log:1-24`).
- The artifact records Qwen3.5-4B, BF16, 200 entries, GP16, and layers 13–21, with distinct content hashes for both vector files (`outputs/experiments/j-lens-persona-components-source-v13/extraction/metadata.json:1-25`).
- Source triples are condition-aligned:
  - same underlying user text at each index;
  - positive, negative, and baseline differ only in their fixed instruction;
  - all sampled conditions end in the same seven-token non-thinking assistant suffix;
  - sampled indices 0, 100, and 199 all end at token ID 271 (`task447-source-samples.log:1-33`; metadata lines 839–846).
- The extraction implementation verifies each prompt’s full assistant suffix and each triple’s final token (`src/vjp_steering/j_lens_concept.py:580-601`).
- The vector pair is structurally consistent. Both directions use the same basis and dual; `+C` targets coordinate 0 and `-C` coordinate 1. This is checked before return, including numerical rank and `basis @ dual.T ≈ I` (`src/vjp_steering/j_lens_concept.py:211-235, 680-687, 753`).
- All preregistered numerical thresholds pass:

| layer | split + / - | component cosine | condition | held-out target order + / - | DEV eligibility + / - |
|---:|---:|---:|---:|---:|---:|
| 13 | .937 / .981 | .677 | 2.280 | 40/40 / 40/40 | .693 / .307 |
| 14 | .994 / .975 | .648 | 2.165 | 40/40 / 40/40 | .524 / .476 |
| 15 | .990 / .959 | .561 | 1.886 | 40/40 / 40/40 | .740 / .260 |
| 16 | .984 / .989 | .523 | 1.788 | 40/40 / 40/40 | .773 / .227 |
| 17 | .976 / .994 | .525 | 1.791 | 40/40 / 40/40 | .719 / .281 |
| 18 | .991 / .985 | .594 | 1.981 | 40/40 / 40/40 | .852 / .148 |
| 19 | .989 / .990 | .594 | 1.982 | 40/40 / 40/40 | .747 / .253 |
| 20 | .987 / .972 | .534 | 1.814 | 40/40 / 40/40 | .538 / .462 |
| 21 | .966 / .978 | .560 | 1.882 | 40/40 / 40/40 | .703 / .297 |

Source: `task447-extraction-summary.log:2-28`.

### Findings

- **Finding: P1 — the 200 “unique sources” contain only 123 unique rendered source messages, contaminating both the fit and held-out diagnostics.**
  - `source_ids` are hashes of the complete suffix entry (`scripts/experiment.py:229-233`), but extraction renders only `entry["user_msg"]` (`scripts/experiment.py:235-241`). Different suffix entries with the same user message therefore pass the unique-ID check while producing exactly identical model inputs.
  - Exact-content counting over the stored prompts gives:
    - 200 unique entry hashes;
    - only 123 unique rendered prompts per condition;
    - 101 unique messages among the 160 fit rows;
    - 34 unique messages among the 40 held-out rows;
    - 12 held-out messages also present in fit, leaving only 22 unique held-out-only messages.
  - `"Tell me a story."` alone appears 20 times per condition, including both fit and held-out positions (`metadata.json:233-425`, with corresponding negative and baseline repetitions at lines 435–829).
  - The repeated inputs produce exact repeated held-out coordinate rows; examples are visible throughout the layer-13 arrays (`metadata.json:96001-96480`).
  - The code splits by position, not by rendered-source identity (`src/vjp_steering/j_lens_concept.py:605-620`), so duplicate messages can cross both split halves and the fit/holdout boundary.
  - **Consequence:** the stated sample sizes and independence are wrong. The 40/40 held-out rates and split-half cosines are pseudoreplicated, although the 22 genuinely unseen unique held-out messages still provide some qualitative support.
  - **Smallest fix:** define source identity from normalized `user_msg` or the rendered prompt triple, reject duplicates, and group-split by that identity. The current pool cannot supply 200 distinct messages; either expand it to 200 unique sources or preregister a smaller unique sample and rerun extraction.

- **Finding: P1 — the exact requested artifact/provenance cannot currently be established.**
  - The requested `candid-correction-v1` directory and named log/plan are absent; task 447 identifies `source-v13`.
  - **Consequence:** this report cannot independently certify that a differently named artifact is byte-identical to task 447.
  - **Smallest fix:** restore the intended artifact or record that it is an alias, then verify the source and vector hashes listed above before calibration.

- **Finding: P2 — separation can reflect the fixed instruction wording and length rather than a general persona component.**
  - Every negative prompt contains benchmark-specific wording about nonexistent methods, frameworks, factors, thresholds, and fabricated methods (`metadata.json:21-23`).
  - The negative instruction is consistently 42 tokens longer than the positive instruction; the baseline is three tokens longer. Representative attended lengths are:
    - source 0: 28 / 70 / 31;
    - source 100: 62 / 104 / 65;
    - source 199: 49 / 91 / 52;
    for positive / negative / baseline respectively (`task447-source-samples.log`).
  - Thus the three token-length distributions are mechanically shifted versions of the same user-message distribution. No truncation occurred, and suffix alignment is correct, but lexical and positional effects are not controlled.
  - Held-out prompts repeat the same exact condition instructions, so perfect separation tests robustness to user-message variation, not transfer to paraphrased candid or sycophantic behavior.
  - No exact source-to-DEV prompt duplicate was identified, but the negative instruction is explicitly tailored to the benchmark’s fabricated-method failure mode.
  - **Smallest fix:** add a preregistered instruction-paraphrase or length-matched control. Do not infer a general candor axis from this extraction alone.

- **Finding: P2 — null/control coverage is incomplete.**
  - The direct-and-accurate baseline is a useful matched subtraction control.
  - Missing controls include shuffled condition labels, instruction paraphrases, an equal-length lexical control, an alternate source seed, and a random-GP extraction null.
  - Baseline coordinates are not neutral-centered: baseline favors the positive coordinate on 47.5%–100% of held-out rows depending on layer (`task447-extraction-summary.log:18-28`).
  - GP16 retains only 19.7%–32.4% of full residual norm. Stability is high, but the retained sparse component has not yet been shown to be causal.
  - **Smallest fix:** retain the current result as an exploratory extraction and add at least one shuffled/paraphrased source control before publication-grade interpretation.

- **Finding: P2 — reproducibility and directional asymmetry need to be carried into calibration.**
  - Both `model_revision` and `tokenizer_revision` are null, although tokenizer content, implementation, lens, source, and vectors are hashed (`metadata.json:15-29, 847-850`).
  - `-C` DEV eligibility falls to .148 at layer 18, versus .852 for `+C`; the two directions should not be assumed to have comparable effective doses.
  - **Smallest fix:** pin the resolved model revision and calibrate non-negative alpha independently for `+C` and `-C`. Do not post-hoc remove weak layers or relabel directions after seeing judge outcomes.

## Interpretation

### Highest-information clues

1. **Negative:** only 123 distinct rendered prompts exist, and 12 prompt identities leak across fit and held-out.
2. **Positive:** every numerical preregistration threshold passes by a wide margin—minimum split cosine .937, maximum condition 2.280, maximum absolute component cosine .677.
3. **Positive engineering evidence:** the two safetensors form a valid common basis/dual pair with opposite target indices and independently recorded hashes.

### Earliest unsupported link

The earliest broken link is not coordinate exchange itself; it is the assumption that 200 unique source IDs represent 200 distinct model inputs with an independent 40-source holdout. That assumption is contradicted.

After correcting that, the next unsupported link is semantic: the stable direction must represent sycophancy/candid correction rather than the exact instruction’s tokens, length, and benchmark-targeted wording. A deduplicated grouped split plus an instruction-paraphrase control would support this; correct-signed DEV behavior would then establish causal transfer.

### Validity estimate

- Probability of tensor corruption, prompt/suffix misalignment, or an invalid basis: **approximately 3%**.
- Probability that the current extraction is invalid for the intended *independent 200-source / 40-held-out calibration gate*: **approximately 65%**, driven by demonstrated duplicate-input leakage and the missing exact requested artifact provenance.
- Classification: **credible positive engineering extraction with a major inferential flaw; not calibration-ready as a confirmatory result.**

### What would change the verdict

A rerun would be calibration-ready if it records:

1. unique rendered-source count equal to the declared sample count;
2. zero rendered-message overlap between fit, split halves, and holdout;
3. the same preregistered stability, conditioning, cosine, held-out, and DEV-eligibility thresholds;
4. exact artifact/model/lens/source hashes;
5. preferably a paraphrase or shuffled-label null showing the result is not merely fixed instruction text.

## Calibration decision

**Do not proceed now with the planned confirmatory calibration.** Deduplication and re-extraction are cheaper and cleaner than interpreting a more expensive behavioral run built on a contaminated holdout.

If an immediate DEV calibration is run for diagnostic value, label it **exploratory and provisional**:

- freeze the existing vectors, layers 13–21, directions, and dose grid;
- calibrate `+C` and `-C` separately;
- inspect raw outputs, coherence, realized patch norms, and judge signs;
- do not tune prompts/layers based on those outcomes;
- do not use it to authorize public plots or claim a 200-source independent extraction.

**Merge verdict: BLOCK planned confirmatory calibration; exploratory diagnostic calibration only with the caveats above.**