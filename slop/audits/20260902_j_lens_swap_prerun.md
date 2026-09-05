# J-lens coordinate swap: pre-run checks

## Question

Does the paper's exact two-coordinate patch for the single tokens `abrasive` and `flattering` move judged sycophancy while retaining low off-target damage on the fixed DEV cohort?

## Method

For each residual-stream layer in the existing 20%–80% band:

$$V=[v_{abrasive}\;v_{flattering}],\quad a=V^\dagger h,\quad h'=h+\alpha V(\sigma(a)-a).$$

The vectors are rows of $W_UJ_\ell$, are not normalized, and are applied at every token position. Positive $\alpha=1$ is the paper swap; $\alpha=2$ is its reported double-strength swap; $\alpha=0.5$ is interpolation. Negative alpha is an extrapolation control, not a reverse source-target swap. Reordering the two basis vectors gives the same intervention.

## Predictions before generation

| condition | predicted judged target effect | predicted damage | interpretation |
|---|---:|---:|---|
| $\alpha=0$ / bare | 0 | 0 | identity control |
| $\alpha=0.5$ | small, sign uncertain | lowest nonzero | partial coordinate exchange |
| $\alpha=1$ | larger if these literal coordinates mediate the trait | moderate | exact paper swap |
| $\alpha=2$ | possibly larger, plausibly damaged | highest | paper's double-strength extrapolation |
| $\alpha<0$ | depends on whether the clean hidden state has more `abrasive` or `flattering` coordinate | plausibly increasing with magnitude | amplifies the clean coordinate difference; it is not opposite semantic steering |

The result that would make this implementation unpromising is no coherent judged target movement at $\alpha=0.5,1,2$, or movement explained by high off-target damage. One token pair is one implementation, not a test of every J-space representation of sycophancy.

## Checks

- `scripts/experiment.py ... --self-test` checks alpha-zero identity, alpha-one coordinate exchange, and exact save/reload.
- The real-model smoke test checks that the hook changes logits and detaches cleanly.
- DEV uses 15 fixed questions, AB order, one pass. The judge, not lens-coordinate movement, defines the result.
- Reviewer finding: the reviewer initially read both manifest grids as positive alpha. `extend_generation` applies `signed_coefficient(side, coefficient)`, so `+C` uses positive alpha and `-C` uses negative alpha; the magnitude-only manifest is not a duplicate.

## Cost estimate

DEV has 6 steered cells × 15 questions = 90 judge calls and 105 generated responses including one bare set. At OpenRouter's listed DeepSeek rates ($0.05/M input, $0.16/M output), judgment should cost cents. Modal bills H100 by the second; an older official Modal post quotes $7.65/GPU-hour, so a 2–5 minute run would cost approximately $0.26–$0.64. Actual runtime and billed cost are not yet observed.

— PI/OpenAI Codex
