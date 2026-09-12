# Reporting and statistical misconceptions

Review of dev3 at 9d55120, 2026-09-12. Author: PI/OpenAI. Review only; no production files changed or paid work.

## 1. A completed diagnostic is described as never run (high, verified)

`RESEARCH_JOURNAL.md:182` says "the vendor-normalized readout was never rank-checked". The older `slop/audits/20260909_j_lens_reference_fidelity.md` ends with that diagnostic still pending. The assistant repeated this in chat and proposed paying for it again.

Direct artifact inspection contradicts this. `outputs/experiments/v14-paper-native-verbal-chat-country-swap-corrected-vendor/results.json` contains `trials[0].clean_layer_lens_readouts` for nine layers, including raw and vendor-normalized candidate ranks. L16 has raw source/target ranks 6/7 and vendor ranks 4/9. Final target rank remains 14 -> 16, with 0/1 top-1 successes. Saved extraction: [reporting_checks.log](../logs/20260912_repo_review/reporting_checks.log). The tracked [corrected diagnostic audit](../audits/20260909_corrected_vendor_diagnostic.md) already records this result.

Impact: stale documentation became an incorrect diagnosis and duplicate-run recommendation. The diagnostic checks one trial, not the entire Qwen layer-band selection. One France/Germany result cannot uniquely decide implementation error versus persona transfer failure.

Recommendation: supersede the pending claim with the completed artifact; retain the unattested Qwen band as a separate limitation. Do not rerun this diagnostic merely because the earlier audit says it is pending.

## 2. Inconclusive comparisons became claims of failure and a known cause (high, verified)

`README.md:11` asserts "no J-lens variant went outside the five-random-vector region in either direction" and connects it to a "loading-dependent single-token effect not surviving". `RESEARCH_JOURNAL.md:182` assigns ~70% to transfer failure without a likelihood model. The assistant further claimed the benchmark cannot resolve sub-1.0 effects "period", that no cohort size could resolve the negative direction, and that a low J-space variance share would make transfer "dead by construction".

The saved bootstrap log instead reports positive and negative possibilities: doubt -C4 versus one selected random seed has margin +0.0167, interval [-1.8800,+1.8833]; L16 swap +C versus another selected seed has +0.4067, interval [-0.7134,+2.3067]. These are not equivalence tests, simultaneous random-region tests, or evidence that the true effect is zero. The uncertainty combines scenario heterogeneity and presentation-order variation, not solely judge noise. A coordinate's magnitude or represented variance is not its causal effect; a small component can matter after rescaling (the paper explicitly rescales perturbations to equal magnitude).

`slop/audits/20260909_low_damage_fairness.md:305-313` calculates k-SE separation from observed effect/SD. This is not a power calculation with a specified rejection level and desired power. The tiny observed -C difference has wide uncertainty, so squaring its reciprocal gives an unstable planning estimate. It cannot establish that more data is inherently useless. The same audit retains the old narrow interval at lines 252-253 after correcting it at 296, and says "the only significant comparison is a +C loss" at 315 despite its caveated corrected interval at 300-303.

Recommendation: report measured configurations and uncertainty, with no general method-death or causal-loading conclusion. Separate an empirical random envelope from inference about a population of random directions. Keep selection uncertainty explicit.

## 3. Bootstrap implementation and its reported point estimate disagree with the description (medium, reproduced)

`slop/scripts/20260909_escape_bootstrap.py:91-105` draws orders once per original scenario per replicate, then resamples scenario indices. Duplicate sampled scenarios reuse their order draw. The docstring claims order resampling within each drawn scenario. These are different sampling schemes.

A CPU fixture calls the actual AST-extracted `boot_margin` function (no replacement implementation): 15 identical scenarios, candidate order values -1/+1, comparator zero. Effect interval is [-0.4667,+0.4667], versus [-0.3333,+0.3333] with independent order draws per sampled occurrence. For this fixture the analytic variance ratio is (2n-1)/n = 1.9333. This does not establish which statistical model best fits the real judges; it demonstrates the code is not the described two-level bootstrap.

More directly, the function returns the bootstrap mean at line 107 and `main` labels that value DAMAGE `point=`. Because damage applies absolute value after order averaging, the bootstrap mean is not the observed estimator. The same fixture has observed damage difference zero but reports approximately +0.5003. Real saved log examples also differ: L16 vs id9 seed4 observed damage difference is 0.1633-0.1200 = 0.0433, not printed 0.0333.

Evidence: [reporting_checks.log](../logs/20260912_repo_review/reporting_checks.log). This test isolates the function; it does not validate end-to-end real-data confidence coverage. The routine also fixes the best seed selected on the observed data rather than reproducing selection, and pairs order draws across distinct judge requests. Neither assumption is justified in the report.

Recommendation: state the estimand first. Compute observed differences directly, choose an explicit paired-scenario uncertainty model, and test duplicate sampling and nonlinear damage handling. Do not label fixed-seed intervals a full zone comparison.

## 4. Paper reliability rates do not establish general unreliability or cherry-picking absence (medium, source verified)

Primary source: Gurnee et al., *Verbalizable Representations Form a Global Workspace in Language Models*, July 6 2026, [paper](https://transformer-circuits.pub/2026/workspace/index.html). Author-reported experiments, not independent replication. Local paper is in the sibling jsteer checkout, not `docs/papers/` in this repository as the journal implies.

At local paper lines 275 and 301 the two-hop and function studies measure target-appropriate top-1 answers. At 215 the category result measures top-5, not top-1. Calling these a single "40–88% effect" merges tasks, models, and endpoints. The paper does more than a selected demonstration, but aggregate results do not themselves rule out task/template selection. The prior assistant's "not cherry-picked" and "honest rates" judgments were stronger than the evidence.

The paper also studies intermediate reasoning, flexible functions, and ablations, not only single-token verbal report. At 305 it says:

> "Workspace loading of the source argument predicts swap success well."

That is an author-reported association within their function task. It does not quantitatively predict our persona outcomes on a different model, word pair, layer band, and generation task. The paper at 215 explicitly says:

> "with every perturbation rescaled to the same magnitude"

This contradicts treating small represented variance as sufficient to rule out useful steering.

Recommendation: cite the exact task-specific rates, scope, and endpoints without using them to explain our failure. Matching the persona-pair extraction data is a sensible comparison to investigate, not a paper-guaranteed repair.
