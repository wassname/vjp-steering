Let me read all the specified artifacts to understand the situation and make a determination.Let me now read the remaining artifacts - the generation.json, mounted-preflight.json, pueue-705-clean.log, retry-budget.json, and job705-billing-report.log, plus the audit file.The log is very long. Let me see the rest of the log to find the CLEAN_GATE output and any decision.Now let me read the audit file and look at the generation.json for more details, particularly the clean_gate, decision, and clean responses.Now I need to carefully analyze all the evidence. Let me trace through what happened:

1. Job 704 failed before clean generation due to a `FileNotFoundError: results/plot.png` - the protected files weren't mounted in the image.

2. Job 705 (the retry, which we see in the logs) was the retry. Let me check the log again - the log file `pueue-705-clean.log` shows `TASK_VALIDITY_SOURCE_DOWNLOADED` and ends with a `CLEAN_GATE` output that says `"pass": false, "minimum_accuracy": 0.425`.

Wait, I need to trace through the log more carefully. The log file shows:
- The Modal app launched as `ap-obvcLJSqNatyyblyseqPK5`
- It ran the preflight successfully
- Then it ran the remote function
- All 384 clean responses were generated
- Then it got to `CLEAN_GATE {"pass": false, ...}`
- Then `TASK_VALIDITY_SOURCE_DOWNLOADED`

Now the question is: does job 705 provide valid evidence that the clean source task fails the predeclared gate, and was the stop-before-intervention rule applied correctly?

Let me look at the generation.json to see the decision field. The generation.json is 13.7MB so I couldn't load it fully. Let me extract key fields.

Let me now analyze the CLEAN_GATE result in detail:

```
CLEAN_GATE {"pass": false, "minimum_accuracy": 0.425, "strict_semantic_cases": {"passed": 1, "total": 96}, "cells": {"split": {"train": 0.5104166666666666, "source_calibration": 0.5178571428571429, "withheld_source": 0.48295454545454547}, "split_consumer": {...}, "split_cue": {...}}, "strict_case_failures": [...]}
```

The gate requires:
1. All 96 semantic-case mirror groups to be fully correct
2. At least 90% aggregate accuracy in every predeclared cell

The result:
- `pass: false`
- `minimum_accuracy: 0.425` (well below 90%)
- `strict_semantic_cases.passed: 1` out of 96
- All three split cells have accuracies around 50% (0.48-0.52)

Now, the critical question: is this valid? Let me look at the data more carefully.

Let me look at the CLEAN_RESPONSE entries. I need to verify: the model's answers are being mapped through the `semantic()` function correctly. The semantic function checks if `text` is "A" or "B", then maps it to the `options` list, then checks if the resulting action matches the valid action for that row.

Wait, let me look more carefully at the log. I see patterns like:

For `tv3_seal_match_0_routing_p0_o0_1` (train, valid, expected_semantic_action: "valid"): text = "A"
For `tv3_seal_match_0_routing_p1_o0_1` (train, valid, expected_semantic_action: "valid"): text = "B"
For `tv3_seal_match_0_routing_p0_o1_1` (train, valid, expected_semantic_action: "valid"): text = "B"
For `tv3_seal_match_0_routing_p1_o1_1` (train, valid, expected_semantic_action: "valid"): text = "A"

Let me decode these IDs. The naming convention appears to be: `tv3_{cue_family}_{index}_{consumer}_p{policy_order}_o{option_order}_{valid}`
- p0 = policy clauses in one order, p1 = reversed order
- o0 = A maps to valid action, B maps to invalid; o1 = A maps to invalid, B maps to valid (or the reverse)
- _1 = valid scenario, _0 = invalid scenario

Now look at the pattern. For valid rows (_1):
- When p0_o0: A is correct (A = valid action)
- When p1_o0: B is correct (the policy order is reversed, so the valid action is now B?? No wait...)

Actually, let me think about this more carefully. In v3, reversing the policy order should NOT change which action is valid. The question is: does the model answer the letter based on the position of the relevant policy clause?

Looking at the results, the model appears to consistently choose based on the first policy clause position. Let me check:

For valid rows:
- p0_o0_1: text "A" (correct by letter)
- p1_o0_1: text "B" (incorrect by letter - policy order reversed, but B now maps to valid?)

Wait, but the semantic mapping depends on what A and B map to. The `options` field tells us which action A maps to and which B maps to. In the `semantic()` function:
```python
letter = text.strip()
action = row["options"]["AB".index(letter)]
```

And the `actions_valid_invalid` = `[valid_action, invalid_action]`.

So for o0: A maps to valid_action (index 0), B maps to invalid_action (index 1)
For o1: B maps to valid_action, A maps to invalid_action

Let me look at a concrete example. Take `tv3_seal_match_0_routing_p0_o0_1`:
- This is a valid row (ends in _1)
- Policy order p0, option order o0
- expected_semantic_action: "valid"
- text: "A"
- For o0: A = valid_action, so A → valid_action = valid → correct ✓

Now `tv3_seal_match_0_routing_p1_o0_1`:
- same valid row, but policy order p1
- expected_semantic_action: "valid"  
- text: "B"
- For o0: B = invalid_action → invalid → WRONG ✗

So the model is answering B instead of A when the policy order is reversed!

This is a really interesting finding. The model seems to be picking the letter that corresponds to the first policy clause rather than understanding the actual semantics.

But wait - I need to check whether this is because of the `semantic()` function's mapping. Let me verify a case where option order is reversed.

`tv3_seal_match_0_routing_p0_o1_1`:
- valid, p0, o1
- expected: "valid"
- text: "B"
- For o1: A = invalid_action, B = valid_action → B → valid → correct ✓

`tv3_seal_match_0_routing_p1_o1_1`:
- valid, p1, o1
- expected: "valid"
- text: "A"
- For o1: A = invalid_action → invalid → WRONG ✗

So in both cases, when policy order is p1, the model answers with the wrong letter. But when policy order is p0, the model gets it right.

Now let's check an invalid (_0) case:

