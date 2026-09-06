# Task 447: matched-persona J-lens component extraction

Target: audit pueue task 447, which ran Qwen3.5-4B extraction for `j-lens-persona-components-source-v13`.

Provenance: task 447 executed commit `569e5a7` from `/workspace/2026/jspace/j-steer_pub`. The complete cleaned log has 196,061 lines and was read from `/home/code/.local/share/pueue/task_logs/447.log`. Selected verbatim lines and exact task metadata are preserved in `slop/logs/20260907_j_lens_native/task447-selected.log`; the downloaded extraction is under `outputs/experiments/j-lens-persona-components-source-v13/`.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| source preparation | 200 unique matched triples; fixed assistant suffix | 200 entry hashes but only 65 unique rendered messages per condition; sampled triples retain the same user text and assistant suffix | no | `task447-source-samples.log`; `component-persona-v15-dedup-check.log` | none | fit/split/holdout contain repeated model inputs |
| GP16 extraction | finite non-negative reconstructions at layers 13–21 | every layer reports two finite nonzero GP norms | yes | `task447-selected.log` per-layer lines | no alternate source seed | one deterministic extraction only |
| split stability | stable half-sample components | minimum split-half cosine `0.937` | yes | `task447-extraction-summary.log` | no independent seed | supports within-source stability |
| reconstruction | GP16 should preserve a useful part of each full residual | GP/full norm ratios `0.197–0.324`; full-to-GP cosines require metadata inspection | unclear | `task447-extraction-summary.log` | behavioral effect is not measured in extraction | sparse components are stable but discard most residual norm |
| pair geometry | `condition < 10`; `abs(cos) < .98` | maximum condition `2.280`; maximum absolute cosine `0.677` | yes | `task447-extraction-summary.log` | none for the stated criterion | basis is not near singular |
| held-out separation | positive and negative unseen source messages favor their intended coordinate | nominal target-coordinate order is `40/40`, but repeated messages cross fit and holdout | no | `task447-extraction-summary.log`; fresh review | deduplicated extraction | nominal rates are pseudoreplicated |
| DEV eligibility | both target orders alter a nontrivial share of attended positions | layer minima: `+C 0.524`, `-C 0.148`; maxima: `+C 0.852`, `-C 0.476` | yes, asymmetric | `task447-extraction-summary.log` | no patch norms yet | both interventions execute, but `-C` may be weaker |
| persistence | save both vectors and metadata | two 371,216-byte safetensors and 4.79 MB metadata downloaded | yes | `outputs/experiments/j-lens-persona-components-source-v13/extraction/` | remote-to-local pull was manual | artifacts are available locally |
| command completion | pueue should exit zero and retain a local log | Modal printed `EXTRACTION_COMPLETE` and `App completed`, but pueue exited 1 because `tee` could not create its destination directory | no | `task447-selected.log` | none | wrapper failure, not extraction failure |
| resolve condition | calibrate only after all stated extraction checks pass | numeric checks pass, but source independence fails because 200 entries reduce to 65 model inputs | no | fresh review and dedup check | deduplicated extraction | rerun extraction before calibration |

## Chronology

The shell wrapper reported two local errors before the remote work:

> `-o: 3: eval: Syntax error: "(" unexpected`
>
> `tee: slop/logs/20260907_j_lens_native/component-persona-v13-source.log: No such file or directory`

Source: `slop/logs/20260907_j_lens_native/task447-selected.log`. The second error makes the `pipefail` pipeline exit 1. The command should not wrap Modal in `sh -lc` or depend on an uncreated log directory; pueue already retains complete output.

Modal nonetheless loaded Qwen3.5-4B, extracted every requested layer, saved the vectors, committed the volume, and finished normally:

> `EXTRACTION_COMPLETE id=j-lens-persona-components-source-v13 hash_plus=a3f76d9e...`
>
> `Stopping app - local entrypoint completed.`
>
> `✓ App completed.`

Source: `slop/logs/20260907_j_lens_native/task447-selected.log`.

