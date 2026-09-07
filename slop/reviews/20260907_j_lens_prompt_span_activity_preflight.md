## Review

### Correct

- The frozen seven pairs and order are unchanged, with one-leading-space single-token and round-trip validation (`scripts/j_lens_prompt_span_activity.py:19-28,62-77`).
- The scored workspace is exactly layers 13–21 (`scripts/j_lens_prompt_span_activity.py:18,398-400,657-661`).
- Original and explicit-validity contexts use the required chat template. Only tokens wholly contained in the exact `row.prompt` character span are selected; boundary-crossing tokens, padding, wrappers, instructions, and suffixes fail validation (`scripts/j_lens_prompt_span_activity.py:80-153,301-357`). The smoke confirms both conditions select the same 36 request tokens at offsets `(17,245)` and `(176,404)` (`slop/logs/20260907_j_lens_prompt_span_activity/tokenizer-span-smoke.log:1-4`; `outputs/audits/20260907_j_lens_prompt_span_activity/smoke-v3.json:3317-4036,43376-44324`).
- Hidden activations are captured from the established block-output seam and indexed using the same token positions as the masks (`scripts/j_lens_prompt_span_activity.py:326-355`; `src/vjp_steering/vjp.py:151-180`).
- J-lens algebra matches the existing audit: `raw = unembedding @ J[layer]`, followed by `hidden @ raw.T`. Pair coordinates use the correct row-basis pseudoinverse (`scripts/j_lens_prompt_span_activity.py:363-377,398-424`; `scripts/j_lens_activity_audit.py:131-142`).
- Ranks are exhaustive over the complete model output vocabulary, not candidate-only. Ties receive rank 1, all tied rank-1 IDs are persisted, and strict semantic hits additionally require `source_score > paired_target_score` (`scripts/j_lens_prompt_span_activity.py:156-164,404-450`).
- Source selection follows strict-hit count, mean reciprocal rank, then declaration order; eligibility requires at least one strict hit (`scripts/j_lens_prompt_span_activity.py:167-190,461-467`). CPU tests exercise rank ties, selection ties, and thresholds (`scripts/j_lens_prompt_span_activity.py:540-594`).
- The explicit control tests both first greedy answer token `false` and negative-source (`+C`) eligibility. No original or causal responses are generated (`scripts/j_lens_prompt_span_activity.py:275-298,471-532,633-640`).
- The random null is deterministic, contains exactly 100 size-seven sets, excludes all 14 assessment IDs, uses pinned-tokenizer-derived lexical IDs, and compares scenario coverage against original-condition full-vocabulary rank-1 sets (`scripts/j_lens_prompt_span_activity.py:236-269,483-509`). Using all tied rank-1 IDs makes it conservative relative to the semantic strict-pair criterion.
- The Modal bridge resolves a snapshot commit and passes the same immutable revision keyword to both tokenizer and model (`scripts/run_modal.py:318-340`; `scripts/j_lens_prompt_span_activity.py:611-627`). Model, tokenizer, implementation, cohort, and lens hashes are persisted.
- The actual H100 smoke completed 648 cells without OOM, produced `false` as the first explicit-control token, and emitted a valid smoke artifact (`slop/logs/20260907_j_lens_prompt_span_activity/actual-lens-smoke-final.log:1-52`). Layer-at-a-time scoring and CPU activation storage make the one-hour DEV-15 run plausible on H100.
- The corrected local validation passed; the earlier argv failure is not relevant (`slop/logs/20260907_j_lens_prompt_span_activity/final-local-validation.log:1-3`).

### Finding

- **P1 — Required descriptive sensitivity summaries and coordinate differences are absent from the artifact schema.**
  The frozen specification requires rank-≤10 and rank-≤25 descriptive summaries and says the source/target pseudoinverse-coordinate difference should be reported (`slop/reviews/20260907_j_lens_next_experiment_oracle.md:78-91`). The implementation persists exact per-cell ranks and two raw coordinates, but `pair_summaries` retains only `strict_hits` and `mean_reciprocal_rank`, while `pair_coordinates` contains only the two coordinate values (`scripts/j_lens_prompt_span_activity.py:388-393,421-424,447-463`; confirmed in `outputs/audits/20260907_j_lens_prompt_span_activity/smoke-v3.json:43242-43371`). Searches find no top-10, top-25, or coordinate-difference output fields. This does not currently alter pass/fail, but it fails the frozen diagnostic artifact contract and would require post-hoc reconstruction or rerunning the expensive full diagnostic after correction.
  **Smallest fix:** accumulate and persist directional `top10_hits` and `top25_hits` beside `strict_hits`, add each pair’s signed coordinate difference alongside its two coordinates, and extend self-test/schema assertions without allowing these fields to affect selection or decisions. Rerun compilation, the embedded self-test, schema check, and N=1 actual-lens smoke before DEV-15.

### Merge verdict: BLOCK

- **Committing current intended implementation:** BLOCK until the required descriptive fields are added and validated.
- **Queueing full DEV-15:** BLOCK to avoid producing a knowingly incomplete frozen artifact.
- Apart from the schema omission above, the masking, activation alignment, rank/hit/tie logic, random comparison, decisions, revision pinning, and expected H100 resource use are suitable for the run.