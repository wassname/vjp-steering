# Layer18 mixer mediation — offline preflight PASS

PI/OpenAI Codex. **No paid launch, model-weight forward, model download, GPU, or judge API call.** Only a random tiny CPU BF16 hybrid model was run. Both research goals remain OPEN. Existing 39-point display and historical scores unchanged (eight protected file hashes checked).

## Actual API and intervention

`Qwen3_5DecoderLayer.forward` calls `linear_attn(hidden_states=..., cache_params=..., attention_mask=...)`, then adds the residual, applies post-attention norm and the positionwise MLP, and adds the second residual. The installed zero-based layer18 architecture is GatedDeltaNet linear attention, not softmax attention. The runner checks actual types/indices17–19 on the loaded model before its first generation.

`Qwen3_5GatedDeltaNet.forward` updates convolution state during prefill, updates recurrent state near its end, then executes `out_proj` and returns a tensor. A forward hook on this module therefore sees the already-written natural cache and the projected mixer output **before residual addition**. The new hook clones that output and assigns only `[0,-1]` on the first unpadded prefill. The adjacent layer17 block-output hook assigns exact saved common hB17. No attention mask, position IDs/embeddings, prefix token, or cache is replaced.

Actual imported source hashes match the design:
- modeling_qwen3_5.py: `0e2cd8dc50885b2701d26b116c585eedcdc62a24080ec34345af55b963126ded`.
- cache_utils.py: `ee7902fbd031ed332b5e26d07756a33f09b5c90a435b8363b9330876dc33ce0e`.

`preflight.json` records actual loaded paths, source/reference hashes, runner/helper hashes, per-arm tiny arrays and cache digests. The runtime repeats API hash checks before snapshot loading, and source/config/index/tokenizer checks before weights. It fails on source drift rather than interpreting different package code as the intended test.

## Saved tests and observed outcomes

