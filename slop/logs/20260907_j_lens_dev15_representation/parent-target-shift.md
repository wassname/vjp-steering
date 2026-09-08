# Frozen target versus replay mean

PI/OpenAI Codex. Parent computed differences directly from CALIBRATION_REPLAY JSON in modal-retry.log. Targets are unchanged in generation.

|representation|side|maximum individual coordinate error|frozen gap|replay gap|gap change|
|---|---|---:|---:|---:|---:|
|full residual|+|0.081861496|8.476953745|8.469267845|-0.007685900|
|J-GP16|+|0.023713589|5.802844048|5.800201654|-0.002642393|
|full residual|-|0.075272083|-7.554213405|-7.571987391|-0.017773986|
|J-GP16|-|0.025772333|-2.479270399|-2.493925750|-0.014655352|

None reverses the sign of the target itself. This does NOT establish that no individual patch would reverse: its sign is target minus current coordinate gap. For alpha1, counterfactual residual change from replacing the target equals 0.5 * gap_change * (basis_row0 - basis_row1). Therefore small target shifts may change near-zero patches; worker must calculate that against saved actual per-call coordinates rather than assuming relative target size proves behavior unchanged.

At inspection the provisional generation artifact is not yet saved; log has reached fin_pnf_02. Actual per-call reversal/magnitude statistics await that artifact. Judging remains paused. Current scripts/experiment.py defaults extract_batch_size8, but current defaults alone are not historical run evidence. Worker must supply historical executed configuration/source corroboration before release. No threshold or target changes approved.
