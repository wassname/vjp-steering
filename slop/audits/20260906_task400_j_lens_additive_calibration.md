# Task 400: additive calibration is obsolete

Task 400 completed 22 one-prompt cells for the v6 additive intervention. The full log is [`task-400-full.log`](../logs/20260906_j_lens_native/task-400-full.log).

Observed:

- `+C` passed the repetition and completion checks through `C=4`.
- `-C` repeated at `C=0.5` and `C=1`, but produced fluent refusals at `C=2` and `C=4`. The automated health result was therefore non-monotonic and did not define a semantic boundary.
- The log records `CONCEPT_CALIBRATION_COMPLETE ... cells=22`.

This result cannot calibrate the paper's reported concept-component experiment. V6 added each component separately. The paper reports coordinate swapping with the two components. The next version must use the coordinate exchange, non-negative gradient-pursuit reconstructions, all attended prefill positions, and more than one prompt.

The public results were not changed.

— PI/OpenAI Codex
