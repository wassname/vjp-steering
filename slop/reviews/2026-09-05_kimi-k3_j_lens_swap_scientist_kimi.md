---
requested_model: moonshotai/kimi-k3
max_tokens: 20000
final_tokens: 20000
reasoning_effort: low
input_bytes: 11159
trace: /workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-05_kimi-k3_j_lens_swap_scientist_kimi.trace.jsonl
generated: 2026-09-05T03:26:26.356347+00:00
---

# bounded completion

## First call reasoning

Let me carefully analyze this. The task: reconstruct the method from evidence and pseudocode, list distinctions, assumptions, failure modes, alternative formulations, experiments. Separate direct evidence from inference, state what would change my mind.

The core issue: paper formula h' = h + α V(σ(V†h) − V†h) with V = [v_s v_t] raw (unnormalized) J-lens vectors, swap applied at all prompt token positions, hooks only during prompt forward, then cached decode. The working Qwen replication instead uses unit-normalized directions and a directed transfer: h = h − (h·d_s)d_s + (h·d_s)d_t — i.e., it removes the source projection and adds equal-magnitude along target. The current failing implementation uses raw vectors + pseudoinverse two-coordinate exchange, hooks during whole generate, and gets wrong sign at α=1, token leaking at α≥1.125.

Key distinctions to note:

1. Raw vs unit vectors. The paper's equation with raw V swaps coordinates in the dual basis; the magnitude transferred depends on the norms of v_s, v_t. J-lens vectors have norms that vary hugely across tokens (unembedding rows × Jacobian). Candidate A (raw) at α=1 doesn't exchange equal-magnitude content — it exchanges coefficients of differently-scaled basis vectors. If ||v_t|| >> ||v_s||, the added component is huge → leaking/repetition. If ||v_t|| << ||v_s||, effect too weak. This explains α=1.25 producing literal lens-token repetition ("flattering abrasive ...") — the raw target lens vector norm is large, so the swapped activation's unembedding directly reads out that token.

2. Pseudoinverse swap vs directed transfer. With non-orthogonal v_s, v_t, pinv coordinate swap is not the same as "subtract source projection, add equal-magnitude target projection." Candidate C: c_s = h·d_s, h' = h − c_s d_s + c_s d_t. Note: after this, h'·d_s = c_s(1 − d_s·d_s) + c_s(d_t·d_s) = c_s(d_s·d_t) ≠ 0 unless orthogonal. So even C leaves residual source component — the pseudocode notes `expected_nonorthogonal_transfer_source_score()`. Also C doesn't preserve the orthogonal complement of span{v_s,v_t}? Actually h − c_s d_s + c_s d_t: the change is c_s(d_t − d_s), which lies in span. Components outside span unchanged, yes. But paper's swap with pinv also preserves orthogonal complement. Difference: what happens within the span.

Actually let's compare A (unit version, B) vs C precisely. With V̂ = [d_s, d_t] unit but non-orthogonal, pinv(V̂)V̂... c = V̂†h = (V̂ᵀV̂)^{-1}V̂ᵀh. Swap c and reconstruct: h' = h + V̂(σc − c). Within-span component becomes V̂σc. C gives within-span: remove c_s d_s where c_s = d_s·h (not the pinv coordinate), add c_s d_t. In general these differ. When d_s ⊥ d_t, pinv coords = projections, and swap gives within-span: c_t d_s + c_s d_t vs C gives (h − c_s d_s within-span part...) — with orthogonality, C: h' = h − c_s d_s + c_s d_t; within-span component = c_t d_t + c_s d_s (since h's within-span component is c_s d_s + c_t d_t). Swap B gives c_t d_s + c_s d_t. So even under orthogonality, B swaps both coordinates while C moves source's magnitude onto target and zeros source (leaves target coordinate as-is plus adds source magnitude). So B: new coords (c_t, c_s). C: new projections (0 along d_s removal... h'·d_s = 0, h'·d_t = c_t + c_s). Different. So B ≈ reflection, C ≈ one-directional transfer. The paper reports "subtract the projection onto the Soccer lens vector and add an equal-magnitude projection onto the Rugby lens vector" — that textual description matches C more than the formal swap equation! Important: the paper's prose ("subtract projection onto source, add equal-magnitude onto target") matches candidate C, while the paper's formula matches A/B. This is a real discrepancy in the evidence: the quote says "we subtract the projection onto the Soccer lens vector and add an equal-magnitude projection onto the Rugby lens vector." Equal-magnitude projection suggests unit directions and transfer of coefficient — candidate C. So the formula and the prose may be inconsistent, or the formula assumes orthonormalized/normalized V.

