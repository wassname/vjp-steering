# Results

All rows use the same all-100 evaluation cohort. Named-method points are means over three seeds.
The random cone shows ten vectors until fewer than half have two coherent directions. The table reports rejected evaluations.

![Judged effect against off-axis change](plot.png)

| method | score↑ | -C on-axis↑ | -C damage↓ | +C on-axis↑ | +C damage↓ | seeds | N | rejected↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vjp_delta | **+1.371** | **1.849** | 0.477 | 2.988 | **0.245** | 3 | 37 | 10 |
| mean_diff | +0.789 | 1.492 | 0.703 | **4.370** | 0.695 | 3 | 60 | 24 |
| pca | +0.265 | 1.227 | 0.963 | 4.090 | 1.031 | 3 | 61 | 39 |
| *random* | -0.782 | -0.425 | **0.357** | 2.995 | 0.553 | 10 | 6 | 5 |
