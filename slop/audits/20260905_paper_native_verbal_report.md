# Paper-native J-lens verbal-report: Qwen audit

— PI/OpenAI Codex

## Target and provenance

This audits pueue task 161, which ran `uv run modal run scripts/run_modal.py::paper_native_verbal_report` from `/workspace/2026/jspace/j-steer_pub` on 2026-09-05 21:58:20–22:02:40 +0800 and exited successfully. I read the complete cleaned log as `pqlog 161 100000` (69/69 lines) and inspected raw pueue bytes. The preserved cleaned log is [paper-native-verbal-report.log](../logs/20260905_j_lens_concept/paper-native-verbal-report.log); raw result records are [results.json](../../outputs/experiments/paper-native-verbal-report-v1/results.json).

The queue label's resolve condition was:

> why: prior J-lens experiments used directed additive/transfer operators rather than the vendored paper coordinate clamp; resolve: reproduce verbal-report with raw J rows, pseudoinverse coordinate swap, paper prompt set, and a predeclared mid-workspace Qwen band before adapting to sycophancy

The task ran the complete coordinate-swap protocol after two repaired pre-inference failures. The exact git revision is not emitted by this entry point. `f941d40` was HEAD immediately before task 161, but that is an inference from the local history, not recorded run provenance.

## Stage table

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| candidate data | 14 categories, first 10 candidates and only one-token targets outside clean top 10 | 117 valid trials from all 14 categories | yes | result JSON | target tokenization counts by category | target eligibility was applied |
| clean prompt | model is poised to name a category item at the scored token | top tokens were ` What`, newline, or double newline, never an eligible category candidate | no | log and result JSON | next semantic answer position / full clean continuation | this is not comparable to the paper's verbal-report condition |
| vector construction | raw `W_U J_l` rows and pseudoinverse coordinates on layers 13–21 | 9 layers, finite condition numbers 1.24–4.37 | yes | result JSON | independent lens-readout check at the scored position | numerical basis was nondegenerate |
| null/control | C=0 equals clean and hooks apply exactly once per selected layer | every saved `zero_hook_calls` and `swap_hook_calls` map has 13–21 set to 1; the script would abort on non-identical C=0 logits | yes | result JSON and script assertions | explicit C=0 max-logit delta saved to JSON | no visible hook-count or identity failure |
| causal swap | target rank improves and reaches rank 1 in some valid trials | 50/117 ranks improved, 65 worsened, 2 unchanged; 0/117 rank 1 | no | result JSON | prompt-compatible baseline | current task does not reproduce the paper outcome |
| persistence | complete record survives | Modal returned and local `results.json` exists | yes | final log line and file | git-tracked artifact copy | result is locally recoverable |

## Primary evidence

### Paper protocol

## *Verbalizable Representations Form a Global Workspace in Language Models* — [Transformer Circuits](https://transformer-circuits.pub/2026/workspace/index.html)
- page date: 2026 (article page); the paper authors describe their own protocol.

The paper describes a semantic answer slot before it describes the coordinate operation:

> We begin with a simple experiment in which the model is instructed to think of an item from a specified category (e.g. a language, a country, an animal; fourteen categories in total) and then to name it in a single word. We apply the J-lens at the token position immediately before the name is produced. In the example below, we ask Sonnet 4.5 to think of a sport, and apply the Jacobian lens to the colon immediately prior to revealing what the sport is. We see that Soccer appears strongly in the Jacobian lens at a late layer (the final layer of the “workspace range” identified in Figure 5), and indeed, the model responds with “Soccer”.

epistemic context: primary paper statement of its authors' experiment; it directly specifies their semantic clean condition but not Qwen compatibility.

This makes a semantic category response an entry criterion, not merely a cosmetic prompt choice.

The same paper defines the operator actually used here:

> The second intervention, patching in lens coordinates (Figure 4C), exchanges one concept for another while leaving the rest of the activation fixed. Given a source token s and target token t, we form V = [v_s v_t], read the lens coordinates c = V^† h (where V^† is the pseudoinverse of V), and set h_patched = h + V(σ(c) - c), where σ swaps the two entries of c (optionally scaled by a factor α). The component of h orthogonal to span{v_s, v_t} is unchanged.

epistemic context: primary paper method description; it supports the algebraic target but does not validate this Qwen run.

### What task 161 actually ran

The complete task log records 14 categories and a nonsemantic clean next token. These are direct runtime observations:

