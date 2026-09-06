# J-lens target-ordered v8b smoke

Target: local processes `proc_feeb` and `proc_9216` at HEAD `269a2607e72b2ed65adddec7460f5dc2d9be76eb` plus the reviewed v8b diff. Primary evidence is the complete 54-line [pipeline log](../logs/20260906_j_lens_native/component-target-ordered-v8b-smoke.log) and complete 29-record [calibration log](../logs/20260906_j_lens_native/component-target-ordered-v8b-calibration-smoke.log). The model is `wassname/qwen3-5lyr-tiny-random`; its text is expected to be incoherent, so this run tests execution rather than behavior.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| actual J-lens construction | autograd lens and projection controls complete | complete | yes | pipeline log: `TINY_LENS_FIT actual_autograd=true persona_projection=true full_residual_control=true` | none | real extraction path executed |
| GP16 extraction | finite non-negative components and rank-two pair | complete | yes | `j_norms=[214.392..., 120.989...]`; metadata condition number `1.779` | real-model scale | only code behavior is established |
| two target directions | both change logits, differ, and restore clean logits | complete | yes | `both_directions_changed_logits=true distinct=true restored_logits=true` | real-model semantic effect | side collapse is rejected |
| coordinate reconstruction | realized target coordinates match requested coordinates | residuals near zero | yes | α=1 residual medians: `3.44e-6` for +C and `0` for -C | BF16 real-model residual | float32 path is numerically consistent |
| generation | bare plus four smoke cells and six calibration cells persist | complete | yes | repeated `generation 15/15`; calibration `cells=6` | coherent text | random-model outputs cannot assess sycophancy |
| judge/export | standard DEV reader consumes both manifests | complete | yes | `JUDGE_COMPLETE required=59 missing=0`; both exports report `arms=4 scenarios=60` | all-100 evaluation | manifest compatibility is established |
| calibration provenance | copied vectors match source bytes and source hash is recorded | complete | yes | copied safetensor SHA-256 values match source; manifest records `extraction_reused_from` and `source_metadata_sha256` | remote-volume round trip | local self-contained persistence is established |
| public outputs | remain unchanged | complete | yes | `public_outputs_untouched=true` | none | no tiny result is presented publicly |

## Chronology and examples

The fixed scalar hash path passed save/reload and extraction. Both directions changed model state:

> `CONCEPT_REAL_HOOK_CHECK both_directions_changed_logits=true distinct=true restored_logits=true calls_once=true removed=true diagnostics=true`

The calibration recorded the expected dose scale. For +C, final-token KL moved from `0` at α=0 to `0.017692` at α=.25 and `0.32404` at α=1. For -C it moved from `0` to `0.0028701` and `0.040414`. A second cause of this asymmetry, besides different target ordering, is that 53.9% of attended positions required a +C exchange while 46.1% required a -C exchange in this random model. The nonzero coordinate residuals stayed below `3.5e-6`.

All inspected bare, +C, and -C generations were multilingual repeated fragments, for example the bare response starts `ratingsevt.toArray startX...`, +C α=.25 starts `尥 startX퓐...`, and -C α=.25 starts with the bare prefix before diverging. Health marked every condition `unfinished` and `repetition`. That is expected for the deliberately random tiny model and prevents behavioral interpretation.

## ML-debug form

| row | answer |
|---|---|
| log length and config | 54 pipeline lines and 29 calibration records; tiny random Qwen, float32 CPU, layer 2, α `.25,1` |
| `SHOULD:` lines | none |
| null and baseline | α=0 is exact logits identity (`KL_mean=0`); bare random text is also incoherent |
| before intervention | bare output is repeated random token fragments |
| dummy comparison | α=0 wins only the identity check; no semantic dummy is meaningful on a random model |
| held-out/model baseline | absent by design; this is not a scientific comparison |
| schedule | no training |
| complete sample | first bare and each side/dose appear in the calibration log; all are incoherent |
| worst step | +C α=1 has the largest KL, `0.32404`; no gradients or loss exist |
| surprise | the direction KL asymmetry is explained by complementary changed-position fractions and unequal coordinate deltas |
| evidence still needed | real Qwen BF16 extraction, multi-prompt calibration, coherent outputs, standard DEV judges, random-region comparison |
| diagnoses | harness executes correctly 90%; latent real-model dtype/mask bug 10%; behavior components miss sycophancy 55%; target ordering works semantically 45%; unknown 10% |
| fresh review | reviewer found five preflight issues; resolutions are recorded in [`20260906_j_lens_v8_preflight_review.md`](../reviews/20260906_j_lens_v8_preflight_review.md) |
| cheapest next test | fresh real-Qwen extraction followed by the existing 15-prompt α grid |
| wall time | pipeline 61 s; calibration/judge/export 71 s; GPU memory was not recorded because both used CPU |

