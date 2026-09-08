# J-lens factual-to-style mismatch: scientist memo

Question: what does the local factual control establish, why did the fixed-token style run not produce a usable monotone effect, and which measurement best separates the remaining explanations?

Scope: review of the supplied paper excerpts, neutral pseudocode, Qwen country diagnostic, and DEV-15 style outcomes. No code, plot, model run, or result file was changed. This is not a replication of the paper and does not select a new intervention.

## Review procedure

- comprehension: GLM 5.3 Flash pilot; a corrected DeepSeek V4 Pro call is incomplete, then Inkling completed the corrected cold read;
- independent pass: GLM 5.3 Flash, DeepSeek V4 Pro, and Kimi K3, three model families from the same pseudocode and evidence;
- seminar: one GLM 5.3 Flash pass read the other independent reports with the same source attachments;
- pass cap: one independent pass and one seminar pass. No second seminar was run because the seminar converted the material disagreements into source-resolvable measurements rather than leaving a competing claim that another discussion could resolve;
- protocol: every call used `pirev`. GLM's independent response reached the output bound and `pirev` completed its documented same-model final-answer fallback. No model or review-protocol substitution was used for completed calls.

The incomplete DeepSeek comprehension trace contains a request and response chunks but no `phase_complete` or `outcome`; its Markdown ends during reasoning. It is retained as incomplete evidence and is not counted as a completed comprehension report. Inkling's corrected report has `finish_reason=stop` and `outcome=complete`.

## Observations

These are in the supplied source or recorded results, not reviewer diagnoses.

1. The paper conditions its token-coordinate intervention on source activity:

   > “For each prompt, we first confirm that the intermediate concept appears in the J-lens at intermediate model layers.”

   It uses raw pseudoinverse coordinates, a prompt-specific spontaneously chosen source, and a same-category target. The separate 100-baseline, top-16 construction is a concept-vector decomposition, not that token swap.

2. The local country diagnostic uses Qwen3.5-4B and two country/capital pairs over three layer bands. At α=1 and 2, directed unit transfer gives 6/6 target answers; raw and unit symmetric coordinate exchange give 0/6. The diagnostic did not apply the paper's source-activity criterion.

3. The style run is a different intervention: one fixed single-token pair (`abrasive↔flattering`), directed unit transfer, layers 6–24 at all prompt-prefill positions, and no prompt-specific source-activity check.

4. DEV-15 selected +C α=1.25 at effect `+0.120`, damage `0.073`, and -C α=3 at `-0.280`, `0.307`. Lower-dose effects are small, non-monotone, or wrong-sign. At α=4–8, damage is `3.93–4.61`; raw outputs repeat the literal token, including:

   > `flattering the flattering the flattering [...]`

   Both semantic directions emit `flattering` at high α.

5. The supplied packet does not contain per-prompt source-coordinate magnitudes, direction norms/cosines, a held-out style result, or judge-repeatability evidence.

## Inferences and disagreements

All three independent families rejected the broad conclusion “J-lens fails on style.” Their common narrower reading is that the local style run does not test the paper's token-coordinate claim under its stated precondition.

- GLM independently emphasized the missing source-activity measurement, the operator algebra, fixed lexical pair, and the paper's separate concept-vector construction. Its strongest inference was that the fixed style token is probably a poor or inactive proxy. It also noted that signed source coordinates could reverse a directed patch at some positions. This remains unmeasured.
- DeepSeek independently made the most cautious claim: small judged effects plus high-dose repetition do not establish either successful style transfer or absence of a style representation. It prioritized source activity, held-out/paraphrase tests, and direction geometry.
- Kimi independently emphasized constant-bias injection, judge sensitivity to literal tokens, and an effect/activity correlation. It called high-dose leakage strong evidence for lexical forcing, but that causal label is more confident than the source supports.
- The GLM seminar objected to treating the style run as a paper replication at all. It also separated two changes that the 0/6 versus 6/6 operator comparison confounds: normalization and exchange-versus-directed coefficient choice. This answered the main source-resolvable disagreement: the country result validates a narrow answer-redirecting operator on a small factual diagnostic, not the paper's operator or a style mechanism.

The seminar did not resolve the cause of high-dose `flattering` in both directions. Token-logit forcing, signed/baseline source projections, direction geometry, and broad repeated patching make different empirical bets. A second discussion pass would repeat these bets without new source measurements.

## Hypotheses and bets

