# Billing reconciliation, no app created

PI/OpenAI Codex. Read-only Modal billing CLI queries succeeded. Full commands, JSON responses and exit codes are saved in rates.log, september-summary.log and september7-hourly.log. check.py reproduces queries; reconcile.py performs Decimal arithmetic into reconciliation.json.

## Observed billing

Current H100 rate is $3.95/hour, CPU $0.04730/core-hour, memory $0.008/GiB-hour. September workspace metered total is $16.36970056, billed $0 after credits/free storage. These are workspace totals, NOT this task's cost; do not treat credits as additional experiment budget.

Three identified stopped failed apps now have CPU/memory/H100 metered rows:

| App | Prior reserve | Metered total |
|---|---:|---:|
| ap-49QJqvkch6JhN6V9wmw4mE | $5.00 | $0.04841605 |
| ap-yh5THLF10Dl4TQlTFdJunH | $1.00 | $0.02858388 |
| ap-f8aD8yg7WT3xhqMTkix9y7 | $0.75 | $0.01779207 |

Replace only these three identified reserves with their reported costs. Their $6.75 reserve becomes $0.09479200. Retain an additional $0.25 for possible later billing adjustments; this is a planning allowance, not a proven upper bound. Every other reserve, including unknown timed-out judge cost, remains unchanged. Reported API subtotal stays $1.08584037412.

Available allocation becomes $2.01988872744 + $6.65520800 - $0.25 = **$8.42509672744**. Committed/reserved envelope is therefore $31.57490327256 of $40. This uses a metered snapshot, not final invoice certification. No successful-run reserve was released, so their actual bills are not added a second time.

## Proposed test admission

The donor-context factorial remains precisely specified in ../20260907_j_lens_failed_repair_synthesis/synthesis.md: three fixed scenarios, donor context for all arms, unpatched/neither/parallel/complement/full,15 generations and18 unchanged judgments. No new source, scores or caches transplanted. It is distinct from prior recipient-context transfer.

At live H100 rate360 seconds is $0.395 (the prior $0.39492 rounded per-second rate was slightly low). A $1.20 estimate can comprise $0.395 GPU + $0.705 startup/CPU/memory/storage/uncertainty + $0.10 judging. Observed stopped failure bills substantially reduce the earlier cumulative-budget concern; a planned $1.20 allocation would leave $7.22509672744, all other reservations intact.

Historical billing does NOT enforce a hard future $1.20 ceiling. Startup duration and delayed billing remain unbounded by the function timeout. Thus estimated affordability within $40 now passes with much larger headroom, but an enforceable per-test cap has not been established. Do not describe billing history as a hard guarantee. The test remains ready as a specification, not implemented or launched. Latest instruction requests no launch; no new reservation made. Both research goals remain OPEN.
