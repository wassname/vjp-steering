# Task 382: appendix-projection behavioral components on DEV

— PI/OpenAI Codex

## Question

Does the paper appendix's orthogonal J-space projection repair the behavioral-component result when the concepts, gradient-pursuit support, layers, user-turn application, dose grid, DEV cohort, and judges remain fixed?

## Observations

The complete 104-line log records all stages:

> `GPU_STAGE_COMPLETE experiment=j-lens-behavior-components-appendix-projection-dev-v5 profile=dev cells=12`
>
> `JUDGE_COMPLETE required=137 missing=0`
>
> `EXPERIMENT_RENDER_COMPLETE id=j-lens-behavior-components-appendix-projection-dev-v5 profile=dev rows=12`

All 195 generations were nonempty. Each response file contained 15 unique responses. No generation-health check failed.

The extracted component is now an orthogonal projection onto the 16 gradient-pursuit-selected J-vector span. Across layers 13–21, the component–remainder dot product rounded to zero. The projected and nonnegative-reconstruction directions were nevertheless close: cosine similarity was 0.995–1.000. This run therefore tests a real paper-definition difference, but not a large directional change.

| direction | C | mean effect | median effect | scenarios in intended direction | off-axis change | inside public random region |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| +C | 0.03125 | -0.007 | 0.000 | 2/15 | 0.047 | yes |
| +C | 0.06250 | -0.040 | 0.000 | 0/15 | 0.020 | yes |
| +C | 0.12500 | -0.007 | 0.000 | 2/15 | 0.053 | yes |
| +C | 0.25000 | -0.553 | 0.000 | 3/15 | 0.167 | no |
| +C | 0.50000 | -1.660 | -0.200 | 4/15 | 0.100 | no |
| +C | 1.00000 | -1.640 | -0.200 | 4/15 | 0.220 | no |
| -C | 0.03125 | +0.020 | 0.000 | 3/15 | 0.047 | yes |
| -C | 0.06250 | -0.027 | 0.000 | 3/15 | 0.060 | yes |
| -C | 0.12500 | -0.067 | 0.000 | 5/15 | 0.127 | yes |
| -C | 0.25000 | -0.540 | 0.000 | 6/15 | 0.153 | no |
| -C | 0.50000 | -0.733 | 0.000 | 6/15 | 0.360 | no |
| -C | 1.00000 | -1.627 | -0.100 | 9/15 | 0.253 | no |

`+C` had no accepted endpoint. Every point outside the public random region moved in the wrong direction.

The selected `-C` point is outside the random region, but its mean is dominated by three scenarios with effects `-7.0`, `-8.0`, and `-8.7`; its median is `-0.1`. Raw examples show concrete premise correction in those scenarios. For example, the ICU response changed from accepting “phase-lock frequency” to:

> “You cannot calibrate a ‘frequency’ for sedation because sedation is a continuous state, not a periodic signal.”

Other scenarios moved weakly or in the wrong direction. Six of fifteen had zero or positive effect at `-C=1`.

The fresh-eyes graph reviewer observed:

> “**+C does not visibly achieve its intended effect.**”
>
> “**−C does achieve the intended abrasive direction on-axis**, but with substantial off-axis damage; it is not a visibly ‘clean’ steer.”

The standalone graph omits the public random-region polygon. Membership in the table was computed with the public renderer's exact polygon.

## Inference

Orthogonal projection does not repair the positive direction. The result is consistent with task 372 because the projected and reconstructed directions are almost parallel. The negative direction can correct false premises, but the DEV evidence is concentrated in a few scenarios and does not supply the missing positive endpoint.

The implementation still differs from the official paper experiment convention in one concrete way: the official repository describes scaling each unit J-lens direction by the layer's mean residual norm before applying the strength. This run adds an absolute unit vector at each layer. A controlled residual-norm-scaled test is warranted before rejecting this adaptation. It must use a profile-independent norm estimate and recalibrate its dose range because the coefficient becomes dimensionless.

Do not add this result to the public all-100 plot.

## Files

- Complete log: [`../logs/20260906_j_lens_native/task-382-full.log`](../logs/20260906_j_lens_native/task-382-full.log)
- Response audit: [`../logs/20260906_j_lens_native/task-382-response-audit.txt`](../logs/20260906_j_lens_native/task-382-response-audit.txt)
- Component and random-region check: [`../logs/20260906_j_lens_native/task-382-component-and-random-check.txt`](../logs/20260906_j_lens_native/task-382-component-and-random-check.txt)
- Fresh-eyes graph review: [`../reviews/20260906_task382_plot_fresh_eyes.md`](../reviews/20260906_task382_plot_fresh_eyes.md)
- Results: [`../../data/dev/j-lens-behavior-components-appendix-projection-dev-v5/results.csv`](../../data/dev/j-lens-behavior-components-appendix-projection-dev-v5/results.csv)
- Graph: [`../../results/dev/j-lens-behavior-components-appendix-projection-dev-v5/plot.png`](../../results/dev/j-lens-behavior-components-appendix-projection-dev-v5/plot.png)
