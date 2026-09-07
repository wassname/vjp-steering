# Actual executed fixed DEV15 representation bridge — PI/OpenAI Codex
source_pool = original_200_suffix_entries
unique = deduplicate_by_exact_user_message(source_pool)  # 65
ordered = Random(0).sample(unique, 65)
fit_ids = ordered[:52]
calibration_ids = ordered[52:]
conditions = [positive_persona, negative_persona, baseline_instruction]
# Original extraction: right padding, batch8, BF16 model
for condition in conditions:
    prompts = chat_template(instruction[condition] + user_message)
    H[condition] = final_real_prefill_block_output(prompts, layer17)
for condition in [positive_persona, negative_persona]:
    signal[condition] = mean(H[condition, fit_ids] - H[baseline, fit_ids])
J = frozen_downloaded_lens[layer17]
dictionary_raw = lm_head_weight @ J
dictionary = unit_normalize_each_vocabulary_row(dictionary_raw)
for condition in [positive_persona, negative_persona]:
    gp[condition] = actual_repository_nonnegative_gradient_pursuit(signal[condition], dictionary, k16)
for representation in [full_residual, j_gp16]:
    components = signal if representation == full_residual else gp
    B = stack(unit(components[positive]), unit(components[negative]))  # 2 x d
    D = pseudoinverse(B).T  # 2 x d
    for side in [positive, negative]:
        source_coordinates = H[side, calibration_ids] @ D.T
        frozen_target[representation, side] = mean(source_coordinates[:,0] - source_coordinates[:,1])
# No DEV answers or judgments set B, D, source order, layer, or targets
# Current verification: exact dictionary/support/component replay
# Replayed 39 calibration source records use their exact saved padded IDs/masks
# Replay shape batch1 instead of original batch8; frozen targets remain unchanged
assert max_individual_coordinate_replay_error < 0.1  # gate specified before run
for question in fixed_DEV15:
    bare = greedy_generate(question, BF16, batch1, max512)
    for representation in [full_residual, j_gp16]:
        for side in [positive, negative]:
            for forward_call in cached_generate(question):
                h = layer17_output_at_current_final_position
                c = h.float() @ D[representation].T
                shift = (frozen_target[representation,side] - (c[0]-c[1])) / 2
                delta = shift * (B[representation,0] - B[representation,1])
                output[-1] = h + delta.to(BF16)  # alpha1, other positions untouched
                assert next_block_input == inserted_output
                record(actual_patch_norm, coordinates_before_after, call_position)
            save_complete_response_and_health()
# One alpha0 identity generation per representation on first fixed question
# Every treatment compared to same-question bare with unchanged judge, AB and BA
# Both orderings retained; negate candor-side contrast for signed plotting effect
# 75 cells,120 judgments; no coefficient/layer search or calibrated frontier
