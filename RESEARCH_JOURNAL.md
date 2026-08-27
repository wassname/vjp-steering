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
