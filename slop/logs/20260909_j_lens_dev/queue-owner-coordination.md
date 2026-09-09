# Shared default queue coordination

At 2026-09-09T12:12+08:00, `01a08431` (the idle session at `/workspace/2026/LUCID3_wikit`) reported that task 815 remained `Running`; it did not pause `default` and could not identify the pause owner from Pueue state. It said there is no automatic resume procedure and that explicit approval from wassname or the queue owner is required before resuming `default`.

The current v14 worker will leave `default` paused. Resume event: explicit approval from wassname or the queue owner after task 815 is no longer using the GPU.

-- PI/OpenAI
