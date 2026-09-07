# Dictionary-only control: prelaunch specification

PI/OpenAI Codex. Approved task/native preflight per parent; no independent review launched here. Source: slop/handovers/j_lens_v10_dictionary_control_authorization.md and prior norm-matched science-update/decision.md. This implements exactly one direct-residual dictionary comparison, NOT J-lens success or a public frontier.

## Question and options

Does replacing unit_rows(lm_head @ J17) with unit_rows(lm_head), under the same norm-matched persistent adapter, change sparse-direction orientation and behavior? All52 original fit signals,16 nonnegative pursuit iterations,layer17,rank2row-normalizedbasis,source IDs/split/persona instructions,DEV15both signs,BF16/batch1,greedy512 and judge are fixed. Only dictionary changes; NEW basis requires NEW13source-only target means. No existing numerical GP target reused. No evaluation responses/judgments used to construct either component or target. Historical model revision remains unknown; current pinned851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a.

|option|predicted metric|separation|
|---|---|---|
|direct residual dictionary (selected)|orientation and on/off-axis effects|same16atoms/source/normadapter;isolates dictionary construction conditionally|
|source/task repair (not run)|factual-premise content|would confound this dictionary comparison|
|dose/layer/k sweep (not run)|magnitude/damage|not needed for this fixed control|

Pseudocode: dictionary=unit_rows(lm_head); component_side=GP16(saved_full_signal_side,dictionary); B=unit_rows(stack(components)); D=pinv(B).T; new_target_side=mean(source13_side@D.T)[0]-mean(...)[1]. On each actual current state h, apply nominal_GP_delta/||nominal_GP_delta|| * ||BF16_full_counterfactual_delta(h)||. For zeroGP/nonzeroreference stop arm;zero reference applieszero. No coefficient/layer selection. Padded head vocabulary rows retained exactly as old dictionary: local tokenizer length248077 versus model head248320, not a vocabulary mask.

## Contrasting predictions

1. PlainGP closer to full and retains partial challenge with less florid damage: transport-derived dictionary contributes conditionally, not proof J-lens globally wrong or complete correction.
2. PlainGP similarly damaged or weak while checks pass: transport-only repair insufficient; generic compression/source construct/context remain. Do not infer defective donor uniquely.
3. New minus correction on previously wrong items: motivates broader source-construction investigation, but preserve continuous fixed benchmark scores and reused DEV selection limits;not final success.
4. Rank/support/calibration/call/mask failure: own-code first, no judging invalid data. Wrong token index would fail permutation/support reconstruction tests. Changed comparator norm does not imply same autoregressive dose history.

Null/control scale: alpha0 identical baseline IDs/zero update expected;achieved norm matches full-reference within BF16rounding bound,not arbitrarybehavioralcriterion. Basis/dual independentFP64checks;actualsource replay of original representations keeps prior error<.1 gate. This engineering gate is not exacthistoricalparity;record allerrors. Judge range[-5,5]perresponse,contrast[-10,10],minusdisplaynegated. Previous matchedGPminusAB-.14/BA-1.56;plus1.853/3.887,offaxisplus1.49. No new acceptance cutoff chosen.

Three ways an apparent improvement could be false: rubric rewards implicit usability denial (read full paired text);different trajectories create different actual doses (save every call);new source replay alters geometry beyond dictionary (same masks/source, save states and old-coordinate replay errors). Failing this one dictionary does not rule out different sources/layers or paper-native designs.

## Execution and safeguards

CPU exact reused normadapter tests FP64/BF16bothsigns,zeroexception,zero-reference,real hybridQwen cached generation identity and next-block/nonfinal/cleanup. New dictionary synthetic test checks support permutation mapping,reconstruction and FP64dual/rank,plus/minusalpha0. Remote actualdictionary uses allheadrows and verifies selected index normalization independently;39source replay inputs use saved padded tokenIDs,attention masks,finalpositions. Save full source states/newcoords/means and reference errors. No modelweights fitting.

One max_containers1,timeout360s,retries0 Modal call. Source replay then30newtreatments+2identity controls,105prioroutputs hash-reused. Cells persist atomically after each generation. Remote returns only path after volume commit;download separately,never regenerate because download fails. Sixty fixed-rubric AB/BA judgments. No extra review/run authorized.

Exact launch command:
`PYTHONUNBUFFERED=1 PYTHONPATH=src uv run --no-sync modal run scripts/scratch/j_lens_dictionary_control.py::launch`
Log: modal.log. Download:
`uv run --no-sync modal volume get jsteer-pub-cache outputs/audits/20260907_j_lens_dictionary_control/generation.json slop/logs/20260907_j_lens_dictionary_control/generation.json`

Budget1.50 inclusive;historical failedstartup5reserve remains. Globalunreserved16.28873536744 afterthisallocation;priorAPI.80169945256. Expectedwork~120s=$.132H100at3.95/hour plusjudging~.01;360soneH100time$.395notinvoice. Unknownstartup/billing remains reserved,notzero. No retry/extraexperiment withoutparentdecision.
