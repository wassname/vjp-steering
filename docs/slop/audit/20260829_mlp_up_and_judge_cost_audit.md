# MLP-up asymmetry and judge-cost audit

## Observations

The published MLP-up vector uses one bipolar direction. `src/vjp_steering/vjp.py:317-326` computes paired positive-minus-negative VJPs, applies one coordinate weight, and globally normalizes the result. Applying `+C` and `-C` changes only the sign. The vector uncertainty weighting is therefore not direction-specific.

The weight is:

$$w_i = \max\left(0, 1 - \frac{\sigma_i^2}{\mu_i^2}\right), \qquad v_i = \mu_i w_i.$$

Here $\mu_i$ and $\sigma_i$ are the mean and standard deviation across paired persona prompts. This is an effect-size rule. It asks whether one fixed coordinate works consistently across prompts. It is not an estimate of uncertainty in the sample mean, which would use $\sigma_i / \sqrt{n}$.

Stored C=8 vectors gave this concentration summary:

| quantity | value |
| --- | ---: |
| coordinates | 267,264 |
| nonzero coordinates | 59,666 |
| largest coordinate energy | 1.38% |
| top 10 coordinate energy | 8.17% |
| top 100 coordinate energy | 23.7% |
| top 1,000 coordinate energy | 55.0% |
| layer 15 + 16 energy | 27.7% |

The three configured MLP-up seed vectors have cosine approximately 1.000000 and maximum pairwise coordinate difference below `4e-8`. The 256-pair dataset is effectively the same set in a different order, so these runs do not measure extraction-sample uncertainty.

The endpoint-tail manifest contains 305 dose/sign cells. Each contains 100 questions. `scripts/judge.py:223-226` requests two presentation orders and two passes:

```text
logical_dose_sides 305
raw_pair_rows 30500 theoretical_calls 122000
unique_response_pairs 14431 required_calls 57724 dedupe_factor 2.1135
prompt_chars mean/p50/p95 4486 4432 4774
raw_chars mean/p50/p95 264 259 342
reason_chars mean/p50/p95/nonzero 0 0 0 0
cost expected sum 11.571625159
```

Exact-response caching reduced 122,000 possible calls to 57,724. The selected records contain no reasoning text. The request count comes from judging every dense dose on every question four times, rather than long judge replies.

## Interpretation

My read is that direction-specific dose search was necessary but does not address direction-specific routing. A separate left/right vector is a different method, not a calibration change to the current bipolar vector. The existing development repo already contains this design as `vjp_left_right`: coefficient sign selects one of two class-conditioned VJPs instead of negating one vector.

For MLP-up, the next comparison should preserve the current method and add one class-conditioned left/right method. Each direction should log split-half cosine as a descriptive diagnostic only, without using it to accept the vector or infer behavioral quality. Mechanical checks should cover finite values, shape, coordinate concentration, layer concentration, first-order held-out target response, and activation-scaled intervention size before a judge sweep.

I would not log-transform signed sensitivities. A Huber mean or median-of-means is a cleaner robust replacement if prompt outliers are the concern. A t-statistic answers whether a coordinate mean is measured precisely, but can overvalue tiny low-variance coordinates; the SAM-style denominator `SE + median(SE)` in the development implementation is safer than raw `mean/SE`.

To limit interventions on naturally tiny MLP coordinates, measure the offset in activation-standard-deviation units. Compare global Euclidean normalization against a natural-scale constraint such as $\sum_i (\delta_i / s_i)^2$, where $s_i$ is the unsteered MLP-up activation standard deviation. Report coordinate and layer energy shares after this scaling. Cropping or clipping should use this measured scale rather than a raw coefficient threshold.

The next judge protocol should screen health-clean doses on a fixed small scenario subset, then run the full 100-question, order-balanced judge only on the candidate endpoint and its lower neighbor. One pass in each order gives two calls per question. A second stochastic pass is better spent on the final endpoint than on every trajectory point.

<!-- PI: audit and interpretation written 2026-08-29. -->
