# Final publication verification: 39 DEV points, incomplete

PI/OpenAI Codex. Finalization resumed through the same worker protocol after the prior session timeout. Process inspection found no active render, precheck or projection command; no generation or judging was repeated.

## Preserved failures and correction

`display-capture.log` is empty from a local60s capture timeout. `display-capture-final.log` records an assertion failure expecting38 points from the older36-point judged-display manifest. The correct prior38-point manifest is `slop/logs/20260907_j_lens_single_concept/manifest.json`. The corrected capture passed in `display-capture-corrected.log`; no scores or historical manifests were modified. The new20-artifact manifest lives in this projection-removal directory and appends just this15-treatment/30-judgment artifact.

## Actual output and machine checks

`render.log`: same existing results renderer, EXIT_CODE=0. Outputs: `results/plot.png`, `results/plot_pareto.png`, `results/index.md`, `results/index.html`.

`display-check.log`: PROJECTION_DISPLAY_PASS, EXIT_CODE=0:

-38 prior points exactly unchanged;39 total DEV points.
-800 primary rows and39 historical trace definitions unchanged.
-New minus-only point effect+0.040000, AB+0.100000, BA−0.020000, damage0.0866667.
-Actual saved Markdown and HTML contain exactly the generated section and its numeric cells.

`export-display-check.log`: independent existing-export-axis reconstruction passes for all39 points; primary CSV SHA256 remains `2802acd96b16a67b05c284133d711257068f8dec937b1c949dbf59c8ca0a6c20`.

Worker opened the actual regenerated `results/plot.png`: the new magenta outlined cross is near effect0.04/damage0.087, visible amid the near-origin DEV cluster. The unchanged legacy curves remain visible. The three-line footer is not clipped and explicitly labels projection removal as minus-only, fraction1, state-dependent and NOT norm-matched to random. The random label remains5/10 seeds; no frontier claim. The plot area is slightly shorter to fit the additional disclosure; numerical trace definitions are unchanged. Dense near-origin points still overlap visually; exact values and requests are available in the table and links.

The table labels the new dose cell `fraction1` rather than disguising it as constant additive alpha1. Public notes disclose the −0.140 comparison decomposition: baseline rescoring−0.283333 plus steered-score contribution+0.143333. No raw result or score is replaced.

The initial41-file immutable check is preserved in `audit-before-display.log`; following separately authorized publication, rerunnable `audit.py` retains37 immutable raw/primary-data hashes and delegates the intentional public-output change to `display_check.py`. Final numerical verification is `audit.log`.

## Scientific decision and budget

Parent communicated the completed non-Claude review a529a256: all30 raw mappings and baseline identity verified; no supported next paid repair. Successful projection removal does not establish topic-to-behavior transfer. The −0.14 aggregate difference is not a corrected score or noise estimate; baseline attribution dominates it. Both research goals remain OPEN, including incomplete5/10 controls and absent full confirmation.

Budget remains$2.01988872744 unreserved, with the entire$0.60 allocation and all previous unknown-charge reserves retained. Actual API$0.00477288; cumulative reported API$1.08584037412. Runtime-only GPU estimate$0.0577136812 is not an invoice. No further paid work is authorized. No GPU/API call was made during this resumed display-only finalization.
