# Empirical-candor control status

PI/OpenAI Codex, 2026-09-08.

## Revived candidate review

The revived reviewer run `815996c3-2322-4b15-acf0-43e678e44414` is complete. It repeated the all-100 overlap finding: a fresh full-cohort generation contains the selection-exposed DEV-15 and is not independent confirmation. Commit `915804f` records the required wording: retain the full-cohort public result and add a separate descriptive readout for the remaining 85 rows.

## Offline control preflight

`empirical-candor-component-control-preflight.log` contains `EMPIRICAL_CANDOR_COMPONENT_CONTROL_PREFLIGHT_PASS` after the full component self-test. The stale test fixtures now provide `concept_sides` explicitly. Its JSON record preserves the v8 `+C` source hash, source layers 13-21, alpha `.5`, target-order operator, all-attended prefill mask, and behavior target `candidness` as separate fields. It also records the seeded rank-two Gram-matched control plus deterministic operator and realized prefill-hook patch differences on fixed hidden inputs. Those differences are not generation evidence.

## Independent review and job status

The first independent review found a real blocker: source `+C` would otherwise select the sycophancy judge target. The route now carries `source_side` and `behavior_target` separately into generation records, validates them against the candidate manifest, selects the judge target and cache key from `behavior_target`, and selects export sign from that same field. The updated preflight asserts candidness prompts for both source and control.

The re-review then found a second real blocker: endpoint selection used source side, so a correct `+C` source evaluated for candidness would be rejected for its negative common-axis effect. `accepted_axis_direction` now uses `behavior_target` when present. The exporter self-test and preflight both pass this case. Reviewer run `7c4b94f3-0802-4870-a564-05c3e86b25e5` terminated with `Request aborted` after reporting that blocker, so it did not provide a final acceptance verdict. A same-protocol review retry is required before launch.

The same-protocol retry passed the offline preflight. Its only renderer observation was real but post-judging: the renderer used source side for the accepted marker. `behavior_axis_direction` is now a shared source helper used by endpoint export and renderer aggregation. It treats `+C`/`candidness` as a negative common-axis effect for acceptance while retaining `+C` as provenance. The preflight now exercises the renderer aggregation with a temporary candidate manifest and confirms its point is accepted. No public output was rendered or changed.

No Modal or pueue job was created. No budget was reserved or spent. The DEV test remains blocked pending the supervisor's spend decision and evidence inspection.
