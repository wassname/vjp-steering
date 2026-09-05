# External scientist review: J-lens intervention

Three independent reviews were followed by a seminar pass in which each reviewer saw the other reports and the country diagnostic.

## Convergence

All reviewers separated three operators:

1. raw two-coordinate pseudoinverse exchange, matching the printed equation;
2. unit-normalized two-coordinate exchange;
3. unit directed source-to-target transfer, matching the paper's “subtract the projection ... add an equal-magnitude projection” prose and the working Qwen replication.

They independently identified continuation-token hooks, missing source-activity checks, the fixed style-token pair, and layer-band choice as confounds in the old run. They recommended baseline-correct country prompts with prompt-prefill-only hooks as the next test.

The diagnostic then observed:

> raw exchange: 0/6 target, 6/6 source
>
> unit exchange: 0/6 target, 6/6 source
>
> unit directed transfer: 6/6 target, 0/6 source

Both exchange implementations satisfied their requested coordinate identities with maximum error below `5.1e-6`. Thus an algebraically correct symmetric exchange was not behaviorally sufficient at alpha 1.

## Minority insights retained

- Kimi identified the paper's formula/prose discrepancy before seeing results. Its seminar review objected that alpha 1 alone could not distinguish operator identity from scaling. The requested alpha 2–4 follow-up was then run: both exchange variants give 0/6 target answers at alpha 2 and 4, while directed transfer remains 6/6 at alpha 2 and falls to 3/6 at alpha 4.
- GLM's strongest surviving objection is conceptual: a single token direction for `abrasive` may encode surface lexical evidence rather than a behavioral style variable.
- DeepSeek emphasized that directed transfer is rank one and leaves the target's existing coordinate in place; this is a genuine mathematical difference, not a normalization detail.
- Kimi's preregistered ill-conditioning explanation is contradicted for the country pairs. The tested unit-direction cosine is `0.340–0.642`, and exchange still fails. The old style pair is also well-conditioned in saved metadata: condition number `1.223–1.364`, target/source norm ratio `1.075–1.137`.

## Hypotheses and bets

| hypothesis | evidence | current credence | discriminating observation |
|---|---|---:|---|
| directed unit transfer is the operative Qwen intervention | target answer in 6/6 at alpha 1 and alpha 2 across three bands; symmetric exchange is 0/6 at alpha 1, 2, and 4; working replication reports 97.2% | 90% | a wider, independently implemented country cohort reverses the operator ranking |
| repeated continuation edits caused the old literal-token collapse | old hooks stayed active during decode; repaired smoke has no repetition | 60% | prompt-only vs continuation-active transfer with all else fixed |
| fixed style-token coordinates do not define an active bipolar behavioral variable | corrected alpha 0.5–2 DEV is weak/non-monotonic in +C and uniformly wrong-sign in -C | 65% | per-prompt source-coordinate activity predicts intended judged effect |
| layer band was the main failure | directed country transfer works at all three bands | 5% | one band alone rescues a strong coherent style effect |
| lens/model mismatch was the main failure | same model/lens gives 6/6 directed country transfer | 2% | failure on a wider country cohort under directed transfer |

Credences are review synthesis, not measured probabilities.

## Decision

Use unit directed transfer, positive alpha in each semantic direction, and prompt-prefill-only edits for the corrected DEV run. Do not describe negative alpha as reverse. The alpha sweep resolves the scaling objection against symmetric exchange on these items: alpha 2–4 gives category-token corruption, not target answers.

The strongest objection is external validity: country-answer redirection does not establish that `abrasive` and `flattering` are active single-token representations of sycophancy. A corrected run can still be null without contradicting the country result.

Sources:

- `slop/reviews/2026-09-05_glm-5.3-flash_j_lens_swap_scientist_glm.md`
- `slop/reviews/2026-09-05_deepseek-v4-pro-0813_j_lens_swap_scientist_deepseek.md`
- `slop/reviews/2026-09-05_kimi-k3_j_lens_swap_scientist_kimi.md`
- corresponding `*_seminar_*.md` reports
- `slop/audits/20260905_j_lens_paper_native_diagnostic.md`

— PI/OpenAI Codex
