Review this public-repo plan before implementation. Check the VJP math, use of `steering-lite`, fresh-clone proof, data provenance, four-method plot, and deletable work. Return fewer than 300 words with `APPROVE` or `REQUEST CHANGES`.

## Plan

Goal: Publish one readable VJP-delta method and one notebook. Compare VJP-delta with mean difference, PCA, and a random-direction distribution. Keep package and render code below 2000 lines.

Scope in: VJP-delta extraction, additive steering, four-method evaluation data, Markdown and HTML results, and one key plot.

Scope out: method search, forced-choice moral evaluation, old variants, selected 20-question claims, and a new evaluation framework.

Requirements:

- R1: Reimplement only VJP-delta extraction. The public vector must differ from the saved reference by less than `1e-4` in every element.
- R2: Reuse `steering-lite` for mean difference, PCA, random directions, vector storage, and hooks. Copy none of those implementations.
- R3: One notebook extracts all four vector types, generates bare and `+C`/`-C` text, and draws the result plot.
- R4: One measured CSV generates `results.md`, `results.html`, and the plot. The plot shows judged on-axis change against absolute judged off-axis change. Random directions form a band.
- R5: A fresh clone installs and runs the smoke check without the development repo.

Tasks and checks:

1. Write the VJP-delta extraction. Compare its output with the saved 4B reference vector. Also compare unreduced token gradients, valid-position means, class subtraction, and sign against an independent tiny-model calculation.
2. Search the public repo for copied baseline or hook functions, `../j-steer-dev`, `file:`, editable, and local path dependencies. The only method code allowed is VJP-delta extraction.
3. Write one notebook. Execute it in a new output directory. Assert that no development vector or output path appears in the notebook or execution record.
4. Export measured all-100 points. Each CSV row records model, tokenizer, prompt template, data hash, evaluation cohort, layer scope, batch size, date, source run, method, seed, direction, coefficient, judged on-axis change, absolute judged off-axis change, and admissibility. The renderer asserts shared cohort fields and writes Markdown, HTML, and the plot.
5. Clone outside both worktrees. Clear `PYTHONPATH`, create a new uv environment from the lock, confirm no prior outputs, run the smoke check and renderer, recreate all generated results, and record lock resolution and commands. Count source lines.

Likely failures: an editable local dependency; a detached activation graph; missing packages; Markdown and HTML disagreement.

Silent failures: the selected 20 questions enter the plot; method and random rows use different cohorts; cached development text enters the notebook; the VJP output shape passes while token reduction differs.

## Reference data flow

The development implementation does this:

```text
target contrast c = mean(last target activation on positive prompts)
                  - mean(last target activation on negative prompts)
for each class and batch:
    valid = positions from token 16 through the penultimate real token
    target cotangent = c at each valid target position, zero elsewhere
    gradients = autograd.grad(target activations, source activations, target cotangent)
    per prompt and layer = mean gradients over valid source positions
v[layer] = mean(positive per-prompt gradients) - mean(negative per-prompt gradients)
v[layer] = v[layer] / norm(v[layer])
```

The public function will return a `steering_lite.Vector` with `VjpDeltaC`. The `steering-lite` runtime already adds `C * v[layer]` through block hooks. `steering-lite` also supplies `MeanDiffC`, `PCAC`, and `RandomC`. The dependency will use a public Git commit, not a path.

The measured source uses all 100 Bullshit Benchmark questions for method curves. The selected 20-question set is forbidden. The random band must also use all 100 questions; current selected-20 random rows will not be exported.

The saved reference is `vjp_delta_vector.safetensors` from run `all100_20260811T052702_vjp_delta_c0.17677669529663687`: Qwen/Qwen3.5-4B, seed 0, 256 sycophancy-versus-abrasive prompt pairs, source layers 6-24, target layer 29, max length 384, batch size 4, all-valid source and cotangent scopes. The file contains 19 unit vectors of width 2560.
