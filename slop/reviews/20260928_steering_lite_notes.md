# steering-lite notes from j-steer_pub (pin 0a064ba) — PI/claude-opus, 2026-09-28

Read-only review. No steering-lite code was changed. j-steer keeps its pin.

## What j-steer uses

- `Vector` / `attach` / `detach`: forward hook on block output, `y += C * sum_k v[k]` on every token (prompt and generated), per selected layer
- `mean_diff`: `unit(mean h+ - mean h-)` at last non-pad token -> `stacked["v"]`
- `pca`: top PC of centered paired diffs, sign set by `v . mean(diff) > 0` -> `shared["v"]`
- `random`: `unit(randn(d, seed*10000+L))` -> `stacked["v"]`
- `make_persona_pairs`: POS/NEG differ only in persona prefix; `thinking=True` puts `<think>` on even-index suffixes
- `_ngram_rep`: `1 - unique/total` trigrams
- VJP: only `VjpDeltaC`, `VjpDelta.apply` (add), `orient_vjp_delta`. j-steer has its own extraction in `src/vjp_steering/vjp.py`.

## Issues (code reading, not run)

| Issue | Where | Affects j-steer? |
|---|---|---|
| `Vector * alpha` scales only `stacked`; PCA keeps `v` in `shared`, so `*` silently does nothing for PCA. Docstring hides this. | `vector.py` `__mul__`, `variants/pca.py` | No (j-steer never multiplies a Vector) |
| Extraction uses `thinking=True` (`<think>` on half the suffixes); j-steer eval uses `enable_thinking=False` | `data/personas.py` vs j-steer `walk.py` | Possibly: train/test prompt mismatch, unmeasured |
| C is a per-layer amount added to every selected layer, so C is not comparable across methods with different layer sets | `attach.py`, variants `apply` | Expected; the dose walk calibrates each method separately |
| `_ngram_rep` is private but imported by j-steer | `calibrate.py` | Breaks if renamed upstream |
| `random` casts to activation dtype (bf16) before normalizing | `variants/random.py` | No (harmless) |
| `__init__` imports all 17 variants + lens/readout modules; import is slow | `__init__.py` | Only speed |
| Persona roster-crossing fix `055bd94` is not in the pin | `data/personas.py` | No: j-steer uses 1 persona tuple, so output is byte-identical |
