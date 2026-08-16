# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # VJP-delta steering
#
# This notebook extracts VJP-delta, mean-difference, PCA, and random vectors from one prompt set.
# It then shows bare, positive, and negative steering and displays the measured all-100 result plot.

# %%
import torch
from IPython.display import Image
from safetensors.torch import load_file
from steering_lite import MeanDiffC, PCAC, RandomC, Vector
from steering_lite.data import make_persona_pairs
from tabulate import tabulate
from transformers import AutoModelForCausalLM, AutoTokenizer

from jsteer import steer, vjp_delta
from jsteer.results import ROOT, _rows, plot

MODEL = "Qwen/Qwen3.5-4B"
DEVICE = "cuda"
N_PAIRS = 256
BATCH_SIZE = 4
MAX_LENGTH = 384

tokenizer = AutoTokenizer.from_pretrained(MODEL)
dtype = torch.bfloat16 if DEVICE == "cuda" else torch.float32
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=dtype, device_map=DEVICE).eval()

# %% [markdown]
# ## Extract one vector per method from the same prompt pairs

# %%
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

# %% [markdown]
# The reference vector pins the extraction on the published model.

# %%
if MODEL == "Qwen/Qwen3.5-4B":
    reference = load_file(ROOT / "data" / "vjp_delta_reference.safetensors")
    vector_max_abs_diff = max(
        (vjp_vector.stacked[layer]["v"] - reference[f"stacked.layer{layer}.v"]).abs().max().item()
        for layer in layers
    )
    if vector_max_abs_diff >= 1e-4:
        raise AssertionError(f"vector max abs diff is {vector_max_abs_diff:.3g}")
else:
    vector_max_abs_diff = None
{"model": MODEL, "vector_max_abs_diff": vector_max_abs_diff, "layers": layers}

# %% [markdown]
# ## Steer both ways on one prompt

# %%
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
print(tabulate(generations, headers="keys", tablefmt="grid", maxcolwidths=[10, 60, 60]))

# %% [markdown]
# ## The measured all-100 result

# %%
# PNG, not an interactive figure, because GitHub does not run the plotly javascript
Image(plot(_rows()).to_image(format="png", scale=2))
