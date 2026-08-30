# Fresh-eyes review: formative per-side MLP-up report

- reviewer: pi builtin `reviewer`
- initial run: `612df5e9-4e0c-4723-a23c-d253cdf5ba06`
- resumed run after fixes: `d2a34c33-441b-4330-9c64-8dbec8c0245f`
- session transcript: `/home/code/.pi/agent/sessions/--workspace-2026-jspace-j-steer_pub--/2026-08-27T01-23-11-091Z_01a040d0-5873-7fb3-9e57-13b7a96fd8bb/353e6f72-5180-4f61-8091-d4f2a69ba403/run-0/session.jsonl`
- reviewed files: `results/formative/mlp-up-left-right-formative-v1/plot.png`, `index.md`, `data/formative/mlp-up-left-right-formative-v1/selected.json`, `src/vjp_steering/results.py`, and `scripts/experiment.py`

## Initial observations — reviewer

> **Finding: P1 — rejected candidates are materially misclassified.** The two `+C` rows have wrong-sign effects (`-0.401`, `-0.404`) [...] Consequently, `plot.png` renders both rejected `+C` candidates as filled markers with no rejected label, while `index.md:11` reports `rejected = 0` instead of `2`.

> **Finding: P2 — endpoint annotation overlaps the y-axis tick.** In `plot.png`, “per-side VJP -C” obscures the `0.3` tick, producing the visible merged text `0per-side VJP -C`.

> **Merge verdict: BLOCK** — the published figure/table do not honestly show the two rejected `+C` candidates.

## Fix and final observation

The report was regenerated after directional acceptance was added to marker fill, hover text, and rejection counts, and the near-left endpoint label was forced inward. The final table reports `rejected = 2`, no `+C` endpoint, and no bilateral score. The final plot uses open circles for both wrong-direction `+C` candidates.

The same reviewer then re-read the regenerated plot and table and returned:

> PASS

— evidence assembled by PI/OpenAI Codex; reviewer statements quoted verbatim
