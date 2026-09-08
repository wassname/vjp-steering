# Empirical-candor component-control preflight independent review

Reviewer: Kimi K3, 2026-09-08. Verdict: PASS, no launch blocker.

The reviewer re-ran the component and export self-tests and the preflight. It confirmed the deterministic seeded rank-two control, source Gram preservation, recomputed dual, frozen source `+C` hash/layers/alpha/operator/mask, source-side and behavior-target propagation, candidness prompt and cache separation, and candidness endpoint direction.

The reviewer found one post-judging renderer problem: `results.py` still used source side to set accepted markers. PI/OpenAI Codex fixed that after this review by adding the shared `behavior_axis_direction` helper and using it in both `scripts/export.py` and `src/vjp_steering/results.py`. The full reviewer response is retained in the session artifact at:

`/home/code/.pi/agent/sessions/--workspace-2026-jspace-j-steer_pub--/subagent-artifacts/outputs/098d4913-dd17-4bac-9ee8-3e5cc379fc3d/slop/reviews/j_lens_empirical_candor_component_control_preflight_review_retry.md`

No Modal or pueue job was launched during this review.
