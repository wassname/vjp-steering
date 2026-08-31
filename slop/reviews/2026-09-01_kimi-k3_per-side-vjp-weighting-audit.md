---
requested_model: moonshotai/kimi-k3
max_tokens: 20000
final_tokens: 20000
reasoning_effort: low
input_bytes: 6940
trace: /workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-01_kimi-k3_per-side-vjp-weighting-audit.trace.jsonl
generated: 2026-08-31T20:36:37.017718+00:00
---

# bounded completion

## First call reasoning

Let me carefully audit this.

The implemented formula:
- μ = mean_i g_i (per layer, per coordinate)
- w = max(0, 1 - v/μ²)
- r = μ ⊙ w
- N = ||σ r|| pooled over layers
- d = σ² r / N

Question 1: derive which scaling is consistent with which objective.

Standard derivation: if we want unit-norm intervention d in metric M: d = M^{-1} r / ||M^{-1} r||... Let's be careful.

If objective: maximize r·d subject to norm constraint in some metric:
- Euclidean: ||d||₂ = 1 → d = r/||r||.
- Standardized norm ||d/σ|| (i.e., dᵀ diag(1/σ²) d = 1): maximize rᵀd → d ∝ diag(σ²) r = σ² r, normalized so that dᵀ Σ^{-1} d = 1. Normalizer: ||σ r|| because dᵀΣ^{-1}d = (σ²r)ᵀ Σ^{-1} (σ² r)/N² = Σ σ² r² / N²... let me compute: d = σ² r / N. Then d²/σ² per coordinate = σ² r² / N². Sum = ||σ r||²/N². So N = ||σ r|| gives ||d/σ|| = 1. So the implemented formula d = σ²r/N with N = ||σr|| is exactly the maximizer of rᵀd subject to ||d/σ|| = 1. That's Mahalanobis / standardized-norm constrained steepest ascent. So actually the normalization N = ||σr|| IS consistent with the applied direction σ²r/N under the standardized-norm objective. So the apparent "contradiction" in item 2 is not a contradiction — it's self-consistent for the ||d/σ|| constraint. Good.

- Activation-weighted norm ||σ d|| = 1: maximize rᵀd → d ∝ r/σ², normalized with N' = ||r/σ||. Not implemented.
- Euclidean: d = r/||r||.
- Fisher preconditioning: d ∝ F^{-1} r where F = diag(σ²) (if Fisher ≈ variance of activations) → d ∝ r/σ² — inverse, not σ². Note that σ² multiplication is *forward* preconditioning (covariance), not inverse. So the implementation corresponds to multiplying by the diagonal covariance, i.e., whitening the constraint, not Fisher inverse preconditioning. This is "natural gradient with the constraint metric", i.e., the Gauss-Newton direction for a penalty on activation-space perturbation size... Actually: constraining ||d/σ|| limits the effect on downstream activations measured in units of activation std — this is a "relative perturbation" trust region. That's a defensible choice: each coordinate's change is measured relative to its natural variability.

So item 1: σ²r/N ↔ activation-standardized norm ||d/σ|| = 1 (steepest ascent in Mahalanobis metric with Σ = diag(σ²)). r/N_euclidean ↔ Euclidean. σr/N ↔ nothing natural from maximize rᵀd; σ r would be d in units... σ r would be d where d/σ = r — i.e., treating r as already standardized direction and rescaling by σ so each coordinate shifts by r standard deviations. Hmm: if you want d = σ ⊙ (unit standardized direction) with standardized direction r/||r||, then d = σ r /||r||. That is "interpret r as a z-score direction and convert to raw units." That corresponds to Euclidean norm constraint on the standardized vector, not on d. So σr/N ↔ Euclidean constraint in standardized coordinates where the *gradient used in the objective is also in standardized coords*? Let's do it: maximize rᵀ(d/σ)?? Eh. Simplest: if r is a direction in standardized space (d/σ), then d = σ r_normalized. So σr/N is consistent with "r is the desired standardized shift pattern; convert to raw units." Not a steepest-ascent for objective rᵀd.

