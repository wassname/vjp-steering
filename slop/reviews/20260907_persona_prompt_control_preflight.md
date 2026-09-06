## Review

### Correct

- Prompt construction is correct: `generation_inputs()` prepends `Answer as someone who is {persona}.` in the same user turn, preserves the benchmark prompt and two-sentence instruction, and disables thinking (`scripts/walk.py:435-447`).
- The controls use the exact existing persona strings: `+C → "sycophantic"` and `-C → "abrasive"` (`scripts/concept_checks.py:248-252`). These agree with `walk.PERSONAS`.
- Side/sign semantics are coherent. Both controls use positive magnitude `1.0`, while side determines the judge target; export subsequently signs `-C` effects negative. This matches the existing target-ordered experiment convention.
- Bare generation is performed once and referenced for both comparisons (`scripts/concept_checks.py:242-267`). The judge similarly loads one bare file and pairs it by scenario with both cells (`scripts/judge.py:237-293`).
- The manifest is judge/export compatible: DEV-15 profile, two complete cells, relative artifact paths, health data, cohort hash, model metadata, and an extraction-shaped section (`scripts/concept_checks.py:276-301`). The tiny artifact confirms 15 bare, 15 `+C`, and 15 `-C` records.
- Random-model incoherence is expected. The tiny log proves all three generation arms completed (`slop/logs/20260906_j_lens_native/persona-prompt-control-tiny.log:2-7`), and the manifest correctly records the unhealthy random outputs rather than hiding them.
- The control cannot enter primary publication CSVs automatically. Experiment export writes under `data/dev/<experiment-id>` (`scripts/export.py:328-355`), while the primary export path writes `data/results.csv` separately. Discovery of legacy public runs is also restricted to fixed methods and `run_*` artifacts (`scripts/judge.py:170-185`).

### Findings

- **P1 — Interrupted Modal runs cannot resume.**
  `persona_prompt_control()` rejects any existing experiment directory before invoking the resumable `extend_generation()` path (`scripts/concept_checks.py:237-245`). Modal commits the volume even when the subprocess fails (`scripts/run_modal.py:98-105`). Therefore, interruption after bare or one control leaves a persisted partial directory that every retry rejects. This is particularly risky for the real-Qwen run.
  **Smallest fix:** permit validated partial directories and reuse completed JSONLs, while rejecting completed or configuration-mismatched manifests.

- **P1 — The dedicated Modal command stops before the existing local judge/export path is usable.**
  The entrypoint only invokes `run_experiment.remote()` and prints part of the returned manifest (`scripts/run_modal.py:124-130`). It does not pull the experiment directory from `jsteer-pub-cache`; judge and export read local `outputs/experiments/<id>` (`scripts/judge.py:237-240`, `scripts/export.py:247-250`). Thus the advertised command can generate remotely, but the requested generation → judge → export flow requires an undocumented/manual volume pull.
  **Smallest fix:** reuse the existing Modal artifact-pull step, or provide an explicit orchestration command that pulls before invoking judge/export.

- **P2 — The tiny smoke covers generation and serialization only.**
  Its log shows model loading and three generation completions, but no Modal invocation, artifact pull, judge, export, or resume test (`slop/logs/20260906_j_lens_native/persona-prompt-control-tiny.log:2-7`). No corresponding `data/dev/j-lens-persona-prompt-control-tiny-v1` export exists. Static inspection shows the manifest should produce 30 DEV judge rows, but that path was not exercised.

### Real-Qwen readiness

A fresh-ID Qwen DEV-15 generation should run on the Modal H100: the invocation snapshots the requested model, routes to the persona-control branch despite the added `--gpu-stage`, generates exactly three 15-row cohorts, and commits the manifest. It is **not yet robustly end-to-end runnable** because partial runs are non-resumable and the dedicated command does not retrieve artifacts for local judging/export.

Supervisor should validate after fixes with a fresh real-Qwen ID, interrupt/retry once after a completed control, pull the artifact, then run the existing DEV judge and export commands.

### Merge verdict: BLOCK