3. Hook scope: current implementation keeps hooks during all generate steps; paper and working replication apply hooks only during prompt forward, then decode with kv cache. Two consequences: (a) generated tokens' activations get swapped too, which can cause feedback loops (model generates token influenced by edit, edit re-applied, repetition). The observed repetition of literal lens tokens at α≥1.125 with hooks active during generate is consistent with this. (b) Also the paper's protocol swaps at all *prompt* token positions; generate-time positions weren't in the protocol. So current run confounds intervention form with intervention scope.

4. Wrong-sign at α=1 in the sycophancy task: effect=-0.607 means behavior moved opposite to intended? "effect" presumably target-side behavior measure. Sign error could arise because fixed pair abrasive/flattering applied across unrelated prompts without checking that source concept is active — the paper explicitly first confirms the intermediate concept appears in the J-lens. The pseudocode notes this: "paper-native success is necessary but not sufficient... also needs an observed active source concept and a target chosen per prompt." Applying a swap when c_s ≈ 0 or negative does arbitrary things: pinv swap then writes c_t onto source coordinate etc. Also for sycophancy steering, the relevant "concept" may not be a token-level lens direction at all.

5. Layer band: saved lens covers layers 0..30 of 32-layer model; current band 6..24 (20–80%? of 32 → 6.4–25.6, roughly). Qwen replication found early-mid band 4–13 of 27 gave full effect, late bands weaker. Band choice interacts with where concept is active.

6. Lens fit corpus / Jacobian quality: Jℓ is a mean Jacobian over a corpus — a linear approximation of transport; errors grow for early layers (long transport). The paper excludes first 16 source positions. Qwen3.5-4B lens — is it a real model? Doesn't matter.

7. Failure modes:
- Norm asymmetry of raw lens vectors → wrong magnitudes, token leaking.
- Non-orthogonality of v_s, v_t → pinv swap ≠ prose description; orthogonal complement claim "component of h orthogonal to span is unchanged" holds for A/B but the effective within-span transform differs from C.
- Near-parallel v_s, v_t → pinv ill-conditioned (VᵀV near singular), coordinates blow up. abrasive/flattering are sentiment adjectives — plausibly highly correlated directions! That's a big one: for the country case, " France" and " China" lens vectors may be fairly orthogonal; for abrasive/flattering (antonyms in sentiment space), they could be near-parallel (both encode "strong sentiment adjective") or near-antiparallel, making the 2×2 Gram matrix ill-conditioned and the swap numerically explosive. Check condition number / cosine similarity.
- Hook during generate → feedback.
- max over positions for source_score vs swap at all positions.
- α scaling interacts with normalization choice: with raw vectors, α meaning differs per pair; with unit vectors α is comparable across pairs.
- Baseline-correct filtering needed.
- Model differences: Qwen3.5-4B vs paper's model; the lens was fit with some corpus; if the fit corpus mismatches the deployment distribution, directions are off.
- Tokenization: " France" with leading space; multi-token concepts.

8. Assumptions:
- Linearity: residual transport via mean Jacobian valid at layer ℓ.
- Concept = single token direction; sycophancy concept may be distributed/multi-token.
- The dual-basis coordinate readout is the right notion of "concept coordinate."
- Equal-magnitude transfer preserves behavior-relevant info.
- That the intermediate concept appears at all positions (swap at all positions) — attention-based routing means later positions may carry the concept.

