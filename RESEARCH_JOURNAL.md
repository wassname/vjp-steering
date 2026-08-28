# Research Journal

Append-only. Newest entries are at the end.

## 2026-08-27 -- Reverse dose walks from the coherence boundary

This note records a planned change to dose walks and two method ideas.

Evidence: wassname reported in this session that walks used about 15 dose points per method, while only the last third was useful after judging. The current walk code detects an Illinois bracket before it inserts a dense tail. Source: `scripts/walk.py:261-285` and wassname's 2026-08-27 session request.

The proposed walk first finds a dose beyond coherence, then evaluates doses back toward zero. For mean difference, the sketch is to find a boundary near `C=0.7`, then use `C=1.5, 1, 0.75, 0.5, 0.25`. This removes the increasing small steps around zero. The random zone means doses that can change outputs before the judge establishes target-directed movement. Its extent is unknown before judging because `C` is method-relative.

Interpretation (Pi): reversing the current walk is a plausible way to remove early low-dose evaluations that rarely affect selection. The claimed speedup is untested. The next walk should compare its evaluated-dose count and selected judged dose against the current grid before treating the estimate as established.

Future work from wassname's session request:

- [ ] Add J-word steering. The implementation details are in `j-steer-dev`.
- [ ] Add VJP steering that intervenes on `mlp.up` rather than the residual stream. Use all layers and account for extraction noise with the standard deviation between samples. The accumulated layer interventions may build up and cause incoherence at lower doses, so compare the coherence boundary as well as target-directed movement. It seems more powerful in preliminary observation, but no comparison is recorded here.

The next walk should test this selection rule against a full grid before it replaces the current procedure.

## 2026-08-27 -- J-word persona contrast

This note records the word choice for the public J-word comparison.

Evidence: wassname specified in this session, "J word should use the two persona words only" so it is directly comparable to the extraction personas. The public runner defines those personas as `sycophantic` and `abrasive` in `scripts/walk.py:24-26`.

Interpretation (Pi): use the unembedding contrast `sycophantic - abrasive`, rather than a broad list of positive words. This makes the J-word readout match the two persona labels while remaining a lexical probe.

The public implementation will log the token ids and the full lens provenance with this contrast.

## 2026-08-27 -- Real-model smoke for the new methods

This smoke checked the deployed path for the two new steering methods.

Evidence: `uv run modal run scripts/run_modal.py::smoke` exited zero. Its log recorded the published Qwen3.5-4B lens with `n_prompts=1000` and the `sycophantic - abrasive` cotangent. The MLP-up method recorded target layer 29, 29 source layers, global norm 16.579, and 142094 live coordinates. Source: `docs/slop/audit/20260827_modal_new_methods_smoke.md`.

Interpretation (Pi): both methods execute on the real model. The J-word smoke was already incoherent at `C=1`, while the MLP-up smoke generated distinct but eight-token-truncated text. Neither two-item smoke supports a steering-quality claim.

The next run must use coherent doses and the full evaluation cohort before judging.

## 2026-08-27 -- J-word full-cohort descending walk

This run evaluated one deterministic J-word vector on all 100 benchmark prompts at five doses below the incoherent `C=1` smoke point.

Evidence: [J-word C=0.5 artifact](outputs/run_20260827T085318_J_word_s0_c0p5/J_word.json) records `"+C": ["unfinished", "role_leak", "repetition"]` and `"-C": ["unfinished", "repetition"]`. Its first `+C` output becomes "The decomposition should be structuredureded" and repeats "The". Its first `-C` output repeats "The abrasive". [J-word C=0.25 artifact](outputs/run_20260827T085320_J_word_s0_c0p25/J_word.json) records empty `breakdown_reasons` for both sides. Its complete first three-arm sample is in [moral_demos.jsonl](outputs/run_20260827T085320_J_word_s0_c0p25/moral_demos.jsonl): the `+C` arm says "You should run the regression separately for each legal system", while the `-C` arm says "There is no single recommended cadence".

Interpretation (Pi): the health gate places the observed J-word boundary between `C=0.25` and `C=0.5`. This is a coherence result only. The blinded judge must select a target-directed dose from `C=0.25, 0.125, 0.0625, 0.03125`; no steering-quality conclusion follows yet.

## 2026-08-27 -- J-word judged selection

This note records the completed judge pass for the J-word descending walk.

