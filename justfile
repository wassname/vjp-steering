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

check: smoke results notebook
