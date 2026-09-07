# PI/OpenAI Codex: actual v16 transfer/persistence diagnostic, no training.
# Source vectors are full-residual controls, not decoded J-lens components.
model ← Qwen3.5_4B(snapshot=851bf6e, dtype=BF16, batch=1)
source ← saved_v16_components(metadata_SHA=aa054e7895…)
layer ← 17                         # prespecified, not selected from these results
B ← source.basis[layer]             # two unit rows, [2,d]
D ← transpose(pseudoinverse(B))      # dual [2,d], saved FP32
source_gap ← −7.5542134046554565
questions ← [legal_pnf01, TCA_pnf02, CSN_pnf03]
# These three questions were selected for diagnosis, not an unbiased DEV sample.
for question in questions:
    bare_prompt ← chat(question, answer_in_two_short_sentences, empty_think_prefill)
    donor_prompt ← chat(source.negative_instruction, question, same_answer_instruction)
    # Both prompts are rendered using the same existing generation_inputs function.
    # The donor prefix is longer; positions and cached histories differ.
    bare ← greedy_generate(bare_prompt, max_new_tokens=512, use_cache=True)
    donor ← greedy_generate(donor_prompt, max_new_tokens=512, use_cache=True)
    h_b ← capture_final_prefill_block_output(bare, layer)
    h_d ← capture_final_prefill_block_output(donor, layer)
    for mode in [bare_identity, donor_identity, full, projected, gap]:
        inputs ← donor_prompt if mode==donor_identity else bare_prompt
        # Exactly one output hook, at layer17 final real prefill position.
        h ← current_final_output(layer)
        c ← float32(h) @ transpose(D)
        if mode==bare_identity: h_new ← h_b
        if mode==donor_identity: h_new ← h_d
        if mode==full: h_new ← h_d
        if mode==projected: h_new ← h + cast_BF16(((h_d−h) @ transpose(D)) @ B)
        if mode==gap:
            midpoint ← sum(c)/2
            desired ← [midpoint+source_gap/2, midpoint−source_gap/2]
            h_new ← h + cast_BF16((desired−c) @ B)
        replace_only_final_position(layer, h_new)
        assert(next_block_input_final == h_new)  # independent input pre-hook
        remove_patch_hook()
        response ← continue_cached_greedy_generate()
        record_all_final_prefill_states(layers=17..31)
        record_first_token_KL_against_bare_and_donor()
    # Identity modes require exact IDs,first-token logits,downstream states.
    for coefficient in [0,1]:
        # Separate persistence run: only schedule changes, same gap/layer/prompt.
        for forward in cached_generate(bare_prompt, max_new_tokens=512):
            h ← current_final_output(layer)
            c ← float32(h) @ transpose(D)
            desired ← [sum(c)/2+source_gap/2, sum(c)/2−source_gap/2]
            h_new ← h if coefficient==0 else h+cast_BF16((desired−c) @ B)
            replace_only_final_position(layer, h_new)
            record_call_position_input_token_predicted_token_and_actual_gap()
            assert(next_block_input_final == h_new)
        assert(call_count == generated_token_count)
        assert(sequence_lengths == [prefill_length]+[1]*decode_call_count)
        if coefficient==0: assert(generated_ids == saved_bare_ids)
# Existing fixed judge rates bare versus each treatment independently in AB and BA.
# Export subtracts steered−bare on-axis, then negates for the minus-side display.
# Retain both raw per-response scores and complete texts; orderings are not samples.
# Full donor replacement does not transplant prior token states or recurrent/KV history.
