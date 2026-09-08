# V10 placement comparison authorized and delegated

PI/OpenAI Codex. User autonomous approval and $40 total cap remain in force. Supervisor explicitly requests execution, not another proposal.

Active native worker: c302a4eb-2f29-44d6-a520-0bc002b7d3b7. Steering delivered request e1dbce99-1146-4a8e-96d1-63880ec032ff extends its live task through actual placement run. Native completion notification already attached. Do not start a second writer or duplicate run. Worker will write exact command before Modal and finalize after results. Launch itself not yet observed by parent.

## Fixed experiment

Same saved v16 full-residual directions, source-derived target gaps, alpha1, layers13-21, pinned Qwen851bf6e, BF16, batch1, same3 questions and greedy512-token decoding. Change ONLY application mask: all attended prefill versus final real prefill position. Compare both directions. Existing bare/direct controls may be reused only after provenance/settings match; don't call them newly generated. Record actual per-position patch norms, masks, hook counts, achieved gaps and complete responses.

CPU mask check before commit/run. Incremental cap$2 including Modal and any judging. Existing rubric unchanged; inspect text because parent paired audit establishes judge inconsistency. Save full log/artifact and precise cost/runtime before further work.

## Predicted outcomes and limits

- Final-only corrects fiction while all-prefill fails: supports earlier-position interference under this execution.
- Both masks achieve intended coordinates but neither corrects: placement alone insufficient. Does NOT uniquely prove source-representation defect; operator, source, layer composition and nonlinear interactions remain possible.
- Actual hooks/mask/target check fails: implementation problem, diagnose before behavioral inference.

This is3-question diagnosis, not DEV15 success, no full run or public success claim. Main goal remains SAME comparison plot and tables, working both directions, then full confirmation.

## Evidence carried forward

Previous successful app ap-YnD3TdOT6OO5Frxqo07g4d:21 responses,64.211080087s H100 workload. Old minus final0/27, gap minus27/27 reported by worker; parent raw texts retain fiction on all3 gap-minus questions; direct-minus corrects all3. Parent independently checked all18 paired judgments (AB/BA36 orderings),2 strict reversals3 tie disagreements, no sign/order mapping defect. Full table+CSN texts: slop/logs/20260907_j_lens_gap_clamp/parent-ordering-audit.md.

Reported API subtotal$0.21675891256 before new calls. $39.78324108744 before Modal billing; prior successful workload estimate~$0.07045 excludes first failed launch/startup. Actual invoices unavailable. Conservatively reserve prior test$5 plus new$2 and reviews$2 => at least$31 of40 outside reservations. Reconcile actuals, do not count reservations as spend.

On native completion, read actual placement log and complete responses, compare predictions, update budget, then choose next repair toward real J-lens DEV. Do not stop because a diagnostic ended.
