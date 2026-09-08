# Task-validity corpus — frozen v2 for independent review

PI/OpenAI Codex, 2026-09-08. **Offline authorship/validation only.** No model responses, API calls, benchmark answer-key inspection, score/rubric changes or paid launch. Both research goals OPEN. Unreserved **$5.72509672744**, new reservation $0.

**Current candidate:** [v2/corpus.jsonl](v2/corpus.jsonl), SHA256 **9d99757d9a449bb821f3b61b4174f5239a5fa51b3249e1c2cbb130b95af88ea9**. Its [freeze manifest](v2/freeze.json) fixes every ID/split and the generator hash before the v2 overlap audit. Root-level corpus.jsonl is preserved **rejected v1**, not the current candidate.

## Construct and provenance

Validity means **the explicitly stated necessary-and-sufficient precondition for an operation is satisfied by the stated complete evidence in a closed rule world**. Invalid means its precondition fails; it does not mean the operation is absent from real-world science. The consuming action is a deterministic consequence of that intermediate. No natural-world factual claim requires a citation: all names, rules, evidence and labels were authored by PI and are synthetic stipulations. No benchmark prompts/answers were used to write them. Inherited summaries exposed earlier benchmark failures to the author; consequently author-level independence is not blind independence.

Six cue families are equality of seal, numerical capacity, roster membership, parity, event precedence and directed connection. Four consumers route an item, allocate counters, choose storage and choose notification. The prompt never names sycophancy/candor or a persona. Each valid/invalid pair changes only its evidence sentence, retaining rule, consumer policy, word count and answer options. Rules are deliberately simple, completely specified and non-ambiguous; truth labels can be independently recomputed without an LLM. Both counterfactual worlds in a pair are coherent; the invalid world simply fails the operation's precondition.

Example v2 seal-match world0/routing: requirement is a Vek0 seal, evidence is either Vek0 or Zum0, the policy routes through gate if satisfied and bypass otherwise. Both A/B answer placements are included. Expected answer labels are stored **outside** the prompt. Higher validity is not defined as higher sycophancy. The proposed transfer hypothesis is that a common inferred *unsupported versus supported premise* representation might generalize to benchmark questions with false assumptions. Closed-world precondition inference may instead have no useful relation to recognizing fictional methods in open-world text; that is a serious falsifiable alternative, not a wording problem to conceal.

## Paper grounding and source-level limits