The layerwise result is compactly reproduced here:

| layer | split + | split - | GP/full + | GP/full - | component cos | condition | eligibility + | eligibility - | held-out + margin | held-out - margin |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 13 | .937 | .981 | .200 | .254 | .677 | 2.280 | .693 | .307 | 1.719 | 1.502 |
| 14 | .994 | .975 | .197 | .258 | .648 | 2.165 | .524 | .476 | 2.015 | .973 |
| 15 | .990 | .959 | .197 | .268 | .561 | 1.886 | .740 | .260 | 3.046 | 2.190 |
| 16 | .984 | .989 | .248 | .312 | .523 | 1.788 | .773 | .227 | 4.371 | 2.736 |
| 17 | .976 | .994 | .250 | .324 | .525 | 1.791 | .719 | .281 | 5.442 | 2.505 |
| 18 | .991 | .985 | .259 | .322 | .594 | 1.981 | .852 | .148 | 5.710 | 3.801 |
| 19 | .989 | .990 | .274 | .313 | .594 | 1.982 | .747 | .253 | 6.465 | 4.640 |
| 20 | .987 | .972 | .249 | .312 | .534 | 1.814 | .538 | .462 | 6.540 | 5.170 |
| 21 | .966 | .978 | .278 | .293 | .560 | 1.882 | .703 | .297 | 6.601 | 7.099 |

Source: `slop/logs/20260907_j_lens_native/task447-extraction-summary.log`, derived directly from the downloaded metadata. Each of the 40 positive held-out sources orders the positive coordinate higher, and each of the 40 negative held-out sources orders the negative coordinate higher at every layer. Baseline order is biased toward the positive coordinate on several layers, so held-out ordering establishes source separability, not a centered neutral axis.

I inspected source triples at indices 0, 100, and 199. Each uses the same source ID and user text under the positive, negative, and direct-accurate instructions. All end in the exact non-thinking assistant suffix, and their recorded final token is ID 271. This confirms triple alignment but not uniqueness. Example:

> `<|im_start|>user\nAnswer as someone who is sycophantic.\n\nTell me a story.<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n`

The corresponding negative and baseline prompts preserve `Tell me a story.` and change only the instruction. Source: `slop/logs/20260907_j_lens_native/task447-source-samples.log`.

No generation or judge stage was expected. A fresh review found that entry hashes included unused suffix fields: the model saw only `user_msg`, and exact counting shows 65 unique rendered prompts per condition, not 200. The review reported 123, but a direct assertion against both `load_suffixes()` and the downloaded metadata corrected that count:

> `local_pool=200 local_unique_user_msg=65`
>
> `v13_positive_prompts=200 v13_positive_unique_rendered=65`
>
> `PERSONA_SOURCE_DEDUP_COUNT_PASS unique_rendered_messages=65`

Source: `slop/logs/20260907_j_lens_native/component-persona-v15-dedup-check.log`. Task 447 therefore cannot establish independent split-half or holdout behavior. V15 now hashes and splits the 65 actual messages, producing 52 fit and 13 holdout items with no repeated rendered prompt.

## ML-debug form

