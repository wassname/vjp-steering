"""Fan the nine dose walks out over Modal GPUs, one container per (method, seed).

Run from the repo root (uv_sync reads ./pyproject.toml + ./uv.lock):
    modal run scripts/run_modal.py::smoke        # tiny random model, one rung, ~minutes
    modal run --detach scripts/run_modal.py      # the nine real walks
    modal volume get --force jsteer-pub-cache outputs .   # pull artifacts back
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[1]
MODEL = "Qwen/Qwen3.5-4B"
METHODS = ("J_word", "vjp_delta", "vjp_mlp_up_shrink", "mean_diff", "pca")
SEEDS = (1, 2, 0)

image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .uv_sync()
    .env({"PYTHONUNBUFFERED": "1", "HF_HOME": "/cache/hf", "PYTHONPATH": "/repo/src"})
    .add_local_dir(REPO / "src", "/repo/src")
    .add_local_dir(REPO / "scripts", "/repo/scripts")
    .add_local_dir(REPO / "data", "/repo/data")
)
app = modal.App("jsteer-pub", image=image)
cache = modal.Volume.from_name("jsteer-pub-cache", create_if_missing=True)


@app.function(
    gpu=os.environ.get("JSTEER_GPU", "H100"),
    volumes={"/cache": cache},
    timeout=24 * 60 * 60,
)
def run(argv: list[str]) -> str:
    """One walk (or one rung) of scripts/walk.py, with outputs/ living on the Volume."""
    from huggingface_hub import snapshot_download

    Path("/cache/outputs").mkdir(parents=True, exist_ok=True)
    if not Path("/repo/outputs").exists():
        os.symlink("/cache/outputs", "/repo/outputs")
    # walk.py runs each rung with HF_HUB_OFFLINE=1, so the weights must be cached first
    snapshot_download(argv[argv.index("--model") + 1] if "--model" in argv else MODEL)
    try:
        subprocess.run([sys.executable, "scripts/walk.py", *argv], cwd="/repo", check=True)
    finally:
        cache.commit()
    method, seed = argv[0], argv[argv.index("--seed") + 1] if "--seed" in argv else "0"
    certificate = Path(f"/cache/outputs/walk_{method}_s{seed}.json")
    return certificate.read_text() if certificate.exists() else ""


@app.local_entrypoint()
def main(
    walk_id: str,
    methods: str = ",".join(METHODS),
    seeds: str = ",".join(map(str, SEEDS)),
    batch_size: int = 32,
    extract_batch_size: int = 8,
    refine_around_cstar: bool = False,
):
    # generation: batch 4 leaves an H100 idle, decode is bandwidth bound so a wide batch is nearly free
    # extraction: vjp_delta's backward graph OOMs an 80 GB card at 32
    jobs = [
        (method, seed)
        for method in methods.split(",")
        for seed in seeds.split(",")
        if method != "J_word" or seed == "0"
    ]
    extra = ["--refine-around-cstar"] if refine_around_cstar else []
    handles = {
        job: run.spawn([
            job[0], "--seed", job[1], "--walk", "--walk-id", walk_id,
            "--batch-size", str(batch_size),
            "--extract-batch-size", str(extract_batch_size),
            *extra,
        ])
        for job in jobs
    }
    for (method, seed), handle in handles.items():
        try:
            certificate = json.loads(handle.get())
            print(f"{method}\ts{seed}\t{certificate['status']}\trungs={len(certificate['rungs'])}")
        except Exception as error:  # one dead walk must not hide the other eight
            print(f"{method}\ts{seed}\tFAILED\t{error}")


@app.local_entrypoint()
def descending(method: str, coefficients: str, seeds: str = "0"):
    """Run full-cohort doses from a known incoherent point back toward zero."""
    handles = {
        (coefficient, seed): run.spawn([
            method, "--seed", seed, "--coefficient", coefficient,
            "--batch-size", "32", "--extract-batch-size", "8",
        ])
        for coefficient in coefficients.split(",")
        for seed in seeds.split(",")
    }
    for (coefficient, seed), handle in handles.items():
        print(f"{method}\ts={seed}\tC={coefficient}\t{handle.get()[:200]}")


@app.local_entrypoint()
def smoke():
    """Run both new methods on the real model through the deployed container path."""
    commands = (
        "J_word --seed 0 --coefficient 1 --n-pairs 2 --batch-size 2 --extract-batch-size 2"
        " --max-length 128 --max-new-tokens 8 --limit 2 --status SMOKE_PASS",
        "vjp_mlp_up_shrink --seed 0 --coefficient 1 --n-pairs 2 --batch-size 2 --extract-batch-size 2"
        " --max-length 128 --max-new-tokens 8 --limit 2 --status SMOKE_PASS",
    )
    for command in commands:
        print(run.remote(command.split()) or "SMOKE_PASS: rung finished")
