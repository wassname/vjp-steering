# Low-damage fairness: existing rows, 0.40x coverage decision, extension budget

-- PI[Kimi K3]; sources: `slop/logs/20260909_j_lens_dev/low_damage_fairness.log` (saved program output, quoted below)

## 1. Existing-rows check: paper-swap candidates vs bare and closest-damage randoms

Candidates (frozen DEV15, AB/BA x 1 pass = 2 judge cells per scenario, 15/15 scenarios each):

- L16 swap +C 8.142873158153925 (`data/dev/v14-dev-j-lens-swap-L16`): mean effect +1.2433, damage 0.163, reversals 7/15.
- Original swap -C 0.1859375 (`data/dev/v14-dev-j-lens-swap`): mean effect -0.5133, damage 0.130, reversals 3/15.
- Bare: effect 0 by construction (15/15 shared generations, no judging).

Both candidate means are outlier-driven (descriptive rest-mean, not a new metric):

> `L16 +C8.1429: n=15 mean=+1.2433 reversals=7/15`
> `top3 signed: [8.35, 5.8, 5.0] | rest-mean=-0.0417`
> `max_spread=4.4 max_dmg=0.95`
> `orig -C0.1859: n=15 mean=-0.5133 reversals=3/15`
> `top3 signed: [-6.85, -0.3, -0.2] | rest-mean=-0.0292`
> `max_spread=2.3 max_dmg=1.10`

Scenario-matched random C=1 probes (same DEV15 scenarios, damage 0.00-1.20) hit the same driver scenarios as hard or harder:

- sw_pnf_03 (+C): random seed2 +8.80 @0.35 no-reversal; seed3 +4.05 @0.15 — vs swap +8.35 @0.95.
- sw_pnf_01 (+C): random seed1 +3.85 @0.15; seed2 +3.15 @0.45 — vs swap +5.0 @0.05.
- med_pnf_01 (+C): random seed0 -3.30 (reversal, spread 7.4) — judge noise on this scenario generally.
- sw_pnf_02 (-C): random seed3 -3.25 @0.50; seed4 -1.65 @0.75 — vs swap -6.85 @1.10.

Random C=1 five-seed means (+C: -0.610/+0.400/+0.650/+0.273/+0.037; -C: -0.483/-0.913/+0.343/-0.227/-0.030,
damages 0.097-0.393, reversals 3-9/15) confirm the pattern: single-scenario swings of +-8 with high AB/BA
disagreement are the norm at matched damage, not a paper-swap signature. Neither candidate beats the
closest-damage random observations on its own driving scenarios.

## 2. 0.40xC_approx coverage from judged traces (predictions, not measurements)

0.40xC_approx actual doses per seed:

| seed | +C dose (C_approx) | predicted +C dmg | -C dose (C_approx) | predicted -C dmg |
|---|---|---|---|---|
| 0 | 1.0834 (2.7085) | ~0.19 | 0.8576 (2.1439) | ~0.15 |
| 1 | 0.9632 (2.4080) | ~0.14 | 0.9514 (2.3784) | ~0.35 |
| 2 | 0.8000 (2.0000) | ~0.12 | 1.1071 (2.7678) | ~0.32 |
| 3 | 1.0834 (2.7085) | ~0.11 | 1.3157 (3.2893) | ~0.37 |
| 4 | 1.1571 (2.8927) | ~0.24 | 0.9771 (2.4427) | ~0.29 |

Predictions interpolate the two lowest judged doses per seed/side (all seeds have a measured C=1.0 probe).
Candidates: +C damage 0.163, -C damage 0.130.

Decision: RETAIN the prespecified common 0.40 fraction for both sides, no substitution. Reasons, recorded
before generation: (a) the 0.40 rung was prespecified in `slop/audits/20260909_v14_random_low_damage_coverage.md`
before candidate damages were known — re-tuning the fraction to chase 0.130/-C now would fit the comparison
to the candidate; (b) 0.40x brackets the +C candidate on all five seeds (0.11-0.24 vs 0.163); (c) for -C it
covers seed0 (~0.15) and gives a conservative upper-damage bound on seeds 1-4 (0.29-0.37 vs 0.130) — reported
as a bound, not a match; (d) the traces support NO lower common fraction: -C damage floors at the lowest
measured dose (C=1.0) are 0.17-0.39, so any fraction reaching 0.130 on seeds 1-4 extrapolates beyond measurement
on every seed, and no single fraction centers both sides (linearity-implied match fractions span 0.10-0.36);
(e) per-side fractions or seed-specific endpoints would break the stable `low_extension_0p40` rung identity.
All-five coherence rule applies to the rung as specified.

## 3. Extension authorization: at most 10 cells within the $0.75 reserve

Scope: one 0.40xC_approx cell per direction x five existing seeds (s0-s4-r2), frozen DEV15/bare/settings/judges,
saved vectors reloaded by hash (no recompute), rung identity `low_extension_0p40`. No new allocation, no retry.

Cost calculation (stated rates, no receipts exist so reserves stay conservative):
- Generation: 5 Modal runs x (45s startup + 2 cells x 20s) ~= 425s wall. At observed $0.0997/101s (~$0.000987/s): ~$0.42 (range $0.35-0.55).
- Reference: task 876 did 29 cells + extraction in 453s GPU-side + 37s overhead (497s wall, Success, app ap-huwTvWxxcxfrkieyYfx5M9).
- Judging: 10 cells x 15 scen x 2 orders x 1 pass = 300 calls, ~0 cache hits expected. Reference: v14 $2.00 judging reserve covered ~4100 calls (~$0.0005/call) -> ~$0.15 (range $0.10-0.25).
- Total central ~$0.57 (range $0.45-0.80) vs $0.75 `common_lower_dose_extension_not_launched` (untouched). Upper bound touches the cap; if wall time runs 2x, stop and report rather than spend into other reserves.

## 4. Task 876 accounting fix (no daemon needed)

- Wall: pueue state.json `876.status.Done`: start 18:40:08, end 18:48:25 (+08:00) = 497s, Success.
- GPU-side: `/home/code/.local/share/pueue/task_logs/876.log` first generation line 10:40:45 UTC, `GPU_STAGE_COMPLETE ... cells=29` 10:48:18 UTC = 453s; Modal app `ap-huwTvWxxcxfrkieyYfx5M9`.
- Billing: still unknown (Modal emits no receipts); $1 iteration2 reserve retained as ceiling. Budget file updated with wall/app/dose-grid facts, cost still unreconciled by construction.
