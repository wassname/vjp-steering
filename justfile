set dotenv-load

smoke:
	#!/usr/bin/env bash
	set -euo pipefail
	for method in vjp_delta mean_diff pca; do
		BEARTYPE=1 uv run python scripts/walk.py "$method" --coefficient 16 --model wassname/qwen3-5lyr-tiny-random --device cpu --dtype float32 --n-pairs 2 --batch-size 2 --max-length 128 --max-new-tokens 8 --limit 2 --layers 1 --target-layer 4 --status SMOKE_PASS
	done

walk method seed:
	HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True uv run python scripts/walk.py {{method}} --seed {{seed}} --walk

walk-dry method seed:
	uv run python scripts/walk.py {{method}} --seed {{seed}} --walk --dry-run

judge-dry:
	uv run python scripts/judge.py

judge:
	uv run python scripts/judge.py --refresh

results:
	uv run python -m vjp_steering.results

# keep nbs/demo.py and nbs/demo.ipynb in step; existing outputs in the .ipynb survive
notebook:
	uv run jupytext --sync nbs/demo.py

# run the notebook on a GPU and store the outputs GitHub shows
notebook-run:
	uv run jupytext --sync --execute nbs/demo.py

# every notebook cell on the tiny random model, CPU, in about a minute
# the last cell needs data/results.csv, so this stays red until the measured results land
notebook-smoke:
	VJP_STEER_MODEL=wassname/qwen3-5lyr-tiny-random VJP_STEER_DEVICE=cpu VJP_STEER_PAIRS=2 \
	VJP_STEER_BATCH_SIZE=2 VJP_STEER_MAX_LENGTH=128 VJP_STEER_TOKENS=8 VJP_STEER_RUNGS=11 \
	uv run jupytext --to ipynb --execute -o outputs/demo_smoke.ipynb nbs/demo.py

check: smoke results notebook-smoke notebook
