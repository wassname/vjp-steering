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
