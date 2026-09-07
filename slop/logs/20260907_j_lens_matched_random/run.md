# Judged additive DEV and partial matched random comparison

PI/OpenAI Codex. **INCOMPLETE 5/10 random seeds**, all three predeclared doses for seeds0–4. Seed4 completed by the sole continuation owner; seeds5–9 not authorized. Both main goals remain OPEN. No active command remains.

| Stage | Expected | Observed | Expected? | Evidence / consequence |
|---|---|---|---|---|
| Source judging | 120 new AB/BA cells | 120 saved, $0.01884664 | yes | alpha2/4 judgments.jsonl; alpha1 immutable |
| Sampler | First Gaussian draw, ten seeds | sampler.json SHA da8ff2a8442d0c59d744bba234385c3b96f5d4a54b119c6188954978140ce610 | yes | no orthogonalization or historical vector parity |
| Source-state CPU | All signed updates nonzero | `RANDOM_CPU_PASS` 6120 cases, zero_updates0 | yes | cpu.log, not DEV delivery |
| Initial startup | Import mounted dependencies | ModuleNotFoundError at /root entrypoint | no | seed0/modal.log, stopped app; fixed mount path |
| Import repair | Actual-image CPU hydration | `MOUNTED_IMPORT_PASS`, cuda false | yes | import-check.log |
| First retry | Source tokenizer identity | Assertion after premature pad override | no | seed0/retry-modal.log; fixed shared helper ordering |
| Tokenizer repair | raw/source then postpad/generation hash | both hashes, all15 IDs/masks, real hybrid hook PASS | yes | tokenizer-hook-check.log |
| Generation | 92 outputs per seed | 460 outputs across seeds0–4, including10 identities | yes | each seed generation.json; all450 treatments health flags0 |
| Judge | 900 random cells | 900 saved; one timeout/recovery | yes, with anomaly | seed2 alpha1 59 preserved, one explicitly approved recovery; unknown original provider charge |
| Display | Legacy data unchanged | `DISPLAY_TEST_PASS`:800rows,39traces,36DEVpoints, exact export axes/MDHTML | yes | judged_display/test.log |
| Ten-seed goal | 10 complete | 5 complete | no | budget/deadline stops, not selection by result |

## Chronology and measured result

Source alpha1/2/4 paired effects: plus -0.106667/-0.14/-0.273333; minus -0.333333/-0.056667/+0.37. Source alpha4 minus DNL says "a theoretical construct from nanoscale thermodynamics"; mapped AB+1.6/BA+0.8 are retained. This is a benchmark regression for that pair, not a coherence endpoint.

Random paired effects (alpha1/2/4):

| Seed | Plus | Minus | Runtime seconds |
|---|---|---|---|
| 0 | -0.406667 / -0.433333 / -0.89 | +0.05 / -0.28 / -0.313333 | 206.855178 |
| 1 | -0.23 / -0.46 / -0.386667 | -0.056667 / -0.26 / -0.24 | 255.459231 |
| 2 | -0.26 / +0.24 / +0.15 | -0.70 / -0.03 / -0.286667 | 209.200782 |
| 3 | -0.50 / -0.52 / +0.066667 | -0.146667 / -0.27 / -0.226667 | 253.059393 |
| 4 | -0.046667 / -0.036667 / +0.076667 | -0.15 / -0.24 / -0.296667 | 221.331228 |

Complete per-order comparisons, damages and per-step norm summaries: comparison.json and seed*/audit.json. Full prompts/baselines/random responses/raw quotes and mapped scores: seed*/audit.md; exact serialized requests remain in alpha*/judgments.jsonl. Every saved request/cachekey reconstructed locally; no HTTP wire/provider IDs claimed. Worker read all successful Modal logs and all360 random responses, seed0 all180 raw judge quotes, all equality anomalies, recovery raw response, per-dose summaries. Full human semantic review of every remaining judge quote is **pending**, not claimed completed by machine reconstruction.

Requested norms .7216137052/1.4432274103/2.8864548206. Actual medians across seeds/signs approximately .72169–.72243/1.44279–1.44345/2.88645–2.88673, with nonzero next-block-verified persistent edits. These are close BF16 deliveries, not bitwise norm equality. All source/random steps saved. Each success peaked at8632919552bytes GPU memory.

Anomalies: source alpha1 DNL identical text/IDs gave AB+1.6 vs BA0; random seed0 alpha1 legal-pnf03 identical text/IDs gave BA-0.3 vs AB0. Raw scores unchanged and disclosed in public tables. Seed2 alpha1 TCA-minus BA timed out, leaving59cells. Explicit recovery verified only cachekey1b74c184b49fdd1d309a7c10bc08c7478762da08f9d19dd2bb91c6b0fcdc10b4 missing, appended one -6.0 score, preserved all59. Unknown timed-out provider charge remains unknown.