> 2026-09-05 13:58:51.975 | INFO     | __main__:main:79 - category=country clean= What source_id=3437 valid_targets=10
> ...
> 2026-09-05 14:00:21.010 | INFO     | __main__:main:79 - category=tree clean= What source_id=3437 valid_targets=10
> ...
> PAPER_NATIVE_J_LENS_VERBAL_REPORT_COMPLETE {"model": "Qwen/Qwen3.5-4B", "data": "/repo/data/vendor/jacobian-lens/verbal-report.json", "data_sha256": "9a33b48074c4565413247bace11d37537a963774936740287f0fb7dff460652c", "prompt_format": "paper verbal-report colon prefill, without a chat template", "operator": "h + V(swap(V^dagger h) - V^dagger h)", "layers": [13, 14, 15, 16, 17, 18, 19, 20, 21], "n_trials": 117, "n_top1": 0, "top1_rate": 0.0, "median_clean_target_rank": 77.0, "median_swapped_target_rank": 79.0}

Source: [paper-native-verbal-report.log](../logs/20260905_j_lens_concept/paper-native-verbal-report.log), a contemporaneous stdout record from Modal.

The raw output confirms that the source coordinate was not a category answer. For example, the first ten country swaps all exchange ` What` with a country word; their targets improve in rank but the swapped top token becomes newline rather than Japan, France, or another country. The sport prompt has clean top newline, and `Soccer` worsens from rank 11 to rank 31. These examples are the first country and sport records in [results.json](../../outputs/experiments/paper-native-verbal-report-v1/results.json), not selected for apparent success.

| category | clean source | trials | median clean rank | median swapped rank | improved | worsened |
|---|---|---:|---:|---:|---:|---:|
| country | ` What` | 10 | 77 | 47 | 10 | 0 |
| city | ` What` | 10 | 323 | 87 | 10 | 0 |
| tree | ` What` | 10 | 1081 | 267 | 10 | 0 |
| river | ` What` | 8 | 2678 | 436 | 8 | 0 |
| sport | newline | 9 | 41 | 49 | 0 | 9 |
| color | double newline | 8 | 34 | 86 | 0 | 8 |

This category asymmetry is observation, not proof that a coordinate swap is semantic: the output top token stayed structural in all 117 trials.

### Prompt eligibility follow-up — task 164

Task 164 is a clean-only follow-up run using the same model/data at source revision `27a6edcf33265d71f124ba160756867bd21d3b13`. I read its complete cleaned log (54/54 lines) and raw pueue bytes. Its direct final output was:

> PAPER_NATIVE_J_LENS_VERBAL_REPORT_COMPLETE {"model": "Qwen/Qwen3.5-4B", "source_revision": "27a6edcf33265d71f124ba160756867bd21d3b13", "data": "/repo/data/vendor/jacobian-lens/verbal-report.json", "data_sha256": "9a33b48074c4565413247bace11d37537a963774936740287f0fb7dff460652c", "prompt_mode": "raw", "prompt_format": "paper verbal-report colon prefill", "n_categories": 14, "n_semantic_clean_answers": 0}
> PAPER_NATIVE_J_LENS_VERBAL_REPORT_COMPLETE {"model": "Qwen/Qwen3.5-4B", "source_revision": "27a6edcf33265d71f124ba160756867bd21d3b13", "data": "/repo/data/vendor/jacobian-lens/verbal-report.json", "data_sha256": "9a33b48074c4565413247bace11d37537a963774936740287f0fb7dff460652c", "prompt_mode": "chat", "prompt_format": "Qwen chat template around the paper verbal-report colon prefill", "n_categories": 14, "n_semantic_clean_answers": 0}

Source: `pqlog 164 100000`; preserved as [paper-native-prompt-diagnostic.log](../logs/20260905_j_lens_concept/paper-native-prompt-diagnostic.log). This first classification used the paper's leading-space token form for both modes.

Inspection of the saved chat top-10 records then found category surfaces at assistant token IDs that have **no leading space**: `France`, `Blue`, `Apple`, `Earth`, `English`, `Doctor`, `Water`, and `Heart`. Local tokenizer replay against the same candidate list verifies 8/14 exact one-token category matches under the no-space form; raw remains 0/14 under its leading-space form. Thus task 164 rules out raw prefill and identifies a Qwen-chat-compatible candidate-token convention. It does not rerun the swap, so it is not a behavior result.

### Eligible Qwen-chat coordinate swap — task 174

