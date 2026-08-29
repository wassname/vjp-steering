# Results

Named rows are each seed/sign's greatest health-clean, judge-accepted tail coefficient. They are not peak target-effect doses.
The frozen random cone shows ten vectors until fewer than half have two coherent directions.

![Judged effect against off-axis change](plot.png)

| method | score↑ | -C on-axis↑ | -C damage↓ | +C on-axis↑ | +C damage↓ | seeds | arms | evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| J_word | **-0.123** | **0.340** | 0.463 | 2.075 | 0.626 | 1 | 2 | judged endpoint |
| *random* | -0.782 | -0.425 | 0.357 | 2.995 | **0.553** | 10 | 60 | frozen control |
| vjp_mlp_up_shrink | -1.030 | -0.758 | 0.272 | 3.508 | 0.624 | 3 | 6 | judged endpoint |
| pca | -1.600 | -1.149 | 0.452 | 4.085 | 0.848 | 3 | 6 | judged endpoint |
| vjp_delta | -1.756 | -1.485 | **0.271** | 3.715 | 0.697 | 3 | 6 | judged endpoint |
| mean_diff | -1.831 | -1.393 | 0.438 | **4.363** | 0.830 | 3 | 6 | judged endpoint |
