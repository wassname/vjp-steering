---
requested_model: deepseek/deepseek-v4-flash-0731
max_tokens: 20000
final_tokens: 20000
reasoning_effort: low
input_bytes: 19774
trace: /workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-05_deepseek-v4-flash-0731_j_lens_swap_code_audit.trace.jsonl
generated: 2026-09-04T22:58:04.386240+00:00
---

# bounded completion

## First call reasoning

We need to audit the diff for concrete deviations from the paper specification. The paper specification is given. The adaptation under review: source token "abrasive" and target "flattering", both single tokens; layers are existing 20%-80% residual-stream band; positive alphas 0.5, 1, 2; negative alphas are labeled extrapolation controls, not reverse swaps; outcomes judged response effect and off-target damage.

We need to check tensor orientation, pseudoinverse use, preservation of orthogonal component, alpha semantics, precision, serialization/reload, hook position, experiment grids, metadata, and whether source-target ordering changes the swap.

Let's analyze the code in the diff.

The key function is `_swap_lens_coordinates` in `src/vjp_steering/vjp.py`. It takes hidden, basis (size [2, d]), dual (size [2, d]), alpha.

Compute coordinates = einsum("...d,kd->...k", hidden, dual). That is hidden (..., d) times dual (k, d) => ... k. So coordinates shape (... , 2). That's correct: c = V^dagger h where V has columns v_s and v_t? Actually paper says V = [v_s v_t] (columns are v_s and v_t) so V shape d x 2. Then V^dagger is 2 x d, so c = V^dagger h gives a 2-vector. Here dual is pinv(basis.T) where basis is shape [2, d] (rows are the two vectors). basis.T is d x 2, pinv gives 2 x d. So dual is the same as V^dagger if basis rows are v_s and v_t. So coordinates = hidden (..., d) * dual (k, d) => ... k good.

Then delta = einsum("...k,kd->...d", coordinates.flip(-1) - coordinates, basis). coordinates.flip(-1) swaps the two coordinates. So that's sigma(c) - c. Then multiply by basis (k, d) to get delta in d-dimensional space. But note: basis is [2, d] rows, so einsum "...k,kd->...d" sums over k, so that gives (sigma(c) - c) * V^T? Actually if basis rows are v_s and v_t, then (sigma(c)-c)_k times basis[k, d] sums over k, so that's V * (sigma(c)-c) where V is [v_s, v_t] as columns? Wait basis rows are the two vectors. If we treat V as columns [v_s, v_t], then V * (sigma(c)-c) would be sum over k of (sigma(c)-c)_k * v_k (where v_k is column). But here basis[k,:] is the row. So it's indeed (sigma(c)-c)_0 * v_s + (sigma(c)-c)_1 * v_t, same as V * (sigma(c)-c) if v_s and v_t are columns. So delta is correct.

Then hidden + alpha * delta. That matches paper: h_patched = h + V(sigma(c) - c), with alpha scaling.

Now, we need to check if the orthogonal component is preserved. The delta is in the span of v_s and v_t, so hidden + delta changes only in that subspace. However, if basis is not orthonormal, the delta as computed using coordinates from dual (pseudoinverse) will have the property that the orthogonal component is unchanged because the projection onto the span is via V V^dagger, but here we add V(change c) where change c is in the coordinates. Indeed, the orthogonal component is unchanged because the added vector lies entirely in the span. So that's fine.

Now, check tensor orientation: basis is [2, d] (two rows). dual is [2, d] (since pinv of basis.T is 2 x d). So coordinates shape ... k. Fine.

Potential issues: The paper does not normalize v_s or v_t. This code doesn't normalize. Good.

