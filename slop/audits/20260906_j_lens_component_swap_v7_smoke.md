# J-lens concept-coordinate swap v7 smoke

The tiny end-to-end test completed extraction, generation, judging, and export. The saved log ends:

> `J_LENS_CONCEPT_PIPELINE_SMOKE_PASS id=j-lens-components-coordinate-swap-tiny-smoke-v7b actual_lens=true generation=true judge=true export=true public_outputs_untouched=true`

The extraction metadata records:

- non-negative GP16 reconstructions for both concept components;
- the coordinate exchange $h' = h + \alpha V(\operatorname{swap}(V^\dagger h) - V^\dagger h)$;
- application to all attended prefill positions;
- independently unit-normalized basis rows as an explicit commensurate-coordinate convention;
- identical saved vector hashes for `+C` and `-C`, as required for one symmetric exchange basis.

The smoke used `wassname/qwen3-5lyr-tiny-random`, so its judged behavioral scores are not evidence about sycophancy. It established that the intervention changes logits, restores clean logits after removing its registered forward hooks, saves and reloads the vectors, generates responses, reaches the judge, and exports without changing the public outputs.

A read-only review found that the first v7 draft rounded the basis and dual separately to BF16, mislabeled a hidden-element metric as a coordinate metric, retained an unsafe default calibration source, and allowed negative $\alpha$ into the normal bidirectional results path. V7b preserves the float32 basis and dual, tests a non-axis-aligned BF16 case, records direct coordinate-exchange residuals, requires an explicit source experiment, and rejects the normal results path. Negative $\alpha$ remains an extrapolation control only.

Files:

- Log: [`../logs/20260906_j_lens_native/component-swap-v7b-smoke.log`](../logs/20260906_j_lens_native/component-swap-v7b-smoke.log)
- Export: [`../../data/dev/j-lens-components-coordinate-swap-tiny-smoke-v7b/results.csv`](../../data/dev/j-lens-components-coordinate-swap-tiny-smoke-v7b/results.csv)

— PI/OpenAI Codex
