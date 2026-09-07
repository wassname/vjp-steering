---
requested_model: moonshotai/kimi-k3
max_tokens: 2400
final_tokens: 1800
reasoning_effort: low
input_bytes: 44040
trace: slop/logs/20260907_j_lens_transfer_probe/science-update/kimi.trace.jsonl
generated: 2026-09-07T16:10:21.380070+00:00
---

# bounded completion

## First call reasoning

Write a bounded independent update: reconstruct method, distinctions, failure modes, what the evidence shows vs inference, what would change my mind.
## First call answer

# Independent update: v16 transfer/persistence diagnostic

## 1. Method reconstruction (what the supplied material directly shows)

**Setup.** A fixed 2D subspace B at layer 17 of Qwen3.5-4B, plus its dual D, from a prior v16 run (not derived from these three questions). Bare and donor prompts differ only by a prepended "bluntly candid about fabricated methods" instruction; both are generated greedily to 512 tokens, and their final-prefill-position layer-17 outputs h_b, h_d are captured.

**Five one-shot patch modes at the final prefill position of the bare prompt:**
- `bare_identity` / `donor_identity`: replace h with the captured h_b / h_d (sanity controls).
- `full`: replace h with h_d — full-residual donor transplant.
- `projected`: h + ((h_d − h) Dᵀ) B — transplant only the B-subspace component of the donor delta.
- `gap`: keep each question's own subspace midpoint, impose the v16 `source_gap` (−7.554) on the dual coordinates — i.e., move the coordinates apart along the basis by the saved gap magnitude, discarding donor location information.

**Persistence run.** Same gap-setting, but applied at the final position on *every* forward through generation (prefill + each decode call), coefficient ∈ {0,1}, with coefficient-0 asserted to reproduce bare token IDs exactly.

**Verification.** Identity controls must match token IDs, first-token logits, and downstream states exactly (reported: 6 transfer + 3 persistent identities exact). An independent pre-hook asserts the next block's input equals the patched value. Downstream states at layers 18–31 recorded; first-token KLs recorded (values not shown).

**Scoring.** Fixed LLM judge, AB and BA orderings, on-axis (naming the fabrication) and off-axis; effects reported as steered−bare. Three questions, selected diagnostically — explicitly *not* a DEV15 sample.

## 2. What the evidence directly shows

1. **Direct instruction works strongly**: donor responses name the fabrication; effects ≈ −6 to −9 on-axis in both orders, all three questions.
2. **Full-residual transplant of the final-prefill state mostly does NOT transfer the behavior.** Leg: effect ≈ 0 (still answers as if real). TCA: partial (−4.6/−1.6, "not a standard methodology" but hedged). CSN: mixed (0.3 AB / −5.0 BA). Response texts stay bare-like in wording.
3. **Subspace-only projection transfers nothing** on-axis (effects ≈ 0 everywhere) despite moving coordinates to donor positions at layer 17 (coefficient 1.0 at layer 17 in measurements).
4. **Gap-setting transfers nothing** one-shot (effects ≈ 0), except a hint on CSN (BA −3.5 with judge awarding partial credit for "cannot use CSN"-adjacent framing — but the text still treats CSN as a real 1990s concept).
5. **Persistent gap-setting transfers partially and question-dependently**: leg ≈ 0; TCA −6.3/−2.0 (partial: "not a standard methodology" but no fabrication-naming); CSN −7.7/−6.0 (names it: "not a standard database tool... cannot use CSN"). Applied gap stays tiny (max ≈ 0.005 vs imposed −7.554), meaning after prefill the model's own state sits near the target coordinates on its own or the hook corrects drift minimally.
6. **Downstream decay**: at layer 17 the patch is exactly placed; by layer 18 the full-transplant state's donor-delta coefficient is already ~0.71–0.79, by layer 21 ~0.35–0.42, by 31 ~0.21–0.31. The transplanted direction is partially washed out within a few blocks. Projected/gap patches decay to near-zero coefficients by layer 21–31.

## 3. Interpretation (inference, flagged as such)

**I1.** The v16 subspace at layer 17, transported via coordinates, does not causally encode the transferable "name the fabrication" behavior in this prompt family. The one-shot projected and gap modes are clean nulls across 3/3 questions. Directly supported within this n=3 diagnostic.

**I2 (stronger, more speculative).** Even the *full* residual transplant largely fails (leg 0, CSN order-dependent, TCA partial), while the same donor state produced the behavior when reached *by the model itself* under the donor prompt. This suggests the behavior is not carried by the final-prefill residual vector at all — it depends on the distributed computation/KV history upstream, which the patch does not transplant (pseudocode explicitly notes this). The layer-17 final-position state may be more an *effect* (readout) of an upstream decision than the *cause* of the downstream text.

