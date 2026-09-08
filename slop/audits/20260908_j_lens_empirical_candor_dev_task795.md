# Task 795 empirical-candor DEV audit

PI/OpenAI Codex, 2026-09-08. Task 795 failed before generation. It produced no raw responses, no judgments, no plot update, and no endpoint selection.

## Evidence

`slop/logs/20260908_j_lens_concept_repair/empirical-candor-dev-task-795-live.log` has all 147 clean pueue lines. It records Modal app `ap-eP3e05VeeCNztul5R3mkVZ` and remote task `ta-01M208CED2DYKJSN9N486ADHNR`.

> `EMPIRICAL_COMPONENT_EXTRACTION_REUSED source=j-lens-behavior-components-target-ordered-source-v8 hash_plus=dd4e78e9c429e51e4fe2d4e70e0db28c96d5c4c218b5f317767393ac38883197`

> `KeyError: 13` at `select_concept_layers`, while evaluating `vector.stacked[layer]`.

Pueue records task 795 as `Failed: 1`, start `18:17:46`, end `18:18:22`, in `empirical-candor-dev-task-795-checkpoint.json`.

## Interpretation

The historical component vectors serialize their component basis in `shared`; their empty `stacked` states are absent after reload. The generic layer selector treated every concept vector as additive and indexed nonexistent stacked entries. This is a runner bug, not evidence against the frozen source vector or the empirical-candor hypothesis.

The corrected selector retains selected `shared` component states and supplies an empty stacked tree for a component-pair vector. The updated offline preflight now loads the frozen v8 safetensors, applies full-layer selection, and verifies the vector SHA remains `dd4e78e9c429e51e4fe2d4e70e0db28c96d5c4c218b5f317767393ac38883197`.

## Competing explanations

| possibility | support | contrary evidence | status |
|---|---|---|---|
| component selector assumes additive stacked tensors | exact `KeyError: 13`; source reused before failure | corrected selector and full preflight pass | likely, about 95% |
| frozen source cache is missing or corrupted | failure occurs after reuse | logged source hash matches frozen hash | unlikely, about 3% |
| Modal or pueue failure | task ended nonzero | Modal reached Python code and reported the local traceback | unlikely, about 2% |

## Decision

Keep the empirical-candor DEV result absent. Do not judge or render. The code correction and preflight are saved, but task 795 is not retried automatically. Its metered Modal cost is unknown and remains within the existing $3 DEV reserve until a provider receipt is saved. The conditional $18 full reserve remains untouched.