9. Alternative formulations:
- Orthogonalize (QR) V before swap; swap in orthonormal basis.
- Unit-direction swap (B).
- Directed transfer (C) — matches paper prose and working replication.
- Mean-difference steering (activation addition) as baseline: h + α(μ_t − μ_s).
- Difference-in-means / probing direction rather than lens direction.
- Subspace (multi-vector) swap if concept spans multiple tokens.
- Apply at subset of positions (only where c_s above threshold) vs all.
- Hooks prompt-only vs generate-time; also compare swapping only at final prompt position.

10. Experiments:
- Geometry assertions (already in pseudocode): verify pinv swap property, orthogonal complement invariance, condition number of VᵀV, norms ||v_s||, ||v_t||, cos(v_s,v_t).
- Norm-matched raw swap: scale v_t by ||v_s||/||v_t|| and see whether α=1 leaking disappears → tests norm hypothesis.
- Prompt-only hooks vs generate-time hooks, holding operator fixed → isolate repetition cause.
- Reproduce country-pair test on Qwen3.5-4B with each candidate A/B/C before sycophancy: gating experiment. If A fails and C passes, adopt C; if all fail, lens/model problem.
- α sweep per candidate; report hit/stayed/damage curves.
- Second country pair replication.
- Early-mid band vs current band, given Qwen1.7B result that early-mid sufficed.
- Sanity: swap with target = random token should degrade fluency; swap with s=t should be identity (for A/B; C would also be identity). Identity test at α: h' = h when s=t — good unit test.
- Negative α as control: with correct sign, negative α should strengthen source behavior; current negative α=0.5 produced source-token repetition ("abrasive abrasive") consistent with sign confusion plus raw-norm issue.
- Check c_s distribution across prompts: is source concept active (paper's gating)? If c_s ≈ 0, swap is a no-op-ish for C but not for A (A also writes c_t onto source axis... actually A swaps coordinates; if c_s≈0 but c_t≠0, the prompt now gets source-concept written in — sign/wrong-direction effects).
- Sycophancy-specific: choose target per prompt, verify active source, use unrelated-prompt controls.

11. What would change my mind: e.g., if raw-vector A with prompt-only hooks reproduces country result at α=1 on Qwen, then normalization isn't essential and the failure is elsewhere; if C also fails country pairs on Qwen3.5-4B, suspect lens quality/band; if condition number small and norms equal, norm hypothesis dead.

12. Directly shown vs inference:
Direct: paper formula, prose description, official repo lacks intervention hooks (so no official reference for the swap implementation!), replication code does normalized directed transfer and reports 97.2%, current code does raw pinv exchange with generate-time hooks and fails.
Inference: that norm asymmetry causes leaking; that prose matches C intentionally; that hook scope causes repetition; these are hypotheses with tests.

Note the important fact: official repo has no intervention hooks — so the "paper equation" is only from the paper text; the only working implementation evidence is C. Also note the paper's prose ("subtract projection, add equal-magnitude") is literally C. So my reconstruction: the method is ambiguous between two readings; the prose reading + working replication point to C; the current failure used the literal-formula reading with raw norms and extended hook scope.

Also: sign conventions — "α=1 uses the positive paper-formula path; negative alpha is extrapolation control" and α=1 gives effect=-0.607 (wrong sign). With a true swap at α=1 there's no sign to get wrong — swap is symmetric s↔t except that prompt expects a_s→a_t mapping... Actually the swap is symmetric: exchanging coordinates turns source-ish into target-ish. Wrong-sign behavior suggests that what's being measured as "effect" moved toward source... Hmm, for the sycophancy task with fixed abrasive/flattering pair, "effect" presumably means change in target-direction behavior. A swap should increase target. Getting wrong-sign at α=1 with raw vectors could happen if pinv coordinates with near-parallel vectors produce sign-flipped coefficients: if cos(v_s, v_t) > 0 large, Gram matrix [[1,ρ],[ρ,1]]... pinv coordinates c = G^{-1} Vᵀh (with raw norms in G). If v_s ≈ v_t nearly parallel, c_s and c_t are huge with opposite signs; swapping them writes huge opposite content — nonsense. That yields erratic sign. If v_s ≈ −v_t (antipodal sentiment), G ≈ [[n_s², −n_sn_t],[−n_sn_t, n_t²]] also near-singular → same blowup. So for antonym pairs the two-coordinate exchange is degenerate almost by construction: the "exchange two entries" operation assumes the two directions form a well-conditioned 2D basis. Country names might too be correlated but apparently enough.

Also the max over positions: source_score uses max over positions but swap applies at all positions — mild inconsistency vs paper? Paper applies at all positions too.

Also: "the first 16 source positions are excluded" in lens fitting — BOS/positional artifacts.

Let me also reconstruct the full pipeline:
1. Fit Jℓ per layer: average Jacobian d h_final / d h_ℓ over fit corpus, via cotangent sums over valid future targets, mean over source positions excluding first 16.
2. Lens vectors: vℓ[tok] = W_U[tok] Jℓ (row of unembedding transported back).
3. Verify source concept visible: projection of hℓ onto vℓ[s] large at intermediate layers.
4. Intervention at band layers, all prompt positions: coordinate exchange in span{v_s, v_t} (paper formula), or per prose/replication: transfer source projection to target direction with equal magnitude.
5. Continue forward; greedy/sample decode with cache; hooks off after prompt.

Missing evidence: no official hook code; no reported α for the prose example; replication n=36 details, baseline 35/64; no per-layer norms; no cosine between abrasive/flattering lens vectors; no ablation of hook scope yet; "Qwen3.5-4B" lens provenance (fit corpus) unstated.

Mathematical expressions for tests:
- Condition number: κ(VᵀV); cos θ = v_s·v_t/(||v_s||||v_t||).
- Show C and B equivalence condition: equal iff c_t = 0... under orthogonality B gives coords (c_t, c_s), C gives projections (0, c_s + c_t). Equal when c_t = 0. So distinguishing experiment: pick prompts where target coordinate c_t is nonzero and see which behavior matches paper.
- Norm test: run A with V scaled to unit norm (== B) — if behavior fixes, norm is the culprit.

Also worth noting: α in C vs paper: "target appears when swap strength doubled to α=2" — in C, α scales both removal and addition. In the paper formula, α scales delta. At α=1 full swap.

One more distinction: replication swaps on normalized directions means the *amount* added equals source projection magnitude; paper formula with raw vectors adds coefficient×raw vector — if lens vectors for frequent tokens have larger norms... unembedding row norms vary.

Also the estimator detail: Jℓ maps layer-ℓ residual to final residual basis; lens_l(h) = unembed(Jℓ h). So v[tok] = row of W_U Jℓ corresponds to logit contribution direction. unit(v) used in replication.

Also potential failure: greedy vs sampling decode; official says "samples the continuation," pseudocode uses greedy_decode — deterministic eval choice, fine but note.

Also: "damage" metric and admissibility threshold in sycophancy runs; α=1.125 damage 1.167 rejected — the operator magnitude explodes between 1.0 and 1.125, consistent with ill-conditioned pinv (coordinate blowup) rather than smooth scaling? Actually with fixed V, delta scales linearly in α, so damage jumping from 0.14 at α=1 to 1.167 at 1.125 is superlinear → nonlinear model response, or the write magnitude already large. Hmm, delta linear in α so activation change is linear; damage superlinearity is model behavior. Token leaking at 9/15 outputs.

Also the "effect=-2.807 at α=1.25" — sign flips back negative; nonmonotonic, consistent with regime where patched activations go off-manifold and behavior is noise.

Also: fixed pair across unrelated prompts means for many prompts neither concept is active; the swap then exchanges near-zero coordinates (should be near no-op for B/C with small coefficients, but for ill-conditioned pinv, coordinates can be large even when projections are moderate). This alone could explain damage with raw pinv: c = pinv(V)h amplifies h's components when V near-singular, and the swap writes amplified content. Key quantitative check: compare ||V(σc−c)|| vs ||h|| across prompts for the abrasive/flattering pair vs France/China pair.

Priority experiment list:
E0 (diagnostic, no behavior): norms, cosine, κ, coordinate magnitudes on actual prompts for both pairs; verify identity when s=t.
E1: geometry assertions on A vs B vs C.
E2: country-pair gate on Qwen3.5-4B, prompt-only hooks, candidates A/B/C × bands; measure hit/stayed/damage.
E3: hook-scope ablation: A with prompt-only hooks vs generate hooks.
E4: norm ablation: A with per-vector rescaling.
E5: only then sycophancy, with per-prompt active-source gating and per-prompt target.

What would change my mind:
- If A with prompt-only hooks passes country gate at α=1 → hook scope was the main bug, not normalization.
- If C fails the country gate on Qwen3.5-4B while it passed on Qwen3-4B → lens/model-specific; distrust cross-model transfer of method.
- If κ small and norms matched yet A still wrong-sign → my ill-conditioning hypothesis wrong; look at sign conventions in scoring.
- If pinv(V)h magnitudes are comparable to h across prompts → damage not from amplification.

Uncertainty about "Qwen3.5-4B" — a model I may not know; treat as given.

Also note assumption: layer indexing/fraction mapping (0.20–0.80 of 32 = 6.4–25.6 → layers 6..24 roughly matches current). Qwen replication band "10–34" for a 36-layer model (Qwen3-4B has 36 layers), same fraction ~0.28–0.94. Early-mid 4–13 of 27 for 1.7B (28 layers) gave full effect — suggests the causal locus is early-mid, and current band 6–24 includes late layers that may add damage without benefit.

Also: the paper first confirms the concept appears; for the sycophancy abrasive/flattering application, no such confirmation was done — the source concept "abrasive" presumably refers to persona/behavior, but the lens vector is for the token " abrasive" — using a token lens vector as a proxy for a behavioral concept is a category leap. Even if the geometry is fixed, the sycophancy test requires: source concept active in prompt, target chosen per prompt (pseudocode's final note). Also whether "abrasive/flattering" as adjective directions steer behavior at all — could test with simple activation-addition baseline.

Organization: I'll structure as:
1. Reconstruction of the method (what the evidence shows).
2. The central ambiguity: formula vs prose; three candidate operators with exact math; when they coincide/differ (theorem-ish statement).
3. Directly shown vs inferred table-ish.
4. Key distinctions/assumptions.
5. Failure modes ranked with mechanism hypotheses tied to observed run facts.
6. Alternative formulations.
7. Experiment plan ordered by information gain per cost, with pass/fail interpretations.
8. What would change my mind; missing evidence.

Explain observed facts:
- wrong sign at α=1, fluent: hypotheses H1 ill-conditioned pinv with near-parallel/antiparallel pair; H2 sign convention in effect scoring; H3 hook-at-generate feedback. Distinguishing checks.
- repetition of literal lens tokens at α≥1.25: raw vector norms large → patched h unembeds as those tokens; plus generate-time hooks reapply on generated tokens causing self-reinforcement ("flattering abrasive" alternation suggests both directions written strongly — swap writes both coordinates, both tokens become high-logit at their positions... the alternation flattering/abrasive is consistent with both v_s and v_t being written with large magnitude at generate positions, each decoded token then re-patched).
- negative α=0.5 → source token repetition: negative α scales delta negatively, pushing toward... with raw norms and wrong geometry, extrapolation writes source direction strongly.

Actually, the alternation "flattering abrasive flattering abrasive" strongly suggests both lens directions get written with large magnitude at each generate step and the model alternately decodes each — supports generate-time-hook + raw-norm hypothesis.

Condition for A≡C: A with unit vectors equals C iff c_t(dual coord of target) relationships... keep simple: B and C coincide (for α=1) iff the target dual coordinate is zero and source dual coordinate equals source projection; guaranteed when v_s⊥v_t and h has no target component. State: operators differ unless v_s ⊥ v_t and c_t = 0; measure both on data.

Length: this is a technical deep-dive; markdown with headers and some math is appropriate. Should be thorough but not bloated. Aim ~1200-1800 words equivalent. Use LaTeX-ish notation sparingly in plain text.
## First call answer

# J-Lens Coordinate Swap: Reconstruction and Review

## 1. Reconstruction of the method

**What the supplied material directly shows.** The pipeline has four stages:

1. **Lens fitting.** For each layer ℓ, estimate `Jℓ`, the mean input–output Jacobian transporting a layer-ℓ residual into the final residual basis: inject one-hot cotangents at every valid future target position, sum gradients over targets `p' ≥ p`, average over source positions `p` (excluding the first 16), average over a fit corpus. The "lens vector" for a token is `vℓ[tok] = W_U[tok] @ Jℓ`, i.e., a row of `W_U Jℓ` — a direction in layer-ℓ residual space that reads out as that token.
2. **Eligibility check.** Confirm the source concept's lens coordinate is actually present at intermediate layers before intervening.
3. **Intervention.** Over a band of layers, at *all prompt token positions*, modify `h` within `span{v_s, v_t}` only, leaving the orthogonal complement untouched; then let the forward pass continue and decode from a KV cache with hooks removed.
4. **Evaluation.** On baseline-correct prompts only, score whether the answer flips from `a_s` to `a_t`.

**The central finding of this review is that "the intervention" is not one operation.** The supplied evidence contains three inequivalent operators, and the record is split on which is "the paper's":

- **Formula reading (candidates A/B):** `h' = h + αV(σ(V†h) − V†h)` — a symmetric two-coordinate exchange in the *dual* (pseudoinverse) basis. This is what the current failing implementation runs, with **raw** (unnormalized) vectors.
- **Prose reading (candidate C):** the paper's own text says "we *subtract the projection onto the Soccer lens vector and add an equal-magnitude projection onto the Rugby lens vector*." That sentence describes a **directed, unit-norm transfer**: `h' = h − (h·d̂_s)d̂_s + (h·d̂_s)d̂_t`. This is *exactly* what the working Qwen replication implements (`coeff = h @ da; h = h - coeff*da + coeff*db`), and it reports 97.2% hit / 0% stayed on countries.

These coincide only under restrictive conditions. With unit vectors, B and C agree at α=1 iff `v_s ⊥ v_t` **and** the target dual coordinate of `h` is zero. Neither is guaranteed, and both are measurable in one line each (`cos(v_s,v_t)`, `pinv(V̂) @ h`). The raw-vector version A additionally inherits the *norm ratio* `‖v_s‖/‖v_t‖`, so "equal-magnitude transfer" is violated by construction whenever unembedding-row norms differ across tokens — which they generally do.

A second load-bearing fact: **the official repository contains no intervention hooks.** There is no authoritative reference implementation of the swap. The only working behavioral evidence on an open model uses operator C.

## 2. Direct evidence vs. my inference

| Claim | Status |
|---|---|
| Paper formula is a dual-basis two-coordinate swap; official repo ships no hook code | Direct (quoted) |
| Paper prose describes directed equal-magnitude projection transfer | Direct (quoted) |
| Working replication uses unit directions + directed transfer; 97.2% on countries (n=36, baseline-correct) | Direct (quoted) |
| Current run: raw pinv swap, hooks live during all of `generate`, fixed abrasive/flattering pair, α=1 wrong-sign, α≥1.125 leaks literal lens tokens | Direct (quoted) |
| Prose and replication indicate the *intended* operator is C, and the formula tacitly assumes well-conditioned, comparable-norm V | **Inference** |
| α=1 wrong-sign and α≥1.125 token-leaking are caused by (i) raw-norm asymmetry, (ii) ill-conditioned pinv for a near-parallel/antiparallel adjective pair, and/or (iii) generate-time hook feedback | **Hypotheses, not established** (tests below) |

## 3. Assumptions and distinctions that matter

1. **Raw vs. unit vectors.** Under A, α has pair-dependent units; under B/C, α is comparable across pairs. Unembedding row norms vary with token frequency, so A's "swap" can be a large-magnitude *write* of the target direction — sufficient to explain an unembedding-level leak of the literal tokens `flattering`/`abrasive`.
2. **Dual coordinates vs. projections.** For non-orthogonal `v_s, v_t`, `V†h` is not `(h·v_s, h·v_t)`. As `|cos(v_s,v_t)| → 1`, `κ(VᵀV) → ∞` and the dual coordinates become large with opposite signs even when `h`'s projections are modest. **Antonym adjective pairs like abrasive/flattering are precisely the case where near-parallel or near-antiparallel lens vectors are plausible** — country names may be far better conditioned. The swap writes `V(σc − c)`, so an ill-conditioned dual readout amplifies noise into the residual stream. This is my leading candidate for the wrong-sign-at-α=1 result, and it is checkable without running the model.
3. **Symmetric swap vs. directed transfer.** A/B write `c_t` onto the source axis *and* `c_s` onto the target axis; C zeros the source projection (up to non-orthogonality residue: `h'·d̂_s = c_s(d̂_s·d̂_t)`) and adds `c_s` along the target. If the prompt has nonzero target coordinate `c_t`, A/B move it; C leaves it. For "redirect the answer" these usually agree; for "remove concept X" they do not.
4. **Hook scope.** Paper and replication patch the prompt forward only, then decode from cache. The current implementation patches every decoding step. The observed `flattering abrasive flattering abrasive …` alternation is exactly what generate-time patching of a two-sided raw swap predicts: both lens directions get written with large magnitude at each new position, and each decoded token is re-patched, self-reinforcing. The current run therefore **confounds operator choice with hook scope**; no conclusion about the operator is possible until scope is fixed.
5. **Band.** The 1.7B replication ablation (early-mid 4–13 alone gives the full effect; late bands degrade monotonically) suggests the causal locus is early-mid and late layers add damage without benefit. The current 6–24 band is untested against that finding on the 4B model.
6. **Concept eligibility.** The paper gates on the source concept being *observably active* in the lens. The sycophancy run applies a **fixed pair across unrelated prompts** with no activity check and no per-prompt target. Even a geometrically perfect swap fails that design: when `c_s ≈ 0` and `c_t ≈ 0`, C is a near-no-op but an ill-conditioned A need not be (dual coordinates can be large when projections are small).
7. **Token-vs-behavior category leap.** `v[token]` is a direction for a *token*. "Abrasive vs. flattering persona" is a behavioral concept that may be multi-token, multi-position, or not linearly represented by these two directions at all. The pseudocode's final note — paper-native success is necessary but not sufficient — is correct and should be treated as a gating requirement, not a footnote.
8. **Lens quality.** `Jℓ` is a *mean* Jacobian — a linearization of transport, presumably degrading for early layers and off-distribution prompts. The fit corpus for the 4B lens is unstated in the evidence (missing evidence).

## 4. Failure modes (ranked by prior × explanatory power for the observed run)

- **F1: Ill-conditioned dual basis** for the adjective pair → amplified, sign-unstable writes. Predicts wrong-sign at α=1 with fluency preserved (the write is large but lies near a real direction) and superlinear damage growth in α.
- **F2: Raw-norm asymmetry** → target-direction write large enough to unembed as the literal token. Predicts leaking scaling with `α·‖v_t‖`.
- **F3: Generate-time hook feedback** → repetition/alternation loops. Predicted by the scope mismatch alone.
- **F4: Inactive source concept on unrelated prompts** → swap is noise injection; inflates "damage," deflates "effect."
- **F5: Band misplacement** → reduced hit rate, extra damage.
- **F6: Lens misfit on this model/corpus** → all operators fail together. This is the null that must be excluded before blaming any operator.
- **F7: Sign convention bug in the effect metric** (cheap to check; the negative-α run producing *source*-token repetition is weakly consistent with metric-vs-geometry confusion, though F1–F3 suffice).

## 5. Alternative formulations worth keeping on the table

- **QR-orthogonalized swap:** swap coordinates in an orthonormal basis of `span{v_s, v_t}`; best-conditioned version of the formula reading.
- **Mean-difference steering:** `h' = h + α(μ_t − μ_s)` from contrastive prompt sets, ignoring the lens entirely — a baseline the lens method must beat to justify itself.
- **Position-selective patching:** patch only positions where `c_s` exceeds a threshold, vs. the paper's all-positions rule.
- **Subspace swap:** if the behavioral concept spans several lens directions, swap a k-dimensional block.
- **Asymmetric α:** scale removal and addition separately (`h − α₁c_s d̂_s + α₂c_s d̂_t`); the paper's "α=2 sometimes needed" hint suggests removal/addition magnitudes are not behaviorally symmetric.

## 6. Experiments, ordered by information gain per cost

**E0 — pure geometry, no model runs (do first).**
For the abrasive/flattering pair and the France/China pair, at each band layer, compute:
```
cos_s,t;  ||v_s||, ||v_t||;  κ(VᵀV)         # raw and unit
median over prompts of ||pinv(V)h|| / ||h||   # dual-coordinate amplification
```
*Interpretation:* if `|cos| > ~0.9` or amplification ≫ 1 for the adjective pair but not the country pair, F1 is confirmed as a *sufficient* mechanism for the sycophancy failure regardless of behavior. Also run the identity check `s == t ⇒ h' == h` (holds for A/B/C at α=1; a failure is a bug, not science).

**E1 — operator identity on data.** Compute `B(h) − C(h)` on real prompts; report the fraction of variance where they differ. This tells you whether the formula-vs-prose ambiguity is empirically relevant or academic.

**E2 — country-pair gate on Qwen3.5-4B (the decisive experiment).**
Prompt-only hooks; candidates A, B, C; bands {current 6–24, early-mid, 0.28→last-fitted}; α ∈ {0.5, 1, 1.5, 2}; both country pairs; baseline-correct filter; report hit/stayed/damage.
*Decision rule:* if C passes and A fails at matched α, adopt C and treat the formula reading as requiring normalization; if **all** fail, F6 (lens/model misfit) is live and no sycophancy conclusion is reachable; if A passes once hooks are prompt-only, F3 was the main bug and my F1/F2 ranking is wrong.

**E3 — hook-scope ablation.** Hold operator fixed (use A to maximize expected effect): prompt-only vs. generate-time hooks. *Prediction:* leaking/alternation disappears with prompt-only hooks. This is the cleanest test of F3.

**E4 — norm ablation.** A with per-vector rescaling to matched norms (≈B). If leaking vanishes, F2 confirmed.

**E5 — only after E2 passes: sycophancy redesign.** Per-prompt observed-active source, per-prompt target, unrelated-prompt controls, and a mean-difference steering baseline. Also a metric audit: verify "effect" sign against a hand-labeled handful of generations before trusting any α sweep.

## 7. What would change my mind

- A passing the country gate at α=1 with prompt-only hooks → normalization is inessential; F3 dominates; I retract the F1/F2 ranking.
- C failing the country gate on this model while succeeding on Qwen3-4B → the method does not transfer across lenses/models; all operator-level discussion is moot until lens quality is established.
- Small κ and matched norms for abrasive/flattering, yet still wrong-sign → F1 dead; audit the metric sign convention (F7) first.
- B(h) ≈ C(h) everywhere on real prompts → the formula/prose discrepancy is empirically vacuous and I'd stop treating it as the central issue.

## 8. Missing evidence

No official hook implementation; the lens fit corpus and its match to deployment distribution; per-layer norms/cosines for any pair; the replication's full n=36 breakdown and damage metric; the definition of "effect"/"damage" in the sycophancy runs; whether any α between 1.0 and 1.125 was tried with prompt-only hooks. The single largest gap is that **every behavioral failure reported here comes from one operator (A), one scope (generate-time), and one ill-motivated pair** — the current record cannot distinguish a broken method from a broken instantiation, and E0/E2 are cheap enough that there is no reason to argue about it further without running them.

## Completion

- outcome: `complete`
- trace: `/workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-05_kimi-k3_j_lens_swap_scientist_kimi.trace.jsonl`
