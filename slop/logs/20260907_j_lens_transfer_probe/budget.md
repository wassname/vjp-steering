# Transfer and persistence ledger

PI/OpenAI Codex. Costs below separate reported usage,workload estimates and reservations. Do not infer billed spend from reserve values.

|item|reported API USD|GPU workload seconds|work-only estimate USD at$3.95/hr|billing status|
|---|---:|---:|---:|---|
|transfer24judgments|0.00359868|0|0|provider-reported usage|
|transfer successful retry|0|49.875740415|0.05472477073|not actual invoice|
|persistence6judgments|0.00089688|0|0|provider-reported usage|
|persistence successful call|0|26.786381522|0.02939061306|not actual invoice|
|transfer failed import-loop|unknown|no inference,local900s timeout|unknown|repeated container startup;NOT zero|

New reported API sum$0.00449556. Entire prior block API subtotal$0.21867299256 plus new=$0.22316855256. Transfer and persistence work-only GPU estimates sum$0.08411538379,excluding all startup,CPU,failed containers,platform idle and billing granularity. Existing prior successful GPU estimates$0.09914011 likewise are not invoices.

Failed app ap-49QJqvkch6JhN6V9wmw4mE stopped with `uv run --no-sync modal app stop --yes ap-49QJqvkch6JhN6V9wmw4mE` before retry. First stop without--yes reported no containers currently running but aborted confirmation;the second explicit stop succeeded.900s*$3.95/hr=$0.9875 is only a one-container hypothetical,NOT a verified bound. Parent separately reserved$5;see [parent-cost-reservation.md](parent-cost-reservation.md),which this worker did not modify.

Allocation before possible final scientific update: original gap+placement$7,failed transfer startup$5,successful transfer/retry$2,persistence$1,reviews already reported$0.21126463256,total$15.21126463256 of$40. Unreserved$24.78873536744. Actual API/GPU estimates already covered by respective diagnostic reservations must NOT be subtracted twice. Final scientific-update reservation$.50 leaves$24.28873536744 unreserved. Completed two-family update reported GLM$0.001562275 and Kimi$0.1160744 (first+oneforced continuation),total$0.117636675. This is inside the$.50reserve,not extra allocation. Updated entire-blockreported API subtotal$0.34080522756. Keepreserves intact untilreconciliation;see science-update/decision.md.

Actual Modal billing remains missing. Reconcile before another paid GPU run;no further Modal authorization is implied. Successful apps:transfer ap-ugr6ztuDu8cmcoAB5mLA0N;persistence ap-4CQzkTNBfQqFL62c5TkVtl. Retry executedtimeout900/default cap;afterward source hardening to180s,max_containers1,retries0 executed for persistence. No more GPU calls made.