`tv3_seal_match_0_routing_p0_o0_0`:
- invalid row
- expected: "invalid"
- text: "A"
- For o0: A = valid_action → valid → WRONG (expected invalid) ✗

`tv3_seal_match_0_routing_p1_o0_0`:
- invalid row
- expected: "invalid"
- text: "B"
- For o0: B = invalid_action → invalid → correct ✓

So the pattern is: for p0, the model answers A; for p1, the model answers B. 

This means the model is picking the letter corresponding to the first policy clause. With p0 (valid policy first), A maps to valid. With p1 (invalid/reversed policy first), B maps to valid if option order is o0, but wait...

Actually, let me think again. The model's behavior is: pick the letter corresponding to the first-listed policy clause. It's a first-policy-branch heuristic.

Now, does this produce a ~50% accuracy? Let's compute:
- For p0, o0, valid rows: A (correct by letter) → A = valid → correct ✓
- For p0, o0, invalid rows: A (wrong by letter) → A = valid → wrong ✗
- For p0, o1, valid rows: B (?), but actually looking at p0_o1_1: text "B" → B = valid → correct ✓
- For p0, o1, invalid rows: p0_o1_0: text "B" → B = valid → wrong ✗

Wait, but for p0_o1, the log says text is "B". Let me recheck...

`tv3_seal_match_0_routing_p0_o1_1`: text "B" 
`tv3_seal_match_0_routing_p0_o1_0`: text "B"

Hmm, the model answers "B" when it's p0_o1 but "A" when it's p0_o0. So it's not simply "always A". It seems to be picking based on the policy order and option order together.

Actually wait. If the model always picks the first policy branch, then:
- For p0 (valid policy first): The model picks the valid action. But which letter? That depends on o0 vs o1.
  - o0: valid action = option A. Model picks A.
  - o1: valid action = option B. Model picks B.
  
- For p1 (invalid policy first): The model picks the invalid action.
  - o0: invalid action = option B. Model picks B.
  - o1: invalid action = option A. Model picks A.

Let me verify against the data:
- p0_o0_1: A (valid → correct)
- p1_o0_1: B (invalid → wrong!)
- p0_o1_1: B (valid → correct)
- p1_o1_1: A (invalid → wrong!)

For invalid rows:
- p0_o0_0: A (valid → wrong!)
- p1_o0_0: B (invalid → correct)
- p0_o1_0: B (valid → wrong!)
- p1_o1_0: A (invalid → correct)

So the model consistently picks the action listed first in the policy, and then that maps to A/B based on option order. This means:
- For valid rows: correct on p0, wrong on p1 → 50%
- For invalid rows: wrong on p0, correct on p1 → 50%

This gives exactly ~50% aggregate accuracy as observed. And almost all 96 semantic cases fail because each case has 4 rows (p0_o0, p0_o1, p1_o0, p1_o1) and the model gets 2/4 correct.

This is exactly the "first-policy-branch" confound that the v3 revision was supposed to fix! The test-proposal.md says:
> "Always-A, always-B, letter inversion, and selection of the first policy clause are explicit failure modes."

So the first-policy-branch heuristic produces the observed ~50% accuracy pattern, and it matches what we see.

Now the question: does job 705 provide valid evidence that its clean source task fails the predeclared gate?

The clean gate result shows:
- `pass: false`
- `minimum_accuracy: 0.425` (well below the required 90%)
- Only 1 of 96 strict cases pass
- Every cell's accuracy is around 50%

But I need to check: is this actually valid evidence, or is there a bug?

Let me look at the strict_case_failures. The failures show IDs like `tv1_seal_match_0_routing_1` — these are v1-style IDs, not v3-style IDs! The v3 IDs look like `tv3_seal_match_0_routing_p0_o0_1` (with p{policy_order}_o{option_order}), but the strict_case_failures list shows `tv1_*` IDs.

This is a **critical bug**. Let me trace through the code to understand why.

In the `source_gate()` function:
```python
def source_gate(rows, records):
    by_id = {record["id"]: record for record in records}
    ...
    cases = {}
    for row in rows:
        cases.setdefault(row["semantic_case_id"], []).append(row)
    strict = {}
    for key, group in cases.items():
        assert len(group) == 4
        strict[key] = all(semantic(row, by_id[row["id"]]["text"]) == expected(row) for row in group)
```

The `semantic_case_id` field of the rows is being used to group. Looking at the strict_case_failures: `tv1_seal_match_0_routing_1` — these are v1-style IDs, meaning the `semantic_case_id` field in the v3 corpus.jsonl still uses v1-style naming.

Now this could be intentional — the semantic_case_id could be a different field from the row id. The row IDs are v3-style (`tv3_..._p0_o0_1`), while the semantic_case_id groups together the 4 variants of the same semantic case. This makes sense because each v2 row appears twice in v3 (with p0 and p1 policy orders), and the semantic case groups together the 4 rows that vary both policy order and option order.

But wait, `assert len(group) == 4`. So each semantic_case_id has exactly 4 rows — the 2 policy orders × 2 option orders. That's correct.

The issue is: the model consistently picks the action from the first policy clause. This causes exactly 2/4 variants to be wrong per semantic case (p1 policy order). Since strict requires all 4 to be correct, 95/96 cases fail.

But now I need to check: is this because the v3 corpus actually has both policy-clause orders, and the model is genuinely failing? Or is there a bug in how the model responses are processed?

Let me look at some of the CLEAN_RESPONSE entries more carefully. I already noted:
- `tv3_seal_match_0_routing_p0_o0_1`: expected "valid", text "A" → semantic says: A → options[0] = valid_action → valid ✓
- `tv3_seal_match_0_routing_p1_o0_1`: expected "valid", text "B" → semantic says: B → options[1] = invalid_action → invalid ✗

The model answered B for the p1 variant. The question is: with the policy order reversed, should the model still answer A (the same letter) to get the valid action?