Primary source: [Transformer Circuits workspace paper](https://transformer-circuits.pub/2026/workspace/index.html), 2026, exact publication day not stated; cached [paper-evidence.md](../20260907_j_lens_dictionary_control/science-update/paper-evidence.md), original lines259/283/287. Cached excerpts preserve unresolved references. These are paper experiments on other models/tasks, not evidence that this synthetic corpus captures a Qwen sycophancy intermediate.

Line283, whole paragraph:

> For each two-hop prompt, we fit a probe for the unspoken intermediate: the mean residual-stream activation over a set of prompts that imply the same intermediate through different surface cues and ask different questions about it, minus the mean over all intermediates. We decompose each probe against the J-lens dictionary by gradient pursuit, splitting it into a J-space component (a non-negative combination of k=25 J-lens vectors, which typically explains roughly 10–15% of the probe's variance) and a J-orthogonal remainder carrying the rest (Figure ??, left). We then repeat the swap experiment with each part: exchanging the intermediate's probe for an alternative along the full probe direction, along only its J-space component, or along only its remaining non-J-space component.

Epistemic context: cached primary-paper paragraph describes its own probe construction and experiments; the corpus is our adaptation, not data from the paper.

Line259 first confirms an intermediate is visible before writing its coordinates; line287 tests whether identified J coordinates mediate the remainder's effect. Accordingly, labeled examples alone are not evidence that the model inferred those labels, and a good decoder alone is not causal evidence. This proposal does not import the paper's reported success rates or claim its entire J-space/complement partition is the orthogonal complement of one behavioral axis.

[Persona-steering skill](/home/code/.pi/agent/skills/persona-steering/SKILL.md) explicitly separates practitioner heuristics from published evidence. Its contrast arithmetic motivates matched prompts and nuisance balance, not confidence that any contrast steers. [Varglight skill](/home/code/.agents/skills/varglight/SKILL.md) motivates quote provenance and an explicit contrary-result branch. All validation here shares one authored source, not independent experimental replication.

## Frozen splits and revision history

V2 has **192 rows,96 valid/invalid pairs,48 base world-consumer instances**; mirrored answer orders are not independent worlds. Train48: seal/capacity/roster worlds0–1, routing/allocation. Source-calibration56: these families' world2 plus all parity worlds, routing/allocation only. Withheld-source88: these first families' world3 plus all precedence/link worlds. Storage/notification occur **only in withheld-source**, absent from both training and calibration. Precedence/link are wholly withheld cue families. No pair crosses a split.

A/B is exactly balanced **within every split × consumer × truth label**, and within every individual world/consumer/label via mirrored answer options. Valid and invalid evidence appear equally often. World parity reverses accepted seal/member, threshold inequality and event/link orientation, and reverses consumer action semantics. Cue/rule order varies by world and is identical within a pair. Every variant and split assignment is fixed; there is no post-output selection of correct examples to fit means.

Rejected v1 remains [corpus.jsonl](corpus.jsonl), hash **4d459ea1cd2efb6257e7a72088febcfec7c5354dba4c44abcfb1377a61a67ded**, recorded in freeze.json. V1 was frozen before overlap inspection and had zero external lexical overlaps, but self-audit found a consumer-specific answer-position association and four calibration rows using nominal withheld consumer types. [internal-design-failure.json](internal-design-failure.json) and [internal-design-check.log](internal-design-check.log) preserve the failures. Zero benchmark matches did not certify internal holdout validity.

Supervisor approved a narrow v2 correction: duplicate every row with both option positions and remap only parity-calibration storage/notification to routing/allocation. All original rules/evidence/facts/labels/splits remain unchanged, every v1 parent remains represented, and v1 bytes remain immutable. V2 froze before its own overlap audit; no words or rows were selected/removed based on benchmark matches. This is explicit design revision, not an unseen replacement corpus.

## Overlap audit, actual paths and limits

[validate.py](validate.py), [v2/validation.log](v2/validation.log), [v2/validation.json](v2/validation.json) save full commands/output, exact input paths/SHA256s/IDs/selectors and every overlap finding. Audited inputs:

- `data/bullshit_bench_v2.jsonl`: all100 prompts/IDs, full local cohort. DEV is its first15, as implemented by `scripts/walk.py` and `src/vjp_steering/experiment.py`.
- `outputs/experiments/j-lens-persona-{components-source-v13,components-source-v15,full-components-source-v16}/extraction/metadata.json`: actual source IDs and all condition prompts, split at recorded fit counts into fit/holdout.
- `outputs/experiments/j-lens-persona-{components-calibration-v15,full-components-calibration-v16}/calibration.json`: cohort size15 and complete ordered input-cohort hash verified against the local100 prompt/ID projection. The calibration references the same first15, not an invented independent set.

Only input prompts/IDs and necessary split metadata are projected from containers. No benchmark answer keys, historical generated answers, health or judge scores were displayed or used for authorship/audit. Input whole-file hashes necessarily cover other fields without interpreting them. No model/Transformers import is needed.

Exact IDs, normalized whole-content equality, bidirectional whole-prompt substring containment of at least40 normalized characters, shared contiguous5-token phrases, declared synthetic entity word matches and six named relation-template term pairs all return **zero matches**, in v1 and v2. These are transparent lexical heuristics, not proof of semantic novelty. Generic rule inference and the idea of a prerequisite may overlap benchmark themes despite zero hits. Private/future benchmark inputs and other historical extraction families were not audited; no global claim that every training source is disjoint. Full local100 is present, not missing. Full upstream/private completeness is unknown. All checks are rerunnable against the listed local paths; historical outputs not present in a fresh clone must be restored by exact recorded hash rather than called disjoint.

## Remaining known confounds

- Explicit rules remove uncertainty and external knowledge. The construct could be instruction following, relational matching, entailment, or conditional branching rather than a validity concept shared with sycophancy.
- Seal and roster families are almost isomorphic. Six family names are not six independent cognitive mechanisms. Parity appears only in calibration, precedence/link only withheld, limiting disentanglement of cue-family difficulty from split.
- Shared scaffold and Vek/Zum entities recur across source splits. Capacity worlds reuse the same numbers/inequalities. The192 rows contain only40 unique rule/evidence cues, with4 cue groups reused across splits (IDs in validation.json). Calibration is not a statistically independent natural task sample; world/order mirrors must not inflate effective N.
- A/B letters and one-token outputs are an artificial consumer; counterbalancing cancels first-order label association, not every nonlinear interaction. Shared phrasing may dominate representations despite balanced labels.
- Vocabulary/action semantics rotate but are not token-count matched under the pinned tokenizer; only whitespace word-count parity is established offline. Future tokenization must report paired lengths/last suffix identity before inference, fail on truncation, and cannot silently pad or rewrite the frozen corpus.
- Author has seen prior benchmark summaries. Mechanical input disjointness does not erase adaptive research choices or make later DEV confirmation held-out.

## Status and epistemic summary

**Review-ready v2, not execution-ready or empirically validated.** Label/split/overlap gates pass; the rejected v1 is preserved. Independent non-Claude review is owned by the parent workflow; this worker makes no claim to have obtained it. The separately frozen [test proposal](test-proposal.md) defines source-state and causal falsifiers plus a conditional transfer test using the **unchanged continuous benchmark judge**, not a new rejection rubric. Review may require revision if this construct is too remote from open-world fabrication handling.

Paper provides a mechanism, PI provides stipulations, script provides arithmetic/overlap checks. These are entangled evidence sources, not behavioral samples. Highly Likely (71–85%, subjective) that v2 removes the two identified first-order design defects; no numerical confidence in behavioral transfer is justified. The cheap way to be wrong is a missed task/label contingency, or a model that answers correctly without a causally usable shared state. That outcome must block the repair rather than motivate new synonyms or relaxed thresholds. Both original goals remain OPEN.
