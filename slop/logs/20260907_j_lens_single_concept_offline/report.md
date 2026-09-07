# Single-concept offline vector check

Scope: CPU only; no GPU, model loading, API, renderer or score changes. Source-state delivery is not actual DEV delivery or behavioral evidence.

## Provenance and reconstruction

Executed command and complete output: `check.log`; executable calculation: `check.py`; all 204 per-state signed measurements, proposed vector and source identities: `check.json`.

Named source SHA256: `9b47dcb594efc67f9b3491013273106346a0afb8c32fea3a6111e6121ca34a53`, verified by the actual additive runner's `source_contrast`. Pinned Qwen revision and layer17 verified. Positive/negative ordering is sycophancy/skepticism. All102 saved full source states are finite, shape102x2560; their first two mean-subtracted signals reconstruct the saved full signals. Both GP components reconstruct independently from FP64 nonzero weights times saved dictionary rows: maximum errors1.29e-8/8.58e-9,16 nonzero weights each. Prior persona GP-v15/full-v16 metadata hashes match the previously tested bridge constants; exact source prompts/IDs are saved in `check.json`.

## Fixed proposed dose and distinctness

`v = positive_GP * ||positive_GP-negative_GP|| / ||positive_GP||`; alpha4, both signs. Base vector norm0.7216137052; requested update norm2.8864548206. No outcome-based normalization.

| Comparison direction | Cosine to proposed v |
|---|---:|
| Previously tested named raw GP difference |0.522559|
| Named GP normalized-basis gap axis |0.370503|
| Named full normalized-basis gap axis |0.064293|
| Prior persona GP-v15 normalized-basis gap axis |-0.203192|
| Prior persona full-v16 normalized-basis gap axis |-0.094773|
| Named skepticism GP component |0.725456|

Basis gaps are axes of state-dependent operators, not claims of fixed-sign or equal per-step update equivalence. The last row cautions against treating single-concept ablation as semantic isolation: the two named components are correlated. No exhaustive novelty claim.

## Actual source-state BF16 delivery

The actual `additive_patch` passed exact equality against an independent FP64 addition of the BF16-rounded update, followed by BF16 rounding. Alpha0 identity passed on all states.

| Sign | Nonzero | Delivered min / median / max | Maximum relative norm error | Identical to old alpha4 update |
|---|---:|---|---:|---:|
|+|102/102|2.883949 / 2.886809 / 2.889112|0.09205%|0/102|
|-|102/102|2.884953 / 2.887021 / 2.888884|0.08414%|0/102|

Actual update difference from prior raw-difference alpha4 has median norm2.820866 (+) /2.821333 (-), ranges2.817267–2.823120 (+) /2.818672–2.823201 (-). Actual-update cosine to prior ranges0.521913–0.523402 (+) /0.521969–0.523342 (-). Minimum cosine to the proposed requested direction is0.9999664.

## Interpretation and boundary

This is a numerically distinct, nonzero perturbation at the same requested norm, not an identical vector under BF16 rounding. It does not establish improved candor, reduced sycophancy, model-hook scheduling correctness on a fresh DEV trajectory, or a unique causal explanation for any future effect. No paid run is authorized or launched here; non-Claude scientific review and parent decision remain pending. GPU/API cost0; no reserves released. Both project goals remain open.
