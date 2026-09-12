# Steering implementation review

Reviewed 2026-09-12 by PI/OpenAI gpt-6-astra. Review only; no production edits, installs, pretrained-model inference, GPU work, API calls, commits, or pushes.

Repository: branch `dev3`, commit `9d55120a8418a05a23035745f36c37677547be9f`. Installed steering-lite reports commit `0a064ba0c23a4998637ff41c5ab0fb5ca50a4271`, matching `pyproject.toml`. References are the supplied local paper and vendor source, not previous assistant reports. Vendor `.git` points to a missing parent gitdir, so I could inspect source but could not establish its commit.

## Decision

Repair extraction identity and argument handling before another comparison. Resolve `vjp_delta`'s semantic sign and the extraction prompt's thinking-marker format next. Existing CPU tests pass while the defects below reproduce; those passes do not establish a valid behavioral comparison.

Evidence:
- [Production-path discriminators](20260912_steering_evidence/discriminators.log)
- [Existing CPU checks](20260912_steering_evidence/existing_cpu_tests.log)
- [Actual cached tokenizer, prompts, and lens metadata](20260912_steering_evidence/data_and_lens.log)

## Verified implementation defects and mismatches

### 1. Extraction reuse does not validate most inputs (high impact)

At `scripts/experiment.py:685-691`, the general validator checks only:

> `if (metadata["method"], metadata["model"], metadata["dtype"]) != (args.method, args.model, args.dtype):`

All subsequent checks are restricted to concept methods. `load_or_extract`, lines 762-782, loads saved vectors and compares their configuration with saved metadata, not with requested layers, target layer, extraction sample count, seed, injection concept, or lens. Hashing an old vector establishes its integrity, not its agreement with the requested experiment.

Observed CPU discriminator:

> `cache_validator_accepts_changed_extraction_args mean_diff`
> `cache_validator_accepts_changed_extraction_args vjp_delta`
> `cache_validator_accepts_changed_extraction_args random`
> `cache_validator_accepts_changed_extraction_args j_lens_injection`

These calls supplied incompatible requested layers/target/sample count/seed/concept/lens while retaining method/model/dtype. They returned without error. This reproduces the validator behavior; it does not establish that a particular historical result was contaminated.

Impact: reusing an experiment ID can silently evaluate the previous extraction while the caller believes a new one was requested. Completed-cell early return at `scripts/experiment.py:1223-1236` can bypass even loading the model and extraction.

Repair/test: define one extraction identity from actual resolved inputs and compare it before any reuse or completion shortcut. Change exactly one field per test, with files otherwise valid; each change must reject reuse. Coordinate this with the evaluation review, which examines broader cache identity.

### 2. Several accepted extraction flags are silently dropped (high impact)

`--lens-file` is parsed at `scripts/experiment.py:204` but not forwarded in the swap, unit-direction, and injection calls at lines 577-580, 598, and 613. Each extractor therefore chooses the default cached/downloadable Qwen lens instead of the selected file. The older `scripts/walk.py:363-369` path does forward it.

The MLP extractor dispatch at `scripts/experiment.py:651-659` drops `args.target_layer`; the layer list computed at lines 621-624 is also unused for these methods. MLP implementations choose `n_blocks - 3` and all preceding layers (`vjp.py:876-877`, `1080-1081`). If all prior layers are an intentional method constraint, reject an incompatible `--layers` flag rather than silently accepting it.

Production dispatch observed with patched extractor boundaries:

> `dispatch_kwargs j_lens_swap {'source_token': 'abrasive', 'target_token': 'flattering'}`
> `dispatch_kwargs j_lens_unit_direction {}`
> `dispatch_kwargs j_lens_injection {'concept_token': 'flattering'}`
> `mlp_dispatch_kwargs {'batch_size': 1, 'max_length': 384, 'skip_first': 16}`

Impact: an intended layer/lens ablation may not occur. An explicit local lens does not reliably prevent the default resolver path.

Repair/test: forward supported flags and reject unsupported ones. Test the real `extract_vectors` dispatcher, not only the extractor called directly. Request a nonexistent explicit lens and confirm an error refers to that exact file, without network access.

