# Prespecified transfer probe

PI/OpenAI Codex. Saved before launch. Incremental cap $2; one H100 Modal call, timeout900s. At$3.95/hr timeout-only GPU upper estimate$0.9875, leaving >$1 for startup/API; actual invoice unavailable. Existing unreserved$32.78873536744 minus$2 reservation=$30.78873536744. No extra review calls.

## Question and scope

At prespecified layer17 final real prefill output, can the actual same-question direct-minus donor residual transfer candid correction to a bare recipient? Does preserving only its two saved v16 source coordinates lose that transfer? Three existing hand-selected legal/TCA/CSN cases, no fitting, layer selection or DEV15 claim. Qwen851bf6e/BF16/batch1/greedy512/cache fixed; alpha1 and source gap unchanged. Minus only, because unresolved failure is minus.

21 fresh responses: bare,direct_minus,identity_minus,donor_identity_minus,full_minus,projected_minus,gap_minus x3. Identity arms replace by their own captured natural residual; both must have exact token IDs,first-token logits,and downstream prefill states. Full replaces final layer17 residual by donor. Projected sets both saved coordinates to donor values while retaining recipient complement: h'=h+((h_d-h)D^T)B. Gap sets source-heldout mean gap preserving recipient coordinate sum. All earlier positions unchanged. Actual next-block INPUT checked against inserted state by a separate pre-hook; record all downstream final states/layer distances and first-token KLs to bare and donor.

Cache/context caveat: direct donor includes an extra instruction and different prefix length/positions. Recipient continues with its own cached history. Full-donor failure is therefore INCONCLUSIVE about source information: distributed cache, attention/recurrent history,layer choice and generation-stage needs remain. Success full vs projected failure supports omitted information only conditionally at this tested layer/context. The two-coordinate donor target is query-specific, an upper-bound diagnostic, NOT a deployable method or new fitted direction. No claim of general source repair.

## Predictions/bets

|Hypothesis|Expected observation|Counterevidence/action|
|---|---|---|
|Source-coordinate information loss (65%,nonexclusive)|full donor corrects,projection does not,despite matched donor coordinates|both transfer weakens loss claim; both fail leaves unidentifiable|
|Downstream/cache or sequential-layer effects (60%)|local donor match but downstream trajectory returns toward bare and correction absent|full and projection both transfer weakens necessity of other context|
|Actual execution bug (15%)|identity mismatch,wrong next-block input,repeat hooks,nonfinal edits or target failure|exact checks reduce this class only; numerical precision/context remain|
|Judge classification/order defect for flagged cases (90%)|judge rewards partial denial despite retained fictional properties|same rubric raw AB/BA are secondary to actual text; no rubric change|
|Unknown (20%)|no clean pattern|report measured limits,not a unique diagnosis|

Probabilities are worker subjective priorities,not measured frequencies/reviewer consensus. Full donor vs projection changes information AND norm; different norms alone cannot prove semantic uniqueness. Single-layer gap vs prior9-layer gap tests necessity of multi-layer composition only on these prompts. A null is not a method-family rejection.

## Commands

CPU: `OMP_NUM_THREADS=1 PYTHONPATH=src uv run --no-sync scripts/scratch/j_lens_transfer_probe.py --self-test`.
Initial tiny model fixture failed because all-attention Qwen cache lacks required linear state. Fixed fixture uses hybrid layers matching model family,not production code; full error retained cpu.log. cpu-hybrid.log passes.
Generation: `PYTHONUNBUFFERED=1 PYTHONPATH=src uv run --no-sync modal run scripts/scratch/j_lens_transfer_probe.py::launch`.
Judge: `PYTHONUNBUFFERED=1 PYTHONPATH=src uv run --no-sync scripts/scratch/j_lens_transfer_probe.py --judge slop/logs/20260907_j_lens_transfer_probe/generation.json --output slop/logs/20260907_j_lens_transfer_probe/judgments.jsonl`.
Four scientific conditions vs bare x3xAB/BA=24 judgments; identity controls not judged because exact-equal by assertion. Four conditions include direct donor. Distinct sample size remains3 questions.

No automatic further experiments,full DEV or public plot update. Primary result should reach production J-lens repair through next parent decision rather than being relabeled as DEV success.
