# Task 450: deduplicated matched-persona J-lens extraction

Target: determine whether the v15 Qwen3.5-4B extraction from 65 unique rendered messages satisfies the recorded conditions for DEV calibration.

Provenance: pueue task 450, commit `366242c`, experiment `j-lens-persona-components-source-v15`, Qwen/Qwen3.5-4B BF16, layers 13–21. The complete cleaned task log is 68 lines at `slop/logs/20260907_j_lens_native/task450-full.log`. Downloaded vectors and metadata are under `outputs/experiments/j-lens-persona-components-source-v15/extraction/`.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| source identity | 65 distinct rendered messages; no split overlap | 65 IDs and 65 unique prompts per condition; deterministic 52 fit / 13 holdout | yes | `task450-extraction-summary.log` counts | no alternate source pool | fixes task 447 pseudoreplication |
| prompt construction | matched user text, fixed condition instructions and assistant suffix | sampled first/middle/last triples retain user text and token 271 suffix | yes | `task450-extraction-summary.log` samples | full prompt list is in metadata | input construction is checkable |
| GP16 extraction | finite non-negative 16-item reconstructions | finite GP norms at all nine layers | yes | `task450-full.log:40-48` | random-label reconstruction | algorithm executed |
| split stability | stable components across 26/26 fit halves | minimum cosine `.940` | yes | `task450-extraction-summary.log` | alternate seed | stable for this source ordering |
| sparse reconstruction | GP16 retains a meaningful J-space portion of the full persona residual | norm ratio `.198–.326`; full-to-GP cosine `.203–.319` | unclear | `task450-extraction-summary.log` | paper-task reference distribution | component is stable but captures a small, weakly aligned part of the residual |
| basis geometry | condition `<10`; absolute cosine `<.98` | maximum condition `2.312`; maximum absolute cosine `.685` | yes | summary `ranges` | none for stated criterion | coordinate basis is not near singular |
| held-out separation | both condition prompts favor their intended coordinate on unseen messages | `13/13` for both conditions at every layer; minimum mean margins `1.512` and `1.221` | yes | summary layer table | instruction paraphrase holdout | generalizes across messages, not instruction wording |
| DEV eligibility | both target orders change a nontrivial portion of attended tokens | minima `+C .525`, `-C .243`; maxima `.757/.475` | yes, asymmetric | summary layer table | realized intervention magnitudes | both directions can act before generation |
| saved vector validation | two vector files have distinct hashes, share a validated basis/dual, and are copied locally | hashes `bb0529...7191` and `123f56...`; 4.6 MB copied locally | yes | `task450-full.log:49-65`; metadata | second copy and reload | calibration can reuse the exact source |
| task completion | exit zero | pueue success; actual run 57 s after queue wait | yes | task status and complete log | GPU peak memory | wrapper repair worked |
| resolve condition | all preregistered extraction checks pass | all explicit thresholds pass; low GP/full alignment and instruction specificity remain caveats | yes with caveats | all above | causal behavior | authorize DEV calibration only |

## Chronology

The run loaded the exact 200-entry pool but deduplicated it before extraction. Metadata records:

> `"n_pairs": 65`
>
> `"source_fit_count": 52`
>
> `"source_holdout_count": 13`
>
> `"source_identity": "sha256(user_msg); duplicate rendered messages removed before seeded ordering"`

Source: `slop/logs/20260907_j_lens_native/task450-extraction-summary.log`.

The complete log then reports every requested layer. The weakest split-half result and widest basis are at different layers:

> `layer=16 ... split_gp_cosines=[0.9520993, 0.9403297] ... condition=1.661 ...`
>
> `layer=14 ... split_gp_cosines=[0.9474409, 0.9697465] ... component_cosine=0.6847 condition=2.312 ...`

Source: `slop/logs/20260907_j_lens_native/task450-full.log:41-43`.

Across all layers, the direct metadata reduction gives:

> `"split_min": 0.9403296709060669`
>
> `"component_abs_cos_max": 0.6846984028816223`
>
> `"condition_max": 2.3115217685699463`
>
> `"elig_plus_min": 0.5249744653701782`
>
> `"elig_minus_min": 0.24260957539081573`
>
> `"hold_plus_rate_min": 1.0`
>
> `"hold_minus_rate_min": 1.0`

Source: `slop/logs/20260907_j_lens_native/task450-extraction-summary.log`.

