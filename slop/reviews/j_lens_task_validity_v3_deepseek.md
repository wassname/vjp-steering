I'll read all the specified files carefully.



Let me read the remaining corpus rows to verify the parity/roster/precedence/link famiI've read all nine files plus the v2 corpus/freeze for the c

I have enough of the corpus structure. Let me verify one concrete claim in point 1 — that v3 differs from v2 *only* in policy-clause order — by reading a v2 row directly.

## Decision: TEST

I read all requested files in full (spec, corpus.jsonl, build.py, validate.py, validation.log/json, test-proposal.md, review-pending.md, parent spec, plus a v2 corpus row to close one gap). Verdict below, from the code and data rather than the declarations.

### 1. V1/v2 preserved; v3 changes only policy-clause order from v2 — CONFIRMED

`build.py` byte-sha-checks `v2/corpus.jsonl` against `v2/freeze.json`, and `validate.py` re-asserts `sha(v2/corpus.jsonl) == v2_freeze["corpus_sha256"] == freeze["parent_corpus_sha256"]`. Each v2 row is emitted exactly twice with `policy_order ∈ {0,1}`; `policy_order==0` keeps `(valid, invalid)` clause order, `==1` reverses it. `validate.py` pins `("rule","evidence","facts","valid","split","cue_family","consumer","options","expected","option_order")` equal to the v2 parent.

I checked this against raw bytes: v2 `tv2_seal_match_0_routing_o0_1` prompt is byte-identical to v3 `tv3_seal_match_0_routing_p0_o0_1` prompt, and the `p1` sibling differs only in the "When the requirement holds … otherwise …" clause. So the only *content* change is policy-clause order; new fields (`policy_order`, `policy_actions`, `expected_semantic_action`, `pair_id`, `v2_parent_id`, `semantic_case_id`, re-named `id`) are metadata.

### 2. Balance and holdout — CONFIRMED

`validation.json` shows every `split × consumer × valid × policy_order` (answer-position) and `split × consumer × valid × option_order` (policy-order) cell balanced (`balanced: true`, counts 6/6, 7/7, 5/5). `validate.py` asserts `storage`/`notification` never appear outside `withheld_source` (`held_consumers = {"storage","notification"}` + `assert not [...] consumer in held and split != "withheld_source"`). Corpus rows confirm these consumers occur only in `world 3`.

### 3. Gate maps letters→semantics; controls behave correctly — CONFIRMED, with residual confounds (acknowledged, not gate-breaking)

`selected_semantic` maps an A/B token through `row["options"]` to `valid/invalid` against `actions_valid_invalid`, never scoring the letter. `gate()` admits only if `min_semantic_accuracy ≥ 0.90` across *all* split / split×consumer / split×cue cells **and** every v2-parent pair and every 4-variant semantic case is consistent-and-correct. `validation.log`/`json` confirm: semantic_oracle passes (1.0), always-A/B (0.5), opposite-letter (0.0), first-policy-branch (0.5) all fail. The always-A/B controls land at exactly 0.5 because answer-key and policy-order are now both balanced, closing v2's constant-letter false positive.

Remaining shortcut surface I verified directly in the data:
- **Storage/notification valid action is not lexically counterbalanced** — `world 3` is the only world using them, so "store in lower drawer" and "notify team violet" are the valid actions for *all* such rows. A per-consumer lexical preference ("lower"/"violet") would score 100% *within* those consumers — but cannot pass the whole gate, because it is wrong on routing/allocation/precedence/link cells, and the gate takes the `min` over all cells.
- **Rule/evidence shared-token → "valid"** is trivially available for `seal_match`/`roster` (rule and valid-evidence share the entity, invalid-evidence does not). This is a real shallowness, but it is the *construct's* weakness, not a gate false positive: such a model still answers correctly, and the proposal already names this as the contrary hypothesis ("closed-world instruction following / relational matching"), which is exactly what the conditional benchmark-transfer test exists to discriminate.
- **Split/cue confounding** (parity only in source-calibration; precedence/link only in withheld) remains real and is acknowledged in both specs.

The one thing I would flag as a design risk, not a blocker: `"pass": ... and all(policy_mirror.values()) and all(full_mirror.values())` in `validate.py` makes the gate effectively **100% correctness across all 384 rows** (each of 96 cases × 4 variants must be perfect, plus "parse only exact stripped A/B, anything else = wrong"). That is materially tighter than the parent proposal's stated clean gates (90% split / 75% group / 90% order-consistency). It is conservative and still falsifiable, so it does not invalidate authorization — but it should be understood as near-certain to block any real 4B greedy run on a single token slip, i.e., the "pass" branch may be vacuously unreachable. Strictness that never passes is a power problem, not a falsifiability problem, and I do not think it rises to a REVISE under the narrow mandate.

### 4. Two claims kept distinct; no binary metric substituted — CONFIRMED

`test-proposal.md` (v3) and the parent `test-proposal.md` both: (a) treat the source-state test as a *separate, gated* admission (fit on train only, probe decomposition, causal "opposite semantic action"), and (b) make the **unchanged continuous sycophancy/off-axis DEV15 judge the sole transfer endpoint**, explicitly "Do not add a binary existence-rejection metric." `spec.md` states the corpus "is not a sycophancy score and does not replace the existing … rubric," and `validation.json`'s `limits` repeat "no binary existence-rejection score is added." The corpus measures *closed-world precondition satisfaction* only, and the proposal refuses to relabel a null as a dose/layer/source sweep.

### What v3 can and cannot establish

**Can establish (offline, and does):** v1/v2 immutability; that v3's only semantic-content change is policy-clause order; per-cell A/B and policy-order balance; no storage/notification leakage into train or source-calibration; zero exact-id / normalized / 40-char-substring / shared-5-gram / entity / relation-template overlap against the audited full cohort and source/calibration inputs; and that the five deterministic shortcut controls fail while the semantic oracle passes — i.e., the letter-vs-semantic and policy-order confounds are closed on paper.

**Cannot establish (and does not claim to):** any target-model behavior (no inference, API, or judge call was made); that solving these prompts implies a *task-validity intermediate* rather than shallow token-match / instruction-following; semantic independence (the lexical audit is explicitly bounded); causal efficacy of a probe direction; or benchmark transfer. Those require the already-described, separately budgeted source-state run and, only after independent review of it, the conditional DEV transfer test against the unchanged benchmark.

**Net:** the same narrow reservation as the spec itself states — v3 is an offline-authorization fix that correctly removes the two named v2 defects and keeps the benchmark as the only transfer endpoint. I would authorize the source-state experiment as described, with the explicit understanding that the 100% mirror gate is the key place it is likely to (legitimately) block rather than the controls leaking a shortcut through.