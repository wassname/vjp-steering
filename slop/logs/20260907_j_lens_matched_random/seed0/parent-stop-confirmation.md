# Parent stop verification

PI/OpenAI Codex ran `uv run --no-sync modal app stop --yes ap-yh5THLF10Dl4TQlTFdJunH`, then `uv run --no-sync modal app list --json`. The combined shell command exited 0. Stop produced no stdout/stderr, saved parent-stop.log is empty; no separate stop exit code was captured.

The subsequent saved parent-app-status.json positively reports:

```json
{"app_id":"ap-yh5THLF10Dl4TQlTFdJunH","state":"stopped","tasks":"0","created_at":"2026-09-08 03:44:23+08:00","stopped_at":"2026-09-08 03:49:58+08:00"}
```

This confirms termination, not an invoice or a count of historical container restarts. No retry launched by parent.
