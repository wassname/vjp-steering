# Actual v16 concept patch replay

Authored by PI/OpenAI Codex. CPU-only; no API/GPU cost. The comparison plot/table remains unfinished.

## Result

`cpu-replay-verified.log` ends with `"decision": "ACTUAL_V16_COMPONENT_REPLAY_PASS"`, `"patch_cases": 108`, `"hook_cases": 36`, and `EXIT_CODE=0`. Full per-case coordinates and errors are in `cpu-replay-verified.json`.

Actual saved calibration vectors: `outputs/experiments/j-lens-persona-full-components-calibration-v16/extraction/{plusC,minusC}.safetensors`. Plus content hash `1cb043932c0ddd676d1953ef5368fe9744f6878ed002f6c46cb730d9df4cc401`; minus `313bf2a731baf804129cf4036d1321abe915b1abbb6e59870901c658779ce3a5`. Both are checked against extraction metadata. Actual production module bytes match `c670930:src/vjp_steering/j_lens_concept.py`.

Both saved basis and dual are float32 at every layer 13–21. Positive/negative row identities are checked independently against normalized saved full signals, not just target-index conventions. Maximum row reconstruction difference is 2.9802322387695312e-08. Largest stored-dual Gram identity error is 3.5762786865234375e-07. The script solves the two-row Gram system in float64 rather than using the stored dual or production target-sort function as its reference.

Each of 108 calls tests five positions: two positive and two negative unequal coordinate pairs with orthogonal residual plus exact zero. This is 540 position comparisons across nine layers, two sides, two dtypes and alpha=0/1/2. An actual wrong-target mutation and actual alpha0 no-op disagree with the nonzero reference. Thirty-six actual hook contexts test attended-position masking and first-call removal on identity blocks. They are not real-model forwards.

| dtype | maximum output difference from float64 oracle | maximum recovered-coordinate difference | maximum output difference from independently staged rounding |
|---|---:|---:|---:|
| FP32 | 4.804136818359339e-07 | 2.876823859798705e-06 | 4.76837158203125e-07 |
| BF16 | 0.004473363869297087 | 0.0014444606312284947 | 0.00048828125 |

Output error is checked against a dtype/operand-magnitude rounding bound, not asserted exactly zero. All alpha0 and already-ordered identity assertions remain bitwise. Numerical parity does not prove semantic transfer; synthetic states do not exclude cancellation at model-scale activations or GPU kernel differences.

## Failed fixture and correction

- `cpu-replay.log`: unmatched closing parenthesis in the newly authored replay script; fixed without production edits.
- `cpu-replay-rerun.log`: exact `assert torch.equal(actual[ordered], hidden[ordered])` failed.
- `cpu-replay-tie-failure-reproduced.log`: deliberate reproduction with original fixture and diagnostic values. At layer14/-C/FP32/alpha1, final row reference coordinates are `[3.8928331062799716e-10, 7.226649256167439e-10]`; production coordinates `[7.450580596923828e-09, 2.561137080192566e-09]` reverse their ordering. Output changes by `4.656612873077393e-10`.
- Exact fixture diff: add `hidden[-1].zero_()` after casting the constructed hidden array. This gives an actual exact tie, while retaining nonzero orthogonal residual on four unequal cases. The assertion was not weakened. A pre-cast float64 orthogonality residual around 1e-17 was not the actual FP32 coordinate residual and is not used as evidence.
- `cpu-replay-final.log/json` are first successful results; `cpu-replay-verified.log/json` repeat success after strengthening negative controls to call the actual production patch with a wrong target and alpha0, and adding the reproducible failure flag. All logs are retained, not overwritten.

## ml-debug form

| Row | Evidence |
|---|---|
| Log/config | Verified log: command, four SHOULD lines, nine layer summaries, final summary, exit0; CPU, saved v16, FP32/BF16, alpha0/1/2. |
| SHOULD vs observed | Saved row/target assertions, independent exchange comparisons, real hook assertions and wrong-target/no-op controls all precede `V16_ACTUAL_REPLAY_COMPLETE`. |
| Null scale for numbers | Exact mathematical output/coordinate error is zero; FP32/BF16 rounding generates nonzero errors above. Alpha0 identity is bitwise zero. These are numerical errors, not behavioral metrics. |
| Initial demo | Five synthetic coordinate pairs `[3,1],[1,3],[-1,-3],[-3,-1],[0,0]`, saved basis and residual; no training update. |
| Dummy comparison | Wrong-target production mutation and no-op each differ from intended nonzero output by >0.01; chosen coordinate gap is 2. This is a trap for missing or reversed intervention, not a scientific threshold. |
| Baseline/held-out | No behavioral inference; all comparisons share input/vector. No validation/held-out model evaluation occurs. |
| Schedule | No optimizer or learning rate. |
| Full sample | `cpu-replay-verified.json`, first case and adjacent alpha1/2 cases: complete pre/expected/recovered coordinates; fixture input construction and seed are in script and JSON. |
| Worst step | Original exact identity assertion on a nominal numerical tie, with values above. No gradients/loss. |
| Surprise | `ORDERED_IDENTITY_FAILURE` despite float64 pre-cast orthogonality; explained by casting and differing dot products reversing ~1e-9 residual order, followed by a tiny update. |
| Missing evidence | Real activation-range inputs, real Qwen forward, sequential layer composition and causal behavior, independent review of this replay. |
| Diagnoses | Post-replay working priorities, not calibrated probabilities: representation/operator mismatch 60%; judge partial-denial overcredit 25%; actual untested model-scale numerical/hook defect 10%; unknown 5%. Passing synthetic replay and saved identities weigh against simple target reversal; no real-forward replay leaves the numerical hypothesis untested at natural scales. Raw-response anchors remain in v10/task462 audit. |
| Fresh review | Parent owns recovered MoA scientist pilot/independent reviews. No nested agents or paid calls started here. |
| Cheapest separator | Replay lowers simple mapping/dtype bug priority. Parent scientific review should select an actual-behavior test, rather than treat this numerical result as proof of representation success. |
| Runtime/memory | Timing after imports is saved in JSON. CPU only; CUDA not used. Import/model-download overhead absent from interpretation. |

## Next experiment recommendation, not executed

Strongest paper-grounded next direction is a bounded on/off test of the paper's unconditional coordinate exchange versus our target-ordering adaptation, with source identification and patch positions tied to a verified active representation on the actual benchmark prompt. Keep actual hook execution and saved sources fixed for the first operator-only comparison if scientific review agrees, so any difference identifies the sorting change rather than a new vector. A final-prefill-only source applied to every attended position is also an explicit source/application mismatch, but changing both operator and positions at once would confound attribution. Neither candidate is approved or implemented here. Parent must review the paper's exact intervention and predeclare a narrow behavioral test; this replay alone cannot choose useful tokens or promise effects beyond random.