Evidence: [task 134's saved complete log](docs/slop/audit/20260827_task_134_jword_judge.log) begins with the five named run arguments and ends `JUDGE_COMPLETE required=3832 missing=0`. [The raw-output index](docs/slop/audit/20260827_jword_raw_output_index.md) links a fixed bare/+C/-C sample from every dose. [The result rows](data/results.csv) record C=0.5 as inadmissible on both sides, with off-axis perturbations 4.02225 and 4.1005. At C=0.25, the +C and -C rows are both admissible with effects 1.39175 and 0.18475 and off-axis perturbations 0.22175 and 0.3675.

Interpretation (Pi): C=0.25 is the selected J-word dose because it is the largest admissible dose and the judge measures target-directed effect on both sides. This is a one-seed result. My read is that it is probable the effect estimates change with a new extraction sample or seed, because the method has no seed replication here.

The completed MLP-up judge pass is the remaining result needed for the combined table and plot.

## 2026-08-27 -- MLP-up judged selection and rendered comparison

This note records the full-cohort MLP-up judge result and its addition to the comparison artifacts.

Evidence: [the saved judge log](docs/slop/audit/20260827_task_139_mlp_up_judge.log) ends `JUDGE_COMPLETE required=4840 missing=0` after naming all fifteen runs. [The raw-output index](docs/slop/audit/20260827_mlp_up_raw_output_index.md) links bare, +C, and -C outputs for every dose and seed. [The rendered table](results/index.md) reports MLP-up VJP score +0.505, with -C on-axis 0.861 at damage 0.356 and +C on-axis 2.027 at damage 0.234. Its seed count is 3 and its candidate count is 10. [The result rows](data/results.csv) record all thirty source arms.

Interpretation (Pi): the MLP-up method has a complete three-seed model-judge measurement with a positive score under the existing per-direction dose selection rule. My read is that the asymmetric directions need an independent judge before a stronger behavioural conclusion, because the selected +C and -C endpoints come from different doses and the current measurements use one judge model.

The table and plot now include the two requested methods alongside the unchanged baselines and random control.

## 2026-08-28 -- Invalidated Modal validity rerun

Evidence: the Modal app `ap-c8wV0flWrodaoxL0nChKOu` stopped with MLP-up seed 0 at C=3.563594872561357. Its complete server log ends `AssertionError: duplicate rung: method='vjp_mlp_up_shrink' seed=0 coefficient=4.0`. The pulled certificate [outputs/walk_vjp_mlp_up_shrink_s0.json](outputs/walk_vjp_mlp_up_shrink_s0.json) has `status: RUNNING`. The other pulled certificates include run directories dated 2026-08-27, such as the first J-word rung `outputs/run_20260827T085324_J_word_s0_c0p03125`.

Interpretation (Pi): the stopped rerun adopted manual artifacts by matching method, seed, dose, and configuration. This makes the certificates unable to establish a single fresh validity run. The two C=4 MLP-up seed-0 artifacts also differ in generated text and health statistics, so choosing one would add an unrecorded selection rule. The existing manual rows are invalid for the requested corrected comparison.

Action: walk artifacts now carry a required `walk_id`; a walk adopts only artifacts with its exact identifier. The four requested walks will restart under `validity-20260828-r2` before any API judge or public artifact update.

## 2026-08-28 -- Isolated sixth-octave walks complete; judge blocked before API access

Evidence: `just modal-pull` recovered four `COMPLETE` certificates: [J-word seed 0](outputs/walk_J_word_s0.json) and [MLP-up seeds 0, 1, and 2](outputs/walk_vjp_mlp_up_shrink_s0.json). Each records the `2^(n/6), n=-30..84` grid. The first rung artifacts record `walk_id: validity-20260828-r2`, for example [J-word C=0.03125](outputs/run_20260828T015026_J_word_s0_c0p03125/J_word.json). MLP-up's three seed certificates place the -C boundary at grid 52, C=12.699208415745595; J-word's certificate places it at grid 21, C=0.3535533905932738.

The fresh-only manifest contains 185 runs and 37,000 demo sides. [Pueue task 5 audit](docs/slop/audit/20260828_task_5_api_judge_credential_failure.md) quotes its complete log: it computed 34,400 required content cells, with 33,380 missing, then failed at `KeyError: 'OPENROUTER_API_KEY'` before an API request or a judge output. Task 5 ran `uv run python scripts/judge.py` directly, which bypassed `justfile`'s `set dotenv-load` and therefore the existing ignored `.env` key.

Interpretation (Pi): the fresh walks satisfy the requested artifact provenance and dose-grid conditions. There is no corrected behavioral result yet. The failure was a queue-command error, not a missing credential: requeue `just judge --walk-id validity-20260828-r2`, require `JUDGE_COMPLETE missing=0`, inspect raw A/B records, then export and render the replacement public artifacts. Manual rows remain invalid and must not enter the export.

## 2026-08-28 -- User-approved sweep grid algorithm

Evidence: user decision in this session, not a measured result. For every method and seed, bracket the maximum coherent coefficient independently for `+C` and `-C` with a bounded Illinois/Newton search. Keep the previous `C` definition and configuration so results remain comparable. Publish the largest generated coherent lower bracket, not an ungenerated numerical root. Construct the previous log grid through that bound, but generate and judge only `grid[ceil(0.66 * len(grid)):]`, the final third of that direction's grid.

Interpretation (Pi): fixed shared-grid comparison rows are invalid under this decision. Rerun every compared method with independent directional endpoints and final-third generation and judging. This entry specifies the requested procedure only; it reports no behavioral or measurement result.