The main anomaly is reconstruction scale. GP16 norms are nonzero and split-stable, but `gp_to_full_norm_ratio` is only `.198–.326` and `full_to_gp_cosine` only `.203–.319`. This is not an algebraic contradiction: the non-negative sparse J dictionary cannot reproduce most of the full residual. It does mean that high split stability and perfect target ordering may describe a narrow instruction-correlated component rather than most of the validated prompted behavior.

I inspected condition triples at source indices 0, 32, and 64. The underlying messages are respectively about *The Great Gatsby*, a snack arithmetic story, and helping turtles. Positive, negative, and direct-accurate prompts retain the same source text and end at the same assistant-suffix token ID 271. The negative instruction is substantially longer and benchmark-specific; this remains an explicit adaptation and lexical/position confound.

The repaired Modal wrapper bounded metadata output, downloaded the complete experiment directory, and exited normally:

> `EXTRACTION_COMPLETE id=j-lens-persona-components-source-v15 ...`
>
> `✓ Finished downloading files to local!`
>
> `EXPERIMENT_EXTRACTION_DOWNLOADED output=/workspace/2026/jspace/j-steer_pub/outputs/experiments/j-lens-persona-components-source-v15`

Source: `slop/logs/20260907_j_lens_native/task450-full.log:49-65`.

## ML-debug form

| row | answer |
|---|---|
| log length; config | 68 cleaned lines. Qwen3.5-4B BF16; GP16; 65 unique messages; 52 fit, 13 holdout; layers 13–21; extraction-only. |
| `SHOULD:` lines | None emitted. The pueue resolve condition is checked in the stage table and all explicit numeric clauses pass. |
| numbers and null | No behavioral random-direction null exists at extraction. Thresholds were preregistered engineering checks. Existing random-direction behavior is used only after judging. |
| before intervention | Baseline held-out coordinates are not consistently centered; baseline favors the positive ordering on `.385–1.0` depending on layer. |
| dummy/control | Direct-accurate baseline subtraction is present. Shuffled labels, paraphrased instructions, and random GP16 controls are absent. |
| baseline model | Each held-out positive/negative source condition is compared with its matched direct-accurate source state. Both intended orderings are 13/13 on every layer. |
| schedule | No optimization schedule. GP uses exactly 16 non-negative pursuit steps. |
| full sample | First, middle, and last complete condition prompts and token-record summaries are in `task450-extraction-summary.log`. |
| worst step | Layer 16 negative split cosine is `.940`; layer 13 full-to-GP cosine is near `.20`. No loss/grad metric applies. |
| surprises | `full_to_gp_cosine=.203–.319`: explained as sparse constrained reconstruction, but causal sufficiency is unresolved. Queue wall time was 34 minutes while task runtime was 57 seconds: explained by waiting behind tasks 448/449. |
| absent evidence | DEV generation coherence, dose response, judge signs, off-axis damage, instruction-paraphrase stability, model revision, all-100 replication. |
| diagnoses | stable but narrow causal component 55%; lexical/instruction component 45%; intervention implementation bug 5%; artifact mismatch 3%; unknown 10%. |
| fresh review | `slop/reviews/20260907_task450_persona_component_extraction.md` independently verified the unique split, geometry, vectors, and diagnostics; verdict: proceed to fixed non-negative DEV calibration. |
| cheapest discriminator | Run fixed non-negative DEV calibration and inspect both raw text and realized patch/logit metrics. Correct signed judge movement distinguishes causal behavior from latent-only separation. |
| wall-clock/GPU | Queue elapsed about 34 minutes; pueue task runtime 57 seconds; extraction metadata 13.95 seconds. GPU peak memory was not logged. |

## Hypotheses

### H1 [method | Chances a little better than even | 55%]

- **Mechanism:** GP16 isolates a small but stable causal part of each instruction-induced residual, and target ordering transfers it to DEV behavior.
- **Evidence:** minimum split cosine `.940`, intended held-out ordering `13/13` at every layer, and both DEV orders are numerically eligible.
- **Contrary evidence:** full-to-GP cosine is only `.203–.319`; previous phrase-derived components separated latently but moved behavior in the wrong direction.
- **Discriminating test:** coherent DEV judge effects should move in the preregistered directions across doses and scenarios.
- **Fix/action:** run DEV calibration without changing vectors, layers, prompts, or sign definitions.
- **Interpretability:** partial until judged behavior exists.

### H2 [method | Unlikely | 45%]

