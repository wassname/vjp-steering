#!/usr/bin/env bash
# PI/OpenAI Codex: measure the same saved vector below C=1, without judging.
set -euo pipefail
{
  echo "COMMIT: $(git rev-parse HEAD)"
  echo 'COMMAND: uv run modal run scripts/run_modal.py::calibrate_concept'
  echo 'SHOULD: C=0 logits unchanged; record actual BF16 displacements, residual norms and next-token changes.'
  uv run modal run scripts/run_modal.py::calibrate_concept
  uv run modal volume get --force jsteer-pub-cache outputs/experiments/j-lens-concept-calibration-v1 outputs/experiments
} 2>&1 | tee slop/logs/20260905_j_lens_concept/calibration.log
