# Repository review: misconceptions and bugs

Reviewed dev3 starting at `9d55120`, 2026-09-12. Author: PI/OpenAI. Two fresh helpers reviewed steering and results independently of the parent's reporting review. Parent inspected their evidence and the decisive production code. No paid calls, GPU runs, production fixes, README edits, or pushes were made for this review.

## Decision

Do not draw a method-level conclusion from the current comparison yet. There are reproducible implementation, plotting, and reporting defects. They do not prove that repaired J-lens will work, nor do they invalidate every historical measurement. Repair reproducibility and source comparability before spending on another behavioral sweep.

## Ranked findings

### 1. Experiment settings can silently fail to change the extraction (high)

`scripts/experiment.py:685-691` validates only method/model/dtype for non-concept extraction reuse. Requested layers, target layer, seed, sample count and injection concepts can differ without rejecting cached vectors. The production dispatcher also drops `--lens-file` for swap/unit/injection at 577-580, 598, 613; MLP dispatch at 651-659 drops target-layer and layer selection.

CPU checks changed these arguments and observed successful cache validation or missing extractor kwargs. An experiment can therefore be labeled as a new condition while using an old or default extraction. Historical contamination is not established by this test.

Repair: validate one resolved extraction identity before cache and completed-cell shortcuts; forward supported flags and reject unsupported flags. Tests must exercise the dispatcher and cached path.

### 2. VJP-delta has no class-derived sign; zero directions become NaNs (high)

`src/vjp_steering/vjp.py:1247-1277` computes `(A_positive - A_negative)^T c`, where c is itself positive-minus-negative. Swapping labels negates both factors, leaving the vector unchanged. The actual extractor returns identical `[0.7071,0.7071]` vectors under label swap in the CPU fixture. Thus positive coefficient does not automatically mean movement toward the positive class. Installed steering-lite has an orientation step; this local extractor omits it.

A constant-Jacobian fixture correctly gives zero raw difference, but line 1276 normalizes it into `[nan,nan]`. Reject undefined/nonfinite vectors rather than hiding them with epsilon.

Historical caveat: published runs predate current source and do not fully identify their extraction implementation. No historical sign error is inferred solely from this current defect. Choosing a different VJP estimator or orientation rule is a method decision, not a silent bug fix.

### 3. Publication artifacts cannot currently be regenerated through the documented path (high)

`src/vjp_steering/results.py::primary_methods` omits random from the seed map consumed by `_summary`. Calling the production summary on the committed CSV raises `KeyError('random')`. Separately, `scripts/export.py:190` calls `judge_diagnostics(cells)` where cells are tuples from `score_cell`; diagnostics expects judgment dictionaries and raises `TypeError`. The export self-test still passes.

The existing README random row also differs from the current summary's sign acceptance rules; fixing only the missing map yields an unconfirmed negative side, not the published score. Treat the PNG/table as saved artifacts, not presently reproducible outputs.

Repair: production end-to-end CPU export/render test against fixed saved inputs; compare generated rows with committed tables and explicitly explain changes. Do not overwrite scores merely to make the test pass.

### 4. DEV Pareto lines use rejected doses, and its random polygon uses ID order as dose order (high)

`src/vjp_steering/results.py:658-663` filters Pareto anchors by complete and in-range, not admissible. Actual plot-path checks include rejected J-lens swap +C1.29883458 as a curve anchor. DEV mean_diff +C ends at rejected `(2.74,1.1233)` while its selected marker is `(3.4333,0.6833)`. The line is not anchored to that marked accepted endpoint.

The appended random dose ID9 represents fraction 0.40 but comes after IDs0/1 at fractions 0.66/0.74375. Using append-only identity order for polygon geometry connects high dose back to low dose. Immutable IDs must remain immutable; geometric ordering must be separate.

Full-data `_smooth_anchors` uses B-spline control points, not interpolation through intermediate measurements. For anchors `(0,0),(1,0.1),(2,1)`, the curve at x=1 has y=0.3. This preserves endpoint anchoring but should not be described as passing through all measured means. Both existing full PNGs also visibly clip the right mean-difference label.

Repair: keep rejected dots separately visible if desired, but form a valid coherent curve through its chosen endpoints. Define the empirical random boundary and sort geometry by its defined coordinate, not bookkeeping ID. Verify plotted arrays and visually compare with the user's main-branch reference. Do not mix DEV measurements into a full-cohort publication curve.

### 5. A transient judge failure can retry indefinitely (high operational impact)

`scripts/judge.py:600-613` uses `format_attempt` for HTTP transient retries, but does not increment it before `continue`. A mocked repeated HTTP500 case makes five requests before the test stops it, logging `attempt=1/3` repeatedly. This is not a bounded three-attempt retry.

Repair: a separate bounded transient-error counter and a test that the next request cannot occur after the limit. Persist incurred costs for retries; this review made no network requests.

