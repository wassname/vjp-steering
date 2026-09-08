**SOURCE_GATE_BLOCKED**

**Correction:** My prior description that the model "genuinely selects the action from whichever policy clause is listed first" was overstrong. The `first-policy-check.json` shows only 248/384 (64.58%) matches to the first-policy-branch action, so the output is not explained by that simple heuristic alone.

That correction does **not** affect the clean-gate block. The decisive evidence remains the `CLEAN_GATE` record in `generation.json` (also printed in `pueue-705-clean.log`): `"pass": false`, `"minimum_accuracy": 0.425` (required ≥0.90), and `"strict_semantic_cases": {"passed": 1, "total": 96}` (required 96/96). Both predeclared conditions independently fail, so the clean gate is not met, intervention was correctly prevented, and the source-stage stop is valid.