Alpha semantics: The paper uses alpha scaling optionally. They have J_LENS_SWAP_GRID = (0.5, 1.0, 2.0). Positive alphas; negative alphas are labeled extrapolation controls. In the diff, they set grid for both sides +C and -C to the same list of positive alphas. But the metadata says -C meaning "negative-alpha extrapolation control". In the code, the boundaries dict: for "-C": {"meaning": "negative-alpha extrapolation control", "trace": []}. But the grid is still set to J_LENS_SWAP_GRID (positive alphas). That suggests that the -C side is actually using positive alphas? Wait the grid is set for both sides to the same list. That might be a deviation: the paper says alpha scaling, and they intend positive alphas for both sides? But the metadata says -C is negative-alpha extrapolation control, yet the grid is positive. Possibly they plan to use alpha values as coefficients, and -C side maybe uses negative alpha? But the grid is defined as J_LENS_SWAP_GRID = (0.5,1,2). So if they want negative alpha for -C, they should have a different grid. But in the diff, they set grid = {side: list(J_LENS_SWAP_GRID) for side in ("+C", "-C")} - same for both. That is suspicious. Maybe they intend to use alpha as a coefficient that can be positive or negative? But the paper says alpha scaling; alpha=1 and alpha=2 are positive. They label negative alpha values as extrapolation controls, but they don't include them in the grid. So -C side is still using positive alphas, but labeled as negative-alpha extrapolation? That is a mismatch. Probably they intended to have negative alphas for -C side? But the grid is positive. That is a concrete deviation: they claim negative alpha extrapolation control but never actually use negative alphas. Might be an oversight. We can flag as medium severity.

Also, they check "source-token: abrasive; target: flattering; both must tokenize to one token" - in code, they do single_token_id(" word") with space prefix. That's fine.

Now check hook position: The JLensSwap.apply method is registered and applied at each layer. The paper says apply at every token position across a band of intermediate residual-stream layers. The code applies to all tokens (hidden is the residual stream state at each token). That's fine. But we need to check if the hook is applied at every token position, not just last token. The apply function receives y (hidden states) and does the swap regardless of position. That matches.

But we need to verify that the hook is not applied to only the last token. The `JLensSwap.apply` is static, and we don't see how it's hooked. But in the diff, we see in experiment.py and walk.py they call `j_lens_swap` to extract vector. The vector is a `Vector` with `JLensSwapC` config and state containing basis and dual per layer. Then the hook is presumably applied via the Vector mechanism. We need to check if the apply function uses `cfg.coeff` as alpha. In JLensSwap.apply, it uses `cfg.coeff` as alpha. That is correct.

Now check pseudoinverse use: They compute `dual = torch.linalg.pinv(basis.T)`. That is correct.

Precision: They cast hidden to float for the computation, then cast back to hidden dtype. That is fine.

Serialization/reload: They save/load Vector with JLensSwapC and state. Self-test checks reload exact. Good.

Now check experiment grids: The grid in gpu_stage sets both sides to the same positive alphas. Also the metadata says -C is negative-alpha extrapolation control, but grid is positive. That is a deviation.

Also check source-target ordering: Does the swap depend on ordering? Yes, swapping coordinates c1 and c2 is symmetric? Actually swapping c1 and c2 is symmetric: sigma(c) = (c2, c1). But the resulting delta = V(sigma(c)-c) = (c2-c1)*v_s + (c1-c2)*v_t = (c2-c1)(v_s - v_t). If we swap source and target, the sign flips? Wait if we swap v_s and v_t, then basis rows are swapped. coordinates computed with dual of swapped basis will swap c1 and c2. Then sigma(c) - c will be (c1-c2) for first component? Let's compute: original basis [v_s, v_t]. Swapped [v_t, v_s]. The dual will be such that coordinates are (c_t, c_s) relative to original? Actually if we swap, the new coordinates are (c_t, c_s). Then sigma(new) - new = (c_s - c_t, c_t - c_s) = - (c_s - c_t, c_t - c_s)? Wait if original c = (c_s, c_t). Swapped gives (c_t, c_s). Then sigma(swapped) = (c_s, c_t). Difference = (c_s - c_t, c_t - c_s) = (c_s - c_t, -(c_s - c_t)). Then delta = (c_s - c_t)*v_t + (-(c_s - c_t))*v_s = (c_s - c_t)(v_t - v_s). Original delta was (c_t - c_s)(v_s - v_t) = -(c_s - c_t)(v_s - v_t) = (c_s - c_t)(v_t - v_s). So delta is identical! So the swap is symmetric with respect to source-target ordering. Actually if we swap source and target, the delta is the same. So ordering does not change the swap. Good.

