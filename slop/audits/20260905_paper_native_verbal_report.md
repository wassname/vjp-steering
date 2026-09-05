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

1. **Resolve-condition verdict:** **not met.** The task used raw rows, a pseudoinverse swap, 117 trials, and the declared band, but it did not reproduce a rank-1 target: `"n_top1": 0, "top1_rate": 0.0`.
2. **Prediction check:** no recorded pre-run predictions beyond the resolve condition. Future runs must state prompt-validity and top-1 predictions first.
3. **Earliest unsupported link:** Qwen is in the same semantic answer condition as the paper. The required measurement is clean semantic candidate identity at the scored token.
4. **Validity:** Define invalid as “cannot test paper verbal report because the clean source is not a category answer.” `P(invalid for that claim) ≈ 0.85–0.95`. Classification: **inconclusive**, not a credible negative for J-lens.
5. **Highest-information clues:** (1) ` What`/newline source tokens contradict the paper's Soccer source; (2) zero top-1 target successes; (3) all hooks and C=0 controls completed, so the next test should change prompt compatibility rather than repair hooks.
6. **Missing metrics by value:** (1) prompt-condition semantic eligibility; (2) J-lens source/target readout at scored position; (3) explicit C=0 max-logit delta and git SHA; (4) full clean continuation.
7. **Bugs requiring code changes:** boolean mask conversion was fixed before task 161. Remaining code work is provenance and readout persistence, not a speculative steering rewrite.
8. **Misconceptions requiring reinterpretation:** “paper operator fails on Qwen” is unsupported. “This raw-prompt, mid-band Qwen condition has no rank-1 target swap” is supported.
9. **What would change verdict:** A valid assistant condition with a category clean answer followed by zero rank improvements/top-1 swaps would make H2 materially more probable; one or more rank-1 swaps would establish that the current failure was primarily H1.
10. **Recommended sequence:** raw is excluded. Repeat the exact coordinate swap only on the eight eligible Qwen-chat rows, using no-space assistant token IDs; retain layers, alpha, operator, and candidate data. Do not combine a prompt convention correction with a band, alpha, or representation change.