- **Mechanism:** the stable components encode the exact condition instructions, their length, or discourse framing rather than transferable sycophancy/candid correction.
- **Evidence:** condition wording is fixed across fit and holdout; the negative instruction is 42 tokens longer than the positive instruction and contains benchmark-specific nonexistence language.
- **Contrary evidence:** source user messages are distinct, direct prompt controls changed benchmark behavior broadly, and no exact source message duplicates DEV.
- **Discriminating test:** DEV may show null, wrong-sign, or mostly off-axis style effects despite strong source separation. A later paraphrased-instruction extraction separates semantics from wording.
- **Fix/action:** label the current DEV run exploratory; do not publish without all-100 confirmation and a defensible source-control interpretation.
- **Interpretability:** yes for this exact instruction-derived adaptation, not a general persona axis.

### H3 [measurement | Highly Unlikely | 20%]

- **Mechanism:** aggregate eligibility hides weak behaviorally relevant patches, especially for `-C`.
- **Evidence:** `-C` eligibility is lower on every layer and reaches `.243`.
- **Contrary evidence:** every layer remains active and calibration records realized patch norm, coordinate residual, final-token KL, and changed outputs.
- **Discriminating test:** inspect those measurements by dose; a near-zero patch/KL with null behavior supports this hypothesis.
- **Fix/action:** calibrate directions independently and do not assume equal effective dose.
- **Interpretability:** partial for a weak direction.

### H4 [harness | Remote | 5%]

- **Mechanism:** coordinate application or cache reuse differs from extraction metadata.
- **Evidence:** no real-Qwen intervention was run in task 450.
- **Contrary evidence:** v15 end-to-end smoke changed distinct logits, restored clean logits, rejected stale cache identities, and passed export; vector hashes and common basis/dual are persisted.
- **Discriminating test:** calibration reload plus realized coordinate-exchange residuals should pass under BF16.
- **Fix/action:** no code change unless those diagnostics fail.
- **Interpretability:** yes for extraction.

### H5 [harness | Remote | 10%]

- **Mechanism:** long-term cache reuse could load a changed model because metadata records `model_revision: null`.
- **Evidence:** task-450 identity output explicitly records null model and tokenizer revisions.
- **Contrary evidence:** tokenizer behavior, exact prompts, source identities, implementation, lens, and vectors are content-hashed; immediate calibration uses the same pinned Modal cache state.
- **Discriminating test:** resolve and persist the HF model commit before publication/all-100 reuse.
- **Fix/action:** add model revision provenance before publication-grade reuse if Transformers continues to omit it.
- **Interpretability:** yes for immediate DEV calibration; weaker for later reproduction.

## Decision

1. **Resolve-condition verdict: met.** The 52/13 unique split has minimum split cosine `.940`, 13/13 held-out intended ordering on every layer, maximum condition `2.312`, maximum absolute component cosine `.685`, and eligibility minima `.525/.243`; artifacts downloaded locally.
2. **Prediction check:** deduplication—supported; split stability—supported; held-out separation—supported; well-conditioned basis—supported; two active DEV directions—supported but asymmetric; causal behavior—unresolved.
3. **Earliest unsupported link:** ordering these coordinates at attended DEV positions must produce the intended behavioral changes. Raw coherent outputs and blinded judge effects provide the next evidence.
4. **Validity:** invalid means repeated inputs cross partitions, tensors are malformed, or metrics come from another source/configuration. Estimated `P(extraction result is invalid)=5%`. Classification: credible positive extraction result, not behavioral evidence.
5. **Highest-information clues:** (1) exact uniqueness counts are 65/65/65 with 65 distinct source IDs; (2) all held-out intended orderings are 13/13; (3) low GP/full alignment shows the sparse component is much narrower than the full prompted behavior.
6. **Missing metrics:** DEV judge/coherence; instruction-paraphrase stability; shuffled/random null; resolved model revision; all-100 replication.
7. **Bugs requiring code changes:** rename tautological `reconstruction_error` to `decomposition_closure_error` after this experiment so the implementation hash remains fixed during calibration. Model revision provenance remains needed before long-term/public reuse.
8. **Misconceptions requiring reinterpretation:** perfect held-out ordering validates repeated instruction separation across messages, not a general candor/sycophancy representation or causal control.
9. **What would change the verdict:** source overlap or vector inconsistency would block calibration; wrong-sign, random-region, or incoherent DEV outcomes would reject this extraction for the public result.
10. **Recommended sequence:** run fixed non-negative DEV calibration from the exact saved vector hashes. Do not add source paraphrases, change layers, or alter the operator in the same run.

— PI/OpenAI Codex
