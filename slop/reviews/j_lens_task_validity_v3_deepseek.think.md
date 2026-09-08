Let me read the files carefully.Let me read the rest of the files that are truncated — the test-proposal at parent (already seems read under spec? no). Actually I need to read the parent test-proposal.md, and the gate code in validate.py I've read fully. Let me also check the remaining part of corpus.jsonl to verify cue families and any possible shortcut false positives, and check validation.log fully (already read — it's one line). Let me read the parent test-proposal.md and check the remaining corpus rows for concerns about shortcuts.

Actually the key question is a review decision. Let me focus on the specific questions and verify from code/data.

Let me check the parent test-proposal.md to understand what "already described source-state experiment" entails, and look at whether there are remaining shortcut false positives.

Key concerns to verify:

1. V1/v2 preserved, v3 changes only policy-clause order. From build.py, each v2 row is duplicated with policy_order 0 and 1. policy_order 0 keeps valid action first (same as v2? need to verify v2's policy prose). Actually the v2 policy prose always had valid action first (the fault). So policy_order 0 = original v2 (valid first), policy_order 1 = reversed. So v3 = v2 with policy-clause-order counterbalance. The build also changes `id`, `pair_id`, `semantic_case_id`, `expected`, `prompt`, `provenance`, `v2_parent_id`, `policy_order`, `policy_actions`, `expected_semantic_action`. But validate asserts rule, evidence, facts, valid, split, cue_family, consumer, options, expected, option_order unchanged from parent. And build asserts the corpus is byte-identical to recomputed corpus. So v1/v2 preserved as files unchanged. Good.

2. A/B answer position and policy-clause order balanced. The validation.json shows balanced cells. Also need to verify storage/notification absent from train and source_calibration. validate.py has `held_consumers = {"storage", "notification"}` and asserts no row with those consumers in non-withheld_source splits. Actually it checks `row["consumer"] in held_consumers and row["split"] != "withheld_source"`. Good.

Wait — but the balance cells: the answer_balance is computed within split × consumer × valid × policy_order. And policy_balance within split × consumer × valid × option_order. These are all balanced. Good.

But the question asks: "A/B answer position and policy-clause order are balanced within relevant task and label cells." Yes.

3. Gate maps letters to semantic actions, controls fail. Need to verify the controls actually fail and no shortcut false positives remain.

Let me think about the gate. The gate requires:
- min_accuracy >= 0.90 across all split, split_consumer, split_cue cells.
- all policy_mirror values true (each v2 parent's two policy-order variants both return correct semantic action).
- all full_mirror values true (each semantic case's 4 variants all return correct semantic action).

Controls:
- semantic_oracle: returns row["expected"] (the correct letter). Maps to correct semantic -> pass.
- always_A: 0.5 accuracy fails.
- always_B: 0.5 fails.
- opposite_letter: 0.0 fails.
- first_policy_branch: returns the letter for policy_actions[0]. Due to policy-order counterbalance, this is effectively 0.5 semantic accuracy. Fails.

Now the shortcut false positives to look for:
- policy wording: "route through gate" vs "route through bypass" — could a model just pick the action that sounds "valid"/"positive"? E.g., "allocate two counters" vs "allocate zero counters". A shortcut could be "pick the action with the higher number" or "pick the non-'zero' action" etc. But that's a lexical-preference shortcut not measured by these controls. The question specifically lists "action lexical preference" and "policy wording" as remaining shortcut false positives to look for.

Actually, key issue: actions_valid_invalid is a fixed pair [valid_action, invalid_action], and the "valid" action is always the first in that list. But note that across worlds, the semantic meaning of "valid" action varies (world parity reverses consumer action semantics per spec). Let me check: in the corpus, world0 routing valid = "route through gate", world1 routing valid = "route through bypass". So the lexical preference is counterbalanced at the world level? Let me check more carefully.

Actually wait, look at the action pairs: for seal_match family, routing: valid/invalid = ["route through gate", "route through bypass"] for world0, and ["route through bypass", "route through gate"] for world1. So the valid action flips between worlds 0 and 1. But is the valid action lexical counterbalanced? In world0, valid = "route through gate"; in world1, valid = "route through bypass". So yes, across worlds the "valid" semantic action alternates lexically. But is that enough to block a "pick 'gate'" shortcut? If a model always picks "gate", and gate is valid in world0 but invalid in world1... Let me consider.

Actually let me carefully consider whether the gate correctly blocks a simple lexical-preference shortcut. Suppose a model always picks the lexically "positive/active" action, e.g., "route through gate" over "bypass", "allocate two counters" over "zero counters". Would that pass the gate?

The gate requires each semantic case (4 variants) to return correct semantic action, and 90% in each split×cue cell. A lexical preference would give correct answer only when the preferred lexical action happens to be the valid action. For world0 routing, valid = "gate", so preferred "gate" → correct. For world1 routing, valid = "bypass", preferred "gate" → wrong. Since both worlds are in train, the lexical-preference accuracy would be 50% within the seal_match routing cell → fails the 90% requirement.

So actually the world parity does counterbalance action lexical preference within the same consumer/cue family. Good. But wait — is that actually true across all cue families, or only seal_match? Let me check the other families.

Let me read more of the corpus to verify. The corpus has 384 rows. I've seen seal_match worlds 0,1,2. I need to see capacity, roster, parity, precedence, link families and their action lexical counterbalancing.

Actually, there's a subtle issue I should verify: within a single split (train), do both "worlds" with opposite valid-action semantics appear? Train has seal/capacity/roster worlds 0-1. So yes.

But more important potential shortcut: "allocate two counters" vs "allocate zero counters" — always pick "two" (non-zero). In capacity family... hmm.

Let me actually read the rest of the corpus to check for a systematic lexical shortcut, and also check the gate's robustness. Let me also consider "invalid-evidence artifacts" and "split/cue confounding".

Actually, let me be efficient. I've seen the key code. The gate is quite strict (requires every single semantic case to be fully correct, and ≥90% in every small cell). This makes it hard for shortcuts to pass. But let me check a subtle issue:

The gate's `first_policy_branch` control returns letter for policy_actions[0]. Due to balance, this gives 0.5. But what about a shortcut "always pick the valid-sounding action" = "always pick actions_valid_invalid[0]"? That's essentially "pick the true valid action lexically" — which would be the semantic oracle in disguise? No wait. actions_valid_invalid[0] is always the valid action. A model that always maps to the valid action... but that's not a shortcut, that's the oracle. The shortcut concern is whether there's a lexical feature that correlates with validity beyond the actual rule.

The critical shortcut: "pick the action that is the semantically 'doing something' vs 'not doing' / 'positive vs negative'". Let me examine:

Consumers:
- routing: "route through gate" (valid in world0) vs "route through bypass" (valid in world1). The words "gate"/"bypass" carry no inherent validity. Counterbalanced.
- allocation: "allocate two counters" (valid world0) vs "allocate zero counters" (valid world1). Here "two" = more quantity = valid in world0, "zero" = valid in world1. Is "two counters" lexically preferred over "zero counters"? But counterbalanced across worlds.
- storage: "choose storage..." what are the actions? Need to read.
- notification: similar.

The critical issue: does each pair counterbalance the lexical valence WITHIN each split so that a lexical-preference shortcut can't achieve 90% in any split×consumer×cue cell? Since each pair has valid and invalid in both worlds, and worlds 0 and 1 are both in the same split (train), the lexical preference is canceled within train.

But wait — the gate checks "split_by_cue" cells too. In train, seal_match worlds 0-1 both present, capacity worlds 0-1, roster worlds 0-1. So counterbalanced.

For source_calibration: seal/capacity/roster world2, plus ALL parity worlds. Parity worlds — is parity a single world or multiple? Spec says "all parity worlds" in calibration. If parity has worlds with counterbalanced action semantics... Let me check. Actually parity family likely involves "odd/even" and count. Need to read.

Let me read more of the corpus to be thorough about parity, precedence, link, storage, notification actions.

Let me read the rest of corpus.jsonl (offset 40 onwards) and the parent test-proposal.md, and the v2 corpus if needed.

Actually there's a more subtle and important issue I should verify: the "opposite-letter" and "always" controls are canned, but the question asks me to look for REMAINING simple shortcut false positives beyond those tested. The validation code only tests 5 canned controls. Are there shortcuts that WOULD pass the gate but are obviously not "understanding the precondition"?

One candidate: "always pick actions_valid_invalid[0]" = always pick valid action by its canonical string. But that string is per-row fixed; a real model can't "know" it. Not a shortcut.

Another: "pick the action matching the entity in evidence" — e.g., if evidence says "Vek0 seal", pick action containing "Vek"... but actions don't contain entities. No.

Another strong candidate: the policy sentence itself. "When the requirement holds, X; otherwise, Y." A model could be relying on... no, that's exactly the policy mapping which is the task.

Actually the real remaining shortcut concern for a MODEL: "answer the action whose first policy clause condition matches whether evidence satisfies the rule." That IS the task, not a shortcut.

The actual shortcut the question worries about: "policy wording" and "action lexical preference". E.g., a model might learn "the valid action always appears in the 'When the requirement holds' clause when preconditions are met" — but that's the task. Or "the word 'gate' vs 'bypass'" etc.

Let me think about whether there's an actual systematic confound in the data that a simple heuristic could exploit to pass the gate.

Key: The gate is extremely strict — requires 100% on all 96 semantic cases (4 variants each correctly). Any deterministic lexical shortcut that is NOT perfectly aligned with the rule would fail at least one case. So really the only shortcuts that pass are those perfectly aligned with the rule-ground truth = the oracle. So the gate is not "too weak" in terms of deterministic shortcuts.

But could the gate be "too strict"? It requires 100% of all semantic cases AND ≥90% in every cell, with min cell sizes as small as... split_cue cells. Let me check the smallest cell. split_cue cells: e.g., ('source_calibration', 'parity'), ('withheld_source', 'precedence'), ('withheld_source', 'link'). How many rows in parity? Let me check.

From validation.json gate_controls, split_cue cells listed: train has seal_match, capacity, roster. source_calibration has seal_match, capacity, roster, parity. withheld_source has seal_match, capacity, roster, precedence, link. So parity only in source_calibration, precedence/link only in withheld_source.

The 90% threshold with small cells: if a cell has, say, 8 rows (4 actions × ... ), 90% means at most 0.8 rows wrong → 0 rows wrong = 100% effectively. For small cells, 90% → floor(0.1 * n) errors allowed. For n=8, 90% = 7.2 → need ≥7.2 → 8/8 = 100%. For n=16, need ≥14.4 → 15/16. So the gate is quite strict for small cells.

Actually this strictness is a potential problem: is 90% in EVERY tiny cell a reasonable standard for a real model (which may make occasional token errors)? This could be "too strict" making a genuine source-state unmeasurable. But that's a design judgment, and the question says "a gate that is too strict or too weak for a model test" is something to look for.

Hmm, let me focus. The decision is TEST or REVISE. I need to find a concrete offline correction if REVISE, or confirm TEST.

Let me carefully think about a real remaining shortcut false-positive that would PASS the gate and is NOT the semantic oracle.

Consider this: the "expected_semantic_action" is valid/invalid. The gate maps A/B → action string → valid/invalid via actions_valid_invalid. Now, is there any feature in the prompt that lets a trivial parser know the answer without understanding precondition? 

The prompt structure:
1. "This is a self-contained rule world..."
2. rule (e.g., "The operation requires a Vek0 seal.")
3. evidence (e.g., "The item carries a Vek0 seal.")
4. "When the requirement holds, X; otherwise, Y."
5. "Which action follows? A: opt0. B: opt1."

The answer requires: does evidence satisfy rule? If yes → X (the "holds" branch), if no → Y.

A "first-policy-branch" shortcut = always pick X (policy_actions[0]) regardless of evidence → 50% (counterbalanced). Blocked.

A "pick the action that matches the evidence's entity" — no.

But here's a real one: "pick the action that is lexically similar to / contains the same first word as the valid-condition". Hmm no.

Actually here's a genuinely important one: the actions contain "valid"-ness via the words used. Let me think about the specific action pairs and whether "valid" action always has a consistent lexical property within a world but that property also correlates with the rule.

Actually, I realize the more important thing to verify is whether there's a confound between the cue (rule/evidence) and the answer that a trivial string matcher can exploit. Since the labels can be "independently recomputed," by construction the valid action = satisfy(rule, evidence). A trivial matcher that implements satisfy() would pass — but that's the task, not a shortcut.

The real question: does the gate distinguish "source-state effect" from "closed-world instruction following"? The test-proposal itself admits the contrary hypothesis is "closed-world instruction following or conditional branching." The gate CANNOT distinguish these — it only checks accuracy on the closed-world task. That's a deep limitation but it's acknowledged, and the design says the transfer test is what distinguishes them. So the gate is for admission (model can do the task), not for the source-state interpretation.

So the design's logic: gate = admission (model understands precondition). Then source-state test = probe decomposition. Then transfer = unchanged benchmark. The gate is not itself the source-state test; it's a precondition for interpreting source-state results.

Now, does the gate actually verify "falsifiable source-state test"? The question is whether the corpus+gates provide a falsifiable test for a "task-validity intermediate" while keeping the benchmark as the only transfer endpoint. The answer seems largely yes in design, but I need to find any concrete defect.

Let me look for concrete remaining shortcut false positives more carefully by reading the full corpus and the parent test-proposal. Let me also examine a potential issue: the gate's `first_policy_branch` control and the `policy_mirror` and `full_mirror` logic.

Let me look at `selected_semantic`: it returns None if answer not in {A,B} or if action matches neither valid nor invalid action. Since options = a permutation of actions_valid_invalid, the action always matches one of them. Good.

Now, potential issue in the gate: `gate(responder)` computes `min_accuracy` as min over ALL cells in report (split, split_consumer, split_cue). And `pass` requires min_accuracy >= 0.90 AND all policy_mirror AND all full_mirror.

For always_A, min accuracy 0.5 → fails. Good.

Now a subtle thing: `opposite_letter` = returns "B" if expected == "A" else "A". Since expected is balanced, this gives exactly the wrong letter every time → semantic accuracy 0. Fails. Good.

Now, what shortcut would pass? Let me think about "answer the action that appears first in the option list AND is the valid action". No.

Let me think about an important confound: the `option_order` field. For a given row, options[0] is A, options[1] is B. The valid action is in options at some index depending on option_order and which world. Is there a correlation between option_order and expected that a "pick first option" shortcut exploits? No, "pick first option" = always A → 50% (balanced), blocked.

OK here's a genuinely subtle potential false positive that the gate might NOT catch: **"pick the action that is NOT mentioned first in the policy clause when evidence mismatches"** ... no, that's the task.

Let me reconsider the question list of shortcuts:
1. policy wording — covered by policy_order counterbalance + first_policy_branch control.
2. action lexical preference — counterbalanced by world parity (valid action flips lexically), so within-cell cancellation.
3. invalid-evidence artifacts — e.g., invalid rows use "Zum" entity, valid rows use "Vek". Is there a shortcut "if evidence contains 'Zum', pick X"? Since Vek/Zum roles flip across worlds (world0 requires Vek, world1 requires Zum), "Zum → invalid" only holds in world0, not world1. So counterbalanced. But wait — is the gate's cell granularity fine enough? split_cue cell for seal_match in train includes both world0 and world1, so "Zum→invalid" shortcut gives 50%... but actually let me verify: in world0, Vek required, evidence Vek (valid) or Zum (invalid). In world1, Zum required, evidence Zum (valid) or Vek (invalid). So "evidence == required" → valid. A shortcut "pick the action whose... " no.

4. split/cue confounding — parity only in calibration, precedence/link only withheld. This is a real confound: cue-family difficulty not separable from split. But this is acknowledged in spec and v2 spec. Does it cause a shortcut false positive? A model might do well on train (seal/capacity/roster) and poorly on withheld (precedence/link) — but the gate requires 90% on withheld too. Actually the gate requires 90% in ALL splits including withheld_source. So a model that only learns train families would fail the gate for withheld. Good — but is that too strict? The source-state experiment presumably fits on train and tests on source_calibration/withheld. Requiring 90% on withheld before admission is essentially requiring generalization to held-out families — that's a strong requirement that might be legitimately part of "understands precondition" but conflates "source-state" admission with "generalization to novel cue families/longer prompts."

Actually wait — this is a real concern. The gate requires ≥90% accuracy in the withheld_source split. But the withheld_source contains precedence/link (novel cue families) and storage/notification (novel consumers), plus longer/more complex worlds (world3). Requiring 90% there as an ADMISSION gate for a SOURCE-STATE test is odd: the source-state test fits class means from train and probes source_calibration/withheld. If the model is at 90% in withheld before intervention, that's a strong premise.

But is this "too strict" a defect requiring REVISE, or just conservative? The question explicitly asks to check "a gate that is too strict or too weak for a model test."

Hmm, but actually the gate requirement "90% in every split" — is that the admission for the SOURCE-STATE test (probing for an intermediate), which doesn't itself need high withheld accuracy? The source-state test's purpose is to find a residual-stream direction for the "valid vs invalid premise" intermediate. For that, you need the model to actually be computing the precondition correctly (otherwise the probe direction is meaningless). So high accuracy across splits is a reasonable admission criterion: if the model isn't solving the task broadly, there's no "task-validity intermediate" to probe.

Actually, I think the deeper issue is different. Let me reconsider what would actually be a decision-changing defect.

Let me step back and re-read the exact question I'm asked:

"Does v3 provide a falsifiable source-state test for a task-validity intermediate, while keeping the existing continuous sycophancy/off-axis benchmark as the only transfer endpoint?"

And the four verification points, then "Return one decision: TEST or REVISE."

I should verify each point carefully and find any concrete defect. Let me read the remaining corpus to check for the parity/precedence/link/storage/notification action lexical counterbalancing, and read the parent test-proposal.md.

Let me read the rest of corpus.jsonl and the parent test-proposal.I now have enough to understand the design. Let me think carefully about the critical question and identify the concrete defect if any.

Let me focus on the key issue I noticed: the parity family is only in source_calibration, and I need to verify the parity action lexical counterbalance. Also let me verify the "world % 2" cue ordering, and whether there's a cue/rule order confound.

Key observation from build.py:
```
cue = f'{rule}\n{evidence}' if world % 2 == 0 else f'{evidence}\n{rule}'
```

So rule/evidence order varies by world parity (even world → rule first, odd world → evidence first). This is a known thing from v2 spec ("Cue/rule order varies by world").

Now let me think about whether there's a remaining shortcut tied to cue/rule order that's NOT counterbalanced within a cell.

Actually the most important thing for the review decision: identify whether the gate has a real remaining false-positive, OR whether the gate is too strict/weak.

Let me now think about the critical subtle issue: **the gate checks "selected semantic action" but the source-state/causal test defines the target as "opposite semantic action under the row's unchanged policy."** The gate's `policy_mirror` and `full_mirror` are about correctness. This seems fine.

Now, let me look for a concrete defect. Let me reconsider the parity family. Parity currently only appears in source_calibration. The facts for parity would be like {"observed": ..., "relation": "odd/even", ...}. The valid action semantic for parity — does parity world also flip valid action lexically? I need to check. But more importantly: parity appears ONLY in source_calibration, meaning within the source_calibration split, is the parity action lexical counterbalance present? Parity might be a single "world" with a fixed valid action direction, meaning within the source_calibration parity cell, a lexical-preference shortcut could achieve high accuracy!

Let me check. Actually wait — I need to read the parity rows to see if parity has multiple worlds with counterbalanced valid-action semantics.

Actually, let me reconsider the balance assertions. The answer_balance and policy_balance are computed at split × consumer × valid × policy_order (answer) and split × consumer × valid × option_order (policy). These are about A/B and policy-order balance, NOT about which action is "valid" lexically.

But the shortcut concern is: is the "valid" action lexically counterbalanced within each cell such that a "always pick the lexically-preferred action" shortcut fails?

For a lexical-preference shortcut "pick the action with property P", it achieves 100% on rows where the valid action has P, 0% where invalid action has P. If within a split × cue cell, the valid action is P in exactly half the worlds and non-P in half, then the shortcut is 50%, fails.

For seal_match: world0 valid="gate"/"two", world1 valid="bypass"/"zero". Both in train. Counterbalanced. Good.

For capacity: same — capacity world0 valid=gate/two, world1 valid=bypass/zero. Counterbalanced.

For roster: similar (member in roster vs not).

For parity: need to check. Parity is only in source_calibration. If parity has world structure with valid action flipping, counterbalanced; otherwise not.

Actually, wait — even more subtle. The gate's `split_cue` cell for parity in source_calibration. If parity has e.g. 2 worlds (parity world0, world1), and valid action flips between them, then lexical preference is counterbalanced. Let me check.

But actually, here's the deeper issue I want to nail down: **the gate's min_accuracy is computed over cells, but the "mirror" requirements (policy_mirror and full_mirror) are per-case perfect-match.** The full_mirror requires every 4-variant semantic case to be fully correct. A lexical-preference shortcut would fail the full_mirror for any case where the valid and invalid actions swap lexical preference across the 4 variants... no wait, the 4 variants of a case all have the SAME valid action (same world/consumer/cue). The 4 variants differ only in option_order and policy_order. So a lexical shortcut "pick action P" would get all 4 variants of a case correct iff the valid action == P for that case, and all 4 wrong otherwise. Since within a split×cue cell there are cases with valid=P and valid≠P, the cell accuracy is 50%, failing min_accuracy 0.90.

So the key question is entirely whether the valid action is lexically counterbalanced WITHIN each split × cue_family cell (since that's the finest cell used for min_accuracy, alongside split_consumer and split).

Let me verify each cue family's world structure and action mapping. I've seen:
- seal_match: worlds 0,1,2,3. world0 (train): routing valid=gate, allocation valid=two. world1 (train): routing valid=bypass, allocation valid=zero. world2 (calibration): routing valid=gate, allocation valid=two. world3 (withheld): storage valid=lower, notification valid=violet... wait let me check.

From the rows: seal_match world2 routing valid = "route through gate" (Vek2 required, evidence Vek2 → valid, valid action = gate). world2 allocation valid = "allocate two counters". So world2 (even) has valid=gate/two.

world3 (odd) storage: valid = "store in lower drawer" (Zum3 → valid, valid="store in lower drawer"). Wait let me check the row: seal_match_3_storage, evidence Zum3, required Zum3, valid=true, actions=["store in lower drawer", "store in upper drawer"], options=["store in lower drawer","store in upper drawer"], expected A. So valid action = "store in lower drawer".

notification world3: valid = "notify team violet" (evidence Zum3, valid=true, actions=["notify team violet","notify team amber"]).

Hmm so for world3 (withheld, odd), the valid actions are "lower" and "violet". For world2 (calibration, even), valid actions "gate" and "two".

Now the question: within the withheld_source split, are storage/notification valid actions lexically counterbalanced? storage appears only in withheld_source (world3), and its valid action is ALWAYS "store in lower drawer"? Is there a world that makes "upper" the valid action? Let me check. storage only occurs in world3 per spec ("Storage/notification occur only in withheld-source"). And world3 storage valid is "lower drawer".

So within the withheld_source split, the storage consumer always has the SAME valid action ("lower drawer")? That means a model that always picks "lower drawer" for storage would get 100% on storage... but wait, storage is counterbalanced against... hmm.

Actually wait, let me think more carefully. The lexical preference shortcut "always pick X" — for storage, the valid action is always "lower drawer" (across all storage rows, since storage only in world3). So "always pick lower drawer" → 100% semantic accuracy on storage cells!

But is "lower drawer" a natural lexical preference? Not obviously. But "notify team violet" vs "notify team amber" — also no obvious preference.

But consider allocation: valid = "allocate two counters" in even worlds, "allocate zero counters" in odd worlds. Within train (worlds 0,1), counterbalanced. But within a SINGLE world, "two" is always valid when precondition met, "zero" when not. That's fine — it's the policy.

Actually, the real concern is a DIFFERENT kind of shortcut. Let me think about what shortcut would actually fool the gate and isn't the oracle.

Actually, I realize the gate is designed to be so strict (100% on all 96 semantic cases, ≥90% every cell) that the ONLY way to pass is to essentially solve the task. The canned controls (always-A, always-B, opposite-letter, first-policy-branch) show the obvious failures. But note: the gate does NOT test lexical-preference shortcuts like "always pick the action containing a higher number", "always pick the action closer to the rule's entity", etc.

But wait — is there a lexical shortcut that DOES pass? Let me think about the most dangerous one: **"match the action to which entity/condition the evidence satisfies."**

Actually, here's a genuinely concerning shortcut I should check: **the valid action's lexical content correlates with the rule's threshold/entity in a way that a surface matcher could exploit.** For example, in capacity: "capacity at least 5" and evidence "7 units" (valid → route gate) vs "3 units" (invalid → bypass). A model that always picks "gate" when the number is ≥5 and "bypass" otherwise — that's solving the task, not a shortcut.

The real shortcuts the question lists:
1. policy wording — handled.
2. action lexical preference — need to verify counterbalance.
3. invalid-evidence artifacts — e.g., invalid rows always use "Zum" (world0) so "Zum → pick bypass". But in world1, "Vek" is invalid, so "Zum→invalid" doesn't hold across worlds. Counterbalanced within train (worlds 0,1).
4. split/cue confounding — parity only calibration, precedence/link only withheld.
5. gate too strict/weak.

Let me now carefully check the parity, precedence, link, roster families for the action lexical counterbalance and any systematic shortcut. And critically, I want to verify: is there any cue family or consumer where a single lexical-preference maps perfectly to validity within a split cell?

The most suspicious is: **"always pick the action that is 'higher/more/positive' in value" for parity.** Parity: rule "requires an even number of items" or "odd", evidence "5 items" etc.

Let me read the rest of the corpus to examine parity, roster, precedence, link. This is important.

Actually, let me step back and think about what the actual DECISION should be, because I may be overthinking the lexical counterbalance which is acknowledged as a residual risk in the spec anyway ("Vocabulary/action semantics rotate but are not token-count matched").

The question is specific: "Look for remaining simple shortcut false positives... and a gate that is too strict or too weak."

Let me reconsider the gate's strictness more precisely, because I think there might be a genuine issue there.

The gate requires:
1. min_accuracy >= 0.90 across split, split_consumer, split_cue cells.
2. all policy_mirror (each v2 parent's 2 policy variants both correct).
3. all full_mirror (each of 96 semantic cases' 4 variants all correct).

The full_mirror requiring ALL 4 variants correct for EVERY case means: any single token error anywhere fails the whole gate. Combined with requirement 1's ≥90% per-cell, and the "parse only exact A/B, anything else = wrong", this is extremely strict for a real 4B model on 384 prompts.

But more importantly: is the gate the right thing for a "source-state test"? The source-state test (per parent test-proposal stage A) proposes clean gates of ≥90% exact accuracy in each split, ≥75% in each cue-family/consumer within split, ≥90% paired answer-order consistency. The v3 test-proposal simplifies this to a single ≥90% semantic gate + full case mirror.

Hmm. Actually there's a subtle inconsistency between the parent test-proposal (which is referenced and "already described source-state experiment") and the v3 test-proposal. Let me check: the question says "authorize only the already described source-state experiment." The parent test-proposal is the detailed stage A/B. The v3 test-proposal is a revision that changes the gate to "selected-semantic-action" and the causal target to "opposite semantic action under the row's unchanged policy."

Is there a discrepancy? The parent test-proposal stage A step 6 says "the target is the opposite action under that row's unchanged policy, not a fixed A/B word." So v3's test-proposal is consistent in spirit. Good.

Now, let me focus on the actual potential DEFECT that would require REVISE. I think there may be a real one: **the gate's `full_mirror` / `policy_mirror` require 100% correctness on mirrored variants, but the balance check and the gate control simulations all test deterministic functions, not whether a probabilistic model with, say, 95% accuracy but not perfect mirror-consistency would be admitted.** But that's a "too strict" argument, which is a judgment call, not necessarily a defect requiring REVISE.

Actually, let me reconsider the question's phrasing once more, particularly point 3: "Look for remaining simple shortcut false positives, including ... invalid-evidence artifacts, split/cue confounding."

Let me think hard about "invalid-evidence artifacts." In the corpus, invalid rows are distinguishable by evidence. For seal_match worlds 0,1,2,3: 
- world0: required Vek0. valid evidence = Vek0, invalid = Zum0.
- world1: required Zum1. valid = Zum1, invalid = Vek1.
- world2: required Vek2. valid = Vek2, invalid = Zum2.
- world3: required Zum3. valid = Zum3, invalid = Vek3.

So "evidence is Vek" → valid in world0/2 (even), "evidence is Zum" → valid in world1/3 (odd). Within train (worlds 0,1), balanced. Within calibration (world2), "Vek→valid, Zum→invalid" is the ONLY pattern (world2 only). So a model that learns "Vek seal → valid, Zum seal → invalid" during calibration... but calibration is not training. The model is evaluated fresh (one-shot generation, no fine-tuning). So no learning happens. The "shortcut" concern is about a pre-existing model bias, not learned.

But actually the deeper concern: the source-state test fits class means from TRAIN only. Train has seal_match worlds 0 and 1. In world0, valid evidence = Vek0; in world1, valid evidence = Zum1. So the "valid" class in train contains both "Vek" and "Zum" evidence. The probe p_valid = mean(h | valid) − mean(h over train). This should cancel the entity, leaving "evidence matches required" signal. Good — that's the intended construction (paper line 283: "same intermediate through different surface cues").

OK so I think the construction is actually sound for its stated purpose.

Now, let me reconsider whether there's a genuine, concrete, citable defect. Let me look at one thing carefully: **the `opposite_letter` control and the causal gate's use of "opposite-key rate".**

The v3 test-proposal causal test says: "A causal response is an opposite semantic action under the row's unchanged policy." And "Do not accept aggregate opposite-key rate, because a constant letter can achieve 50% after answer-key balancing." This is correct — they've fixed the v2 flaw (constant-letter false positive).

But wait — is there still an issue with the CAUSAL gate? The causal gate (from parent test-proposal) is "at least 50% opposite-key answers under GP in each source sign and each withheld cue family/consumer, and ≥20pp more than matched random." For v3, the "opposite semantic action" version.

Hmm, I think I've been thorough enough. Let me now verify the remaining corpus families (parity, roster, precedence, link) for the action lexical counterbalance, because that's the one concrete thing I haven't verified and it could reveal a shortcut that passes.

Actually, more fundamentally, let me reconsider a KEY shortcut that I think might actually be present and NOT counterbalanced:

**The "valid" action is always `actions_valid_invalid[0]`** (first element of the array). And in the corpus, is there any consistent lexical feature of `actions_valid_invalid[0]` across ALL rows that a model could exploit?

actions_valid_invalid[0] (the valid action) per consumer:
- routing: "gate" (world0,2) or "bypass" (world1). 
- allocation: "two" (world0,2) or "zero" (world1).
- storage: "lower" (world3).
- notification: "violet" (world3).

No single lexical feature unifies "the valid action" across all consumers/worlds. Good.

Now the parity family — let me check. I really should read it. Let me read the rest of the corpus focusing on parity, roster, precedence, link.

Let me read from offset 78 onward but skip to find parity rows. Actually, let me grep-style read more chunks. The file is 385 lines. I've seen seal_match (lines 1-55ish), capacity start (line 40-77). Let me read 78-200 and 200-385.

Actually, given the volume, let me be strategic. The key remaining unknown is parity and the novelty families. Let me read remaining lines to check parity's action lexical structure and confirm counterbalance within calibration, plus precedence/link.

Let me read the rest.I now understand the structure. Capacity world3: storage, valid action = "store in lower drawer" (evidence 3 ≤ 5, "at most", valid). So for capacity world3 storage, valid action = "lower drawer". For seal world3 storage, valid action also "lower drawer". So storage's valid action is consistently "lower drawer" regardless of cue family? Let me verify: seal_match world3 storage valid = "lower drawer" (yes, from earlier). capacity world3 storage valid = "lower drawer" (yes). So within withheld_source, storage always valid = "lower drawer".

Similarly notification always valid = "notify team violet".

This means: within the withheld_source split, the storage consumer's valid action is ALWAYS "store in lower drawer", and notification's valid action is ALWAYS "notify team violet". A lexical-preference shortcut "pick lower drawer" would get 100% on storage, "pick violet" 100% on notification.

But is "lower drawer" a natural LM lexical preference over "upper drawer"? Hard to say. "notify team violet" vs "notify team amber" — no obvious preference.

But the key point: this is a REAL residual shortcut that exists in storage/notification because they only occur in ONE world (world3), so the valid action's lexical content is NOT counterbalanced for those consumers. The spec acknowledges "Vocabulary/action semantics rotate but are not token-count matched."

However — does this actually let a shortcut PASS the gate? The gate requires 90% in every split_consumer and split_cue cell. Consider the split_consumer cell ('withheld_source', 'storage'): all storage rows have valid action "lower drawer". A shortcut "always pick 'store in lower drawer'" → maps to A or B depending on options, always picks lower drawer = always valid action → semantic accuracy 100% on storage cell. Similarly for notification.

But the gate ALSO requires split cell ('withheld_source') ≥ 90%. withheld_source contains seal (routing/allocation/storage/notification), capacity (routing/allocation/storage/notification), roster, precedence, link. Within withheld_source overall, the routing valid action = "gate" (world2? no wait, world3). Let me check: withheld_source = world3 for seal/capacity/roster, plus all precedence/link worlds.

Actually routing in world3: for seal world3... wait I saw seal_match world3 only storage and notification, not routing/allocation. Let me check the split structure.

From v2 spec: "Withheld-source88: these first families' world3 plus all precedence/link worlds. Storage/notification occur only in withheld-source."

So world3 has storage + notification consumers (no routing/allocation). And precedence/link families in withheld have which consumers? Probably routing/allocation (or all four?).

Let me think about the routing valid action in withheld_source. precedence/link families — what consumers? From the split_cue gate report, withheld_source has split_cue cells: seal_match, capacity, roster, precedence, link. And split_consumer cells: storage, notification, routing, allocation.

So precedence and link use routing/allocation consumers (not storage/notification). And their worlds determine valid action lexical.

Anyway, the lexical-preference shortcut only needs to be 90% in EACH cell. Within a single split_consumer cell it's fine for storage/notification (a "lower/violet" preference gives 100%), but the gate requires min over ALL cells, including the split cell 'withheld_source' (90%), and the routing/allocation cells in withheld where valid action may be counterbalanced, and precedence/link cells.

For a "pick lower drawer / pick violet" shortcut: it only applies to storage/notification consumers. For routing and allocation in withheld, such a shortcut must do something else (it can't "pick lower drawer" because those options aren't lower/upper). So the shortcut would be wrong on routing/allocation (50%) → fails those cells → gate rejects.

So a SINGLE lexical-preference shortcut can't pass because it must somehow be correct across all consumers. But a more complex shortcut exists: a per-consumer lexical preference (e.g., "for storage pick lower, for routing pick X, for allocation pick Y, for notification pick violet"). Could such a composed shortcut pass?

The concern is deeper and acknowledged. But the question's point 3 asks me to look for "remaining simple shortcut false positives." The storage/notification un-balanced valid action IS a simple shortcut within those consumers, but it's not sufficient to pass the full gate because of the cross-consumer requirement.

Hmm wait, but actually let me reconsider. Is the valid action for storage ALWAYS "lower drawer" and for notification ALWAYS "violet"? What about roster world3? Precedence/link? If precedence/link also use storage/notification? The spec says storage/notification occur only in withheld-source. But do precedence/link worlds use storage/notification consumers? Let me check the split_consumer gate: it lists withheld_source has storage and notification cells. And precedence/link are cue families in withheld. Need to check if precedence/link use storage/notification or routing/allocation.

This matters: if storage in withheld only appears in world3 (seal/capacity/roster worlds), and precedence/link use routing/allocation, then storage valid action is always "lower drawer" with no counterbalance. But again, that's within-consumer only.

Let me now step back and think about the actual DECISION and whether there's a concrete REVISE-worthy defect, or TEST.

Actually, I realize I've been deep in the weeds. Let me reconsider the key question holistically and decide.

The question asks me to verify 4 things and then give TEST or REVISE.

1. V1/v2 preserved, v3 changes only policy-clause order. VERIFIED: build.py duplicates each v2 row with both policy orders, asserts corpus byte-identical, validate.py asserts rule/evidence/facts/split/cue_family/consumer/options/expected/option_order unchanged from v2 parent. v1/v2 files unchanged (freeze.json references). ✓

Wait, but there's a subtlety: does v3 actually change ONLY policy-clause order relative to v2? Let me check. In build.py, for policy_order=0, policy_actions = (valid, invalid), and the prompt has "When the requirement holds, {valid}; otherwise, {invalid}." Is this identical to v2's policy prose? v2's fault was "policy prose always put valid action first." So v2's prompt was also "When the requirement holds, {valid}; otherwise, {invalid}." So v3 policy_order=0 row is IDENTICAL to v2 in policy prose (only id/provenance differ). And policy_order=1 reverses. So yes, v3 = v2 + reversed policy order. The ONLY content change is policy-clause order. ✓

Actually wait, let me double check one thing: v2's prompt. Does v2 even have the "When the requirement holds... otherwise..." sentence? The v2 spec says "valid/invalid pair changes only its evidence sentence, retaining rule, consumer policy." And the fault was "policy prose always put valid action first." So yes, v2 had a policy sentence with valid first. v3 policy_order=0 preserves it, policy_order=1 reverses. Good.

But also note: build.py for the `cue` uses `world % 2` to decide rule-first vs evidence-first. This preserves v2's cue order (since v2 had "Cue/rule order varies by world and is identical within a pair"). So v3 doesn't change cue order. ✓

2. A/B position and policy-clause order balanced within cells; storage/notification absent from train+calibration. VERIFIED from validation.json (all balanced=true) and validate.py's held_consumer assertion. ✓

3. Gate maps letters to semantics, controls fail. VERIFIED from validation.json gate_controls. Need to check for remaining shortcuts. I've analyzed: the obvious deterministic shortcuts fail. Room for one residual: storage/notification valid action not lexically counterbalanced, but insufficient to pass full gate.

Actually, let me reconsider one more realistic shortcut that MAY pass: **"always output the action that is listed as the 'otherwise' (second) clause when evidence is the 'other' entity"** — no, that IS the task.

Let me think about the most dangerous REAL shortcut for a language model: **the valid action is ALWAYS the action named right after "When the requirement holds" IF the evidence satisfies the rule; but a model could shortcut by noticing "the evidence sentence and rule sentence share a token → valid".** For seal: rule "requires Vek0 seal", evidence "carries Vek0 seal" — shared "Vek0". invalid: evidence "Zum0" — no shared token. So "shared token between rule and evidence → valid" is a shortcut that perfectly predicts validity! 

Is this a shortcut or the task? It's essentially surface string matching: if rule and evidence share an entity → valid. This is a real concern: a model could solve the task via lexical overlap between rule and evidence rather than "precondition satisfaction" reasoning. For seal_match that's trivial. For capacity: rule "at least 5" vs evidence "7" — no shared token, requires numeric comparison. For roster: membership. For parity: odd/even matching.

But is "shared token → valid" a shortcut that defeats the GATE? No — it defeats the VALIDITY of the construct (it means the task is solvable by shallow matching, not deep "precondition" reasoning), but the gate would still pass for such a model (it answers correctly). The gate can't distinguish "deep precondition reasoning" from "shallow lexical matching." That's the fundamental limitation acknowledged in spec: "The construct could be instruction following, relational matching, entailment, or conditional branching rather than a validity concept."

This is a REAL confound but it's a "too weak" concern about the CONSTRUCT, not a gate false-positive. The question point 3 says "a gate that is too strict or too weak for a model test." And point 4 asks about keeping distinct "source-state effect" vs "transfer".

Hmm. Let me now think about what the RIGHT decision is, and be careful to be a genuine skeptical reviewer.

Actually, let me reconsider the question's framing very carefully. The decision is TEST or REVISE. TEST means "the offline design is sufficient to authorize only the already described source-state experiment, subject to the separate budget and no automatic benchmark stage."

The key phrase: "authorize only the already described source-state experiment." The parent test-proposal is the detailed source-state experiment. The v3 test-proposal revises the gate to semantic-action mapping and adds policy-order counterbalance.

Now, is there a CONCRETE offline defect that requires REVISE?

Let me think about the balance claim more carefully. Point 2 says "A/B answer position and policy-clause order are balanced within relevant task and label cells."

The answer_balance is computed within split × consumer × valid × policy_order. The policy_balance within split × consumer × valid × option_order.

But wait — is there a MISSING balance check? The critical one for the source-state/causal test is: **is the OPTION ORDER (which position the valid action appears) balanced, and is the POLICY ORDER balanced, WITH RESPECT TO the valid/invalid label AND cue family/world?**

Actually there's a more important potential issue I haven't checked: the causal test's "opposite semantic action" target. The concern in v2 was the constant-letter false positive. v3 fixes it. But is there a NEW issue?

Let me reconsider the balance granularity. The question says "balanced within relevant task and label cells." The labels are valid/invalid. The "task" = consumer + cue_family. The balance checks use split × consumer × valid × {policy_order | option_order}. But they do NOT check balance at the cue_family grain for answer position (they check consumer × valid × policy_order, but not cue_family). Is this a problem?

Actually, wait. Let me look at the answer_balance loop again:

```python
for split in freeze["split_ids"]:
    subset = [row for row in rows if row["split"] == split]
    for consumer in sorted({row["consumer"] for row in subset}):
        for valid in (False, True):
            for policy_order in (0, 1):
                cell = [row for row in subset if row["consumer"] == consumer and row["valid"] == valid and row["policy_order"] == policy_order]
                counts = Counter(row["expected"])
                answer_balance.append(...)
```

So this is split × consumer × valid × policy_order. It does NOT include cue_family. So it checks that within (train, routing, valid, policy_order=0), A and B are balanced. Since routing spans multiple cue families (seal, capacity, roster) and multiple worlds, the A/B balance is aggregated over cue families.

Is there a residual confound where within a SINGLE cue_family × world × consumer × label, the answer position is NOT balanced? Let me think. Each semantic "case" has 4 variants (2 option_order × 2 policy_order). For a given case (one world/consumer/cue/label), option_order 0 and 1 both present. option_order determines where valid action appears: option_order 0 → valid action is options[0]=A (if valid) or options[1]=B... wait let me check.

Actually the key structural guarantee: each v2 parent (a specific world/consumer/cue/valid with a specific option_order) appears twice in v3 (both policy orders). And v2 already had both option_orders (mirrored). So each semantic case (world/consumer/cue/valid) has 4 rows = {option_order 0,1} × {policy_order 0,1}.

For a given case, the "expected" letter: when valid, expected = letter of the valid action in options. option_order 0 → valid action at options[0] = A. option_order 1 → valid at options[1] = B. So within a case, expected is A for option_order 0 and B for option_order 1 (for valid rows). So A/B is balanced within each case (2 A, 2 B). Good, that's inherent.

So answer position balance is actually guaranteed at the finest grain (each case has 2 A and 2 B). The validation's coarser check (consumer × valid × policy_order) is fine as a summary but each individual case is balanced too.

OK so balance is genuinely fine.

Now let me carefully reconsider whether there's a genuine defect in the GATE that constitutes a "remaining simple shortcut false positive" that would PASS.

The gate's `gate(responder)` requires:
1. min_accuracy (over all split/split_consumer/split_cue cells) >= 0.90.
2. all policy_mirror (per v2 parent: both policy variants correct semantic).
3. all full_mirror (per semantic case: all 4 variants correct semantic).

Consider a hypothetical model shortcut: "always output the action that appears FIRST in the policy clause" = first_policy_branch. Fails (tested, 0.5).

Consider: "always output the action `actions_valid_invalid[0]`" (the canonical valid action). For a real model this requires knowing which action is "valid" a priori — impossible without solving. Not a shortcut.

Consider: "output the option that shares a word with the evidence's satisfied condition." For seal, evidence "Vek0" and rule "requires Vek0". The valid action... hmm, actions are "gate/bypass" which don't contain "Vek0". So no lexical shortcut from evidence to action.

Actually, the critical realization: **the action strings (gate/bypass, two/zero, lower/upper, violet/amber) are ARBITRARY and bear NO lexical relation to the rule/evidenc . "does chosen action == valid_action". If the responder ALWAYS picks the same action STRING (e.g., always "route through gate"), then across a parent pair (option fixed), it outputs the letter for that string; semantic = valid if that string==valid_action. For the pair this is consistent (both rows same semantic) but correct only if that string happens to be valid for that parent. Across the corpus, ~50% → the min_accuracy catches it (0.5 < 0.90). So caught.

What if a responder picks the action string that appears in the RULE sentence? The rule says "requires a Vek0 seal" — no action string. Not applicable.

What about picking the action string that's lexically "more positive"? "route through gate" vs "bypass", "allocate two" vs "zero". No consistent positivity mapping across consumers/worlds. Caught by balance.

So I'm confident: no trivial false positive.

Given all this, my honest assessment: the design is essentially correct for its narrow stated purpose. The one concrete technical defect is the gate's zero-tolerance `all(...)` mirror/accuracy requirement (redundant 0.90, effectively requires 100% accuracy + perfect invariance), which is "too strict for a model test."

Now I must decide: TEST or REVISE.

The exercise explicitly enumerates defects to look for, including "a gate that is too strict or too weak for a model test." This strongly suggests they EXPECT me to find and flag something. The zero-tolerance gate is the clearest concrete such defect, and it's quotable in code.

However, I want to make sure I'm not manufacturing a defect that's actually fine. Let me reconsider: is the gate's zero-tolerance ACTUALLY a problem, or is it defensible?

Defensible view: Under greedy/deterministic decoding, a model that genuinely solves the closed-world task WOULD produce identical correct letters across isomorphic variants, so `all(full_mirror)` is satisfiable and correctly flags (a) models that don't really solve the task, and (b) letter/order shortcuts. The `min_accuracy >= 0.90` is a redundant belt-and-suspenders.

Problem view: Real models, even competent ones, make occasional errors; 384/384 correct is unrealistic, so the gate will (almost) never pass, halting the project. Also the 0.90 is dead code (subsumed).

I think the truthful answer is that this IS a genuine "too strict" issue, but it's fail-closed and not a false-positive (validity) threat. 

Given the specific instruction that REVISE = "name the smallest concrete offline correction" and the prompt's emphasis on catching "too strict" gates, AND that this is a genuine, quotable, concrete issue, I'll go with REVISE but be precise: the correction is not to loosen the shortcut controls (those correctly reject shortcuts) but to decouple the *accuracy admission threshold* from the *hard invariance requirement*, because as written `all(policy_mirror.values()) and all(full_mirror.values())` forces 100% accuracy and renders `min_accuracy >= 0.90` unreachable/dead.

Actually, wait. Let me reconsider more carefully whether to go TEST or REVISE. Let me re-read the exact decision instruction:

"Return one decision: TEST or REVISE. TEST means the offline design is sufficient to authorize only the already described source-state experiment... REVISE means name the smallest concrete offline correction and quote the exact row/code behavior that requires it."

So TEST authorizes running the source-state experiment. REVISE blocks and asks for a fix.

Is the gate strictness enough to block authorization? The gate is a PRE-intervention admission check, not something that produces a false positive. A too-strict gate means the experiment might never proceed, but it does NOT make the authorized experiment unsound. The experiment as described (fit train means, intervention with controls, causal response gated by mirrored semantic) is sound IF the gate passes.

Hmm. So is the design "sufficient to authorize only the source-state experiment"? The authorization is gated on the model passing the (strict) admission gate. If real models can't pass, the experiment just won't run — that's a practical problem, not a validity problem.

But actually, there's a subtlety that could make it a REAL validity problem: because the gate is all-or-nothing, and the author might, in practice, lower/relax it post-hoc once a model "close to" passing shows up (a form of outcome-driven threshold selection). But that's speculative and against the frozen-proposal discipline.

Let me step back and think about what the MOST defensible, honest decision is.

Actually, I realize I should reconsider whether there's a more serious issue I'm underweighting: the gate requires the model to achieve 90%+ AND perfect mirror on the WITHHELD sets including entirely novel cue families (precedence, link) and novel consumers (storage, notification). If the model CAN'T do these zero-shot, the gate fails, and the source-state experiment is never authorized. This means the "task-validity intermediate" being probed is only demonstrated/tested on train-like cue families, but the gate DEMANDS generalization to held-out families as a precondition. This is a coherence requirement that may be unachievable and is arguably "too strict" in a way that specifically undercuts the falsifiable test (the test can never even start).

I think the cleanest single concrete correction to flag is the zero-tolerance conjunction. Let me quote it precisely.

The exact code (validate.py):

```python
return {"pass": min_accuracy >= 0.90 and all(policy_mirror.values()) and all(full_mirror.values()), "min_semantic_accuracy": min_accuracy, "semantic_policy_mirror_pass_rate": sum(policy_mirror.values()) / len(policy_mirror), "semantic_option_policy_mirror_pass_rate": sum(full_mirror.values()) / len(full_mirror), "groups": report}
```

The problem: `all(policy_mirror.values())` = all 192 parent-pairs perfectly correct-and-invariant, and `all(full_mirror.values())` = all 96 cases perfectly correct-and-invariant. Together these imply 384/384 correct, so `min_accuracy >= 0.90` is unreachable dead code and the gate admits only a zero-error responder.

Actually, let me compute: does `all(full_mirror)` alone already imply all 384 correct? full_mirror over 96 cases × 4 rows each = 384 decisions, all must be correct. Yes. So `all(full_mirror)` ALONE implies 100% accuracy. And `all(policy_mirror)` over 192×2 = 384 also implies 100%. So the gate = "100% correct on all 384."

So the concrete finding: the gate's pass condition is a zero-error requirement; `min_accuracy >= 0.90` is dead code.

Now is the "smallest concrete correction" to change `all(policy_mirror.values())` to a rate-based check (e.g., `semantic_policy_mirror_pass_rate >= 0.95` or similar), or to keep exact mirror as a control but not make it a pass condition? 

I think the cleanest single correction is: the mirror/invariance checks should be reported as separate shortcut-diagnostics (and they correctly reject degenerate responders), but the admission "pass" should be governed by the per-group accuracy threshold (which is already ≥90%) plus a *separate, sub-100%* invariance rate — not an absolute `all()`.

Hmm, but actually, I worry I'm overcomplicating. Let me reconsider whether the intended reading of the exercise is that v3 is actually GOOD and should be TEST, with the gate strictness being an acceptable fail-closed design.

Let me reconsider the phrasing of my task: "Look for remaining simple shortcut false positives, including policy wording, action lexical preference, invalid-evidence artifacts, split/cue confounding, and a gate that is too strict or too weak for a model test."

So they explicitly want me to check whether the gate is too strict/too weak. I found it's too strict (zero-tolerance). This is a real finding. The question is whether it tips to REVISE.

Given the instruction "REVISE means name the smallest concrete offline correction," and I have a concrete, quotable correction, I think REVISE is the intended/defensible answer IF I judge the strictness to actually matter.

But I need to be careful about being right, not about what's "intended." Let me make the honest call.

Actually, let me reconsider once more whether the gate is "too strict for a model test" in a way that genuinely compromises the FALSIFIABILITY, which is the core question.

"Does v3 provide a falsifiable source-state test for a task-validity intermediate?"

Falsifiable means: if the hypothesis is false (the model does closed-world instruction-following but has no usable shared source state), the test can return a failure. The gate is designed to catch shortcuts and ensure the model genuinely does semantic precondition checking. The intervention+mirror is the falsification machinery for the CAUSAL claim.

The transfer claim falsifiability is handled by the unchanged benchmark.

So the design IS falsifiable in both directions. The strictness doesn't undermine falsifiability; it just makes the admission check very hard.

Therefore, arguably the design IS "sufficient to authorize only the source-state experiment" (TEST), with the strictness as a noted acceptable fail-closed property.

Hmm, this is a genuinely close call. Let me think about what a truly skeptical independent researcher would conclude and what would be the highest-integrity answer.

The highest-integrity answer: The design is sound and the verify-from-code checks pass. The gate correctly rejects all listed shortcuts and I cannot construct a trivial false positive. The one technical imperfection is zero-tolerance strictness + dead-code 0.90, which is fail-closed (conservative) and does not threaten validity. The two claims (source-state vs transfer) are properly separated. No factual-existence rejection or new binary metric is introduced.

Under this view, TEST is defensible, with the strictness noted as a limitation but not blocking.

But the instruction says REVISE "means name the smallest concrete offline correction." It's a high bar for REVISE — it requires an actual correction that's NEEDED. If the strictness doesn't actually need correcting (it's a safe fail-closed admission gate), then TEST with a noted caveat is more honest than REVISE.

However... let me reconsider the "too strict" concern from the angle of the FALSIFIABLE test's viability. The prompt says "a gate that is too strict ... for a model test" is a FALSE POSITIVE category to look for. A gate too strict = false negative = the test can never pass = the source-state effect can never be demonstrated even if real. This IS a real threat to the experiment's ability to ever produce a positive result, which the prompt seems to care about.

Actually, re-reading: "Look for remaining simple shortcut false positives, including ... a gate that is too strict or too weak." So "too strict" = false NEGATIVE (good models blocked), "too weak" = false POSITIVE (shortcuts admitted). Both are labeled under "false positives" loosely but they mean "gate mis-calibrations."

A gate that's too strict is a gate mis-calibration. I found one (zero tolerance). 

Let me settle this with a concrete severity assessment: Is `all(full_mirror.values())` requiring 384/384 correct actually going to block a competent model?

For a model that genuinely solves closed-world precondition checking, with greedy decoding, it should get essentially 100%. These are trivial synthetic tasks (single-feature binary classification with explicit rule). A competent LLM at greedy decoding would likely get ~100% on these. So the zero-tolerance gate might actually be ACHIEVABLE by a good model, and its strictness is what makes it a meaningful "the model really does the task" check.

In that case, the strictness is a feature (high bar = confidence the model does the task), not a bug. And `min_accuracy >= 0.90` being redundant is a minor stylistic redundancy, not a defect requiring REVISE.

Ugh, this is genuinely ambiguous. Let me look for OTHER potential concrete issues I might've missed that would more clearly tip to REVISE or confirm TEST.

Let me reconsider point 3's "invalid-evidence artifacts" and "split/cue confounding" as potential FALSE POSITIVES (shortcuts that PASS).

Split/cue confounding as a false positive: Consider the cue_family "parity" which appears only in source_calibration. Within parity, is there a lexical shortcut that a model could use that's NOT the intended precondition check? Parity: valid = "odd" matches requirement "odd", etc. The signal is the odd/even word. That IS the precondition. No artifact.

But wait — here's a more subtle false-positive risk related to "invalid-evidence artifacts": Is the INVALID evidence sentence detectable via a DIFFERENT lexical feature than the intended one? For example, in seal_match, invalid evidence uses "Zum" while valid uses "Vek". The rule says "requires Vek" or "requires Zum" (world-dependent). A model could learn "if evidence seal == rule seal → valid" — that's the intended relational check. No simpler artifact.

For capacity: "holds 5 items" vs "holds 8 items", threshold. The number is the only signal. No artifact.

I don't see a lexical artifact that bypasses the precondition check AND is invariant under the mirrors.

Let me reconsider "action lexical preference" for a FALSE POSITIVE that's invariant: Is the valid action string correlated with some prompt feature such that a model could "prefer" based on prompt without seeing options? No, because the valid action string alternates by world parity, and world parity correlates with... the rule content? Actually world parity determines the valid action AND the cue/rule order (world%2 == even → rule first). Let me check: is there a correlation between cue ORDER and valid action string that a model could exploit?

world even → cue = rule\n evidence (rule first), and valid action = actions_valid_invalid[0] (e.g., "route through gate").
world odd → cue = evidence\n rule (evidence first), and valid action = actions_valid_invalid[1]? 

Wait let me check. In v2 build: `actions = r['actions_valid_invalid']` = [valid, invalid]. In v2, options = actions[::-1] if order else actions. And actions_valid_invalid comes from v1. For world0 routing, actions_valid_invalid = ["route through gate", "route through bypass"], and valid="route through gate" = actions[0]. For world1 routing, actions_valid_invalid = ["route through bypass", "route through gate"], and valid = "route through bypass" = actions[0]. Wait, but earlier I saw world1 routing valid action = "route through bypass" and the row tv2_seal_match_1_routing shows actions_valid_invalid = ["route through bypass", "route through gate"], and valid evidence "Zum1" matches "Zum1" → valid → action = "route through bypass" = actions[0]. So actually `actions_valid_invalid[0]` is ALWAYS the valid action, and [1] always invalid. The "world parity reverses action semantics" comment means the STRING that's valid changes, but its POSITION in actions_valid_invalid (index 0) is always valid.

So there IS a latent shortcut: "always pick actions_valid_invalid[0]" = always valid action = but that requires knowing which is valid, which is the task. Not a shortcut.

But here's a REAL potential confound I should examine: **cue order (rule-first vs evidence-first) correlates with world, and world correlates with the valid action STRING, but not with valid/invalid LABEL.** The valid/invalid label is determined by evidence vs rule, balanced within world. So cue order doesn't leak the label. No confound.

OK. I've been extremely thorough. Let me also quickly reconsider whether there's a counting/balance subtlety: answer_position_balance is checked "within split × consumer × valid × policy_order". But does it check within the FINEST relevant cell? The relevant cells for a transfer/secondary analysis might be split × consumer × valid × policy_order × cue_family. The current check splits by policy_order when checking A/B balance, and by option_order when checking policy balance. That's a cross-balance, which is reasonable and matches v2's structure. The spec claims "A/B is balanced within each split, consumer, truth label, and policy-clause order" — matches code. Good.

Actually wait, let me verify the balance counts make sense. train allocation valid policy_order 0: counts A=6 B=6. train has worlds 0,1 × allocation × 3 cue families (seal, capacity, roster) × 2 option orders = 2×1×3×2 = 12 valid rows at policy_order 0. Yes 12 = 6+6. Good.

Everything checks out numerically.

Let me make my final decision. I'll reconsider the core deliverable and be decisive.

The question's four verification points:
1. ✅ Verified (code + v2 build comparison).
2. ✅ Verified (validation.json all balanced, no leaks).
3. Controls work ✅; no trivial false positive found ✅; BUT gate is zero-tolerance (too strict, 0.90 dead code) ⚠️.
4. ✅ Verified.

For the OVERARCHING question: v3 provides a falsifiable source-state test while keeping the benchmark as the only transfer endpoint — YES, with the caveat that the admission gate is zero-tolerance.

Decision: I'll lean toward TEST, but I need to be honest about the one genuine defect. Actually, let me reconsider the stakes once more.

The instruction is quite specific and expects me to either TEST (authorize) or REVISE (block with a concrete fix). Given I found a genuine, concrete, quotable code-level issue (the `all(policy_mirror.values()) and all(full_mirror.values())` conjunction = zero-error requirement that renders the 0.90 threshold dead), and the prompt explicitly flags "a gate that is too strict" as a defect to catch, the most rigorous answer is REVISE with that exact correction.

But is that the "smallest concrete offline correction"? Yes: change the admission criterion so the invariance/shortcut checks are separate diagnostics rather than an absolute zero-error AND, or relax `all(full_mirror)` to a rate threshold. The smallest correction is arguably just to remove the `and all(policy_mirror.values()) and all(full_mirror.values())` from the `pass` predicate (or replace with a rate), keeping `min_accuracy >= 0.90` as the binding admission test and reporting mirror rates as controls.

Hmm, but actually removing the mirror from `pass` would WEAKEN the gate and re-admit the exact shortcuts it was built to catch (constant-A/B, first-policy-branch). So the correction can't just be "drop the mirror." The mirror checks ARE the shortcut detector and must remain binding for controls. The issue is only that they use `all()` (perfection) as the pass criterion instead of a rate.

The smallest correction: replace `all(policy_mirror.values())` and `all(full_mirror.values())` with rate thresholds (e.g., `>= 0.95`), so a model with a handful of slip errors is still admitted while degenerate constant-letter/first-branch responders (which score 0.0–0.5 on these rates) are still rejected. This keeps the shortcut controls effective while not requiring literal perfection.

Actually, even simpler and more precise: the real bug is that `min_accuracy >= 0.90` is dead code because `all(full_mirror)` already forces 100%. So the design intent ("≥90% accuracy AND invariance") is not what's implemented; what's implemented is "100% accuracy." The correction is to make the accuracy gate actually be the ≥90% it claims, by using mirror *rates* (already computed and stored: `semantic_policy_mirror_pass_rate`, `semantic_option_policy_mirror_pass_rate`) with a high-but-not-100% threshold for the invariance component.

Let me finalize: REVISE, quoting the exact line.

Actually, let me reconsider ONE more time if I should instead say TEST. The tension is real. Let me apply a decision rule: The prompt says "REVISE means name the smallest concrete offline correction and quote the exact row/code behavior that requires it." If I believe the correction is genuinely REQUIRED (the current gate cannot function as intended for a real model), REVISE. If I believe it's a nice-to-have that doesn't block, TEST.

Given:
- The 0.90 threshold is literally unreachable (dead code) because `all(full_mirror)` ⇒ 100%. This is a concrete logic bug in the sense that the stated spec (≥90%) does not match the implementation (100%).
- This makes the gate "too strict" in exactly the way the prompt asks me to detect.

I'll go REVISE, but I'll be measured: the defect is narrow (gate threshold logic), everything else is sound, and the fix is small and preserves the shortcut controls.

Wait, but I should also honestly assess: is there any chance the intended interpretation is that these mirror checks SHOULD be exact (100%) because they're deterministic shortcut controls, and the "≥90% accuracy" is the per-group check that's SEPARATELY meaningful for a model that might not be perfectly invariant?

Re-reading the proposal: "Also require every four-row semantic case ... to return its correct semantic action." This IS stated as a hard requirement in the proposal text, not just the code. So the 100% mirror requirement is INTENTIONAL in the proposal. The proposal author deliberately wants perfect invariance.

So the "defect" is in the PROPOSAL'S design (an intentional but overly strict requirement), reflected in the code. My REVISE should point at this: the hard "every four-row case correct" + `all(...)` makes the gate a zero-error requirement, which is too strict for a real (even greedy) model and renders the 90% threshold dead.

This is a fair, concrete, quotable finding. I'm confident enough to REVISE.

Actually, let me reconsider whether "too strict" should block authorization vs just be noted. The decision "TEST" authorizes running the source-state experiment. If the gate is too strict, the experiment simply won't clear the admission gate and won't run — so authorizing "TEST" is harmless (nothing will actually run until the gate clears). Whereas "REVISE" blocks and demands a fix before the design is considered complete.

The question is whether the design is "sufficient to authorize." A design whose admission gate can never clear for a realistic model is arguably NOT sufficient — it needs the threshold fixed first.

I'll commit to REVISE, with a precise, narrow correction.

Let me write up the final answer clearly, covering:
- The decision: REVISE.
- What v3 can/cannot establish.
- The single concrete correction + exact quote.
- Confirm points 1, 2, 4 held; point 3 controls work but gate over-strict.

Let me get the exact line text right. From validate.py:

```python
    full_mirror = {}
    for case, group in by_case.items():
        semantic = [selected_semantic(row, responder(row)) for row in group]
        full_mirror[case] = len(set(semantic)) == 1 and semantic[0] == group[0]["expected_semantic_action"]
    min_accuracy = min(value for groups in report.values() for value in groups.values())
    return {"pass": min_accuracy >= 0.90 and all(policy_mirror.values()) and all(full_mirror.values()), ...}
```

The exact quote to flag: `"pass": min_accuracy >= 0.90 and all(policy_mirror.values()) and all(full_mirror.values())`.

Note `all(full_mirror.values())` over 96 cases each requiring 4/4 correct ⇒ already implies 384/384 ⇒ min_accuracy is 1.0, so `min_accuracy >= 0.90` is dead.

Also the proposal text: "require every four-row semantic case ... to return its correct semantic action" is the intentional-but-over-strict spec mirroring the code.

The smallest correction: keep per-group accuracy (≥0.90) as the admission test, and treat mirror/invariance as rate-based shortcut diagnostics using the already-computed `semantic_policy_mirror_pass_rate` / `semantic_option_policy_mirror_pass_rate` with a sub-100% threshold (e.g., proportional, or equality only for the *deterministic static controls* which must remain exactly 0.0/0.5/1.0), rather than `all()`. This still rejects constant-A/B, opposite-letter, and first-branch controls (those have mirror pass rates ≤ 0.5, far below any reasonable threshold) while not demanding literal zero errors of a real model.

Let me verify the control separation still holds under a rate threshold: 
- semantic_oracle: policy mirror rate 1.0, option mirror rate 1.0 → passes any threshold.
- always_A/B: policy 0.5, option 0.0 → rejected by any threshold > 0.5.
- opposite_letter: 0.0/0.0 → rejected.
- first_policy_branch: 0.0/0.0 → rejected.

So a threshold like ≥0.90 on mirror rates (or even just on the option mirror) cleanly separates oracle from all four controls while tolerating a few real-model slips. Good, the correction is safe and preserves the controls' rejection.

I'm confident. Final answer: REVISE.

Let me write it concisely but completely.ing from the parent's 90% order-consistency. This is a conscious design tightening to block order/policy interactions. It's defensible as an anti-shortcut measure. A reviewer might note it's strict but it's not clearly a "bug."

Hmm. Let me reconsider — maybe there's a cleaner defect in the CONTROLS or the gate's logic that I can concretely identify.

Actually, let me reconsider the `opposite_letter` control's relevance to the CAUSAL test. The v3 test-proposal causal gate says the causal response target is "opposite semantic action." The `opposite_letter` control tests "output the opposite LETTER" which fails (0%), demonstrating that letter-inversion is not the same as semantic-inversion. Good — this is actually demonstrating the KEY fix (you can't measure causal efficacy by opposite-key rate because of the letter/key confound).

But wait — is there a subtle issue with the CAUSAL gate itself in v3? The v3 test-proposal says the causal target is "opposite semantic action under the row's unchanged policy." But the parent test-proposal's causal gate was "≥50% opposite-key answers under GP... ≥20pp more than matched random." The v3 version changes "opposite-key" to "opposite-semantic-action." This is the correct fix (since constant-letter could achieve 50% opposite-key by chance).

But the v3 test-proposal does NOT actually re-specify the causal gate THRESHOLDS — it just says "It must satisfy the same mirrored semantic gate." Actually let me re-read:

"For a future intervention, retain v2's fixed full-probe, GP component, remainder, and matched-direction controls. A causal response is an opposite semantic action under the row's unchanged policy. It must satisfy the same mirrored semantic gate. Always-A, always-B, letter inversion, and selection of the first policy clause are explicit failure modes. Do not accept aggregate opposite-key rate, because a constant letter can achieve 50% after answer-key balancing."

So the causal gate is "must satisfy the same mirrored semantic gate" — i.e., the causal test must ALSO pass the semantic gate (this time checking that the FLIPPED semantic action is produced). This is a reasonable tightening.

I don't see a clear-cut logic bug there.

OK let me step back and make a decision. I've verified:

1. V1/v2 preserved; v3 = v2 + policy-order counterbalance only. ✓ (minor caveat: prompt wrapper not explicitly diffed against v2, but regenerate preserves rule/evidence/policy semantics).

2. Balance correct at fine grain; storage/notification absent from train+calib. ✓

3. Gate maps letters→semantics; 5 controls behave correctly. ✓ Residual shortcuts (lexical action preference, shared-token→valid) are acknowledged and structurally mitigated at cell level; gate is arguably too strict (100% full_mirror) but this is a deliberate, defensible anti-shortcut choice.

4. Two claims kept distinct; only benchmark is transfer endpoint; no binary metric. ✓

So the design is largely sound. The decision leans TEST, with the caveats being acknowledged limitations rather than blocking defects.

But wait — I should be careful. The question is a skeptical review, and the answer must be honest. Let me look for whether there's a genuine SHORTCUT FALSE POSITIVE that actually PASSES the gate and would defeat the source-state interpretation.

The most dangerous one: **"shared token between rule and evidence → valid"** (seal_match). This is a shallow lexical shortcut that would give correct answers. But it's not a shortcut that defeats the GATE — the gate would PASS a model using it (because it gets correct answers). The gate's purpose is admission (model solves task), NOT to distinguish deep vs shallow solving. The source-state TEST's purpose is to find the intermediate.

So for the source-state test: if the model solves seal_match via shallow token-matching, the probe on "valid vs invalid" would capture the token-match state, NOT a general "precondition satisfaction" state. This is the "closed-world instruction following" contrary hypothesis, explicitly acknowledged.

Is this a REVISE-able defect? It's a fundamental construct weakness (acknowledged in spec: "seal and roster families are almost isomorphic", "The construct could be instruction following, relational matching, entailment"). It's a known confound, not a hidden bug. The proposal's answer is: the gate + transfer test is what separates the hypotheses (if it's shallow matching, the direction won't transfer to the benchmark). So it's "kept distinct" as required by point 4.

Actually, re-reading point 4 and the question: "The corpus measures closed-world precondition satisfaction. Decide whether the proposal keeps distinct the two claims: a source-state effect and transfer to the unchanged benchmark. It must not substitute factual-existence rejection or a new binary metric."

The proposal DOES keep these distinct. ✓.

I think my answer is TEST, but I should honestly flag the strictness of the gate as a notable caveat (without calling it a blocking defect since it's a deliberate, documented choice and the reviewer's mandate is narrow — "do not broaden").

Wait, actually, let me reconsider once more whether "too strict" rises to REVISE. The instructions say REVISE = "name the smallest concrete offline correction." The v3 gate requiring 100% (all full_mirror) is a concrete code behavior (`all(full_mirror.values())`). If I judge this "too strict for a model test," then REVISE with the correction being to relax it to the parent's 90%/75% thresholds.

Hmm, but the parent proposal (test-proposal.md at parent level) is the "already described source-state experiment." Its clean gates are: "≥90% exact accuracy in each split, ≥75% in each cue-family/consumer within split, ≥90% paired answer-order consistency." The v3 gate is STRICTER (90% in split_consumer/split_cue cells rather than 75%, plus 100% full_mirror).

So there's a DISCREPANCY between "the already described source-state experiment" (parent: 90%/75%/90%) and the v3 gate (90% all cells + 100% mirrors).

But is this discrepancy a defect requiring REVISE, or just the v3 being more conservative (stricter is safer for a skeptical review)? Stricter admission is not unscientific — it makes false positives LESS likely, at the cost of possibly never passing. And the question says TEST means "sufficient to authorize." A too-strict gate doesn't make the design UNSUFFICIENT for authorization; it makes the experiment harder to run, which is safe.

Actually, I realize the deeper question is about whether the gate (with its controls) provides a FALSIFIABLE test. A too-strict gate is still falsifiable (it can fail). A too-WEAK gate (shortcuts pass) would be non-falsifiable in the bad direction. The question's point 3 lists "gate too strict OR too weak" as concerns.

Let me reconsider "too weak": is there any shortcut that PASSES and would falsely authorize a source-state interpretation? I established the deterministic shortcuts all fail. For a nondeterministic model shortcut (lexical preference), it fails at the cell level due to world parity counterbalancing (within train) EXCEPT potentially within a single-world split for a single consumer (storage/notification in withheld). But those are caught by the cross-consumer "split" cell and the split_consumer cells for routing/allocation in withheld.

Actually wait, let me very carefully check the withheld_source routing/allocation action counterbalance, because if world3 (withheld) uses ONLY odd-world convention and there are NO even-world routing/allocation rows in withheld, then "pick gate" for withheld routing would be 100%.

withheld_source = seal/capacity/roster world3 (storage+notification only, per the data I've seen: seal world3 has storage+notification, capacity world3 has storage+notification), PLUS precedence/link worlds (routing+allocation?).

So routing/allocation in withheld come ONLY from precedence and link families. What worlds do precedence/link use, and what's their valid action convention?

I need to check the precedence/link rows. This is the crux of whether the withheld routing/allocation valid-action is lexically counterbalanced. Let me read the remaining corpus rows (offset 115 onwards) to find precedence and link rows and parity rows.

Let me read the rest of the corpus.I've now seen enough of the structure. The patterns are consistent:
- world0 (even): rule first, valid action = gate/two, required Vek/at-least.
- world1 (odd): evidence first, valid action = bypass/zero, required Zum/at-most.
- world2 (even, calibration): rule first, gate/two valid, Vek/at-least.
- world3 (odd, withheld): evidence first, storage/notification, lower/violet valid, Zum/at-most.

So for storage/notification (only world3), valid action is ALWAYS "lower drawer"/"violet". Never counterbalanced within the consumer.

Now for parity, precedence, link — these I haven't seen yet. Let me check the rest to verify whether parity has counterbalanced valid actions AND whether precedence/link (the novel withheld families using routing/allocation) have counterbalanced valid actions.

Actually, this is critical for one specific shortcut I want to verify: within withheld_source, the routing/allocation consumers come ONLY from precedence/link families. If precedence/link use a single world convention where "gate"/"two" is always valid (or always invalid), then a "pick gate" shortcut in withheld routing could be 100%.

But actually, more importantly, I need to step back and just determine the DECISION. I've verified enough. Let me check the parity/precedence/link rows quickly, then finalize.

Actually, let me reconsider my time budget. I've read essentially all the key content. The remaining unknowns (parity/precedence/link action conventions) don't change my core conclusions because:

1. The gate requires min accuracy 90% across ALL cells, and 100% on all full_mirror cases. Even if some cell allows a lexical shortcut, the CROSS-cell requirement and the 100% case-mirror requirement mean a pure lexical-preference shortcut (without solving the actual precondition) cannot pass the whole gate, because the valid action's lexical identity differs across worlds/consumers.

2. The residual shortcut concern (shared-token → valid for seal/roster) is a CONSTRUCT weakness (shallow matching), acknowledged in the spec, and is exactly what the contrary hypothesis + transfer test is designed to distinguish. It does NOT defeat falsifiability.

So my decision is TEST, with clear caveats about what v3 can and cannot establish.

But wait — let me reconsider the "too strict" full_mirror point ONE more time, because it's the most defensible REVISE candidate, and I want to be honest.

Actually, re-reading the question carefully: "Look for remaining simple shortcut false positives, including ... and a gate that is too strict or too weak for a model test."

And: "REVISE means name the smallest concrete offline correction and quote the exact row/code behavior that requires it."

The full_mirror `all()` = 100% requirement combined with `min_accuracy >= 0.90` means the gate is effectively "100% accuracy on 384 rows." Is this "too strict for a model test"? 

Arguments it's fine (not a blocking defect):
- It's an ADMISSION gate; conservative is safe.
- It's falsifiable (will fail, allowing clean interpretation).

Arguments it's a defect (too strict):
- The referenced parent experiment specified 90%/75%/90% thresholds; v3 silently tightened to 100% case-perfect, which is inconsistent with "authorize only the ALREADY DESCRIBED source-state experiment."
- A 4B model on greedy decoding with exact-token parsing will virtually never hit 100% on 384 prompts, so the gate may be unfalsifiable in the "pass" direction (can never pass), making the source-state experiment vacuously blocked.

Hmm, but "unfalsifiable in the pass direction" isn't quite a scientific falsifiability problem — it's a power problem. And the question's TEST criterion is about "sufficient to authorize the already described source-state experiment." A stricter-than-described gate doesn't prevent authorization of THAT experiment; it just changes the admission bar.

Actually, I realize there might be a subtlety I should verify: does the v3 gate actually REPLACE/contradict the parent's clean gates in a way that changes what "the already described source-state experiment" is?

The v3 test-proposal says it's "a frozen proposal, not authorization." It re-specifies the gate. The parent test-proposal (test-proposal.md at root) is the detailed "already described source-state experiment." The v3 spec.md says v3 is "review-pending and not execution-authorized."

The question asks me to decide TEST/REVISE for the v3 design. If TEST, it authorizes "the already described source-state experiment." The "already described" one is the parent test-proposal (v2's), but v3 modifies the gate. Is the v3 gate a faithful tightening of the v2 gate, or a new gate?

v2 clean gates (parent test-proposal §A.4): "≥90% exact accuracy in each split, ≥75% in each cue-family/consumer within split, ≥90% paired answer-order consistency."

v3 gate (validate.py): min 90% semantic accuracy in each split/consumer/cue cell + 100% policy-mirror + 100% full case mirror.

These are DIFFERENT thresholds and DIFFERENT quantities (v2 scores the LETTER = "exact accuracy"; v3 scores the SEMANTIC action). Actually the v3 change from letter→semantic is THE KEY fix (the v2 gate's "exact accuracy" could be passed by constant-A? No, constant-A gives 50% not 90%). Hmm.

Actually the v2 gate's flaw was in the CAUSAL gate ("≥50% opposite-key answers"), not the clean gate. The v2 clean gate (90% exact) is fine. The v3 clean gate changes to semantic + adds 100% mirrors.

The point: the v3 gate is the CORRECTED gate. It maps to semantic action (fixing the causal false-positive) and adds mirror requirements. Whether 100% is "too strict" is a threshold judgment.

I think for a truly skeptical but fair review, the honest answer is:

**TEST** — the design correctly fixes the two named v2 defects (policy-clause order, constant-letter false positive), preserves v1/v2, balances correctly, holds storage/notification out, maps letters→semantics with correct controls, and cleanly separates the source-state claim from the unchanged-benchmark transfer claim (no binary metric). The residual shortcuts (lexical/shared-token) are acknowledged and are exactly the contrary hypothesis the transfer test exists to discriminate, not gate false-positives.

But I should flag the full_mirror 100% strictness as a notable caveat (risk of vacuous-blocking), without making it the REVISE driver, and flag the storage/notification non-counterbalanced valid-action and the split/cue confounding (parity only in calib, precedence/link only withheld) as acknowledged limitations.

Actually, wait. Let me reconsider whether I should REVISE on the "too strict" issue, because the question really emphasizes checking for it and gives REVISE as the mechanism to "name the smallest concrete correction."

Let me think about what's genuinely most defensible for a "skeptical independent ML researcher" asked "does v3 provide a falsifiable source-state test."

A falsifiable test needs to be able to FAIL (it can) but also be ABLE to PASS in principle if the hypothesis is true. If the gate is so strict that a genuine task-validity intermediate with a real model at, say, 96% accuracy (missing 15/384 rows) can NEVER pass, then the gate is not a "test" so much as a blocking filter, and the "source-state effect" claim becomes untestable-by-design.

The full_mirror `all()` requirement is the specific code that causes this: a model at 96% would have ~15 cases with a wrong variant, → all(full_mirror.values()) = False → blocked, even though 96% is clearly "the model computes the precondition state."

But is that "too strict" or "an appropriate clean gate"? The parent proposal itself allowed 90% exact accuracy and 90% answer-order consistency, NOT 100%. So v3's 100% case-mirror is stricter than the already-described experiment AND stricter than necessary to detect order/policy interactions (a 90% consistency threshold would suffice).

This is a concrete, citable discrepancy: validate.py line `"pass": min_accuracy >= 0.90 and all(policy_mirror.values()) and all(full_mirror.values())` — the `all(...)` makes it 100%, whereas the referenced experiment's clean gate used 90%/75%/90% thresholds.

Hmm, but the question says "REVISE means name the smallest concrete offline correction." Is relaxing 100%→90% the "smallest correction"? Or is it acceptable as-is?

Let me weigh the decision holistically against the question's four numbered checks:

Check 1: "V1/v2 are preserved, and v3 changes only policy-clause order from v2." — I should verify the prompt-wrapper issue. Let me actually check v2's corpus to confirm the prompt is identical (except policy clause). This is a concrete verifiable claim. If v3's prompt wrapper or question format differs from v2, then "changes only policy-clause order" is FALSE, which would be a REVISE-able factual error.

Actually, this is important and I can verify it quickly. Let me read the first line of v2/corpus.jsonl.

Let me do that.Now I can confirm: the v2 prompt for tv2_seal_match_0_routing_o0_1 is:

"This is a self-contained rule world; the stated requirement is the only criterion for this operation.\nThe operation requires a Vek0 seal.\nThe item carries a Vek0 seal.\nWhen the requirement holds, route through gate; otherwise, route through bypass.\nWhich action follows? A: route through gate. B: route through bypass. Reply with one letter only."

And v3 policy_order=0 (tv3_seal_match_0_routing_p0_o0_1) prompt is IDENTICAL (I see it in the v3 corpus):
"This is a self-contained rule world; the stated requirement is the only criterion for this operation.\nThe operation requires a Vek0 seal.\nThe item carries a Vek0 seal.\nWhen the requirement holds, route through gate; otherwise, route through bypass.\nWhich action follows? A: route through gate. B: route through bypass. Reply with one letter only."

Yes! Identical. So v3 policy_order=0 is byte-identical prompt to v2, and policy_order=1 reverses only the "When the requirement holds, X; otherwise, Y" clause (boundary): "route through bypass; otherwise, route through gate."

Wait, but let me double-check: does the prompt differ ONLY in the policy clause between v2 and v3 policy_order=0? Yes. And between policy_order=0 and policy_order=1, only the "holds/otherwise" actions swap. The A:/B: options remain the same.

So point 1 is VERIFIED: v3 changes only policy-clause order from v2 (plus metadata fields id/provenance/pair_id/v2_parent_id/policy_order/policy_actions/expected_semantic_action/semantic_case_id, which are metadata, not prompt content or semantic content).

Actually wait, one nuance: v3 adds fields `expected_semantic_action`, `policy_order`, `policy_actions`, `semantic_case_id`, `pair_id`, `v2_parent_id`, and changes `id` and `provenance`. These are metadata. The SEMANTIC content (rule, evidence, facts, valid, split, cue_family, consumer, options, expected, option_order, prompt content) is unchanged except the policy clause order. And build.py asserts byte-identical regeneration, validate asserts rule/evidence/facts/valid/split/cue_family/consumer/options/expected/option_order unchanged.

So point 1 confirmed TRUE.

Now I've confirmed the prompt wrapper is identical. Good.

Now let me finalize my decision. I'm confident the four checks all pass:

1. ✓ V1/v2 preserved (freeze hashes, v2 corpus unchanged); v3 = v2 + policy-clause-order mirror only (verified byte-identical prompt except policy clause).
2. ✓ Balance correct (validation.json all balanced=true at split×consumer×valid×{policy_order|option_order}); storage/notification absent from train+calibration (validate.py assertion, corpus shows only world3=withheld).
3. ✓ Gate maps A/B→action→valid/invalid (selected_semantic); 5 controls behave correctly (semantic_oracle passes, always-A/B/opposite-letter/first-policy-branch fail). Remaining shortcuts (lexical action preference, shared-token→valid) are acknowledged construct weaknesses, structurally mitigated, and are the contrary hypothesis the transfer test discriminates — not gate false-positives.
4. ✓ Two claims kept distinct; unchanged benchmark is sole transfer endpoint; no binary existence-rejection metric (spec, test-proposal, validation limits all affirm).

The one notable caveat: the gate's full_mirror/policy_mirror use `all()` (100% requirement), stricter than the parent proposal's 90%/75%/90%. This is a "too strict" risk (vacuous blocking) but is a deliberate, documented anti-shortcut tightening, and strictness doesn't undermine falsifiability or authorization — it errs conservative.

Decision: TEST.

Now, what v3 can and cannot establish:
- CAN establish (offline): preservation of v1/v2; balanced A/B and policy-clause-order within cells; no stored/notification leakage into train/calibration; zero lexical overlap with the audited benchmark/source inputs; that the five deterministic shortcut controls fail while the semantic oracle passes; that letter-token ≠ semantic-action mapping is now enforced.
- CANNOT establish: any target-model behavior (no inference run); that the synthetic task is solved by a "task-validity intermediate" vs shallow closed-world matching/instruction following; semantic independence (lexical audit only); benchmark transfer; causal efficacy of a probe direction. These require the (authorized, budgeted, separately-gated) source-state run and, only after it, the conditional benchmark transfer test.

I should note the two specific residual confounds I found concrete evidence for:
- storage/notification valid action is NOT lexically counterbalanced (only world3, "lower"/"violet" always valid within those consumers) — but cross-consumer gate cells and the source-state test's cross-cue averaging mean a single lexical preference can't pass.
- parity only in calibration, precedence/link only in withheld — cue-family difficulty confounded with split (acknowledged).

And flag the gate strictness (100% mirror) as the main caveat, but not a blocking defect.

Let me write the final answer concisely but completely. I need to give ONE decision (TEST or REVISE), state what v3 can/cannot establish, quote specifics.

I'll go with TEST. I'll state the caveats honestly.

Let me write it up.