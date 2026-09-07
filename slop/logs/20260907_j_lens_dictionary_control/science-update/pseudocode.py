# PI/OpenAI Codex: conceptual pseudocode, not executable Python.
# Shapes: hidden h[d], vocabulary dictionary A[V,d], two-row basis B[2,d].
# Data identities and raw current/previous outputs are supplied separately.
# Paper/reference implementation excerpts are a separate primary attachment.
model ← pinned Qwen3.5-4B, BF16
layer ← 17
fit_ids ← original seeded source first52
calibration_ids ← original seeded source last13
DEV_ids ← fixed15 benchmark questions, reused across prior repairs
assert no overlap(fit_ids, calibration_ids, DEV_ids)
for persona in [positive, negative, neutral]:
    for question in source_questions:
        input ← original_chat_prompt(persona_instruction, question)
        h[persona,question] ← residual_block_output_at_final_prefill(input, layer)
for side in [positive, negative]:
    signal[side] ← mean_fit(h[side] - h[neutral])
J ← previously fitted average future-output Jacobian at layer
A_j ← unit_rows(lm_head @ J)
A_direct ← unit_rows(lm_head)  # current control; all padded head rows retained
for representation in [full, j_gp16, direct_gp16]:
    for side in [positive, negative]:
        if representation == full:
            component[side] ← signal[side]
        else:
            A ← A_j if representation == j_gp16 else A_direct
            component[side] ← nonnegative_gradient_pursuit(signal[side], A, k=16)
    B[representation] ← unit_rows(stack(component[positive], component[negative]))
    D[representation] ← pseudoinverse(B[representation]).transpose()
    assert rank(B[representation]) == 2
    for side in [positive, negative]:
        coordinates ← h[side,calibration_ids] @ D[representation].transpose()
        target[representation,side] ← mean(coordinates[:,0] - coordinates[:,1])
# Full and old J-GP targets frozen in prior artifact; direct-GP targets recalculated from source only.
# New replay retains original padded IDs/masks but runs batch1 rather than historical batch8.
# Current original-coordinate replay max error .08186; prior approximate .1 gate unchanged.
for question in DEV_ids:
    bare ← greedy_cached_generate(question + 'Answer in 2 short sentences.')
    for side in [positive, negative]:
        for every prefill/decode model forward:
            h ← current final token residual at layer17
            c_gp ← h @ D[current_representation].transpose()
            c_full ← h @ D[full].transpose()
            delta_gp ← .5*(target[current_representation,side] - c_gp[0] + c_gp[1])*(B_gp[0]-B_gp[1])
            delta_full ← .5*(target[full,side] - c_full[0] + c_full[1])*(B_full[0]-B_full[1])
            realized_full ← BF16(h + BF16(delta_full)) - h
            if norm(delta_gp)==0 and norm(realized_full)>0: stop_arm
            delta ← unit(delta_gp) * norm(realized_full)  # zero reference → zero delta
            h_after ← BF16(h + BF16(delta))
            assert next_block_input == h_after
            record(norms, direction_cosine, coordinates, target, nonfinal_identity, call)
        output ← complete generated response; no treatment on earlier prefix tokens
        for order in [AB, BA]:
            score_each_response_independently(bare, output, fixed_rubric_with_known_flaw)
            effect ← steered_on_axis - bare_on_axis
            displayed_effect ← effect if side==positive else -effect
# Earlier full/J-GP alpha1 runs used delta_gp directly, without norm matching.
# Two alpha0 real-model identity controls must reproduce baseline tokens exactly.
# Gram/reconstruction/actual-state checks are mechanics, not semantic efficacy.
# Current control uses no J transport and is not labeled as J-lens success.