But wait: the paper says V = [v_s v_t] and sigma swaps the two entries. If we swap source and target, V becomes [v_t v_s], and sigma still swaps, but the coordinates are with respect to V^dagger h. The delta is V(sigma(c)-c). Let's compute generally: V = [v_s, v_t], c = V^dagger h = (c_s, c_t). sigma(c) = (c_t, c_s). Delta = (c_t - c_s)v_s + (c_s - c_t)v_t = (c_t - c_s)(v_s - v_t). If we swap source and target, V' = [v_t, v_s], c' = V'^dagger h = (c_t, c_s) (since it's the same projection? Actually if V' has columns swapped, the pseudoinverse will give coordinates in the swapped basis: c' = (c_t, c_s). Then sigma(c') = (c_s, c_t). Delta' = (c_s - c_t)v_t + (c_t - c_s)v_s = (c_s - c_t)(v_t - v_s) = - (c_t - c_s)(v_t - v_s) = (c_t - c_s)(v_s - v_t). Same delta. So ordering doesn't matter. So no issue.

Now check metadata: They store metadata with paper_equation, normalization: "none", token_scope: "all_positions", etc. That matches.

Potential issues:

1. The experiment grid: both +C and -C use same positive alphas, but metadata says -C is negative-alpha extrapolation control. This is a mismatch. The paper says optional scaling by alpha, and they use positive alphas. But they claim negative alphas are extrapolation controls, yet they don't use them. This is a deviation: they might intend to have negative alphas on -C side, but they have positive. Could be a bug.

2. The J_LENS_SWAP_GRID is (0.5, 1.0, 2.0). That's fine.

3. Check that they use the band of intermediate residual-stream layers: they call `walk.resolve_layers(model, None)` which likely returns the 20-80% band. That's good.

4. Check that they apply at every token position: the apply function does not restrict to last token, so yes.

5. Check that they don't normalize v_s or v_t: they don't.

6. Check tensor orientation: OK.

7. Check pseudoinverse: OK.

8. Check preservation of orthogonal component: OK.

9. Precision: They cast to float, but that could cause precision loss if hidden is in bfloat16? But they cast back to hidden dtype. Might be okay.

10. Serialization/reload: self-test passes.

11. Hook position: They use `shared["basis"]` and `shared["dual"]` in apply. That is fine.

Now look for concrete deviations from paper intervention. The paper says "set h_patched = h + V(sigma(c) - c)" and optionally scale by alpha. In code, they do that. So core math is correct.

But there is a subtle issue: The paper says "The component of h orthogonal to span{v_s,v_t} is unchanged." That holds because delta is in span. But is it exactly unchanged? Yes, because delta is a linear combination of v_s and v_t.

Now check the self-test: They test alpha=0 gives identity, alpha=1 gives coordinate exchange. That's good.

Now check experiment grid: In `gpu_stage`, they set `grid = {side: list(J_LENS_SWAP_GRID) for side in ("+C", "-C")}`. That means both sides use same alphas. But they may intend to have -C side use negative alphas. The metadata says -C meaning "negative-alpha extrapolation control". That is a concrete deviation: the -C side is labeled as negative-alpha extrapolation control, but the grid values are positive. This could be a mistake. The user asked about "negative alpha values are explicitly labeled extrapolation controls, not reverse swaps". So they want to test negative alphas as extrapolation, but the grid doesn't include them. So they are not actually testing negative alphas. That is a deviation from the spec.

