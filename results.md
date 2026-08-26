# Results

All rows use the same all-100 evaluation cohort. Named-method points are means over three seeds.
The random cone shows ten vectors until fewer than half have two coherent arms. The table reports rejected arms.

![Judged effect against off-axis change](results.svg)

| method | steer dir | seeds | arms | rejected | peak on-axis | damage at peak |
| --- | --- | --- | --- | --- | --- | --- |
| vjp_delta | -C | 3 | 18 | 10 | -1.849 | 0.477 |
| vjp_delta | +C | 3 | 19 | 0 | +2.988 | 0.245 |
| mean_diff | -C | 3 | 29 | 15 | -1.492 | 0.703 |
| mean_diff | +C | 3 | 31 | 9 | +4.370 | 0.695 |
| pca | -C | 3 | 29 | 24 | -1.227 | 0.963 |
| pca | +C | 3 | 32 | 15 | +4.090 | 1.031 |
| random | -C | 10 | 30 | 4 | +4.075 | 0.724 |
| random | +C | 10 | 30 | 1 | +3.851 | 0.470 |
