#!/usr/bin/env bash
# PI/OpenAI Codex: grid chosen from one positive-side prompt; negative side uncalibrated.
set -euo pipefail
{
  echo "COMMIT: $(git rev-parse HEAD)"
  echo 'GRID_PROVENANCE: C=.125,.25,.5 produced responsive text on one positive-side prompt; this does not establish cohort-wide or negative-side validity.'
  sha256sum outputs/experiments/j-lens-concept-calibration-v1/calibration.json
  sha256sum results/plot.png results/plot_pareto.png outputs/experiments/j-lens-concept-dev-v1/manifest.json
  echo 'COMMAND: uv run python scripts/experiment.py j_lens_concept --dev --experiment-id j-lens-concept-dev-v2-calibrated --reuse-extraction-from j-lens-concept-dev-v1 --coefficients-plus 0.125,0.25,0.5 --coefficients-minus 0.125,0.25,0.5'
  uv run python scripts/experiment.py j_lens_concept --dev --experiment-id j-lens-concept-dev-v2-calibrated --reuse-extraction-from j-lens-concept-dev-v1 --coefficients-plus 0.125,0.25,0.5 --coefficients-minus 0.125,0.25,0.5
  sha256sum results/plot.png results/plot_pareto.png outputs/experiments/j-lens-concept-dev-v1/manifest.json
} 2>&1 | tee slop/logs/20260905_j_lens_concept/calibrated-dev.log