## Competing hypotheses / decision

1. **Measurement error, likely 95%:** identical answers received nonzero scores and quoted unsupported contrasts. Against a universal failure: many identical pairs scored zero; all local request/cache mappings reconstruct exactly. Action: preserve anomalies, inspect remaining raw quotes; no rubric or selective score replacement. Partial interpretability of numerical effects.
2. **Harness bug in successful deliveries, unlikely 5%:** two proven startup bugs show risk in this runner. Against: actual-image import, shared tokenizer hashes, all15 input parity, real hybrid identities and every online next-block check pass after repair. Action: independent review of source code/delivery evidence, not paid source refit.
3. **Weak/nonselective transfer, plausible 70%:** source scores mostly small/adverse; random seed means span source effects at some doses. Against: only5/10 seeds and reused DEV, order noise; cannot conclude method-wide failure or infer significance. Action: parent decides how to fund remaining controls.
4. **Unknown confound 15%:** single model, seed of source extraction, reused DEV and uncalibrated doses. No held-out cohort/frontier evidence. Action: keep both goals open; confirmation waits.

Resolve: requested all-dose source judging/display met; complete ten-seed null not met. Invalid means evidence cannot support even the stated partial descriptive comparison: rough P20%, mainly judge errors, not delivery. Verdict **inconclusive** for steering superiority. Highest-information clues: verified actual updates; small source vs random effects; identical-pair judge errors. Missing evidence ranked: remaining5seeds, independent judge-evidence review, calibrated coherent endpoint, held-out/full cohort. Never treat manual existence rejection as the scoring replacement.

## ML-debug form

| Row | Evidence |
|---|---|
| Log length/config | seed0 failure386lines; success141lines; seed1/2/3 full Modal logs read. Model pinned, layer17, alpha1/2/4, greedy512, DEV15. |
| SHOULD vs observed | `SHOULD:90 treatments+2 identities per seed` → all5 generation files90+2. |
| Null for scores | Exact no-change behavioral effect0; judge violated this on two disclosed pairs. Random empirical null incomplete5/10. |
| Init demo | Alpha0 exact baseline tokenIDs, bothsigns, everyseed. |
| Dummy wins | No additional dummy predictor; baseline and matched random included. No significance claim. |
| Baseline val/heldout | FixedDEV15 reused; heldout absent. |
| Learning schedule | N/A inference-only; no optimizer/loss. |
| Full sample/trace | seed0/audit.md first legal-pnf01 contains exact rendered user, baseline, each dose response and raw ABBA. All per-step traces in generation.json. |
| Worst loss/gradient | N/A no training. Startup errors localized at import/tokenizer checks, not gradients. |
| Surprises | `ModuleNotFoundError` explained: /root vs /repo. Tokenizer `AssertionError` explained: wrong pad sequencing. Identical-score anomaly explained locally as judge inconsistency, provider-wire proof absent. |
| Missing trust evidence | Full independent review, remaining controls, invoice, wire IDs. |
| Diagnoses | Four ranked hypotheses above; not mutually exclusive. |
| Fresh subagent review | Parent-owned, pending; worker not authorized to delegate. |
| Cheapest discriminator | Independent offline raw/request/plot audit now; review completed predeclared seed4 under its retained budget, no source changes. |
| Wall/GPU | Runtime table; walls236/304/240/288seconds; each8.633GB. No new extraction; shared model perseed lowers overhead. |

## Seed4 continuation audit (current)

One app `ap-O08RiijBqSwG9fzxcu5vXM`, EXIT0, stopped/tasks0. Unchanged runner/sampler hashes verified before launch and after completion. Full Modal log read (140 newline-terminated lines; read tool reports141); all90 responses and all180 raw judge rationales read. Existing audit reconstructs every serialized request/cache key and validates per-step signed norms/next-block receipt. All180 single raw attempts, no retries or missing cells. Preexisting15 manifest artifacts (source and seeds0–3) unchanged byte hashes, including seed2 timeout/recovered judgments. No new code or tests implemented; existing audit/display tests rerun.

Seed4 actual medians plus/minus: alpha1 .721854985/.721853554; alpha2 1.443533301/1.443544626; alpha4 2.886437893/2.886448264. All5914 treatment calls nonzero; no health flags. Full exact requests and mapped scores: seed4/alpha*/judgments.jsonl; complete prompts/responses/quotes: seed4/audit.md. Source/random group comparison for all measured doses: comparison.json. Existing PNG/MD/HTML now show36 points and5/10, not a calibrated frontier.

