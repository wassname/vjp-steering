---
requested_model: anthropic/claude-fable-5.1
max_tokens: 20000
final_tokens: 20000
reasoning_effort: low
input_bytes: 11289
trace: /workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-02_claude-fable-5.1_per-side-eb-scientific-brainstorm-fable51.trace.jsonl
generated: 2026-09-02T03:59:23.902519+00:00
---

# bounded completion

## First call reasoning

I need to work through the causal claim itself: the cotangent vector at the target layer is being treated as the trait direction, and the vector-Jacobian product pulls this back to the source layer's mlp.up_proj outputs conditioned on each prompt, then averaged across prompts to approximate an expected local linear map.

Several assumptions concern me here. First, the pulled-back direction c may be confounded—positive and negative prompts likely differ in valence, agreement, length, and register beyond just the intended trait. Second, the VJP is a gradient describing an infinitesimal effect, yet steering happens at magnitudes far from infinitesimal, so treating the local linear approximation as valid for these finite perturbations is a stretch. Third, the extrapolation logic itself seems backward or at least confusing to me—negating the gradient computed on negative-class prompts and applying it to push those prompts further negative is essentially extrapolating outward along the same direction rather than correcting toward the positive class, and I'm not fully convinced this is doing what's intended. There's also the empirical Bayes assumption of a shared τ² per layer, implying coordinates are treated as independently drawn from a common normal prior, which is a strong simplification.

I'm also uneasy about the σ² activation-covariance scaling—this implicitly assumes a diagonal metric aligned with activation variance is the "correct" one for converting gradients into steering directions, which isn't something implied by the VJP calculation itself; it's an added natural-gradient-style choice. Then looking at the τ² estimator itself, it's a Morris-style shrinkage estimator, but since it uses the sampling variance of the mean (scaled by n=200) rather than the raw gradient variance, the resulting shrinkage weights end up close to 1 for most coordinates—so the empirical Bayes approach barely shrinks anything and mostly just recovers the mean, unlike the harder prior estimator that zeroed out many coordinates. This makes me think the improved cosine similarity (0.887 vs 0.863) is less about noise removal and more just a reflection of that estimator difference, and the per-layer allocation of τ² essentially decides which layers get shrunk wholesale.

I'm now also questioning the pairing of prompts across sides—variance is being treated as if prompts within a side are independent, which seems fine on its own, but the contrast vector c's own variance is being ignored entirely. And the asymmetric damage numbers between positive and negative steering directions could stem from several sources: evaluator ceiling/floor effects, incomparable Z-normalization units across sides, side-specific σ estimates, or genuinely different class-conditional Jacobians where the local gradient structure differs between positive and negative prompts.

I'm listing out possible mechanisms behind this asymmetric dose-response: mismatched units between the two sides' displacement measures, class-conditioned Jacobians pointing toward different features depending on prompt polarity, nonlinear saturation from extrapolating past the training manifold (with RLHF likely imposing a harder floor on abrasiveness than ceiling on sycophancy), differences in prompt length/token count skewing gradient estimates, gradient-variance differences driving different layer allocation, and finally the possibility that the evaluator's notion of "sycophantic" isn't symmetric with its notion of the opposite trait.

I'm also weighing whether judge asymmetry (flattery being easier to detect than rudeness, or judges conflating rudeness with harm) could explain the skewed effect sizes, and whether the model's baseline position near the agreeable end changes how much headroom exists on each side. I'm consolidating these into a shortlist of confounds — generic agreement/harshness effects, cotangent mismatch, allocation shifts, side-specific variance, saturation, and ignored pairing variance — before ranking which tests would best disambiguate them.

For that ranking, I'm considering a swap test where the +C and -C vectors get applied to the opposite prompt class to see if curves converge (pointing to an estimator artifact) or stay separate (pointing to genuine prompt-class asymmetry), and a cotangent-projection dose check that measures actual displacement along and orthogonal to the target direction to separate steering failure from behavioral failure from judge bias.