| Hypothesis | Evidence now | Distinguishing observation | What would disfavor it | Origin / objection |
|---|---|---|---|---|
| The paper's source-activity precondition fails for the fixed style tokens. | The check is absent; the paper says failed swaps concentrate where the source vector “was not strongly active.” | Clean-prompt `h·d_source` is near a token-direction null on most prompts/layers and does not track desired behavior. | Strong prompt-consistent activity that predicts per-prompt effect. | GLM independent; DeepSeek and Kimi agreed. Seminar reframed this as a validity condition, not a diagnosis. |
| The directed edit acts mainly as lexical/token-logit forcing. | `v(token)` is decoder-derived; high α emits literal `flattering` repeatedly in both directions. | First-token/logit changes concentrate on the pair's lexical neighborhood; matched irrelevant tokens show a similar dose cliff. | Held-out style changes remain after controlling literal-token probability and without leakage. | DeepSeek and Kimi; GLM independently derived the token-logit prediction. Seminar objected that the -C `flattering` leak is not explained by a simple target-only story. |
| Operator geometry explains the factual swap/direct discrepancy. | Raw/unit symmetric exchange is 0/6 while directed unit transfer is 6/6 in the same lens pair span. | `c_source-c_target`, vector norms/cosines, and condition numbers show contrast cancellation or unstable scaling; a raw-directed comparison separates normalization from coefficient choice. | Geometry is well-conditioned and norm-matched operators retain the same categorical difference. | GLM and Kimi independently; seminar made the normalization-versus-exchange confound explicit. |
| Repeated all-position, multi-layer patching causes an off-manifold dose cliff. | Layers 6–24 and every prefill position are patched; damage jumps to 3.93+ at α≥4. | Patched activation norms or source-coordinate signs become unstable across layers near the observed cliff; a localized application avoids the cliff at matched effect. | The same collapse occurs from one validated position/layer with modest activation displacement. | GLM independent; DeepSeek called it all-layer compounding. |
| A weak real style channel exists at low dose. | Selected signs are intended at +C 1.25 and -C 3.00. | Pre-registered doses reproduce on held-out prompts with judge repeats and a semantic effect not explained by token occurrence. | Effects vanish, reverse, or remain below judge-repeat variability. | DeepSeek preserved this possibility; GLM noted -C as the strongest objection to a pure-null reading. |
| Style is distributed across several J-lens vectors or outside J-space. | The paper explicitly distinguishes diffuse abstract concepts and its top-16 concept decomposition; the local run uses one token per side. | A measured style concept vector has weak single-token alignment but a stable multi-vector J component or substantial non-J remainder. | One token direction is strongly active and reliably mediates held-out style behavior. | All three independent reports; no reviewer treated this as already shown. |
| Judge lexical sensitivity inflates apparent effect. | Judge procedure and repeatability are absent; high-dose outputs contain the evaluation word itself. | Rejudging semantically equivalent, token-controlled responses changes the measured effect materially. | Independent blinded judges agree after lexical controls. | Kimi first emphasized this in the independent pass; DeepSeek listed it as missing evidence; seminar retained it as a live control. |

## Next measurement

Run one passive geometry/activity dump on the existing clean DEV-15 prompts before another intervention:

- per layer and prompt position, record `h·d_source` and `h·d_target` for both directions;
- record their signs, token-vector norms, pairwise cosine, and symmetric-pair condition number;
- compare source coordinates with a null distribution of matched token directions and with the already recorded per-prompt effect.

This is useful before a new style run because it tests the paper's required precondition and the directed operator's effective dose from the same forward pass. Weak/null source activity would show that the fixed-token experiment did not contain a source representation to transfer. Strong activity with poor effect prediction would shift attention to operator geometry, patch locus, or judge validity. Large signed baseline projections or poor conditioning would explain why the current α is not a comparable semantic dose. No arbitrary correlation threshold is justified by the current n=15 packet.

## Parent decisions

No new parent decision is encoded here. The existing no-full decision remains supported by the observed small, non-monotone DEV effects and high-dose degeneration. Goal 10 remains active for supervisor review and sign-off.

## Artifacts

Source:

- [neutral pseudocode](../../docs/pseudocode/j_lens_style_transfer_moa.py)
- [primary evidence](20260905_j_lens_style_moa_primary_evidence.md)

Comprehension:

- [GLM pilot](2026-09-05_glm-5.3-flash_j-lens-style-comprehension-pilot.md) · [trace](2026-09-05_glm-5.3-flash_j-lens-style-comprehension-pilot.trace.jsonl)
- [DeepSeek corrected attempt, incomplete](2026-09-05_deepseek-v4-pro-0813_j-lens-style-corrected-comprehension.md) · [trace](2026-09-05_deepseek-v4-pro-0813_j-lens-style-corrected-comprehension.trace.jsonl)
- [Inkling corrected comprehension](2026-09-05_inkling_j-lens-style-corrected-comprehension.md) · [trace](2026-09-05_inkling_j-lens-style-corrected-comprehension.trace.jsonl)

Independent reports:

- [GLM 5.3 Flash](2026-09-05_glm-5.3-flash_j-lens-style-independent-scientist.md) · [trace](2026-09-05_glm-5.3-flash_j-lens-style-independent-scientist.trace.jsonl)
- [DeepSeek V4 Pro](2026-09-05_deepseek-v4-pro-0813_j-lens-style-independent-scientist.md) · [trace](2026-09-05_deepseek-v4-pro-0813_j-lens-style-independent-scientist.trace.jsonl)
- [Kimi K3](2026-09-05_kimi-k3_j-lens-style-independent-scientist.md) · [trace](2026-09-05_kimi-k3_j-lens-style-independent-scientist.trace.jsonl)

Seminar:

- [GLM seminar](2026-09-05_glm-5.3-flash_j-lens-style-seminar.md) · [trace](2026-09-05_glm-5.3-flash_j-lens-style-seminar.trace.jsonl)

— PI/OpenAI Codex
