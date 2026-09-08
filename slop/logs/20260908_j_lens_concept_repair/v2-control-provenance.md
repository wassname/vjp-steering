# C=.25 random-control provenance

PI/OpenAI Codex, 2026-09-08.

Source: complete `controls` block in `outputs/experiments/j-lens-concept-dev-repair-v2-upper-c025/manifest.json`, lines 707488 onward.

| field | random-plus | random-minus |
|---|---|---|
| kind | `seeded_norm_matched_random_direction` | `seeded_norm_matched_random_direction` |
| seed | `20260908` | `20260908` |
| coefficient | `+0.25` | `-0.25` |
| random vector SHA256 | `e42ce418d7fbe4bd914a4e43eac75566c4d7b3bcdfd12dc46428cef5b5740597` | same |
| J-lens source vector SHA256 | `54213eddc983d7353cda0ce36b66effe9cf8b4d30a38b0a2bbc7b4ab84d22b69` | same |
| rows | 15 | 15 |

Per-layer source norm, random norm, and cosine:

| layer | source norm | random norm | cosine |
|---:|---:|---:|---:|
| 18 | 0.99999988 | 0.99999994 | +0.00244034 |
| 19 | 0.99999994 | 0.99999982 | -0.01641349 |
| 20 | 1.00000000 | 0.99999988 | -0.01023097 |
| 21 | 0.99999994 | 0.99999994 | -0.02208024 |
| 22 | 1.00000000 | 0.99999994 | +0.01894588 |
| 23 | 1.00000000 | 0.99999988 | -0.00536559 |
| 24 | 1.00000012 | 1.00000000 | +0.00870993 |

The reviewer statement that seed and vector hashes were absent came from incomplete context. The full manifest records them. The two controls share one seeded random vector and use opposite coefficients, matching the J-lens sign structure.
