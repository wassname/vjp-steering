# Complete generation recovered; small calibration replay shift, no update sign changes

PI/OpenAI Codex. Executed3a1b921;app ap-bCPr0KrKBwsaTUFLD0W0Rp. Judging PAUSED pending parent release. No regeneration.

|stage|expected|observed|expected?|consequence|
|---|---|---|---|---|
|source IDs/split|original52fit/13calib,noDEVoverlap|all65raw-ID hashes exact;3group intersections empty|yes|no target-label/DEVresponse use|
|tokenizer|historical extraction hash|default tokenizer exact0ef9d092;195source tokenlists exact|yes after corrected retry|initial generation-pad bug retained|
|dictionary/GP|same lens/vocab/unit rows,pursuit supports/components|both exactsupports,component_max_error0|yes|actualJ-GP16construction reproduced|
|calibration numerical replay|pre-existing maximum-coordinate gate .1|max.0818615full/.0257723GP|yes but not exact|batch shape differs;impact analyzed below|
|DEV generation|75fixedcells+2identities|75log/artifactmatches,3937treated steps,2exact55-token identities|yes|complete cohort available|
|remote return|download through function|360stimeout AFTER DEV15_COMPLETE245.513s|no|wrapper/return failure,not incomplete inference|
|recovery|existing volume artifact only|modal volume get EXIT0,all75cells,missing[]|yes|no duplicate paidrun|
|judging|120unchangedABBA|not run by supervisor pause|pending|no behavioral verdict yet|

## Timeout and recovery evidence

modal-retry.log includes:
> DEV15_COMPLETE {"seconds": 245.513383215, "gpu": "NVIDIA H100 80GB HBM3", "peak_memory_bytes": 18085427712, "torch": "2.13.0+cu130"}

Then:
> in-01M1YC817EA71AJ4M9431NQQ5R:1788799616238-0 hit its timeout of 360s

The precise blocked return/commit substage is not instrumented;do not claim cache.commit alone caused the timeout. generation.json downloaded from existing jsteer-pub-cache volume;recovery.log records full command and EXIT0. Hash b5ebc369ad048844e64456e1949206af0450383f40c33f891f27b9a47727c985. Offline replay-impact.py validates exact15x5coverage,no duplicate/missingcells,75raw logtexts equal artifact,executed sourcehash7d78f14093354fbc698cc7b9d3ea13e0d70ff13a5ab2c3fc365efdaa028c7dc5,finite values and all3937requiredcall/mask/nextblock/targetfields. This is not recovery from text-only logs;all per-call arrays persisted.

## Pre-existing acceptance gate, not relaxed

Executed3a1b921 function metrology:
> assert error < .1, (name,condition,error)

The bound was recorded in predictions.md BEFORE first launch at2df01cd. It was an engineering gate,not proof of identical states or empirical behavioral insignificance. All target gaps remained ORIGINAL saved means throughout. No source/tolerance changes after outcomes.

## Exact masks and source order

Historical task460 audit slop/audits/20260907_task460_j_lens_full_residual_extraction.md:7–9 records executed e9877a2 and CLI without a batch override. e9877a2:scripts/run_modal.py:350–368 defaults extract_batch_size8 and forwards it; scripts/experiment.py:310 supplies that to extract_persona_components;residuals uses padded batches of8. This is recovered command/default evidence,not a separately saved resolved argv.

Replay executed3a1b921 constructs BOTH input_ids AND attention_mask from each saved token_record,shape[1,original_padded_length],calls model.model(use_cache=False),reads saved final_position. It is NOT unpadded batch1 and NOT identical original batching. replay-masks.json records every39sourcecalibration ID,ordinal,original batch start/shape,replay shape,fulltokenIDs/fullmask,valid/padlength and finalposition. All39right masks are contiguousones thenzeros,padded tokens exactly248044,finalposition=sum(mask)-1. 34/39contain padding. Shapes[1,52/57/60/72/75/91/99/103/114],original corresponding[8,samewidth]. Nomask reconstructed from EOS or dropped. Source order positive52:65,negative52:65,baseline52:65 retains original condition-major ordinals. Original extraction fit first52;targets from last13 only.

