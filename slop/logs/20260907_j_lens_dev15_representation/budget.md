# DEV15 representation block spending

PI/OpenAI Codex. Keep actual provider charges, GPU-work estimates, and spending reservations separate.

| Item | Observed/estimated cost | Evidence |
|---|---:|---|
| 120 unchanged judgments | $0.01873164 actual reported | judgments.jsonl, 120 single attempts |
| Successful generation/metrology workload | ~$0.26938274 estimate | 245.513383215s H100 at $3.95/hr |
| Entire retry function bound | $0.395 one-H100 allocation, not invoice | 360s function timeout after complete generation |
| Initial failed tokenizer guard | ~$0.047 wall-based estimate, not invoice | 42.84s local log lifetime; $0.50 allowance within original $3 |
| Scientific GLM update | $0.003356175 actual reported | science-update/glm.trace.jsonl |
| Scientific Kimi update and continuation | $0.2368236 actual reported | science-update/kimi.trace.jsonl |
| New scientific update total | $0.240179775 actual reported | within separately approved $0.50 reserve |

Global reported API subtotal: prior $0.34265634756 + judgments $0.01873164 + review $0.240179775 = **$0.60156776256**.

Original DEV allocation remains $3, including failed attempt and retry; do not count the $0.50 failure allowance again. Review allocation $0.50 added after parent authorization. Previous global allocated $16.71126463256 + DEV $3 + review $0.50 = $20.21126463256. **Unreserved $19.78873536744 of $40.** Prior failed-import startup $5 reserve remains inside prior allocations. No further paid run authorized or launched. Proposed next $1.50 test is not spent or allocated by this worker.

Actual Modal billed container lifetimes/startup/idle charges remain unavailable. None are counted as zero. Estimates are not verified invoice bounds; reconcile before future budget-sensitive execution.