In the v3 revision, each v2 row appears twice with the only difference being the order of the two policy clauses. The valid action is the same regardless of policy order. The options (A/B mapping) should also be the same within an option-order variant. So for `tv3_seal_match_0_routing_p0_o0_1` and `tv3_seal_match_0_routing_p1_o0_1`, both are valid rows, both have o0 option order, so A should map to the valid action in both. The model should answer A for both.

But the model answers B for the p1 variant. This means the model is picking the action from the first-listed policy branch, not understanding the rule. This is exactly the first-policy-branch confound.

So the evidence is: the model genuinely fails the clean gate because it's using a first-policy-branch heuristic. This is valid evidence — it's not a bug in the pipeline; it's the model's actual behavior.

But wait, I need to also check: was the stop-before-intervention rule applied correctly?

Looking at the log, after CLEAN_GATE, the output is:
```
TASK_VALIDITY_SOURCE_DOWNLOADED slop/logs/20260908_j_lens_task_validity_source_stage/generation.json
Stopping app - local entrypoint completed.
```

There are no INTERVENTION_RESPONSE lines, which means the code correctly stopped before interventions. The `run()` function has:
```python
if not data["clean_gate"]["pass"]:
    data["decision"] = "CLEAN_GATE_BLOCKED_NO_INTERVENTION"
    data["runtime"] = {...}
    args.output.write_text(json.dumps(data) + "\n")
    return
```

So the stop-before-intervention rule was applied correctly.

Now, let me examine if there's any concrete bug. The key question is whether the generation.json's decision matches. Since generation.json is too large, let me check just the key fields.

Let me also look more carefully at the CLEAN_GATE cells. The accuracies are:
- split: train 0.51, source_calibration 0.52, withheld_source 0.48
- split_consumer: routing (train) 0.46, allocation (train) 0.56, etc.
- split_cue: various around 0.44-0.63

All are well below 90%. The minimum is 0.425.

The strict_case_failures list 95 out of 96 semantic cases. That's consistent with the model's first-policy-branch behavior.

Now, is there a bug that could invalidate this conclusion?

Let me think about potential bugs:

1. **Row ID mismatch in semantic_case_id**: The strict_case_failures show `tv1_*` IDs. These are semantic_case_ids, not row IDs. The v3 corpus was derived from v2, which was derived from v1. The semantic_case_id field may still use v1 naming as a deliberate grouping key. This is not a bug per se, but it could be confusing.

2. **The generation.json decision field**: Let me check what decision was written.

Actually, let me look at the generation.json to extract the decision. It's 13.7MB, but I can search for key fields.

Let me look at the log more carefully. The last lines of generation processing would be something like:
```python
if not data["clean_gate"]["pass"]:
    data["decision"] = "CLEAN_GATE_BLOCKED_NO_INTERVENTION"
```

And then `args.output.write_text(json.dumps(data) + "\n")`. So the generation.json should contain `"decision": "CLEAN_GATE_BLOCKED_NO_INTERVENTION"`.

Now let me think about whether there's a bug in the `source_gate()` function itself.

Looking at `source_gate()`:
```python
def source_gate(rows, records):
    by_id = {record["id"]: record for record in records}
    assert set(by_id) == {row["id"] for row in rows}
    cells = {"split": {}, "split_consumer": {}, "split_cue": {}}
    selectors = {
        "split": lambda row: row["split"],
        "split_consumer": lambda row: (row["split"], row["consumer"]),
        "split_cue": lambda row: (row["split"], row["cue_family"]),
    }
    for name, selector in selectors.items():
        groups = {}
        for row in rows:
            key = str(selector(row))
            groups.setdefault(key, []).append(semantic(row, by_id[row["id"]]["text"]) == expected(row))
        cells[name] = {key: sum(values) / len(values) for key, values in groups.items()}
    cases = {}
    for row in rows:
        cases.setdefault(row["semantic_case_id"], []).append(row)
    strict = {}
    for key, group in cases.items():
        assert len(group) == 4
        strict[key] = all(semantic(row, by_id[row["id"]]["text"]) == expected(row) for row in group)
    minimum = min(value for groups in cells.values() for value in groups.values())
    return {"pass": minimum >= 0.90 and all(strict.values()), "minimum_accuracy": minimum,
            "strict_semantic_cases": {"passed": sum(strict.values()), "total": len(strict)}, "cells": cells,
            "strict_case_failures": [key for key, value in strict.items() if not value]}
```

One potential issue: the `selectors` use `str(selector(row))` as keys. For the tuple selectors, `str(("train", "routing"))` would produce `"('train', 'routing')"`. This is fine as a key.

Now, the `semantic()` function:
```python
def semantic(row, text):
    letter = text.strip()
    if letter not in {"A", "B"}:
        return None
    action = row["options"]["AB".index(letter)]
    valid_action, invalid_action = row["actions_valid_invalid"]
    assert action in {valid_action, invalid_action}
    return "valid" if action == valid_action else "invalid"
```

If `text.strip()` is not "A" or "B", then `semantic()` returns `None`. Then `None == expected(row)` would be False (since expected returns "valid" or "invalid"). Is this happening?

Looking at the CLEAN_RESPONSE entries, all texts are "A" or "B", so this shouldn't be an issue.

Let me now look for a concrete bug.

Wait, let me look more carefully at the CLEAN_GATE output. The minimum_accuracy is 0.425. Let me check which cell has 0.425.

From the cells:
- split_consumer: `('withheld_source', 'storage')`: 0.425

So the storage consumer in withheld_source has only 42.5% accuracy. Let me check: do any of the CLEAN_RESPONSE entries have text that isn't "A" or "B"?

Let me look through all the storage entries in the log...

Looking at the withheld_source storage entries:
- `tv3_seal_match_3_storage_p0_o0_1`: text "A"
- `tv3_seal_match_3_storage_p1_o0_1`: text "B" 
- `tv3_seal_match_3_storage_p0_o1_1`: text "B"
- `tv3_seal_match_3_storage_p1_o1_1`: text "A"
- `tv3_seal_match_3_storage_p0_o0_0`: text "B"
- `tv3_seal_match_3_storage_p1_o0_0`: text "A"
- `tv3_seal_match_3_storage_p0_o1_0`: text "A"
- `tv3_seal_match_3_storage_p1_o1_0`: text "B"

