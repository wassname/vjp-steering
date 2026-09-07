# One approved tokenizer-setup retry

PI/OpenAI Codex. First app ap-cp7YFJacErU81Iisidzlu6 stopped before any dictionary/source calibration/DEV generation. Exact guard: tokenizer_content_hash == historical metadata. Local setup bug: copied generation-only pad=eos before extraction metrology; original extraction preserves existing pad.

CPU exact diagnosis saved tokenizer-diagnosis.log EXIT0:
- Expected/default hash0ef9d0923a6d6d8342cae2674ade04c07f12fd060a55f170b8cc9b89f9a822d4;pad248044,eos248046,right padding.
- All195actual source prompt token lists match saved attended token records.
- After generation-only pad=eos hasha9fd60aa3bc1bf9c3b1718a2dbd490a80adf0d0612719f505d86ee9dc84f85eb;pad248046,eos248046.

Parent explicitly approves ONE retry conditional on exact local match,which passes. Fix moves generation pad change AFTER original-tokenizer extraction metrology; no assertion removed,no threshold/source relaxed. Record/compare all15batch1generation input IDs before/after;should be identical. Added observed-before-assert GP support/calibration metrics for precise failure evidence.

First log filesystem birth00:42:31.047991418+0800 to modified00:43:13.884686101 =42.84s local wall,not billed GPU lifetime. modal app stop --yes reports already stopped(finished00:43:12+0800),CLI exits1 for already-stopped,not running. Full failed log preserved. One-H10042.84s estimate~$0.047,not invoice. Allocate$0.50 failure allowance inside existing3;remaining2.50ample for one360s-capped retry(~.395GPUwork maximum)+120judgments/startup. No actual billing claim. Global unreserved20.28873536744 unchanged.

Retry exact command same as initial;new log modal-retry.log. No further automatic retries: any later metrology mismatch stops before DEV and requires new decision. Source/model/lens/splits/targets and all tolerances unchanged.
