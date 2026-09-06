# Paper-native J-lens sycophancy

> “do J-len steering right and add to the plot” — wassname

— PI/OpenAI Codex

1. [/] goal: replace the old directed unit-vector transfer with the paper coordinate exchange
   - subtle failure mode: the code still uses normalized dot-product transfer while metadata says pseudoinverse exchange
   - discriminator: alpha 0 is identity; alpha 1 exchanges both raw J-lens coordinates; saved vectors contain `basis` and `dual`
   - verify: `PYTHONPATH=src:scripts uv run python scripts/experiment.py j_lens_swap --self-test`
   - tasks:
     1. [x] use `h + alpha V(swap(V†h) - V†h)` with raw `abrasive` and `flattering` J-lens rows
     2. [x] use signed alpha: +C is coordinate exchange; -C extrapolates away from exchange
     3. [/] run the real-model pipeline smoke
2. [ ] goal: measure the coherent DEV dose range on Bullshit Bench v2
   - subtle failure mode: a generation passes repetition and truncation checks but scores well only because it refuses or ignores the question
   - discriminator: raw generations remain responsive and the judge reports intended on-axis signs with low off-axis change
   - verify: complete pueue log, DEV `results.csv`, `selected.json`, and raw first samples from every cell
   - tasks:
     1. [ ] search each signed-alpha direction for the generation-health boundary
     2. [ ] judge the local ±33% dose grid
     3. [ ] audit the complete log and raw responses
3. [ ] goal: add comparable J-lens results to the public plot
   - subtle failure mode: DEV-15 or category-token evidence is presented beside all-100 methods
   - discriminator: the plotted rows use the all-100 cohort, the same judge rubric, and the same admissibility filter
   - verify: `just results`; inspect `results/plot.png`, `results/plot_pareto.png`, and table provenance
   - tasks:
     1. [ ] run all-100 confirmation for DEV-accepted candidates
     2. [ ] merge the judged rows under `J-lens coordinate swap`
     3. [ ] regenerate and inspect both PNGs