**I3.** The partial persistence successes (TCA, CSN) are ambiguous evidence for I2. Two readings: (a) repeatedly nudging every decode step compensates for the washout and the subspace does carry weak causal signal; (b) the persistent hook acts as a generic perturbation that occasionally tips the model into "this isn't real" phrasing without the subspace being the specific mechanism. The data do not distinguish these; notably the TCA persistent text still doesn't call TCA fabricated, and leg — the question where one-shot full transplant failed most cleanly — gets nothing from persistence either. If (a) were cleanly true I'd expect leg to respond too.

**I4.** The maxgap ≈ 0.005 report cuts both ways: it confirms the hook is holding coordinates near target during decode, but also means we cannot tell whether decode-time coordinates *matter*, since they're never allowed to deviate. There is no persistence run with the hook on only during prefill vs only during decode.

**I5 (judge/measurement caveat, recorded scores vs text).** The recorded scores are the fixed rubric's output; my reading of the texts agrees directionally in most cases but I'd flag: (a) CSN bare text ("theoretical concept from the 1990s, never implemented") is itself partially challenge-y — the judge scores it negative because it doesn't say "fabricated," which is correct per rubric, but it shrinks the available headroom; (b) the CSN gap BA −3.5 looks like judge generosity for "Current solutions rely on manual migrations," not premise-naming. Treat single-pair AB/BA effects as ±~1 noisy at minimum; order asymmetries of 5+ points (CSN full: 0.3 vs −5.0) show judge position sensitivity is a first-order error source here.

## 4. Key distinctions and assumptions

- **Coordinate match ≠ state match ≠ behavior match.** Projected mode achieves donor coordinates at layer 17 (coefficient 1.0) with zero behavioral effect — already falsifying "coordinates are sufficient." But it also perturbs off-subspace nothing, so it doesn't test necessity.
- **Full transplant ≠ prompt transplant**: KV cache and all upstream layer states remain bare-computed. The patch changes one vector; everything attending to earlier positions still sees bare keys/values.
- **Final prefill position vs distributed representation**: the choice to probe only the last position is an assumption; the "decision" to name the fabrication may live in earlier positions' states (the instruction tokens' positions), which the donor prompt has and the bare prompt lacks entirely (different token sequence — cannot be transplanted position-wise).
- **Gap magnitude imported from a different context** (source_gap = −7.554 from v16 components) assumes the on-axis separation is context-independent; bare coordinates here ([−1.05, 0.28] etc.) are far from the imposed targets ([−4.16, 3.39] etc.), so gap mode is a much larger coordinate displacement than donor-relative — yet still null. That strengthens the null but also means gap mode isn't "subtle."
- **n=3, selected, one model, one layer, greedy decoding, one judge.** Nothing here licenses claims about DEV15 or generality.

## 5. Possible failure modes of the diagnostic itself

1. **Washout confound**: downstream decay (layer 18 coefficient ~0.7) means even a "correct" transplant may be diluted before it matters. Null results may reflect patch non-persistence, not absence of causal content. Persistence mode addresses this only for gap, not for full/projected.
2. **Hook-position artifacts**: BF16 cast of the patch, batch-1 cache interactions; mitigated by identity controls passing exactly — this is genuinely well controlled.
3. **Judge position sensitivity** (above) can manufacture or erase effects at this sample size.
4. **Prompt-family confound**: the bare CSN/TCA answers are already mildly corrective; the subspace may encode "contradict the user" only when the base rate of contradiction is low (leg), and leg is exactly where persistence fails — opposite of what this confound predicts, which weakens it, but n=3.
5. **Selection**: these three were chosen for diagnosis; unknown on what criterion. If chosen as "hardest," nulls are expected and uninformative about transfer rates.

## 6. Alternative formulations worth testing

- **Multi-position / multi-layer patch**: transplant the donor delta at all positions, or at layers 17–20 jointly. If behavior appears, the representation is distributed, not point-localized.
- **Persistent full/projected**: extend the every-step hook to full and projected modes, isolating whether washout is the binding constraint.
- **Decode-only vs prefill-only persistence** in the gap run (separates setting initial conditions from clamping dynamics).
- **Necessity**: ablate the subspace in the *donor prompt* run (project h_d off B at layer 17). If the donor still names the flaw, the subspace isn't necessary either — closing the causal loop rather than only testing sufficiency.
- **Coordinate-controlled gap sweep**: impose gaps of 0, ¼, ½, 1× source_gap persistently and check for dose response; a flat null at all doses is much stronger than one null at 1×.
- **Judge-side**: swap in a deterministic string criterion ("does not exist / fabricated / no such") alongside the LLM judge for these rubric items; report both.

