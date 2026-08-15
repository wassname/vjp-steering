We need answer review? User asks review public-repo plan. Need return <300 words APPROVE or REQUEST CHANGES. We have plan text now. Need check issues. We need evaluate as skeptical reviewer. Need identify VJP math, steering-lite use, fresh clone proof, data provenance, four-method plot, deletable work. We don't have actual files, but can review plan. Need decide APPROVE or REQUEST CHANGES. Likely find issues. Need be concise.

We need assess requirement/check mapping. R1 reimplement VJP-delta, compare saved reference <1e-4 and independent tiny-model reference. Check task 1. Likely failure: detached activation graph? Not explicitly check? Task 1 compares independent tiny model catches detached hooks wrong token masks wrong class subtraction. It checks output. Silent failure: VJP output shape passes while token reduction differs. Does R1 check token reduction? Compare output <1e-4 with saved ref would catch token reduction? Maybe if shape same but token reduction differs, output different. Task 1 independent tiny model might catch. Need mention.

R2 reuse steering-lite for mean diff, PCA, random, vector storage hooks. Copy none. How check? Need verify dependency commit, no copied implementations. Task? Fresh clone install lock file; source lines. Need explicit check for no copied code? Maybe not. Could pass if vendored copied code. Need review.

R3 notebook extracts all four vector types, bare and +/- text, plot. Execution from start to finish no cached dev vectors. Task 2. Need check no reading cached development vectors. How verify? Could include grep for dev paths, run in fresh clone. Fine.

R4 measured CSV generates results.md/html and plot. Plot judged on-axis vs abs off-axis; random directions form band. Assert one evaluation cohort for all rows. Need check CSV schema, admissibility. Likely okay.

R5 fresh clone installs and runs smoke check without dev repo. Task 4 clone temp, install lock, run smoke/renderer, recreate generated result, record commands/output, count source lines.

Maybe issue: "The public vector must differ from saved reference by less than 1e-4 in every element." But saved reference has 19 unit vectors of width 2560 = 48640 elements. Need absolute diff <1e-4, okay.

VJP math review: In reference flow, target cotangent = c at each valid target position, zero elsewhere. Gradients = autograd.grad(target activations, source activations, target cotangent). Then per prompt and layer = mean gradients over valid source positions. Then v[layer] = mean(pos per-prompt gradients) - mean(neg). Then normalize. Potential issue: Convention sign? c = mean(last target activation on positive) - mean(last target activation on negative). Vector = mean(pos grad) - mean(neg grad). If target cotangent is c at all valid target positions, grad wrt source activations. But target activation is at target layer, source activation at source layer. Since linear influence of source on target is positive? v = difference in source activations? Sign? Need check if sign matches additive steering: steering_lite adds C*v through hooks, but VJP-delta for activation difference maybe sign? The formula: VJP of difference in last target activation between pos and neg w.r.t source activations? For each prompt, if target activation a_T is a scalar? Actually last target activation maybe activation vector? The target cotangent = c (a vector? or scalar?) If target activation is hidden state vector at last target token, c is mean of last target activation vector over positive minus negative, a vector cotangent? Then autograd.grad(target activations, source activations, target cotangent) yields gradient contribution to source. Then per prompt mean, then difference. That is one possible formulation. If target activation is maybe scalar probability? But okay.

Potential math issue: "mean gradients over valid source positions" - For source layers, source activations at each valid source position. Autograd.grad returns gradients per position. They average over valid source positions. Then they average over prompts by class and subtract. Fine. But if target cotangent is c at each valid target position, they do "autograd.grad(target activations, source activations, target cotangent)": PyTorch `autograd.grad(outputs=target_activations, inputs=source_activations, grad_outputs=target_cotangent)` requires outputs shape grad_outputs same. If target_activations is per-token hidden states at valid target positions and target_cotangent is c repeated at those positions, okay. Then get grad per source position for each target position? Actually autograd.grad sums over outputs positions? Need careful: If outputs has shape [batch, target_valid_len, hidden], grad_outputs same shape, then inputs source_activations shape [batch, source_valid_len, hidden], autograd.grad returns gradient with same shape as inputs: sum over target positions of chain. Then mean over source positions. valid source positions maybe all-valid. fine.

Sign issue: For target cotangent `c` at each valid target position, they compute gradient wrt source. Then v = mean(pos_grad) - mean(neg_grad). This is VJP of target difference? It gives direction in source activation space. Additive steering `+C*v` should increase target contrast? Let's check: If we add C*v with C positive, target contrast increases? v is gradient of c w.r.t source, so if source moves along v, c increases. Add v => increase c. So yes.

Potential issue: "steering-lite runtime already adds C * v[layer] through block hooks" with `VjpDeltaC`? Need know steering-lite variants. It may add vector to residual stream? Does it use unit normalized vector? Fine.

Deletable work: plan says scope out old variants, selected 20. Need ensure no copying. Could mention `rg` for copied code. 