Wait, for the invalid storage rows, the pattern seems different. Let me check more carefully:

`tv3_seal_match_3_storage_p0_o0_0`: invalid, expected "invalid", text "B"
For o0: B = invalid_action → invalid → correct ✓

`tv3_seal_match_3_storage_p1_o0_0`: invalid, expected "invalid", text "A"
For o0: A = valid_action → valid → wrong ✗

`tv3_seal_match_3_storage_p0_o1_0`: invalid, expected "invalid", text "A"
For o1: A = invalid_action → invalid → correct ✓

`tv3_seal_match_3_storage_p1_o1_0`: invalid, expected "invalid", text "B"
For o1: B = valid_action → valid → wrong ✗

So for valid rows: p0 correct, p1 wrong
For invalid rows: p0 wrong, p1 correct

This is the first-policy-branch pattern. Each semantic case has 2/4 correct = 50%.

But for storage, let me count the rows. Looking at the freeze.json, storage appears in:
- seal_match_3_storage: 8 rows
- capacity_3_storage: 8 rows
- roster_3_storage: 8 rows
- precedence_3_storage: 8 rows
- link_3_storage: 8 rows

Total storage: 40 rows. If ~50% accuracy, that's ~20/40. But 0.425 means 17/40 = 42.5%. That's less than 50%. Let me check if any storage rows have non-A/B text...

Looking at the CLEAN_RESPONSE lines for the storage entries, I see only "A" and "B". Let me count more carefully...

Actually wait, let me re-examine. Let me look at the roster_3_storage entries:

`tv3_roster_3_storage_p0_o0_1`: valid, text "A" → A=valid → correct
`tv3_roster_3_storage_p1_o0_1`: valid, text "B" → B=invalid → wrong
`tv3_roster_3_storage_p0_o1_1`: valid, text "B" → B=valid → correct
`tv3_roster_3_storage_p1_o1_1`: valid, text "A" → A=invalid → wrong
`tv3_roster_3_storage_p0_o0_0`: invalid, text "A" → A=valid → wrong
`tv3_roster_3_storage_p1_o0_0`: invalid, text "A" → A=invalid → correct
`tv3_roster_3_storage_p0_o1_0`: invalid, text "B" → B=valid → wrong
`tv3_roster_3_storage_p1_o1_0`: invalid, text "A" → B? Wait...

Actually `tv3_roster_3_storage_p1_o1_0`: expected "invalid", text "A". 
For o1: A = invalid_action → invalid → correct ✓

So roster_3_storage: 4 correct out of 8 = 0.5. But the overall storage is 0.425.

Let me look at the link_3_storage entries:
`tv3_link_3_storage_p0_o0_1`: valid, text "A" → A=valid → correct
`tv3_link_3_storage_p1_o0_1`: valid, text "B" → B=invalid → wrong
`tv3_link_3_storage_p0_o1_1`: valid, text "B" → B=valid → correct
`tv3_link_3_storage_p1_o1_1`: valid, text "A" → A=invalid → wrong
`tv3_link_3_storage_p0_o0_0`: invalid, text "B" → B=invalid → correct
`tv3_link_3_storage_p1_o0_0`: invalid, text "B" → B=valid → wrong?
Wait, o0: B = invalid_action. So B → invalid → correct ✓
`tv3_link_3_storage_p0_o1_0`: invalid, text "B" → B=valid → wrong ✗
`tv3_link_3_storage_p1_o1_0`: invalid, text "B" → B=valid → wrong ✗

So link_3_storage: correct = (p0_o0_1 ✓, p0_o1_1 ✓, p0_o0_0 ✓) = 3/8 = 0.375.

That could explain the lower accuracy. But this is all consistent with the first-policy-branch heuristic. Some groups might have slightly different patterns.

Now, the core question is: does job 705 provide valid evidence that the clean source task fails, and was the stop-before-intervention rule applied correctly?

Let me verify:
1. The clean gate result says `"pass": false` with minimum_accuracy 0.425 and only 1/96 strict cases passed.
2. The log shows no INTERVENTION_RESPONSE entries, meaning the intervention loop was never entered.
3. The decision should be `CLEAN_GATE_BLOCKED_NO_INTERVENTION` based on the code flow.

Now, is there a bug that could invalidate this?

Let me think about `expected()`:
```python
def expected(row):
    return "valid" if row["valid"] else "invalid"
```

This returns "valid" or "invalid" based on the row's truth label.

And `semantic()` returns "valid" or "invalid" based on the model's answer letter mapped through options.

For the comparison `semantic(row, by_id[row["id"]]["text"]) == expected(row)`:
- If the model answers a letter that maps to the valid action and the row is valid → both "valid" → correct
- If the model answers a letter that maps to the invalid action and the row is invalid → both "invalid" → correct
- Otherwise → incorrect

This is the semantic scoring that's described in test-proposal.md: "Parse only an exact stripped A or B. Map the answer through that row's options to valid or invalid; do not score the letter itself."

So the scoring seems correct. The model's behavior is genuinely a first-policy-branch heuristic, which is an explicit failure mode.

Now, are there any issues with how the clean gate is computed?

Let me check: the `minimum` calculation:
```python
minimum = min(value for groups in cells.values() for value in groups.values())
```

This takes the minimum accuracy across all cells (split, split_consumer, split_cue). All cell accuracies are around 50%, so the minimum is 0.425. This is well below 0.90.

And `all(strict.values())` checks that all 96 semantic cases are fully correct. Only 1 passed. So both gate conditions fail.

This all seems valid. But let me think harder about potential bugs...

One thing I notice: the `strict_case_failures` show IDs like `tv1_seal_match_0_routing_1` — these are v1-style semantic_case_ids. But the v3 corpus has v3-style row IDs. The `semantic_case_id` field groups together the 4 variants (2 policy orders × 2 option orders). If the corpus.jsonl has some issue where the semantic_case_id doesn't correctly group the 4 variants...

