# CODEX: This marimo notebook is the public extract, steer, generate, and plot example.

import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    mo.md(
        """
        # VJP-delta steering

        This notebook extracts VJP-delta, mean-difference, PCA, and random vectors from one prompt set.
        It then shows bare, positive, and negative steering and displays the measured all-100 result plot.
        """
    )
    return (mo,)


@app.cell
def _(mo):
    import torch
    from pathlib import Path
    from safetensors.torch import load_file
    from steering_lite import MeanDiffC, PCAC, RandomC, Vector
    from steering_lite.data import make_persona_pairs
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from jsteer import steer, vjp_delta
    from jsteer.results import _rows, plot

    CLI = mo.cli_args()
    MODEL = str(CLI.get("model", "Qwen/Qwen3.5-4B"))
    DEVICE = str(CLI.get("device", "cuda"))
    N_PAIRS = int(CLI.get("pairs", 256))
    BATCH_SIZE = int(CLI.get("batch-size", 4))
    MAX_LENGTH = int(CLI.get("max-length", 384))
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    dtype = torch.bfloat16 if DEVICE == "cuda" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=dtype, device_map=DEVICE).eval()
    return (
        BATCH_SIZE,
        MAX_LENGTH,
        MODEL,
        MeanDiffC,
        N_PAIRS,
        PCAC,
        Path,
        RandomC,
        Vector,
        load_file,
        make_persona_pairs,
        model,
        plot,
        steer,
        tokenizer,
        vjp_delta,
    )


@app.cell
def _(
    BATCH_SIZE,
    MAX_LENGTH,
    MeanDiffC,
    N_PAIRS,
    PCAC,
    RandomC,
    Vector,
    make_persona_pairs,
    model,
    tokenizer,
    vjp_delta,
):
    positive_prompts, negative_prompts = make_persona_pairs(
        tokenizer,
        n_pairs=N_PAIRS,
        thinking=True,
        persona_pairs=[("sycophantic", "abrasive")],
        template="Answer as someone who is {persona}.",
        seed=0,
    )
    n_layers = len(model.model.layers)
    target_layer = n_layers - 3
    layers = tuple(range(max(1, int(n_layers * 0.2)), min(target_layer, int(n_layers * 0.8))))
    vjp_vector = vjp_delta(
        model,
        tokenizer,
        positive_prompts,
        negative_prompts,
        layers,
        target_layer=target_layer,
        batch_size=BATCH_SIZE,
        max_length=MAX_LENGTH,
        skip_first=min(16, MAX_LENGTH // 4),
    )
    baseline_kw = dict(batch_size=BATCH_SIZE, max_length=MAX_LENGTH)
    vectors = {
        "vjp_delta": vjp_vector,
        "mean_diff": Vector.train(
            model, tokenizer, positive_prompts, negative_prompts, MeanDiffC(layers=layers), **baseline_kw
        ),
        "pca": Vector.train(
            model, tokenizer, positive_prompts, negative_prompts, PCAC(layers=layers), **baseline_kw
        ),
        "random": Vector.train(
            model, tokenizer, positive_prompts, negative_prompts, RandomC(layers=layers, seed=0), **baseline_kw
        ),
    }
    return layers, vectors, vjp_vector


@app.cell
def _(MODEL, Path, layers, load_file, vjp_vector):
    if MODEL == "Qwen/Qwen3.5-4B":
        reference = load_file(Path(__file__).parents[1] / "data" / "vjp_delta_reference.safetensors")
        vector_max_abs_diff = max(
            (vjp_vector.stacked[layer]["v"] - reference[f"stacked.layer{layer}.v"]).abs().max().item()
            for layer in layers
        )
        if vector_max_abs_diff >= 1e-4:
            raise AssertionError(f"vector max abs diff is {vector_max_abs_diff:.3g}")
    else:
        vector_max_abs_diff = None
    {"model": MODEL, "vector_max_abs_diff": vector_max_abs_diff, "layers": layers}
    return


@app.cell
def _(mo, model, steer, tokenizer, vectors):
    prompt = "A senior researcher says a fabricated statistical method is standard. Explain whether to use it."
    text = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    def generate(vector=None, C=0.0):
        if vector is None:
            output = model.generate(**inputs, do_sample=False, max_new_tokens=64)
        else:
            with steer(model, vector, C=C):
                output = model.generate(**inputs, do_sample=False, max_new_tokens=64)
        return tokenizer.decode(output[0, inputs["input_ids"].shape[1] :], skip_special_tokens=True)

    coefficients = {"vjp_delta": 0.177, "mean_diff": 0.5, "pca": 1.0, "random": 2.0}
    generations = [{"method": "bare", "-C": generate(), "+C": generate()}]
    generations.extend(
        {
            "method": method,
            "-C": generate(vector, -coefficients[method]),
            "+C": generate(vector, coefficients[method]),
        }
        for method, vector in vectors.items()
    )
    mo.ui.table(generations)
    return


@app.cell
def _(plot):
    result_rows = _rows()
    result_figure = plot(result_rows)
    result_figure
    return


if __name__ == "__main__":
    app.run()
