# Offline projection-removal precheck — PASS

PI/OpenAI Codex. **No GPU inference, Modal app launch, model download or judge API call was made.** Both research goals remain open. This is a numerical and routing check, not behavioral evidence.

## Implementation and provenance

`projection_patch` in the existing `scripts/scratch/j_lens_additive_concepts.py` implements `h' = h - u(u^T h)` using FP32 projection arithmetic and one final cast to the input dtype. `u` is the normalized, frozen saved GP(sycophancy) component. It reuses `source_contrast(True)` to reconstruct the same single-concept direction; normalization removes that helper's previous magnitude scaling. No direction fit, new words, layer change or dose search.

The shared `intervention` hook selects this operator only with `projection_removal=True`. Existing additive paths remain the default. The actual `run()` and Modal entrypoint now accept the separately named `--projection-removal` mode, restricted to fraction1, minus-only, 15 treatments plus one fraction0 identity. Output directory and condition/method names are distinct. Existing loading, tokenizer identity sequence, current-position schedule, next-block checks and incremental persistence are reused. A future run verifies the offline source/vector/implementation hashes before loading model weights.

- Model revision: `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`.
- Source artifact SHA256: `9b47dcb594efc67f9b3491013273106346a0afb8c32fea3a6111e6121ca34a53`.
- Transfer-state SHA256: `b69925310ad2b2744e107442b1d283569d106365fda73c5a1ec98f857bf169e9`.
- Baseline reference SHA256: `b5ebc369ad048844e64456e1949206af0450383f40c33f891f27b9a47727c985`.
- Tested runner SHA256: `979d88b25d1b0c7f8da66b548b188be66540524bcbf49e897b754a756dce0f04`.

Saved dictionary rows times saved GP weights independently reconstruct the positive component in FP64. Unit directions agree; all three bare-state model revisions and prompt token IDs match the baseline reference.

## Independently replicated bare-state projections

| State | FP64 coordinate / requested norm | Actual BF16 update norm | FP64 residual coordinate | Orthogonal update error norm |
|---|---:|---:|---:|---:|
| legal-pnf01 | 0.2411386849 | 0.2405044436 | +0.0012365722 | 0.0170106399 |
| TCA | 0.2885251460 | 0.2882512212 | +0.0008821076 | 0.0187149518 |
| CSN | 0.0643275518 | 0.0654060394 | +0.0009176762 | 0.0160355234 |

The prior constant subtraction norm was about2.886455, much larger than these coordinates. This precheck reproduces the review's proposed distinction; it does not establish what the coordinate means behaviorally.

## 102 source + 3 bare states

210 cases =105 states × fractions0/1. All105 fraction1 updates are nonzero. Fraction0 is bitwise identity for every saved state.

| Quantity, fraction1 | Min | Median | Max |
|---|---:|---:|---:|
| FP64 requested norm |0.0005173945|0.3800512602|1.4616189459|
| Actual BF16 update norm |0.0001556790|0.3796747327|1.4612786770|

All105 residual projections are nonzero after BF16 rounding; largest absolute residual0.0048526813, largest orthogonal change0.0205346642. A tiny requested update can have large relative rounding error, as the minimum norms demonstrate. Do not claim exact coordinate zero or BF16 idempotence. Ideal FP64 projection is idempotent and preserves the orthogonal component to1e-12; actual residuals and orthogonal changes are bounded by independently computed FP64 update error and elementwise BF16/FP32 rounding bounds. All per-state numbers and bounds are saved in `offline-bf16.json`. The one negative source coordinate is removed toward zero, not blindly pushed negative. Sign-inverting the direction leaves removal unchanged.

These are source states and three bare final-prefill states only. No DNL state or actual DEV decode trajectory was available or generated.

## Actual hook and runner checks

- Real tiny Qwen3.5 hybrid model: fraction0 and fraction1 cached generation, next-block exact receipt, nonfinal positions unchanged, fraction0 exact generated IDs, post-context cleanup, exceptional cleanup.
- The old additive patch is poisoned with an exception during these tests: the projection route must be used.
- Separate local transport fixture executes the actual `run()` function over all15 scenarios using shared hooks at layer17, while replacing model/tokenizer transport with CPU fixtures. It verifies exactly15 minus treatments+one identity, projection metrics on every call, persistence and routing. Its printed responses are reused baseline fixtures, **not generated behavioral results**. Temporary fixture generations are deleted.
- Existing additive CPU tests at alpha1/2/4 and the single-concept alpha4 route pass; their artifact writes are redirected to temporary directories. Full stdout is in `additive-regression.log`.
-41 protected source/result/judgment/public-output hashes remain unchanged.

Full command and output: `precheck.log`, EXIT_CODE=0. `precheck-attempt1.log` is an earlier successful precheck before the final implementation-hash guard and regression additions; final evidence is `precheck.log`. `cli-help.log` confirms the Python CLI flag. An unthread-limited help invocation timed out locally at20s; no associated process remained, and the OMP_NUM_THREADS=1 retry completed. No paid failure or retry occurred.

## Exact continuation (subsequently authorized; see amendment below)

Offline rerun:

```bash
OMP_NUM_THREADS=1 PYTHONPATH=src uv run --no-sync python slop/logs/20260907_j_lens_projection_removal/precheck.py
```

Implemented future generation CLI, only after separate authorization:

```bash
OMP_NUM_THREADS=1 PYTHONPATH=src uv run --no-sync modal run scripts/scratch/j_lens_additive_concepts.py::launch --alpha 1 --projection-removal
```

This would request one H100 container with timeout360/retries0 and persist `outputs/audits/20260907_j_lens_projection_removal/generation.json`. This Modal launch was not executed. The existing 30-treatment additive report functions were deliberately not broadened; a future minus-only behavioral audit must explicitly handle15 treatments/30 judgments rather than reuse those cardinality assumptions silently.

At offline completion the budget was unchanged: **$2.61988872744 unreserved**. The offline precheck itself reserved/spent nothing; all outstanding reserves intact. Numerical gates pass. Subsequent mid-run parent authorization in `slop/handovers/j_lens_v10_projection_execution.md` reserves$0.60 for exactly one minus-only run and30 unchanged judgments, leaving$2.01988872744 unreserved. This authorization arrived after offline verification; execution evidence will be saved separately. Projection removal is state-dependent and not norm-matched to prior random controls; better behavior could reflect weaker updates rather than coordinate-zero targeting specifically.