| row | answer |
|---|---|
| log length; config | 196,061 cleaned lines. Qwen/Qwen3.5-4B, BF16, 200 matched sources, fit 160/holdout 40, GP16, layers 13–21, DEV-15 coordinate diagnostics. |
| `SHOULD:` lines | None emitted. The recorded resolve condition required stable splits, condition below 10, abs cosine below .98, and both DEV target orders nontrivial; each is satisfied in the table above. |
| numbers and null | Random-direction behavioral null is not measured at extraction. Geometry thresholds came from the preregistration, not a distributional null. The next DEV evaluation compares against the existing random-direction region. |
| before intervention | Held-out baseline coordinate means are near zero relative to persona means but are often ordered positive; no intervention was applied. |
| dummy/control | Direct-accurate prompt is the matched subtraction baseline. No shuffled-label extraction was run, and task 447's nominal holdout was contaminated by duplicate messages. |
| baseline model | Held-out positive and negative condition coordinates are compared with matched baseline coordinates; both are 40/40 target ordered at every layer. |
| schedule | No training schedule. GP uses exactly 16 pursuit steps. |
| full sample | Source indices 0, 100, and 199 for every condition are quoted in `task447-source-samples.log`. |
| worst step | Local persistence wrapper failed after remote success because the `tee` parent directory did not exist. No loss or gradient metric applies. |
| surprise | The 200 nominal sources contain only 65 unique rendered messages. Explained: entry hashes included unused suffix/category fields while extraction rendered only `user_msg`; task 447's stability is therefore inflated. |
| absent evidence | DEV generations, dose response, judged direction, off-axis damage, coherence boundary, all-100 replication, and uncertainty. |
| diagnoses | H1 99%; duplicate-input contamination 99%; semantic transfer 50%; instruction confound 35%; unknown 10%. |
| fresh review | Requested against the complete log, all extraction artifacts, sampled prompts, and code; its result will be appended before calibration is authorized. |
| cheapest discriminator | Run the existing DEV calibration over non-negative alpha and inspect raw generations plus judge scores. |
| wall-clock/GPU | Pueue duration 69 seconds; extraction metadata reports 21.58 seconds. GPU memory was not logged. Avoiding full metadata printing and duplicate model loads will shorten review and logs. |

## Hypotheses

### H1 [harness | Almost Certain | 99%]

- **Mechanism:** the remote extraction succeeded, but local `tee` failed because its parent directory did not exist; `pipefail` propagated exit 1.
- **Evidence:** the same complete log contains `tee: ... No such file or directory`, `EXTRACTION_COMPLETE`, and `✓ App completed` (`task447-selected.log`).
- **Contrary evidence:** pueue records `Failed:1`; this reflects the shell pipeline, not the remote subprocess.
- **Discriminating test:** rerun the existing remote extraction cache with no shell pipeline and let the local entrypoint pull artifacts. It should exit zero without recomputing vectors.
- **Fix/action:** make `extract_experiment` pull artifacts and print only a bounded metadata prefix; invoke Modal directly under pueue.
- **Interpretability:** yes; the persisted extraction is complete.

### H2 [data | Almost Certain | 99%]

- **Mechanism:** hashes of full suffix entries treated repeated `user_msg` values as unique even though the model input discarded the differing suffix fields.
- **Evidence:** `local_pool=200 local_unique_user_msg=65` and each v13 condition has 200 prompts but 65 unique rendered prompts (`component-persona-v15-dedup-check.log`).
- **Contrary evidence:** condition triples and assistant suffixes are aligned; the defect is independence, not mismatched conditions.
- **Discriminating test:** hash the rendered message identity and assert unique count before extraction. V15 does so and records 65 unique sources.
- **Fix/action:** deduplicate before seeded ordering and split; rerun extraction.
- **Interpretability:** no for split-half/holdout independence; yes for basic tensor execution.

### H3 [method | Chances a little better than even | 50%]

- **Mechanism:** deduplicated stable sparse persona components transfer causally to the DEV benchmark under target-ordered coordinate exchange.
- **Evidence:** minimum split-half cosine is .937; all held-out persona sources are target ordered; both DEV orderings are eligible at every layer.
- **Contrary evidence:** extraction measures representation, not behavior; GP16 keeps only .197–.324 of full residual norm, and previous phrase-derived components moved in an unintended direction.
- **Discriminating test:** non-negative DEV dose calibration with raw generation and blinded judge scores. Intended effects should have the correct sign broadly before severe off-axis change.
- **Fix/action:** deduplicate by rendered `user_msg`, split only unique identities, and re-extract before DEV calibration.
- **Interpretability:** no for task 447's independence claim; partial as engineering evidence.

### H4 [method | Unlikely | 35%]

