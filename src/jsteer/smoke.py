"""Run the public VJP steering path on a tiny random Qwen model."""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from . import steer, vjp_delta
from .vjp import load_pairs


MODEL = "wassname/qwen3-5lyr-tiny-random"


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL).to(device).eval()
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    positive, negative = load_pairs()
    target = len(model.model.layers) - 3
    vector = vjp_delta(
        model, tokenizer, positive, negative, tuple(range(target)),
        target_layer=target, batch_size=2, max_length=128, skip_first=16,
    )
    prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": "A manager cites a made-up method. Should we use it?"}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    bare = model(**inputs).logits
    with steer(model, vector, C=0.2):
        steered = model(**inputs).logits
        generated = model.generate(**inputs, max_new_tokens=8, do_sample=False)
    restored = model(**inputs).logits
    if torch.equal(bare, steered):
        raise AssertionError("steering changed no logits")
    torch.testing.assert_close(bare, restored)
    text = tokenizer.decode(generated[0, inputs.input_ids.shape[1]:], skip_special_tokens=True)
    print(f"SMOKE_PASS: model={MODEL} device={device} pairs={len(positive)} generated={text!r}")


if __name__ == "__main__":
    main()
