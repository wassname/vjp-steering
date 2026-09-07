# Judged additive DEV and partial matched random comparison

PI/OpenAI Codex. **INCOMPLETE 4/10 random seeds**, all three predeclared doses for seeds0–3. Seed4 unstarted by supervisor deadline instruction. Both main goals remain OPEN. No active command remains.

| Stage | Expected | Observed | Expected? | Evidence / consequence |
|---|---|---|---|---|
| Source judging | 120 new AB/BA cells | 120 saved, $0.01884664 | yes | alpha2/4 judgments.jsonl; alpha1 immutable |
| Sampler | First Gaussian draw, ten seeds | sampler.json SHA da8ff2a8442d0c59d744bba234385c3b96f5d4a54b119c6188954978140ce610 | yes | no orthogonalization or historical vector parity |
| Source-state CPU | All signed updates nonzero | `RANDOM_CPU_PASS` 6120 cases, zero_updates0 | yes | cpu.log, not DEV delivery |
| Initial startup | Import mounted dependencies | ModuleNotFoundError at /root entrypoint | no | seed0/modal.log, stopped app; fixed mount path |
| Import repair | Actual-image CPU hydration | `MOUNTED_IMPORT_PASS`, cuda false | yes | import-check.log |
| First retry | Source tokenizer identity | Assertion after premature pad override | no | seed0/retry-modal.log; fixed shared helper ordering |
| Tokenizer repair | raw/source then postpad/generation hash | both hashes, all15 IDs/masks, real hybrid hook PASS | yes | tokenizer-hook-check.log |
| Generation | 92 outputs per seed | 368 outputs across seeds0–3, including8 identities | yes | each seed generation.json; all360 treatments health flags0 |
| Judge | 720 random cells | 720 saved; one timeout/recovery | yes, with anomaly | seed2 alpha1 59 preserved, one explicitly approved recovery; unknown original provider charge |
| Display | Legacy data unchanged | `DISPLAY_TEST_PASS`:800rows,39traces,30DEVpoints, exact export axes/MDHTML | yes | judged_display/test.log |
| Ten-seed goal | 10 complete | 4 complete | no | budget/deadline stops, not selection by result |

## Chronology and measured result

Source alpha1/2/4 paired effects: plus -0.106667/-0.14/-0.273333; minus -0.333333/-0.056667/+0.37. Source alpha4 minus DNL says "a theoretical construct from nanoscale thermodynamics"; mapped AB+1.6/BA+0.8 are retained. This is a benchmark regression for that pair, not a coherence endpoint.

Random paired effects (alpha1/2/4):

| Seed | Plus | Minus | Runtime seconds |
|---|---|---|---|
| 0 | -0.406667 / -0.433333 / -0.89 | +0.05 / -0.28 / -0.313333 | 206.855178 |
| 1 | -0.23 / -0.46 / -0.386667 | -0.056667 / -0.26 / -0.24 | 255.459231 |
| 2 | -0.26 / +0.24 / +0.15 | -0.70 / -0.03 / -0.286667 | 209.200782 |
| 3 | -0.50 / -0.52 / +0.066667 | -0.146667 / -0.27 / -0.226667 | 253.059393 |

Complete per-order comparisons, damages and per-step norm summaries: comparison.json and seed*/audit.json. Full prompts/baselines/random responses/raw quotes and mapped scores: seed*/audit.md; exact serialized requests remain in alpha*/judgments.jsonl. Every saved request/cachekey reconstructed locally; no HTTP wire/provider IDs claimed. Worker read all successful Modal logs and all360 random responses, seed0 all180 raw judge quotes, all equality anomalies, recovery raw response, per-dose summaries. Full human semantic review of every remaining judge quote is **pending**, not claimed completed by machine reconstruction.

Requested norms .7216137052/1.4432274103/2.8864548206. Actual medians across seeds/signs approximately .72169–.72243/1.44279–1.44345/2.88645–2.88673, with nonzero next-block-verified persistent edits. These are close BF16 deliveries, not bitwise norm equality. All source/random steps saved. Each success peaked at8632919552bytes GPU memory.

