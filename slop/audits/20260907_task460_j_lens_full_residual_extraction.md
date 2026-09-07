# Task 460: full matched-residual extraction

— PI/OpenAI Codex

Target: test whether GP16 removed transferable behavior by replacing each sparse reconstruction with its complete matched condition-minus-baseline residual. This is a non-J control. It is not evidence that the paper tested sycophancy.

Task 460 ran commit `e9877a2` from `/workspace/2026/jspace/j-steer_pub`. Pueue records status `Success`, start `2026-09-07 12:29:06 AWST`, end `12:30:01`, and this command:

> `uv run modal run scripts/run_modal.py::extract_experiment --method j_lens_concept_components --experiment-id j-lens-persona-full-components-source-v16 --j-lens-source persona_components --persona-direction full_residual`

Its resolve condition was:

> `calibrate only if both full-residual basis vectors are nonzero, split-half stable, rank-2 and well-conditioned, separate all 13 held-out fixed-instruction sources in their fixed target order, and have nontrivial DEV target-order eligibility`

## Stage audit

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| source identity | same 65 messages, prompts, 52/13 split, and suffix as v15 | IDs, rendered prompts, split counts, and suffix match v15 exactly | yes | `task460-extraction-summary.tsv` | instruction paraphrase | only the projection changed |
| full residual | nonzero positive and negative condition-minus-baseline means | norms grow from `5.15/4.25` at layer 13 to `13.78/13.26` at layer 21 | yes | task 460 lines 43–51 | random-label residual norm | neither basis row is a numerical zero |
| stability | independent fit halves align | minimum full-residual split cosine is `.9690` | yes | `task460-extraction-summary.tsv` | alternate source seed | stable over this source split only |
| basis geometry | rank 2 and moderate condition number | component cosine `.145–.560`; condition `1.157–1.882`; saved rows equal normalized full residuals and share a dual with `basis @ dual.T ≈ I` | yes | task 460 lines 43–51; `task460-vector-check.log` | none | no near-singular or wrong-basis failure is indicated |
| held-out source separation | each fixed instruction has its target coordinate larger on 13 unseen messages | 13/13 in both directions at all nine layers | yes | `task460-extraction-summary.tsv` | paraphrased instructions | fixed wording generalizes across source messages |
| DEV eligibility | both targets have positions where target ordering changes coordinates | aggregate `+C 6657/8829`, `-C 2172/8829` | yes, asymmetric | aggregate summary lines | realized logit effect | both targets execute somewhere, but not equally |
| final prefill position | measure direct final-position eligibility | `+C 135/135`, `-C 0/135` across layers and prompts | no symmetric effect | aggregate summary lines | generation response | `-C` can affect the final state only through patched earlier positions and later attention |
| saved files | metadata and two vectors downloaded | metadata 3.99 MB; each vector 371 KB | yes | task 460 lines 52–66 | resolved HF revision | calibration can reload the exact files |

## Complete evidence

The complete task log has 68 lines: [`task-full-residual-source-v16.log`](../logs/20260907_j_lens_full_residual/task-full-residual-source-v16.log). The first line, `-o: 3: eval: Syntax error: "(" unexpected`, is emitted by the `sh -lc` startup environment; Modal then completed and pueue returned success. Future commands should use `bash -lc` to avoid this unrelated shell startup error.

The extraction lines report:

> `layer=13 projection=full_residual basis_norms=[5.146275997161865, 4.2525224685668945] split_basis_cosines=[0.9836761951446533, 0.9807884693145752] component_cosine=0.5090 condition=1.753 eligibility_plus=0.560 eligibility_minus=0.440`

> `layer=20 projection=full_residual basis_norms=[12.106684684753418, 11.195371627807617] split_basis_cosines=[0.9717494249343872, 0.9714564085006714] component_cosine=0.1539 condition=1.168 eligibility_plus=0.999 eligibility_minus=0.001`

> `EXTRACTION_COMPLETE id=j-lens-persona-full-components-source-v16 hash_plus=1cb043932c0ddd676d1953ef5368fe9744f6878ed002f6c46cb730d9df4cc401`

Saved identities:

- `+C`: `1cb043932c0ddd676d1953ef5368fe9744f6878ed002f6c46cb730d9df4cc401`
- `-C`: `313bf2a731baf804129cf4036d1321abe915b1abbb6e59870901c658779ce3a5`
- source: `f9391d9b58dec7a97f5bbafda4a95b26bfb80a898e9065456a0b88ef1949a839`
- lens: `1f9a8f8fd593f0ffec1a9640993257ca4560f8ae3e5602315643d5cc6818534e`

## ML-debug form

| row | answer |
|---|---|
| log length and config | 68 lines; Qwen3.5-4B BF16, layers 13–21, 65 unique sources, 52 fit, 13 held out, full residual |
| `SHOULD:` lines | none |
| null scale | random high-dimensional split cosine is near zero; held-out target-order chance is 6.5/13. No shuffled-label extraction was run. DEV eligibility is complementary by construction and is not a performance metric |
| initial state | there is no optimizer. Matched prompts and suffixes are identical to v15 |
| simple baseline | v15 GP16 retained only 20–33% of full residual norm and then failed DEV semantics. This run changes only the selected basis signal |
| held-out | both conditions score 13/13 target ordering on held-out messages at every layer; this does not test instruction paraphrases |
| schedule | not applicable |
| complete sample | metadata stores every rendered prompt and token record; summary verifies source prompt identity against v15 |
| worst observation | `-C` final-position eligibility is 0/135; late-layer all-position eligibility falls to .001–.015 |
| surprise | full residual reverses the layerwise eligibility pattern compared with a balanced expectation: aggregate +C is .754 and -C .246 |
| missing evidence | actual calibration patches, logit KL, coherent generations, judged intended signs, shuffled labels, alternate source wording, HF revision |
| diagnoses | H1–H5 below |
| fresh review | reviewer blocked because “nontrivial” had no per-layer threshold; oracle recommends all nine layers because layer selection would confound the GP16/full-residual comparison |
| cheapest discriminator | run the unchanged DEV alpha grid. A weak `-C` logit effect with strong `+C` implicates target-order eligibility; broad correct effects implicate GP16 information loss |
| runtime | Modal extraction reports 13.84 s after model load; pueue elapsed 55 s |