- **Mechanism:** the extracted components primarily encode instruction wording, prompt length, or general response style rather than the intended behaviors.
- **Evidence:** the positive, negative, and baseline instructions differ substantially in length and lexical content; no assistant response is included in extraction.
- **Contrary evidence:** direct prompt controls validated the exact instructions behaviorally, and target ordering generalizes perfectly to held-out source messages.
- **Discriminating test:** DEV judge effects could remain near zero, reverse sign, or show style/off-axis movement despite strong latent separation. A later matched paraphrase source would separate wording from disposition if needed.
- **Fix/action:** do not relabel after observing outcomes; treat a failed DEV transfer as evidence against this extraction instance.
- **Interpretability:** yes as a specific matched-instruction component test.

### H5 [measurement | Highly Unlikely | 20%]

- **Mechanism:** nonzero aggregate eligibility hides near-zero changes at behaviorally decisive final positions, especially for `-C`.
- **Evidence:** `-C` eligibility falls to .148 at layer 18, and final-position eligibility varies by prompt.
- **Contrary evidence:** every layer has nontrivial all-position eligibility and later intervention diagnostics record realized patch and logit changes.
- **Discriminating test:** calibration must report realized patch norms, coordinate residuals, final-token KL, and raw output changes by side/dose.
- **Fix/action:** use existing `prefill_diagnostics`; interpret weak `-C` effects with eligibility rather than as a semantic null.
- **Interpretability:** partial if one direction is numerically sparse.

### H6 [harness | Remote | 10%]

- **Mechanism:** model weights could change under the same repository name because real-Qwen metadata records `model_revision: null`.
- **Evidence:** downloaded metadata records no model or tokenizer revision.
- **Contrary evidence:** tokenizer behavior and J-lens content are hashed; the Modal volume and HF cache used the same downloaded model for extraction and near-term calibration.
- **Discriminating test:** record a resolved HF model commit in Modal before later all-100 evaluation; reject mismatches.
- **Fix/action:** add stable model-revision provenance before publication-grade reuse if the loader continues to return null.
- **Interpretability:** yes for the immediate cached-volume calibration; weaker for long-term reproducibility.

## Decision

1. **Resolve-condition verdict: not met.** The numeric values satisfy the stated thresholds, but the intended independent split and holdout do not exist: 200 entry hashes reduce to 65 rendered messages, with repeated inputs crossing partitions. Deduplicated extraction is required before calibration.
2. **Prediction check:** distinct conditioned basis—supported; independent split stability—contradicted by duplicate leakage; independent held-out separation—contradicted by duplicate leakage; both DEV target orders active—supported but asymmetric; causal behavioral transfer—unresolved.
3. **Earliest unsupported link:** swapping the extracted coordinates must produce the intended signed behavioral changes. A coherent DEV dose-response with blinded judge scores would support it.
4. **Validity:** invalid means task 447 is used as evidence from independent fit/holdout model inputs. That use is invalid with approximately 99% confidence because duplicate rendered prompts are observed directly. Classification: credible engineering extraction with invalid independence evidence; no behavioral result yet.
5. **Highest-information clues:** (1) only 65 unique rendered messages underlie 200 entries; (2) task 447 still produced valid finite basis tensors; (3) both DEV orderings remain eligible despite strong asymmetry.
6. **Missing metrics:** DEV causal effect and coherence; model revision; shuffled-label extraction; source-paraphrase stability; all-100 replication.
7. **Bugs requiring code changes:** bound local metadata output, pull extraction artifacts, and avoid the failing shell/tee wrapper.
8. **Misconceptions requiring reinterpretation:** pueue `Failed:1` does not mean the remote extraction failed; strong source separation does not mean sycophancy steering works.
9. **What would change the verdict:** a deduplicated extraction that preserves stability, geometry, held-out ordering, and both DEV eligibilities would satisfy the extraction condition. Wrong-sign, random-region, or incoherent DEV effects would then reject that component instance for the public plot.
10. **Recommended sequence:** rerun extraction using the 65 unique rendered messages, audit the new diagnostics, and only then calibrate non-negative alpha. Keep instructions, layers, operator, and dose scale fixed.

— PI/OpenAI Codex
