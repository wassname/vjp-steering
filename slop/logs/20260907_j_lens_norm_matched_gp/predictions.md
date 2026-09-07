# Pointwise norm-matched GP16 DEV15: prelaunch predictions

PI/OpenAI Codex. Approved parent contract slop/handovers/j_lens_v10_norm_matched_gp_authorization.md and scientific decision in previous DEV/science-update/decision.md. Only new adapter magnitude changes; no source fit, layer search, rubric change or new review. Same DEV15 is development data already inspected, not fresh held-out generalization.

Formula at actual current h: nominal GP delta = .5*(t_GP - gap_GP(h))*(B_GP[0]-B_GP[1]). Full reference = BF16(h + BF16(delta_full(h))) - h, using existing probe.replacement. Scale nominal GP direction to reference realized norm, then use same two-rounding residual addition. This is not old GP target achievement, not equal semantic dose, and not matching old full trajectories. Record before coordinates in both bases, nominal GP norm, actual full counterfactual norm, desired and actual matched norm, rounding bound/error, direction cosine, nonfinal identity and independently observed next-block exact input. Zero reference produces zero; zero GP/nonzero reference raises and persists failure, no invented direction. Alpha0 identity bypasses treatment but records counterfactuals.

|option|predicted result|distinction|
|---|---|---|
|selected magnitude control|GP approaches full partial-challenge score without extra damage|smaller prior dose explained some gap|
|source/representation mismatch|same-fiction/weak GP despite larger verified norm|norm alone insufficient,not source defect proven|
|direction-dependent damage|incoherence/refusal/repetition increases|equal norm not equal effective dose,requires calibration|
|own adapter bug|zero/sign/mask/next-block/Gram check fails|mechanical failure before behavioral reading|

Expect30treatments+2newidentity controls,75exact reused reference cells,60new ABBAjudgments. Reference SHA b5ebc369ad048844e64456e1949206af0450383f40c33f891f27b9a47727c985; previous source model revision remains null; current851bf6e pinned. CPU FP64 both signs FP32/BF16 and real tinyhybrid cached controls PASS in cpu.log. Exact source/basis/provenance loaded by existing bridge.sources; no repeating expensive extraction replay from already audited reference.

Exact command after owned source commit:
`PYTHONUNBUFFERED=1 PYTHONPATH=src uv run --no-sync modal run scripts/scratch/j_lens_norm_matched_gp.py::launch`
Full output modal.log. OneH100container,max360s,retries0. Atomic artifact replacement each completed cell; remote logs commit start/end and returns only path. Retrieve existing volume outside remote return:
`uv run --no-sync modal volume get jsteer-pub-cache outputs/audits/20260907_j_lens_norm_matched_gp/generation.json slop/logs/20260907_j_lens_norm_matched_gp/generation.json`
No retry/regeneration without supervisor decision. Estimated successful inference~100s/$0.11 plus startup;360s singleH100 runtime~$0.395 excludes startup/billing. Whole$1.50allocated including judging, unreserved$18.28873536744, failed-startup$5reserve intact. Known API0.60156776256 before test. No further paid experiment authorized. Plot/frontier goal not satisfied by this diagnostic.
