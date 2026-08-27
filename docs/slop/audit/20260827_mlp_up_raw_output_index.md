# MLP-up full-cohort raw outputs

Each linked file has 300 JSONL records. Lines 1-100 are bare, 101-200 are +C, and 201-300 are -C. Lines 1, 101, and 201 use the same fixed first scenario and provide one complete bare/+C/-C sample. The 100 records per arm are the complete all-100 cohort outputs.

| C | seed 0 | seed 1 | seed 2 |
|---:|---|---|---|
| 8 | [`1,101,201`](../../outputs/run_20260827T090858_vjp_mlp_up_shrink_s0_c8p0/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T090859_vjp_mlp_up_shrink_s1_c8p0/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T090859_vjp_mlp_up_shrink_s2_c8p0/moral_demos.jsonl) |
| 4 | [`1,101,201`](../../outputs/run_20260827T090901_vjp_mlp_up_shrink_s0_c4p0/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T090903_vjp_mlp_up_shrink_s1_c4p0/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T090905_vjp_mlp_up_shrink_s2_c4p0/moral_demos.jsonl) |
| 2 | [`1,101,201`](../../outputs/run_20260827T090904_vjp_mlp_up_shrink_s0_c2p0/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T090907_vjp_mlp_up_shrink_s1_c2p0/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T090905_vjp_mlp_up_shrink_s2_c2p0/moral_demos.jsonl) |
| 1 | [`1,101,201`](../../outputs/run_20260827T091006_vjp_mlp_up_shrink_s0_c1p0/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T091101_vjp_mlp_up_shrink_s1_c1p0/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T091130_vjp_mlp_up_shrink_s2_c1p0/moral_demos.jsonl) |
| 0.5 | [`1,101,201`](../../outputs/run_20260827T091132_vjp_mlp_up_shrink_s0_c0p5/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T091133_vjp_mlp_up_shrink_s1_c0p5/moral_demos.jsonl) | [`1,101,201`](../../outputs/run_20260827T091135_vjp_mlp_up_shrink_s2_c0p5/moral_demos.jsonl) |

The all-100 health summaries in each sibling `vjp_mlp_up_shrink.json` report no `breakdown_reasons` for the included five-dose cohort. The selected result uses all three seeds.
