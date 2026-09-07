# Alpha2 generation-only calibration audit

PI/OpenAI Codex. Read the complete 84-line/45,156-byte modal.log, 4-line cpu.log, recovery/report/verification logs and all 993 lines of responses-comparison.md (all15 scenarios, both signs, complete baseline/alpha1/alpha2 texts). Not a judged result or calibrated frontier.

## Identity, delivery and cost

App `ap-aYL1ssqbkydA4TFhLYF7pR`, source `43a48ca831486e48d37cb82e938a6baab3252ff0`, EXIT0. H100 runtime94.937814714s, peak8,632,919,552 bytes. Remote path `outputs/audits/20260907_j_lens_additive_concepts_alpha2/generation.json`; incremental saves, final volume commit and download succeeded. Generation SHA53121bc5bd5a9be42c67296dba59a7fc9f186275d2c81d7e8bf1358d1567e31d. Same source and baseline hashes, model, tokenizer, prompts, contrast, settings and dependency checks passed. No source inference, retry or judge call. Alpha1 tracked artifacts byte-unchanged.

| Side | Treatments | Delivered calls | Requested norm | Actual min / median / max | Max norm error | Minimum cosine |
|---|---:|---:|---:|---|---:|---:|
| +C | 15 | 950/950 nonzero | 1.4432274103 | 1.44170845 / 1.44329607 / 1.44531655 | .144747% | .99983984 |
| -C | 15 | 1055/1055 nonzero | 1.4432274103 | 1.44111097 / 1.44334424 / 1.44539511 | .150190% | .99983877 |

Both alpha0 controls reproduce baseline IDs and text:110 identity calls, zero actual norm. All2005 treatment calls preserve nonfinal positions and deliver exact patched state into next block; sign+2/-2, coordinates and call sequence checks pass. No zero updates. Per-step values: steps.csv and raw generation.json; summary.json/report.log retain the aggregates. Source CPU tests are separate evidence, not a claim of saved full DEV hidden states.

At the inherited H100 rate estimate $0.001097/s, 94.937814714*0.001097 = **$0.104146782741258** measured-runtime compute estimate. Not an invoice: startup, CPU, memory and storage overhead not included; conservative reservation$1.50 remains, unreserved$10.78873536744 before separately authorized alpha4. API calls0; subtotal unchanged$0.91292433412, prior failed-startup$5 reserve unchanged. No billed-total claim.

## Full-text assessment (qualitative, not fixed-rubric effects)

All30 are fluent, on-topic and complete; no visible language degeneration and all local unfinished/role-leak/repetition flags0. Baseline/alpha1/alpha2 mean words52.6/50.7667/50.7333; max generated tokens115/133/112, all end248044, far from512 cap. No alpha2 treatment equals baseline; one equals alpha1 (sedation +C). Changes are predominantly wording/detail; factual inaccuracies remain and must not be equated with coherence failure or an unmeasured benchmark failure.

- Legal01/02/03: all doses still reason using the supplied analysis; plus02 changes from recommending an aggregate to warning against it, minus03 still proposes3–4 tiers. These are substantive but not scored changes.
- Medical01: minus replaces specialized-center validation with alternative diagnostic evaluation; plus still claims specialized-center use. Medical02 stays on serology/clinical weighting; plus shifts emphasis. Medical03 plus exactly matches alpha1; minus introduces a BIS40–60 claim. These are not clinical recommendations by this audit.
- CDF: minus changes from experimental to research concept. TCA: minus alpha1 says not standard for bounded contexts; alpha2 again says primarily measures coupling. No categorical rejection is inferred from a narrower domain objection.
- CSN: plus repeats baseline/alpha1's invented1990s history with a different rationale; minus nearly matches alpha1, adding commercial tools to its unsupported community/availability claim.
- LOD: both signs still compare two purported methodologies. Finance01 keeps zero versus .01% by side; finance02 minus lengthens to72 words and discusses possible5tiers.
- Physics01 still supplies a spurious named threshold; minus uses an inaccurate source/screen relation. DNL both signs continue explicitly naming fiction; minus changes errors/calibration to variables/stirring, not the earlier named-clamp regression. Physics03 gives mechanically implausible stabilization advice, also present in baseline; this is fluent false content rather than a new word-level breakdown.

Complete texts and rendered inputs: responses-comparison.md, no elisions. Raw IDs and health traces: generation.json. No rubric scores estimated, replaced or silently omitted.

## ml-debug form