I'm also thinking about judge-swap and rubric decomposition, scoring sycophancy, harshness, and coherence separately with baseline calibration, plus a neutral-prompt test to see if the trait is confounded with valence, and possibly a shared-metric re-extraction with pooled variance as a fourth check, though I want to keep the list to three.

A fifth angle: a paired estimator taking the difference between per-pair gradients to test whether there's a single class-invariant source direction. This cancels topic noise but risks mixing Jacobian differences into the trait signal and imposing a symmetry that might not actually hold.

The claim that EB helped one side more looks incoherent since both sides had different extraction and normalization, with no matched-dose comparison and a missing prior-estimator curve, so coverage can't really be assessed. Even a narrower claim about EB vectors producing measurable effects requires that missing curve at matched doses, so I'm concluding the pipeline is plausible but the observed asymmetry can't be trusted until units are properly matched.

The strongest objection is that doses aren't even comparable, confounding any per-side dose-response comparison by construction — I need to check the swap/pooled-σ test with c-projection next. I'm also suspicious that hard-shrink zeros out heavily since its variance term isn't divided by n, while EB's /n term barely shrinks anything, meaning the apparent "improvement" from EB is really just an artifact of near-zero shrinkage rather than a genuine effect.

Given gradients are often sparse and heavy-tailed, the mean μ² gets dominated by a few large coordinates, inflating τ² so that the shrinkage weight w≈1 nearly everywhere — meaning EB behaves like a mild outlier suppressor rather than a true noise remover. Time to write this up with clear labels, keeping it thorough but not overly long.


## First call answer

# Review: per-side VJP + EB steering

**Decision:** The pipeline is a coherent *extraction* procedure, but the current design cannot support any comparative claim about the two sides (or about EB vs. hard-shrink) because the two vectors live in different units and the shrinkage change is much smaller than the narrative implies. Treat the reported curves as two separate feasibility observations, not as a side-by-side result.

**Strongest objection:** `Z` and `σ` are computed per side, so `C=16` on −C and `C=44` on +C are not the same dose in any shared metric. Any asymmetry in dose-response is confounded *by construction* before model geometry or evaluator semantics enter.

**Next check:** the swap/pooled-metric test in §4, with the target-layer displacement along `c` measured directly.

---

## 1. Assumed causal story and which parts are assumptions

The story: `c` is the trait axis at the target layer; the per-prompt VJP is the local linear pullback of `c` onto `mlp.up_proj` outputs; averaging over prompts of one class gives the class-conditional expected pullback; EB removes sampling noise; `σ²` converts a gradient (covector) into an activation-space displacement (a diagonal metric); adding `+d` to +C prompts and `−d` to −C prompts moves each class outward along its own local trait gradient.

What VJP/EB actually give you:
- VJP gives `J_pᵀ c` at prompt `p` — a first-order object valid for infinitesimal perturbations. Nothing more.
- EB gives a coordinate-wise posterior mean under a normal-normal model with a *per-layer shared* `τ²`.

Strong assumptions (not consequences):
- **(A1)** `c` = trait, not valence/register/length/agreement. The prompts are "positive/sycophantic vs negative/abrasive"; that is at least a two-factor contrast.
- **(A2)** First-order extrapolation to `C=16–44` in activation-scaled units. Steering doses are finite; the gradient is only guaranteed correct at `C→0`.
- **(A3)** `−d["−C"]` on −C prompts is "more of the trait's negative pole." Actually `d["−C"]` is the direction that moves −C prompts *toward the positive mean*; negating it extrapolates outward from the negative class. There is no reason the anti-sycophancy direction and the more-abrasive direction coincide.
- **(A4)** Coordinates within a layer are exchangeable draws from `N(0, τ²)`. Gradients through `up_proj` are typically heavy-tailed/sparse; a single `τ²` per layer is a poor prior for that.
- **(A5)** The diagonal activation variance `σ²` is the right metric for gradient→displacement. That is a natural-gradient-flavored choice, not implied by anything upstream, and doing it per side is a further choice.
- **(A6)** The judge's "effect" axis is the same axis as `c`.

