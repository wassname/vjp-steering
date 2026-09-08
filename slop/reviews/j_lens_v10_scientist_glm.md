---
requested_model: z-ai/glm-5.3-flash
max_tokens: 8000
final_tokens: 6000
reasoning_effort: low
input_bytes: 13589
trace: slop/reviews/j_lens_v10_scientist_glm.trace.jsonl
generated: 2026-09-07T14:43:15.619547+00:00
---

# bounded completion

## First call reasoning

Need to reconstruct method, list distinctions, assumptions, failure modes, alternatives, experiments, with evidence vs inference labels. Medium-length structured answer.
## First call answer

# Reconstruction and review: v16 full-residual control + J-lens context

## 1. What the method actually is (reconstruction)

Two separate stages, reconstructed from the pseudocode, evidence packet, and replay log.

**Stage A — basis extraction (per layer, layers 13–21):**

1. Run the model in prefill over n matched, deduplicated source questions under three chat conditions: positive persona, negative persona, neutral persona, with an empty thinking prefill. Capture final prefill block (residual-stream) outputs.
2. Form per-condition difference signals against neutral:
   `s₊[ℓ] = mean(states₊[ℓ] − states_neutral[ℓ])`, same for s₋. These are **full residual-width** difference-in-means vectors, not dictionary-sparse components. (GP16 over a row-normalized `unembedding @ J[ℓ]` dictionary is *measured as a diagnostic* but explicitly not the v16 basis.)
3. Basis rows: `B[ℓ] = stack(unit(s₊), unit(s₋))` — two non-orthogonal unit vectors; the dual `D[ℓ] = (B Bᵀ)⁻¹ B` (pseudoinverse) gives the coordinate readout. Saved twice with different target indices (0 for plus, 1 for minus). Both sides use nonnegative α; direction of steering comes only from which component's coordinate is clamped high vs. low.

**Stage B — patching at generation:**

For each side and α ∈ {0.25…2}, over dev15 questions:
- A one-shot prefill hook, at every layer 13–21, on all attended prefill positions, computes coordinates `c = hidden @ Dᵀ ∈ R²`, sets `desired = (max(c), min(c))` per position (order chosen by target index), and adds `α (desired − c) B` to the hidden state. No intervention during generation; cache-based greedy decode, 512 tokens.
- Effect = rubric-based OpenRouter comparison of steered vs. bare responses; off-axis tracked separately.

This is a **2D coordinate clamping / spread operator**: at each position it pushes the state toward the 2D subspace with coordinates separated to the extremes (max/min), i.e., it *amplifies the difference* between the two persona coordinates while leaving the shared component intact. The patch is `α[(high−c₊)b₊ + (low−c₋)b₋]`; since `high ≥ low`, the update always adds along b₊ and subtracts along b₋ scaled by the existing spread.

**Status of evidence:** The replay log (direct evidence) establishes only numerical/implementation correctness: saved bases match the difference-in-means construction (row max error ≤ ~3e-8), duals satisfy the Gram identity, patch equals an independent Gram-system solve, hooks fire once on attended prefill positions only, wrong-target/no-op negative controls are detected. It is **not** a behavioral test. The packet says so explicitly (inference-free statement).

## 2. What the evidence shows vs. what I infer

Directly shown:
- v16 aggregate at α=2: plus mean +1.227 / median +0.3 / 9/15 intended signs; minus mean −0.52 / median 0 / 6/15. Neither meets the historical ≥10/15 breadth bar. Means not dose-monotonic.
- Direct instruction control (prior, aggregate only): minus −6.37, 15/15.
- Two anecdotal steered-vs-bare pairs at α=2 with exported effect (+0.2, −7.7) and off-axis (0.7, 0.4).
- Corrected J-lens readout (transport + final RMSNorm + head): 0/15 exact rank-1 for the assessment-token study; actual emitted false-answer 14/15 on fabricated questions; BF16 batching changes ranks (hence batch-1 diagnostics).
- Numerical replay pass (details above).

My inferences (flagged):
- **(I)** The weak behavioral transfer is more consistent with "the full-residual difference-in-means basis carries a lot of non-persona content" than with a bug in the patching math — the replay rules out implementation error in the patch operator, but nothing localizes *what content* the basis rows carry.
- **(I)** The asymmetry between plus (9/15, mean +1.23) and minus (6/15, median 0) suggests the negative persona signal is weaker or noisier at extraction time, or that "not-sycophantic" is not a linearly coherent direction in this model.
- **(I)** The per-position max/min clamp, applied across layers 13–21 simultaneously, is a strong nonlinear distortion; loss of dose monotonicity is expected once α pushes the state far off-manifold.

## 3. Distinctions that matter

