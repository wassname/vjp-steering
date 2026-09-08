# Task-validity corpus v3

PI/OpenAI Codex, 2026-09-08. This is an offline revision. It made no model call, API call, judge change, score change, reservation, or paid launch. Both research goals remain OPEN. Unreserved budget remains $5.72509672744.

Current corpus: `corpus.jsonl`, SHA256 `b4ef9920b02959e1204c0baa681fc5d402909af65ee676d120145468324f527e`. It is frozen by `freeze.json` before its overlap audit. V1 and v2 remain unchanged. V1 failed its internal answer-position and calibration-holdout checks. V2 corrected those faults but an independent review found two further design faults: policy prose always put the valid action first, and its proposed causal gate accepted a constant A or B answer pattern.

## Construct

Each synthetic closed rule world asks whether complete stated evidence satisfies an operation precondition. The next action is a deterministic valid or invalid action. This is not a claim that a real methodology exists. It is not a sycophancy score and does not replace the existing continuous sycophancy/off-axis benchmark rubric.

The primary paper mechanism is retained from `../spec.md`, which quotes its paragraph 283: prompts can imply one intermediate through varied surface cues and ask different questions about it, then a residual probe can be decomposed against the J-lens dictionary. This supports a source-probe construction hypothesis. It does not establish that closed-world precondition satisfaction transfers to open-world fabrication correction in this model.

## V3 revision

Every frozen v2 row appears twice in v3. The pair keeps rule, evidence, label, split, consumer, action options, and answer position unchanged. It reverses only the order of the two policy clauses. V3 has 384 rows and 96 semantic cases, each expressed at both answer positions and both policy-clause orders.

`validate.py` verifies all of the following:

- A/B is balanced within each split, consumer, truth label, and policy-clause order.
- Valid-first and invalid-first policy clauses are balanced within each split, consumer, truth label, and answer position.
- Storage and notification are absent from both train and source-calibration, and occur only in withheld-source.
- Each semantic case has all four option-order and policy-order variants.
- V3 preserves the v2 rule, evidence, facts, label, split, cue family, consumer, options, expected answer, and option order.
- The local full100, DEV15, v13/v15/v16 source fit/holdout, and v15/v16 calibration prompt audits have zero exact-ID, normalized-content, 40-character containment, shared 5-gram, entity, and relation-template matches.

The lexical audit does not prove semantic independence. The synthetic scaffold, repeated entities, simple rule-following demands, and six non-independent cue families remain possible confounds.

## Test status

`test-proposal.md` defines a proposed semantic gate for a future source-state test. It evaluates selected action semantics, not A/B letters. The static controls in `validation.json` show that semantic-oracle answers pass while always-A, always-B, opposite-letter, and first-policy-branch heuristics fail. These simulations do not establish target-model behavior or benchmark transfer.

The independent non-Claude review is pending because the configured Codex reviewer reached its usage limit. Therefore v3 is review-pending and not execution-authorized.