Task 174 held the candidate data, raw `W_U J_l` coordinate construction, layers 13–21, and alpha 1 fixed. It changed only the token form required by Qwen's chat answer slot. Full cleaned log: 55/55 lines; raw bytes were also read. The run selected the eight semantic clean categories, of which six had at least one first-ten one-token target outside the clean top-10: country, color, planet, language, profession, and organ. Fruit and beverage had no eligible first-ten target after exclusions.

> 2026-09-05 14:30:18.952 | INFO     | __main__:main:118 - category=country clean=France source_id=47358 valid_targets=2
> 2026-09-05 14:30:22.269 | INFO     | __main__:main:118 - category=color clean=Blue source_id=10025 valid_targets=6
> 2026-09-05 14:30:31.790 | INFO     | __main__:main:118 - category=planet clean=Earth source_id=42373 valid_targets=1
> ...
> PAPER_NATIVE_J_LENS_VERBAL_REPORT_COMPLETE {"model": "Qwen/Qwen3.5-4B", "source_revision": "b2a4cf6b3439dfe6c37dc305debd752641758ea9", "data": "/repo/data/vendor/jacobian-lens/verbal-report.json", "data_sha256": "9a33b48074c4565413247bace11d37537a963774936740287f0fb7dff460652c", "prompt_mode": "chat", "candidate_prefix": "", "prompt_format": "Qwen chat template around the paper verbal-report colon prefill", "operator": "h + V(swap(V^dagger h) - V^dagger h)", "layers": [13, 14, 15, 16, 17, 18, 19, 20, 21], "n_trials": 18, "n_top1": 0, "top1_rate": 0.0, "median_clean_target_rank": 40.0, "median_swapped_target_rank": 9.0}

Source: [paper-native-chat-swap.log](../logs/20260905_j_lens_concept/paper-native-chat-swap.log), a contemporaneous Modal log. Saved raw rows are [chat results.json](../../outputs/experiments/paper-native-verbal-report-chat-v1/results.json).

The swap improves 17/18 target ranks, worsens 1/18, and leaves none unchanged; median rank falls 40→9. It still produces 0/18 rank-1 targets. Examples selected by the fixed target list: `Blue→Black` moves Black rank 55→3, `English→Italian` 149→35, and `Heart→Eye` 16→5. The clean top token remains `Blue`, `English`, or `Heart` in most of these examples; the rank movement is not yet a greedy output replacement. C=0 and swap hook maps are all `{13:1,...,21:1}` in every raw trial. Per-layer basis condition numbers span 1.34–2.59.

This is a valid **directional-rank reproduction** on the Qwen-compatible prompt condition, but it does not meet the paper's rank-1 success criterion. It materially lowers the probability that the earlier null was an inherent impossibility of applying the paper operator to Qwen.

The paper's appendix describes the most direct next test:

> The output is typically still the correct answer for the original argument, but the swapped-in target's answer often appears further down the ranking. This suggests that the α = 1 swap moves the activation in the right direction but not far enough; consistent with this interpretation, the target answer often does appear when the swap strength is doubled to α = 2.

epistemic context: primary paper authors' interpretation of their own flexible-generalization experiment; it supplies an alpha-2 hypothesis, not a promise that Qwen verbal-report will cross rank 1.

The next run should therefore change alpha from 1 to 2 only, keeping this chat condition, candidate selection, operator, and band fixed.

### Alpha-2 confirmation — task 179

Task 179 changes alpha from 1 to 2 and preserves every other task-174 choice: Qwen chat prompt, no-space answer-token IDs, candidate data, source/target eligibility, raw `W_U J_l`, layer band 13–21, and prompt-only prefill hooks. Full cleaned log was read (57/57 lines) and raw bytes were inspected.

> PAPER_NATIVE_J_LENS_VERBAL_REPORT_COMPLETE {"model": "Qwen/Qwen3.5-4B", "source_revision": "19bd7ec6782b73855882a88dd37324a9a09892c6", "data": "/repo/data/vendor/jacobian-lens/verbal-report.json", "data_sha256": "9a33b48074c4565413247bace11d37537a963774936740287f0fb7dff460652c", "prompt_mode": "chat", "candidate_prefix": "", "prompt_format": "Qwen chat template around the paper verbal-report colon prefill", "operator": "h + V(swap(V^dagger h) - V^dagger h)", "coefficient": 2.0, "layers": [13, 14, 15, 16, 17, 18, 19, 20, 21], "n_trials": 18, "n_top1": 13, "top1_rate": 0.7222222222222222, "median_clean_target_rank": 40.0, "median_swapped_target_rank": 1.0}