Also check if they have any check for alpha semantics: The apply uses cfg.coeff as alpha. The cfg.coeff is set from the grid coefficient. In the experiment, they likely pass coefficient values from the grid. So positive alphas are used. They might later use negative coefficients for -C side via some other mechanism, but the grid doesn't reflect that.

Another possible issue: They don't include alpha=0 as a control? Not required.

Now check the self-test: They print "J_LENS_SWAP_SELF_TEST_PASS alpha0=identity alpha1=coordinate_exchange reload=exact". Good.

Now check the experiment grid: The dev stage: in `gpu_stage`, if args.dev and "boundaries" in manifest and args.method != "j_lens_swap", they expand grid via dev_grid. For j_lens_swap, they skip that. In the else branch, they set boundaries with meaning and empty trace, and grid to J_LENS_SWAP_GRID for both sides. So they always use fixed grid for j_lens_swap. That's fine.

Now check the `extract_vectors` function: It returns vectors for both "+C" and "-C" as the same vector (same object). That is fine because they want to apply same swap but with different coefficient signs maybe? But they store same vector for both sides. In the gpu_stage, they use vectors[side] for each side. So they will apply the same basis/dual but with different coefficients (alpha) depending on the grid. Since the grid is the same for both sides, both sides will get same alphas. But they might intend to have -C side use negative alphas? The metadata says -C meaning "negative-alpha extrapolation control". But the grid is same. So that is a concrete issue.

Also note that in `gpu_stage`, they set `grid = {side: list(J_LENS_SWAP_GRID) for side in ("+C", "-C")}`. If they want negative alphas for -C, they should set -C grid to negative values. But they don't. So this is a deviation.

Another potential issue: The paper says "optionally scaled by a factor alpha". The adaptation uses alpha as the coefficient, but they also have `coefficient` in args. In the experiment, the coefficient is likely used as the multiplier for the steering vector. For j_lens_swap, the coefficient is alpha. That's fine.

Now check if the code enforces that alpha values are positive for +C and negative for -C. It doesn't; it sets same grid. That's a mismatch.

Now check the metadata: In `j_lens_swap`, they set `"normalization": "none"`. That's correct.

Now check if they use the same lens file as J_word? They use `_load_j_lens` which loads the same checkpoint. That's fine.

Now check the source-target ordering: already discussed, no issue.

Now check the tensor orientation in basis: basis is [2, d] with rows v_s and v_t. But the paper says V = [v_s v_t] as columns. In the code, they treat basis as rows. But since they compute delta as einsum("...k,kd->...d", coords_diff, basis), that sums over k and multiplies by basis rows, which is exactly V * diff if V columns are the rows. So it's consistent.

Now check the pseudoinverse: `dual = torch.linalg.pinv(basis.T)`. basis.T is d x 2, pinv is 2 x d. Good.

Now check if they compute the coordinates correctly: coordinates = einsum("...d,kd->...k", hidden, dual). That is hidden (..., d) * dual (k, d) -> ... k. That's fine.

Now check preservation of orthogonal component: Is there any subtlety because they use pinv? The delta is in span, so orthogonal component unchanged. Good.

Now check hook position: The apply function receives y at each layer. It uses shared basis and dual. The basis and dual are stored per layer in layer_state. So at each layer, they apply the swap using that layer's basis. That's correct.

Now check that they apply at every token position: The apply function does not filter tokens. So yes.

Now check that they use the same band: They use `walk.resolve_layers(model, None)` which likely returns the 20-80% band. Good.

Now check metadata: They store source_token, target_token, etc. Good.

Now check serialization/reload: The self-test verifies reload exact. Good.

Now check if there are any issues with the `extract_vectors` function: It returns same vector for both sides. That might be intended, but then metadata for -C side is mislabeled. In `gpu_stage`, they set boundaries for -C as "negative-alpha extrapolation control". But the grid is same positive alphas. So the labeling is wrong.

