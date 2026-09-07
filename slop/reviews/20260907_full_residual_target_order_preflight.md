## Review

- Correct: Projection-specific operator, representation, spec digest, source hash, and sample identity prevent GP16/full-residual cache collisions (`src/vjp_steering/j_lens_concept.py:27-28,59-82`; `scripts/experiment.py:271-292,392-415`).
- Correct: The actual full-residual basis uses independently normalized positive-minus-baseline and negative-minus-baseline final-prefill signals (`src/vjp_steering/j_lens_concept.py:641-659,687-697`). GP16 remains only for comparative diagnostics/metadata, not as the applied basis.
- Correct: `+C` and `-C` retain target indices 0 and 1 and use the unchanged target-order coordinate exchange (`src/vjp_steering/j_lens_concept.py:211-257,692-697`).
- Correct: Source prompts, fixed split, layers, DEV cohort, calibration grid, and judge path remain unchanged. CLI and Modal extraction/calibration propagate `persona_direction` (`scripts/experiment.py:105,223-316`; `scripts/run_modal.py:115-123,355-369,383-418`).
- Correct: Metadata explicitly calls this a “non-J full-residual control,” not paper-native (`src/vjp_steering/j_lens_concept.py:809-815`).
- Correct: Tiny smoke exercised extraction, reload, both targets, generation, judge, and export; the separate basis check confirmed the saved basis exactly equals normalized full signals and differs from GP16 (`slop/logs/20260907_j_lens_full_residual/v16-basis-check.log:1`; `slop/logs/20260907_j_lens_full_residual/v16-smoke.log:11-56`).

No issues found.

- Merge verdict: **OK**

— PI reviewer/OpenAI GPT-5.6 Sol
