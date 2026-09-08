## Review

- Correct: The decision properly treats “discussion/detection/evaluation” as an inference, explicitly saying it is “not an established mechanism” (`representation-comparison-decision.md:58`). The topic-only source and `Tell me about {text}` extraction template support that caution.
- Correct: Dose/layer, raw-response, and matched random-control claims are supported: all-layer and lower/middle `.125` are negative on both sides; upper `.125` is equal at `+.0733`; final-prompt `.25` is only `+.0333` above random-minus with 11/15 byte-identical outputs.
- Correct: The no-paid-launch budget conclusion follows exactly: `$3.40106842 + $18.00 + $18.59893158 = $40.00`; the $18 full-endpoint reserve is explicitly retained and not authorized (`budget.json`).
- Finding: P2 — The blanket claim “There is no bounded current-route repair supported” (`representation-comparison-decision.md:85`) omits an already evidenced bounded harness repair. The cited exact-flaw audit states: “answer-key edits can leave cohort hashes and judge cache keys unchanged, reusing stale judgments,” with the smallest fix: “include exact flaw text in judge cache identity and persist its hash separately.” It also says “no stale reuse is observed here,” so this does **not** support a paid DEV launch or invalidate these results; it should be recorded as required provenance work before future judging.
- Finding: P2 — The exclusion of “another upper C=.125/C=.25 user-turn or final-prompt test” (`representation-comparison-decision.md:72`) is broader than its cited final-prompt evidence. `final-prompt-judgment-summary.log` documents only `-C, .25`; the audit refers generally to prior `.125/.25` results but does not identify or substantiate the asserted user-turn endpoint in the cited material. Cite that saved endpoint artifact directly, or narrow the exclusion to the evidenced final-prompt `.25` test.

- Merge verdict: **REVISE** — retain the no-launch decision, but qualify the absolute “no bounded repair” statement and tighten the endpoint-exclusion citation.

**Paid DEV launch supported: No.**
