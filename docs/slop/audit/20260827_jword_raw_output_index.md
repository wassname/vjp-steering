# J-word full-cohort raw outputs

Each source has 300 JSONL records: bare at lines 1-100, +C at lines 101-200, and -C at lines 201-300. The three line-1, line-101, and line-201 records share `scenario: "syco_bullshit_v2_leg_pnf_01"`; they are a complete, side-by-side sample selected by fixed line position rather than outcome.

| C | raw bare/+C/-C output |
|---:|---|
| 0.5 | [`moral_demos.jsonl:1,101,201`](../../outputs/run_20260827T085318_J_word_s0_c0p5/moral_demos.jsonl) |
| 0.25 | [`moral_demos.jsonl:1,101,201`](../../outputs/run_20260827T085320_J_word_s0_c0p25/moral_demos.jsonl) |
| 0.125 | [`moral_demos.jsonl:1,101,201`](../../outputs/run_20260827T085321_J_word_s0_c0p125/moral_demos.jsonl) |
| 0.0625 | [`moral_demos.jsonl:1,101,201`](../../outputs/run_20260827T085322_J_word_s0_c0p0625/moral_demos.jsonl) |
| 0.03125 | [`moral_demos.jsonl:1,101,201`](../../outputs/run_20260827T085324_J_word_s0_c0p03125/moral_demos.jsonl) |

At C=0.5, the first +C sample contains repeated `<think>` text and the first -C sample repeats `abrasive`. At C=0.25 and lower, the first +C and -C samples are complete responses to the same prompt. This index does not establish aggregate quality. The health statistics and judge result are in the corresponding `J_word.json` and `data/results.csv` records.
