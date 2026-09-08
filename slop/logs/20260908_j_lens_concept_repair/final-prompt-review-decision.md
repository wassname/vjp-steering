# Final-prompt DEV review decision

PI/OpenAI Codex, 2026-09-08.

## Decision: STOP this endpoint before all-100

The final-prompt application test does not meet the v13 endpoint condition: a task-responsive J-lens arm clearly better than its same-sign random control under the unchanged rubric and AB/BA accounting.

The generation audit passed. This establishes pairable, responsive output. It does not establish target effect.

- J-lens `-C=.25` raw candidness effect: `+0.2600`.
- Random-minus raw candidness effect: `+0.2267`.
- Difference: `+0.0333`.
- J-lens has a slightly lower mean off-axis delta (`-0.0333` versus `-0.0267`), but a higher absolute steered off-axis score (`1.1700` versus `1.0433`). These are different comparisons.
- Eleven of fifteen J-lens/random responses are byte-identical. The remaining apparent difference is concentrated in measurement-sensitive `phys_pnf_01`, where J-lens reverses between AB and BA and an exact-equal random/bare pair has nonzero effect.
- TCA is shared by J-lens and random-minus. The prior TCA result remains a local correction observation, not an endpoint-selection result.

The final-prompt patch changed application position exactly as planned. This negative endpoint result does not establish that position mismatch caused the older narrow effect, or that final-prompt application cannot ever work. It rejects this bounded final-prompt `-C=.25`, upper-layer endpoint as sufficient evidence for all-100.

## Scope

- Do not generate all-100 results.
- Do not edit `data/results.csv`, `results/index.md`, `results/index.html`, or `results/plot.png`.
- Preserve the complete records, execution-mask provenance, response audit, and judgment audit.
- Both research goals remain OPEN.
