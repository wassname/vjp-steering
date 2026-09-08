# Proposed repair: isolate sycophancy addition and ablation

PI/OpenAI Codex. Proposal only; no paid launch. Both goals remain open, existing scores unchanged.

## Evidence read

Parent read request_sensitivity/audit.log: all1080 effects/36points/six contrasts reconstruct,45raw/plot hashes unchanged. Alpha4 minus source-minus-random contrast+0.6426667 remains adverse within observed-repeat envelope[0.622,0.6966667] and all leave-one-out contrasts[0.3992857,0.6928571];14/15 paired contributions positive. Four other contrast signs depend on TCA inclusion. These are sensitivity checks, not confidence intervals or method success. Report text remains in worker finalization.

Primary paper https://transformer-circuits.pub/2026/workspace/index.html, cached quote in slop/logs/20260907_j_lens_dictionary_control/science-update/paper-evidence.md lines174,213–215:

> Writing. The simplest intervention is steering along a J-lens vector: h ← h + α v_t, applied at one or more layers and token positions. With negative α, or by projecting out the component of h along v_t entirely, this becomes an ablation.

Authors also describe concept-vector GP16 components and experiments with perturbations rescaled to equal magnitude. These claims motivate the control; they do not establish behavioral sycophancy steering on Qwen.

## One proposed change

Current direction d = saved GP(sycophancy) - saved GP(skepticism). Its minus intervention removes one concept AND adds the other. Proposed direction v = GP(sycophancy) * ||d|| / ||GP(sycophancy)||. Use +4v and -4v in the same persistent layer17 hook, same DEV15 prompts/model/decoding. This changes only direction at the already measured requested norm2.8864548206329344, not source words, dictionary, schedule, dose or rubric. No new fit. Single-concept suppression need not induce candor; that is an explicit risk, not an assumption.

First do an offline check of saved components: exact provenance/order/reconstruction, v nonzero, cosine(v,d), BF16 requested/delivered norms on saved source states, synthetic hook identities. If v and d are effectively identical at delivered precision, this is not a discriminating test: do not spend. No new threshold chosen to force a run; report actual vector/output differences.

Predictions: if the added skepticism concept contributes to adverse minus behavior, removing that addition should reduce adverse fixed-rubric effects across scenarios, not only TCA. If source concepts do not encode the desired behavior, single-concept ablation remains null/adverse at matched norm. If implementation is wrong, source/hash/sign/next-block/identity checks fail. Improvement would support this particular direction change, not uniquely prove the skepticism interpretation. Retain all15 contributions and both judge orders; report identical-request issues without score replacement.

## Cost and boundary

Offline feasibility costs0GPU/API. Proposed later run30treatments+2identities and60unchangedABBAjudgments: prior comparable32response runs78–95s imply roughly0.09–0.11GPU runtime cost plus~0.01API; neither includes startup. Conservative proposed reservation0.80 (360sGPU ceiling0.39492 plus0.40508 forAPI/startup/CPU/memory). Current unreserved3.41988872744 would leave2.61988872744 if separately authorized. All outstanding failure reserves stay intact; no actual invoice claim. No money reserved or run authorized by this proposal. Read final sensitivity report and review this narrow mechanism before any paid execution.
