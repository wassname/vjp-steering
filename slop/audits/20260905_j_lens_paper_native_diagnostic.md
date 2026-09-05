# J-lens paper-native diagnostic

## Result

On two baseline-correct country pairs and three layer bands, the working Qwen directed transfer changes the answer to the target in 6/6 cases. The literal raw exchange and a unit-normalized two-coordinate exchange remain at the source answer in 6/6 cases each. Hooks edit prompt prefill only and fire exactly once per selected layer.

| operator | target answer | stayed at source | trials |
|---|---:|---:|---:|
| raw two-coordinate exchange | 0 | 6 | 6 |
| unit two-coordinate exchange | 0 | 6 | 6 |
| unit directed transfer | 6 | 0 | 6 |

Trials are France→China and Canada→Egypt at layers 6–24, 9–30, and 4–13. Alpha is 1.

## Verbatim outputs

Baseline:

> France: ` Paris.\nThe capital of`
>
> China: ` Beijing.\nA. True`
>
> Canada: ` Ottawa.\nA. True`
>
> Egypt: ` Cairo. Cairo is located in`

Raw and unit exchanges return the source answer at every band:

> ` Paris.\nA. True`
>
> ` Ottawa.\nA. True`

Directed transfer returns the target answer at every band:

> ` Beijing.\nA. True`
>
> ` Cairo.\nA. True`

Source: `outputs/audits/20260905_j_lens_paper_native/diagnostic.json`, captured from the Modal return in `slop/logs/20260905_j_lens_paper_native_diagnostic.log`.

## Geometry and scope checks

- For both exchange variants, the maximum measured post-coordinate error from the requested exact swap is `5.0067901611328125e-06`; median is below `9e-7`. The exchange code does what its identity test says, but that operation does not redirect these answers.
- The unit-direction cosine across tested item/layer combinations ranges from `0.33978843688964844` to `0.642048716545105`; median `0.49085502326488495`. Near-singularity does not explain the exchange failure on these country pairs.
- The old `abrasive`/`flattering` extraction metadata also contradicts the preregistered norm/conditioning hypothesis: target/source norm ratios are `1.075–1.137` (median `1.097`), and raw-basis condition numbers are `1.223–1.364` (median `1.284`). Large norm imbalance or an ill-conditioned pseudoinverse did not cause that collapse.
- Directed-transfer source absolute mean coordinate before each layer edit ranges from `0.07990105450153351` to `1.1486414670944214`; median `0.26890823245048523`.
- Every selected layer has `hook_calls: 1`; continuation decoding is unhooked.

## Alpha 2–4 follow-up

The seminar review identified a remaining scaling alternative: symmetric exchange might require alpha above 1. A follow-up repeated every item and band at alpha 1, 2, and 4.

| operator | alpha | target | source | other |
|---|---:|---:|---:|---:|
| raw exchange | 1 | 0 | 6 | 0 |
| raw exchange | 2 | 0 | 0 | 6 |
| raw exchange | 4 | 0 | 0 | 6 |
| unit exchange | 1 | 0 | 6 | 0 |
| unit exchange | 2 | 0 | 0 | 6 |
| unit exchange | 4 | 0 | 0 | 6 |
| unit transfer | 1 | 6 | 0 | 0 |
| unit transfer | 2 | 6 | 0 | 0 |
| unit transfer | 4 | 3 | 0 | 3 |

At alpha 2–4, both exchange variants leave the source answer but produce category-token lists or repetitions rather than the target answer. Directed transfer remains perfect at alpha 2 and degrades at alpha 4. Thus the exchange failure is not repaired by the paper's doubled strength.

Source: `outputs/audits/20260905_j_lens_country_alpha/diagnostic.json` and `slop/logs/20260905_j_lens_country_alpha_diagnostic.log`.

## Interpretation

Observation: candidate C reproduces the expected paper behavior on two items and all three bands. Candidates A and B do not, despite exact coordinate-exchange checks.

Inference: the paper's verbal “subtract the projection onto [source] and add an equal-magnitude projection onto [target]” is the operative intervention in the available working Qwen replication. The paper's printed symmetric-pseudoinverse exchange is behaviorally different here. This does not prove why the paper text differs from the working implementation.

The old literal-token collapse is now most likely a combination of continuation-token edits and an inactive fixed style-token source. The diagnostic does not yet show whether `abrasive`→`flattering` can steer sycophancy.

## Updated diagnoses

| probability | diagnosis of the old collapse |
|---:|---|
| 50% | hooks edited every continuation step, allowing repeated token-direction feedback |
| 30% | fixed `abrasive` source was not active in unrelated benchmark prompts |
| 15% | symmetric exchange was the wrong operative intervention |
| 2% | layer band mismatch |
| 1% | model/lens transfer |
| 2% | unknown/evaluation confound |

— PI/OpenAI Codex
