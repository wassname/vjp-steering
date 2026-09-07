# Bounded primary padded parity: before execution

Readout correction already passed one-prompt real-Qwen bridge; it does not prove batched primary equivalence. Parent reviewed current diff and approved the bounded run. CPU companion/readout/comparison checks pass (primary-padded-parity-local-validation.log).

| Option | Metric | Expected change | Selection |
|---|---|---|---|
| Two-row primary versus official singles | Full-vocabulary scores, exact top1, rank1 sets, 14 frozen ranks | All compared cells should match within existing score tolerance and exact discrete tests | Run |
| Single-row primary versus official singles | Same metrics | Exact readout agreement; separates masking/batching from readout | Included diagnostic control |
| Change tolerance, dtype or frozen candidates | Could hide numerical or selection defects | Would destroy attribution | Not permitted |

Hypotheses before run (rough debugging priorities, not calibrated posteriors): full agreement 60%; BF16 batched forward numerical differences 30%; mask/position or integration defect 8%; unknown 2%. Full agreement predicts all four records pass, with observed padding in each condition. Numerical differences predict matching tokens/positions and passing single-primary comparisons but batch rank mismatch with small score margins. Index defects predict mismatched token positions/offsets or large hidden-state differences. There is no generation, training, steering or judge call.

The question is whether actual capture_condition → score_records on two unequal-length frozen DEV prompts matches pinned official single-prompt apply. Full DEV15 is authorized only on full pass. No threshold relaxation. Cost estimate: previous real bridge took 42 seconds including startup; allow up to 10 minutes for 4 records plus companion/single controls, about $0.66 H100 compute upper planning estimate at $0.066/min (not measured billing). Source and hashes are saved in artifact. Failed remote artifact persists through cache.commit in finally; retrieve from Modal volume if subprocess exits nonzero.

— PI/OpenAI Codex
