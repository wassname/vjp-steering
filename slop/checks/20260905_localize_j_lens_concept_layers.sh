#!/usr/bin/env bash
# PI/OpenAI Codex: localize the unchanged concept contrast before changing its representation.
set -euo pipefail
{
  echo "COMMIT: $(git rev-parse HEAD)"
  echo 'WHY: both signs of the all-layer contrast moved judged behavior negative; test whether repeated layer application causes the non-bipolar response.'
  echo 'SCALE: each band uses the same within-vector per-layer coefficient as the health-clean all-layer C=0.125 cell. Each manifest records realized patch/residual ratios and final-token KL; do not compare this coefficient across methods.'
  for band in lower:6,7,8,9,10,11 middle:12,13,14,15,16,17 upper:18,19,20,21,22,23,24; do
    name=${band%%:*}
    layers=${band#*:}
    id="j-lens-concept-dev-v3-${name}"
    echo "COMMAND: uv run python scripts/experiment.py j_lens_concept --dev --experiment-id ${id} --reuse-extraction-from j-lens-concept-dev-v1 --concept-layers ${layers} --coefficients-plus 0.125 --coefficients-minus 0.125"
    uv run python scripts/experiment.py j_lens_concept --dev \
      --experiment-id "$id" \
      --reuse-extraction-from j-lens-concept-dev-v1 \
      --concept-layers "$layers" \
      --coefficients-plus 0.125 \
      --coefficients-minus 0.125
  done
} 2>&1 | tee slop/logs/20260905_j_lens_concept/layer-localization.log
