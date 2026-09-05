# Primary evidence for J-lens swap review

## Paper

Source: *Verbalizable Representations Form a Global Workspace in Language Models*, Anthropic, 2026, https://transformer-circuits.pub/2026/workspace/index.html

> Given a source token s and target token t, we form V = [v_s v_t], read the lens coordinates c = V^\dagger h (where V^\dagger is the pseudoinverse of V), and set h_patched = h + V(σ(c) - c), where σ swaps the two entries of c (optionally scaled by a factor α). The component of h orthogonal to span{v_s, v_t} is unchanged.

> We refer to the rows of W_U J_l as the Jacobian lens (J-lens) vectors at layer l; each J-lens vector is a direction in residual-stream space associated with a single token in the model’s vocabulary.

> For each prompt, we first confirm that the intermediate concept appears in the J-lens at intermediate model layers. We then apply the coordinate-swap procedure described in [the methods]: we exchange (at all token positions) the lens coordinates of the intermediate concept and a chosen alternative, leaving all components of the activation outside the span of those two lens vectors untouched, and allow the forward pass to continue.

> At all token positions, we swap the lens vector of the model's spontaneously chosen item with that of a different item from the same category that was not in the top-10 of the model’s possible outputs, leaving the rest of the activation unchanged, and allow the forward pass to continue. In this example, we subtract the projection onto the Soccer lens vector and add an equal-magnitude projection onto the Rugby lens vector.

> Swaps on country facts redirect the model's answer almost perfectly. Swaps on months succeed partially, animals rarely, and number relations never succeed at α = 1. [...] the target answer often does appear when the swap strength is doubled to α = 2.

## Official companion repository

Source: `anthropics/jacobian-lens@581d398613e5602a5af361e1c34d3a92ea82ba8e`, Apache-2.0.

`jlens/fitting.py:5-17`:

> The lens reads out an early-layer residual `h_l` by linearly transporting it into the final-layer basis with the average input-output Jacobian, then decoding with the model's own unembedding: `lens_l(h) = unembed(J_l @ h)`.
>
> for each output dimension, inject a one-hot cotangent at every valid target position at once and backprop. The gradient at source position `p` is then `sum_{p' >= p} dh_final[p'] / dh_l[p]`, the sum over later target positions; we take the mean over source positions `p`.

`data/experiments/README.md`:

> Swap — clamping a lens coordinate replaces one token's direction with another's at every band layer at the specified positions, then samples the continuation.

> The flexibility test swaps the lens representation of one arg for another from the same category, applied at every prompt position, and scores the next token against the new arg's answer.

The official repository does not include intervention hooks.

## Independent working Qwen replication

Source: `tao-hpu/jspace-replication@e03ee9711e2b8b7116f173aff32de38a3a463c51`, Apache-2.0.

`src/interventions.py:31-36,71-84`:

```py
def token_direction(lens, unembed_weight, token_id, layer):
    u = unembed_weight[token_id].float()
    J = lens.jacobians[layer].to(u.device).float()
    d = J.T @ u
    return d / d.norm()

coeff = h @ da
h = h - coeff.unsqueeze(-1) * da + coeff.unsqueeze(-1) * db
```

`experiments/e1-flexible-generalization/run_e1.py:63-81`:

```py
with swap_ctx:
    out = hf(ids, use_cache=True)
past = out.past_key_values
nxt = out.logits[0, -1].argmax().reshape(1, 1)
for _ in range(n_new - 1):
    out = hf(nxt, past_key_values=past, use_cache=True)
```

`docs/replication-log.md` reports:

> Qwen3-4B (band 10–34 by the same fraction, baseline 35/64): countries 97.2% hit / 0% stayed (n=36).

It also reports an early-mid band result on Qwen3-1.7B:

> all-layers 0–26: 91.7%/4.2%; early-mid 4–13 alone: 91.7%/4.2% (full effect); default 8–26: 87.5%; late 14–26: 79.2%; tail 20–26: 70.8%.

## Current implementation and observed run

`src/vjp_steering/vjp.py` currently constructs raw vectors and a two-coordinate pseudoinverse exchange:

```py
basis = torch.stack((unembedding[source_id] @ jacobian,
                     unembedding[target_id] @ jacobian))
dual = torch.linalg.pinv(basis.T)
coordinates = torch.einsum("...d,kd->...k", hidden.float(), dual.float())
delta = torch.einsum("...k,kd->...d", coordinates.flip(-1) - coordinates, basis.float())
return hidden + (alpha * delta).to(hidden)
```

`scripts/experiment.py` keeps the hook installed for the whole `model.generate` call:

```py
with vector(model, C=signed_coefficient(side, coefficient)):
    answers = walk.generate(model, tokenizer, missing_prompts, args.batch_size, args.max_new_tokens)
```

Current configuration: Qwen/Qwen3.5-4B; fixed pair ` abrasive` token 90474 and ` flattering` token 80238; layers 6–24 of 32; alpha=1 uses the positive paper-formula path; negative alpha is an extrapolation control.

Observed DEV means:

```text
alpha=0.5   effect=-0.180  damage=0.147  admissible
alpha=1.0   effect=-0.607  damage=0.140  admissible
alpha=1.125 effect=+0.067  damage=1.167  rejected; 9/15 outputs leak a lens token
alpha=1.25  effect=-2.807  damage=4.593  rejected
negative alpha=0.5 effect=+0.707 damage=4.207 rejected
```

Example alpha=1.25 continuation:

> flattering abrasive flattering abrasive flattering abrasive flattering abrasive ...

Example negative-alpha=0.5 continuation:

> abrasive abrasive abrasive abrasive abrasive abrasive abrasive abrasive ...

-- Compiled by PI/OpenAI Codex.
