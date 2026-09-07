# Full-residual target-order control v16 smoke

— PI/OpenAI Codex

Target: test the complete matched condition-minus-baseline residual with the existing target-order coordinate intervention. This is a non-J diagnostic control; it is not paper-native J-lens evidence.

## Stage audit

| stage | expected | observed | expected? | consequence |
|---|---|---|---|---|
| extraction | use the full positive and negative residuals, not GP16 reconstructions | metadata says `projection=full_residual`; saved basis rows equal the unit-normalized full signals and differ from GP16 | yes | the diagnostic isolates GP16 projection from the source and intervention |
| intervention | both fixed targets change logits; hooks execute once and are removed | `both_directions_changed_logits=true distinct=true restored_logits=true calls_once=true removed=true` | yes | no hook lifecycle failure was found |
| generation | persist bare, `+C`, and `-C` results at alpha .25 and 1 | five 15-row generation files completed | yes | the real generation path executed |
| judge/export | complete the standard DEV experiment interfaces | `JUDGE_COMPLETE required=60 missing=0`; 60 scenario rows exported | yes | downstream interfaces accept the new projection identity |
| public files | leave the public comparison unchanged | `public_outputs_untouched=true` | yes | random-model results cannot enter the public plot |

## Complete log

The full smoke log is 48/48 lines: [`v16-smoke.log`](../logs/20260907_j_lens_full_residual/v16-smoke.log).

Key lines:

> `persona components layer=2 projection=full_residual basis_norms=[159.48233032226562, 260.1879577636719] split_basis_cosines=[0.9650400876998901, 0.9942208528518677] component_cosine=0.7222 condition=2.490 eligibility_plus=0.547 eligibility_minus=0.453`

> `CONCEPT_REAL_HOOK_CHECK both_directions_changed_logits=true distinct=true restored_logits=true calls_once=true removed=true diagnostics=true`

> `J_LENS_CONCEPT_PIPELINE_SMOKE_PASS id=j-lens-persona-full-components-tiny-smoke-v16 actual_lens=true generation=true judge=true export=true public_outputs_untouched=true`

The separate basis check records:

> `FULL_RESIDUAL_BASIS_CHECK_PASS projection=full_residual differs_from_gp=true exact_unit_full_signals=true`

Source: [`v16-basis-check.log`](../logs/20260907_j_lens_full_residual/v16-basis-check.log).

## ML-debug form

| row | answer |
|---|---|
| log length and config | 48 lines; tiny random model, float32 CPU, layer 2, full residual, alpha .25 and 1 on both fixed targets |
| `SHOULD:` lines | none in the log |
| null scale | alpha zero is the unchanged-model null; smoke assertions require exact restoration. Tiny random-model judge scores have no semantic interpretation |
| initial state | bare generation completed once; this is an integration test, not learning |
| dummy/baseline | GP16 is the removed-part control. The saved full basis differs from normalized GP16 while all other smoke interfaces are unchanged |
| held-out comparison | not applicable to semantic performance; extraction reports split-full cosine .965/.994 and target eligibility .547/.453 only for the tiny model |
| schedule | no optimizer or schedule |
| full sample | all generated rows are stored under `outputs/experiments/j-lens-persona-full-components-tiny-smoke-v16/`; random-model text is not semantic evidence |
| worst step | no training gradients. The first ad hoc vector-load check omitted the module import needed to register the vector config; rerunning with registration passed. The production smoke had already loaded through the registered experiment path |
| surprising line | 46/60 judge pairs required API calls despite a random-model smoke. Explained: the smoke intentionally exercises judge/export, but this is more expensive than needed for future projection-only tests |
| missing evidence | real-Qwen extraction geometry, coherent DEV generations, judged sign breadth, same-cohort random comparison |
| diagnoses | 65% GP16 discarded transferable residual information; 55% the complete residual still will not transfer because the matched final-prefill mean is context- or wording-specific; 20% target ordering is the wrong causal operator; 8% unobserved implementation bug after the passing basis/hook checks |
| fresh review | pending at smoke completion; its result is recorded separately before the real-Qwen run |
| cheapest discriminator | real-Qwen extraction then the same DEV grid. Intended-sign medians on both sides support GP16 information loss; another null or wrong-sign result moves the failure to the source or target-order operator |
| runtime | 100 seconds total on CPU, dominated by generation and 46 judge calls; the real extraction remains the expensive stage |

## Activity-diagnostic smoke retry

The first calibration-only smoke stopped before generation:

> `ValueError: J-lens extraction cache lens mismatch`

Source: [`v16-activity-calibration-smoke-crash.log`](../logs/20260907_j_lens_full_residual/v16-activity-calibration-smoke-crash.log), complete 21-line log and traceback.

Cause: the tiny source intentionally stores its generated Jacobian lens, while the calibration command omitted `--lens-file` and therefore resolved the repository default. Cache validation rejected the mismatch as intended. No calibration output directory or partial file remained. The retry supplied the source’s exact `tiny_actual_jacobian.pt`; this does not change production defaults.

The retry completed six cells and recorded treated-forward eligibility plus realized changed-position counts. At alpha .25 and 1, `+C` changed all 537 eligible positions, including 9/15 final positions; `-C` changed all 445 eligible positions, including 6/15 final positions. Alpha zero changed none. Sources: [`v16-activity-calibration-smoke.log`](../logs/20260907_j_lens_full_residual/v16-activity-calibration-smoke.log) and [`v16-activity-diagnostics.tsv`](../logs/20260907_j_lens_full_residual/v16-activity-diagnostics.tsv).

## Decision

- Resolve condition: met for the tiny integration test. The full residual, rather than GP16, is the saved basis and the complete pipeline executed.
- Earliest unsupported link: a stable complete residual may still fail to causally transfer the instructed behavior to Bullshit Bench prompts.
- Validity: credible software-path smoke only. It has no semantic result.
- Next action: obtain independent diff review, then extract the complete residual on Qwen3.5-4B with the frozen 65-source split. Only then run the unchanged DEV calibration and blinded judge.
