# Review scope and ml-debug checks

Author: PI/OpenAI, 2026-09-12. This is a repository review, not a training run. No paid requests, generation, GPU jobs, or publication edits were authorized or made by this review.

## Evidence checks

- Logs read: complete `escape_bootstrap.log` (42 lines), complete reporting CPU fixture log, worker discriminator logs, and the saved paired empirical-candor sample. Primary code and paper passages inspected separately from old audits.
- Configuration: frozen DEV15 comparisons in bootstrap; B=20000, RNG seed 20260909. Review fixture uses B=100000, seed 20260912. Fixture exercises actual AST-extracted `boot_margin`; it does not replay full export/cache dispatch.
- SHOULD lines: no predictive SHOULD lines in the bootstrap log. Review fixture expectation is derived: symmetric AB=-1/BA=+1 has observed effect and damage difference zero against zero comparator. Actual reported damage bootstrap mean: 0.500276.
- Null and baseline: fixture null exactly zero by construction. Research comparison null is matched random-vector cells, not zero steering alone. Saved effect margins against selected seeds cross zero; these are not equivalence bounds.
- Initialization / updates / LR schedule / worst gradient step: not applicable to CPU artifact review. No optimization run was performed.
- One complete raw sample inspected: `20260912_results_review_raw_samples.json`, first AB and BA pair, original cache line 238596. Both responses elaborate fabricated differential indemnity decomposition. Judge evidence: "both treat the fabricated framework as real." This supports preserving the measured failure on that example, not a failure of J-lens as a class.
- Surprises: a completed normalized-rank diagnostic was called pending (explained: older audit and later journal disagree with saved artifact); resampled damage differs from observed estimator (explained: absolute value after order resampling); infinite retry warning stays at 1/3 (explained: transient path does not advance format counter).
- Missing evidence: causal effect of these implementation defects on historical published vectors; complete historical judge-cache reconstruction; broader Qwen workspace-band validation; valid simultaneous inference for an outcome-selected random region.
- Alternative diagnoses for poor persona results remain open. Subjective pre-repair plausibility, not estimated probabilities and not mutually exclusive: extraction/application defects contribute (plausible, 60%); evaluation/selection/plotting distort the comparison (likely, 70%); source persona contrast does not capture the judged epistemic axis (plausible, 60%); other causes (plausible, 30%). Existing defects are verified; their causal contribution to historical outcomes is untested. No percentage here licenses a scientific conclusion.
- Independent review: two fresh helper sessions reviewed production steering and evaluation code. Their signed reports and executable checks are linked from the consolidated review. Same model family; not independent empirical replications.
- Cheapest discriminator: CPU production regression for configuration-to-extraction dispatch and cache rejection, then regenerate tables/plot traces from unchanged saved rows. Expected distinction: implementation fix changes metadata validation/trace membership without changing raw model outputs. This precedes any paid rerun.
- Wall-clock / GPU memory: no GPU use. CPU cache scan covers 2.18GB; scalar checks take seconds. Do not scan the full cache once per comparison when a single indexed pass suffices.

## Interpretation boundaries

The idea: transport a contrastive steering signal through model sensitivity, or use J-lens concept directions.
The implementation tested: current production functions and existing saved artifacts.
Other valid tests: same persona-pair data with a prespecified J-space reconstruction and matched application scope; paired-source concept swaps with validated occupancy.
A failing implementation does not refute those alternatives. Likewise, proving a code bug does not show that fixing it will yield better sycophancy steering.