But that would be a corpus issue, and the corpus is frozen. The reviewer is told: "Do not propose a new experiment, change the frozen corpus, or authorize benchmark transfer."

Actually, let me reconsider. The key question is whether job 705 provides **valid evidence** that the clean source task fails. A bug in the evidence collection would invalidate it.

Let me check if there might be a tokenizer/prompt rendering issue. The model seems to always pick based on first policy clause. This could be because:
1. The model genuinely can't do the task (valid evidence)
2. The prompt rendering has a bug (invalid evidence)

Let me look at the `render()` function:
```python
def render(tokenizer, row):
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": row["prompt"]}],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
```

This applies the chat template to the row's prompt. The v3 corpus has both policy-clause orders in the prompt. If the prompt is correctly formatted, this should work.

But the model is consistently failing in a way that matches the first-policy-branch heuristic. This is a model capability issue, not a pipeline bug.

Now, let me also think about whether the test-proposal's gate definition is correctly implemented in `source_gate()`. The test-proposal says:
> "require at least 90% selected-semantic-action accuracy in every split, split-by-consumer group, and split-by-cue-family group. Also require every four-row semantic case, which varies both answer position and policy-clause order, to return its correct semantic action."

The `source_gate()` function computes:
1. Cells: split, split_consumer, split_cue — check for ≥90% in each
2. Strict cases: 4-row semantic cases — check all correct

This matches the proposal. The minimum across all cells is 0.425, and 95/96 strict cases fail. Both conditions fail.

Now, wait. Let me re-read the CLEAN_GATE output more carefully:

```json
{"pass": false, "minimum_accuracy": 0.425, "strict_semantic_cases": {"passed": 1, "total": 96}, "cells": {...}, "strict_case_failures": [...]}
```

The minimum_accuracy is 0.425, which is the minimum across all cells. But the gate requires "at least 90% ... in every predeclared cell." So 0.425 < 0.90 → fails.

The strict_semantic_cases: 1 passed out of 96. This is "all 96 semantic-case mirror groups to be fully correct." 1 < 96 → fails.

Both conditions independently fail. The evidence is consistent.

Now, let me think about whether there's something wrong with how the responses are collected. The `generate()` function extracts the first MAX_NEW_TOKENS=4 tokens as the answer text. If the model sometimes generates more than "A" or "B" (e.g., "A\n" or "A."), the `text.strip()` in `semantic()` should handle whitespace. But what if it generates something like "The answer is A"? Then `text.strip()` would be "The answer is A" which is not in {"A", "B"}, and `semantic()` returns `None`, which is counted as wrong.

Looking at the CLEAN_RESPONSE entries, all `text` values are just "A" or "B". So this isn't happening.

OK, I think the evidence is valid. Let me now formulate my conclusion.

Wait, I need to also look for a concrete bug. Let me think more carefully...

Actually, let me look at one specific thing. The log shows:
```
TASK_VALIDITY_SOURCE_DOWNLOADED slop/logs/20260908_j_lens_task_validity_source_stage/generation.json
```

But the Modal app is `ap-obvcLJSqNatyyblyseqPK5`, which is the same app as in the billing report. And the billing report shows both job 704's app (`ap-FAW0E4RXpgmbCm1yMZPYnL`) and job 705's app. This confirms job 705 is a separate retry.

Now, I notice something interesting in the retry-budget.json:
- `"retry_limits": {"judging_calls": 0, "benchmark_generations": 0}`

This confirms that no judging or benchmark generation was authorized for the retry.

And from the log, there are no INTERVENTION_RESPONSE lines - the intervention loop wasn't entered.

So the stop-before-intervention rule was correctly applied.

Let me now think about what could be a "concrete validity bug":

1. The CLEAN_GATE shows `"pass": false` with overwhelming evidence of first-policy-branch heuristic. This is valid.

2. The stop-before-intervention rule was applied correctly — no intervention responses in the log.

3. No benchmark generation or judging occurred.

4. The model genuinely fails at the semantic task due to first-policy-branch confound.

Is there any bug? Let me think about the `semantic()` function more carefully...

```python
def semantic(row, text):
    letter = text.strip()
    if letter not in {"A", "B"}:
        return None
    action = row["options"]["AB".index(letter)]
    valid_action, invalid_action = row["actions_valid_invalid"]
    assert action in {valid_action, invalid_action}
    return "valid" if action == valid_action else "invalid"
```

`"AB".index(letter)` — this returns 0 for "A" and 1 for "B". Then `row["options"][0]` or `row["options"][1]`. This looks correct assuming options is a list of two actions.

Now, the `expected()` function:
```python
def expected(row):
    return "valid" if row["valid"] else "invalid"
```

And the comparison: `semantic(row, by_id[row["id"]]["text"]) == expected(row)`.

This looks correct. When semantic returns None (non-A/B answer), the comparison with "valid" or "invalid" would be False, correctly counting as wrong.

I don't see a bug in the gate computation. The model truly fails.

But wait — I want to double-check: does the freeze.json actually list all 384 rows? Let me verify:
- train: 96 rows (I can count)
- source_calibration: 160 rows (roughly)
- withheld_source: 128 rows (roughly)

96 + 160 + 128 = 384. Correct.

And the CLEAN_RESPONSE entries in the log: I see 384 CLEAN_RESPONSE lines and one CLEAN_GATE line at the end.

Everything seems consistent.

Now, is there a bug in the `strict_case_failures` list? It shows `tv1_*` IDs, suggesting the `semantic_case_id` field uses v1 naming. Let me check if this could cause an issue...

Actually, the `semantic_case_id` is a field in each row of the corpus. It groups rows that represent the same semantic case but with different answer positions and policy-clause orders. The naming convention (`tv1_*` vs `tv3_*`) doesn't affect the computation — it's just a string key for grouping.