1. **v16 is a control, not the J-lens method.** The packet states this. The corrected J-lens readout (transport, RMSNorm, head) concerns a token-level swap/summoning paradigm; v16 is residual-vector steering. Conflating their negative results would be a category error.
2. **Measured GP16 ≠ used GP16.** The dictionary approximation is computed but not the basis; any comparison to the earlier "GP16 persona-component version (weak transfer)" must be careful about which basis produced which number.
3. **Non-orthogonal 2D basis with dual readout.** Condition numbers ~1.16–1.88 mean the two persona directions are substantially non-collinear but not orthogonal — coordinate clamping is well-conditioned but the "high/low" semantics on a non-orthogonal pair is not the same as clamping along two orthogonal axes. Inference from the logged condition numbers.
4. **Prefill-only, generation-clean intervention.** The hook edits only attended prefill positions and removes itself; the cache carries the perturbation. This is a deliberate design (steer context, not each generated token) — distinct from per-token steering, and it caps how much the intervention can shape long continuations.
5. **Effect metric is LLM-judge rubric, not a causal readout.** Distinguishes it from the rank-1 readout in the companion protocol.

## 4. Assumptions (mostly inferred; the material does not defend them)

- (I) The mean over source prompts of (persona − neutral) residual states is a valid linear encoding of persona strength at all positions of *unrelated* benchmark questions.
- (I) Persona effect is approximately position-independent and layer-invariant enough to justify the same clamp at 9 layers.
- (I) The neutral condition is a true shared baseline (no order effects from condition presentation).
- (I) The LLM-judge rubric effect is monotone in the underlying construct ("sycophancy") and comparable across plus/minus sides.
- (I) 15 dev questions suffice — no significance is claimed, correctly, but the 9/15 vs 6/15 counts are near coin-flip territory.

## 5. Failure modes

- **Off-target content in the basis** (I): full-residual difference-in-means includes topic, length, and register confounds from the source prompts; matched/deduplicated helps but cannot guarantee persona isolation.
- **Non-dose-monotonicity** (shown): suggests saturation, judge noise, or chaotic off-manifold dynamics; any selection rule keyed on a single α is fragile.
- **Min-coordinate pathology** (I): `min(c)` can be large-negative; pushing toward it may inject content unrelated to the persona, explaining off-axis movement.
- **BF16 batching sensitivity** (shown for the readout; I: plausibly affects steering too): rank-level behavior differs between batch-1 and batched execution; steering results may not be reproducible under different batching.
- **Selection-gaming risk** (I): the historical selection rule (both mean/median sign, ≥10/15, off-axis < 1.5) applied to 7 α values × 2 sides on 15 questions is a multiple-comparisons garden; the packet's refusal to claim significance is appropriate.

## 6. Alternative formulations worth testing

1. **Per-position projection instead of max/min spread:** `δ = α (P_B hidden − hidden)` (project onto the 2D subspace) — removes the extreme-coordinate push, isolates "remove off-subspace" from "amplify within-subspace."
2. **Asymmetric clamp:** only push the target coordinate high, leave the other untouched (`desired_target = high`, other = c_other). Tests whether the min-side is doing harm or work.
3. **Generation-time steering:** re-apply the hook per generated token at low α, to test whether prefill-only application is the transfer bottleneck.
4. **Orthogonalized basis:** Gram–Schmidt on {s₊, s₋} and steer only along the orthogonalized persona axis; compare transfer.
5. **Difference-of-personas direction** (s₊ − s₋) with a single signed coordinate, instead of the 2D clamp — the classical delta method; the 2D construction's added value is untested.
6. **Layer-restricted steering** (e.g., only 13–15 or 19–21) to see whether the 9-layer aggregate causes the non-monotonicity.

## 7. Experiments that would change my mind / fill gaps

- **Basis content probe:** decode top-|·| unembedding directions of s₊ and s₋, or compute cosine of s₊/s₋ with topic/length principal components of the source prompts. If persona directions are confounded, weak transfer is explained. (Observation that would change my mind: s₊/s₋ nearly orthogonal to topic directions *and* transfer still weak → construct problem, not basis contamination.)
- **Dose–response curve at finer α** on more than 15 questions with a fixed judge and bootstrap CIs on per-question effects. Would test whether non-monotonicity is noise.
- **Ablate the min-coordinate** (formulation 2 above) on the two attached example questions first, then dev15. If minus transfer improves, the clamp shape is the problem.
- **Corrected-readout steering analog:** apply the v16 basis but evaluate with the *corrected* J-lens readout (transport + RMSNorm + head, batch-1) on the fabricated-question set, connecting the two paradigms with a causal rather than rubric metric.
- **Direct-control under identical harness:** the −6.37/15-of-15 direct instruction control was run under a different pipeline; re-run it through the same judge to calibrate the rubric's dynamic range. (Currently I cannot tell whether +1.23 is "weak" or "half the rubric's ceiling.")

## 8. Uncertainties / missing evidence

- No per-question v16 results beyond two α=2 examples; medians of 0 and +0.3 hide the distribution shape.
- The direct-control raw outputs are not attached, so its aggregate is unverifiable here.
- No evidence on whether the plus and minus bases are approximately antiparallel or independent (condition number bounds non-collinearity of the *pair*, not s₊ ≈ −s₋).
- The companion J-lens protocol is described only by verbal report of a pinned commit; the swap mechanics (all positions, band, single-token forms) cannot be audited from here.
- Judge (OpenRouter rubric) reliability: no inter-judge or repeat-judge variance estimate.

I make no selection between v16 and alternatives; the local evidence supports implementation fidelity of v16 and does not support a J-lens behavioral claim, which matches the packet's own framing.

## Completion

- outcome: `complete`
- trace: `slop/reviews/j_lens_v10_scientist_glm.trace.jsonl`
