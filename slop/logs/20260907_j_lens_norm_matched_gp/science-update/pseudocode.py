# Actual norm-matched GP16 DEV comparison; PI/OpenAI Codex
# Shapes: h:[1,d], B:[2,d], D:[2,d]; no fitting in this run.
# Frozen extraction source:52fit,13calibration,15DEVquestions disjoint by IDs/text.
# Source questions generic; exact source messages in primary evidence.
for layer in [17]:
    for persona in [positive,negative]:
        signal[persona] ← mean(h_persona_fit - h_neutral_fit)
        dictionary ← unit_rows(lm_head @ saved_J[layer])
        gp_component[persona] ← gradient_pursuit(signal[persona],dictionary,16)
    B_full ← unit_rows(stack(signal[positive],signal[negative]))
    B_gp ← unit_rows(stack(gp_component[positive],gp_component[negative]))
    D_full ← solve(B_full @ B_full.T,B_full)
    D_gp ← solve(B_gp @ B_gp.T,B_gp)
    for basis in [full,gp]:
        # Historical calibration means saved in each basis,not DEV response labels.
        t[basis,positive] ← mean(c_positive_calibration[:,0]-c_positive_calibration[:,1])
        t[basis,negative] ← mean(c_negative_calibration[:,0]-c_negative_calibration[:,1])
# Reuse75prior outputs:15questions × bare,full+/−,oldGP+/−.
# Prior methods gap-clamp only at final prefill and then every decode current position.
# Frozen model851bf6e,BF16,batch1,greedymax512; source modelrevisionunknown.
for question in DEV15:
    for side in [positive,negative]:
        for forward in [prefill, every_cached_decode]:
            h ← block17_output[:,last_position]
            cg ← FP32(h) @ D_gp.T
            cf ← FP32(h) @ D_full.T
            dg ← 0.5*(t[gp,side]-(cg[0]-cg[1]))*(B_gp[0]-B_gp[1])
            # Existing full reference implementation uses midpoint coordinates.
            midpoint ← (cf[0]+cf[1])/2
            cf_new ← [midpoint+t[full,side]/2,midpoint-t[full,side]/2]
            df ← (cf_new-cf) @ B_full
            reference_after ← BF16(h+BF16(df))
            reference_delta ← FP32(reference_after)-FP32(h)
            if norm(dg)==0 and norm(reference_delta)>0: stop_and_save_failure()
            desired ← 0 if norm(reference_delta)==0 else norm(reference_delta)*dg/norm(dg)
            after ← BF16(h+BF16(desired))
            assert other_positions_exact_identity
            assert next_block_input_equals_inserted_after
            record(norm(desired),norm(FP32(after)-FP32(h)),cosine(actual_delta,dg))
            record(cg,cf,targets,norm(dg),norm(reference_delta),call_index)
        save(full_generated_ids,text,health,measurements)
# 2freshalpha0identities produce exactoldbareIDs;30fresh treatments;60newABBAjudgments.
# Evaluator's continuous target effect is distinct from explicit rejection of existence.
# New trajectories receive their own full-counterfactualnorm,not oldfulltrajectorydose.
# Rescaling intentionally does NOT reach oldGPtargetgap or preserve coordinate sum exactly after rounding.
# No random control of this new adapter,no new calibration,sourcefit,layerchoice,or public frontier.