Another issue: The grid values are (0.5,1,2). The paper's ordinary swaps use alpha=1 and double-strength alpha=2. They include 0.5, which is a weaker swap. That's an extrapolation, but they label negative alphas as extrapolation controls, so maybe they should have negative values. They have 0.5 which is a positive extrapolation. That's not a deviation per se, but the labeling mismatch is.

Now check the condition number metadata: They store condition number. That's fine.

Now check if they explicitly check that source and target tokenize to one token: They do via single_token_id. Good.

Now check if source-target ordering changes the swap: As we reasoned, it doesn't. So no issue.

Now check if the code uses the correct lens: The J_lens is a cached Jacobian lens. They compute basis as unembedding[source_id] @ jacobian. That is the tangent of the logit difference? Actually paper says J-lens vectors are single-token rows of W_U J_l. So they compute unembedding row times jacobian. That's correct.

Now check if they scale alpha correctly: In apply, they do `return hidden + (alpha * delta).to(hidden)`. That's correct.

Now check if they use the same alpha for both +C and -C? The grid is same, so yes. But the metadata says -C negative alpha. So that's a concrete deviation.

Now check the self-test: It tests alpha=0 identity, alpha=1 coordinate exchange. Good.

Now check if they have any other deviations: The paper says "applies swaps at every token position". The code does that. Good.

Now check the hook orientation: The apply function is called with `y` which is likely the hidden state. It doesn't modify in-place; returns new tensor. Good.

Now check the serialization of basis and dual: They are tensors, stored in Vector state. They save to safetensors. Good.

Now check if they save the metadata correctly: In `j_lens_swap`, they return metadata dict. Good.

Now check the experiment grid for dev mode: They skip dev grid expansion for j_lens_swap. That's fine.

Now check if they handle the case where alpha is negative? The grid only has positive. So negative alphas not tested. That is a deviation from the adaptation specification which says negative alpha values are explicitly labeled extrapolation controls. So they should include negative alphas somewhere.

Now, let's list findings by severity.

Potential findings:

1. (High/Medium) The -C side is labeled as "negative-alpha extrapolation control" but the grid uses the same positive alphas as +C. This is a deviation: negative alphas are not actually tested, and the labeling is misleading. This could be a bug in the grid definition.

2. (Low) The self-test does not test alpha=2, but that's not required.

3. (Low) The metadata for -C says "negative-alpha extrapolation control" but the grid is positive. This is part of finding 1.

4. (Low) They don't explicitly check that the basis is full rank? They do check singular_values[-1] > 0, so that's fine.

5. (Low) They compute dual as pinv(basis.T) but don't recompute it after saving/loading? Not an issue.

6. (Low) The apply function uses `cfg.coeff` as alpha. In the experiment, the coefficient is likely set from the grid. But is there any chance that the coefficient is used for something else? Not seen.

Now, the user asked: "State whether source-target ordering changes the swap." We'll answer: No, the swap is symmetric with respect to source-target ordering; the resulting delta is identical.

Now, "Give file/line findings ordered by severity and the smallest correction."

We need to locate lines in the diff. Let's look at the diff for the grid setting: in `scripts/experiment.py` around line 517-528? The diff shows:

```
+        if args.method == "j_lens_swap":
+            boundaries = {
+                "+C": {"meaning": "paper swap alpha", "trace": []},
+                "-C": {"meaning": "negative-alpha extrapolation control", "trace": []},
+            }
+            grid = {side: list(J_LENS_SWAP_GRID) for side in ("+C", "-C")}
```

So line numbers: after the diff, in the new file, it's around line 517-520? We can say in `scripts/experiment.py`, in `gpu_stage`, the grid is set to same positive alphas for both sides, but -C is labeled as negative-alpha extrapolation control. That's a deviation.

Also in the same function, they set `expanded_grid` condition skips j_lens_swap. That's fine.