Fisher: if Fisher F ≈ diag(σ²) (activation second moments as curvature proxy), natural gradient d ∝ F^{-1} μ = μ/σ², normalized in whatever norm. σ² is the *opposite* — it's multiplication by covariance, appropriate for trust region in whitened space.

Item 2: internal contradiction? No — N = ||σr|| is precisely the normalizer that makes ||d/σ|| = 1 when d = σ²r/N. The naming "global_activation_scaled" is consistent with standardized-activation norm. So no P0 here; the apparent mismatch is actually consistent. But it's an unsupported convention in the sense that nothing cites it; and the choice of constraint metric (σ in denominator of norm → multiply by σ²) vs Fisher (divide) is a real fork that the σ-vs-σ² trial gestured at. The trial σ→ no admissible -C dose: σr/N has norm ||d/σ|| = ||r||/N — much smaller in high-variance coords... eh, speculation.

Item 3: shrinkage. w = max(0, 1 - v/μ²). This looks like a James–Stein / shrinkage estimator of μ²: E[g²] = μ² + v, so estimate of μ² is ḡ² - v̄... Actually the classic: to estimate signal power μ² from observation with variance v, μ̂² = ḡ² − v. Then "signal fraction" = 1 − v/ḡ²... But here it's 1 - Var_i(g_i)/mean_i(g_i)² per coordinate, where Var_i is variance across prompts. If we model g_i = θ + ε_i with true per-prompt direction θ constant across prompts and noise ε with variance s², then mean of g_i has variance s²/n. The MSE-optimal shrinkage of the mean toward 0 (James–Stein-ish / empirical Bayes with prior θ~N(0,τ²)): weight = τ²/(τ² + s²/n) = 1 - (s²/n)/(τ² + s²/n). The implemented w = 1 - s²/μ̄² approximates this with τ² + s²/n ≈ μ̄² (since E[μ̄²] = τ² + s²/n under the model E[g]=0 prior... wait under prior mean 0, E[μ̄²] = τ² + s²/n, yes). So w ≈ 1 - s²/E[μ̄²] ≈ 1 - s²/μ̄² — a positive-part James–Stein estimator. Missing n: correct — the variance of the *mean* is v/n, so w should be 1 - v/(n μ²). Omitting n over-shrinks by factor n=256... i.e., 1 - v/μ² vs 1 - v/(256 μ²). With n=256 prompts, the shrinkage applied is drastically stronger than the empirical-Bayes justification. But: if the model is instead g_i = θ_i heterogeneous across prompts (each prompt has its own true direction), then Var_i(g_i) includes true heterogeneity and the pooled mean's relevance to a *generic* prompt... then shrinkage toward the mean by factor depending on SNR... Actually w = μ²/(μ²+v) = signal fraction if you interpret coordinate energy: E[g²] = μ² + v, fraction of energy due to the common component = μ²/(μ²+v) = 1/(1+v/μ²) ≈ 1 - v/μ² for small v/μ². Note 1 - v/μ² vs μ²/(μ²+v): these differ (first-order equal). The positive-part 1 - v/μ² is the unbiased estimate of the signal fraction? E[ḡ² - s²]... Let me just present: two coherent estimators:

(a) Empirical-Bayes/James–Stein shrinkage of the per-coordinate mean under prior θ~N(0,τ²): w = τ²/(τ² + v/n). Requires n. Implemented formula omits n → only justified if v is already the variance of the mean (it's not; it's across-prompt variance).

(b) SNR / signal-fraction weight: w = μ²/(μ² + v) = 1/(1 + v/μ²) — the fraction of second moment attributable to the mean. Implemented clamp(1 − v/μ²) is its first-order/positive-part analog. These are variants — both plausible, neither is "the" fix.

t-statistic alternative: w = indicator or monotone function of t = μ/sqrt(v/n), e.g., soft threshold. That's a different inferential stance (testing vs shrinkage) — a variant, not a bug fix.

But severity: is the missing n a P0 correctness error? Given the name "shrink" and the stated intent, the formula as written corresponds to signal-fraction weighting (per-coordinate "how much of the across-prompt energy is coherent"). Under that reading, no n is *needed* — v/μ² is a coefficient-of-variation-squared penalty. So I'd call it P1: the estimator is ambiguous; under EB-of-the-mean reading n=256 is missing and the applied shrinkage is far too aggressive; under signal-fraction reading it's self-consistent. The discriminating test can check whether shrinkage is binding.

