# J-lens sycophancy repair: primary evidence

— PI/OpenAI Codex

## Gurnee et al., *Verbalizable Representations Form a Global Workspace in Language Models* — [primary paper](https://transformer-circuits.pub/2026/workspace/index.html)

> The simplest intervention is steering along a J-lens vector: h ← h + α v_t, applied at one or more layers and token positions. With negative α, or by projecting out the component of h along v_t entirely, this becomes an ablation.

> The second intervention, patching in lens coordinates (Figure 4C), exchanges one concept for another while leaving the rest of the activation fixed. Given a source token s and target token t, we form V = [v_s v_t], read the lens coordinates c = V†h [...] and set h_patched = h + V(σ(c) − c), where σ swaps the two entries of c (optionally scaled by a factor α).

> At all token positions, we swap the lens vector of the model's spontaneously chosen item with that of a different item from the same category that was not in the top-10 of the model’s possible outputs, leaving the rest of the activation unchanged, and allow the forward pass to continue.

> We extract concept vectors [...] recording the residual stream activation prior to the Assistant’s response to the prompt “Tell me about {concept}”, mean-subtracted over a baseline set of 100 other concepts. We then split each concept vector into two parts: a J-space component, the non-negative combination of its top k=16 J-lens vectors found by gradient pursuit, and a non-J-space component, the remainder.

> We then repeat both experimental protocols from this section, substituting each component for the J-lens vectors used previously, with every perturbation rescaled to the same magnitude.

> swapping along the concept vectors’ J-space components drives the swap target into the model's top-5 outputs on 59% of trials, approaching the 88% achieved by the pure J-lens vectors. However, swapping along the non-J-space components succeeds on only 5% of trials.

Epistemic context: direct method and result statements by the paper authors. The paper tests verbal report, introspection, factual reasoning, and flexible generalization. It does not report targeted sycophancy or flattery steering.

## Local observations

- The raw coordinate swap on Qwen3.5-4B, layers 13–21, reached the intended rank-1 category answer on 13/18 eligible alpha-2 trials: [audit](../audits/20260905_paper_native_verbal_report.md).
- The fixed `abrasive`/`flattering` swap on layers 6–24 remained in the public plot's random-direction zone. Its best coherent all-100 effects were +0.133 and -0.442, with damage 0.162 and 0.153: [audit](../audits/20260906_task279_j_lens_native_all100_grid.md).
- Above the coherent boundary, the fixed pair emits and repeats the literal lens words. This is direct output evidence, not proof of the underlying cause.
- The first broad-concept adaptation used long phrases, a signed difference of two J-space components, layers 6–24, and addition at every valid prefill position. Its GP16 tokens were often multilingual fragments and refusal-related terms; it is not the same as the paper's separate concept-component injection or swap.
- A coordinate exchange is symmetric in its two basis vectors. Reversing source and target leaves the operator unchanged; negative alpha extrapolates away from the exchange and is not the reverse paper intervention.

## Question

What is the smallest paper-faithful experiment that can distinguish a bad layer/source choice from a genuine failure to adapt J-lens interventions to bidirectional sycophancy? A working result must leave the random-direction zone on both benchmark sides before it returns to the public plot.
