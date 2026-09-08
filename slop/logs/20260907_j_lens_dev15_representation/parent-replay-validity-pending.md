# Replay discrepancy: validity review pending

PI/OpenAI Codex. Judging and further paid runs paused; active generation may finish and persist provisionally.

Executed source3a1b921 lines154-158 computes maximum absolute coordinate error and checks:

```python
error=float((coords-saved).abs().max())
assert error < .1, (name,condition,error)
```

The threshold existed before retry, but its existence alone does not establish scientific adequacy. Observed full-residual positive max0.08186149597167969 passes this approximate check, not exact parity.

Executed replay lines143-148 load each original token record directly:

```python
tr = fm['token_records'][ci*n+index]
encoded = {k:torch.tensor([tr[k]],device=model.device) for k in ('input_ids','attention_mask')}
model.model(**encoded,use_cache=False)
states.append(found[LAYER][0,tr['final_position']].float())
```

Thus replay preserves saved per-row padded input IDs, attention masks and final index. It changes batch shape to1. Original residuals() batches prompts with padding=True; historical actual batch size and saved padding statistics still require the worker's source/config audit. Do not attribute mismatch conclusively to BF16 kernels without that evidence.

Saved versus replay positive full-residual means: [6.9433465003967285,-1.5336072444915771] versus [6.9358229637146,-1.533444881439209]. Negative: [-1.8721760511398315,5.682037353515625] versus [-1.8686497211456299,5.703337669372559]. Targets remain the saved values; no replay recalibration occurred. Worker must quantify gap differences and residual-patch consequences, not confuse per-cell maximum with target mean shift. Historical extraction model revision remains unknown. GP support and component replay exact do not prove historical activation equality.

No judging release until durable discrepancy/scale/mask analysis is read. Source record hashes and provenance.json remain authoritative for original lists.
