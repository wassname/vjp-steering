"""Run dose sweeps on Modal, one container per method and extraction seed."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[1]
MODEL = "Qwen/Qwen3.5-4B"
METHODS = ("J_word", "vjp_delta", "vjp_mlp_up_shrink", "mean_diff", "pca")
SEEDS = (1, 2, 0)


def source_revision() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


base_image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .uv_sync()
    .env({"PYTHONUNBUFFERED": "1", "HF_HOME": "/cache/hf", "PYTHONPATH": "/repo/src"})
)
image = (
    base_image.add_local_dir(REPO / "src", "/repo/src")
    .add_local_dir(REPO / "scripts", "/repo/scripts")
    .add_local_dir(REPO / "data", "/repo/data")
)
j_lens_diagnostic_image = (
    base_image.uv_pip_install(
        "git+https://github.com/anthropics/jacobian-lens.git@581d398613e5602a5af361e1c34d3a92ea82ba8e",
        extra_options="--no-deps",
    )
    .add_local_dir(REPO / "src", "/repo/src")
    .add_local_dir(REPO / "scripts", "/repo/scripts")
    .add_local_dir(REPO / "data", "/repo/data")
)
app = modal.App("jsteer-pub", image=image)
cache = modal.Volume.from_name("jsteer-pub-cache", create_if_missing=True)


@app.function(gpu="H100", volumes={"/cache": cache}, timeout=15 * 60)
def j_lens_gap_clamp_remote(output: str, revision: str, placement: str = "all", reuse: str = "") -> str:
    destination = Path("/cache/outputs") / output
    if destination.exists():
        raise FileExistsError(destination)
    try:
        argv = [
            sys.executable, "scripts/scratch/j_lens_gap_clamp.py",
            "--source-root", "/cache/outputs/experiments", "--output", str(destination),
            "--source-revision", revision, "--placement", placement,
        ]
        if reuse:
            argv.extend(["--reuse", str(Path("/cache/outputs") / reuse)])
        subprocess.run(argv, cwd="/repo", check=True)
        return destination.read_text()
    finally:
        cache.commit()


@app.local_entrypoint()
def j_lens_gap_clamp(output: str = "audits/20260907_j_lens_gap_clamp/results-v1.json", placement: str = "all", reuse: str = ""):
    destination = REPO / "outputs" / output
    if destination.exists():
        raise FileExistsError(destination)
    result = j_lens_gap_clamp_remote.remote(output, source_revision(), placement, reuse)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x") as file:
        file.write(result)
    print("GAP_CLAMP_DOWNLOADED", destination)


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
def extract_experiment_remote(method: str, argv: list[str]) -> str:
    from huggingface_hub import snapshot_download

    Path("/cache/outputs").mkdir(parents=True, exist_ok=True)
    if not Path("/repo/outputs").exists():
        os.symlink("/cache/outputs", "/repo/outputs")
    model = argv[argv.index("--model") + 1]
    snapshot_download(model)
    try:
        subprocess.run(
            [sys.executable, "scripts/experiment.py", method, "--extract-only", *argv],
            cwd="/repo",
            check=True,
        )
    finally:
        cache.commit()
    experiment_id = argv[argv.index("--experiment-id") + 1]
    return Path(f"/cache/outputs/experiments/{experiment_id}/extraction/metadata.json").read_text()


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
    filename = "calibration.json" if "--concept-calibrate" in argv else "manifest.json"
    return Path(f"/cache/outputs/experiments/{experiment_id}/{filename}").read_text()


@app.local_entrypoint()
def calibrate_concept(
    method: str,
    source_experiment: str,
    experiment_id: str = "j-lens-concept-calibration-v1",
    j_lens_source: str = "concept",
    persona_direction: str = "j_gp16",
):
    result = run_experiment.remote(method, [
        "--concept-calibrate", "--dev", "--experiment-id", experiment_id,
        "--source-experiment", source_experiment, "--model", MODEL,
        "--j-lens-source", j_lens_source, "--persona-direction", persona_direction,
    ])
    output = pull_experiment(experiment_id)
    print(result[:500])
    print(f"CONCEPT_CALIBRATION_DOWNLOADED output={output}")


def pull_experiment(experiment_id: str) -> Path:
    parent = REPO / "outputs/experiments"
    destination = parent / experiment_id
    if destination.exists():
        raise ValueError(f"local experiment output exists: {destination}")
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent, prefix=".modal-pull-") as directory:
        subprocess.run([
            "modal", "volume", "get", "jsteer-pub-cache",
            f"outputs/experiments/{experiment_id}", directory,
        ], check=True)
        downloaded = Path(directory) / experiment_id
        if not downloaded.is_dir():
            raise FileNotFoundError(downloaded)
        downloaded.replace(destination)
    return destination


@app.local_entrypoint()
def persona_prompt_control(
    experiment_id: str = "j-lens-persona-prompt-control-exact-flaw-dev-v3",
):
    result = run_experiment.remote("j_lens_concept_components", [
        "--persona-prompt-control", "--dev", "--experiment-id", experiment_id,
        "--model", MODEL,
    ])
    output = pull_experiment(experiment_id)
    print(result[:500])
    print(f"PERSONA_PROMPT_CONTROL_DOWNLOADED output={output}")


@app.function(
    gpu=os.environ.get("JSTEER_GPU", "H100"),
    volumes={"/cache": cache},
    timeout=60 * 60,
)
def paper_native_verbal_report_remote(
    model: str, dtype: str, output: str, source_revision: str, prompt_mode: str, coefficient: float
) -> str:
    from huggingface_hub import snapshot_download

    Path("/cache/outputs").mkdir(parents=True, exist_ok=True)
    snapshot_download(model)
    remote_output = Path("/cache/outputs") / output
    subprocess.run(
        [
            sys.executable, "scripts/reproduce_paper_j_lens.py", "--model", model,
            "--dtype", dtype, "--prompt-mode", prompt_mode, "--coefficient", str(coefficient),
            "--source-revision", source_revision, "--output", str(remote_output),
        ],
        cwd="/repo", check=True,
    )
    cache.commit()
    return remote_output.read_text()


@app.local_entrypoint()
def paper_native_verbal_report(
    model: str = MODEL,
    dtype: str = "bfloat16",
    output: str = "experiments/paper-native-verbal-report-v1/results.json",
    prompt_mode: str = "raw",
    coefficient: float = 1.0,
):
    result = paper_native_verbal_report_remote.remote(
        model, dtype, output, source_revision(), prompt_mode, coefficient
    )
    local_output = REPO / "outputs" / output
    local_output.parent.mkdir(parents=True, exist_ok=True)
    local_output.write_text(result)
    summary = json.loads(result)
    print("PAPER_NATIVE_J_LENS_VERBAL_REPORT_DOWNLOADED", json.dumps({
        key: summary[key] for key in summary if key != "trials"
    }))


@app.function(
    gpu=os.environ.get("JSTEER_GPU", "H100"),
    volumes={"/cache": cache},
    timeout=60 * 60,
)
def paper_native_prompt_diagnostic_remote(model: str, dtype: str, output: str, source_revision: str) -> str:
    from huggingface_hub import snapshot_download

    Path("/cache/outputs").mkdir(parents=True, exist_ok=True)
    snapshot_download(model)
    results = {}
    for prompt_mode in ("raw", "chat"):
        remote_output = Path("/cache/outputs") / output / f"{prompt_mode}.json"
        subprocess.run(
            [
                sys.executable, "scripts/reproduce_paper_j_lens.py", "--model", model,
                "--dtype", dtype, "--prompt-mode", prompt_mode, "--clean-only",
                "--source-revision", source_revision, "--output", str(remote_output),
            ],
            cwd="/repo", check=True,
        )
        results[prompt_mode] = json.loads(remote_output.read_text())
    cache.commit()
    return json.dumps(results)


@app.local_entrypoint()
def paper_native_prompt_diagnostic(
    model: str = MODEL,
    dtype: str = "bfloat16",
    output: str = "experiments/paper-native-verbal-report-prompt-diagnostic-v1",
):
    result = paper_native_prompt_diagnostic_remote.remote(model, dtype, output, source_revision())
    local_output = REPO / "outputs" / output / "results.json"
    local_output.parent.mkdir(parents=True, exist_ok=True)
    local_output.write_text(result)
    summary = json.loads(result)
    print("PAPER_NATIVE_PROMPT_DIAGNOSTIC_DOWNLOADED", json.dumps({
        mode: {key: value for key, value in rows.items() if key != "clean_rows"}
        for mode, rows in summary.items()
    }))


@app.function(
    gpu=os.environ.get("JSTEER_GPU", "H100"),
    volumes={"/cache": cache},
    timeout=60 * 60,
)
def paper_native_binary_agreement_remote(model: str, dtype: str, output: str, source_revision: str) -> str:
    from huggingface_hub import snapshot_download

    Path("/cache/outputs").mkdir(parents=True, exist_ok=True)
    snapshot_download(model)
    remote_output = Path("/cache/outputs") / output
    subprocess.run([
        sys.executable, "scripts/paper_native_binary_agreement.py", "--model", model,
        "--dtype", dtype, "--source-revision", source_revision, "--output", str(remote_output),
    ], cwd="/repo", check=True)
    cache.commit()
    return remote_output.read_text()


@app.local_entrypoint()
def paper_native_binary_agreement(
    model: str = MODEL,
    dtype: str = "bfloat16",
    output: str = "experiments/paper-native-binary-agreement-v1/results.json",
):
    result = paper_native_binary_agreement_remote.remote(model, dtype, output, source_revision())
    local_output = REPO / "outputs" / output
    local_output.parent.mkdir(parents=True, exist_ok=True)
    local_output.write_text(result)
    print("PAPER_NATIVE_BINARY_AGREEMENT_DOWNLOADED", result)


@app.function(
    gpu=os.environ.get("JSTEER_GPU", "H100"),
    volumes={"/cache": cache},
    timeout=60 * 60,
)
def j_lens_activity_audit_remote(model: str, dtype: str, output: str, revision: str) -> str:
    from huggingface_hub import snapshot_download

    Path("/cache/outputs").mkdir(parents=True, exist_ok=True)
    snapshot_download(model)
    remote_output = Path("/cache/outputs") / output
    subprocess.run([
        sys.executable, "scripts/j_lens_activity_audit.py", "--model", model,
        "--dtype", dtype, "--source-revision", revision, "--output", str(remote_output),
    ], cwd="/repo", check=True)
    cache.commit()
    return remote_output.read_text()


@app.local_entrypoint()
def j_lens_activity_audit(
    model: str = MODEL,
    dtype: str = "bfloat16",
    output: str = "audits/20260906_j_lens_benchmark_activity/results.json",
):
    result = j_lens_activity_audit_remote.remote(model, dtype, output, source_revision())
    local_output = REPO / "outputs" / output
    local_output.parent.mkdir(parents=True, exist_ok=True)
    local_output.write_text(result)
    print("J_LENS_ACTIVITY_AUDIT_DOWNLOADED", json.dumps(json.loads(result)["summary"]))


@app.function(
    gpu=os.environ.get("JSTEER_GPU", "H100"),
    volumes={"/cache": cache},
    timeout=60 * 60,
    image=j_lens_diagnostic_image,
)
def j_lens_prompt_span_activity_remote(
    model: str,
    dtype: str,
    output: str,
    revision: str,
    limit: int,
    smoke: bool,
    readout_bridge: bool,
    padded_parity: bool = False,
) -> str:
    from huggingface_hub import snapshot_download

    Path("/cache/outputs").mkdir(parents=True, exist_ok=True)
    if model != MODEL:
        raise ValueError("prompt-span diagnostic is fixed to Qwen/Qwen3.5-4B")
    model_revision = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
    model_snapshot = Path(snapshot_download(model, revision=model_revision))
    if model_snapshot.name != model_revision:
        raise ValueError(f"Hugging Face snapshot path differs from pinned revision: {model_snapshot}")
    remote_output = Path("/cache/outputs") / output
    argv = [
        sys.executable, "scripts/j_lens_prompt_span_activity.py",
        "--model", model,
        "--dtype", dtype,
        "--source-revision", revision,
        "--model-revision", model_revision,
        "--limit", str(limit),
        "--batch-size", "2" if padded_parity else "1",
        "--output", str(remote_output),
    ]
    if smoke:
        argv.append("--smoke")
    if readout_bridge:
        argv.append("--readout-bridge")
    if padded_parity:
        argv.append("--padded-parity")
    try:
        subprocess.run(argv, cwd="/repo", check=True)
        return remote_output.read_text()
    finally:
        cache.commit()


@app.local_entrypoint()
def j_lens_prompt_span_activity(
    model: str = MODEL,
    dtype: str = "bfloat16",
    output: str = "audits/20260907_j_lens_prompt_span_activity/results.json",
    smoke: bool = False,
):
    limit = 1 if smoke else 15
    result = j_lens_prompt_span_activity_remote.remote(
        model, dtype, output, source_revision(), limit, smoke, False,
    )
    local_output = REPO / "outputs" / output
    local_output.parent.mkdir(parents=True, exist_ok=True)
    local_output.write_text(result)
    parsed = json.loads(result)
    print("J_LENS_PROMPT_SPAN_ACTIVITY_DOWNLOADED", json.dumps({
        "status": parsed["status"],
        "summary": parsed["summary"],
        "output": str(local_output),
    }, sort_keys=True))


@app.local_entrypoint()
def j_lens_primary_padded_parity(
    output: str = "audits/20260907_j_lens_prompt_span_activity/primary-padded-parity-v1.json",
):
    local_output = REPO / "outputs" / output
    if local_output.exists():
        raise FileExistsError(f"refusing to overwrite diagnostic artifact: {local_output}")
    result = j_lens_prompt_span_activity_remote.remote(
        MODEL, "bfloat16", output, source_revision(), 2, False, False, True,
    )
    local_output.parent.mkdir(parents=True, exist_ok=True)
    with local_output.open("x") as file:
        file.write(result)
    print("PRIMARY_PADDED_PARITY_DOWNLOADED", json.dumps(json.loads(result)["summary"], sort_keys=True))


@app.local_entrypoint()
def j_lens_readout_bridge(
    model: str = MODEL,
    dtype: str = "bfloat16",
    output: str = "audits/20260907_j_lens_prompt_span_activity/readout-bridge-v1.json",
    smoke: bool = False,
):
    limit = 1 if smoke else 15
    result = j_lens_prompt_span_activity_remote.remote(
        model, dtype, output, source_revision(), limit, smoke, True,
    )
    local_output = REPO / "outputs" / output
    local_output.parent.mkdir(parents=True, exist_ok=True)
    local_output.write_text(result)
    parsed = json.loads(result)
    print("J_LENS_READOUT_BRIDGE_DOWNLOADED", json.dumps({
        "status": parsed["status"],
        "summary": parsed["summary"],
        "output": str(local_output),
    }, sort_keys=True))
    if parsed["summary"]["decision"] in ("MECHANICAL_MISMATCH", "ANSWER_SEAM_MISMATCH"):
        raise RuntimeError(f"readout bridge failed; inspect {local_output}")


@app.function(
    gpu=os.environ.get("JSTEER_GPU", "H100"),
    volumes={"/cache": cache},
    timeout=60 * 60,
)
def diagnose_j_lens_remote(model: str, dtype: str, output: str) -> str:
    from huggingface_hub import snapshot_download

    Path("/cache/outputs").mkdir(parents=True, exist_ok=True)
    if not Path("/repo/outputs").exists():
        os.symlink("/cache/outputs", "/repo/outputs")
    snapshot_download(model)
    try:
        subprocess.run(
            [
                sys.executable, "scripts/experiment.py", "j_lens_swap",
                "--j-lens-diagnostic", "--model", model, "--dtype", dtype,
                "--diagnostic-output", output,
            ],
            cwd="/repo",
            check=True,
        )
    finally:
        cache.commit()
    return (Path("/repo") / output).read_text()


@app.local_entrypoint()
def diagnose_j_lens_swap(
    model: str = MODEL,
    dtype: str = "bfloat16",
    output: str = "outputs/audits/20260905_j_lens_paper_native/diagnostic.json",
):
    print(diagnose_j_lens_remote.remote(model, dtype, output))


@app.local_entrypoint()
def extract_experiment(
    method: str,
    experiment_id: str,
    model: str = MODEL,
    dtype: str = "bfloat16",
    n_pairs: int = 200,
    extract_batch_size: int = 8,
    max_length: int = 384,
    j_lens_source: str = "concept",
    persona_direction: str = "j_gp16",
):
    argv = [
        "--experiment-id", experiment_id,
        "--model", model,
        "--dtype", dtype,
        "--n-pairs", str(n_pairs),
        "--extract-batch-size", str(extract_batch_size),
        "--max-length", str(max_length),
        "--j-lens-source", j_lens_source,
        "--persona-direction", persona_direction,
    ]
    result = extract_experiment_remote.remote(method, argv)
    output = pull_experiment(experiment_id)
    print(result[:500])
    print(f"EXPERIMENT_EXTRACTION_DOWNLOADED output={output}")


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
    concept_layers: str = "",
    j_lens_source: str = "concept",
    persona_direction: str = "j_gp16",
    reuse_extraction_from: str = "",
    random_control_seed: int | None = None,
    random_control_coefficient: float | None = None,
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
    if reuse_extraction_from:
        argv.extend(["--reuse-extraction-from", reuse_extraction_from])
    if concept_layers:
        argv.extend(["--concept-layers", concept_layers])
    if random_control_seed is not None:
        if random_control_coefficient is None:
            raise ValueError("random control requires coefficient")
        argv.extend([
            "--random-control-seed", str(random_control_seed),
            "--random-control-coefficient", str(random_control_coefficient),
        ])
    if j_lens_source != "concept":
        argv.extend(["--j-lens-source", j_lens_source])
    if persona_direction != "j_gp16":
        argv.extend(["--persona-direction", persona_direction])
    if profile == "full" or coefficients_plus or coefficients_minus:
        argv.extend([
            "--coefficients-plus", coefficients_plus,
            "--coefficients-minus", coefficients_minus,
        ])
    if profile == "dev":
        argv.append("--dev")
    manifest = json.loads(run_experiment.remote(method, argv))
    cell_count = (
        len([value for value in coefficients_plus.split(",") if value])
        + len([value for value in coefficients_minus.split(",") if value])
        if profile == "full" else sum(len(values) for values in manifest["grid"].values())
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
def smoke_j_lens_swap():
    command = (
        "j_lens_swap --seed 0 --coefficient 1 --n-pairs 2 --batch-size 2 --extract-batch-size 2"
        " --max-length 128 --max-new-tokens 8 --limit 2 --status SMOKE_PASS"
    )
    print(run.remote(command.split()) or "J_LENS_SWAP_MODAL_SMOKE_PASS")


@app.local_entrypoint()
def smoke():
    """Run the research methods on the real model through the deployed container path."""
    commands = (
        "J_word --seed 0 --coefficient 1 --n-pairs 2 --batch-size 2 --extract-batch-size 2"
        " --max-length 128 --max-new-tokens 8 --limit 2 --status SMOKE_PASS",
        "j_lens_swap --seed 0 --coefficient 1 --n-pairs 2 --batch-size 2 --extract-batch-size 2"
        " --max-length 128 --max-new-tokens 8 --limit 2 --status SMOKE_PASS",
        "vjp_mlp_up_shrink --seed 0 --coefficient 1 --n-pairs 2 --batch-size 2 --extract-batch-size 2"
        " --max-length 128 --max-new-tokens 8 --limit 2 --status SMOKE_PASS",
    )
    for command in commands:
        print(run.remote(command.split()) or "SMOKE_PASS: rung finished")
