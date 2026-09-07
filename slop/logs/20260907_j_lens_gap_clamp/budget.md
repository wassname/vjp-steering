# V10 executed diagnostic budget

PI/OpenAI Codex. Total human cap$40. Exact provider-reported usage, separated from GPU estimates:

|item|reported API USD|GPU compute estimate USD|evidence|
|---|---:|---:|---|
|8 MoA calls including continuations|0.21126463256|n/a|slop/reviews/j_lens_v10_*.trace.jsonl usage events|
|original21-response diagnostic AB+BA36 judgments|0.00549428|0.07045382398|judgments*.jsonl;64.211080087s H100|
|placement6 new responses AB+BA12 judgments|0.00191408|0.02868628427|placement/judgments*.jsonl;26.144461617s H100|
|failed first provenance check|n/a|unknown|modal.log;no generation,config assertion failure|

Reported API total$0.21867299256. Successful inference compute estimate$0.09914010826 at H100$3.95/hr; no actual Modal invoice retrieved. Estimated combined known usage$0.31781310082 excludes failed startup and platform overhead,so is not actual billed total.

Reservations are NOT additive to actual costs inside them: original diagnostic$5 includes its judge/GPU; authorized placement increment$2 includes its judge/GPU. With these reserves held and actual review spend charged,unreserved remainder is40−0.21126463256−5−2=$32.78873536744. The old$2 review reserve is replaced by its actual$0.21126463256,not double counted. Reconcile actual Modal billing before releasing reserves. No further run launched.