Now the smallest correction: To match the label, they should set grid for "-C" to negative alphas, e.g., `{"+C": [0.5,1,2], "-C": [-0.5,-1,-2]}` or maybe just -1 and -2. But the adaptation says negative alpha values are explicitly labeled extrapolation controls, not reverse swaps. So they should include some negative alphas like -0.5, -1, -2. The smallest correction would be to change the grid for "-C" to negative values. Alternatively, change the metadata meaning to "paper swap alpha" for both. But the spec says negative alphas are extrapolation controls, so they likely intended to have them. So better to correct the grid.

Now also check the self-test: They test alpha=1, but not alpha=2. Not a deviation.

Now, check if there is any issue with the hook position: The apply is registered for all layers in layers. That's fine.

Now, check if they apply at every token: The apply function does not mask positions, so yes.

Now, check if they correctly preserve orthogonal component: They do.

Now, check if they use the correct pseudoinverse: yes.

Now, check if they compute coordinates correctly: yes.

Now, check if they use the same vector for both sides: that might be intended. But metadata says -C negative alpha, so it's inconsistent.

Now, check if they have any off-target damage measurement: not in diff.

Now, also check if they add the vector to both sides in extraction: they return same vector for both sides. That's fine as long as coefficients differ. But coefficients are same positive alphas. So both sides will be identical experiments, which is a waste. That also indicates a bug: they probably intended to use negative alphas for -C side to have different experiments.

Now, let's compile the findings.

Severity: High? Or medium? The paper adaptation says negative alphas are extrapolation controls, so they should test them. Not doing so is a deviation. But it's not a core math error. I'd say medium severity.

Also, check if the self-test uses random basis, but they use pinv. That's fine.

Now, check if they store basis and dual per layer, and the apply uses shared dict. That's fine.

Now, check if there is any issue with the precision: They cast hidden to float, compute, then cast back. That's fine.

Now, check if the hook is applied at the correct layers: They use layers from resolve_layers. That's fine.

Now, check if they use the same lens file as J_word: yes.

Now, check if they correctly handle the case where source and target tokens are the same? Not relevant.

Now, also check if they use `alpha * delta` where alpha can be negative. If they use negative alpha, the swap is reversed? Actually negative alpha would flip the direction of delta, but still not a reverse swap. They label negative as extrapolation, not reverse swaps. That suggests they want to test negative multipliers. So they should include negative alphas.

Now, the smallest correction: In `scripts/experiment.py` in `gpu_stage`, change the grid to have negative alphas for -C side. For example:

```python
grid = {
    "+C": list(J_LENS_SWAP_GRID),
    "-C": [-alpha for alpha in J_LENS_SWAP_GRID],
}
```

Or at least add -1 and -2. But the spec says negative alpha values are explicitly labeled extrapolation controls, so they likely want both -0.5, -1, -2. So that.

Now, also adjust the boundaries meaning if needed.

Now, also note that the metadata for -C says "negative-alpha extrapolation control", so they should have negative grid.

Now, let's state the decision: The implementation mostly follows the paper, but there is a concrete deviation regarding the -C side grid.

Now, strongest objection: The -C side is supposed to test negative alpha extrapolation controls, but the grid uses the same positive alphas, so negative alphas are never tested; the -C side is redundant and mislabeled.

Next check: Verify that the grid is actually used for coefficient values in the runs. That is likely.

Now, answer the user: Provide findings ordered by severity.

I'll list:

1. [Medium] `scripts/experiment.py` in `gpu_stage` (around line 519-522): The grid for "-C" is set to positive alphas `J_LENS_SWAP_GRID` while metadata labels it as "negative-alpha extrapolation control". Negative alphas are never tested. Smallest correction: set `grid["-C"] = [-a for a in J_LENS_SWAP_GRID]` and keep metadata.

2. [Low] `scripts/experiment.py` `extract_vectors` returns the same vector for both "+C" and "-C" with no indication of sign; this is consistent if coefficients differ, but with current grid they are identical.

3. [Low] No other deviations found.

Also mention that source-target ordering does not change the swap.

Now, produce final answer.
## First call answer

