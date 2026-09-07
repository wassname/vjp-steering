# Results

The primary table uses the all-100 evaluation cohort and reports each named method's seed count. Any appended DEV table uses its separately stated cohort.
The random cone shows ten vectors until fewer than half have two coherent directions. The table reports rejected evaluations.
Both figures retain the all-100 baselines and prior methods. The first connects their displayed admissible dose means in dose order. The additional figure shows measured dose means as small dots and smoothly connects bare, the intended-side Pareto-efficient means, and each selected/final endpoint.

## Measured dose paths

![Measured dose paths](plot.png)

## Pareto-smoothed paths

![Pareto-smoothed paths](plot_pareto.png)

| method | score↑ | -C on-axis↑ | -C damage↓ | +C on-axis↑ | +C damage↓ | seeds | N | rejected↓ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| vjp_delta | **+1.371** | **1.849** | 0.477 | 3.806 | **0.314** | 3 | 42 | 28 |
| mean_diff | +0.789 | 1.492 | 0.703 | **4.362** | 0.648 | 3 | 60 | 36 |
| vjp_mlp_up_left_right_shrink | +0.552 | 0.968 | 0.416 | 3.466 | 1.129 | 1 | 11 | 1 |
| vjp_mlp_up_shrink | +0.505 | 0.861 | 0.356 | 3.508 | 0.624 | 3 | 26 | 7 |
| pca | +0.265 | 1.227 | 0.963 | 4.090 | 1.031 | 3 | 61 | 39 |
| J_word | +0.078 | 0.275 | **0.197** | 2.075 | 0.626 | 1 | 13 | 3 |
| *random* | -0.782 | -0.425 | 0.357 | 2.995 | 0.553 | 10 | 6 | 5 |

## Named-GP additive DEV — incomplete

Incomplete, uncalibrated DEV15; all measured alpha=1,2,4 doses retained. Matched random seeds judged: 5/10 ([0, 1, 2, 3, 4]). Coherence eligibility unknown; no accepted frontier. New layer17/current-position controls are not the historical random cone. Alpha1 minus DNL had identical baseline/steered text and token IDs, but AB invented a quote and scored +1.6; BA scored 0. Random seed0 alpha1 minus legal-pnf03 also had identical answers but BA scored -0.3. Random seed4 CSN minus at alpha1 and alpha2 had identical text, token IDs and same-order judge requests; BA effects were -1.7 and -7.7, while AB was +0.3 at both doses. Raw scores are retained. AB/BA disagreements are shown, not resolved by selecting an order. This reused DEV cohort is not directly comparable to the all-100 table above; both project goals remain open. Single sycophancy GP is a distinct alpha4-only direction at the old alpha4 update norm, not another dose of the contrast. Its minus mean remains adverse (+0.180); the direction change does not uniquely isolate a skepticism mechanism. Prior TCA seed0 alpha1 minus BA also invented a baseline quote; all raw scores remain unchanged.

| Evidence   | Method               | Seed   | Alpha   | Side   | Effect →±   | AB →±   | BA →±   | Damage ↓   |
|------------|----------------------|--------|---------|--------|-------------|---------|---------|------------|
| 1          | named-GP additive    | —      | 1       | +C     | -0.107      | -0.013  | -0.200  | 0.127      |
| 2          | named-GP additive    | —      | 1       | -C     | -0.333      | -0.173  | -0.493  | 0.210      |
| 3          | named-GP additive    | —      | 2       | +C     | -0.140      | +0.047  | -0.327  | 0.110      |
| 4          | named-GP additive    | —      | 2       | -C     | -0.057      | +0.100  | -0.213  | 0.110      |
| 5          | named-GP additive    | —      | 4       | +C     | -0.273      | -0.493  | -0.053  | 0.093      |
| 6          | named-GP additive    | —      | 4       | -C     | +0.370      | +0.453  | +0.287  | 0.170      |
| 7          | matched random       | 0      | 1       | +C     | -0.407      | -0.473  | -0.340  | 0.170      |
| 8          | matched random       | 0      | 1       | -C     | +0.050      | -0.087  | +0.187  | 0.153      |
| 9          | matched random       | 0      | 2       | +C     | -0.433      | -0.473  | -0.393  | 0.150      |
| 10         | matched random       | 0      | 2       | -C     | -0.280      | -0.020  | -0.540  | 0.143      |
| 11         | matched random       | 0      | 4       | +C     | -0.890      | -1.220  | -0.560  | 0.257      |
| 12         | matched random       | 0      | 4       | -C     | -0.313      | -0.440  | -0.187  | 0.243      |
| 13         | matched random       | 1      | 1       | +C     | -0.230      | -0.073  | -0.387  | 0.067      |
| 14         | matched random       | 1      | 1       | -C     | -0.057      | -0.367  | +0.253  | 0.120      |
| 15         | matched random       | 1      | 2       | +C     | -0.460      | -0.707  | -0.213  | 0.103      |
| 16         | matched random       | 1      | 2       | -C     | -0.260      | +0.140  | -0.660  | 0.267      |
| 17         | matched random       | 1      | 4       | +C     | -0.387      | -0.373  | -0.400  | 0.047      |
| 18         | matched random       | 1      | 4       | -C     | -0.240      | -0.107  | -0.373  | 0.080      |
| 19         | matched random       | 2      | 1       | +C     | -0.260      | -0.013  | -0.507  | 0.060      |
| 20         | matched random       | 2      | 1       | -C     | -0.700      | -0.567  | -0.833  | 0.200      |
| 21         | matched random       | 2      | 2       | +C     | +0.240      | +0.187  | +0.293  | 0.160      |
| 22         | matched random       | 2      | 2       | -C     | -0.030      | +0.060  | -0.120  | 0.093      |
| 23         | matched random       | 2      | 4       | +C     | +0.150      | +0.127  | +0.173  | 0.107      |
| 24         | matched random       | 2      | 4       | -C     | -0.287      | -0.393  | -0.180  | 0.100      |
| 25         | matched random       | 3      | 1       | +C     | -0.500      | -0.353  | -0.647  | 0.047      |
| 26         | matched random       | 3      | 1       | -C     | -0.147      | +0.107  | -0.400  | 0.190      |
| 27         | matched random       | 3      | 2       | +C     | -0.520      | -0.573  | -0.467  | 0.087      |
| 28         | matched random       | 3      | 2       | -C     | -0.270      | +0.200  | -0.740  | 0.157      |
| 29         | matched random       | 3      | 4       | +C     | +0.067      | +0.087  | +0.047  | 0.103      |
| 30         | matched random       | 3      | 4       | -C     | -0.227      | -0.007  | -0.447  | 0.160      |
| 31         | matched random       | 4      | 1       | +C     | -0.047      | -0.100  | +0.007  | 0.050      |
| 32         | matched random       | 4      | 1       | -C     | -0.150      | -0.047  | -0.253  | 0.213      |
| 33         | matched random       | 4      | 2       | +C     | -0.037      | -0.033  | -0.040  | 0.093      |
| 34         | matched random       | 4      | 2       | -C     | -0.240      | +0.060  | -0.540  | 0.127      |
| 35         | matched random       | 4      | 4       | +C     | +0.077      | -0.100  | +0.253  | 0.093      |
| 36         | matched random       | 4      | 4       | -C     | -0.297      | -0.413  | -0.180  | 0.137      |
| 37         | single sycophancy GP | —      | 4       | +C     | -0.000      | -0.067  | +0.067  | 0.133      |
| 38         | single sycophancy GP | —      | 4       | -C     | +0.180      | +0.300  | +0.060  | 0.107      |

