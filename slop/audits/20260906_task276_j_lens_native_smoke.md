# Task 276: paper-native J-lens real-Qwen smoke

— PI/OpenAI Codex

Target: task 276, real-Qwen smoke for the signed paper-native coordinate exchange. Command, timestamps, and label are in [task metadata](../logs/20260906_j_lens_native/task-276-metadata.json). The job succeeded after 399 seconds. Full evidence: [97-line clean pueue log](../logs/20260906_j_lens_native/task-276-clean.log), [raw pueue log](../logs/20260906_j_lens_native/task-276-raw.log), [run log](../../outputs/run_20260906T041511_j_lens_swap_s0_c1p0/run.log), [six generated records](../../outputs/run_20260906T041511_j_lens_swap_s0_c1p0/moral_demos.jsonl), and [resolved artifact](../../outputs/run_20260906T041511_j_lens_swap_s0_c1p0/j_lens_swap.json).

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| extraction | paper raw-basis pseudoinverse exchange at layers 6–24 | operator and 19 well-conditioned bases saved | yes | `operator=paper_native_pseudoinverse_coordinate_swap`; condition numbers 1.24–1.36 | exact source revision | intended operator persisted |
| controls | intervention changes logits and hook removal restores them | both signed applications passed | yes | two `hook_check changed_logits=true restored_logits=true` lines | change magnitude | application is active and reversible |
| generation | bare, +C, and -C complete and persist | 2/2 per side in JSONL | yes | `generation_changes +C=0/2 -C=2/2` | longer responses | real generation path works |
| behavior at alpha 1 | +C may transfer abrasive to flattering; -C may move away | +C equals bare for first eight tokens; -C repeats `abrasive` | mixed | `abrasive` repeated eight times on both -C samples | judged on/off-axis scores | alpha 1 is beyond the useful negative range; positive utility unresolved |
| resolve condition | persist all three sides and finish | `J_LENS_SWAP_MODAL_SMOKE_PASS`, exit 0 | yes | final result block and downloaded artifacts | none for smoke | proceed to dose calibration |

## Chronology and raw result

The run loaded Qwen3.5-4B in BF16 and constructed one raw J-lens basis for token IDs 90474 (`abrasive`) and 80238 (`flattering`). The saved layer condition numbers are modest (1.24–1.36), so numerical rank collapse is not evident.

The direct controls passed twice:

> `hook_check changed_logits=true restored_logits=true`

The first raw response set is preserved in `moral_demos.jsonl`. At alpha +1, both eight-token continuations equal bare. At alpha -1, both are exactly:

> `abrasive abrasive abrasive abrasive abrasive abrasive abrasive abrasive`

This smoke deliberately caps output at eight tokens, so all sides report `unfinished`; that is a smoke-scale artifact, not a calibrated coherence result. The negative repetition is still informative because it appears before truncation.

## ml-debug form

| row | answer |
|---|---|
| log/config | 97/97 clean lines and raw log read; Qwen3.5-4B BF16, layers6–24, C=1, 2 prompts, 8 tokens. |
| SHOULD lines | extraction pair shares suffix; exact benchmark chat input printed; hook change/restoration passed; health reports unfinished on all sides and repetition only on -C. |
| metric scales/null | C=0/bare is the output null. Changed-response count is 0/2 for +C and 2/2 for -C. A random-direction behavioral null is absent. |
| initial demo | full first input and all six outputs are in `moral_demos.jsonl`. |
| dummy/baseline | bare is the direct baseline. +C matches it over the short window; -C is worse by visible repetition. |
| held-out | none; smoke uses first two benchmark rows. |
| schedule | fixed alpha, no optimization. |
| worst step | -C alpha1 repeats one token eight times; no loss/gradient applies. |
| surprise | +C changed logits but no greedy token. Explained: the argmax path remained unchanged over eight positions. |
| missing | full-length outputs, health boundary, on/off-axis judges, random direction, peak GPU memory. |
| diagnoses | H1–H3 below. |
| fresh review | unavailable: subagent registry previously failed with a `goal-worker` name collision. |
| cheapest test | the standard 15-row boundary search, which halves -C below 1 and increases +C until breakdown. |
| wall time/memory | 399 seconds including a Modal final-log timeout; model work ended after about 65 seconds. Peak memory absent. |

## Hypotheses

### H1 [method | Highly Likely | 80%]
- **Mechanism:** alpha -1 amplifies the already active abrasive coordinate and causes lexical repetition.
- **Evidence:** both -C outputs are eight repetitions of `abrasive`; the intervention directly uses that J-lens coordinate.
- **Contrary evidence:** only two prompts and eight tokens were sampled.
- **Discriminating test:** boundary search should recover coherent -C outputs at smaller magnitude; persistent repetition at tiny alpha would suggest broader instability.
- **Fix/action:** calibrate magnitude; do not change the operator.
- **Interpretability:** yes for alpha1 being unsuitable on the negative side.

### H2 [method | Chances a little less than even | 45%]
- **Mechanism:** positive exchange changes internal coordinates but not benchmark behavior.
- **Evidence:** `generation_changes +C=0/2` despite direct logit change.
- **Contrary evidence:** the sample is only two eight-token prefixes; paper-native category tests changed 13/18 targets at alpha2.
- **Discriminating test:** full-length DEV grid with judge scores.
- **Fix/action:** run the planned calibration and do not infer a null from the smoke.
- **Interpretability:** unresolved.

### H3 [bug | Remote | 10%]
- **Mechanism:** saved/loaded vectors or hooks differ from the in-memory operator.
- **Evidence:** this is a new persistence route.
- **Contrary evidence:** vector files saved, both hook controls passed, and outputs changed strongly under -C.
- **Discriminating test:** DEV manifest hashes plus C=0 identity and call counts.
- **Fix/action:** retain provenance and controls in the DEV artifact.
- **Interpretability:** smoke integration is credible.

## Decision

1. **Resolve-condition verdict: met.** The log says `J_LENS_SWAP_MODAL_SMOKE_PASS`; vectors and all six generations persist.
2. **Prediction check:** persistence, logit change, restoration, and three generation paths are supported; useful behavior remains unresolved.
3. **Earliest unsupported link:** a coherent dose with intended judge effect. The DEV boundary search and judged grid test it.
4. **Validity:** invalid means the smoke did not execute the saved native operator through real generation. `P(invalid) ≈ 10%`; credible positive integration smoke, not efficacy evidence.
5. **Highest-information clues:** direct change/restoration controls; six raw records; -C lexical repetition.
6. **Missing metrics:** judged DEV effect/damage, coherence boundary, full-length samples, peak memory.
7. **Bugs requiring changes:** none established by task 276.
8. **Reinterpretation:** `unfinished` is caused by the eight-token smoke cap; alpha1 -C repetition is not.
9. **What would change the verdict:** missing or mismatched vector hashes in DEV would invalidate persistence; coherent intended-sign DEV scores would support efficacy.
10. **Recommended sequence:** run the standard DEV boundary and local grid unchanged; inspect all boundary outputs; run all-100 only for accepted DEV candidates.
