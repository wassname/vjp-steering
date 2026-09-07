# Display and repeated-request verification

PI/OpenAI Codex. Both research goals remain open. No paid experiment is authorized by this report.

## Display

Parent inspected the actual results/plot.png: hollow source/random markers near the origin, legacy curves visible, footer5/10 uncalibrated. Renderer now scopes all-100 wording to the primary table and explicitly discloses seed4 CSN identical-request BA effects -1.7 versus -7.7 (AB+0.3 both). Regeneration completed exit0 in disclosure-render.log. Numerical verification in disclosure-test.log positively reports:

> DISPLAY_TEST_PASS {"primary_rows_unchanged": 800, "legacy_traces_unchanged": 39, "DEV_points": 36, "export_axes_exact": true, "markdown_html_cells_exact": true, "primary_csv_sha256": "2802acd96b16a67b05c284133d711257068f8dec937b1c949dbf59c8ca0a6c20"}

Scores were not changed. Render launch first failed because the process tool's temporary log directory was missing; it did not register a running process. Parent recreated that directory and retried the same process protocol successfully (proc_016e). Independent oracle003c631b returned review prose but its run was reported failed, not a successful harness acceptance; its observations were independently checked here.

## Offline reliability

repeated_request_audit.py rechecks manifest judgment hashes and groups1080 saved judgments by exact(cache_key,prompt). Full groups, prompts, raw responses and source paths are in repeated-request-audit.json; command output is repeated-request-audit.log.

| Check | Observed |
|---|---:|
| Repeated request groups |92|
| Bitwise differing effect groups |60|
| Differences larger than1e-12 |56|
| Groups containing positive and negative effects |17|
| Groups containing zero and nonzero effects |21|
| Largest within-group effect range |6.6|
| Median within-group range |0.1|

The four extra bitwise differences are floating-point arithmetic, not substantive judge variation. Strict reversals and tie disagreements can overlap. The1e-12 comparison only removes arithmetic noise in this audit; no stored score or scoring threshold changes.

## All measured dose effects

Values below are cohort means, unlike the individual-request ranges above. Random means use five fixed seeds, not confidence intervals.

|Alpha|Source +|Random + mean|Source -|Random - mean|
|---:|---:|---:|---:|---:|
|1|-0.106667|-0.288667|-0.333333|-0.200667|
|2|-0.140000|-0.242000|-0.056667|-0.216000|
|4|-0.273333|-0.196667|+0.370000|-0.272667|

Source: matched_random/comparison.json and judged_display/points.json. Individual repeated-request ranges cannot be used as uncertainty intervals for these aggregate means. Nevertheless, identical inputs changing sign demonstrate that small dose differences cannot safely be attributed entirely to steering. The data do not support broad intended bidirectional steering: all source plus means have the wrong sign, and alpha4 minus also has the wrong sign. This is a descriptive finding on reused DEV and an imperfect judge, not a general rejection of J-lens or a quantified significance result. No specific source/operator repair is identified. Next useful work is measurement validation; do not select a preferred repeat or overwrite raw scores.

## Budget

Phase API reported0.15862204; cumulative API1.07154637412. Five random runs' runtime-only GPU estimate1.257058675897834, not invoice. Remaining phase allocation0.13115336 plus otherunreserved3.28873536744 gives3.41988872744. All historical and new failure/startup reserves remain. Infrastructure billing and prior timed-out API charge are unknown. No additional paid work occurred for this offline audit/render.
