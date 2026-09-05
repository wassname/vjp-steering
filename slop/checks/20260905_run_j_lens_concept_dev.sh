#!/usr/bin/env bash
# PI/OpenAI Codex: bounded DEV, preserving old experiments and public plots.
set -euo pipefail
log=slop/logs/20260905_j_lens_concept/dev.log
{
  echo "COMMIT: $(git rev-parse HEAD)"
  echo 'COMMAND: uv run python scripts/experiment.py j_lens_concept --dev'
  echo 'SHOULD: six DEV cells, 15 rows each, same vector hash with opposite coefficient signs; no public rendering.'
  sha256sum results/plot.png results/plot_pareto.png outputs/experiments/j-lens-transfer-formative-v2/extraction/metadata.json
  uv run python scripts/experiment.py j_lens_concept --dev
  sha256sum results/plot.png results/plot_pareto.png outputs/experiments/j-lens-transfer-formative-v2/extraction/metadata.json
} 2>&1 | tee "$log"