### 3. Local `vjp_delta` cannot derive the advertised positive/negative direction (high conceptual impact)

At `src/vjp_steering/vjp.py:1247-1277`, the implementation computes:

> `cotangent = _target_mean(... positive ...) - _target_mean(... negative ...)`
> `directions = {layer: positive[layer] - negative[layer] for layer in layers}`

Writing the averaged pullback maps as A+ and A-, the raw direction is `(A+ - A-)^T c`. Exchanging the class labels negates both factors, leaving the result unchanged. Normalization does not fix that. Therefore a positive coefficient does not inherit the meaning “toward the positive class” as a mean difference does. It measures a difference in class-conditioned sensitivity to a frozen target contrast.

The installed steering-lite implementation explicitly documents this symmetry and calls `orient_vjp_delta` (`.venv/lib/python3.13/site-packages/steering_lite/variants/vjp_delta.py:98-124, 414-419`). The repository imports its apply function/configuration but bypasses that extraction orientation. The library's orientation heuristic is not proof of behavioral direction either, but the local implementation does not perform it at all.

Observed through the real local extractor on a two-layer CPU model, with a square nonlinearity:

> `vjp_label_swap [[0.7071068286895752, 0.7071068286895752]] [[0.7071068286895752, 0.7071068286895752]] equal True`

The input-class activation difference in this example is `[1,-1]`; the returned direction `[1,1]` is orthogonal to it. This is an analytic counterexample, not a Qwen outcome.

Impact: `+C`/`-C` result labels can carry an unsupported behavioral interpretation. The valid conclusion from poor performance is about this class-difference-of-pullbacks implementation, not Jacobian steering in general.

Historical scope: `outputs/experiments/v14-dev-vjp-delta-r2/extraction/metadata.json` records vector hashes and target layer 22, but no extraction implementation/revision identity. Published `data/results.csv` includes older 2026-08-21 VJP runs with source layers 6-24. I did not reconstruct those historical execution environments or establish whether they used this local extractor or steering-lite's oriented extractor. The current defects alone do not invalidate their measured outputs or establish a historical sign error.

Repair/test: first choose whether the intended quantity is sensitivity separation or movement along a behavioral axis. If the latter, specify and test orientation on held-out behavior; a label-swap test must reverse a signed axis. A common pullback `(A+ + A-)/2` does reverse under label swap, but replacing the algorithm requires a deliberate method decision, not a silent fix.

### 4. Zero VJP-delta produces NaNs instead of rejecting extraction (medium/high impact)

`vjp.py:1276` divides by `direction.norm()` without a zero/finite check. On a constant-Jacobian model, both class pullbacks agree even when the target activation contrast is nonzero. Zero is therefore a meaningful, expected case for this estimator.

Observed through the actual extractor with identity downstream mapping:

> `constant_jacobian_vjp [[nan, nan]] finite False`

Impact: an invalid vector can be saved and used for generation; model incoherence could then be attributed to steering strength. The current tests only check layer bounds (`tests/test_vjp_delta_target_layer.py:17-24`). `j_word` has the same unguarded normalization at `vjp.py:518`, though I did not reproduce its zero case.

Repair/test: reject a zero/nonfinite raw vector before saving or normalizing. Keep the identity/constant-Jacobian fixture; it should fail clearly rather than generate NaNs. This does not require adding an epsilon that hides the undefined direction.

### 5. The current persona source has a thinking-template mismatch (verified input mismatch; behavioral damage unmeasured)

The normal source for mean_diff and VJP methods is `extraction_prompts` (`scripts/experiment.py:402-417`), which calls `make_persona_pairs(... thinking=True, seed=0)`. Installed `load_suffixes` manually prepends `<think>` to half the entries (`steering_lite/data/personas.py:96-99`). The renderer appends these entries as assistant content with `continue_final_message=True` (lines 312-319).

With the actual cached Qwen tokenizer, the first consumed positive prompt was:

```text
<|im_start|>user
Answer as someone who is sycophantic.

Tell me a story.<|im_end|>
<|im_start|>assistant
<think>

</think>

<think>Once there was a little boy, who felt very miserable. ...
```

