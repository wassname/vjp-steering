Inherited decisions:
- The full-residual run is a diagnostic control for the failed GP16 result, not a paper-native J-lens result.
- Its causal value depends on changing only GP16 → full residual while keeping sources, split, layers 13–21, target-order operator, dose grid, DEV cohort, and judge fixed.
- No layer selection based on behavioral outcomes is allowed.
- All-100 evaluation and public plotting require broad intended-sign effects in both fixed directions.

Diagnosis:
- **Choose A: calibrate all nine layers unchanged.**
- Aggregate `-C` eligibility is 2,172/8,829 layer-position observations, which is sufficient to run this inexpensive diagnostic. The undefined word “nontrivial” prevents treating extraction eligibility as a confirmatory pass, but it does not justify blocking the measurement that directly resolves whether those positions affect logits, text, and behavior.
- Selecting a subset now would confound the intended GP16/full-residual contrast with a layer change. Option B therefore weakens causal attribution.
- Option C is premature because calibration is the cheapest direct test of the reviewer’s concern.
- The `0/135` bare final-position result predicts weak `-C`, but does not imply a causal no-op:
  - Hooks modify each block’s output.
  - Earlier-position changes at layer \(L\) can alter the final position through attention in later layers.
  - Eligibility at later layers was measured on the bare forward pass. Upstream intervention can change later coordinate ordering, activating a layer that was nearly identity on bare inputs.
- Conversely, low-eligibility layers are harmless only when their treated-forward coordinates remain ordered. If upstream patches reverse ordering, those layers become active. That composition is part of the predeclared nine-layer operator and should be measured rather than removed.

Drift / contradiction check:
- The reviewer’s proposed layer selection conflicts with the earlier decision to isolate decomposition loss by changing only GP16 to the complete residual.
- Quietly redefining “nontrivial” as “nonzero at every layer” would also change the extraction condition after observing its values.
- Treating bare eligibility as fixed intervention activity would be incorrect because later-layer eligibility can change under upstream patches.
- The extraction should be described as **technically valid but directionally asymmetric**, not as having conclusively satisfied a previously numerical eligibility threshold.

Recommendation:
- Run the unchanged all-nine DEV calibration with alpha:
  - `0, .25, .5, .75, 1, 1.25, 1.5, 2`
  - layers 13–21
  - all attended prefill positions
  - fixed `+C` and `-C` labels
  - no layer selection or source changes.
- Before judging, record per side, layer, and dose:
  1. treated-forward eligible and changed position counts;
  2. treated-forward final-position eligible and changed counts;
  3. realized patch-norm distribution;
  4. coordinate residual and relative error;
  5. final-logit delta norm and KL;
  6. number of changed outputs and generation-health findings.
- Alpha zero must remain exact. Read every generation before judging.
- Predictions:
  - `+C` should produce substantially larger final-logit and text changes than `-C`.
  - Some later `-C` layers may become eligible after upstream patches; if none do, `-C` acts only through earlier-position pathways.
  - Broad intended signs in both directions would support GP16 information loss.
  - Real numerical exposure with mixed, null, or wrong-sign semantics would implicate the matched final-prefill source or target-order operator.
- Behavioral success remains the predeclared broad criterion: intended mean and median sign, at least 10/15 intended-sign scenarios, and mean steered off-axis score below 1.5 for each direction.
- Stop this matched-source/target-order design if both directions reach exposure comparable to v15 but still fail that behavioral criterion.
- Use v15 as the exposure scale:
  - `+C` alpha 2: logit norm `229.38`, KL `.28011`, 15/15 outputs changed.
  - `-C` alpha 2: logit norm `76.196`, KL `.017437`, 10/15 outputs changed.
- If full-residual `-C` remains below that exposure while coherent, do **one secondary comparison**: extend only its non-negative alpha until it approximately matches v15 `-C` KL or output-change count, or until coherence fails. This is more informative than selecting layers because it preserves the source and operator.
- Do not run a layer subset as the immediate secondary comparison. Since every layer has zero bare final-position `-C` eligibility, subset selection cannot restore a direct final-position pathway and would add a confound.

Risks:
- A failed `-C` semantic result is inconclusive if its realized exposure remains materially below v15.
- Full-residual success would identify GP16 information loss but would not itself produce a publishable J-lens result.
- Full-residual failure localizes the problem only to the combined final-prefill source/target-order mechanism; it does not reject J-lens generally.
- Model revision provenance remains incomplete, although exact activation agreement with v15 makes wrong current-run weights unlikely.

Need from main agent:
- No scientific decision is still required. Proceed with A while documenting that the extraction eligibility condition was qualitative and the reviewer’s stricter per-layer interpretation was not adopted.

Suggested execution prompt:
- “Add treated-forward per-layer and final-position eligibility/change counts to the existing calibration diagnostics without changing intervention behavior. Re-run self-test and tiny smoke. Then calibrate `j-lens-persona-full-components-source-v16` on DEV-15 at alpha `0,.25,.5,.75,1,1.25,1.5,2`, layers 13–21, all attended prefill positions. Preserve fixed labels and read all outputs before judging. Compare numerical exposure with v15; if `-C` is underexposed but coherent, perform one dose-matched extension rather than selecting layers.”
— PI oracle/OpenAI Codex