Item 4: one low-cost discriminating calculation. Using saved tensors (prompt_gradients per side per layer, activation_scale per layer): compute, per side, the three candidate directions d1 = r/||r|| (Euclidean... well r pooled), d2 = σr/||σ... and d3 = σ²r/||σr|| (implemented), and measure how different they are: cosine similarity between candidate global vectors, and the distribution of per-coordinate weights — e.g., effective rank / participation ratio of w, and the fraction of coordinates with w=0. Actually the discriminating test should decide *between formula interpretations before generation/judging*. The key discriminating quantity: correlation between |μ| and σ per coordinate, and how the three formulas reweight. Better: compute the implied per-coordinate z-score shift t_j = d_j/σ_j for each candidate and check which yields uniform t (implemented σ²r/N gives t = σr/N — proportional to σ|μ|... hmm).

Let me think about what actually discriminates. The candidates differ by powers of σ: d ∝ σ^k r, k ∈ {0,1,2}. A decisive cheap computation: the relationship between r (=μw) magnitudes and σ across coordinates. If μ and σ are strongly correlated (typical: VJP magnitude scales with activation scale), then σ²r dramatically concentrates the direction on high-σ coordinates vs r. Compute, per side: cosine similarity between normalized directions of the three variants, and the effective number of coordinates (participation ratio) each uses. If cosine(σ²r, r) is high (>0.9), the whole σ debate is moot and the weak result is not due to the scale choice → stop fiddling with σ powers, the formula family is just weak. If cosine is low and the variants concentrate on disjoint coordinates, then the choice is consequential and the observed σ-vs-σ² trial difference (no admissible dose) is explained by geometry, and you can pick by checking which variant's top coordinates align with high t-stat (SNR) coordinates — i.e., which convention passes signal rather than noise.

Also compute the shrinkage diagnostic: fraction of weight mass zeroed by clamp, and 1/n-corrected variant w' = 1 - v/(n μ²) participation ratio vs current. If current w zeroes out, say, 90% of coordinates while n-corrected w keeps most, the missing n is materially changing the direction — that distinguishes P0 (over-shrinkage bug) from benign.

But the request: "exactly one low-cost, discriminating calculation." So I must pick one. I'd pick: from saved `prompt_gradients` and `activation_scale` tensors, compute per side the three normalized candidate directions d_k = σ^k r / N_k (k=0,1,2) plus the n-corrected shrinkage variant, and report (i) pairwise cosine similarities of the concatenated multi-layer vectors, (ii) participation ratio of each, (iii) fraction of coordinates killed by clamp with and without n. Decision rule: if cosines ≥ ~0.95, the σ-power and shrinkage conventions are immaterial → verdict: weak method, no bug fix will rescue, stop. If they diverge, the convention choice is load-bearing and must be justified/selected before more GPU. That's a single metadata computation on saved tensors, no GPU generation/judging.

Hmm, "one calculation" — I'll frame as: reconstruct candidate vectors from saved tensors and compute cosine-similarity/participation matrix. It decides "does the formula interpretation matter" — the discriminating fork.

Item 5: severity findings with quoted lines.

Findings:
- No P0 on normalization: the pair N = ||σr|| with d = σ²r/N is exactly unit-norm under ||d/σ||. Quote lines:
  - `activation_norm = torch.stack([(scales[side][layer] * raw[layer]).norm() for layer in layers]).norm()`
  - `directions = {layer: scales[side][layer].square() * raw[layer] / activation_norm ...}`
  Verify: d/σ per layer = σ r / N; norm over layers = ||σr||/N = 1. ✓. So standardized norm is exactly 1 — internal consistency confirmed, not a contradiction. P1: the choice of the standardized norm (multiplying by σ²) vs Fisher inverse-variance (dividing by σ²) is an uncited convention; these are opposite preconditionings and the σ trial suggests the fork matters empirically.

