# VJP-delta public-method review

Review the method and experimental design below as a skeptical ML researcher. Focus on mathematical correctness, controls, and silent failure modes. Do not review style or propose a larger framework.

## Point

This repository is a minimal, reproducible reference for VJP-delta activation steering. It reimplements only the VJP extraction. `steering-lite` supplies mean difference, PCA, random vectors, vector storage, and intervention hooks.

## Hope and falsifiable goal

The hope is that VJP-delta can move a model away from sycophancy with a larger judged on-axis change at the same or lower judged off-axis change than mean difference, PCA, and random directions. The all-100 experiment can falsify this. A VJP-delta curve inside the random band, or dominated by a baseline, gives no support for the hope.

## Evaluation specification

- Model: Qwen/Qwen3.5-4B.
- Questions: all 100 Bullshit Benchmark questions. The selected 20-question set is forbidden.
- Methods: VJP-delta, mean difference, PCA, and seeded random directions.
- Rows: both steer directions, several fixed coefficients per method, three random seeds.
- Effect: a blinded judge's per-question on-axis difference from bare, oriented so positive means more of that direction's target behavior.
- Damage: mean absolute per-question change in the blinded judge's off-axis rating.
- Validity: output caps reject repetition, loops, length distortion, answer failure, prompt echo, unfinished text, or excess prefill NLL.
- Plot: the sycophancy-reducing `-C` direction only. It shows the best on-axis effect available at each damage budget. The random distribution is a band over independent seeds.
- A renderer checks that every row has one model, tokenizer, prompt template, data hash, evaluation cohort, layer set, and batch size. It writes Markdown, HTML, SVG, and PNG from one CSV.

## Pseudocode

```python
def vjp_delta(P_pos, P_neg, L, T):
    mu_pos <- mean(last_hidden(model, P_pos, T))
    mu_neg <- mean(last_hidden(model, P_neg, T))
    c <- mu_pos - mu_neg
    for P in (P_pos, P_neg):
        for batch in batches(P):
            M <- valid_tokens(batch, first=16, last=-1)
            H <- forward_with_source_activations(batch, L, T)
            for l in L:
                G[l] <- grad_H[l] sum(H[T] * M[..., None] * c)
                q[P, l] += sum_s(G[l] * M[..., None]) / sum_s(M)
        q[P] <- q[P] / len(P)
    for l in L:
        v[l] <- (q[P_pos, l] - q[P_neg, l]) / norm(q[P_pos, l])
    return v

for method, seed, C, side in measured_arms:
    bare <- generate(model, all_100_questions)
    steered <- generate(model, all_100_questions, add=C * extract(method, seed))
    ratings <- blinded_judge(bare, steered, target="sycophancy")
    effect <- mean(oriented_on_axis(ratings, side))
    damage <- mean(abs(off_axis_delta(ratings)))
    record(method, seed, C, side, effect, damage, output_caps_pass(bare, steered))
```

## Questions

1. What central assumption would make this method outperform the baselines, and how could it fail silently?
2. Do the all-100 cohort, random seeds, and output caps address the major confounds?
3. Is the VJP reduction and normalization internally consistent?
4. What is the smallest additional control that would materially improve the claim?
5. State one concrete UAT condition that blocks publication.
