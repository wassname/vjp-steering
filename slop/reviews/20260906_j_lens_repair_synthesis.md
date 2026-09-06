# J-lens repair review synthesis

— PI/OpenAI Codex

## Shared conclusion

The four reviews converge on one issue: the fixed pair does not satisfy the paper's active-source condition. The paper swaps an item the model already chose; this benchmark intervention swaps two hand-picked words without first showing that either is active.

GLM's seminar review states:

> “Candidate B's source-selection rule (median J-lens rank ≤ 25 across layers) is *not* the paper's ‘spontaneously chosen item.’ The paper identifies the model's actual output; Candidate B identifies high J-space activity on a hand-picked assessment lexicon.”

DeepSeek's independent review adds a task-level objection:

> “In the paper's tasks, the swapped tokens are object-level answers (e.g., cities, animals), so emitting the target token is the goal. In sycophancy, emitting the word ‘flattering’ is not the goal; behaving flatteringly is.”

Both are inferences from the paper evidence, not new experimental observations.

## Decision

1. Complete the already-running layers 13–21 fixed-pair diagnostic. Task 333 has now done this and both selected points remain inside the random cone.
2. Measure actual next-token ranks, J-lens ranks, swap coordinates, and pair conditioning for the fixed pair and the pre-registered assessment lexicon on all 100 clean prompts.
3. Do not run Candidate B if its source tokens are absent from the model's actual next-token distribution. J-lens activity alone is not the paper's observed output criterion.
4. If the lexicon is inactive, test separate paper-style concept J components with matched full-vector, non-J, and random-J controls. Do not represent the second benchmark direction with negative scaling of the same symmetric swap.

## Added checks

The reviews identified checks missing from the initial pseudocode:

- actual softmax rank, not only `Dℓ @ h` rank;
- per-layer pair condition number and clean pseudoinverse coordinates;
- explicit literal lens-token emission;
- random J-lens rows, not only Gaussian residual directions;
- monotone dose response before damage, not one selected point outside the cone.

## Disagreement

The first independent GLM review preferred the fixed-pair layer diagnostic before Candidate B. Its seminar pass preferred Candidate B directly. This is now resolved by task 333: the layer-only change did not leave the random cone, so source activity is the next discriminating measurement.