## Hypotheses

### H1 [harness | Almost Certain | 95%]

- **Mechanism:** the revised extraction, vector persistence, direction selection, generation, judge, and export paths are connected.
- **Evidence:** `J_LENS_CONCEPT_PIPELINE_SMOKE_PASS ... generation=true judge=true export=true` and the separate calibration export completed.
- **Contrary evidence:** the tiny model uses one float32 layer rather than nine BF16 layers.
- **Discriminating test:** run fresh Qwen extraction and require finite rank-two bases plus low BF16 coordinate residuals at every layer.
- **Fix/action:** proceed to that extraction; stop on any failed invariant.
- **Interpretability:** yes, for pipeline connectivity only.

### H2 [method | Chances a little less than even | 45%]

- **Mechanism:** putting the larger local coordinate on the requested behavior component causes distinct positive and critical response changes.
- **Evidence:** the two interventions changed logits differently and affected complementary attended positions.
- **Contrary evidence:** random-model text has no semantic content, and fixed exchange previously moved only toward critical responses.
- **Discriminating test:** judge the full α grid on real-Qwen DEV and compare each side with the stored random-direction region.
- **Fix/action:** do not enable all-100 or public rendering before that comparison.
- **Interpretability:** no behavioral conclusion yet.

### H3 [measurement | Unlikely | 35%]

- **Mechanism:** a large aggregate effect could be caused by a few false-premise corrections rather than broad sycophancy control.
- **Evidence:** the preceding fixed-exchange DEV aggregate was dominated by a few scenarios despite small median scenario effects.
- **Contrary evidence:** v8b has not yet produced real-model judged outputs.
- **Discriminating test:** inspect all raw DEV responses and report both aggregate and median per-scenario changes.
- **Fix/action:** retain every response and audit scenario concentration before selection.
- **Interpretability:** yes if reported as a distribution, not only an aggregate.

## Decision

1. **Resolve-condition verdict:** met. The intended tiny extraction → intervention → generation → calibration → judge → export path completed, with self-contained calibration vectors.
2. **Prediction check:** both directions changed logits (supported); directions differed (supported); clean logits restored (supported); scalar persistence passed (supported); behavioral effectiveness (unresolved).
3. **Earliest unsupported link:** extracted behavioral component coordinates correspond to sycophancy behavior on real Qwen. Judged DEV responses would support it.
4. **Validity:** invalid means the smoke failed to execute or persisted inconsistent state. `P(smoke result is invalid) ≈5%`; this is a credible positive engineering result, not a scientific result.
5. **Highest-information clues:** distinct side logits reject side collapse; low coordinate residuals validate reconstruction; byte-identical copied vectors validate calibration provenance.
6. **Missing metrics:** real-Qwen semantic effects, coherence, random-region comparison, scenario concentration, all-100 confirmation.
7. **Bugs requiring code changes:** none remain from this smoke; the reviewer’s addressed findings are listed in the review resolution.
8. **Misconceptions requiring reinterpretation:** this target-ordering rule is a behavioral adaptation. It is not the paper’s evidence of sycophancy steering.
9. **What would change the verdict:** a BF16 residual failure or extraction cache mismatch would invalidate transfer from this smoke to the real run.
10. **Recommended sequence:** commit this reviewed implementation, extract fresh real-Qwen vectors, run the two-direction non-negative α calibration, then inspect and judge DEV before any all-100 run.

— PI/OpenAI Codex