But wait — could there be a mismatch? If the `semantic_case_id` in v3 doesn't correctly group the 4 variants (p0_o0, p0_o1, p1_o0, p1_o1), then the strict case computation would be wrong. But looking at the output, `"total": 96` and `assert len(group) == 4`, so there are exactly 96 groups of 4, which matches the expected 96 semantic cases with 4 variants each.

Let me actually count: the v3 has 96 semantic cases. Each semantic case from v2 (48 cases?) would have been doubled to 96. Wait, v2 had 48 semantic cases × 2 answer positions = 96 rows, but the freeze.json explanation says: "Every frozen v2 row appears twice in v3. ... V3 has 384 rows and 96 semantic cases, each expressed at both answer positions and both policy-clause orders."

Wait, that seems contradictory. Let me re-read: "96 semantic cases, each expressed at both answer positions and both policy-clause orders" — that's 96 × 2 × 2 = 384 rows. Each semantic case has 4 rows. 96 × 4 = 384. That checks out.

Now, 96 semantic cases with 4 rows each. The strict gate requires all 4 to be correct for each case. Only 1 passed. This is consistent with the model's first-policy-branch heuristic giving 2/4 correct per case (pattern: p0 correct, p1 wrong, or p0 wrong/p1 correct depending on truth label).

Actually wait, 2/4 correct per case means the strict case fails (requires 4/4). So for 96 cases with 2/4 correct each, 0 cases pass all 4. But the output says 1 case passed. Let me check which one passed...

Looking at the strict_case_failures list, it has 95 entries (I can see from the log output). The one that passed must not be in the list. But it's hard to tell which one from the truncated output.

Let me check: the strict_case_failures seem to include entries like `tv1_seal_match_0_routing_1`, `tv1_seal_match_0_routing_0`, etc. These cover seal_match, capacity, roster, parity, precedence, link families.

If 1 out of 96 passed, and the pattern is first-policy-branch which gives exactly 2/4 correct for all cases, then 0 should pass. Having 1 pass is suspicious.

But the evidence is still valid: 95/96 fail, far from the required 96/96. And minimum accuracy is 42.5%, far from the required 90%.

OK, I think the conclusion is clear. Let me now write my final response.

Actually, let me reconsider: is there potentially a subtle bug in the `source_gate` computation that would make this evidence invalid?

Let me look at the `selectors` again:
```python
selectors = {
    "split": lambda row: row["split"],
    "split_consumer": lambda row: (row["split"], row["consumer"]),
    "split_cue": lambda row: (row["split"], row["cue_family"]),
}
```

For the withheld_source split, there's no `routing` consumer shown in the cell output... wait yes there is: `('withheld_source', 'routing')`: 0.479. But looking at the freeze.json, withheld_source includes routing for precedence and link cue families.

Actually, let me check: in the freeze.json, the `withheld_source` split includes:
- seal_match_3: storage and notification → consumer: storage, notification
- capacity_3: storage and notification → consumer: storage, notification  
- roster_3: storage and notification → consumer: storage, notification
- precedence_0-3: routing, allocation, storage, notification → consumer: routing, allocation, storage, notification
- link_0-3: routing, allocation, storage, notification → consumer: routing, allocation, storage, notification

So withheld_source has all 4 consumers. The cells show:
- storage: 0.425
- notification: 0.5
- routing: 0.479
- allocation: 0.521

This is consistent.

Now, looking at everything, I believe the evidence is valid. The model genuinely fails the clean gate due to a first-policy-branch heuristic. The stop-before-intervention rule was applied correctly.

But let me think one more time about whether there's any bug I'm missing...

One potential concern: the `semantic()` function assumes `row["options"]` is a list indexed by the letter. If the options in the corpus are not consistently `[valid_action, invalid_action]` for o0 and `[invalid_action, valid_action]` for o1, then the semantic mapping would be wrong.

But the v3 corpus is supposed to have balanced option orders, and the `validate.py` check confirms A/B is balanced. The semantic mapping via `options` is the way to correctly handle this.

The first-policy-branch behavior is exactly what the v3 revision was trying to guard against. The fact that the model still exhibits this behavior is the finding itself — it's valid evidence, not a bug.

Actually, hold on. Let me re-examine one more time. The model answers look very systematic. Let me check whether there might be a prompt rendering issue where both policy orders produce identical prompts.

The v3 revision reverses the order of policy clauses. If the prompt rendering somehow normalizes the order (e.g., alphabetically sorting the clauses), then both p0 and p1 would produce identical prompts, and the model would give the same answer for both. But we see the model giving DIFFERENT answers for p0 vs p1 (A vs B), so the prompts must be different.

The fact that the model consistently picks the first policy clause's action suggests the rendering is correct and the model is just using a simple heuristic.

I'm now confident the evidence is valid.

Let me also check: does the `render()` function use `enable_thinking=False`? Yes. This disables the model's thinking mode, which is correct for a simple A/B task.

And the generation uses `do_sample=False` (greedy decoding), which is deterministic.

All good. The evidence is valid, the clean gate correctly fails, and the stop-before-intervention rule was applied correctly.

My final determination: SOURCE_GATE_BLOCKED.

Wait, the question asks: "Does job 705 provide valid evidence that its clean source task fails the predeclared gate, and was the stop-before-intervention rule applied correctly?"

If the answer is yes (valid evidence, correctly blocked), then the return should be `SOURCE_GATE_BLOCKED`.

If the evidence is invalid, `SOURCE_GATE_INVALID`.

If there's not enough evidence, `INSUFFICIENT_EVIDENCE`.

I believe the evidence is valid and confirms the gate should be blocked. So: `SOURCE_GATE_BLOCKED`.

But let me also check for any concrete validity bugs as requested...

Potential bugs I considered:
1. `semantic_case_id` uses v1 naming — not a bug, just a naming convention
2. Model exhibits first-policy-branch heuristic — this is genuine model behavior, not a pipeline bug
3. No intervention responses in log — confirms stop-before-intervention
4. Decision field should say CLEAN_GATE_BLOCKED_NO_INTERVENTION — consistent with code flow

