set dotenv-load

smoke:
	uv run python -m jsteer.smoke

results:
	uv run python -m jsteer.results

# keep nbs/demo.py and nbs/demo.ipynb in step; existing outputs in the .ipynb survive
notebook:
	uv run jupytext --sync nbs/demo.py

# run the notebook on a GPU and store the outputs GitHub shows
notebook-run:
	uv run jupytext --sync --execute nbs/demo.py

# every notebook cell on the tiny random model, CPU, in about a minute
# the last cell needs data/results.csv, so this stays red until the measured results land
notebook-smoke:
	JSTEER_MODEL=wassname/qwen3-5lyr-tiny-random JSTEER_DEVICE=cpu JSTEER_PAIRS=2 \
	JSTEER_BATCH_SIZE=2 JSTEER_MAX_LENGTH=128 JSTEER_TOKENS=8 JSTEER_RUNGS=11 \
	uv run jupytext --to ipynb --execute -o outputs/demo_smoke.ipynb nbs/demo.py

check: smoke results notebook-smoke notebook