The [evidence log](20260912_steering_evidence/data_and_lens.log) retains the full suffix and matching negative prompt. Evaluation instead uses an empty generation prefix with thinking disabled and asks for two short sentences (`scripts/walk.py:444-455`). Thus source activations include a fixed assistant story after a closed empty thinking block and a reopened `<think>`; evaluation starts before any answer.

Observed source counts: 200 suffix entries, 65 unique user messages, 100 manually prefixed `<think>` entries; actual maximum rendered source length 240 under the requested limit 384. These are paired persona-prefix perturbations of the same fixed continuation, not 200 independently collected sycophantic/candid response pairs. Repeated user messages do not make the suffixes identical, but they reduce independence for prompt-level split-half diagnostics.

Impact: extraction can capture processing of persona words under an unusual continuation/thinking context rather than the behavior intended at inference. Both positive and negative share the structural issue, so its effect on their difference is uncertain; shared structure alone does not prove cancellation after a nonlinear transformer.

Repair/test: specify whether extraction and inference prompts should enable thinking, inspect token IDs after rendering, and prohibit duplicated/reopened thinking markers if not intended. Compare source behavior with and without the persona prefix on a small held-out set before interpreting the vector as a candidness axis. Use message-group splits when estimating generalization across user prompts.

### 6. The vendor readout unit regression does not invoke production readout (medium impact)

`tests/test_j_lens_vendor_readout_regression.py:36-44` computes both “production” and “direct” scores using duplicated local code and the same local RMSNorm object. It never calls `scripts/reproduce_paper_j_lens.py:76` (`clean_layer_lens_readouts`). Mutating the real function to omit normalization would leave this synthetic test passing.

The actual production function currently does call `model.model.norm` at lines 115-120; I am not reporting a current missing-normalization bug there. The later real-trial test checks saved historical readouts, which also cannot detect a new mutation of the production function.

Repair/test: call the actual production helper with a nonuniform norm fixture, then independently compute its expected output. Mutate the production call to identity and require the test to fail. Existing injection tests do better here: their nonsymmetric-J fixture checks extraction and their dispatch test exercises actual Vector hooks.

## Reference fidelity and actual method semantics

Reference source: Gurnee et al., *Verbalizable Representations Form a Global Workspace in Language Models*, supplied local copy `/workspace/2026/jspace/jsteer/docs/papers/jacobian_lens_workspace.md`, Methods, lines 160-221; author's own method description, not independent replication.

> “We refer to the rows of W_U J_\ell as the Jacobian lens (J-lens) vectors at layer \ell.”

> “Given a source token s and target token t, we form V = [v_s\; v_t], read the lens coordinates c = V^\dagger h ... and set h_{patched} = h + V(\sigma(c) - c) ... The component of h orthogonal to span{v_s, v_t} is unchanged.”

The supplied vendor `jlens/fitting.py:6-16, 186-205` uses a sum over valid target positions and a mean over valid source positions, then an equal-prompt mean. It excludes the first 16 and final positions. This agrees with local `_batch_gradients` and `_class_mean_vjp` reductions. Do not report the absence of target-count division as a local bug: it is the reference estimator, although the paper's expectation notation can invite a different reading.

