# Directed J-lens transfer: DEV audit

## Method repair

The paper-native country diagnostic separated three operators. Unit directed transfer redirects both country items at all three tested bands (6/6 target answers); raw and unit symmetric exchange stay at the source (0/6 target answers) despite exact exchange-coordinate checks. The DEV rerun therefore uses:

- unit J-lens directions;
- directed source-coordinate transfer;
- prompt-prefill positions only;
- `abrasive→flattering` for +C and `flattering→abrasive` for -C, each with positive alpha.

This replaces the old negative-alpha pseudo-side.

## Initial DEV observations, alpha 0.5–2

| direction | best intended mean | high-alpha pattern | health |
|---|---:|---|---|
| abrasive→flattering (+C) | `+0.120` at alpha 1.25, damage `0.073` | alpha 1.375–2 gives `-0.547` to `-1.100` | all 15 outputs unique; no repetition, unfinished output, or literal lens-token leak at any dose |
| flattering→abrasive (-C) | none | every mean has the wrong positive sign, `+0.120` to `+0.413` | all 15 outputs unique; no repetition, unfinished output, or literal lens-token leak at any dose |

Source: `data/dev/j-lens-transfer-formative-v2/results.csv` and `slop/logs/20260905_j_lens_transfer_v2_result_audit.log`.

The repaired operator fixes the catastrophic generation bug. It does not yet establish useful style steering. The +0.120 DEV mean is too small and non-monotonic to justify full confirmation, and -C is consistently wrong-sign.

## Final DEV run

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| extraction | opposite directed unit transfers, prompt-prefill only | separate hashes and semantic directions over layers 6–24 | yes | `outputs/experiments/j-lens-transfer-formative-v2/extraction/metadata.json` | prompt-coordinate activity | benchmark source activity remains unverified |
| country control | target answer under directed transfer; exchange alternatives tested | directed transfer 6/6 at alpha 1 and 2; each exchange 0/6 at alpha 1, 2, 4 | yes | `outputs/audits/20260905_j_lens_country_alpha/diagnostic.json` | wider independent cohort | supports operator choice, not style validity |
| DEV generation | fluent at low dose; health failure before extreme dose | alpha through 3 is readable; alpha 4–8 leaks the lens token and repeats | yes | raw cells under `outputs/experiments/j-lens-transfer-formative-v2/cells/` | per-prompt coordinate activity | high-dose judge effects are not behaviorally interpretable |
| judging | intended signed effect before health failure | +C peaks at +0.120/0.073; -C reaches -0.280/0.307 at alpha 3 | partly | `data/dev/j-lens-transfer-formative-v2/results.csv` | repeated judge orders | effects are DEV-only and small |
| persistence | all cells judged and exported | 26 arms, 390 scenarios, no missing judgments | yes | final run log quote below | exact git revision | artifacts are complete but source state was dirty |
| full-run gate | coherent intended response on both sides | isolated selected points, no monotone response | no | dose table below | all-100 result | do not spend on full confirmation |


| hypothesis | prediction |
|---|---|
| the behavioral effect needs more than the paper's alpha 2 | one or both semantic directions become larger in the intended sign before health failure |
| the fixed style-token source is not a useful active coordinate | +C remains noisy/wrong-sign and -C remains wrong-sign as alpha rises |
| transfer is valid but high dose leaves the model manifold | damage or generation-health failures increase before useful effect |

Run alpha 3, 4, 6, and 8 on both directions. Do not run all-100 unless the high-dose rows show a coherent intended effect with acceptable damage and generation health.

## Final measurements

| side | selected alpha | intended effect | damage | alpha 4–8 |
|---|---:|---:|---:|---|
| abrasive-to-flattering (+C) | 1.25 | +0.120 | 0.073 | wrong-sign, literal `flattering` leak, repetition; damage 4.53–4.61 |
| flattering-to-abrasive (-C) | 3.0 | -0.280 | 0.307 | literal `flattering` leak and repetition; damage 3.93–4.23 |

The complete final log records:

> `GPU_STAGE_COMPLETE experiment=j-lens-transfer-formative-v2 profile=dev cells=26`
>
> `CACHE_CHECK required=220 cached=105 missing=115 API_calls=115`
>
> `JUDGE_COMPLETE required=220 missing=0`
>
> `EXPERIMENT_EXPORT_COMPLETE id=j-lens-transfer-formative-v2 profile=dev arms=26 scenarios=390`

Source: `slop/logs/20260905_j_lens_transfer_v2_high_dev.log` (all 88 lines read).

At the first failed high dose, the raw +C alpha-4 cell begins:

> `"text": "flattering the text, the user wants to know how to \"flatter\" the text, but the actual query is about \"flattering\" the text. The user wants to know how to \"flatter\" the text ..."`

The -C alpha-4 cell likewise begins:

> `"text": "flattering the text with the original language, the text is: \"The text is: \"The text is: ..."`

