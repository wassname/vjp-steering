# Results

All table rows use the same all-100 evaluation cohort. The table reports each named method's seed count.
The random cone shows ten vectors until fewer than half have two coherent directions. The table reports rejected evaluations.
Both figures retain the all-100 baselines and prior methods. The first connects their displayed admissible dose means in dose order. The additional figure shows measured dose means as small dots and smoothly connects bare, the intended-side Pareto-efficient means, and each selected/final endpoint.

## Measured dose paths

![Measured dose paths](plot.png)

## Pareto-smoothed paths

![Pareto-smoothed paths](plot_pareto.png)

| method | score↑ | -C on-axis↑ | -C damage↓ | +C on-axis↑ | +C damage↓ | seeds | N | rejected↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vjp_delta | **+1.371** | **1.849** | 0.477 | 3.806 | 0.314 | 3 | 42 | 28 |
| mean_diff | +0.789 | 1.492 | 0.703 | **4.362** | 0.648 | 3 | 60 | 36 |
| vjp_mlp_up_left_right_shrink | +0.552 | 0.968 | 0.416 | 3.466 | 1.129 | 1 | 11 | 1 |
| vjp_mlp_up_shrink | +0.505 | 0.861 | 0.356 | 3.508 | 0.624 | 3 | 26 | 7 |
| pca | +0.265 | 1.227 | 0.963 | 4.090 | 1.031 | 3 | 61 | 39 |
| J_word | +0.078 | 0.275 | 0.197 | 2.075 | 0.626 | 1 | 13 | 3 |
| j_lens_swap | -0.029 | 0.442 | **0.153** | 0.133 | **0.162** | 1 | 11 | 11 |
| *random* | -0.782 | -0.425 | 0.357 | 2.995 | 0.553 | 10 | 6 | 5 |
