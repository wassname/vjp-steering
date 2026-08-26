# Results

All rows use the same all-100 evaluation cohort. Named-method points are means over three seeds.
The random cone shows ten vectors until fewer than half have two coherent arms. The table reports rejected arms.

![Judged effect against off-axis change](plot.png)

| method | score↑ | -C on-axis↑ | -C damage↓ | +C on-axis↑ | +C damage↓ | seeds | arms | rejected↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean_diff | +2.232 | 1.492 | 0.703 | 4.370 | 0.695 | 3 | 60 | 24 |
| vjp_delta | +2.057 | 1.849 | 0.477 | 2.988 | 0.245 | 3 | 37 | 10 |
| pca | +1.662 | 1.227 | 0.963 | 4.090 | 1.031 | 3 | 61 | 39 |
| random | +0.830 | -0.425 | 0.357 | 2.995 | 0.553 | 10 | 6 | 5 |