Source: [paper-native-chat-alpha2.log](../logs/20260905_j_lens_concept/paper-native-chat-alpha2.log), a contemporaneous Modal run log. Saved per-trial output: [alpha-2 results.json](../../outputs/experiments/paper-native-verbal-report-chat-alpha2-v1/results.json).

| alpha | trials | target rank 1 | median clean target rank | median swapped target rank | target ranks improved | worsened |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 18 | 0 | 40 | 9 | 17 | 1 |
| 2 | 18 | 13 | 40 | 1 | 13 | 5 |

Alpha 2 does not globally damage this narrow next-token task: the 13 successful rows' top token is their target (`Blue→Black`, `Earth→Moon`, `English→Japanese`, `Heart→Skin`, and others). Five rows instead send the target to rank 248320 while preserving the old top token, e.g. `France→Germany` and `Blue→Yellow`. This heterogeneity is visible in the complete stored records and prevents a claim that alpha 2 is uniformly safe. All 18 C=0 hook maps and all 18 swap hook maps record one call for each layer 13–21; no condition number exceeds 2.59.

**Native-reproduction verdict:** the paper-native coordinate operator is established on this Qwen-compatible verbal-report subset: it produces rank-1 intended tokens on 13/18 paired alpha-2 trials. This is strong evidence against interpreting the earlier additive concept-vector failure as a failure of J-lens coordinate swaps. It remains a limited next-token, single-token, Qwen-specific reproduction, not evidence that arbitrary abstract style vectors work.

## ml-debug form

| row | answer |
|---|---|
| log length and config | 69/69 cleaned lines read; Qwen/Qwen3.5-4B, BF16, `W_U J_l`, layers 13–21, alpha 1, 117 eligible target trials. |
| SHOULD lines / observed | No explicit `SHOULD:` lines. Successful completion implies C=0 exact-logit assertion and one-hook-per-layer assertion did not raise; saved hook maps are all ones. |
| headline scale and null | Paper success null is no rank-1 target. Observed 0/117 rank 1. Rank delta null is 0; observed 50 negative, 65 positive, median +4. |
| initial/demo output | `country` clean source ` What`; `sport` clean source newline. Neither is a category item, unlike the paper's Soccer example. |
| baseline / dummy | Bare prefill is the baseline. There is no random-vector control because the clean prompt validity fails before it would be informative. |
| full sample | Country Japan: clean rank 59, swapped rank 26, but top token changes ` What` to newline; sport Soccer: 11 to 31, top token remains newline. See result JSON. |
| worst-looking state | 0/117 target top-1; 65/117 targets worsen. No optimizer, loss, or gradients exist. |
| surprising lines | `country clean= What` and `sport clean=` newline contradict the paper's semantic clean-condition expectation; chasing prompt/model compatibility. |
| missing evidence | exact executed git SHA, C=0 max-logit difference, full clean continuation, and baseline prompt variants that produce a one-token category answer. |
| cheap discriminator | Run clean-only Qwen prompt variants and retain only those whose scored token is a category item; then repeat the unchanged swap. |
| wall-clock | 260 seconds from pueue start to end including model load; no GPU-memory metric. |

## Hypotheses

### H1 [data | Highly Likely | 85%]

- **Mechanism:** The unwrapped Qwen prompt has no valid assistant answer slot, so its final token predicts formatting or a follow-up question rather than a category item. Swapping ` What` or newline cannot test a category-answer coordinate exchange.
- **Evidence:** The run reports `category=country clean= What` and `category=sport clean=` newline; the paper says its example source is `Soccer` at “the colon immediately prior” to the answer.
- **Contrary evidence:** Country/city/tree/river target ranks improve consistently, so the operator causes some structured rank change even under this invalid condition.
- **Discriminating test:** Completed in task 164. Raw has 0/14 semantic answers; Qwen chat has 8/14 when candidates use no-space assistant token IDs. The next separator is the unchanged swap on those eight rows.
- **Fix/action:** Require the prompt-mode-specific semantic-answer eligibility test before any Qwen swap trial.
- **Interpretability:** partial; hook and rank movement are interpretable, but not the paper's verbal-report claim.

### H2 [method | Likely | 65%]

- **Mechanism:** Even with a valid prompt, Qwen's fitted lens or chosen 13–21 band may not support the paper's all-band alpha-1 swap.
- **Evidence:** With the present band, no target reaches rank 1 and median rank worsens from 77 to 79.
- **Contrary evidence:** The model was not in the paper's semantic source condition, so the result does not separate this from H1.
- **Discriminating test:** Hold the operator and valid source/target rule fixed; compare adjacent predeclared Qwen workspace bands only after a valid clean condition.
- **Fix/action:** Do not change representation or alpha until prompt eligibility passes.
- **Interpretability:** no causal paper-reproduction verdict yet.

