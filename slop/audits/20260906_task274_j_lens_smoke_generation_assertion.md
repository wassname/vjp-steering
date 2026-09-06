# Task 274: paper-native J-lens smoke reached generation

— PI/OpenAI Codex

Target: task 274, `uv run modal run scripts/run_modal.py::smoke_j_lens_swap`, `/workspace/2026/jspace/j-steer_pub`, 2026-09-06 12:10:25–12:11:11 +0800, exit 1. Relevant committed fix: `40ee2aa`; the log does not print the source revision. Evidence: [complete 168-line clean log](../logs/20260906_j_lens_native/task-274-clean.log), [raw pueue log](../logs/20260906_j_lens_native/task-274-raw.log), [metadata](../logs/20260906_j_lens_native/task-274-metadata.json).

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| model/input | Qwen3.5-4B and two real benchmark prompts | loaded and printed one full prompt | yes | `resolved ... cohort=2/100 ... tokens=8` | source revision | real model path ran |
| extraction | native raw-basis pseudoinverse operator | constructed at layers 6–24 | yes | `operator=paper_native_pseudoinverse_coordinate_swap` | per-layer condition numbers in stdout | intended operator ran |
| persistence | save vectors | passed the point that failed in task 273 | yes | no safetensors error; execution reached hook checks | explicit reload hash | contiguity fix worked |
| intervention | change logits and restore hooks | both vectors changed logits and restored clean logits | yes | two lines: `hook_check changed_logits=true restored_logits=true` | hook count in stdout | operator application is active |
| generation | bare, +C and -C execute | 2/2 generated for each | yes | six generation completion lines | full generated strings were not persisted locally | all generation paths ran |
| smoke assertion | at least one of two eight-token +C strings differs from bare | +C strings were byte-identical to bare | no | `AssertionError` at `assert any(a != b ...)` | token-level logit margin | the test stopped after successful generation |

## Chronology and observed data

The run printed the exact first benchmark input and selected the native operator. Serialization no longer failed. Both interventions passed the direct logit test:

> `04:11:00 | hook_check changed_logits=true restored_logits=true`
>
> `04:11:01 | hook_check changed_logits=true restored_logits=true`

All three generation calls completed:

> `stage=generate side=bare` / `generation 2/2`
>
> `stage=generate side=+C` / `generation 2/2`
>
> `stage=generate side=-C` / `generation 2/2`

The run then stopped at `assert any(a != b for a, b in zip(bare, positive_answers, strict=True))`. This assertion treats unchanged greedy text over two samples and eight tokens as an application failure, although the preceding direct logit check already established that the intervention changed the model and restored it afterward. No scored behavioral result can be inferred from this smoke.

## ml-debug form

| row | answer |
|---|---|
| log/config | 168/168 lines read; Qwen3.5-4B BF16, C=1, layers6–24, two prompts, eight tokens. |
| SHOULD lines | paired prompt suffix matches; benchmark chat prompt printed; both hook checks changed and restored logits. Health SHOULD lines were not reached. |
| null/baseline | C=0 restoration passed inside both hook checks. Greedy-text baseline matched +C for two short samples. No random direction. |
| full sample | full input is in the log; generated strings are missing because the assertion precedes JSONL persistence. |
| dummy/baseline | bare generation ran; only +C equality is known. -C comparison was not reached because assertions are sequential. |
| schedule | not applicable. |
| worst step | post-generation assertion, not model execution. |
| surprise | logits changed but eight-token greedy outputs did not. Explained: argmax tokens can remain unchanged under nonzero logit changes. |
| missing | generated strings, changed-logit magnitude, margins, health stats, vector reload hash, DEV outcomes. |
| cheapest discriminator | log changed-output counts instead of requiring them; retain direct logit identity/change assertion; rerun unchanged model and dose. |
| wall time/memory | 46 seconds; peak GPU memory absent. |

## Hypotheses

### H1 [harness | Highly Likely | 85%]
- **Mechanism:** the smoke uses a brittle behavioral assertion after a stronger direct application check.
- **Evidence:** `changed_logits=true restored_logits=true` precedes an equality assertion on only 2×8 greedy tokens.
- **Contrary evidence:** a useful C=1 intervention would often change at least one short output; no changed-logit magnitude was printed.
- **Discriminating test:** persist outputs and counts without requiring a difference; DEV then measures effect.
- **Fix/action:** replace the assertion with `generation_changes +C=n/N -C=n/N`; keep the direct logit assertion.
- **Interpretability:** yes for integration, no for behavioral utility.

### H2 [method | Chances less than even | 40%]
- **Mechanism:** the lexical coordinates alter logits too weakly to change behavior on benchmark prompts.
- **Evidence:** +C changed zero of two short greedy outputs at α=1.
- **Contrary evidence:** only eight tokens were generated and logit changes were directly observed; earlier category trials changed 13/18 targets at α=2.
- **Discriminating test:** standard boundary search and dose grid with full 512-token responses.
- **Fix/action:** run the predeclared DEV protocol after the smoke persists outputs.
- **Interpretability:** unresolved.

### H3 [bug | Unlikely | 20%]
- **Mechanism:** the old walk path still gives both sides positive α and reversed bases, which are mathematically the same exchange.
- **Evidence:** the task-274 log constructs both `abrasive→flattering` and `flattering→abrasive`; the old walk code special-cased both coefficients as positive.
- **Contrary evidence:** the newer standard experiment path already uses signed α.
- **Discriminating test:** make walk and experiment use one saved basis and ±α; hook checks should then exercise distinct operators.
- **Fix/action:** remove the walk special case and duplicate reverse extraction.
- **Interpretability:** task 274 cannot validate the negative direction.

## Decision

1. **Resolve-condition verdict: not met.** Save and generation completed, but the smoke did not finish.
2. **Predictions:** serialization supported; active/restored hooks supported; smoke completion contradicted; behavioral effect unresolved.
3. **Earliest unsupported link:** persisted generation artifact, blocked by a post-generation assertion.
4. **Validity:** `P(this harness diagnosis is invalid) ≈ 15%`; credible integration progress, inconclusive method evidence.
5. **Highest-information clues:** two direct hook passes; all generation calls completed; the exact assertion location.
6. **Missing metrics:** full response text, ±α change counts, logit-change magnitude, health and judge scores.
7. **Code changes:** H1 → log output changes; H3 → one basis with signed α.
8. **Reinterpretation:** unchanged short greedy text is not proof of an inactive intervention.
9. **What would change the verdict:** unchanged full DEV responses despite material logit changes would raise H2.
10. **Recommended sequence:** align the walk path with signed α, retain direct hook assertions, rerun smoke, then immediately run standard DEV. Do not change tokens or layers.
