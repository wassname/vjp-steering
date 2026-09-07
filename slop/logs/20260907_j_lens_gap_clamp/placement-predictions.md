# Placement-only comparison, recorded before execution

PI/OpenAI Codex. Parent authorized after completed all-prefill test and36 ordering judgments. No extra review round. Change ONLY new gap clamp mask from all-attended to final-real-prefill position. Same saved basis/dual/source gaps,alpha1,three scenarios,Qwen851bf6e,BF16,batch1,layers13–21,max512,greedy caching. No new vector/dose selection.

Reference: outputs/audits/20260907_j_lens_gap_clamp/results-v1.json (all-prefill generation commit1de151f). Reuse21 original rows only with identical pinned model/settings/source metadata and rendered input/token IDs. Generate6 new rows (gap_final_plus/minus×3); no fresh bare/direct or old-sort generation. Record reference hash and original revision.

Predictions: final-only minus correcting fabrication where all-prefill failed supports earlier-position interference. Both failing despite achieved per-layer final target gaps leaves representation/operator/layer composition unresolved, not unique proof of bad source direction. Hook failure or nonfinal edits invalidate placement claim. Preserve judge rubric/model; judge six comparisons in AB and BA as12 ordering judgments, not12 scenarios.

CPU first: verify alpha0,source gap/sum and final-only mask leaves every earlier position exactly unchanged,each of9 hooks runs once. Actual run records all per-position before/after coords,patch norms,mask,hook counts,final target/error.

Exact command before launch:
`PYTHONUNBUFFERED=1 uv run --no-sync modal run scripts/run_modal.py::j_lens_gap_clamp --placement final --reuse audits/20260907_j_lens_gap_clamp/results-v1.json --output audits/20260907_j_lens_gap_clamp/placement-final-v1.json`

Full log: placement/modal.log. Remote H100 limit900s,estimated <1min model time/~$0.07 plus startup; cost not billed. Incremental cap$2 including judging. Earlier diagnostic reserve$5 covers earlier block only; new$2 reserve is separate,not actual spend. Actual reviews$0.21126463256 leaves conservative unreserved$32.78873536744 with both reserves held. No full/DEV success or publication.
