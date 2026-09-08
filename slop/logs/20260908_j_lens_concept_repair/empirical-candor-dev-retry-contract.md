# Empirical-candor DEV corrected retry contract

PI/OpenAI Codex, 2026-09-08. This is one explicit corrected retry after task 795 failed before generation. It is not an automatic retry, full evaluation, public update, or goal sign-off.

Task 795 reused the frozen v8 source correctly, then failed in generic layer selection because component vectors serialize basis tensors in `shared` and omit empty `stacked` tensors. The corrected selector now preserves the component shared layout and the additive stacked layout explicitly. The preflight loads both frozen component directions and a saved additive vector, selects full and subset layers, and verifies all corresponding tensor hashes.

| field | fixed value |
|---|---|
| experiment | `j-lens-components-empirical-candor-dev-v1` |
| source | `j-lens-behavior-components-target-ordered-source-v8` |
| source vector SHA256 | `dd4e78e9c429e51e4fe2d4e70e0db28c96d5c4c218b5f317767393ac38883197` |
| source side / behavior target | `+C` / `candidness` |
| operator | `mean100-gp16-reconstruction-target-ordered-coordinate-exchange-all-prefill-v8` |
| layers / alpha / mask | 13-21 / `.5` / all attended prefill positions |
| arms | fresh bare, source, seeded rank-two source-Gram-preserving control |
| control seed / target index | `20260909` / 0 |
| cohort | unchanged DEV-15, same order |
| remote bound | one H100 container, 900 seconds, no automatic retry |
| queue | pueue `modal`, one slot |
| retry reserve | $3.00, separate from task795's retained $0.50 unknown-cost reserve and the $18.00 full reserve |

If generation succeeds, save complete logs, manifest, raw JSONL, pueue/Modal status, and metered cost; audit all responses and realized source/control patches; then judge candidness in AB and BA and obtain endpoint review. If generation fails, save its complete evidence and stop without another retry. Full all-100 and public artifacts remain blocked pending Goal 1 review.