## 7. What would change my mind

- Persistent *full* transplant succeeding where one-shot full fails → washout explanation (I2 weakened in favor of "right vector, wrong schedule").
- Ablating B in the donor run killing the behavior → subspace necessary; I'd upgrade the subspace claim despite transfer nulls (mechanism present, transport broken).
- Leg persistent gap succeeding after a decode-only variant → my I3 reading (b) weakened.
- More diagnostic questions with consistent nulls for full transplant → I'd treat "final-prefill state is a readout,
## Final answer call answer

# Independent update: v16 transfer/persistence diagnostic (n=3, selected questions)

## Decision

**The v16 layer-17 subspace does not causally transport the "name the fabrication" behavior into bare prompts, by any tested delivery method.** One-shot projected and gap modes are clean nulls (3/3 questions). Full-residual transplant — the strongest possible point patch — mostly fails too (leg ≈ 0, TCA partial, CSN order-dependent). Persistent gap-setting rescues behavior on 2/3 questions (TCA partial, CSN strong) but not leg. Since even the complete donor state at the final prefill position fails to transfer behavior that the same state produced when reached naturally, the working conclusion is: **the behavior is not carried by the final-prefill residual vector; it depends on upstream computation/KV history the patch cannot transplant.** The layer-17 state reads like a readout of an upstream decision, not its cause.

## Strongest objection

The nulls may reflect **patch washout, not absent causal content**: the transplanted direction decays fast downstream (donor-delta coefficient ~0.71–0.79 at layer 18, ~0.2–0.4 by layer 21). Persistence rescuing CSN/TCA is consistent with "right vector, wrong schedule" rather than "wrong vector." Against this objection: leg — the cleanest one-shot failure — also fails persistently, and the TCA persistent text still doesn't name the fabrication. But the rescue/leg asymmetry across n=3 selected questions cannot settle it.

Secondary objections:
- **Judge position sensitivity is a first-order error source**: CSN full shows 0.3 (AB) vs −5.0 (BA) on the *same text pair*. Single-pair AB/BA effects should be treated as ±~1 noisy at minimum; the CSN gap BA −3.5 looks like partial credit for corrective framing, not premise-naming. Recorded scores are the fixed rubric's output; my text reading agrees directionally except there.
- **Headroom**: bare CSN/TCA texts are already mildly corrective ("theoretical concept from the 1990s"), compressing measurable transfer — though the rubric correctly scores them negative for not saying "fabricated."

## What the material directly shows vs. inference

**Direct**: identity controls exact (6 transfer + 3 persistent); projected/gap achieve target coordinates at layer 17 (coefficient 1.0) with zero on-axis effect; downstream decay measured; persistent maxgap ≈ 0.005 (hook holds coordinates throughout decode); n=3, selected, greedy, one judge — nothing licenses DEV15 or generality claims.

**Inference (flagged)**: readout-not-cause interpretation; persistence-as-weak-signal vs. persistence-as-generic-perturbation ambiguity — the data don't distinguish, and the persistent run never lets coordinates deviate, so decode-time coordinate necessity is untested.

## Next check (single most decisive)

**Necessity test, closing the causal loop**: ablate the subspace in the *donor prompt* run — project h off B at layer 17 during donor generation.
- Donor still names the flaw → subspace not necessary; readout interpretation confirmed, transfer program for this subspace stops.
- Behavior collapses → subspace is the mechanism and transport is broken; immediately run **persistent full transplant** (every-step hook, full mode) to separate washout from wrong-vector, plus a **persistent gap dose sweep** (0, ¼, ½, 1× source_gap) — a flat null at all doses is far stronger than one null at 1×.

Cheap parallel fix regardless: add a deterministic string criterion ("does not exist / fabricated / no such") alongside the LLM judge for these rubric items, given the observed AB/BA asymmetries.

**Uncertainties**: selection criterion for these three questions is unknown (if "hardest," nulls are expected and uninformative about rates); one model, one layer, one judge; first-token KLs recorded but not shown.

## Completion

- outcome: `completed_after_follow_up`
- trace: `slop/logs/20260907_j_lens_transfer_probe/science-update/kimi.trace.jsonl`
