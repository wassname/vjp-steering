# Empirical-candor DEV generation audit

Scope: raw generation and execution provenance only. This audit does not score candidness or select an endpoint.

## Result

The three DEV arms are pairable for unchanged candidness AB/BA judging:

| arm | rows | source side | behavior target | coefficient |
|---|---:|---|---|---:|
| bare | 15 | empty | candidness | 0.0 |
| source | 15 | +C | candidness | 0.5 |
| seeded Gram-matched random control | 15 | +C | candidness | 0.5 |

All three have the same 15 scenario IDs and byte-identical prompts per scenario. All 45 responses are complete, readable two-sentence answers. The audit found no refusal template, truncation, role-token leakage, or repeated-response pattern.

The source differs from bare on 15/15 rows and from random on 15/15 rows. Random equals bare on 8/15 rows. These are text-difference facts, not behavioral success claims.

The source and random interventions differ in realized execution while sharing the requested mask. The source final-token mean KL from bare is 0.08884294 and mean logit-delta norm is 175.8067. The random control values are 0.00311300 and 30.2873. Both use all attended prefill positions, with zero selected padding positions.

## Provenance

- Artifact: `outputs/experiments/j-lens-components-empirical-candor-dev-v1/`
- Source vector SHA256: `dd4e78e9c429e51e4fe2d4e70e0db28c96d5c4c218b5f317767393ac38883197`
- Random vector SHA256: `3817b2b56c977eb07ea505ceba5a780b5ce4d824b5df94413b9442d0e2584710`
- Layers: 13-21
- Operator: `mean100-gp16-reconstruction-target-ordered-coordinate-exchange-all-prefill-v8`
- Mask: `all_attended_prefill_positions`
- Full independent audit artifact: `/home/code/.pi/agent/sessions/--workspace-2026-jspace-j-steer_pub--/subagent-artifacts/outputs/22aec613-2988-4348-bdb5-307a06db4ead/slop/reviews/j_lens_empirical_candor_dev_generation_audit.md`
- Source manifest summary: `slop/logs/20260908_j_lens_concept_repair/empirical-candor-dev-manifest-summary.json`

## Decision

Generation admission passes. Run unchanged candidness AB/BA judging next. Do not infer candidness improvement or authorize all-100 from this audit.
