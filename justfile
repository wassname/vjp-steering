set dotenv-load

# uv_sync images need a 2025+ builder; the workspace default is still 2024.10
export MODAL_IMAGE_BUILDER_VERSION := "2025.06"

smoke:
	#!/usr/bin/env bash
	set -euo pipefail
	for method in vjp_delta mean_diff pca; do
		BEARTYPE=1 uv run python scripts/walk.py "$method" --coefficient 16 --model wassname/qwen3-5lyr-tiny-random --device cpu --dtype float32 --n-pairs 2 --batch-size 2 --max-length 128 --max-new-tokens 8 --limit 2 --layers 1 --target-layer 4 --status SMOKE_PASS
	done
	uv run python scripts/export.py --self-test

walk-self-test:
	uv run python scripts/continue_side.py --self-test

endpoint-tail-self-test:
	uv run python scripts/endpoint_tail_manifest.py --self-test

endpoint-tail-stage-manifest:
	uv run python scripts/endpoint_tail_manifest.py --allow-missing-continuations

endpoint-tail-manifest:
	uv run python scripts/endpoint_tail_manifest.py

walk method seed:
	HF_HUB_OFFLINE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True uv run python scripts/walk.py {{method}} --seed {{seed}} --walk

walk-dry method seed:
	uv run python scripts/walk.py {{method}} --seed {{seed}} --walk --dry-run

judge-self-test:
	uv run python scripts/judge.py --self-test

judge-dry:
	uv run python scripts/judge.py

judge *args:
	uv run python scripts/judge.py --refresh {{args}}

judge-walks-dry:
	uv run python scripts/judge.py --walks

judge-walks:
	uv run python scripts/judge.py --walks --refresh

judge-walks-faulthandler:
	uv run python -X faulthandler scripts/judge.py --walks --refresh

judge-cell-repro:
	uv run python scripts/scratch/repro_judge_cell.py

export:
	uv run python scripts/export.py

queue-walks:
	#!/usr/bin/env bash
	set -euo pipefail
	for seed in 1 2 0; do
		for method in vjp_delta mean_diff pca; do
			pueue add --group default --priority=-9 -l "why: complete the public all-100 $method seed $seed dose walk; resolve: walk certificate is COMPLETE after either direction crosses two breakdowns plus two rungs" -w "$PWD" -- just walk "$method" "$seed"
		done
	done

sweeps: queue-walks

# the same nine walks on Modal, nine GPUs at once instead of one card in series
modal-smoke:
	uv run modal run scripts/run_modal.py::smoke

# seed the Volume with the rungs already on disk so Modal adopts them instead of re-running
modal-push:
	rm -rf /tmp/jsteer-push && mkdir -p /tmp/jsteer-push
	rsync -a --include="*/" --include="*.json" --include="*.jsonl" --exclude="*" outputs/ /tmp/jsteer-push/
	uv run modal volume put -f jsteer-pub-cache /tmp/jsteer-push outputs

modal-continue method seed continuation_id:
	uv run modal run --detach scripts/run_modal.py::continuation --method {{method}} --seed {{seed}} --continuation-id {{continuation_id}}

modal-continuations continuation_id:
	uv run modal run scripts/run_modal.py::continuations --continuation-id {{continuation_id}}

modal-endpoint-tail-judge:
	uv run modal run scripts/run_modal.py::endpoint_tail_judge

modal-walks *args:
	uv run modal run --detach scripts/run_modal.py::main {{args}}

modal-follow app:
	uv run modal app logs {{app}} --follow --timestamps

modal-pull:
	uv run modal volume get --force jsteer-pub-cache outputs .

queue-judge:
	pueue add --group api -l "why: judge every arm in the nine completed public walks; resolve: all content cells are cached and judge reports zero missing" -w "$PWD" -- just judge-walks

results:
	uv run python -m vjp_steering.results

publish-results: results
	git diff --exit-code -- results
	git subtree push --prefix results origin gh-pages

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
