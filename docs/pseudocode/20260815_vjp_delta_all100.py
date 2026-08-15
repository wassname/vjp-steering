# CODEX: Public VJP-delta extraction and all-100 comparison.

# ── Extract VJP-delta ─────────────────
def vjp_delta(P_pos, P_neg, L, T):
    μ_pos ← mean(last_hidden(model, P_pos, T))        # μ ∈ ℝ^d
    μ_neg ← mean(last_hidden(model, P_neg, T))
    c ← μ_pos - μ_neg                                 # target contrast

    for P in (P_pos, P_neg):
        for batch in batches(P):
            M ← valid_tokens(batch, first=16, last=-1)  # M ∈ {0,1}^{b×s}
            H ← forward_with_source_activations(batch, L, T)
            for l in L:
                G[l] ← ∇_{H[l]} sum(H[T] * M[..., None] * c)  # G ∈ ℝ^{b×s×d}
                q[P, l] += sum_s(G[l] * M[..., None]) / sum_s(M)
        q[P] ← q[P] / len(P)

    for l in L:
        v[l] ← (q[P_pos, l] - q[P_neg, l]) / norm(q[P_pos, l])
    return v


# ── Measure one steering arm ──────────
def measure(method, seed, C, side, questions):
    v ← extract(method, seed)
    bare ← generate(model, questions)
    steered ← generate(model, questions, add=C * v)
    ratings ← blinded_judge(bare, steered, target="sycophancy")
    effect ← mean(oriented_on_axis(ratings, side))
    damage ← mean(abs(off_axis_delta(ratings)))
    admissible ← output_caps_pass(bare, steered)
    return {method, seed, side, C, effect, damage, admissible}


# ── Publish one comparable plot ───────
questions ← all_100_bullshit_benchmark_questions()    # never the selected 20
rows ← [
    measure(method, seed, C, side, questions)
    for method, seeds, doses in [
        ("vjp_delta", [0], measured_vjp_doses),
        ("mean_diff", [0], measured_mean_diff_doses),
        ("pca", [0], measured_pca_doses),
        ("random", [0, 1, 2], measured_random_doses),
    ]
    for seed in seeds for C in doses for side in (-C, +C)
]
assert one_shared_cohort(rows)
plot_pareto(rows, side=-C, random_band=per_seed_frontier(rows))
write_same_table_as_markdown_and_html(rows)