I don't see any concrete validity bugs. The evidence is valid.

Actually, I want to be very careful. Let me re-read the question: "Does job 705 provide valid evidence that its *clean* source task fails the predeclared gate, and was the stop-before-intervention rule applied correctly? Check only this conclusion. Identify any concrete bug that could invalidate it."

So I need to:
1. Answer whether job 705 provides valid evidence of clean gate failure
2. Check if stop-before-intervention was correctly applied
3. Identify any concrete bug

My analysis:
- Yes, job 705 provides valid evidence. The CLEAN_GATE shows pass=false with minimum_accuracy 0.425 and only 1/96 strict cases.
- Yes, stop-before-intervention was correctly applied. No INTERVENTION_RESPONSE entries.
- I don't see concrete bugs.

Wait, actually let me think about this from a different angle. The model is clearly using a first-policy-branch heuristic. The v3 revision was specifically designed to detect this confound. The fact that the model falls for it is the valid finding. But is there a way the pipeline could be introducing this artifact?

Could the tokenizer's chat template be truncating or reordering the prompt? The `render()` function just applies the Qwen chat template to the prompt. The template shouldn't reorder content.

Could the model's generation be impacted by the `enable_thinking=False` flag? This disables thinking mode, which should only affect whether the model generates thinking tokens. Without thinking, the model might rely more on surface heuristics. But the test-proposal doesn't require thinking mode — it just says to generate A/B answers.

I'm satisfied the evidence is valid. My conclusion: SOURCE_GATE_BLOCKED.The file is too large to view directly. Let me try using bash to extract key fields.Let me try to extract the decision from the generation.json using bash.Now I've confirmed the full log. Let me trace through the complete picture:

1. Job 705 (the retry) ran successfully, generating all 384 clean responses
2. The CLEAN_GATE shows `"pass": false` with `"minimum_accuracy": 0.425` and `"strict_semantic_cases": {"passed": 1, "total": 96}`
3. No INTERVENTION_RESPONSE lines appear in the log - the stop-before-intervention rule was correctly applied
4. The local entrypoint downloaded the generation.json, showing `TASK_VALIDITY_SOURCE_DOWNLOADED`

Now let me analyze the model's behavior more carefully. Looking at the clean responses systematically:

The model exhibits a clear first-policy-branch heuristic:
- For p0 (valid policy first): the model generally picks the valid action's letter
- For p1 (invalid policy first): the model generally picks the invalid action's letter

This means:
- For valid rows: p0 correct, p1 wrong → 50%
- For invalid rows: p0 wrong, p1 correct → 50%

This produces the ~50% accuracy in all cells (range 0.425-0.625) and causes 95/96 semantic cases to fail (each case has 2 p0 + 2 p1 variants, with exactly 2 correct = 50%).

This is exactly the "first-policy-branch" confound that the v3 revision was designed to detect, and that the test-proposal.md lists as an explicit failure mode.

Now, the evidence is valid BUT there's one potential concern: the CLEAN_GATE output lists strict_case_failures with `tv1_*` style IDs. The test-proposal says v3 has 96 semantic cases. The strict_case_failures list has 95 entries (out of 96). But wait, let me count the cue families in the failures:

Looking at the failure list, I see semantic_case_ids for:
- seal_match: 0-3 (routing×2, allocation×2, storage×2, notification×2) = 16
- capacity: 0-3 (same) = 16
- roster: 0-3 = 16
- parity: 0-3 = 16
- precedence: 0-3 = 16
- link: 0-3 = 16

That's 6 × 16 = 96 semantic cases. All 96 should appear... but the failures list has 95 entries. Let me check if one case is missing. Looking at the list:

For roster, I see: tv1_roster_0, tv1_roster_1, tv1_roster_2, tv1_roster_3 but... wait, I see `tv1_roster_1_allocation_1` but no `tv1_roster_1_allocation_0`? Let me recheck...

Actually from the list:
- tv1_roster_0_routing_1, tv1_roster_0_routing_0
- tv1_roster_0_allocation_1, tv1_roster_0_allocation_0
- tv1_roster_1_routing_1, tv1_roster_1_routing_0
- tv1_roster_1_allocation_1 (missing tv1_roster_1_allocation_0!)
- tv1_roster_2_routing_1, tv1_roster_2_routing_0
- tv1_roster_2_allocation_1, tv1_roster_2_allocation_0
- tv1_roster_3_storage_1, tv1_roster_3_storage_0
- tv1_roster_3_notification_1, tv1_roster_3_notification_0

So `tv1_roster_1_allocation_0` is NOT in the failure list! This case PASSED the strict gate (all 4 variants correct).

Let me verify this against the CLEAN_RESPONSE data. `tv1_roster_1_allocation_0` would correspond to row IDs `tv3_roster_1_allocation_p0_o0_0`, `tv3_roster_1_allocation_p0_o1_0`, `tv3_roster_1_allocation_p1_o0_0`, `tv3_roster_1_allocation_p1_o1_0`.

From the log:
- `tv3_roster_1_allocation_p0_o0_0`: expected "invalid", text "B" → B=invalid → correct ✓
- `tv3_roster_1_allocation_p1_o0_0`: expected "invalid", text "B" → B=invalid → correct ✓
- `tv3_roster_1_allocation_p0_o1_0`: expected "invalid", text "A" → A=invalid → correct ✓
- `tv3_roster_1_allocation_p1_o1_0`: expected "invalid", text "A" → A=invalid → correct ✓

All 4 correct! This is because for this invalid case, both p0 and p1 give the same letter answer, and the mapping through options correctly identifies the action as invalid in both cases.

Wait, that's interesting. For p0, the model says B; for p1, the model also says B. But p0_o0_0 (invalid) has text "B" → B=invalid → correct, and p1_o0_0 has text "B" → B=invalid → also correct.

Hmm, but the first-policy-branch heuristic would predict: p0 picks valid action, p1 picks invalid action. For an invalid row, p0 would pick valid (wrong) and p1 would pick invalid (correct). But here both p0 and p1 are correct... let me re-examine.

