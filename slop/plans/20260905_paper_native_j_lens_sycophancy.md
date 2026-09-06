# Paper-native J-lens sycophancy

> “do J-len steering right and add to the plot” — wassname

— PI/OpenAI Codex

1. [x] goal: replace the old directed unit-vector transfer with the paper coordinate exchange
   - subtle failure mode: the code still uses normalized dot-product transfer while metadata says pseudoinverse exchange
   - discriminator: alpha 0 is identity; alpha 1 exchanges both raw J-lens coordinates; saved vectors contain `basis` and `dual`
   - verify: `PYTHONPATH=src:scripts uv run python scripts/experiment.py j_lens_swap --self-test`
   - tasks:
     1. [x] use `h + alpha V(swap(V†h) - V†h)` with raw `abrasive` and `flattering` J-lens rows
     2. [x] use signed alpha: +C is coordinate exchange; -C extrapolates away from exchange
     3. [x] run the real-model pipeline smoke: task 276 persisted all sides; +C changed 0/2 short outputs and -C repeated `abrasive`, so calibrate below alpha 1
2. [x] goal: measure the coherent DEV dose range on Bullshit Bench v2
   - subtle failure mode: a generation passes repetition and truncation checks but scores well only because it refuses or ignores the question
   - discriminator: raw generations remain responsive and the judge reports intended on-axis signs with low off-axis change
   - verify: complete pueue log, DEV `results.csv`, `selected.json`, and raw first samples from every cell
   - tasks:
     1. [x] boundary: +C clean through 1.097; -C clean through .136; both leak/repeat above their boundary
     2. [x] judge 22 local-grid cells; fixed the experiment exporter's missing -C axis sign
     3. [x] audit task 277 and raw responses; DEV selected +1.097 (+.02 effect) and -.1128 (-.18 effect)
3. [/] goal: add a working, comparable J-lens result to the public plot
   - subtle failure mode: DEV-15 or category-token evidence is presented beside all-100 methods
   - discriminator: the plotted rows use the all-100 cohort, the same judge rubric, and the same admissibility filter
   - verify: `just results`; inspect `results/plot.png`, `results/plot_pareto.png`, and table provenance
   - tasks:
     1. [x] run all 22 calibrated doses on the all-100 cohort with AB+BA judging
     2. [x] merge 22 dose rows and 2,200 scenario rows under `J-lens coordinate swap`
     3. [x] diagnose the fixed `abrasive`/`flattering` adaptation: it remains in the random zone and is not a working method
     4. [x] remove that failed adaptation from the public comparison; retain its standalone audit
     5. [x] test the fixed pair on the reproduced layers 13–21; both DEV points remain inside the random cone
     6. [/] audit actual next-token and J-lens activity before choosing an active-source or concept-component intervention
     7. [ ] match the paper's active-source or concept-component intervention and clear the random zone on DEV
     8. [ ] run the working method on all-100 and regenerate both public PNGs
   - evidence:
     - > `task-279-clean.log`: `JUDGE_COMPLETE required=2878 missing=0`
     - > `task-333-random-zone-check.log`: `+C ... inside_random_cone True`; `-C ... inside_random_cone True`
     - > `results/index.md`: the public table has no J-lens row while the adaptation remains unvalidated