Command and complete output in `preflight.log`, EXIT_CODE=0:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src uv run --no-sync python slop/logs/20260907_j_lens_layer18_mediation/preflight.py
```

- Real tiny hybrid: four blocks with adjacent linear/linear/full/linear, hidden32, BF16, two contexts of4/8 tokens. All eight actual generation arms run through the production `generate()` and intervention. EOS disabled only on this synthetic model to force three cached decode steps. Observed mixer sequence lengths are `[4,1,1,1]` or `[8,1,1,1]`, while each intervention/observer hook fires once. Hooks are removed at final prefill block before any cached decode.
- Native route matches independently generated no-intervention full IDs/logits and all block states. D0 also matches an independent layer0-only clamp fixture, with no mixer seam. B0/self routes preserve full IDs, logits, block states, full prefill cache and final decode cache exactly.
- Both crossed mixer updates are nonzero (tiny norm0.0016953544567454035), injected endpoints exact, receiving residual and MLP results exact; each cross h18 equals the opposite-context common-input endpoint bitwise. Common h17 and layer18 input-normalized final rows are exact across contexts.
- Every upstream/mixer cache snapshot clones all layer tensor states plus metadata. Hashes differ before/after the mixer's internal forward, establishing internal cache writes occurred; they do not differ across output-hook assignment or later within the same prefill through layer18. Cross arms retain their **own-context** B0/D0 cache hashes through the mixer, not the opposite context's cache. A mutation fixture demonstrates snapshots do not alias live tensors.
- Full cross prefill cache hashes **do** differ from same-context controls because downstream layers see the changed output; decode later changes cache even without an intervention. Those are expected effects, not preservation failures. This explicitly prevents claiming that hook-local invariance means all downstream/decode cache is fixed.
- Input IDs/masks and block/mixer position/mask metadata hashes unchanged. Earlier h17 and mixer output rows exactly unchanged. Padding is rejected rather than shifted. Actual residual addition is verified at post-attention layernorm entry, MLP output captured, next-block input exact. A deliberately wrong block-output mutation is rejected by the location/endpoint checks. Normal and pre-forward/mid-forward exceptional cleanup leave no hooks and restore baseline generation.
- Actual `run()` orchestration fixture visits all24 arms with the saved six input sequences (55/108,72/125,69/122 tokens), checks forwarded clamp/endpoint arguments and saves only temporary fixture responses. Model transport is mocked for this fixture; its printed text is reused historical text, NOT new behavioral evidence. Numerical mechanics are separately tested on the genuine tiny model above.
- Exactly nine diagnostic pairs/18 valid synthetic requests use the shared unchanged judge prompt, cache key, model, rubric, response format, temperature, provider route and token limit. Both signed mappings independently checked. Missing records, wrong context, failed identity/endpoint/gate are rejected. One deliberate invalid synthetic response exercises the no-retry guard: the helper logs its intention to retry, but the guard raises before a second transport request. No paid request occurs.

First local attempt failed because cache initialization flags are dictionaries and the assertion tested keys (including0), not values. Corrected to `.values()`; no intervention or design change. Failed `preflight-attempt1.log` retained. Attempt2 passed numerical/transport tests; attempt3 added full run orchestration; final `preflight.log` additionally checks full prefill/decode cache distinctions. These are local retries, not repeated paid experiments.

## Fixed scientific decision boundaries

The original fixed design remains authoritative: `../20260907_j_lens_retained_context_design/design.md`, especially sections3–5. Eight arms per three fixed scenarios: B-native,D-native,B0,D0,B-self,D-self,B-cross,D-cross. No vector fitting, norm rescaling, cache transplant, source or question change.

For TCA/CSN, conditional on reproducing native/common-input behavior and all mechanical gates:

| D-cross relative to corrective D0 | B-cross relative to noncorrective B0 | Relevance to a later J-lens repair |
|---|---|---|
| Loses correction | Gains correction | Immediate context-conditioned mixer contribution mediates both necessity and sufficiency locally. Supports investigating a context-aware read/write rule, NOT automatically selecting a layer18 vector recipe. |
| Loses correction | No gain | Locally necessary, insufficient by itself. Retained context/application compatibility remains part of the mechanism; a context-free GP repair is unsupported. |
| Preserves correction | Gains correction | Locally sufficient but redundant/bypassed in donor context. Could motivate a transferable-context contribution study, not necessity or benchmark success. |
| Preserves correction | No gain | This one-shot path is not the separator under retained routes. No supported next repair; no automatic layer sweep/cache experiment. |
| Any identity/delivery failure or only small unstable scores | Any | Mechanical/metrology blocker. Stop without semantic interpretation or retry. |

Legal D0 already loses correction; it is the layer17 sensitivity anchor, not a donor-corrective necessity comparison. Mixed cases remain case-specific. All answers must reject the fabrication without reintroducing invented valid uses. Full answers outrank a first-token distance or omitted judge rationale. Positive signed score here means degradation from its paired donor/common-input baseline, not beneficial minus steering.

The intervention preserves upstream/layer18 cache, other prefill positions, later mixing paths and natural donor decode history. A null does not show retained context is unimportant. A positive result does not establish J-space specificity, a full J-lens repair, norm-matched superiority, useful bidirectionality or held-out success.

## Cost and exact release boundary

No reservation made. Current unreserved balance stays **$7.22509672744**. Proposed allocation **$1.50 = $0.395 GPU (360s at $3.95/hour) + $0.955 startup/shutdown/CPU/memory/storage/uncertainty + $0.150 for18judgments**. If the parent reserves it, margin is **$5.72509672744**. Prior donor reservation and late-billing reserves remain retained. This is a conservative allocation, not an enforced provider cap.

Implemented launch command, **not executed**, only after parent reads PASS and releases paid work:

```bash
PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src timeout --signal=INT --kill-after=30s 540s uv run --no-sync modal run scripts/scratch/j_lens_layer18_mediation.py::launch
```

One H100, max_containers1, remote function timeout360s, retries0. The local540s bound covers admission/build/import/wait rather than falsely extending the function timeout to startup. On local timeout/error, inspect the already-reported app ID, explicitly stop if still running, recover persisted partial generation from `outputs/audits/20260907_j_lens_layer18_mediation/generation.json`, and do not rerun. The local timeout is not a guarantee that provider billing stops instantly. No detached or repeated app. Future owner keeps native completion notification on its worker task.

Judging, only after all24 completed gates and explicit released scope:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONPATH=src uv run --no-sync python scripts/scratch/j_lens_layer18_mediation.py --judge
```

No API retry or replacement judge. Read all24 full responses and18 rationales, preserve raw requests/provider responses, reconcile repeated baseline-score shifts, inspect metered app costs read-only (including billing lag), and obtain parent decision before any follow-up. Public outputs are not changed by either command. Partial observations are saved before cross-run/replay assertions; failures inside a model forward can terminate before that arm's generation completes and need the saved traceback, not reconstructed success.
