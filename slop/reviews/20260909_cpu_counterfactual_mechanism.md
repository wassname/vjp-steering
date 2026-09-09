# Mechanism review: CPU counterfactual + corrected vendor diagnostic (2026-09-09)

**Verdict: pass.** The counterfactual's math, separation of coordinate presence from downstream final-logit failure, and the proposed L16 single-layer repair are all internally consistent and corroborated by the GPU artifacts; only minor precision caveats apply.

## Checklist

1. **Absent/reversed coordinate vs downstream failure** — Correctly separated. The dual is an exact left-inverse of `basis.T`, so `dual @ h_swapped == flip(c_before)` holds exactly (verified algebraically: `dual @ basis.T = I_2`). L13 shows France c=0.116 vs Germany 0.483, yet the swap still inverts the readout (0.903→-1.221), while `"final_logit_rank": "14->16"` is recorded alongside. Coordinate exists and is exchanged; failure is downstream. Claim supported.

2. **Readout inversion ≠ causal success** — Correctly shown. CPU "before" diffs match the GPU vendor diffs in results.json within 0.03 (max L19: 0.000 vs -0.029), so the CPU readout replays the vendor pipeline; large deltas (L15 -2.26, L13 -2.12) with rank 14→16 unchanged demonstrate readout change without causal success.

3. **L19 tie** — Correctly scoped as single-layer: "Layer19 tie 9.25/9.25 shows clean winner not dominant at that layer" — no global noncausality claim. Minor caveat: the exact 9.25/9.25 is partly a bf16 rounding artifact (float diff -0.029); the qualitative reading (winner not dominant) is unaffected.

4. **Failed results preserved** — Yes: results.json retains clean/swapped logits (France 21.5 top1, Germany rank14→16), the audit keeps the raw-vs-vendor table, and every counterfactual layer record carries "final logit rank14->16 still fails downstream."

5. **Next repair** — Justified. Audit explicitly rejects blind 0–30 sweep (only 13–21 captured) and Germany-dominant bands (would swap Germany out). L16 is France-dominant in both CPU coords (0.454 vs 0.273) and GPU means (0.457 vs 0.064), and is where the exchange moves the readout toward Germany (+0.91). Internally consistent with the exchange operator's symmetry.

## Critical bugs
None.

## Minor notes
- Counterfactual applies swaps per-layer on the clean final-position trajectory, while the real run swapped all 9 layers over 22 positions; it is a linear probe, not a replay of the actual intervention — adequately framed as such.
- Unused `raw_before` in loop 1; loop 1 and loop 2 differ only in redundant bf16 wrapping (numerically identical).
- No new GPU spend; ≤$1 reserve untouched.