## 2. Mechanisms for legitimately different dose-response curves

1. **Different units (normalization).** `Z` and `σ` are side-specific. If negative prompts have larger source activation variance, `d["−C"]` concentrates energy in different coordinates and the same `C` produces a different target displacement. *Inference:* this alone can produce the observed ~3.5× difference in "effect at accepted dose."
2. **Class-conditioned Jacobians.** `J_p` at abrasive prompts routes `c` through features salient in that context (harshness, negation, refusal-like tokens). Pulling back the *same* `c` through different Jacobians yields directions that need not be antiparallel in behavior space. The shared cotangent is a mismatch for the negative class if `c` is dominated by positive-class features.
3. **Nonlinear geometry / asymmetric manifold.** An RLHF'd Qwen has a soft floor on abrasiveness: pushing outward from −C leaves the trained manifold quickly (incoherence, damage), while more sycophancy stays in-distribution. Hence −C saturates or breaks at lower effective dose. This is consistent with damage 0.416 at effect −0.97 vs damage 1.13 at effect +3.47, but not proven by it.
4. **Prompt distribution / token counts.** Per-prompt VJPs are token-summed or -averaged after `skip_first=16`; different length distributions change gradient magnitude, variance, and `σ` estimates by side. Also affects `τ²` via `s²`.
5. **Estimator SNR → layer allocation.** `τ²` is per layer; layers where negative-class gradients are noisier get wholesale-shrunk, shifting the −C vector toward shallower/deeper layers than +C. The two vectors may then have different effective depth, which changes both effect and damage.
6. **Evaluator semantics.** An AB/BA judge may detect flattery more readily than rudeness, or may count rudeness partly as "damage," collapsing the accepted −C region. The health gate failing at `C≥28.6` for −C is consistent with this and with (3); the data don't separate them.
7. **Baseline position.** The base model is already agreeable; "effect" is measured relative to that. Headroom and judge sensitivity are not symmetric around the baseline.

## 3. Unintended objectives / failure modes