## Hypotheses

### H1 [method | Likely | 65%]

- **Mechanism:** GP16 discarded behavior carried by the complete residual.
- **Evidence:** v15 retained only 20–33% of residual norm; task 460 now stores nonzero stable complete residuals.
- **Contrary evidence:** stable fixed-instruction separation can reflect wording rather than behavior.
- **Discriminating test:** unchanged DEV calibration. Broad intended-sign medians support H1; another null or wrong-sign result rejects it.
- **Action:** run the fixed grid without layer selection or relabeling.
- **Interpretability:** partial until judged behavior exists.

### H2 [method | Likely | 60%]

- **Mechanism:** a mean final-prefill instruction residual does not transfer behavior to unrelated benchmark prompts.
- **Evidence:** direct instructions produced `+3.10/-6.37`, while v15 target ordering failed despite perfect held-out source separation.
- **Contrary evidence:** v15 used only the sparse GP16 fraction; the complete residual remains untested behaviorally.
- **Discriminating test:** full-residual DEV judge.
- **Action:** stop this matched-source design if both fixed directions remain wrong-sign or have zero median.
- **Interpretability:** yes as a test of this specific source/operator combination.

### H3 [measurement | Highly Likely | 80%]

- **Mechanism:** asymmetric eligibility makes `-C` much weaker than `+C`, independently of semantic vector quality.
- **Evidence:** `+C 6657/8829` versus `-C 2172/8829`; final positions are `135/135` versus `0/135`.
- **Contrary evidence:** earlier-token patches can influence later final positions through subsequent attention layers.
- **Discriminating test:** compare per-side realized patch norms, final-logit norm, KL, and output changes at each alpha.
- **Action:** calibrate directions independently but retain the same alpha grid for the first comparison.
- **Interpretability:** yes for effective intervention strength; partial for semantics.

### H4 [harness | Remote | 10%]

- **Mechanism:** judge sign or answer-key pairing could hide a real semantic effect.
- **Evidence:** DEV has one AB pass.
- **Contrary evidence:** direct controls passed with the same judge, and answer-key text is now bound to cohort and cache identities.
- **Discriminating test:** inspect all raw responses before judging, then compare median and sign counts with judge output.
- **Action:** do not use the mean alone.
- **Interpretability:** partial.

### H5 [bug | Remote | 5%]

- **Mechanism:** saved vectors could differ from the full residual basis or cache under the GP16 identity.
- **Evidence:** this is the main silent implementation failure that could mimic a negative result.
- **Contrary evidence:** both the tiny check and [`task460-vector-check.log`](../logs/20260907_j_lens_full_residual/task460-vector-check.log) pass; real saved rows equal normalized full residuals, differ from GP16, share a valid dual, and use target indices 0/1.
- **Discriminating test:** calibration reload validation plus real-artifact basis comparison.
- **Action:** fail before generation on any identity mismatch.
- **Interpretability:** yes if reload passes.

## Decision

1. **Resolve-condition verdict:** not judgeable as written because “nontrivial” had no numerical or per-layer definition. The measured aggregate is substantial (`-C 2172/8829`), but some late layers approach identity and `-C` has 0/135 bare final-position eligibility. This uncertainty motivates measurement rather than layer selection.
2. **Prediction check:** stable/nonzero, rank-2, held-out separation, and aggregate all-position eligibility predictions are supported. Equivalent effective strength is contradicted by 0/135 final-position eligibility for `-C`.
3. **Earliest unsupported link:** complete residual target ordering must cause the instructed benchmark behavior. DEV generations and blinded scores test it.
4. **Validity:** invalid means the files do not represent the declared complete residuals or the reported geometry is contaminated. Estimated `P(invalid)=8%`; credible positive extraction, no behavioral result.
5. **Highest-information clues:** 13/13 held-out separation; minimum split cosine .969; zero `-C` final-position eligibility.
6. **Missing metrics:** realized per-side patch/logit magnitude; judged median and sign breadth; shuffled or paraphrased source control; resolved HF revision.
7. **Code changes:** none required before calibration; use `bash -lc` for future pueue commands.
8. **Reinterpretation:** held-out instruction separation does not establish sycophancy or candid correction; eligibility does not establish efficacy.
9. **What changes the verdict:** a reload/hash mismatch blocks calibration; no nonzero `-C` model response despite increasing alpha would show that nominal all-position eligibility is ineffective.
10. **Recommended sequence:** run the unchanged all-nine-layer DEV calibration, recording treated-forward eligibility and changed-position counts at each layer and dose; inspect every response; judge only if both targets are coherent and numerically active. If `-C` is underexposed relative to v15, make one non-negative dose extension rather than selecting layers. Do not run all-100 or edit the public plot before broad two-sided judged effects.

The independent reviewer’s conservative verdict is [`20260907_task460_full_residual_extraction.md`](../reviews/20260907_task460_full_residual_extraction.md). The oracle’s attribution-preserving decision is [`20260907_task460_eligibility_oracle.md`](../reviews/20260907_task460_eligibility_oracle.md).