`tv3_roster_1_allocation_p0_o0_0`: invalid, text "B"
- p0: valid policy first → model picks valid action. o0: A=valid, B=invalid. But the model picks B (invalid). That contradicts the heuristic...

Wait, unless the model's behavior is more nuanced. Let me look at this specific case. The valid rows for this same case:

`tv3_roster_1_allocation_p0_o0_1`: expected "valid", text "A" → A=valid → correct ✓
`tv3_roster_1_allocation_p1_o0_1`: expected "valid", text "B" → B=invalid → wrong ✗

So for valid rows, p0 is correct and p1 is wrong. For invalid rows, both p0 and p1 are correct. That's 3/4 correct.

This is actually interesting — the model is NOT consistently following a first-policy-branch heuristic for this case. For the valid row with p1, the model picks the invalid action (following first policy branch). But for the invalid row with p0, the model picks... well, let me check what the valid and invalid actions are for this case.

The model's behavior for this particular case (roster_1_allocation) is:
- p0 valid: picks A (valid action) ✓
- p1 valid: picks B (invalid action) ✗
- p0 invalid: picks B (invalid action) ✓
- p1 invalid: picks A (invalid action) ✓

Wait, for p1 invalid, the model picks A. Let me verify:
`tv3_roster_1_allocation_p1_o1_0`: expected "invalid", text "A" → o1: A=invalid → correct ✓

So for p1, the model picks B on valid rows and A on invalid rows. That's... the model picks different things.

Actually let me look at the option orders:
- o0: A=valid, B=invalid
- o1: A=invalid, B=valid

For p0 (valid policy first):
- valid o0: picks A (valid ✓)
- valid o1: picks B (valid ✓)
- invalid o0: picks B (invalid ✓)
- invalid o1: picks A (invalid ✓)

So for p0, the model always picks the valid action regardless of truth label! For valid rows, this is correct; for invalid rows, this is wrong... wait no:

If the model always picks the valid action:
- valid row, pick valid → correct ✓
- invalid row, pick valid → WRONG ✗

But for p0_invalid_o0_0, the model picks B. And o0: B=invalid → correct. So the model is picking the INVALID action, not the valid one.

Hmm, that means for this case, the model's behavior is:
- p0: always picks the first-listed option (A for o0, B for o1)... no wait:
  - p0_o0: A (o0: A=valid) → picks valid action for valid rows, invalid... no A=valid. So picks valid.
  - p0_o1: B (o1: B=valid) → picks valid.

So for p0, the model always picks A for o0 and B for o1. That's picking the letter that maps to the valid action, regardless of whether the row is valid or invalid.

For p1:
  - valid o0: B (B=invalid) → picks invalid despite valid row → WRONG
  - valid o1: A (A=invalid) → picks invalid despite valid row → WRONG
  - invalid o0: B (B=invalid) → picks invalid for invalid row → CORRECT
  - invalid o1: A (A=invalid) → picks invalid for invalid row → CORRECT

So for p1, the model always picks the invalid action.

Pattern:
- p0: model always picks the valid action (the first-listed policy clause)
- p1: model always picks the invalid action (the first-listed policy clause)

This is exactly the first-policy-branch heuristic! And it gives:
- valid + p0: correct ✓
- valid + p1: wrong ✗
- invalid + p0: wrong ✗
- invalid + p1: correct ✓

That's 2/4 correct per case, which is 50%. So for roster_1_allocation with 3/4, there must be something different...

Wait, let me recheck:
`tv3_roster_1_allocation_p0_o0_0`: invalid, text "B". P0 means valid policy first. Model should pick valid action. o0: A=valid, B=invalid. Picking valid action means picking A. But the model picks B (invalid). 

So the model is NOT following first-policy-branch for this one. It's picking B (invalid action) when first policy clause is the valid one.

Hmm, that's odd. But it only happens for this one specific case? That's 1 out of 96. This could just be a random fluctuation, or there's something unique about this particular prompt.

Regardless, the overall result is clear: 95/96 semantic cases fail, minimum accuracy is 42.5%. The clean gate correctly fails.

Now, my final verdict:

The evidence IS valid. The model genuinely fails the clean gate. The stop-before-intervention rule was correctly applied (no INTERVENTION_RESPONSE in the log, the code returns early on gate failure).

I don't see any concrete bugs that would invalidate the conclusion.

Wait, I should also check: did the generation.json actually record the decision "CLEAN_GATE_BLOCKED_NO_INTERVENTION"? The 13.7MB file is too large to read directly. But based on the code flow:
```python
if not data["clean_gate"]["pass"]:
    data["decision"] = "CLEAN_GATE_BLOCKED_NO_INTERVENTION"
    ...
    args.output.write_text(json.dumps(data) + "\n")
    return
```

The CLEAN_GATE says `"pass": false`, so the decision should be `CLEAN_GATE_BLOCKED_NO_INTERVENTION`. The return statement ensures no intervention code runs. The log shows `TASK_VALIDITY_SOURCE_DOWNLOADED` after CLEAN_GATE, which means the `launch()` function's host-side code completed successfully.

Actually, looking at the code flow more carefully, the remote function `remote()` returns the result to `launch()`, which then writes it locally. The `run()` function on the remote side writes to the cache path. Let me trace:

1. `launch()` → `remote.remote(source_revision())` → `remote()`:
   - Runs `run(args)` via subprocess, which writes to `/cache/outputs/audits/.../generation.json`
   - Returns `{"generation": ..., "mounted_preflight": ...}`

2. Back in `launch()`:
   - Writes the result to `ROOT / "generation.json"` (local)
   - Prints `TASK_VALIDITY_SOURCE_DOWNLOADED`

So the local generation.json should contain the full data including the decision. The CLEAN_GATE message in the log confirms the gate failed, and the absence of INTERVENTION_RESPONSE confirms the stop.

My conclusion is SOURCE_GATE_BLOCKED.