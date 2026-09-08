# Final-prompt judge blocker

PI/OpenAI Codex, 2026-09-08.

The first final-prompt J-lens judgment process ended before any provider call with `KeyError: '+C'`. The new experiment intentionally has only the `-C` cell, but `scripts/judge.py:experiment_rows` iterated both sides unconditionally.

Fix: build DEV/all-generated candidates only from nonempty `manifest["cells"]` entries, and fail clearly if an explicit absent `--side` is requested. Host check after the fix reports:

> `SPARSE_SIDE_JUDGE_PASS rows=15 side=-C`

This is a runner compatibility fix. It does not change the rubric, records, scores, or selection rule. The failed process did not spend judge provider calls. The replacement judgment will use the same unchanged command after this commit.
