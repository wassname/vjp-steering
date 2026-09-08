# Final-prompt DEV launch

PI/OpenAI Codex, 2026-09-08.

Preflight passed locally and received focused independent PASS review in [j_lens_final_prompt_preflight_review.md](../../reviews/j_lens_final_prompt_preflight_review.md). The launch is within the existing `$3.00` reservation: one 900-second H100 container, no automatic retry, and up to `$1.00` for unchanged-rubric AB/BA judging after generation passes raw-response audit.

Frozen generation contract:

- experiment: `j-lens-concept-dev-repair-v3-final-prompt-c025`
- source vector: `j-lens-concept-dev-v1`, SHA256 `8841bc93cf13558a0b01c61d8fdeb737437ee82389754c786d4dd02f351e0f97`
- changed factor: patch only the final real chat-prompt token
- application: layers 18-24, `-C=.25`
- arms: bare, J-lens minus, seeded norm-matched random-minus
- cohort and decoder: frozen DEV-15 order and greedy 512-token decoding
- judge: unchanged rubric, AB and BA mapped once to arm identity

The run cannot authorize all-100 generation or a public plot update. It first requires complete raw outputs, an independent raw-response audit, unchanged-rubric AB/BA judgment, and an independent endpoint review.
