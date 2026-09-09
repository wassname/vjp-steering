# Machine-checked comparison: state-dependent swap vs frozen unit-direction (DEV L16)

**Source:** `outputs/logs/20260909_j_lens_dev/dev-abrasive-flattering-coords.json` (15 DEV prompts, Qwen3.5-4B, lens qwen-n1000, layers 13-21) and `outputs/experiments/v14-paper-native-verbal-chat-country-swap-corrected-vendor/results.json` (France->Germany, 9 hidden states).

## Axis mapping (attribution: v2 review corrected)
- `J_LENS_SWAP_SOURCE=abrasive (90474)`, `J_LENS_SWAP_TARGET=flattering (80238)`, `basis=[w_source@J,w_target@J]`, `c=V†h` where `V=basis.T`, `c[0]=abrasive`, `c[1]=flattering`.
- DEV L16 mean **final-position** `c=[0.798, -0.154]` (abrasive occupied, flattering near-zero) — v2 review's prior reversal (+0.798 as flattering) was an error; corrected here with attribution to `slop/reviews/20260909_dev_raw_science_v2.md`.
- **Mean-over-positions** `c` at L16: `[0.348, -0.063]` (diff -0.411, std 0.148) vs final-position diff -0.951 (std 0.118). Per-prompt scalar `c_target-c_source` varies: min -1.214, max -0.788 (final), -0.629 to -0.071 (mean-over). State-dependence is non-negligible; a rescaled fixed direction at final positions alone does not capture mean-over-positions behavior, so it does not justify another run.

## Operator comparison (CPU tensors, no behavioral coherence claim)
- **Swap:** `h' = h + C·V(swap(c)-c)`, `c=V†h` per-prompt, `C` is alpha. At `C=1`, full swap: `c'=[-0.154,0.798]`. At `C=-16` (for -C16), `c'=[16.03,-15.39]` (not -14.4/+15.1 as v2 review computed with +16). Off-manifold magnitude ~15, far beyond natural sd ~0.1.
- **Unit-direction:** `d=V(swap(c_bar)-c_bar)` at mean `h_bar` (final-position mean), `d̂=d/||d||`, `h' = h + C·d̂` with explicit `C` as residual-stream step, `C=0` bare in-pipeline control (hooks installed, delta 0). Both preserve `h_orth = h - V·V†h` exactly (verified: `h_orth` before vs after `≈0` up to bf16 noise, `orthogonal_residual_max_abs_error` diagnostic), so **h_orth preservation does NOT imply off-axis perturbation ~0** — later nonlinear layers (MLP, attention) can change arbitrary outputs; v2 review's claim `h_orth preserved ⇒ off-axis ~0` is false (attribution: `slop/reviews/..._v2.md`).
- **Zero-dose identity:** `C=0` gives `h'=h` exactly for both (verified with CPU tensors: `torch.allclose(h, h+0*delta)` True).
- **Signed coefficient math:** `+C` toward flattering (increase sycophancy), `-C` toward abrasive (decrease) — verified with `C=-16` correct sign above.

## Hypothesis distinguished and result that would change paper-based implementation
- **Hypothesis:** The *swap delta direction* `(v_source−v_target)` is causally engaged for sycophancy, but the *state-dependent scalar* `(c_target−c_source)` conflates dose with per-prompt coordinate values and drives off-manifold saturation at high |C| (e.g., -C16). A **fixed-direction, dose-linear** unit vector with explicit `C` semantics and true zero control would show a monotone dose-response through zero intercept if the direction is causally engaged, vs flat if occupancy (c≈0.8) is without leverage.
- **Result that would change paper implementation:** If the fixed unit-direction at L16 shows a **monotone, sign-symmetric dose-response through C=0** (e.g., +C 0→8 gives +0.8→+1.8 with 7/15 → 12/15 coherent, -C 0→8 gives -0.2→-0.5 with similar coherence) while the state-dependent swap shows **non-monotone, sign-asymmetric** (as observed: +C 0.07→1.24→1.79, -C -0.25→+0.48 at C=8, -0.453 at 11.9, +1.013 at 16), then the paper-based method should be repaired by **replacing the per-prompt scalar with a fixed scalar** (or equivalently, normalizing the swap delta to unit norm and defining C as step size), preserving `h_orth` and adding `C=0` control. If the fixed-direction also shows flat or asymmetric response, then `c≈0.8` is occupancy without leverage and the pair should be abandoned for DEV.

## Position-dependent scaling
A rescaled version of the same fixed direction at **final positions alone** (as v2 review proposed) does not justify another run, because mean-over-positions `c` differs markedly (0.348/-0.063 vs 0.798/-0.154) and the all-prompt operator applies at all 22 prompt positions, not just the final one. Any diagnostic must specify whether it uses final-position `c_bar` or mean-over-positions `c̄` and must preserve `h_orth`.

## Decision
The comparison shows the swap's state-dependence and the v2 review's algebra errors (h_orth ⇒ off-axis, -C16 sign, paper support). The next bounded diagnostic run (if justified) should be the **fixed unit-direction at L16 with C∈{0,0.25,0.5,1,2,4,8}**, retaining both swap curves for comparison and separate identity (blue 13-21 vs green L16 already distinct, plus new orange for unit-direction), using its outcome to repair the paper-based method's dose semantics. Otherwise, redirect the $1 reserve to a specific paper-supported repair (e.g., full-band 13-21 with corrected single-token and all-prompt scope already validated, or J-space clamp with explicit C semantics and bare control) rather than an ActAdd substitution that discards the state-dependent swap.

-- PI/OpenAI (machine-checked, attribution to v2 review errors)
