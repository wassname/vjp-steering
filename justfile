set dotenv-load

export MODAL_IMAGE_BUILDER_VERSION := "2025.06"

smoke:
	#!/usr/bin/env bash
	set -euo pipefail
	for method in vjp_delta mean_diff pca; do
		BEARTYPE=1 uv run python scripts/walk.py "$method" --coefficient 16 --model wassname/qwen3-5lyr-tiny-random --device cpu --dtype float32 --n-pairs 2 --batch-size 2 --max-length 128 --max-new-tokens 8 --limit 2 --layers 1 --target-layer 4 --status SMOKE_PASS
	done
	BEARTYPE=1 uv run python scripts/walk.py vjp_mlp_up_left_right_shrink --coefficient 1 --model wassname/qwen3-5lyr-tiny-random --device cpu --dtype float32 --n-pairs 2 --batch-size 2 --extract-batch-size 2 --max-length 128 --max-new-tokens 8 --limit 2 --status SMOKE_PASS
	uv run python scripts/export.py --self-test

experiment method *args:
	uv run python scripts/experiment.py {{method}} {{args}}

sweep method seed walk_id:
	HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True uv run python scripts/walk.py {{method}} --seed {{seed}} --walk --walk-id {{walk_id}}

sweep-dry method seed walk_id:
	uv run python scripts/walk.py {{method}} --seed {{seed}} --walk --walk-id {{walk_id}} --dry-run

queue-sweeps walk_id:
	#!/usr/bin/env bash
	set -euo pipefail
	for method in vjp_delta mean_diff pca vjp_mlp_up_shrink; do
		for seed in 0 1 2; do
			pueue add --group default -l "sweep $method seed $seed walk={{walk_id}}" -w "$PWD" -- just sweep "$method" "$seed" "{{walk_id}}"
		done
	done
	pueue add --group default -l "sweep J_word seed 0 walk={{walk_id}}" -w "$PWD" -- just sweep J_word 0 "{{walk_id}}"

judge walk_id *args:
	uv run python scripts/judge.py --walk-id {{walk_id}} --refresh {{args}}

judge-dry walk_id:
	uv run python scripts/judge.py --walk-id {{walk_id}}

judge-experiment experiment_id profile *args:
	uv run python scripts/judge.py --experiment-id {{experiment_id}} --profile {{profile}} --refresh {{args}}

export walk_id:
	uv run python scripts/export.py --walk-id {{walk_id}}

results:
	uv run python -m vjp_steering.results

modal-smoke:
	uv run modal run scripts/run_modal.py::smoke

modal-sweeps walk_id *args:
	uv run modal run --detach scripts/run_modal.py::main --walk-id {{walk_id}} {{args}}

modal-push:
	rm -rf /tmp/jsteer-push && mkdir -p /tmp/jsteer-push
	rsync -a --include="*/" --include="*.json" --include="*.jsonl" --exclude="*" outputs/ /tmp/jsteer-push/
	uv run modal volume put -f jsteer-pub-cache /tmp/jsteer-push outputs

modal-follow app:
	uv run modal app logs {{app}} --follow --timestamps

modal-pull:
	uv run modal volume get --force jsteer-pub-cache outputs .

publish-results: results
	git diff --exit-code -- README.md results
	git subtree push --prefix results origin gh-pages

notebook:
	uv run jupytext --sync nbs/demo.py

notebook-run:
	uv run jupytext --sync --execute nbs/demo.py

notebook-smoke:
	VJP_STEER_MODEL=wassname/qwen3-5lyr-tiny-random VJP_STEER_DEVICE=cpu VJP_STEER_PAIRS=2 \
	VJP_STEER_BATCH_SIZE=2 VJP_STEER_MAX_LENGTH=128 VJP_STEER_TOKENS=8 VJP_STEER_RUNGS=11 \
	uv run jupytext --to ipynb --execute -o outputs/demo_smoke.ipynb nbs/demo.py

check: smoke results notebook-smoke notebook