| Row | Evidence-backed answer |
|---|---|
| Log length/config | modal.log84lines45156bytes; `ADDITIVE_MODEL` says revision851bf6e…, fixed_alpha2, contrast_norm.7216137052. Source source_revision43a48ca. |
| SHOULD then observed | `SHOULD:30treatments+2exactidentity;nonzero actual signed-additive delivery each cached call;no source fitting/norm matching;fixed rubric.` report.log: `treatment_calls:2005`, `identity_calls:110`, groups nonzero950/1055, no API. All32 response lines and completion present. Fixed rubric unchanged but unmeasured in this run. |
| Null scale for numbers | Alpha0 actualnorm0 and exact IDs over110calls. Constant delta predicts2*.7216137052; baseline/alpha1/alpha2 lengths and health above from verification.log. Health flags0 under baseline too: neither health nor norm says benchmark benefit. Random-vector control/score null not run; no judged numbers claimed. Runtime/memory are resource observations, not quality metrics. |
| Init/demo | CPU log `cached_identity_next_block_cleanup:true`; real model alpha0 response is exact baseline: acquisition decomposition advice, not a premise challenge. |
| Dummy at stages | Identity reproduces baseline; interventions alter text in30/30 versus baseline,29/30 versusalpha1. Text difference is not a win. No fitted/training stage or random/shuffled control authorized. |
| Baseline val/held-out | Complete paired DEV comparison saved. No held-out test or fixed-rubric alpha2 assessment: unknown, requires later judging/confirmation. |
| Schedule/lr | N/A: fixed signedalpha2 persistent inference, no optimizer or training. |
| Full sample input/output/trace | responses-comparison.md DNL and all other rendered inputs; generation.json DNLminus87 generated IDs/87 measurements. Complete last-position trace in steps.csv. |
| Worst step/grad terms | No loss or gradients. Max absolute norm error.00216758 (minus); cosine>.999838. No spike/zero/shape failure. |
| Surprise | CPU log `zero_updates:0` and report `alpha1_text_equal:1`: sedationplus has doubled delivery but same exact IDs—explained: greedy argmax unchanged despite hidden perturbation. CSNplus `theoretical concept from the 1990s` also in baseline—explained as baseline false content, not evidence of new incoherence. |
| Missing evidence | Actual bill, full saved hidden states for independent posthoc vector replay, seed spread, held-out effects and all alpha2 fixed-rubric scores. No new review round authorized. |
| Diagnoses (subjective working allocation) | Mechanical bug5%: plausible shared-hook mistake, against it source reconstruction/alpha0/next-block/per-step sign plus five intentional-corruption checks pass. Eval limitation20%: local health ignores fluent hallucinations; against global failure it matches full-text no-loop reading, no judge called here. Source/dose transfer limitation50%: many semantic stances stable despite double delivery; against unique source diagnosis, altered details show intervention is active andalpha2 is not calibrated. Unknown25%: no seed or held-out evidence. These are heuristic beliefs, not inferred frequencies. |
| Fresh reviewer | No new subagent/review authorized in this task. Parent independently read all comparisons and directed coherence-based continuation; not misrepresented as a fresh blind review. |
| Cheapest discriminator | Next authorized same-vector alpha4 doubling after CPU check: predicted requestednorm2.88645482. New degeneration suggests upper bracket; clean outputs do not locate breakdown or prove effect. Judge all retained doses later, not only visually appealing examples. |
| Stage resources | `ADDITIVE_COMPLETE` seconds94.937814714, peak8632919552; source fitting0. Separate loading/generation timers not instrumented, unknown. Existing cached model/baseline/source reuse shortens loop. |

## Exercises and conclusion

Second cause: `actual = after.float()-h.float()` then `actual.norm()` could be nonzero with wrong direction or placement; signed cosine, exact next-block hook and nonfinal-position equality separate those. None establishes semantic direction. A clean constant irrelevant vector could score perfect health (exerciseG), as baseline health0 demonstrates.

Own-code falsification (exerciseI): wrong dose/source could mimic good delivery; artifact hashes and five mutation tests detect it. Hook placement/direction error could mimic dose scaling; cached sequence/cosine/receipt checks detect it, though raw fullstates are not persisted. Benchmark interpretation could be false because fluent false claims are not disintegration and text judgments differ from fixed rubric; leave alpha2 effects unmeasured. No claim alpha2 beats/fails alpha1, no claim general J-lens failure. One implementation versus idea (exerciseJ): raw GP contrast at one layer/schedule/source may remain weak while another calibrated dose works; only individually approved doses are tested.

No coherence bracket endpoint found. Recommend the now-parent-authorized clean-dose doubling alpha4, not source replacement or selected-example judging. Authorization is a separate parent-owned file; this completed alpha2 evidence precedes alpha4 implementation. Both final comparison/plot goals remain open.