- **mean_diff:** actual installed extractor records the final nonpadding token of the fixed assistant suffix and subtracts class means. It normalizes independently at each residual layer, then adds `C*v` at every prefill and decode position. Positive sign follows the source label by construction. “Abrasive” still does not mean “independent critical assessment without insults.” No arithmetic bug found in this path.
- **vjp_delta:** cotangent is the difference at the final source-prompt position (`vjp.py:282-284`); it is broadcast to all valid target positions, excluding that final position, before source pooling. The module header's claim that the target cotangent is pooled is inaccurate. This last-position-to-all-position transfer is an adaptation, not the same statistic as mean_diff and not a paper-prescribed sycophancy method. Unit norm per residual layer; applied during prefill and decode.
- **MLP VJP variants:** extraction and apply both target `mlp.up_proj` output, before gating/down-projection. The per-side variant uses the positive-conditioned pullback for `+C` and the negative-conditioned pullback for `-C` with an external minus sign. The shared variant averages matched positive/negative pullbacks, applies EB shrinkage, and uses the same ray with opposite coefficients. Its last-token variant changes the target cotangent mask, while still averaging valid source positions. Scaling is `sigma^2*g / ||sigma*g||` globally across layers: C is a standardized-activation displacement magnitude, not a per-layer residual-vector norm. Side-specific sigmas also make the two stored per-side raw norms incomparable without their scale. I checked these formulas and hook locations; I did not validate their behavioral optimum or statistical assumptions.
- **J_word:** `vjp.py:495-503` averages unembedding rows of independently tokenized word fragments before applying J. Actual cached tokenization is `sycophantic -> [' s','yc','oph','antic']`, versus the single token `' abrasive'`. Therefore this is a contrast of mean subtoken vocabulary rows, not a learned multi-token sycophancy representation or a sequence log-probability gradient. The paper explicitly limits ordinary lexical J-lens vectors to single-token concepts. Treating J_word as the paper's sycophancy vector is a verified conceptual mismatch; the behavioral size of the damage is unmeasured. It applies unit vectors at all prefill/decode positions through VjpDelta.apply. It is available via `walk.py`, but not the current `experiment.py` METHODS list.
- **Lexical swap:** `basis = W_U[[source,target]] @ J`, `dual = pinv(basis).T`, then `(swap(coordinates)-coordinates) @ basis` has the correct transpose and pseudoinverse semantics (`vjp.py:50-60, 547-548`). This is not a dot-product coordinate transfer. Alpha=1 swaps; alpha=-1 extrapolates away from the swap, not its inverse (a full swap is its own inverse). The metadata acknowledges this, but calling the sides “toward sycophancy/candidness” needs evidence about which coordinate is initially larger at each patched position. Production skips sequence-length-one calls; under ordinary cached generation this is prefill-only. It also edits left-padding positions, unlike masked concept hooks; those positions should be attention-masked, but padding invariance was not tested.
- **Unit direction/injection:** unit direction is `normalize(v_flattering-v_abrasive)`. Injection uses a single normalized lexical row; both side coefficients are positive and select different concepts. These are valid additive adaptations of the paper's writing operation. They are not a complete replication of its introspection/report tasks, and injecting “abrasive” has no necessary candidness meaning. Their apply tests pass, including decode skip and distinct side vectors.
- **Concept variants:** `j_lens_concept.py:498-645` uses “Tell me about {concept},” a locally authored 100-concept baseline, and nonnegative gradient pursuit with unit dictionary rows and 16 steps. The positive/negative concepts are specified in `j_lens_concepts.json`, distinct from the lexical pair. The signed variant subtracts reconstructed J components and unit-normalizes; components variant independently unit-normalizes two components and sorts their coordinates toward a chosen target (`component_target_coordinates`, lines 247-254). Target sorting is conditional swap/identity, not the unconditional paper swap. The code labels these normalization and behavioral adaptations. Persona-component extraction uses 65 deduplicated source messages and an 80/20 split (52 fit, 13 held out), with separate positive/negative-versus-neutral signals. I checked the code, not its saved behavioral results.

The paper's normalized readout is `W_U norm(J h)`, whereas its named writing vectors are rows of raw `W_U J`. A raw dot product, pseudoinverse coordinate, and vendor-normalized token score are different measurements. Learned nonuniform RMSNorm weights prevent assuming their rankings agree. The present raw writing-vector construction is consistent with the paper's stated definition; omitting RMSNorm from that construction is not, by itself, a demonstrated implementation bug.

Cached lens observation: n_prompts=1000, d_model=2560, source layers 0-30, snapshot `16a01f309fcec900fdcec3f4cd5b64f3d00e4d5a`, filename under `Salesforce-wikitext`. Its four-key checkpoint contains no model revision, target layer, tokenizer identity, source prompt IDs, or fitting configuration. `_load_j_lens` only checks width and layer membership (`vjp.py:475-480`). Same-width but incompatible models can pass. The filename suggests a Wikitext fit; I did not independently reconstruct the actual 1000 samples or fitting revision. Treat exact corpus/model compatibility as an open provenance issue, not established by the filename.

