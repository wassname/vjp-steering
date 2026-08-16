set dotenv-load

smoke:
	uv run python -m jsteer.smoke

results:
	uv run python -m jsteer.results

notebook:
	uv run marimo check nbs/demo.py
	uv run --with nbformat marimo export ipynb nbs/demo.py -o nbs/demo.ipynb

check: smoke results notebook
