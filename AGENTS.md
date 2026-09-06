<!-- HUMAN WRITTEN DO NOT EDIT -->
This repo is a public repo to compare multiple steering methods on a sycophancy benchmark. It works like this

For each steering method:
- Use N steps of search to find the dose C_calib where we think it breaks down into incoherence. We use repititions and length to find this, which has a large uncertainty compared to the more reliable judge assesments which we use for the final eval.
- For a grid of M doses `C centered around +-33% of C_calib
  - Eval bullshit benc v2
- Now we judge each evaluation for 1) on target effect 2) off target change 3) incoherence
- We filter out incoherent generations, giving us the maximum possible dose according to the judge
- We plot their coherent evals on a plot of on vs off target effects. This lets us see a) how much intervention they support before incoherence b) their pareto optimal dose

This plot has other nice featurs such as the region that random steers occur, and annotation of the corners. 

This plot, and the associated table are the output we need to produce and show to the user in order to evaluate changes. We have a dev plot with a subset of bullshit bench, and less repitations and a coarser search space, and the full plot.



For entrypoints run `just --list`

For reading finished jobs read ml-debug skill, and perhapps the moa and review skilsl to get multiple perspectives

For programing see setup-repo and token-efficient logging skills

We want clean, maintainble, simple, fail fast, readable, repeatable, pseudocode like research code.
<!-- END HUMAN -->
# LLM persistant message
