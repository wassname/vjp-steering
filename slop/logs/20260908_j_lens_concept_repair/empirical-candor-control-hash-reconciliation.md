# Empirical-candor control hash reconciliation

## Observation

The local preflight control hash is `619f4fce627406eab698c960aee05b76ac0aba309ecd6df415c6088cb4544e49`. The successful Modal runtime manifest records `3817b2b56c977eb07ea505ceba5a780b5ce4d824b5df94413b9442d0e2584710`.

The hashes are different. This record retains both values. It does not replace the frozen preflight hash.

## What the saved evidence verifies

The local preflight and successful runtime use the same execution implementation hash `b73a35fbd5587aa363531600b5b0e7ae5c9d13106f1980638b210df33c1830b7`, the same source-vector SHA256 `dd4e78e9c429e51e4fe2d4e70e0db28c96d5c4c218b5f317767393ac38883197`, source side `+C`, behavior target `candidness`, seed `20260909`, layers 13-21, and target-order all-attended-prefill operator.

All nine saved runtime layers have source rank 2 and control rank 2. The largest saved runtime Gram error is `2.980232238769531e-07`; the largest dual identity error is `4.76837158203125e-07`. All nine source-basis hashes are byte-identical between preflight and runtime. No runtime control-basis hash equals its preflight counterpart. The largest absolute difference among the 36 saved source-control cross-Gram entries is `2.2351741790771484e-08`.

`random_gram_matched_component_vector` creates the control with CPU seeded `torch.randn`, CPU QR, Cholesky, and pseudoinverse, then casts basis and dual to source dtype. This construction has no explicit cross-machine bitwise determinism contract. The preflight itself noted that QR/LAPACK conventions could change the hash across machines.

## Limit

The successful runtime output retains control JSON rows and manifest geometry, but does not retain a control safetensors tensor. Therefore the saved artifacts cannot establish bitwise equivalence or exactly locate the differing numerical operation. The same configuration, exact source tensors, near-identical cross-Gram values, and valid runtime geometry make cross-environment floating-point/LAPACK variation plausible. A changed construction is not supported by the saved implementation hash or contract, but cannot be excluded solely from the absent runtime tensor.

## Control-strength limitation

Gram matching constrains basis geometry, not induced patch or logit strength. In the runtime data, source final-token KL from bare is `0.08884294` and source logit-delta norm is `175.8067`; random values are `0.00311300` and `30.2873`. The source is therefore a much stronger realized perturbation in this run. This prevents interpreting the random comparison as an equal-strength placebo. It does not establish behavioral success or failure.

## Decision

Keep the discrepancy visible in endpoint review. Do not launch, rerun, or release the conditional full endpoint from this reconciliation alone.

## Evidence

- `slop/logs/20260908_j_lens_concept_repair/empirical-candor-component-control-preflight.json`
- `slop/logs/20260908_j_lens_concept_repair/empirical-candor-dev-manifest-summary.json`
- `src/vjp_steering/j_lens_concept.py`, `random_gram_matched_component_vector`
- `outputs/experiments/j-lens-components-empirical-candor-dev-v1/` (there is no saved control safetensors file)
