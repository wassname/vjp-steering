# Paper-native J-lens candidates for a bidirectional sycophancy benchmark.
# Pseudocode only. — PI/OpenAI Codex

# Shared lens and workspace from the successful local verbal-report reproduction.
Jℓ = mean_jacobian(pretraining_prompts=1000, source_and_future_positions=True)
Dℓ[token] = unembed[token] @ Jℓ
workspace_layers = range(13, 22)


def coordinate_swap(h, v_source, v_target, α):
    V = stack_columns(v_source, v_target)        # d × 2, raw J-lens rows
    c = pinv(V) @ h                             # 2 × positions
    return h + α * V @ (reverse(c, axis=0) - c)


# Candidate A: isolate the known layer mismatch before changing the representation.
# It is diagnostic only: swapping a pair is symmetric, so negative α is not a reverse swap.
def fixed_pair_diagnostic(prompt, α):
    with prefill_hooks(workspace_layers):
        h = coordinate_swap(h, Dℓ[' abrasive'], Dℓ[' flattering'], α)
    return greedy_decode_without_hooks(prompt)


# Candidate B: mirror the paper's active-source condition for each prompt.
# The paired lexicon is fixed before DEV. Pair choice uses only clean J-lens activity.
assessment_pairs = [
    (' false', ' true'),
    (' incorrect', ' correct'),
    (' invalid', ' valid'),
    (' impossible', ' possible'),
    (' nonsense', ' reasonable'),
    (' unrelated', ' related'),
    (' unsupported', ' supported'),
]


def active_assessment_swap(prompt, side, α):
    h_clean = clean_prefill(prompt)
    source_set = left_tokens(assessment_pairs) if side == '+C' else right_tokens(assessment_pairs)
    source = argmax_token_activity(Dℓ, h_clean, source_set, position='assistant-prefill')
    target = paired_counterpart(source)
    if rank(Dℓ[source] @ h_clean) > predeclared_activity_rank:
        return greedy_decode(h_clean)            # explicit no-op, not a silent fallback
    assert rank(Dℓ[target] @ h_clean) > 10
    with prefill_hooks(workspace_layers):
        h = coordinate_swap(h, Dℓ[source], Dℓ[target], α)
    return greedy_decode_without_hooks(prompt)


# Candidate C: use the paper's broader-concept decomposition and injection protocol.
# Each side gets its own component; this is not positive/negative scaling of one contrast.
def concept_J_component(concept):
    aℓ = residual(f'Tell me about {concept}', position='assistant-prefill')
    aℓ -= mean(residual(f'Tell me about {b}') for b in fixed_100_baselines)
    weights = nonnegative_gradient_pursuit(signal=aℓ, dictionary=unit_rows(Dℓ), k=16)
    return weights @ unit_rows(Dℓ)


j_syco = concept_J_component('sycophancy')
j_abrasive = concept_J_component('abrasiveness')


def concept_injection(prompt, side, α):
    j = j_syco if side == '+C' else j_abrasive
    with prefill_hooks(workspace_layers, positions='user_turn'):
        h = h + α * unit(j)                      # paper's positive steering/injection family
    return greedy_decode_without_hooks(prompt)


# Candidate C controls distinguish J-space semantics from generic concept steering.
def matched_controls(prompt, side, α):
    a = full_concept_vector('sycophancy' if side == '+C' else 'abrasiveness')
    j = concept_J_component('sycophancy' if side == '+C' else 'abrasiveness')
    nonJ = a - j
    magnitude = norm(α * unit(j))
    return {
        'J': inject(prompt, rescale(j, magnitude)),
        'nonJ': inject(prompt, rescale(nonJ, magnitude)),
        'random': inject(prompt, rescale(fixed_random_direction, magnitude)),
    }


# Selection contract: a method is not working merely because it is coherent.
def accept(method_results, random_zone):
    assert intended_sign(method_results['+C'])
    assert intended_sign(method_results['-C'])
    assert method_results_outside(random_zone)
    assert raw_answers_remain_responsive()
    return True
