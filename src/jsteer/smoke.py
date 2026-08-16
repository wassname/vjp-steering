"""Run the public VJP path on the tiny random Qwen model."""

import torch
from steering_lite.data import make_persona_pairs
from transformers import AutoModelForCausalLM, AutoTokenizer

from . import steer, vjp_delta


def main() -> None:
    model_name = "wassname/qwen3-5lyr-tiny-random"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, dtype=torch.float32).eval()
    positive, negative = make_persona_pairs(
        tokenizer,
        n_pairs=2,
        thinking=True,
        persona_pairs=[("sycophantic", "abrasive")],
        template="Answer as someone who is {persona}.",
        seed=0,
    )
    target_layer = len(model.model.layers) - 3
    vector = vjp_delta(
        model,
        tokenizer,
        positive,
        negative,
        (target_layer - 1,),
        target_layer=target_layer,
        batch_size=2,
        max_length=128,
        skip_first=16,
    )
    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": "Should I trust a senior researcher without checking?"}],
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt")
    bare = model(**inputs).logits
    with steer(model, vector, C=0.03125):
        steered = model(**inputs).logits
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=8)
    restored = model(**inputs).logits
    if torch.equal(bare, steered):
        raise AssertionError("steering changed no logits")
    torch.testing.assert_close(bare, restored)
    if generated.shape[1] <= inputs["input_ids"].shape[1]:
        raise AssertionError("generation produced no tokens")
    print(f"SMOKE_PASS: canonical_pairs={len(positive)} layers={tuple(vector.stacked)}")


if __name__ == "__main__":
    main()
