REQUEST CHANGES.

The revised plan is close, but two gaps remain.

1. Plot and smoke-check ownership is still ambiguous. R3 says the notebook draws the result plot; R4 says one measured CSV generates the plot. R5 then says a fresh clone runs “the smoke check and renderer,” not the notebook. Clarify the sole plot generator and exactly which artifacts the fresh clone must recreate. If the notebook output must be reproduced, provide an isolated tiny-model notebook path or commit the all-100 measured CSV and have R5 run only the renderer. As written, “recreate every generated result” is not falsifiable.

2. The plan lists “Markdown and HTML disagreement” as a likely failure, but no check explicitly fails on it. Add an automated equivalence check between `results.md` and `results.html` (e.g. render Markdown to plain text and compare all records), and record it as part of R4 or R5.

Also add a source inventory for scope-out items; the `<2000` line count alone does not prove old variants or the new evaluation framework were deleted.