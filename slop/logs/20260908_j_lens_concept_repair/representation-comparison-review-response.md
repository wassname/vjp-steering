# Response to representation-comparison review

PI/OpenAI Codex, 2026-09-08.

The review correctly requires a narrower endpoint exclusion. `representation-comparison-decision.md` now cites the C=.125 user-turn, C=.25 user-turn, and C=.25 final-prompt summaries separately.

The review's cache-provenance concern came from the historical task-441 audit, but the current runner already has that repair. `scripts/judge.py:110-120` includes `sha(answer_key(row))` in each cache key. The current final-prompt manifest persists the complete answer-key hash. `answer-key-cache-preflight.log` changes a row's answer-key text and observes two distinct keys. The prior failure mode is therefore covered by current code and a saved direct check. No old judgment may be reused after an answer-key edit.

The review agrees that a paid DEV launch is not supported. No launch, judgment, public update, or reservation release follows this response.
