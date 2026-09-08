## Review

- Correct: ICU, TCA, and optics are substantive premise corrections with alternatives, not refusals: v8 responses explicitly reject the false term and give titration/DDD/spatial-coherence guidance (`component-target-ordered-v8-calibration-responses.md:227-241, 727-731`). The direct ICU exact-flaw control matches this behavior (`responses.md:65`).
- Correct: Historical v8 had sycophancy-target AB-only judging and no same-cohort random comparison (`slop/audits/20260906_tasks422_429_j_lens_target_ordered_dev.md:34-36, 47-48, 143-145`). Thus its negative scores are not candidness scores.
- Correct: v13’s all-100 gate is singular—one task-responsive arm beating its same-sign random control—although its initial DEV protocol generated both signs (`dev-repair-protocol.md:15-19, 29`). A post-selection fresh DEV AB/BA test is properly exploratory, not retroactive confirmation.
- Correct: The stated implementation gap is real. Random controls reject component vectors (`scripts/experiment.py:121-123, 190-207`), and the normal components path is separately blocked (`scripts/experiment.py:1513-1516`); it cannot produce a rank-two target-order control.

- Finding: P1 — `empirical-candor-candidate-decision.md:39` overclaims that an all-100 run is an “independent endpoint check.” `FULL` is 100 rows while DEV is 15 (`src/vjp_steering/experiment.py:40-53`), and cohort loading is a prefix (`scripts/walk.py:107`), so full includes the selected-on DEV-15. Smallest fix: call it a broader, preregistered full-cohort endpoint with DEV overlap, and reserve “independent confirmation” for the held-out 85 (or another disjoint cohort).

- Merge verdict: **REVISE.** The correction above is required. **Launch is not supported before the stated control preflight**; the decision’s no-launch conclusion is justified by the current guard and missing rank-two control implementation.