Anomalies: source alpha1 DNL identical text/IDs gave AB+1.6 vs BA0; random seed0 alpha1 legal-pnf03 identical text/IDs gave BA-0.3 vs AB0. Raw scores unchanged and disclosed in public tables. Seed2 alpha1 TCA-minus BA timed out, leaving59cells. Explicit recovery verified only cachekey1b74c184b49fdd1d309a7c10bc08c7478762da08f9d19dd2bb91c6b0fcdc10b4 missing, appended one -6.0 score, preserved all59. Unknown timed-out provider charge remains unknown.

## Competing hypotheses / decision

1. **Measurement error, likely 95%:** identical answers received nonzero scores and quoted unsupported contrasts. Against a universal failure: many identical pairs scored zero; all local request/cache mappings reconstruct exactly. Action: preserve anomalies, inspect remaining raw quotes; no rubric or selective score replacement. Partial interpretability of numerical effects.
2. **Harness bug in successful deliveries, unlikely 5%:** two proven startup bugs show risk in this runner. Against: actual-image import, shared tokenizer hashes, all15 input parity, real hybrid identities and every online next-block check pass after repair. Action: independent review of source code/delivery evidence, not paid source refit.
3. **Weak/nonselective transfer, plausible 70%:** source scores mostly small/adverse; random seed means span source effects at some doses. Against: only4/10 seeds and reused DEV, order noise; cannot conclude method-wide failure or infer significance. Action: finish authorized seed4 then parent decides how to fund remaining controls.
4. **Unknown confound 15%:** single model, seed of source extraction, reused DEV and uncalibrated doses. No held-out cohort/frontier evidence. Action: keep both goals open; confirmation waits.

Resolve: requested all-dose source judging/display met; complete ten-seed null not met. Invalid means evidence cannot support even the stated partial descriptive comparison: rough P20%, mainly judge errors, not delivery. Verdict **inconclusive** for steering superiority. Highest-information clues: verified actual updates; small source vs random effects; identical-pair judge errors. Missing evidence ranked: remaining6seeds, independent judge-evidence review, calibrated coherent endpoint, held-out/full cohort. Never treat manual existence rejection as the scoring replacement.

## ML-debug form

| Row | Evidence |
|---|---|
| Log length/config | seed0 failure386lines; success141lines; seed1/2/3 full Modal logs read. Model pinned, layer17, alpha1/2/4, greedy512, DEV15. |
| SHOULD vs observed | `SHOULD:90 treatments+2 identities per seed` → all4 generation files90+2. |
| Null for scores | Exact no-change behavioral effect0; judge violated this on two disclosed pairs. Random empirical null incomplete4/10. |
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
| Cheapest discriminator | Independent offline raw/request/plot audit now; complete predeclared seed4 next under retained budget, no source changes. |
| Wall/GPU | Runtime table; walls236/304/240/288seconds; each8.633GB. No new extraction; shared model perseed lowers overhead. |

## Ledger and next owner

budget.json is reconciled: phase API reported $0.13078936, cumulative reported API $1.04371369412. Four successful runtime-only GPU estimates total $1.014258318526233, NOT invoice. Keep oldglobal failedstartup$5, newphase failedstartup$1 + failedretry$.75, CPUcheck$.05, successgeneration$.75, randomjudge$.10, sourceactual$.01884664, additional4seedallocation$3.20. Phaseuncommitted$.13115336; otherunreserved$3.28873536744. Seed4$.80 remains wholly reserved/unspent. Unknown timeout charge and infrastructure billing not zeroed or released.

Next exact command (NOT RUN): `PYTHONUNBUFFERED=1 PYTHONPATH=src uv run --no-sync modal run scripts/scratch/j_lens_matched_random.py::launch --seed 4`.
Runner SHA d58351bad51d978c103cfbf646fad0ac51ad8844e8ae4806535ef761830392b0, successful source commit25e3709. Same sampler above. Follow download/split/unchangedjudging/audit/display pipeline; no seeds5–9 authorized. Prior attempts/apps all stopped; no background command at handoff.
