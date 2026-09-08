# Projection-removal execution decision

PI/OpenAI Codex, 2026-09-07. Both v10 goals remain open.

Parent read precheck-attempt1.log and inspected the actual launch path. Sole owner is worker b2b4fe93-7919-41fb-99ea-03b39d92b8b6, currently finishing offline evidence. Native completion notification is attached to that run.

## Decision and evidence

Authorize ONE minus-only DEV15 projection-removal test after the worker commits the passing precheck and confirms regression checks. No automatic retry. Equation: h' = h - u(u^T h), u the unit saved GP(sycophancy) component; removal fraction 1, layer17, persistent current position. Fixed model, prompts, decoding and judge rubric.

Non-Claude decision d16e9491-8070-4820-89e4-0138e8978301 supports this conditional test. Paper excerpt at slop/logs/20260907_j_lens_dictionary_control/science-update/paper-evidence.md, line174, explicitly distinguishes negative addition from projecting out the component entirely. This is a behavioral extension, not a reproduced paper result.

Observed log: `ACTUAL_RUNNER_ROUTE_PASS 15minus+1identity; old additive poisoned; fixture generation is not behavioral evidence`, `IMMUTABLE_HASHES_PASS 41`, `EXIT_CODE=0`.

Source SHA 9b47dcb594efc67f9b3491013273106346a0afb8c32fea3a6111e6121ca34a53. Three bare coordinates .241138685/.288525146/.064327552 versus prior subtraction magnitude 2.886455. On 102 source plus 3 bare states, all105 removal updates nonzero; delivered norm min/median/max .000155679/.379674733/1.461278677. Maximum residual coordinate .004852681 and orthogonal rounding change .020534664. BF16 removal is NOT exact zero. These are offline states, not DEV decode delivery.

## Predictions

If oversubtraction contributes, removing the coordinate without forcing it strongly negative should reduce adverse responses across scenarios, not just TCA. If semantic transfer fails, measured removal can pass while behavior stays null/adverse. If improvements arise mainly from unchanged-baseline rescoring, the saved decomposition should expose that. Actual per-call residuals, orthogonal errors, identity and next-block checks distinguish delivery defects. Smaller norms mean existing constant-dose random controls are NOT matched controls for this test.

## Command and scope

`PYTHONUNBUFFERED=1 PYTHONPATH=src uv run --no-sync modal run scripts/scratch/j_lens_additive_concepts.py::launch --projection-removal`

One container, H100, timeout360, retries0. Save 15 minus responses +1 identity and 30 unchanged AB/BA judgments. Read complete responses and raw judgments, preserve old scores, save baseline/steered attribution against prior subtraction. No positive arm, source fit, sweep or further experiment.

## Budget

Reserve $0.60 generation plus judging from $2.61988872744: remaining unreserved $2.01988872744. Allocation includes estimated360s H100 $0.39492 and $0.20508 startup/judging/other allowance; this is not an invoice or hard startup bound. Preserve all prior unknown-charge reserves. Stop if this allowance is threatened; do not retry or treat unknown billing as zero. Cumulative reported API before launch remains $1.08106749412.

## Actual launch confirmed

Parent inspected the live saved modal.log and native task status. App `ap-1Arwmij0hs19R8fo5PCFy8` initialized: `https://modal.com/apps/wassname/main/ap-1Arwmij0hs19R8fo5PCFy8`; latest observed line `Created function remote.` Source/precheck commit ffb65ae is pushed. Exact launched command additionally sets OMP_NUM_THREADS=1. Log: `slop/logs/20260907_j_lens_projection_removal/modal.log`.

Sole owner b2b4fe93-7919-41fb-99ea-03b39d92b8b6 remains running, process terminal pending. Its native async completion notification is retained; no duplicate launch or separate polling process. App initialization is confirmed, inference completion is not yet observed. The $0.60 cap and no-retry rule remain unchanged.

## Generation completion and judging correction

Worker reports app EXIT0, all16 responses downloaded, runtime52.6105s H100. Judging stopped before API calls at the shared helper's 30-treatment assertion; this minus-only artifact contains15. Parent approved only a projection-specific cardinality correction plus offline scenario/side/identity and unchanged-request checks, then the original30ABBA calls. Preserve failed judge.log. No GPU retry or extra allocation. Supervisor reply c41a8aa3-e70a-44c9-83cb-e92caae3caf0 delivered to the same sole owner.

## Audit collection and display continuation

Parent independently reconstructed all30 new raw judgments against old single-concept judgments. `parent-attribution-verified.log` reports baseline -0.2833333333, steered +0.1433333333, total change -0.14, new effect +0.04. Initial parent assertion incorrectly expected parsed dictionaries to omit derived contrast fields; failed log retained, corrected check validates every raw field without discarding parsed extras. No scores changed.

Same sole worker is authorized offline display addition of this failed minus point, preserving38 existing points and historical rows, with explicit state-dependent/non-norm-matched limitations. Non-Claude oracle a529a256-ca0b-45f9-b2f2-1a1ceb5cd072 is running a read-only next-decision review; native completion active, managed output slop/reviews/j_lens_v10_projection_next_decision.md. No further paid work authorized. Unreserved $2.01988872744; prior reservations unchanged.

## Completed scientific decision

Non-Claude oracle a529a256-ca0b-45f9-b2f2-1a1ceb5cd072 independently verified all30 raw mappings and baseline identities: new +0.04, old +0.18, baseline contribution -0.283333, steered +0.143333. It read all15 complete comparisons and found no supported next paid repair. Recommendation: finish failed-point display, retain remaining funds, no further paid variants on this branch without independent evidence of a missing mechanism. Paper line174 supports projection removal but not behavioral transfer. This is a pause in paid experimentation, NOT goal completion or evidence that J-lens cannot work generally.

Saved review: /home/code/.pi/agent/sessions/--workspace-2026-jspace-j-steer_pub--/subagent-artifacts/outputs/a529a256-ca0b-45f9-b2f2-1a1ceb5cd072/slop/reviews/j_lens_v10_projection_next_decision.md. Additional paid cap $0; $2.01988872744 remains unreserved, all prior reserves retained. Display worker remains sole owner; collect its verification and final commit next.

## Completion action

Collect actual app ID and full log on native progress/completion. Read generation, online delivery, all30 judgments and cost evidence. Keep the existing38-point results unchanged until new evidence is audited and explicitly labeled; neither mechanics nor a minus-only improvement completes either goal.