## Verification, limits, and ml-debug form

Executed CPU checks with `CUDA_VISIBLE_DEVICES=''`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, using `.venv/bin/python` directly. No dependency resolution. Pytest is absent (`ModuleNotFoundError: No module named 'pytest'`); existing tests were invoked through unittest/runpy instead. Three unittest cases, three injection functions, two unit-direction functions, and the synthetic vendor-norm test passed. The real-trial replay was deliberately excluded. New inline discriminators exercised the actual VJP extractor, dispatch function and cache validator; patched boundaries prevented model loads.

The first tokenizer inspection hit a 30-second timeout with buffered output. A second unbuffered attempt printed all data/lens observations above but reached the 60-second command timeout. Its log is evidence of those observations, not a successful process-exit assertion. No remaining inspection process was seen afterward. The precise timeout cause is unknown; imports/local tokenizer loading and shutdown were not separately timed.

This is a source review, not a run-result audit. Form fields are explicit so static evidence is not mistaken for run evidence:

- Log/config: linked CPU logs; no training/evaluation run was selected or read in full. Repository defaults and actual rendered extraction inputs were inspected.
- SHOULD/observed: valid signed axes should reverse under label swap; local VJP did not. A zero raw VJP should reject normalization; it returned NaNs. A requested extraction identity change should invalidate reuse; the validator accepted it.
- Null scales: constant Jacobian implies zero difference of class pullbacks analytically. Unit-vector magnitude is one by definition. Token counts are exact source counts, not performance metrics.
- Init demo/baseline/dummy/held-out wins: unknown; no pretrained-model inference executed. The full consumed source prompt is retained in the data log; generated behavior under that prompt was not measured.
- Schedule, loss, gradient norms, worst step, wall-clock/GPU memory by stage: unavailable/not applicable to these nontraining CPU checks. A real-run trace would be needed for behavioral conclusions.
- Surprising lines: repeated `<think>` source structure is explained by loader plus template; identical VJP under label swap is explained algebraically; NaNs are explained by zero-norm division; cache/flag acceptance is explained by missing comparisons/forwarding.
- Trust gaps: no complete historical extraction/generation reconstruction; no cross-seed behavior; no matched prefill/decode control; no lens fitting-source identity. These prevent claims that one steering method wins or fails scientifically.
- Competing explanations for a disappointing steering curve (subjective prioritization, not measured posterior probabilities): source/axis mismatch 40%; extraction identity/configuration error 25%; evaluation/selection problem 15%; genuinely weak behavior transfer 10%; unknown 10%. For: direct source issues above. Against: no demonstrated historical contamination or repaired behavioral run; all causal attribution remains untested. These possibilities can coexist.
- Fresh reviewer: this worker is the parent's fresh source reviewer. No further reviewer launched, per task restriction; parent must independently check the decisive lines and logs.
- Cheapest discriminator: before any behavioral run, test resolved arguments/cache invalidation and label reversal through production. Then inspect a source-prompt behavioral control separately from a steering control. A source mismatch predicts the persona prompt itself fails to instantiate candidness; an extraction defect predicts it can succeed while the extracted intervention does not.

## Recommended repair order

1. Unify resolved extraction identity and forward/reject CLI flags; test fresh and cached dispatch.
2. Reject zero/nonfinite vectors before saving. Choose and document VJP sign semantics with label-swap tests.
3. Repair or explicitly justify source thinking/continuation format; validate the source persona behavior. Treat J_word's subtoken averaging and abrasive/candidness mismatch as method limitations until replaced by an explicit representation choice.
4. Exercise production readout and hook paths in CPU regression tests; include nonsymmetric J, nonorthogonal basis, mixed prompt lengths, real attachment dtype and decode behavior.
5. Only then spend compute comparing behavior with matched source data, position scope and held-out judgment. No experiment was queued or recommended as an immediate paid action in this review.

Signed: PI/OpenAI gpt-6-astra.
