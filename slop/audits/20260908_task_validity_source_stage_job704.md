# Audit: source-stage pueue job 704

Target: pueue job 704, `why: test whether frozen v3 closed-rule source states support a specific GP rank-one causal handle; resolve: stop at source gate or save reviewed evidence before any benchmark transfer`.

Provenance: job 704 ran `uv run modal run scripts/scratch/j_lens_task_validity_source_stage.py::launch` in `/workspace/2026/jspace/j-steer_pub`. `pueue-status-after-704.json` records start `2026-09-08T10:20:23.323770792+08:00`, end `2026-09-08T10:21:05.812759296+08:00`, and `Failed: 1`. Its only Modal app, `ap-FAW0E4RXpgmbCm1yMZPYnL`, is stopped with zero tasks. The full cleaned log has 130 of 130 lines in [pueue-704-clean.log](../logs/20260908_j_lens_task_validity_source_stage/pueue-704-clean.log). [launch-attempts.md](../logs/20260908_j_lens_task_validity_source_stage/launch-attempts.md) proves the earlier rejected `--follow` command did not create another job or app.

| stage | expected | observed | expected? | clues | missing metric | consequence |
|---|---|---|---|---|---|---|
| queue/app uniqueness | one source-stage job and app | one failed job 704 and one stopped app | yes | `launch-attempts.md` | cost receipt | no duplicate spend/run |
| image construction | runner, corpus, tokenizer preflight, and protected files available | runner/corpus/freeze/preflight mounted, protected files absent | no | full log mount list and traceback | image content hash | runner cannot create initial artifact |
| pinned model load | pinned 4B weights load | all 426 weight shards loaded | yes | full log `Loading weights: ... 426/426` | model config/source hashes in artifact | setup reached model load |
| clean source generation | 384 saved records then strict gate | zero records | no | `FileNotFoundError: results/plot.png` | clean outputs/gate | no source-state claim |
| intervention and controls | only after clean gate | not entered | no | traceback occurs before loop | all causal metrics | no causal claim |
| benchmark release | false | no benchmark command or judge call | yes | command and traceback | none | benchmark remains blocked |

## Primary evidence

## Job 704 clean log — [pueue-704-clean.log](../logs/20260908_j_lens_task_validity_source_stage/pueue-704-clean.log)
- time: 2026-09-08 10:20 to 10:21 +08:00; local pueue capture of the executed Modal process.

The mount list is the direct evidence of what the remote image contained.

> ├── 🔨 Created mount `slop/logs/20260908_j_lens_task_validity_source_stage/preflight.json`
> ├── 🔨 Created mount `slop/logs/20260908_j_lens_task_validity_corpus/v3/freeze.json`
> ├── 🔨 Created mount `slop/logs/20260908_j_lens_task_validity_corpus/v3/corpus.jsonl`
> ├── 🔨 Created mount `/workspace/2026/jspace/j-steer_pub/src`
> ├── 🔨 Created mount `/workspace/2026/jspace/j-steer_pub/scripts`
> ├── 🔨 Created mount `/workspace/2026/jspace/j-steer_pub/data`
> └── 🔨 Created function remote.

Epistemic context: raw tool output from the only launched app.

The expected protected result files were not mounted.

The model itself loaded before the failure.

> Loading weights:  83%|████████▎ | 353/426 [00:01<00:00, 214.05it/s]
> Loading weights: 100%|██████████| 426/426 [00:01<00:00, 222.95it/s]
> Traceback (most recent call last):
>   File "/repo/scripts/scratch/j_lens_task_validity_source_stage.py", line 344, in run
>     "protected_sha256": {str(path): sha(path) for path in PROTECTED}, "clean": [], "interventions": {}, "benchmark_released": False}

Epistemic context: raw remote stderr/stdout produced after pinned-weight loading.

The causal error is explicit.

> FileNotFoundError: [Errno 2] No such file or directory: 'results/plot.png'
> subprocess.CalledProcessError: Command '['/.uv/.venv/bin/python', 'scripts/scratch/j_lens_task_validity_source_stage.py', '--output', '/cache/outputs/audits/20260908_task_validity_source_stage/generation.json', '--source-revision', '43fedadf1414efd5d416837bdb26a0f5adeb6f8d']' returned non-zero exit status 1.
> Stopping app - uncaught exception raised locally: CalledProcessError(1, ['/.uv/.venv/bin/python', 'scripts/scratch/j_lens_task_validity_source_stage.py', '--output', '/cache/outputs/audits/20260908_task_validity_source_stage/generation.json', '--source-revision', '43fedadf1414efd5d416837bdb26a0f5adeb6f8d']).

