# Oracle review: J-lens concept-component swap

## Inherited decisions

- Public acceptance requires coherent, judged effects outside the random-direction zone on both benchmark sides.
- The paper reports 59% top-5 success for **coordinate swapping** with J-space concept components; it does not report sycophancy steering.
- Negative swap strength was already recognized as extrapolation, not a reverse swap.
- Current v6 separately adds positive and negative components over user-turn tokens.

## Diagnosis

Changing from separate addition to

\[
h' = h + \alpha V\left(\sigma(V^\dagger h)-V^\dagger h\right)
\]

is the correct operator-level response to the paper’s 59% result, but it is not the only required correction.

Two additional direct conflicts exist:

1. **Wrong J-space component.**
   The paper defines the component as the non-negative GP reconstruction. `extract_concept()` instead uses `selected_span_projection()` when `separate_components=True`. That projection is generally not the non-negative combination returned by GP; `self_test()` explicitly establishes that reconstruction and projection differ.

2. **Wrong position scope for the swap protocol.**
   The quoted swap protocol applies at all token positions. Current execution uses `user_turn_mask()`, excluding the assistant-generation suffix. A concept-component reproduction of that protocol should use all real prefill positions.

The v6 calibration cannot validate the corrected operator. It evaluated addition, not swapping. It is also only one prompt and is non-monotonic: `-C` repeats at 0.5 and 1.0 but becomes fluent refusals at 2.0 and 4.0, while `+C` remains fluent through 4. Automated fluency therefore does not define a reliable semantic boundary here.

## Drift / contradiction check

- Replacing non-negative GP reconstruction with selected-span projection silently revised the paper’s decomposition definition.
- Restricting swap application to the user turn silently revised “all token positions.”
- Treating signed alpha as two paper-native behavioral directions conflicts with the established fact that coordinate exchange is symmetric. Positive alpha interpolates toward/exceeds the exchange; negative alpha moves away from it. Swapping basis labels does not reverse the operator.
- Equal-normalizing the two basis vectors is plausible, but the supplied quote does not establish that this is how “every perturbation rescaled to the same magnitude” was implemented. A common scale on both columns cancels under the pseudoinverse; independent column normalization changes the operator.

## Recommendation

Implement a **paper-protocol diagnostic**, not yet a bidirectional public method:

1. Construct each component from the non-negative GP reconstruction, not the unconstrained span projection.
2. Form a full-rank two-component basis and its pseudoinverse per layer.
3. Apply the coordinate exchange at all non-padding prefill positions.
4. Use non-negative alpha, including `0`, partial exchange, and exact exchange at `1`; record basis norms, cosine, singular values, condition number, clean coordinates, and realized patch norm.
5. If equal-normalizing columns, label it as an explicit commensurate-coordinate convention unless stronger primary evidence confirms it. Record both pre-normalization component norms and resulting perturbation magnitudes.
6. Recalibrate from scratch on multiple DEV prompts. Do not reuse task 400’s additive boundary.
7. Do not prelabel `+alpha` and `-alpha` as sycophancy and critical directions. A separate directed operator or preregistered clean-coordinate/source rule is needed for two semantic benchmark sides.

The available v6 components are not numerically near-singular after unit normalization: cosine is approximately `0.657–0.818`, implying condition numbers about `2.20–3.16`. Rank conditioning does not block the diagnostic.

## Risks

- Behavioral phrases may not be spontaneously active discrete items, unlike the paper’s source-selection setting.
- The paper’s 59% result uses top-5 target appearance on other tasks, not judged sycophancy.
- Full coordinate exchange may produce only one consistent behavioral movement, so it may be structurally unable to satisfy both plot sides.
- Per-trial output-delta matching may be what the paper means by equal-magnitude perturbations; unit-normalizing basis columns may not reproduce it.
- Fluency-only calibration can accept coherent refusals or other severe off-target changes.

## Need from main agent

No blocking decision is needed to run the paper-protocol diagnostic. A later explicit decision is required between:

- preserving paper-faithful non-negative coordinate exchange as a one-direction diagnostic, or
- introducing a directed, side-specific transfer/clamp operator for the bidirectional benchmark and labeling it as an adaptation rather than the paper’s swap.

## Suggested execution prompt

Update `j_lens_concept_components` into a fresh-version paper-protocol diagnostic: use the GP non-negative reconstruction for each concept component, build and validate a commensurate two-component basis plus pseudoinverse per layer, apply `h + alpha V(swap(V†h)-V†h)` at all attended prefill positions, update diagnostics/tests/metadata, invalidate v6 caches, and run a new multi-prompt calibration with non-negative alpha. Do not claim signed alpha supplies paper-native bidirectionality or reuse task 400’s additive calibration.

— Oracle subagent / PI
