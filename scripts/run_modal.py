"""Run dose sweeps on Modal, one container per method and extraction seed."""

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
    """Run one sweep or one fixed-dose evaluation."""
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
    if "--extract-only" in argv:
        output = Path(argv[argv.index("--output") + 1])
        return (Path("/repo") / output / "extraction_audit.json").read_text()
    method, seed = argv[0], argv[argv.index("--seed") + 1] if "--seed" in argv else "0"
    certificate = Path(f"/cache/outputs/walk_{method}_s{seed}.json")
    return certificate.read_text() if certificate.exists() else ""


@app.function(
    gpu=os.environ.get("JSTEER_GPU", "H100"),
    volumes={"/cache": cache},
    timeout=24 * 60 * 60,
)
def run_experiment(method: str, argv: list[str]) -> str:
    from huggingface_hub import snapshot_download

    Path("/cache/outputs").mkdir(parents=True, exist_ok=True)
    if not Path("/repo/outputs").exists():
        os.symlink("/cache/outputs", "/repo/outputs")
    model = argv[argv.index("--model") + 1]
    snapshot_download(model)
    try:
        subprocess.run(
            [sys.executable, "scripts/experiment.py", method, "--gpu-stage", *argv],
            cwd="/repo",
            check=True,
        )
    finally:
        cache.commit()
    experiment_id = argv[argv.index("--experiment-id") + 1]
    return Path(f"/cache/outputs/experiments/{experiment_id}/manifest.json").read_text()


@app.local_entrypoint()
def experiment(
    experiment_id: str,
    profile: str,
    method: str = "vjp_mlp_up_left_right_shrink",
    model: str = MODEL,
    dtype: str = "bfloat16",
    n_pairs: int = 256,
    batch_size: int = 32,
    extract_batch_size: int = 8,
    max_length: int = 384,
    max_new_tokens: int = 512,
    coefficients_plus: str = "",
    coefficients_minus: str = "",
    verify_extraction: bool = False,
):
    if profile not in {"dev", "full"}:
        raise ValueError("profile must be dev or full")
    argv = [
        "--experiment-id", experiment_id,
        "--model", model,
        "--dtype", dtype,
        "--n-pairs", str(n_pairs),
        "--batch-size", str(batch_size),
        "--extract-batch-size", str(extract_batch_size),
        "--max-length", str(max_length),
        "--max-new-tokens", str(max_new_tokens),
    ]
    if verify_extraction:
        argv.append("--verify-extraction")
    if profile == "full":
        argv.extend([
            "--coefficients-plus", coefficients_plus,
            "--coefficients-minus", coefficients_minus,
        ])
    if profile == "dev":
        argv.append("--dev")
    json.loads(run_experiment.remote(method, argv))
    cell_count = (
        len([value for value in coefficients_plus.split(",") if value])
        + len([value for value in coefficients_minus.split(",") if value])
        if profile == "full" else 18
    )
    print(f"EXPERIMENT_GPU_COMPLETE id={experiment_id} profile={profile} cells={cell_count}")


@app.local_entrypoint()
def audit_noisy_coordinates(
    output: str = "outputs/audits/20260901_per-side-vjp-noisy-coordinates",
    model: str = MODEL,
    n_pairs: int = 200,
    batch_size: int = 32,
    extract_batch_size: int = 8,
):
    argv = [
        "vjp_mlp_up_left_right_shrink",
        "--extract-only",
        "--output", output,
        "--model", model,
        "--n-pairs", str(n_pairs),
        "--batch-size", str(batch_size),
        "--extract-batch-size", str(extract_batch_size),
    ]
    print(run.remote(argv))


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