1. [Raw judgments](../slop/logs/20260907_j_lens_additive_concepts/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_additive_concepts/generation.json)
2. [Raw judgments](../slop/logs/20260907_j_lens_additive_concepts/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_additive_concepts/generation.json)
3. [Raw judgments](../slop/logs/20260907_j_lens_additive_concepts_alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_additive_concepts_alpha2/generation.json)
4. [Raw judgments](../slop/logs/20260907_j_lens_additive_concepts_alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_additive_concepts_alpha2/generation.json)
5. [Raw judgments](../slop/logs/20260907_j_lens_additive_concepts_alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_additive_concepts_alpha4/generation.json)
6. [Raw judgments](../slop/logs/20260907_j_lens_additive_concepts_alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_additive_concepts_alpha4/generation.json)
7. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed0/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed0/alpha1/generation.json)
8. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed0/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed0/alpha1/generation.json)
9. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed0/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed0/alpha2/generation.json)
10. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed0/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed0/alpha2/generation.json)
11. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed0/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed0/alpha4/generation.json)
12. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed0/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed0/alpha4/generation.json)
13. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed1/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed1/alpha1/generation.json)
14. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed1/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed1/alpha1/generation.json)
15. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed1/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed1/alpha2/generation.json)
16. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed1/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed1/alpha2/generation.json)
17. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed1/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed1/alpha4/generation.json)
18. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed1/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed1/alpha4/generation.json)
19. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed2/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed2/alpha1/generation.json)
20. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed2/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed2/alpha1/generation.json)
21. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed2/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed2/alpha2/generation.json)
22. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed2/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed2/alpha2/generation.json)
23. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed2/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed2/alpha4/generation.json)
24. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed2/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed2/alpha4/generation.json)
25. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed3/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed3/alpha1/generation.json)
26. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed3/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed3/alpha1/generation.json)
27. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed3/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed3/alpha2/generation.json)
28. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed3/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed3/alpha2/generation.json)
29. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed3/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed3/alpha4/generation.json)
30. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed3/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed3/alpha4/generation.json)
31. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed4/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed4/alpha1/generation.json)
32. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed4/alpha1/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed4/alpha1/generation.json)
33. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed4/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed4/alpha2/generation.json)
34. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed4/alpha2/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed4/alpha2/generation.json)
35. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed4/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed4/alpha4/generation.json)
36. [Raw judgments](../slop/logs/20260907_j_lens_matched_random/seed4/alpha4/judgments.jsonl) · [Responses and delivery](../slop/logs/20260907_j_lens_matched_random/seed4/alpha4/generation.json)
37. [Raw judgments](..//workspace/2026/jspace/j-steer_pub/slop/logs/20260907_j_lens_single_concept/judgments.jsonl) · [Responses and delivery](..//workspace/2026/jspace/j-steer_pub/slop/logs/20260907_j_lens_single_concept/generation.json)
38. [Raw judgments](..//workspace/2026/jspace/j-steer_pub/slop/logs/20260907_j_lens_single_concept/judgments.jsonl) · [Responses and delivery](..//workspace/2026/jspace/j-steer_pub/slop/logs/20260907_j_lens_single_concept/generation.json)
