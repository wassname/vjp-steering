# Results

DEV15 comparison only. Every point passed exact scenario, shared-bare, generation-config, AB/BA judgment, and coherence provenance checks.
The gray region and measured gray dots are five random vectors. It is a descriptive reference, not a confidence interval. This first comparison does not show J-lens outside the measured random points in either direction. `not eligible` means an incoherent or wrong-direction measured point; raw rows are in `dev-comparison.csv`.

## Measured dose paths

![Measured dose paths](plot-dev.png)

## Pareto-smoothed paths

![Pareto-smoothed paths](plot-pareto-dev.png)

| method | score↑ | -C on-axis↑ | -C damage↓ | +C on-axis↑ | +C damage↓ | seeds | N | not eligible↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean_diff | **+2.750** | **5.477** | 0.910 | **3.433** | 0.683 | 1 | 24 | 20 |
| j_lens_unit_L16 | +0.423 | 0.603 | 0.180 | 1.480 | 0.283 | 1 | 29 | 17 |
| j_lens_injection_doubt_L16 | +0.343 | 1.160 | 0.283 | 0.743 | 0.400 | 1 | 10 | 3 |
| j_lens_swap_L16 | +0.130 | 0.453 | 0.323 | 1.787 | 0.367 | 1 | 29 | 15 |
| j_lens_swap | +0.040 | 0.513 | **0.130** | 0.080 | **0.040** | 1 | 21 | 13 |
| j_lens_injection_L16 | -0.210 | 0.227 | 0.180 | 0.587 | 0.797 | 1 | 10 | 6 |
| vjp_delta | — | 2.217 | 0.423 | not confirmed | — | 1 | 21 | 19 |
| *random* | — | not confirmed | — | 1.913 | 0.527 | 5 | 4 | 1 |
