REQUEST CHANGES.

- R2 reuse is not mechanically checked: add a test/grep that the public repo contains no copied mean-diff/PCA/random/hook implementation, no `../j-steer-dev` path, and no `file:`/editable lock dependency. A passing fresh install does not prove “copied none.”
- R5 fresh-clone proof is incomplete as stated: it must run with no development repo on `PYTHONPATH`, no pre-existing outputs, and in an isolated environment; record lock resolution and commands.
- Data provenance: the CSV fields omit model, dataset/prompt commit or hash, tokenizer/template, layer scope, batch size, date, and source run ID. Add these and assert they match the `all100_20260811T052702` reference cohort.
- VJP math: the flow is consistent only if `c` is a repeatable vector cotangent and `autograd.grad` sums target positions before the per-prompt source-position mean. Add a tiny-model check for token reduction scope and sign, not just final vector tolerance; shape passing can mask incorrect token reduction.
- Notebook: “must not read cached development vectors” needs an explicit assertion/fresh-output check, not just a task statement.

Add these verifications before implementation.