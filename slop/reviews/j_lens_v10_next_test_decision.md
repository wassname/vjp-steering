# V10 next bounded experiment

PI/OpenAI Codex. Parent decision, not reviewer consensus. Reviews: j_lens_v10_scientist_{glm,deepseek,kimi}.md and one seminar pass. All three discussion outputs read. DeepSeek's final answer cuts off during its judge assessment despite provider stop and runner completed_after_follow_up; it is partial evidence, not a completed judge verdict. No further review round planned. It emphasizes sequential-layer interactions and source/application-position mismatch; the selected test logs actual treated final-position gaps at every hook to avoid clean-prepass inference. Completed review spend: $0.21126463256; $39.78873536744 remains before the $5 test reservation.

## Evidence and decision

Task461 audit, slop/audits/20260907_task461_j_lens_full_residual_calibration.md:
> “`-C` changes no final prefill position at any dose, but changes 12/15 outputs through earlier-position pathways.”
> “`-C` changes 1,323/8,829, only at layers 13, 14, and 18.”

Actual c670930 concept_patch uses c=h@dual.T, target_coordinates=component_target_coordinates(c,target), delta=(target_coordinates-c)@basis. component_target_coordinates puts max(c) at target. For minus, eligibility is c1<c0. If c1>=c0, delta=0 regardless of alpha. CPU replay verified actual saved-vector mapping and hook execution, not semantic transfer.

Kimi independent review proposes distribution-matched target values; DeepSeek questions transfer/construction; their source activity/coordinate questions motivate this bounded test. GLM/Kimi seminar do not accept the two flagged pairs as proof of general judge defect. Parent disagrees with their claim that TCA response fully names fabrication: it retains “as it is primarily used to measure coupling strength”. Decision: near-zero legal score is consistent; -7.7 magnitude is not trustworthy proof of full correction. No global arithmetic/rubric defect established. Keep judge/rubric fixed; inspect complete responses and per-response scores, and do not use that outlier alone as success.

## Single operator change

Keep saved v16 full-residual basis/dual, layers13-21, attended-prefill mask, BF16 model, tokenizer, and cached greedy generation. Use batch1 for all compared conditions. Replace target sorting with a source-calibrated coordinate-gap replacement:

- g=c0-c1; m=(c0+c1)/2.
- g_target = mean source-heldout c0 - mean source-heldout c1 for the requested persona, fixed before DEV.
- desired=(m+g_target/2, m-g_target/2).
- h_new=h+alpha*(desired-c)@basis, alpha=1.

This preserves coordinate sum; changes only coordinate gap target. It can edit an already ordered but weak state. Source means are from saved extraction metadata, not selected on DEV outcomes. Observed layer13 means: positive[4.057392120361328,-0.4992178976535797], negative[-1.0265229940414429,3.6704108715057373], baseline[-0.9738060235977173,-0.4862443208694458]. Verify all layers before use. This is a source-calibrated clamping diagnostic inspired by paper coordinate clamping, NOT a claimed faithful paper swap or a final J-lens method.

## Smallest test and predictions

Three fixed diagnostic scenarios: leg_pnf_01, sw_pnf_02, sw_pnf_03 (chosen to examine saved failure/outlier, not unbiased DEV confirmation). Compare bare, old sort +/-, new gap +/-, and direct persona instructions +/- with the same output settings. Alpha0 exact identity CPU check; synthetic gap-target and sum-preservation checks first. Save all21 responses plus per-layer final/whole-prefill activity and actual target-gap error.

- Ordering suppresses needed intervention: old minus final delta remains0; new minus reaches target gap with nonzero final patch, and improves explicit fabrication correction relative to old minus/bare. Plus moves in opposite semantic direction where baseline permits it.
- Wrong/noncausal source direction: new clamp reaches target gap but responses remain unchanged, worsen, or track wrong persona; direct instruction still changes behavior.
- Runtime defect: target-gap/hook/alpha0 checks fail. Diagnose before interpreting generated text.
- Judge issue: unchanged rubric gives large effects unsupported by complete responses. Preserve scores, flag them, and do not declare success.

## Cost / execution

Reviews reserved $2 of $40; completed reported spend previously $0.097265405 plus pending review usage. First Modal diagnostic cap $5 (H100, hard remote runtime <=15min, roughly $1 GPU plus startup);21 responses and bounded judging expected below $2, estimate not billed fact. At least $33 remains after both conservative reservations. Worker must save exact CLI and predicted test inventory BEFORE launching, full log and artifacts after, then usage/runtime cost. No full-cohort run or publication based on this three-scenario test. Parent-owned worker will implement and run this bounded test; do not stop at preparation.
