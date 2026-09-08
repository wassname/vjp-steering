# Transfer retry cost reservation

PI/OpenAI Codex. Recorded before the retry was observed launched.

First app ap-49QJqvkch6JhN6V9wmw4mE crash-looped on import; local command timed out after 900 seconds. No inference output observed. Billing is unknown, not zero. $0.9875 equals one H100 at $3.95/hour for 900 seconds; it is NOT an upper bound on startup churn or all platform charges.

Reserve $5 separately for that failed launch and its unknown overhead, pending actual usage reconciliation. This is a conservative spending allocation, not a verified billing bound. Original tests retain $7 reserved; review API cost $0.21126463256. Transfer successful-test/retry allowance stays at $2 including judging. Total allocated $14.21126463256 of $40, leaving $25.78873536744 unreserved. If observed charges exceed a reservation, revise the ledger before any next paid run. Do not double-count covered API/GPU usage.

Permit only the already approved short retry after confirming old app stopped, with one container maximum and explicit remote timeout. No further paid test after this retry until its saved usage and failure allowance are reconciled. Actual billing cannot be asserted from local wall time alone.

Read-only inspection found fix commit 1bcbb10 and passing CPU rerun; modal-retry.log did not yet exist at inspection. Exact old-app shutdown and next app ID remain worker evidence to collect.
