# Results

All rows use the same all-100 evaluation cohort. The table reports each named method's seed count.
The random cone shows ten vectors until fewer than half have two coherent directions. The table reports rejected evaluations.

![Judged effect against off-axis change](plot.png)

| method | score↑ | -C on-axis↑ | -C damage↓ | +C on-axis↑ | +C damage↓ | seeds | N | rejected↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| J_word | **-0.123** | **0.340** | 0.463 | 2.075 | 0.626 | 1 | 2 | 0 |
| *random* | -0.782 | -0.425 | 0.357 | 2.995 | **0.553** | 10 | 6 | 5 |
| vjp_mlp_up_shrink | -1.030 | -0.758 | 0.272 | 3.508 | 0.624 | 3 | 2 | 0 |
| pca | -1.600 | -1.149 | 0.452 | 4.085 | 0.848 | 3 | 2 | 0 |
| vjp_delta | -1.756 | -1.485 | **0.271** | 3.715 | 0.697 | 3 | 2 | 0 |
| mean_diff | -1.831 | -1.393 | 0.438 | **4.363** | 0.830 | 3 | 2 | 0 |
