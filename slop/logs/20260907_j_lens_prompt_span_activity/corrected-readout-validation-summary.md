# Corrected readout validation

Implementation complete; review and complete CPU validation remain required before Modal. No GPU or judge calls ran.

## Changes

- Primary score_records and bridge share j_lens_scores: float32 h @ J.T, cast to head dtype/device, actual model.model.norm, lm_head (including bias), optional tanh softcap, float32 output. Raw W_U @ J still defines pair geometry and pseudoinverse coordinates.
- Companion lens.py/hf.py hashes are checked before apply. The reference source is unchanged. force_bos=False preserves rendered chat; requested positions and full input token IDs are checked.
- Both artifacts identify corrected readout semantics with v2 schema. Existing output files are refused. Qwen lens bytes must match task465. Modal resolves the exact task465 model revision, not mutable model HEAD.
- Companion installation uses --no-deps in a diagnostic-only image; the shared image no longer installs it. Remote outputs commit in finally. A bridge mismatch saves its diagnostic then exits nonzero; a failed Modal call's artifact can be recovered from the volume.

## Observed outputs

Full first run: corrected-readout-cpu-first.log. Command: OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1 PYTHONPATH=src:/home/code/.cache/uv/git-v0/checkouts/41f7024740f025b9/581d398 timeout 600 .venv/bin/python scripts/j_lens_prompt_span_activity.py --companion-self-test. Shell reported EXIT=124.

Quoted lines:

```text
J_LENS_PROMPT_SPAN_ACTIVITY_SELF_TEST_PASS
CORRECTED_PRIMARY_READOUT_PASS cells=90 raw_top1_different_layers=16
CORRECTED_READOUT_DTYPE_BIAS_SOFTCAP_PASS dtypes=float32,bfloat16
AssertionError
```

This is not a full passing run. The final exact-rank comparison of primary results against companion failed, after bridge parity had passed its assertion. The test had converted its reused model to BF16 then restored only persistent state. Qwen rotary buffers are nonpersistent, so that test could change its reference model. The final test isolates dtype conversion on a deepcopy instead; this explanation remains unconfirmed by rerun.

Bounded final rerun: corrected-readout-cpu-validation.log. It timed out at 180 seconds with EXIT=124 before any self-test marker. An earlier bounded faulthandler probe of plain import transformers showed importlib.metadata.packages_distributions -> _top_level_inferred -> files -> skip_missing_files -> pathlib.exists/stat. No library or environment files were modified to work around this. Per supervisor instruction, environment investigation stopped.

Static validation: corrected-readout-static-validation.log. Compile and diff checks pass. AST comparison to HEAD confirms all frozen scoring selection/mask/random/prompt functions and constants remain unchanged; only decoded scores change. AST checks confirm dependency isolation. No staged files.

## ml-debug (bounded implementation test)

| Row | Evidence or unknown |
|---|---|
| Log/config | First CPU log contains tiny random Qwen3.5 warning, three passing markers, then traceback; exact command above. Final rerun log has command and EXIT=124 only. |
| SHOULD and observed | No SHOULD claim was inserted. The primary test requires nonuniform norm to change raw rankings; observed raw_top1_different_layers=16. |
| Null for cited metrics | Old raw readout is the null. Exact primary comparison tests 90 cells; raw top1 differs in 16 of 18 prompt/layer groups. No behavioral statistic is estimated. |
| Initial demo | No training or behavioral demo; tiny random weights only. |
| Dummy at stages | Old raw ranking is explicitly rejected by the fixture; no judge or learning stage. |
| Baseline/held-out | Not measured; this tests mechanics, not scientific coverage. |
| Learning schedule | Not applicable; no optimizer. |
| Full sample | Embedded fixture: prompts token17 token18 and token19 token20 token21; toy whitespace tokenizer, real tiny Qwen3.5 forward, real request masks and primary scorer. It does not replace the real Qwen tokenizer/weight check. |
| Worst step | Exact primary/companion rank assertion; traceback in first CPU log. No gradients. |
| Surprise | Primary and dtype/softcap checks pass but later exact ranks differ; test model mutation is suspected, not established. |
| Missing evidence | Passing final CPU companion test, existing experiment selftest rerun, Modal image import/build, real-Qwen parity. |
| Diagnoses | For failed final rank assertion: fixture dtype mutation 65% (persistent-only restore; no confirmed rerun), numerical batch/mask differences 20% (batched primary versus single companion; full logits were close), production readout defect 10% (independent primary formula and bridge passed, but incomplete verification), unknown 5%. These are debugging priorities, not calibrated probabilities. |
| Fresh review | Parent owns scheduled native reviewer; not yet reviewed. No nested agents launched. |
| Cheapest discriminator | Run final --companion-self-test once imports work. If rank assertion remains, print candidate IDs/ranks/logit differences and compare single versus batched capture before interpreting it. |
| Runtime/memory | First command bounded at 600s; final command at 180s. GPU memory not applicable. Import delay dominates this validation environment. |

— PI/OpenAI Codex