Epistemic context: raw remote exception and local Modal transport exception, not an inferred diagnosis.

## Hypotheses

### H1 [bug | Almost Certain | 98%]

- **Mechanism:** the custom Modal image mounts corpus/preflight but not `results/` or `scripts/judge.py`, while the runner hashes those files before its clean loop.
- **Evidence:** the mount quote omits `results`; the traceback quotes `FileNotFoundError ... results/plot.png` at the protected-hash comprehension.
- **Contrary evidence:** none in the complete log. The remote working directory could contain an unlisted mount, but the missing-path exception rules that out for `results/plot.png`.
- **Discriminating test:** inspect the image construction and run a no-GPU container preflight that reads every protected path. H1 predicts this fails before the fix and passes after mounting the protected files.
- **Fix/action:** add the five protected files to the source-stage image, then rerun local preflight/fixture and obtain a fresh source-stage authorization before any new job.
- **Interpretability:** no. The job did not reach a source generation.

### H2 [harness | Likely | 65%]

- **Mechanism:** a corrected image may reveal a second remote-only dependency error, because the runner has not executed its clean loop in the Modal container.
- **Evidence:** the failure was before `CLEAN_RESPONSE`; only model loading exercised the remote environment.
- **Contrary evidence:** corpus, freeze, preflight, scripts, src, and data mounted successfully, and all 426 model shards loaded.
- **Discriminating test:** a remote preflight-only entrypoint that verifies every mount, tokenizer hash, and J-lens dependency without starting the generation loop. H2 predicts a second failure only if another dependency is absent.
- **Fix/action:** make remote preflight part of the next single bounded job and save its output before clean records.
- **Interpretability:** partial. The model image can load weights, but the full runner is unverified.

### H3 [data | Chances a little better than even | 48%]

- **Mechanism:** the corpus has 384 rows but only 336 unique rendered inputs, so repeated inputs reduce effective source evidence and can interact with the strict all-mirror gate.
- **Evidence:** [preflight.log](../logs/20260908_j_lens_task_validity_source_stage/preflight.log) reports `"rendered_inputs": 384, "unique_rendered_inputs": 336, "duplicate_rendered_inputs": 48`.
- **Contrary evidence:** duplicates have a consistent expected semantic label by the preflight assertion; v3 documentation already treats mirrored variants as nuisance controls rather than independent worlds.
- **Discriminating test:** the saved clean records can group duplicate rendered IDs and report token/text identity before any interpretation. A consistent duplicate result is expected; disagreement would indicate generation nondeterminism or record mapping error.
- **Fix/action:** add this duplicate-group receipt to the successful-run audit. Do not change the frozen corpus after the result.
- **Interpretability:** partial. It affects effective sample size, not this crash.

## Decision

**Resolve-condition verdict: not met.** The job was intended to "stop at source gate or save reviewed evidence before any benchmark transfer," but it stopped before the source gate and saved no source output.

**Validity:** invalid as a source-state experiment, P(result invalid) approximately 0.98–0.99. It is a credible infrastructure failure, not a behavioral null or a negative result for J-space.

**Three highest-information clues:**

1. The exact missing file names the localized image defect.
2. The 426/426 weight-load line rules out model download/load failure as the immediate cause.
3. The app list and pueue status show one stopped failed app, so duplicate execution does not explain the result.

**Missing metrics, by information gain:** complete clean records and strict gate; remote mount preflight; source decomposition; intervention/identity/random comparisons; Modal billing receipt.

**Recommended sequence:** preserve job 704 as failed evidence. Correct the missing protected-file mount and add a remote mount receipt, then re-run local fixture/preflight. Do not enqueue again until that changed runner is reviewed as a new bounded launch decision. Do not release DEV/full generation or judging.

## Epistemic summary

- **Who says what:** pueue and Modal logs directly report the executed command, mount list, model load, and exception.
- **How they could know:** these are runtime observations, not researcher interpretation.
- **Entanglement check:** all crash evidence has one origin, job 704. It establishes the failure mechanism strongly but does not independently validate the corrected image.
- **Hard-to-vary check:** a model/science failure would not naturally produce `FileNotFoundError` for a protected local path before the first clean response.
- **What would change the conclusion:** a saved remote preflight showing the path exists and a later error at a different stage would lower H1 and raise H2.
- **Calibrated take:** Almost Certain that job 704 provides no source-state evidence. The cheap way to be wrong is to mistake successful model loading for successful generation.