### H3 [measurement | Likely | 60%]

- **Mechanism:** Rank-1 success alone loses evidence that the swap affected target rank; 50 ranks improved, with large improvements in four categories, while no top token was semantic.
- **Evidence:** The result JSON gives 50 improved, 65 worsened, median delta +4, and zero top-1 targets.
- **Contrary evidence:** The paper's declared verbal-report success is rank 1, so the primary verdict remains not met.
- **Discriminating test:** On a valid prompt, retain both paper top-1 and rank delta, and record clean/swapped top-10 tokens.
- **Fix/action:** Add top-10 and full clean continuation to the next artifact; do not reinterpret this as a partial reproduction.
- **Interpretability:** partial for distribution shifts only.

### H4 [bug | Unlikely | 35%]

- **Mechanism:** The coordinate implementation, hook site, or J matrix convention differs from the paper despite matching the stated formula.
- **Evidence:** The protocol lacks the paper's actual causal implementation; the result entry point does not independently read the J-lens at the patched token.
- **Contrary evidence:** The script passes exact C=0 assertions, hook maps are one call for every layer in every trial, condition numbers are finite (1.24–4.37), and it directly implements the quoted pseudoinverse formula.
- **Discriminating test:** At a valid prompt, record the source/target J-lens scores before and after swap plus a small algebraic reference test. A mismatch there would increase this hypothesis.
- **Fix/action:** Add lens-readout diagnostics before any claim about Qwen J-space failure.
- **Interpretability:** partial; arithmetic/hook identity checks are credible, model-level equivalence is not proved.

### H5 [harness | Unlikely | 25%]

- **Mechanism:** The run could have used a different dirty revision than `f941d40` because pueue records command/path but not git SHA.
- **Evidence:** The full log records no commit hash.
- **Contrary evidence:** The result schema and behavior match the currently inspected entry point; the run began immediately after the commit in local history.
- **Discriminating test:** Record `git rev-parse HEAD` and source hashes in the entry point before future inference.
- **Fix/action:** Add run provenance to the JSON before the next remote task.
- **Interpretability:** partial; this modestly lowers confidence in exact code provenance, not in the observed raw rows.

## Decision

1. **Resolve-condition verdict:** **met for a limited native reproduction.** Alpha 2 produces 13/18 rank-1 intended category tokens with the paper operator under the Qwen-chat-compatible token convention.
2. **Prediction check:** prompt eligibility prediction supported: raw 0/14, chat 8/14 semantic clean sources with correct token form. Alpha-2 prediction supported on 13 rows and contradicted on 5 rows, which suppress their targets to rank 248320.
3. **Earliest unsupported link:** a paper-native coordinate swap can redirect Qwen category answers. The next unsupported link is that it redirects a coherent agreement/disagreement behavior rather than a category label.
4. **Validity:** Define invalid as “the task lacks a semantic clean source or an exact alpha-2 control.” `P(invalid for the limited native claim) ≈ 0.05–0.15`; classification: **credible positive**, with 18-row scope.
5. **Highest-information clues:** (1) clean Qwen-chat tokenization yields semantic source tokens; (2) alpha 2 moves median target rank 40→1 and 13 targets to rank 1; (3) one-call hooks/C=0 assertions remain intact.
6. **Missing metrics by value:** (1) a paired binary agreement behavior test; (2) J-lens source/target readout at scored position; (3) explicit C=0 max-logit delta; (4) multi-token category coverage.
7. **Bugs requiring code changes:** no surviving bug is needed to explain the alpha-2 success. The boolean mask conversion was fixed before task 161.
8. **Misconceptions requiring reinterpretation:** “paper operator fails on Qwen” is contradicted on this task. “a rank movement at alpha 1 will become a rank-1 success uniformly at alpha 2” is contradicted by 5/18 rows.
9. **What would change verdict:** a no-space-token Qwen rerun that fails C=0 or hooks would lower confidence in implementation; an agreement task with no semantic clean source would not test behavioral adaptation.
10. **Recommended sequence:** change only the task source/target from category words to clean `No`/target `Yes` (or reverse) in a constrained false-claim agreement prompt. Keep Qwen chat tokenization, coordinate operator, alpha 2, and the band fixed. Do not call a successful binary-token shift general sycophancy control without a free-response follow-up.