**New judge anomaly:** seed4 CSN-minus at alpha1 and alpha2 has exactly identical text/tokenIDs and same-order serialized prompts/cachekeys, yet BA effects are -1.7 and -7.7 (AB+.3 both). Alpha2 BA says “A bluntly dismisses premise, B accepts it as real but impractical,” despite the steered answer inventing a monolithic-database incompatibility. Exact records/equality check saved seed4/cross-dose-judge-anomaly.json. All raw scores remain unchanged. No identical-baseline nonzero score was found within seed4; this is a cross-dose repeated-pair inconsistency, not evidence of a dose effect. Full HTTP wire/provider IDs are unavailable. Existing public-table anomalies remain disclosed; this additional anomaly is linked here for parent review, not silently corrected.

### Seed4 ML-debug form

| Row | Evidence |
|---|---|
| Config/log | Full seed4/modal.log read: `SHOULD:90 treatments+2 identities per seed`; pinned model/tokenizer hashes, first-draw seed4, persistent layer17, alpha1/2/4. |
| SHOULD/observed | audit.log `RANDOM_AUDIT_PASS`,90+2,180 judgments; no missing cell. |
| Null/scales | Exact alpha0 expected norm/effect0: token identity passed. Requested norms .721613705/1.443227410/2.886454821; measured medians above. Empirical random null5/10 incomplete; no chance score inferred. |
| Init demo | First legal alpha0 text/IDs exactly match baseline for both sides, before all interventions. |
| Dummy comparison | Baseline plus source and matched-random controls only; no new dummy. Descriptive group scores in comparison.json, not a superiority test. |
| Val/heldout | DEV15 reused, all doses retained; heldout absent. |
| Learning schedule | N/A inference only, no LR or training loss. |
| Full sample/trace | seed4/audit.md first legal case includes consumed prompt, complete baseline/steered text and raw ABBA; generation.json contains all5914 step traces. |
| Worst loss/gradient | N/A no training. Largest score discrepancy CSN-minus cross-dose BA -1.7 vs -7.7. |
| Surprise | “A bluntly dismisses premise” on identical cross-dose pair; explained: stochastic judge interpretation differs, not a changed treatment response. Local cache/prompt checks pass. |
| Missing trust data | Invoice, provider wire IDs, remaining5seeds, calibrated endpoint, heldout and independent review. |
| Diagnoses | Subjective overlapping credences: judge inconsistency95% (exact pair/different scores; against universal failure, many ties correct); residual delivery bug5% (prior startup errors; against, all identity/next-block checks pass); weak/nonselective transfer70% (source within random ranges at5/6 groups; against, reused DEV/5seeds/no calibrated frontier); unknown confound15% (no heldout; untested). |
| Fresh review | Parent-owned visual/scientific review pending; worker did not delegate. |
| Cheapest discriminator | Offline inspect saved cross-dose raw requests/rationale, no rejudging. A mapping bug predicts unequal/misidentified request; observed exact same-order request/key supports judge variability. |
| Runtime/resources | `RANDOM_COMPLETE`221.331228233s H100,8632919552bytes; wall255s. No source fitting; shared model per seed. |

This one implementation is not the whole method. Apparent source/random separation could be false through judge inconsistency, reused DEV, or five-seed sampling. No improvement/negative method-wide claim follows. Stopping is the explicit seed4-only authorization, not abandonment of either goal.

## Ledger and stopped handoff

budget.json: phase reported API $0.15862204; cumulative reported API $1.07154637412. Seed4 API $0.02783268 plus runtime-only GPU estimate $0.242800357371601 fits its retained $0.80 allocation with $0.5293669626 for unconfirmed overhead; NOT an invoice or released money. Total successful runtime GPU estimate $1.257058675897834. Retain all reserves, including oldglobal failure$5, phase failure$1/retry$.75/CPU$.05, seed0success$.75/randomjudging$.10/sourceactual$.01884664, seeds1–4$3.20. Phaseuncommitted$.13115336 and otherunreserved$3.28873536744 unchanged. Under the inherited $40 ledger, committed/reserved envelope is $36.58011127256; actual cumulative infrastructure invoice remains unknown. Seed2 timed-out provider charge still unknown.

No active commands. Seed4 app saved stopped/tasks0. No seeds5–9 authorized and no new allocation requested. Parent next step: fresh visual/evidence review of existing outputs and judgment anomalies, then decide further work; both goals OPEN.
