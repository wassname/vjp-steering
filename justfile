set dotenv-load

smoke:
	uv run python -m jsteer.smoke

results:
	uv run python -m jsteer.results

notebook:
	uv run marimo check nbs/demo.py
	mkdir -p outputs/notebooks
	uv run marimo export html --force nbs/demo.py -o outputs/notebooks/demo.html

check: smoke results notebook