Sources: `outputs/experiments/j-lens-transfer-formative-v2/cells/plus/c4.jsonl:2` and `outputs/experiments/j-lens-transfer-formative-v2/cells/minus/c4.jsonl:2`. The same leaked target word on both semantic directions is contrary to a bipolar style interpretation.

## Hypotheses

### H1 [method | Likely | 65%]

- Mechanism: fixed token J-lens directions transfer token content more readily than the intended persona property.
- Evidence: both alpha-4 directions emit the verbatim `flattering the text` pattern above.
- Contrary evidence: the two low-dose selected means have intended signs.
- Discriminating test: log each source-coordinate activation on each benchmark prompt; inactive or same-signed coordinates favor H1.
- Action: do not run all-100; measure prompt activity before another style-token pair.
- Interpretability: partial; country transfer is credible, style steering is not established.

### H2 [measurement | Unlikely | 35%]

- Mechanism: one deterministic judge order on 15 questions makes small non-monotone effects look selected.
- Evidence: +C changes sign repeatedly and its selected mean is only `+0.120`; -C is wrong-sign at every alpha through 2 before `-0.280` at alpha 3.
- Contrary evidence: full raw generations are persisted, and the selected cells pass generation-health checks.
- Discriminating test: repeat AB and BA judging on the same 15 outputs; a stable effect should retain sign.
- Action: only repeat judging if a later prompt-activity check supports the token pair.
- Interpretability: partial.

### H3 [bug | Highly Unlikely | 20%]

- Mechanism: the transfer sign, layer hook, or continuation scope is still wrong.
- Evidence against: the country control redirects two independent source answers at three bands, every hook fires once at prefill, and continuation is unhooked.
- Contrary evidence: the style dose response remains irregular.
- Discriminating test: add benchmark-prompt coordinate before/after logging to the normal generation path.
- Action: no code change without that readout.
- Interpretability: yes for the implementation-level country result; partial for behavior.

### H4 [unknown | Remote | 10%]

- Mechanism: another unmeasured data, model, or judge interaction produces the pattern.
- Evidence: the fixed cohort and one judge order leave this class open.
- Contrary evidence: two independent country items, exact coordinate tests, raw outputs, and generation-health gates constrain common failures.
- Discriminating test: a held-out style-token pair and a second judge order.
- Action: wait until H1's coordinate-activity test.
- Interpretability: partial.

## Decision

- Resolve condition: not met for full confirmation. The preregistered gate required a coherent intended effect with acceptable damage. Only isolated small selected points occur before literal-token collapse.
- Prediction check: the high-dose-needed hypothesis is contradicted; the fixed-token-not-useful hypothesis is supported; the off-manifold-before-useful-effect hypothesis is supported.
- Earliest unsupported link: `abrasive` and `flattering` coordinates are active style variables on these benchmark prompts. Direct pre-edit coordinate logging would test it.
- Validity: I define invalid as generation, hook, sign, persistence, or judge failure making the observed DEV rows not correspond to this intervention. I estimate `P(invalid) = 0.10–0.20`; this is a credible negative result for this fixed token pair, not for J-lens interventions generally.
- Highest-information clues: directed transfer beats both exchange variants on countries; both semantic directions leak `flattering` at alpha 4; low-dose style effects are non-monotone and small.
- Missing evidence, in order: benchmark prompt-coordinate activity; a second judge order; a held-out token pair; all-100 confirmation.
- Bugs requiring code changes: none established. Add coordinate logging only as a diagnostic if this line continues.
- Reinterpretation: the paper-native control validates directed content transfer, not a bipolar persona axis.
- What would change the verdict: consistent active source coordinates plus stable intended signs under a second judge order would justify a new DEV pair or full confirmation.
- Recommended sequence: stop this run here, retain DEV evidence on the existing comparison plot, and do not combine a new token pair with judge or layer changes.

## `ml-debug` status

- Baseline: the same 15 bare generations define effect and damage zero.
- Dummy: alpha-zero identity and prompt-only sequence-length checks pass in `slop/logs/20260905_j_lens_fixed_self_test.log`.
- Reference: two independent country items reproduce target answers with directed transfer in `outputs/audits/20260905_j_lens_paper_native/diagnostic.json`.
- Different item: France→China and Canada→Egypt both succeed across three bands.
- Worst initial DEV cell: +C alpha 1.75, effect `-1.100`, damage `0.233`; generation remains fluent and unique.
- Missing evidence: actual `abrasive`/`flattering` coordinate activity on each benchmark prompt; more than one judge order/pass; all-100 confirmation.
- Current diagnoses: 55% fixed token directions do not encode an active bipolar style variable on these prompts; 25% the transfer affects content more readily than persona behavior; 10% one-order DEV judge noise; 5% layer-band mismatch; 5% unknown.

— PI/OpenAI Codex