**Decision:** The adaptation matches the paper's core formula (`h + α V(σ(V†h) − V†h)`, no normalization, all token positions, 20–80% band). One concrete deviation exists: the `-C` side is labeled **negative-alpha extrapolation control** but the experiment grid uses only positive alphas (0.5, 1, 2), so negative alphas are never tested and the two sides are redundant.

**Strongest objection:** The `-C` control is misconfigured—it claims to test negative alphas but reuses the positive-alpha grid, making it a duplicate of `+C` and violating the stated extrapolation-control intent.

**Next check:** Confirm that the grid values in `manifest["grid"]` are actually used as the `coeff` in the steering application (likely via `Vector.apply`), and that no other code path silently flips the sign for `-C`.

---

### Findings (ordered by severity)

#### 1. [⚠️ Medium] `-C` grid uses positive alphas despite "negative-alpha extrapolation control" label
**File:** `scripts/experiment.py`, `gpu_stage()` (approx. lines 519–522 in new file)
```python
if args.method == "j_lens_swap":
    boundaries = {
        "+C": {"meaning": "paper swap alpha", "trace": []},
        "-C": {"meaning": "negative-alpha extrapolation control", "trace": []},
    }
    grid = {side: list(J_LENS_SWAP_GRID) for side in ("+C", "-C")}
```
- **Issue:** Both sides get `J_LENS_SWAP_GRID = (0.5, 1.0, 2.0)` — all positive. The `-C` side is explicitly labeled as a negative-alpha extrapolation control, but no negative alpha values are included. This makes the `-C` side identical to `+C` and fails to test the intended negative extrapolation regime.
- **Smallest correction:** Change the `-C` grid to negative alphas, e.g.:
  ```python
  grid = {
      "+C": list(J_LENS_SWAP_GRID),
      "-C": [-alpha for alpha in J_LENS_SWAP_GRID],
  }
  ```

#### 2. [ⓘ Low] `extract_vectors` returns the same vector for both sides
**File:** `scripts/experiment.py`, `extract_vectors()` (approx. lines 160–165)
```python
if args.method == "j_lens_swap":
    ...
    return {"+C": vector, "-C": vector}, metadata, 0, "fixed_tokens:abrasive-flattering"
```
- **Issue:** Both sides share the same vector (same basis/dual). This is acceptable **only if** the coefficient sign differs. With the current grid (finding #1), both sides receive identical positive coefficients, making the experiment redundant. Producing a negative-coefficient grid for `-C` would resolve this.

---

### Non-issues (checked, no deviation)

- **Tensor orientation:** `basis` shape `[2, d]` (rows = `v_s`, `v_t`), `dual = pinv(basis.T)` (shape `[2, d]`) — matches `V = [v_s v_t]` and `V†` (2×d).
- **Pseudoinverse use:** Correctly computes `dual = pinv(basis.T)`; coordinates `c = hidden @ dual.T` (einsum `...d,kd→...k`).
- **Orthogonal component preservation:** `delta` lies entirely in `span{v_s, v_t}`, so `h + α·delta` leaves the orthogonal part unchanged.
- **Alpha semantics:** The paper’s `α` is implemented `cfg.coeff`; positive α scaling is correct. Negative α (if used) would be extrapolation, not a reverse swap — consistent with the intent.
- **Precision / serialization:** Self-test confirms `α=0` gives identity, `α=1` gives coordinate swap, and `Vector` save/load round-trips exactly.
- **Hook position:** Applied to all tokens in each `y` (residual stream) at every layer in the 20–80% band.
- **Metadata:** `source_token`, `target_token`, `lens_sha256`, and per‑layer condition number recorded; `normalization: "none"` is correct.
- **Source-target ordering:** Does **not** change the swap. Exchanging `v_s` and `v_t` yields the same `delta` (the sign flips twice and cancels).

## Completion

- outcome: `complete`
- trace: `/workspace/2026/jspace/j-steer_pub/slop/reviews/2026-09-05_deepseek-v4-flash-0731_j_lens_swap_code_audit.trace.jsonl`
