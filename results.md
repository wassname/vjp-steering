# Results

All rows use the same all-100 evaluation cohort. Named-method points are means over three seeds.
The random cone shows ten vectors until fewer than half have two coherent arms. The table reports rejected arms.

![Judged effect against off-axis change](results.svg)

| method | steer dir | seeds | arms | rejected | peak on-axis | damage at peak |
| --- | --- | --- | --- | --- | --- | --- |
| vjp_delta | -C | 3 | 1 | 5 | -1.944 | 0.562 |
| vjp_delta | +C | 3 | 3 | 0 | +3.502 | 0.406 |
| mean_diff | -C | 3 | 3 | 0 | -1.223 | 0.871 |
| mean_diff | +C | 3 | 3 | 0 | +3.715 | 0.521 |
| pca | -C | 3 | 3 | 0 | -1.360 | 1.495 |
| pca | +C | 3 | 3 | 0 | +3.939 | 0.830 |
| random | -C | 10 | 30 | 4 | +4.075 | 0.724 |
| random | +C | 10 | 30 | 1 | +3.851 | 0.470 |
