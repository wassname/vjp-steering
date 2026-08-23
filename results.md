# Results

All rows use the same all-100 evaluation cohort. Named-method points are means over three seeds.
The random cone shows ten vectors until fewer than half have two coherent arms. The table reports rejected arms.

![Judged effect against off-axis change](results.svg)

| method | steer dir | seeds | arms | rejected | peak on-axis | damage at peak |
| --- | --- | --- | --- | --- | --- | --- |
| vjp_delta | -C | 3 | 17 | 14 | -1.826 | 0.556 |
| vjp_delta | +C | 3 | 22 | 0 | +3.525 | 0.395 |
| mean_diff | -C | 3 | 29 | 17 | -1.805 | 0.502 |
| mean_diff | +C | 3 | 31 | 12 | +4.311 | 0.665 |
| pca | -C | 3 | 29 | 27 | -1.310 | 0.917 |
| pca | +C | 3 | 32 | 18 | +4.158 | 0.981 |
| random | -C | 10 | 30 | 4 | +4.075 | 0.724 |
| random | +C | 10 | 30 | 1 | +3.851 | 0.470 |
