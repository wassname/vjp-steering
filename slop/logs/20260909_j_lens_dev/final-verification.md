# Final verification output (v14 DEV comparison sign-off pack)

-- PI[Kimi K3], 2026-09-09. All values machine-read on 2026-09-09, not reconstructed.

## Frozen identity
- DEV15 cohort SHA256: `c0b64ebf1713f71fa5ae6218fbbcb866b15402a98adbead8caf88d5a6a129874` (15 ordered scenarios)
- Shared bare (provenance-canonical hashes, quoted verbatim from dev-comparison-provenance.json):
  source_experiment `j-lens-paper-native-sycophancy-v1`,
  path `outputs/experiments/j-lens-paper-native-sycophancy-v1/bare.jsonl`,
  file SHA256 `2c2e2fa1efa51290841877adbb1b02edb053cc99e911d9e06e973193442fdbeb`,
  selection `ordered scenario-ID match; each selected record has profile=dev, status=DEV, side='', and coefficient=0.0`,
  selected_records_canonical_sha256 `da588b04d6a15488c9e6734ae0174400a4c7d8286bed7266a9ee5850b81d5460`,
  source_manifest_sha256 `562fcc44ffb473453f5985a96ec479af0a7e9718419e830f90414a933aec8b3e`
  (Correction: an earlier draft cited `9a696bde…` — that is the SHA256 of the per-experiment
  bare.jsonl COPIES, e.g. `outputs/experiments/v14-dev-random-s0-r2/bare.jsonl` (identical bytes in
every experiment dir checked: s0, s1, swap-L16 — same 15 records under rewritten serialization),
  not the canonical source file. The canonical values above govern.)
- Generation: Qwen/Qwen3.5-4B, bfloat16, Qwen3 chat, max_length 384, max_new_tokens 512
- Judging: paired AB/BA x 1 pass, frozen rubric `results-demo-perresponse-syco-v7`,
  model deepseek/deepseek-v4-flash-0731

## Method inventory (results/dev-comparison.csv: 279 rows)
| method | rows | sides |
|---|---|---|
| j_lens_swap (13-21 band) | 21 | +C/-C |
| j_lens_swap_L16 | 29 | +C/-C |
| j_lens_unit_L16 (ActAdd control) | 29 | +C/-C |
| j_lens_injection_L16 (flattering/abrasive) | 10 | +C/-C |
| j_lens_injection_doubt_L16 (trusting/doubtful) | 10 | +C/-C |
| mean_diff | 24 | +C/-C |
| vjp_delta | 21 | +C/-C |
| random (5 seeds) | 135 | +C/-C, calibrated rungs +C[0,1,9] -C[9] |

## Cost ledger vs ceilings
- v14 allocation: $20.00 ($9.00 remote + $2.00 paired judging + $9.00 post-comparison reserves)
- Judging recorded (cost_usd records, one positive record per key, zero duplicates/zeros):
  v14 total $0.9904; extension $0.0380 new + $0.0078 historical; injection $0.0497 (upper bound);
  doubt $0.0446 → paired-judging reserve $2.00 holds with ~$0.91 verified unused ($0.25 retained for retries)
- Modal generation: NO receipts exist anywhere; wall times recorded (876: 497s, 882-886: 288s total,
  913: 126s, 918: 105s); unknown billing retained under existing reserves, never assumed zero
- Review reserve $12.00: separate, untouched by v14 work
- Bounded diagnostics actuals: extension ~$0.322, injection ~$0.17, doubt ~$0.15 — each vs its ceiling

## Uncertainty conclusion (binding)
Paired bootstrap + exact permutation (slop/logs/20260909_j_lens_dev/escape_bootstrap.log):
doubt -C4 vs best -C rung +0.0167, 95% CI [-0.240,+0.273], p=0.98;
swap-L16 +C vs best +C rung +0.407, CI [-0.407,+1.220], p=0.45;
vs +C id0 best -0.853, CI [-1.263,-0.433], p=0.049 (a loss).
The frozen DEV15 cohort cannot statistically resolve the two-direction discriminator.
Options: accept descriptive plots, expand scenario cohort (new scope decision), or stop.
