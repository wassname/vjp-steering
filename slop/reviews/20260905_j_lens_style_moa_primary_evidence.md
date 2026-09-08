# Primary evidence packet: paper and Qwen J-lens interventions

Question: how should the supplied methods, implementations, and observed outcomes be interpreted, and what measurements would resolve the important uncertainties?

## Global Workspace paper

### *Verbalizable Representations Form a Global Workspace in Language Models* — Gurnee et al. — [paper](https://transformer-circuits.pub/2026/workspace/index.html)

Epistemic context: primary paper; these are the authors' method and result descriptions.

> The second intervention, patching in lens coordinates (Figure 4C), exchanges one concept for another while leaving the rest of the activation fixed. Given a source token s and target token t, we form V = [v_s v_t], read the lens coordinates c = V^† h (where V^† is the pseudoinverse of V), and set h_patched = h + V(σ(c) - c), where σ swaps the two entries of c (optionally scaled by a factor α). The component of h orthogonal to span{v_s, v_t} is unchanged.

> At all token positions, we swap the lens vector of the model's spontaneously chosen item with that of a different item from the same category that was not in the top-10 of the model’s possible outputs, leaving the rest of the activation unchanged, and allow the forward pass to continue. In this example, we subtract the projection onto the Soccer lens vector and add an equal-magnitude projection onto the Rugby lens vector.

> For each prompt, we first confirm that the intermediate concept appears in the J-lens at intermediate model layers. We then apply the coordinate-swap procedure described in Figure 4: we exchange (at all token positions) the lens coordinates of the intermediate concept and a chosen alternative, leaving all components of the activation outside the span of those two lens vectors untouched, and allow the forward pass to continue.

> We study the role of Jacobian lens vectors in multi-step reasoning more systematically, using a set of 50 two-hop factual prompts with known intermediates like those above, choosing the swap target at random from within the same category as the true intermediate step. We measure the fraction of trials in which the swap moves the target-appropriate answer to the top of the model's output distribution. The Jacobian-lens coordinate swap succeeds in 54% of trials on Haiku 4.5, 70% on Sonnet 4.5, and 70% on Opus 4.5.

The paper also uses a distinct representation for broader concepts:

> We extract concept vectors using an approach introduced in prior work: recording the residual stream activation prior to the Assistant’s response to the prompt "Tell me about {concept}", mean-subtracted over a baseline set of 100 other concepts. We then split each concept vector into two parts: a J-space component, the non-negative combination of its top k=16 J-lens vectors found by gradient pursuit, and a non-J-space component, the remainder.

The paper's limitation section directly names weak single-token source activation:

> Some abstract concepts may map to tokens much more diffusely, and thus be difficult to read out from the J-lens, even if the model represents them as a single direction. We expect this accounts for a portion of the failures in our intervention experiments. Recall [...] that the cases where a lens-coordinate swap fails to redirect the model's answer are predominantly the cases where the source concept's lens vector was not strongly active to begin with; one reason a concept's lens vector might not be active is that the model's working representation of that concept does not coincide with any single-token lens vector.

## Our setting

Directly observed configuration:

- model: `Qwen/Qwen3.5-4B`;
- J-lens: average Jacobian fitted on 1,000 pretraining-like prompts;
- layers: 6 through 24;
- application: every prompt-prefill position, hooks removed during decoding;
- operator: unit-normalized directed transfer `h' = h + α(h·d_source)(d_target-d_source)`, not the paper's symmetric raw pseudoinverse swap;
- directions: one fixed single-token lexical pair across every prompt, `abrasive→flattering` for +C and `flattering→abrasive` for -C (Qwen token IDs 90474 and 80238);
- behavior test: fixed 15-question sycophancy development cohort, greedy generation, judged target effect and off-target damage;
- missing paper precondition: no per-prompt evidence that the fixed source token is active in the J-lens;
- persona pairs do not construct this intervention. They construct earlier VJP methods. Bare/steered response pairs are used only by the judge.

## Factual control

`outputs/audits/20260905_j_lens_country_alpha/diagnostic.json` directly records two baseline-correct country pairs across three layer bands. At α=1 and α=2:

- directed unit transfer: target answer in 6/6 item-band trials;
- raw symmetric coordinate exchange: target answer in 0/6;
- unit symmetric coordinate exchange: target answer in 0/6.

This establishes that the current directed operator can redirect a concrete, baseline-correct factual intermediate. The diagnostic records pre-edit coordinates but does not apply the paper's source-activity criterion. It does not establish style transfer.

## Style result

`data/dev/j-lens-transfer-formative-v2/results.csv` directly records:

- +C selected α=1.25: effect `+0.120`, damage `0.073`;
- -C selected α=3: effect `-0.280`, damage `0.307`;
- most lower doses have small, non-monotone, or wrong-sign effects;
- α=4, 6, 8: damage `3.93–4.61`, rejected for literal lens-token leakage/repetition.

Raw generation excerpts at α=4:

> `flattering the flattering the flattering the flattering the flattering [...]`

— `outputs/experiments/j-lens-transfer-formative-v2/cells/plus/c4.jsonl`, scenario `syco_bullshit_v2_med_pnf_02`.

> `flattering the the the the the the the the the the [...]`

— `outputs/experiments/j-lens-transfer-formative-v2/cells/minus/c4.jsonl`, scenario `syco_bullshit_v2_med_pnf_01`.

> `flattering the text with the original instruction: "flattering the text with the original instruction: [...]`

— `outputs/experiments/j-lens-transfer-formative-v2/cells/minus/c4.jsonl`, scenario `syco_bullshit_v2_leg_pnf_01`.

Observation: both semantic directions leak the token `flattering` at high α. Inference, not established cause: this looks more like forcing lexical token content than moving a stable behavioral variable.

— PI/OpenAI Codex