### 6. J-word and persona extraction are not the representations previously claimed (high conceptual impact)

Actual Qwen tokenization gives `sycophantic -> [' s','yc','oph','antic']` and `abrasive -> [' abrasive']`. `vjp.py:495-503` averages the former fragments' unembedding rows. This is not the paper's single-token concept vector, nor a validated representation of the complete word. My previous statement that J-word was already an equivalent, losing baseline was unjustified.

Current persona extraction contains 200 suffix entries from 65 unique user messages. Half prepend `<think>`; actual rendering includes a closed empty thinking block followed by another open `<think>` and a fixed story continuation. Evaluation starts before an answer, with thinking disabled. This source mismatch is observed; its behavioral cost remains unmeasured. These are matched persona-prefix perturbations, not independently generated positive/negative response pairs.

Repair: define the intended source contrast and prompt positions, inspect consumed tokens, and validate source behavior. Same evaluation questions do not compensate for different extraction data, word representations, or application scope.

### 7. Reporting turned uncertainty into failure explanations, and forgot completed evidence (high conceptual impact)

`RESEARCH_JOURNAL.md:182` says vendor-normalized ranks were never checked. Direct inspection of the corrected-vendor saved trial finds nine layers of raw and normalized candidate ranks; L16 raw source/target 6/7 becomes 4/9 after normalization. The pending claim and duplicate diagnostic recommendation were wrong.

The paper's 54–70% two-hop top-1 and 40–53% function top-1 results are different tasks from its 88% category top-5 result. They neither demonstrate general unreliability nor explain the Qwen persona outcome. An association between source loading and success does not identify our failure mechanism. Small variance in a direction does not prove it has little causal effect, particularly after rescaling.

Intervals crossing zero are inconclusive, not evidence of equivalence or failure. Per-scenario heterogeneity is not solely judge noise. Claims that no cohort size can resolve an effect, or that a method is "dead", were unsupported. Preserve measured responses while withdrawing those explanations.

### 8. Statistical and regression tests give misleading reassurance (medium)

`slop/scripts/20260909_escape_bootstrap.py:91-105` reuses one order resample for duplicate scenario occurrences, unlike its stated independent within-draw resampling. Its bootstrap mean is printed as the damage point estimate; with observed damage difference zero, a symmetric fixture reports +0.5003. Comparator selection is held fixed, so these intervals do not cover full random-region selection uncertainty.

`tests/test_j_lens_vendor_readout_regression.py:36-44` compares duplicated local calculations without calling the production readout helper. A production normalization regression could pass it. The production helper currently includes normalization; the defect here is test coverage.

Repair: compute observed estimators directly, state the uncertainty model, and test actual production functions with nonuniform normalization and nonsymmetric Jacobians.

### 9. The +C rubric contradicts itself; historical measurement identity is incomplete (high concern)

`scripts/judge.py:436-440` always says "Naming the flaw is the target behaviour", while ordinary +C `target_text` requests more sycophancy, including accepting the user's premise. This is a verified prompt contradiction, not a demonstrated sign error in the resulting judgments. Changing it requires a new rubric version, not silently recomputing old scores under the same identity.

The full CSV does not record judge model, rubric, prompt hash, pass count, or score-definition version. A single cache scan finds 200/200 required keys and exactly reconstructs the selected empirical-candor full result, but cannot reconstruct two sampled historical MLP rows under the current judgment contract. The cause of their damage discrepancy remains unknown; different metric versions are one possibility, not an established finding. Same evaluation cohort does not establish the same measurement contract.

Repair: resolve the prompt contradiction and bind published rows to original judgment keys and estimator version. Preserve historical scores pending exact reconstruction.

## Verification and limits

- Parent CPU evidence: [reporting_checks.log](../logs/20260912_repo_review/reporting_checks.log).
- Steering review and runnable fixtures: [steering report](20260912_steering_review.md), [discriminators.py](20260912_steering_evidence/discriminators.py), [log](20260912_steering_evidence/discriminators.log).
- Results review: [results report](20260912_results_review.md); production checks: [checks.py](20260912_results_review_checks.py), [log](20260912_results_review_checks.log).
- Reporting sources and statistics: [reporting review](20260912_reporting_review.md).
- Scope, raw sample, and ml-debug checks: [review scope](20260912_review_scope.md).

No full model run was replayed. Historical cache coverage and extraction implementation remain incomplete. Failed configuration tests establish current defects, not their causal role in every old run. The review does not certify the rest of the repository.

## Recommended order

1. Bound retry behavior; validate extraction identity and CLI dispatch; specify the judge target without contradictory instructions.
2. Restore saved-data export/render reproducibility and correct curve membership/geometry.
3. Resolve VJP sign, zero-vector handling, and source/token representation mismatches.
4. Correct unsupported publication/journal claims with minimal author-reviewed edits.
5. Only after these CPU checks, consider a separately authorized matched-data behavioral comparison.
