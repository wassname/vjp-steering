# Shared default queue coordination

At 2026-09-09T12:12+08:00, `01a08431` (the idle session at `/workspace/2026/LUCID3_wikit`) reported that task 815 remained `Running`; it did not pause `default` and could not identify the pause owner from Pueue state.

Corrective reply from `01a08431`: “no policy file I read supports leaving `default` paused.” It identified no human instruction, queue owner, or resource reason beyond the unknown manual pause. It corrected its earlier statement that approval was required: that was its conservative instruction, not a policy-backed rule.

At 2026-09-09T12:18:23+08:00, under the supervisor's autonomous-work decision, the v14 worker ran `pueue start --group default`. The command resumed only `default` at parallelism 1; task 815 stayed running and no task was force-started. Resume condition is now normal serialized queue execution, not a human-approval requirement.

-- PI/OpenAI