- **Valence vs trait.** *Speculation, but likely:* the contrast set encodes agreement/harshness jointly; `+d` may just increase generic agreement, `−d` generic harshness. The +C effect of +3.47 is large for a "sycophancy" axis; check whether it is mostly "says yes more."
- **Shared cotangent mismatch for −C.** See mechanism 2. The −C vector is "how to make abrasive prompts more positive," negated. That is a different scientific object from "how to make prompts more abrasive."
- **EB is nearly the identity here.** *Inference from the formula:* with `n=200`, `s² = Var/n` is ~200× smaller than the old `Var`, and `τ²` is a coordinate-*mean* of `μ² − s²`, which heavy-tailed coordinates will inflate. So `w≈1` for almost all coordinates; only coordinates with `Var > n·τ²` are shrunk. EB is therefore acting as a mild outlier suppressor, and the cosine of 0.86–0.89 vs hard-shrink mostly reflects *un-shrinking* what the old estimator zeroed. "EB removes noise" is not the right description; "EB restores the mean and changes layer weighting via `τ²`" is.
- **Layer reallocation, not denoising.** Because `τ²` is per layer, the ratio `τ²_layer/(τ²_layer + s²)` reweights *layers*, not just coordinates. This is a design choice with direct behavioral consequences.
- **Side-specific σ = two metrics.** `σ[side]²` in the direction and again in `Z` means `d["+C"]` and `d["−C"]` are not comparable vectors; their norms in a shared metric differ. Any "one side responded more" comparison is ill-posed.
- **Saturation/threshold.** The +C curve reached `C=44` with rising damage; the −C curve broke early. Without the displacement-along-`c` curve you cannot tell whether −C saturated (target didn't move), broke (target moved but behavior degraded), or is judged asymmetrically.
- **Pairing ignored — but in a different place than stated.** Within a side, prompts are legitimately iid; pairing doesn't matter there. Where it matters: `c` itself is a difference of means whose variance is never propagated, and the paired structure could cancel template/topic variance in a joint estimator (§5).

## 4. Three ranked discriminating tests

1. **Cross-application with pooled metric (cheapest, most decisive for the unit problem).** Re-normalize both vectors with pooled `σ` and a shared `Z`; then apply `−d["+C"]` to −C prompts and `−d["−C"]` to +C prompts alongside the originals. Supports mechanism 1 if curves converge under pooled metric; supports mechanisms 2/3 if `d["+C"]` negated on −C prompts behaves very differently from `−d["−C"]` even in shared units. No re-extraction needed.
2. **Direct target displacement.** For each accepted point, measure `⟨Δh_target, ĉ⟩` and `‖Δh_target ⊥ ĉ‖` per side vs `C`. Distinguishes: same displacement, different behavior (→ evaluator or downstream nonlinearity); different displacement per unit `C` (→ units or Jacobian mismatch); displacement plateau (→ saturation).
3. **Rubric decomposition on neutral prompts.** Apply `±d` at matched displacement to neutral prompts and score separately: agreement rate, harshness, sycophancy-specific markers, coherence. If `+d` → generic yes-saying and `−d` → generic hostility with coherence loss, (A1)/(A6) fail and the "trait" is valence. Also calibrates the judge's asymmetry by scoring baseline-vs-baseline.

## 5. Paired / joint extraction

**Hypothesis tested:** there exists a single source direction `d*` such that `J_pᵀ c` is approximately class-invariant — i.e. the mechanism mapping source to trait is linear and shared across contexts. Estimator: `Δg_i = g_i⁺ − g_i⁻` per pair (cancels template/topic gradient noise), or pool both sides' VJPs and shrink jointly.

**Benefit:** proper paired variance, a single vector applicable with `±C` in one metric, and a direct test of (A3): if `d*` works on both sides, the outward-extrapolation story is supported; if it works on neither while per-side vectors work, the mechanism is genuinely class-conditional.

**Confounds:** `Δg_i` mixes `(J⁺−J⁻)ᵀc` (geometry difference) with any shared signal; pairs may not be tightly matched so the difference adds noise rather than cancelling it; and joint extraction loses the "conditional on own class" property, which might be exactly what makes the per-side vectors work. Run it as a comparison against per-side, not a replacement.

## 6. Is "EB helped one side more" coherent?

No. Three independent reasons: (i) both sides changed estimator, so there is no within-side control; (ii) the sides are in different units, so cross-side comparison of any curve is undefined; (iii) the hard-shrink −C curve is missing due to dose-coverage error, so there is no baseline to compare against on that side. Additionally, per §3, the EB change is mostly un-shrinking plus layer reweighting, so even a within-side improvement would need attributing to the right sub-effect.

**Justified narrower claim (observations only):** the EB per-side vectors yield an accepted operating point on each side (−C: effect −0.97/damage 0.42 at C=16; +C: effect +3.47/damage 1.13 at C=44), and the EB direction has cosine ~0.86–0.89 with the hard-shrink direction on each side. Nothing comparative beyond that is supported until the hard-shrink vectors are run at matched displacement on both sides.

## Labels
- **Observations:** the cosines, the two accepted points, the −C grid coverage error, the `vjp_delta` comparison being confounded by multiple differences.
- **Inferences:** `w≈1` for most coordinates under EB with `n=200`; units differ per side; `−d["−C"]` is outward extrapolation from the negative class, not the anti-trait direction.
- **Speculation:** valence confound in `c`; RLHF floor on abrasiveness; judge asymmetry; heavy-tailed gradients inflating `τ²`.

## Completion

- outcome: `complete`
- trace: `/workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-02_claude-fable-5.1_per-side-eb-scientific-brainstorm-fable51.trace.jsonl`
