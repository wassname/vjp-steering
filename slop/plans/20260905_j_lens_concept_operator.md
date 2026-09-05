# Concept J-lens adaptation

— PI/OpenAI Codex

Primary source: [Gurnee et al., Methods / J-space and verbal report](https://transformer-circuits.pub/2026/workspace/index.html):
> We extract concept vectors using an approach introduced in prior work: recording the residual stream activation prior to the Assistant’s response to the prompt "Tell me about {concept}", mean-subtracted over a baseline set of 100 other concepts. We then split each concept vector into two parts: a J-space component, the non-negative combination of its top k=16 J-lens vectors found by gradient pursuit, and a non-J-space component, the remainder.

The paper cites [Nanda et al. 2024](https://www.alignmentforum.org/posts/C5KAZQib3bzzpeyrg/progress-update-1-from-the-gdm-mech-interp-team-full-update), whose inline algorithm selects the maximum residual inner product, updates all currently nonzero weights plus that index, uses `(c dot residual)/(c dot c)` as its line-search step, and clips weights to zero. Sixteen iterations can yield fewer than sixteen nonzero entries. This is NOT fixed initial top-16 ranking or NNLS on a preselected set.

The paper does not specify dictionary row normalization in the available text. The cited SAE procedure uses unit decoder directions. We explicitly use unit J-lens rows as a local numerical convention; record raw row norms and unit-coordinate weights. Do not claim an exact paper reproduction.

```python
# PI/OpenAI Codex; local additive style adaptation, not coordinate exchange
h(concept, layer) = residual_output(final_real_token(chat('Tell me about {concept}')))
mean[layer] = mean(h(b, layer) for b in saved_100_concepts)
a[side, layer] = h(style_concept[side], layer) - mean[layer]
D[layer] = unit_rows(W_U @ J[layer])
w = zeros(vocab)
repeat 16:
    residual = a - w @ D
    scores = D @ residual
    active = (w != 0); active[argmax(scores)] = True
    g = active * scores
    c = g @ D
    w = maximum(w + (c @ residual)/(c @ c) * g, 0)
j[side, layer] = w @ D
remainder[side, layer] = a[side, layer] - j[side, layer]
d[layer] = unit(j[positive, layer] - j[negative, layer])
h_prime[layer, prompt_valid_positions] = h[layer, prompt_valid_positions] + C * d[layer]
```

Positive concept: `sycophantic agreement and flattery toward the user`.
Negative concept: `independent critical assessment of the user's claims`.
+C adds positive-minus-negative; -C subtracts the same vector. C is residual Euclidean norm per layer and prompt position. Normalization is only per-layer direction normalization, not activation-relative scaling. Remainders are saved, not discarded or called orthogonal. Layer outputs follow existing J-lens indexing (6–24 on Qwen3.5-4B). Extraction is final real chat-prompt token; application is all valid prompt positions, with no continuation edits.

DEV uses one seed and coefficients 1, 4, 16 on each side: a bounded geometric grid in the existing additive coefficient units, not calibrated semantic thresholds. Bare is the behavioral control. Passive diagnostics use the same clean DEV prompts, old lexical rows, vocabulary rank, signed unit score/cosine, baseline-concept score distribution, and 128 seeded random token directions. Raw magnitude alone does not establish source inactivity. No behavioral random-vector claim will be made from this passive null.

SHOULD: nonnegative weights reconstruct j exactly and a=j+remainder; C=0 is identity; ±C are antisymmetric; hooks disappear before decode and after exceptions. These follow from the formulas, not behavioral expectations.
TODO validate: a discussion-of-style residual may represent the topic rather than the behavior. A weak DEV effect cannot decide this alone.
