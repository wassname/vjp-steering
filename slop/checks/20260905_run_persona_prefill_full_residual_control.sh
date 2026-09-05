#!/usr/bin/env bash
# PI/OpenAI Codex: diagnostic control for the prefill-state J projection.
set -euo pipefail
{
  echo "COMMIT: $(git rev-parse HEAD)"
  echo 'QUESTION: does the full persona difference at the response-prefill state steer behavior when its GP16 J projection does not?'
  echo 'CONTROL: same 200 matched persona-prefill prompts, layers, additive signed patch, DEV cohort, and scales as j-lens-persona-prefill-jspace-dev-v1. Only replace unit(GP16 J component) with unit(full paired residual difference). This is not a J-lens result.'
  echo 'COMMAND: uv run python scripts/experiment.py j_lens_concept --dev --j-lens-source persona_prefill --persona-direction full_residual --experiment-id persona-prefill-full-residual-control-dev-v1 --coefficients-plus 0.03125,0.0625,0.125 --coefficients-minus 0.03125,0.0625,0.125'
  uv run python scripts/experiment.py j_lens_concept --dev --j-lens-source persona_prefill --persona-direction full_residual \
    --experiment-id persona-prefill-full-residual-control-dev-v1 \
    --coefficients-plus 0.03125,0.0625,0.125 \
    --coefficients-minus 0.03125,0.0625,0.125
} 2>&1 | tee slop/logs/20260905_j_lens_concept/persona-prefill-full-residual-control.log
