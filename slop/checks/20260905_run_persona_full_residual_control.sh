#!/usr/bin/env bash
# PI/OpenAI Codex: diagnostic control. This is not a J-lens result.
set -euo pipefail
{
  echo "COMMIT: $(git rev-parse HEAD)"
  echo 'QUESTION: did the sparse J projection, rather than the matched persona residual source, remove the causal style signal?'
  echo 'CONTROL: normalize and apply the complete paired residual difference at each layer. The source prompts, layer set, signed additive operator, generation, cohort, and nominal scales match j-lens-persona-jspace-dev-v1. Interpret behavior with realized patch/residual ratios and KL.'
  echo 'COMMAND: uv run python scripts/experiment.py j_lens_concept --dev --j-lens-source persona --persona-direction full_residual --experiment-id persona-full-residual-control-dev-v1 --coefficients-plus 0.03125,0.0625 --coefficients-minus 0.03125,0.0625'
  uv run python scripts/experiment.py j_lens_concept --dev --j-lens-source persona --persona-direction full_residual \
    --experiment-id persona-full-residual-control-dev-v1 \
    --coefficients-plus 0.03125,0.0625 \
    --coefficients-minus 0.03125,0.0625
} 2>&1 | tee slop/logs/20260905_j_lens_concept/persona-full-residual-control.log
