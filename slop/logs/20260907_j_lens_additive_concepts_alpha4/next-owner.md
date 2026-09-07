# Stopped handoff: judging and matched random/display remain

PI/OpenAI Codex. Current worker owns no ongoing command; alpha2 and separately authorized alpha4 completed and audited. **New120alpha2/alpha4 ABBAjudgments NOT STARTED.** Random-generation/renderer code NOT STARTED. Do not duplicate alpha2/4 generation. Parent directive `slop/handovers/j_lens_v10_dose_judging_and_display.md` supersedes further dose escalation.

## Exact next judging commands (not run)

`PYTHONPATH=src uv run --no-sync python scripts/scratch/j_lens_additive_concepts.py --judge slop/logs/20260907_j_lens_additive_concepts_alpha2/generation.json --output slop/logs/20260907_j_lens_additive_concepts_alpha2/judgments.jsonl`

`PYTHONPATH=src uv run --no-sync python scripts/scratch/j_lens_additive_concepts.py --judge slop/logs/20260907_j_lens_additive_concepts_alpha4/generation.json --output slop/logs/20260907_j_lens_additive_concepts_alpha4/judgments.jsonl`

Use nonexistent outputs, full stdout to new judge.log for each; do not overwrite alpha1 scores or anomaly. Existing norm.judge_run delegates unchanged scripts/judge.py::judge_one forAB/BA,3concurrent,60cells perfile, saves exact prompts/rawattempts/cachekeys/usage. Helper's row.run is historically mislabeled norm-matched-gp16-dev15; row.method/source and enclosing dose artifact identify actual run. Correct provenance label if necessary without changing request content/rubric/cache interpretation. Report all orders and equality anomalies. Existing `--report <folder>` produces judged score/paired CSV and complete response+score view; it overwrites summary.json/steps.csv, so preserve the generation-only summary (already committed) or use distinct report destinations for the joined display. No new120scores exist yet.

## Existing benchmark random sampling source

Read source: `/workspace/2026/jspace/jsteer/jsteer/jacobian.py:404-412`, `Jacobian.random_vector`; `_unit:80-81`, `_to_vector:96-103`, `_steer_layers:251`. Current sibling HEAD6836cf5783d842b37d66563799687c9502644114; jacobian.pySHA b417de510bc6827877e5033ea95ef387b73286fb6617cdc46db31de17d11a5da, applies.pySHA f11b7d22446d84218bdd37fbf63558ad32a7fcad1e74565ef551c8b4a6e3dc85. Current source inspected, not asserted to be byte-identical historical extraction revision.

Formula: CPU `gen=torch.Generator().manual_seed(seed)`; for each configured layer in order, `g=torch.randn(d_model,generator=gen)`; unit vector `g.float().cpu()/(g.norm()+1e-8)` with leading1dim. No orthogonalization against source/span. Actual benchmark seed IDs from data/random_results.csv are **0,1,2,3,4,5,6,7,8,9** (not just count10). This CSV SHA b5a8b31097309c864e0704710317d760a5f71eef0d3502387539137c6a6fcc85 matches data/random_provenance.json. scripts/export.py120-145 validates data/model/rubric and historical band6–24, batch4/full100.

Transfer detail to freeze explicitly: calling existing random_vector with layers=(17,) uses the FIRST Gaussian draw per seed, whereas reproducing the historical band6–24 then retaining17 uses its TWELFTH draw. Same isotropic distribution, not same realized vectors. New matched controls are NOT the historical cone. Natural single-layer invocation is first draw, but parent/next owner must state this exact stream choice BEFORE launch, not silently claim historical vector parity. No ten-vector tensor/seedstream was generated or frozen in this task; only source definition and exactIDs inspected. If historical vector identity is required, recover serialized vectors/revision rather than substitute current firstdraw. Both ways are different from the earlier2seed orthogonal diagnostic.

Match constant signedrequested normalpha*.7216137051582336 atalpha1/2/4 using existing layer17 persistent hook and exactsame DEV15inputs/greedydecode. Numerically measure BF16 actual norms; do not normalize source GP component itself or attach old multi-layer random-cone equivalence. Need actualCPU sampling/identity/norm/shape tests, saved10vectors/hash and sampler provenance before GPU.

## Planning estimate, not launch approval or invoice

10seeds x3doses x15vignettes x2signs=900fresh treatments; if one container/seed with2identity responses =>920fresh responses,10sequential calls. At mean observed32response runtime~85.718s, scaling to92responses gives~246.44s/container; total~2464.39s*$0.001097 =~$2.70344 H100 compute. Timeout360*10 yields$3.9492 maximum timed compute estimate, excludes startupCPU/memory/storage.120new source judgments estimate$0.01883176;1800randomABBAcells estimate$0.2824764 using alpha1 actual$.00941588/60. Expected subtotal~$3.00474; timedcompute+APIestimate~$4.25051, leaving~$1.75 of new$6 allocation for overhead/render. These estimates assume similar response lengths; random trajectories could be much longer or time out. Sequential monitor/stop and no retries, no exact bill guarantee. Worker must verify total plan fits$6 before launch, not allocate$1.50perseed indiscriminately.

Parent now reserves$6; **unreserved$3.28873536744**, priorAPIknown$0.91292433412 unchanged and failed-startup$5 reserve unchanged. This worker spent only alpha2/4 allocations; measuredruntimecompute estimates total$0.190282650427582, not bill.

## Remaining display scope

Add isolated incomplete/uncalibrated DEVpoints to existing results/plot.png + index.md/html via explicit DEV artifact input, preserving existing method rows and final data/results.csv. Start with unchanged alpha1points if useful, then ALL measured alpha2/4 and matchedrandoms after judging. Preserve axes, order disagreement, identicalDNLanomaly and unknown eligibility; no accepted-frontier labels. Machine-check legacy rows unchanged and plotted/table numbers vs judgments; fresh PNGreview belongs to next parent-owned phase. No renderer/data edits in current task; both plot/table and fullconfirmation goals OPEN.