Need decide. The plan seems reasonably thorough but maybe missing explicit verification for R2 anti-copying, and R5 checks "without the development repo" but not mention dev repo path hidden dependency beyond editable dependency. It mentions likely failures editable local dependency. Need request changes maybe due to R1 "independent tiny-model reference calculation" but if tiny model is in dev repo? Need no hidden dev dependency. Need define independent reference in public repo? Maybe okay.

Potential flaw: "The plot shows judged on-axis change against absolute judged off-axis change. Random directions form a band." But `render_noise_cone.py` maybe the plot. Need ensure random band uses all 100 questions; the plan says random band must also use all 100; current selected-20 random rows will not be exported. Good.

Missing data provenance: CSV export includes run ID, method, random seed, direction, coefficient, judged changes, admissibility. But doesn't include model/checkpoint, prompt dataset version, number of questions, date, commit hash? It says run ID; maybe run ID encodes? Need explicit provenance fields. The saved reference says run ID, model, seed, prompt pairs, source layers, etc. But CSV may not include all. "Record run ID, method, random seed, direction, coefficient..." Might be insufficient. Need request changes: add model, dataset commit/hash, tokenizer, prompt template, layer scope, date/commit, source run metadata. This is data provenance issue.

Also "Assert one evaluation cohort for all rows." Good but if selected 20 enters? It will assert cohort? Could be.

"Recreate every generated result" in fresh clone: need ensure generated files checked in? Possibly.

Need maybe mention "R1 <1e-4 in every element" but saved reference has 19 vectors; task 1 only compares saved 4B reference vector? Need exact absolute tolerance across all 48,640 elements. Fine.

"independent tiny-model reference calculation"—where is code? Is it copied? Need specify it lives in public repo as test fixture, not dev.

"Count source lines" below 2000 lines, but what counts? Need define includes tests? Not.

Maybe final: REQUEST CHANGES, with 3-4 concrete items.

Need be under 300 words. We can write:

REQUEST CHANGES

- R2 anti-copying is asserted but not mechanically checked; add a check that scans for steering_lite implementation code (e.g., mean-diff/PCA/random/hook) and dev-repo paths; a fresh clone passing smoke check does not prove no copied code or no dev path if lock references local? Actually lock file could include local path? Need check lock does not use file path. "public Git commit" okay.

- R5 fresh-clone proof is incomplete: must inspect pyproject/lock for local/path dependencies (`file:`, `../`, `-e`), and run with `PYTHONPATH` cleared / in isolated env, not just install from lock.

- Data provenance: CSV fields lack model/dataset/tokenizer/prompt template/layer scope/commit, and exact raw evaluation metadata. Add required provenance columns and assert they match saved reference.

- VJP math: formula as described uses target cotangent `c` at every valid target position; if `c` is mean vector across prompts and then reused for all positions, that is correct for the described contrast, but verify autograd.grad sums target positions before mean over source positions. Need add a check that token reduction is exactly all-valid source/cotangent scopes; the saved vector tolerance may pass while scope differences cancel? Hmm.

- Notebook "must not read cached development vectors": add a startup assertion that no dev result files exist or hook file open? Hard. Could mention.

Need maybe not overdo. Need deliver final. The user says "Return fewer than 300 words with APPROVE or REQUEST CHANGES." We'll comply.

But before final, maybe consider if we can approve? Let's see if issues are minor. They ask "skeptical reviewer". Need likely request changes. I'll provide concise.

Let's craft with bullet list. Word count under 300. Need include APPROVE or REQUEST CHANGES at start maybe.

Final should not say we cannot review? We have plan now. We'll review.

Need maybe mention "Fresh-clone proof" must not depend on development repo; but check must also ensure no local path in lock. 

Let's draft:

REQUEST CHANGES.

- R2: plan checks reuse via fresh install and line count, but does not statically forbid copied implementations. Add a grep/test that the public repo contains no duplicate mean-diff/PCA/random/hook code and no `../j-steer-dev` or editable path references; lockfile must refer to git commit, not `file:`/path.
- R5: fresh clone must run from clean checkout with no development repo on `PYTHONPATH` and no pre-existing outputs; record environment and exact commands. Otherwise editable dep or hidden results can pass smoke.
- Data provenance: CSV fields omit model, dataset/prompt commit or hash, tokenizer/template, layer scope, batch size, date, and source run ID for reference; add columns/assertions so render outputs are traceable to the `all100_20260811T052702` cohort.
- VJP math: description is consistent only if `c` is a vector cotangent repeated over valid target positions and `autograd.grad` sums over output positions before the per-prompt source-position mean. Add a tiny-model check for scope/token reduction shape and sign, not just final vector tolerance.
- Notebook: add explicit assertion that no development cache/vector files are loaded; execute in fresh clone with output dir absent.

Then final.

Need ensure word count. Good.