- P1 (potentially P0 depending on intent): shrinkage `1 - var/mean²` omits n; if intended as shrinkage of the mean (EB/James–Stein), correct factor uses v/n; as written it's a coefficient-of-variation signal-fraction weight. Quote:
  `1 - samples[side][layer].var(0, unbiased=True) / means[layer].square().clamp(min=1e-30)` and `.clamp(min=0)`.
  Also note: `.var(0, unbiased=True)` with per-prompt g_i — v is across-prompt variance, not variance of the mean.

- Also potential subtlety: `weights` multiplies μ: r = μ·w where w = 1 − v/μ² gives r = μ − v/μ — this is not a standard shrinkage of μ (EB gives μ·τ²/(τ²+v/n)) — μ·(1−v/μ²) = (μ³ ... it's like a soft-threshold-ish on... μ·(1 − v/μ²) = μ − v/μ, which diverges oddly for small μ (but clamp at 0 handles negatives). Under EB shrinkage, w should be τ²/(τ² + v/n) ≈ 1/(1 + v/(nμ²+...)). The form 1 − v/μ² vs 1/(1 + v/μ²): first-order same, but 1−v/μ² goes to zero at v=μ² whereas SNR weight goes to 1/2. Hard zeroing is a sparsifying choice. Variants.

- Another check: pooling counts — `activation_count` is total valid tokens across batches; mean = sum/count ✓; variance via E[x²]−E[x]² with clamp ✓ (fine, double precision used ✓).

- Note also: cotangent is the same for both sides; -C vector extracted from negative prompts with the same c. g_i for negative prompts measures d<h_T,c>/dup for negative-prompt inputs — that's a different conditioning distribution, fine, per-side. OK.

- One more mathematical point: w applied per-coordinate multiplies μ, but the "correct" EB posterior mean under heteroscedastic noise is μ·τ²/(τ²+v_i) — fine.

- Also: mean over prompts with equal weight vs token-count weighting: they use mean_token then mean over prompts — prompts weighted equally regardless of length. Convention, fine.

Also note the diagnostic comment `standardized_energy = sum((directions / scales)^2)` — that energy equals exactly 1 by construction; consistent with my derivation. Good to cite as confirmation.

Decision per instructions: "state the decision, strongest objection, and next check." Decision: No P0 in normalization; the σ²r/N with N=||σr|| pair is self-consistent steepest ascent under activation-standardized norm. The shrinkage factor is an unsupported, nonstandard estimator (missing n under EB reading; hard-zeroing) — P1. The weak judged result does not indicate a formula bug, and the σ-vs-σ² trial can't discriminate conventions. Next check: the cosine/participation recomputation on saved tensors.

Strongest objection to my verdict: the claim "no bug" on shrinkage depends on reading w as signal-fraction weighting; if the design intent (per the name "shrink") is EB shrinkage of the estimated mean direction, then omitting n=256 over-shrinks by orders of magnitude and is a P0 for that intent — the discriminating calc (participation ratio with/without n) resolves which regime we're in.

Let me write up the derivation of each objective cleanly.

Setup: per layer, choose d to maximize rᵀd (r = shrunk VJP mean) subject to constraint; global over layers (concatenate).

1. Euclidean ||d||₂=1: d = r/||r|| → form r/N with N=||r||.
2. Standardized ||d/σ||₂=1 (Mahalanobis with Σ=diag σ²): Lagrangian rᵀd − λ dᵀΣ⁻¹d → d ∝ Σ r = σ²r; normalizer for unit constraint: N = ||σr||. ✓ implemented.
3. Activation-weighted ||σd||₂=1: metric Σ⁻¹... constraint dᵀΣ² d =1? ||σd||² = Σσ²d² = dᵀΣ d with Σ=diag(σ²)? ||σ d||² = Σ_j σ_j² d_j² — metric matrix diag(σ²). Steepest ascent: d ∝ Σ^{-1} r = r/σ², N = ||r/σ||. None of the listed r/N, σr/N, σ²r/N matches; so activation-weighted norm is *not* what any candidate implements.
4. Fisher/inverse-variance preconditioning: d ∝ F⁻¹r with F=diag(σ²) → d ∝ r/σ² (then normalize in chosen norm). σ²-multiplication is the opposite direction (covariance, not inverse covariance). So the implementation is a trust-region/whitened-constraint steepest ascent, not natural gradient.

σr/N placement: d = σr/||r|| is "take r as standardized-space direction, unstandardize" — corresponds to Euclidean constraint in standardized space applied to a direction already expressed per-σ; equivalently maximize rᵀ(d/σ) s.t. ||d/σ||=1 then d = σ r/||r||. So it's the standardized-norm analog but with r treated as the gradient w.r.t. standardized coordinates. In other words: σ²r treats r as gradient w.r.t. raw d with whitened constraint; σr treats r as gradient w.r.t. whitened variable.

Also the objective maximized: rᵀd where r is pooled VJP mean = dE[c·h_T]/d(up) — so maximizing rᵀd maximizes predicted first-order change in c·h_T. With constraint ||d/σ||=1 = "equal total perturbation measured in activation-std units" — a sensible damage control metric, which aligns with the off-axis damage desideratum. So the convention is defensible, just uncited → P1.

Now the discriminating test, precisely stated:

Using saved `prompt_gradients[side][layer]` (n×d tensors) and `activation_scale[side][layer]`, compute for each side:
- w_now = clamp(1 − v/μ²), w_n = clamp(1 − v/(n μ²)) with n=256 (or actual count).
- Candidate global vectors D_k = concat_L σ_L^k (μ_L ⊙ w_L)/N_k for k∈{0,1,2}, with w ∈ {w_now, w_n}.
- Report: cosine similarity matrix among {D_0, D_1, D_2(implemented)}, participation ratio (Σd²)²/Σd⁴ of each, and fraction of coordinates with w_now=0 vs w_n=0.

Decision rule: if cos(D_2, D_0) and cos(D_2, D_1) ≥ 0.95 and w participation similar, then all formula variants implement nearly the same vector → the σ-power/shrinkage debate is immaterial; the weak result is a method-level weakness; do not spend GPU on variants. If cosines are low, convention choice is load-bearing → select by checking which candidate's mass sits on high-|t| coordinates (t = μ/√(v/n)), since signal-aligned reweighting is the only defensible selection criterion without judging; then run one DEV dose scan.

That's one saved-tensor calculation (a few seconds CPU). Good.

Severity list:

1. No bug — normalization/direction pair internally consistent (quote activation_norm line + directions line + diagnostic comment). Classification: no bug; P1 only for uncited convention (matches "global_activation_scaled" name as standardized-activation norm).

2. P1 (with P0 conditional on intent): shrinkage estimator. Quote the `1 - var/mean²...clamp(min=0)` block. Missing n under EB/James–Stein reading; as written equals positive-part coefficient-of-variation weight (signal-fraction first-order approx). t-stat / SNR weights are alternative stances, not bug fixes. Also the multiplicative composition r = μ(1−v/μ²) = μ − v/μ is not the EB posterior mean form μτ²/(τ²+v/n); the hard clamp sparsifies — undocumented.

3. Minor note: Fisher claim — if anyone intended inverse-variance preconditioning, σ² multiplication is the wrong direction (should divide); that's a design fork, resolved by test.

Also small correctness notes: variance computed via E[x²]−E[x]² in float64 — fine; equal prompt weighting — convention; `var(0, unbiased=True)` across prompts ✓ consistent with v definition.

Also, subtle: the same `activation_count` used for all layers — fine since same mask.

One more: weights use `means[layer].square()` — E[ḡ]² not E[ḡ²]; under model μ̄² estimates μ² + v/n, so w = 1 − v/μ̄² slightly over-shrinks even more. Minor.

Also: is there any actual inconsistency between stated and implemented normalization? The prompt says "stated normalization is N=||σr||, but applied direction is σ²r/N" — I've shown this is consistent for the ||d/σ|| metric. The repo comment `standardized_energy = sum((directions / scales)^2)` confirms the author intended standardized energy 1. So: no contradiction; label P1 naming/documentation only.

Formatting: concise report with headers, quoted lines. Should state decision, strongest objection, next check per system prompt. Use markdown. Keep derivation tight but complete. Distinguish derivation vs speculation explicitly.
## First call answer

# Audit: `vjp_mlp_up_left_right_shrink` weighting/normalization

**Decision up front:** No P0 in the normalization pair — `N = ||σr||` with `d = σ²r/N` is exactly self-consistent under an activation-standardized norm, not a contradiction. The shrinkage factor is a P1: it is only justifiable as a signal-fraction weight; read as shrinkage of the *estimated mean* it is missing `n=256` and over-shrinks by orders of magnitude. The weak judged result does not diagnose either point. Run one CPU-only recomputation on saved tensors (§4) before any GPU spend.

---

## 1. Derivation: which form matches which objective

Setup: choose global `d` (concatenated over layers) to maximize the first-order predicted effect `rᵀd` (r = pooled VJP) subject to a unit-norm constraint. Lagrange: constraint metric `M` gives `d ∝ M⁻¹r`.

| Objective / constraint | Optimal d | Candidate match |
|---|---|---|
| Euclidean `‖d‖₂ = 1` | `r / ‖r‖` | `r/N` |
| **Standardized `‖d/σ‖₂ = 1`** (Mahalanobis, Σ = diag σ²) | `Σr / N = σ²r/N`, with `N = ‖σr‖` | **`σ²r/N` — the implementation** |
| Activation-weighted `‖σd‖₂ = 1` | `Σ⁻¹r / N = (r/σ²)/‖r/σ‖` | **none of the three** |
| Diagonal Fisher / inverse-variance preconditioning (`F ≈ diag σ²`) | `F⁻¹r = r/σ²`, then normalize | **none — σ²-multiplication is the opposite direction** |

The remaining candidate `σr/N` is not steepest ascent for `rᵀd` under any of these; it corresponds to treating `r` as a direction *already expressed in standardized units* and converting back (`d = σ·(r/‖r‖)`), i.e., a Euclidean constraint in whitened coordinates with `r` as the whitened-space gradient.

**Derivation check on the implementation:** with `d = σ²r/N`, per layer `d/σ = σr/N`, so globally `‖d/σ‖ = ‖σr‖/N = 1` exactly when `N = ‖σr‖`. The code's own diagnostic comment confirms intent:

```python
# Diagnostic only: standardized_energy = sum((directions / scales)^2)
```

That energy is 1 by construction.

## 2. Alleged internal contradiction — none

These two lines are a matched pair, not a mismatch:

```python
activation_norm = torch.stack(
    [(scales[side][layer] * raw[layer]).norm() for layer in layers]
).norm()
directions = {
    layer: scales[side][layer].square() * raw[layer] / activation_norm
    for layer in layers
}
```

`N = ‖σr‖` is *precisely* the normalizer that makes `σ²r/N` unit-norm under `‖d/σ‖`. So the name `global_activation_scaled` is at least descriptively accurate: unit total perturbation measured in activation-standard-deviation units — a defensible damage-control trust region, and arguably aligned with the off-axis-damage desideratum. **However** (speculation flagged): the choice between multiplying by σ² (whitened-constraint steepest ascent) and dividing by σ² (Fisher/natural-gradient) is a genuine, uncited fork pointing in *opposite* directions, and the coarse σ-trial (no admissible -C dose) hints the fork may matter empirically. Severity: **P1 unsupported convention**, not P0.

## 3. Shrinkage factor

```python
weights = {
    layer: (
        1
        - samples[side][layer].var(0, unbiased=True)
        / means[layer].square().clamp(min=1e-30)
    ).clamp(min=0)
    for layer in layers
}
```

**Derivation.** Two coherent readings:

- **(a) Empirical-Bayes / James–Stein shrinkage of the mean.** Model `g_i = θ + ε_i`, prior `θ ~ N(0, τ²)`. Posterior mean weight is `τ²/(τ² + v/n)` where `v` is the across-prompt variance and **n is the prompt count**. The implemented `1 − v/μ²` is this form **with `n` omitted** (using `E[μ̄²] ≈ τ² + v/n` as denominator). Under this reading, `n=256` is missing and the applied shrinkage is ~256× too aggressive.
- **(b) Signal-fraction weight.** `E[g²] = μ² + v`, so the coherent-energy fraction is `μ²/(μ²+v)`; `clamp(1 − v/μ², 0)` is its first-order positive-part analog. Under this reading no `n` is *required* — but note it hard-zeroes coordinates at `v = μ²` (the exact SNR weight would give ½), so it is a sparsifying variant, not the SNR weight itself.

A per-coordinate t-statistic weight (`t = μ/√(v/n)`) is a third stance (testing/thresholding rather than shrinkage). **These are variants of each other, not bug fixes for each other** — but reading (a) is what the name "shrink" suggests, and under (a) the missing `n` is a correctness error. Two further minor derivational notes: `means[layer].square()` estimates `μ² + v/n`, slightly over-shrinking further; and `r = μ(1 − v/μ²) = μ − v/μ` is not the EB posterior-mean form `μ·τ²/(τ²+v/n)` in any case.

## 4. The one discriminating calculation (CPU-only, saved tensors)

From the already-saved `prompt_gradients[side][layer]` (n×d) and `activation_scale[side][layer]`, per side:

1. Compute `w_now = clamp(1 − v/μ²)` and `w_n = clamp(1 − v/(n·μ²))`, plus per-coordinate `t = μ/√(v/n)`.
2. Build the three global candidates `D_k = concat_L[ σ_L^k (μ_L ⊙ w_L) ] / N_k` for `k ∈ {0, 1, 2}` (k=2 = implemented), under both `w_now` and `w_n`.
3. Report: cosine-similarity matrix among `D_0, D_1, D_2`; participation ratio of each; fraction of coordinates zeroed by `w_now` vs `w_n`; correlation of each `D_k`'s mass with `|t|`.

**Decision rule (pre-registered):**
- If all pairwise cosines ≥ ~0.95 **and** `w_now` vs `w_n` zero-out fractions are similar → every formula interpretation in dispute produces nearly the same vector; the σ-power and shrinkage debates are immaterial; the weak judged result is a method-level weakness. **Stop tuning this family; do not spend GPU.**
- If cosines are low or `w_n` rescues a large zeroed fraction → the convention choice is load-bearing. Select the variant whose mass concentrates on high-`|t|` coordinates (signal alignment is the only selection criterion available without judging), and only then run one DEV dose scan.

This is seconds of CPU and decides the formula question *before* generation/judging. It directly distinguishes "P0 over-shrinkage" from "P1 benign convention," which the judged result and the coarse σ-trial cannot.

## 5. Findings by severity

- **P0:** none confirmed. Conditional P0: if the shrinkage is intended as EB/James–Stein shrinkage of the estimated mean (as the name implies), the omitted `n` in `1 − var/mean²` is a correctness error; §4 resolves intent vs. impact.
- **P1 (unsupported convention):** the σ²-multiplication (`scales[side][layer].square() * raw[layer]`) implements a whitened trust-region (`‖d/σ‖=1`), the *inverse* of Fisher/inverse-variance preconditioning; uncited, and the fork is empirically untested at fine resolution. The normalization pair itself is internally consistent — the apparent contradiction in the review request does not exist.
- **P1 (undocumented estimator):** shrinkage `clamp(1 − v/μ²)` hard-sparsifies at `v=μ²`, omits `n`, and uses `μ̄²` where `μ̄² − v/n` would be the unbiased signal estimate; t-stat/SNR weights are alternatives, not fixes.
- **No bug:** activation variance via `E[x²]−E[x]²` in float64 with clamp; token-masked pooling and equal per-prompt weighting are consistent conventions.

**Strongest objection to this verdict:** "no contradiction" only holds if the intended metric is `‖d/σ‖`; if the method's intent (per its name and the failed σ-trial) was Fisher-style scaling, then both the σ² direction and the missing `n` are load-bearing errors, and the §4 cosine/participation numbers — not the judged aggregate — are the right instrument to settle it.

## Completion

- outcome: `complete`
- trace: `/workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-01_kimi-k3_per-side-vjp-weighting-audit.trace.jsonl`