Observed:calibration coordinates differ. Inference:BF16batch/kernel shape differences are a plausible cause,not proven by this one replay. No controlled samebatch replay was run. Historical model_revision remains null;current snapshot851bf6e is pinned and path saved. Lens/dictionary exactness does not prove all historical hiddenstates identical.

## Offline target-impact table

Each replay mean computed independently from recalculated source coordinates. Max individual coordinate error is a DIFFERENT metric from target-mean shift.

|representation/sign|frozen target|replay mean gap|absolute shift|relative target shift|max coordinate error|update-vector delta norm|calls|strict sign flips|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|full+|8.476953745|8.469267845|.007685900|.090668%|.081861496|.004681897|946|0|
|full−|-7.554213405|-7.571987391|.017773986|.235286%|.075272083|.010827097|987|0|
|GP+|5.802844048|5.800201654|.002642393|.045536%|.023713589|.001285558|1055|0|
|GP−|-2.479270399|-2.493925750|.014655352|.591116%|.025772333|.007130015|949|0|

At each actual recorded prepatch gap g,compare sign(frozen_target−g) versus sign(replay_target−g). No flips,no exactlyzeroactualupdates,no zero signedshifts,and no actualpatchnorm<=the corresponding target-shift update norm. Thus no near-zero/sign-flip subset exists;its quantiles correctly have count0 rather than invented zeros.

The unrounded linear update difference at FIXED actual h is exactly .5*(replay_target−frozen_target)*(B0−B1). Saved measured BF16actualupdate norms are denominators,not replaced by nominal dose. target-impact-steps.json includes all3937counterfactuals,actualnorms,analytic frozen/replaynorms,absolute magnitude differences and explicit zero handling. This is a fixed-state analytic sensitivity,not actual regenerated BF16trajectories;rounding/argmax changes could amplify a small shift.

|representation/sign|actualnorm median|max|delta/actual median|q95|max|
|---|---:|---:|---:|---:|---:|
|full+|5.645744|6.653973|.082924%|.089698%|.103503%|
|full−|3.978192|5.137379|.272161%|.302625%|.347962%|
|GP+|2.754957|3.760935|.046663%|.056735%|.074951%|
|GP−|1.124482|1.878415|.634071%|1.156956%|2.915375%|

Fullmin/q25/median/q75/q95/max statistics,absolute magnitude differences,and explicit emptyflip subsets are preserved in target-impact.json. Offlinefirstattempt compared tinyCPU/remoteFP64diagnostic floats for exact equality and failed;corrected to exact immutablehashes/IDs/targets while retaining numericalchecks. Both logs saved;this changes no inference/source/tolerance.

## Validity recommendation

Recommend release judging of the EXISTING75cells as the frozen historical-target DEVdiagnostic,with replay/batching caveat. Evidence of materially corrupted intervention is weak:all75complete,GPconstructionexact,3937callsfinite/verified,0signchanges,and fixed-state update differences small relative to observednorms. This does NOT prove counterfactual replay-target generations would match,or erase unknown historical modelrevision. Probability of major mechanical invalidity roughly10%(subjective);against:checks above;for:BF16/history uncertainty. Measurement misinterpretation remains likely80%given prior same-rubric fictional-use denials. Broadmethod-generalization remains unknown untilscores/texts read;no positive claim yet.

No new GPU needed. Cheapest next step is unchanged120ABBAjudgments on recoveredartifact,not changingtargets/regenerating. If accepted later integrate robust checkpoint download outside remote return and separate metrology/serialization timing before anotherGPUrun;that wrapper repair would not alter this dataset.

## Spending

Generation work245.513s =>estimatedH100$0.269383 at3.95/hr,notinvoice. Entire retry360sfunction bound=>$0.395singleH100runtime allocation,plusstartupplatformunknown. Local log~471.46swall is not GPUwork. Firstfailure42.84swall estimate.047notinvoice,reserve.50. Keep wholeoriginal3allocationpendingbilling,globalunreserved20.28873536744. Nojudgesyet. Nozero-costclaimforfailedapps,noextrareserveorpaidexecution.
