#!/usr/bin/env bash
# PI/OpenAI Codex: test J-space projection of matched persona prompt states.
set -euo pipefail
{
  echo "COMMIT: $(git rev-parse HEAD)"
  echo 'WHY: the Tell-me-about concept vector made both signs more skeptical in lower layers. This source uses matched prompts that differ only in the requested persona.'
  echo 'SCALE: nominal values label unit per-layer additions only. The manifest records realized patch/residual ratios and final-token KL for every cell; interpret behavior against those measurements, not against coefficients from another representation.'
  echo 'COMMAND: uv run python scripts/experiment.py j_lens_concept --dev --j-lens-source persona --experiment-id j-lens-persona-jspace-dev-v1 --coefficients-plus 0.03125,0.0625,0.125 --coefficients-minus 0.03125,0.0625,0.125'
  uv run python scripts/experiment.py j_lens_concept --dev --j-lens-source persona \
    --experiment-id j-lens-persona-jspace-dev-v1 \
    --coefficients-plus 0.03125,0.0625,0.125 \
    --coefficients-minus 0.03125,0.0625,0.125
} 2>&1 | tee slop/logs/20260905_j_lens_concept/persona-jspace-dev.log
