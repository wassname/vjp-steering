# V14 random controls at low damage

- author: PI/OpenAI
- scope: offline read of the five completed matched DEV random result CSVs. No new generation or judging.

## Observation

The calibrated-rung envelope is intentionally strict: a normalized rung requires one coherent result from every seed. It has two +C rungs and no -C rung. This does not mean that no low-damage random controls exist.

Each seed also has the predeclared actual-`C=1` calibration probe. It was excluded from the normalized-rung envelope because it is an inserted probe rather than a common fraction of every seed's `C_approx`; including it as a fraction would shift rung identities. It is still a matched, measured five-vector comparison at a common actual coefficient.

| side | five C=1 effects | five C=1 damages | comparison J-lens point |
|---|---|---|---|
| +C | -0.610, +0.400, +0.650, +0.273, +0.037 | 0.170, 0.147, 0.147, 0.097, 0.230 | +0.080 at 0.040 |
| -C | -0.483, -0.913, +0.343, -0.227, -0.030 | 0.170, 0.373, 0.310, 0.393, 0.300 | -0.513 at 0.130 |

Source: `slop/logs/20260909_j_lens_dev/random-rung-coverage.log`; raw points are in `results/dev-comparison.csv`.

The J-lens +C result is inside the observed C=1 random effect range. The J-lens -C result is also inside the observed C=1 random effect range, though its 0.130 damage is a little below the lowest C=1 random damage (0.170). This supports neither a J-lens advantage nor a comparison based only on the high-damage random peaks.

## Why the -C envelope is empty

At normalized -C rung 0, seeds 2 and 3 are inadmissible. At rung 1, seeds 2 and 3 are again inadmissible; higher rungs have further inadmissible measurements. The strict all-five rule therefore produces no -C filled region. The failed entries are preserved in the result CSVs; they are not replaced by nearest doses.

## Prepared, not launched, lower-dose extension

If a future repaired J-lens point needs a strength-matched low-damage random comparison, generate exactly one new fraction `0.40 * C_approx` in each direction for the same five seed values, shared DEV15 bare records, generation config, and AB/BA rubric. Record it as normalized rung `low_extension_0p40`, not as a renumbering of existing rungs. It would add at most 10 remote generation cells plus their paired judgments, under the separately reserved $5.00 in `v14-budget.json`. Do not launch this extension before the paper/operator diagnostic supplies a candidate repair.

-- PI/OpenAI
