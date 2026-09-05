#!/usr/bin/env bash
# PI/OpenAI Codex: behavior-state source, not a teacher-forced answer-state source.
set -euo pipefail
{
  echo "COMMIT: $(git rev-parse HEAD)"
  echo 'WHY: the teacher-forced answer-state persona contrast failed both as a GP16 J projection and as its full residual control. This run measures the final prompt state immediately before the model begins its response, matching the patched position.'
  echo 'METHOD: 200 paired generic user prompts differ only in sycophantic versus abrasive instruction. GP16 J projection, all layers, signed additive patch, and DEV-15 are otherwise unchanged. Interpret nominal values only with the saved realized patch/residual ratios and KL.'
  echo 'COMMAND: uv run python scripts/experiment.py j_lens_concept --dev --j-lens-source persona_prefill --experiment-id j-lens-persona-prefill-jspace-dev-v1 --coefficients-plus 0.03125,0.0625,0.125 --coefficients-minus 0.03125,0.0625,0.125'
  uv run python scripts/experiment.py j_lens_concept --dev --j-lens-source persona_prefill \
    --experiment-id j-lens-persona-prefill-jspace-dev-v1 \
    --coefficients-plus 0.03125,0.0625,0.125 \
    --coefficients-minus 0.03125,0.0625,0.125
} 2>&1 | tee slop/logs/20260905_j_lens_concept/persona-prefill-jspace-dev.log
