# Correction for the VJP-delta review

The review's batch-weighting and asymmetric-normalization findings came from two errors in the supplied pseudocode. The implementation at `src/jsteer/vjp.py:128-146` instead does this:

```python
for prompt in batch:
    q[P, l] += mean_over_valid_tokens(G[l, prompt])
q[P, l] /= len(P)
v[l] = (q[P_pos, l] - q[P_neg, l]) / norm(q[P_pos, l] - q[P_neg, l])
```

Thus the final partial batch has its actual number of prompts, and every deployed layer vector has unit norm. Source layers must precede the target layer, so the target no-op case does not occur.

The plot compares methods by judged off-axis change, not by the numeric coefficient C. For every method, including each random seed, it uses the same per-seed best-effect-at-or-below-damage frontier. Coefficient grids therefore select points only within a method's curve. The public claim will not use vector cosine similarity as evidence.

Re-evaluate the batch-weighting, normalization, target-layer, coefficient-grid, and random-band findings with these facts. Keep, withdraw, or restate each finding. Then give the strongest remaining publication blocker.
