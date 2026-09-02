"""Measure whether a saved shared VJP moves its target functional as predicted."""

import argparse
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path

import torch
from loguru import logger
from steering_lite import Vector
from steering_lite.data import make_persona_pairs

import walk
from experiment import load_model
from vjp_steering.experiment import DEFAULT_EXPERIMENT_IDS, experiment_dir
from vjp_steering.vjp import _batch_gradients, _encode, _target_mask, _target_mean


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-id", default=DEFAULT_EXPERIMENT_IDS["vjp_mlp_up_shared_eb"])
    parser.add_argument("--model", default="Qwen/Qwen3.5-4B")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--dtype", choices=("float32", "bfloat16"), default="bfloat16")
    parser.add_argument("--n-pairs", type=int, default=32)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument("--coefficients", type=float, nargs="+", default=[0.25, 1.0])
    parser.add_argument("--output", type=Path, default=Path("slop/audits/20260902_shared_pair_eb_mediation.json"))
    return parser.parse_args()


def vector_sha256(vector: Vector) -> str:
    digest = hashlib.sha256()
    for kind, tree in (("shared", vector.shared), ("stacked", vector.stacked)):
        for layer, tensors in sorted(tree.items()):
            for name, tensor in sorted(tensors.items()):
                value = tensor.detach().contiguous().cpu()
                digest.update(f"{kind}:{layer}:{name}:{value.dtype}:{tuple(value.shape)}".encode())
                digest.update(value.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def directions(vector: Vector) -> dict[int, torch.Tensor]:
    result = {}
    for name, values in vector.stacked.items():
        prefix, _, _ = name.partition(".")
        if prefix != "layers":
            raise ValueError(f"unexpected vector hook name {name!r}")
        layer = int(name.split(".")[1])
        result[layer] = values["v"].sum(0)
    return result


@contextmanager
def apply_directions(model, direction_by_layer: dict[int, torch.Tensor], coefficient: float):
    handles = []

    def hook(direction: torch.Tensor):
        def add(_module, _inputs, output):
            if not torch.is_tensor(output):
                raise TypeError("mlp.up_proj hook must receive a tensor")
            return output + coefficient * direction.to(output)
        return add

    for layer, direction in direction_by_layer.items():
        handles.append(
            model.model.layers[layer].mlp.up_proj.register_forward_hook(hook(direction))
        )
    try:
        yield
    finally:
        for handle in handles:
            handle.remove()


@contextmanager
def record_target(model, target_layer: int):
    captured = []

    def record(_module, _inputs, output):
        hidden = output[0] if isinstance(output, tuple) else output
        captured.append(hidden)

    handle = model.model.layers[target_layer].register_forward_hook(record)
    try:
        yield captured
    finally:
        handle.remove()


def target_means(model, tokenizer, prompts, target_layer, cotangent, batch_size, max_length, direction_by_layer, coefficient, target_scope):
    values = []
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        encoded = _encode(model, tokenizer, batch, max_length)
        target_valid = _target_mask(encoded["attention_mask"], skip_first=16, target_scope=target_scope)
        with record_target(model, target_layer) as captured:
            with apply_directions(model, direction_by_layer, coefficient):
                model(**encoded)
        if len(captured) != 1:
            raise ValueError("target block hook did not capture exactly one activation")
        target = captured[0].float()
        projection = (target * cotangent.to(target)).sum(-1)
        values.append((projection * target_valid).sum(1).cpu() / target_valid.sum(1).cpu())
    return torch.cat(values)


def predicted_means(model, tokenizer, prompts, layers, target_layer, cotangent, batch_size, max_length, direction_by_layer, target_scope):
    values = []
    for start in range(0, len(prompts), batch_size):
        batch = prompts[start : start + batch_size]
        gradients, valid, _ = _batch_gradients(
            model, tokenizer, batch, layers, target_layer, cotangent,
            skip_first=16, max_length=max_length, source_readout="mlp.up_proj",
            target_scope=target_scope,
        )
        predicted_total = sum(
            (gradient.float() * valid.unsqueeze(-1) * direction_by_layer[layer].to(gradient)).sum((1, 2))
            for layer, gradient in gradients.items()
        )
        target_count = 1 if target_scope == "last_token" else valid.sum(1)
        values.append((predicted_total / target_count).detach().cpu())
    return torch.cat(values)


def summarize(values: torch.Tensor) -> dict[str, float]:
    return {
        "mean": values.mean().item(),
        "std": values.std(unbiased=True).item(),
        "n": int(values.numel()),
    }


def main() -> None:
    args = parse_args()
    root = experiment_dir(args.experiment_id)
    metadata = json.loads((root / "extraction" / "metadata.json").read_text())
    vectors = {
        side: Vector.load(str(root / "extraction" / f"{side.replace('+', 'plus').replace('-', 'minus')}.safetensors"))
        for side in ("+C", "-C")
    }
    hashes = {side: vector_sha256(vector) for side, vector in vectors.items()}
    if hashes != metadata["vector_content_sha256"]:
        raise ValueError("saved vector hashes do not match extraction metadata")
    if hashes["+C"] != hashes["-C"]:
        raise ValueError("shared experiment must use one vector on both sides")
    direction_by_layer = directions(vectors["+C"])
    layers = tuple(sorted(direction_by_layer))
    target_layer = metadata["target_layer"]
    target_scope = metadata["target_cotangent_scope"]

    model, tokenizer = load_model(args)
    model.requires_grad_(False)
    extraction_positive, extraction_negative = make_persona_pairs(
        tokenizer, n_pairs=metadata["n_pairs"], thinking=True,
        persona_pairs=walk.PERSONAS, template=walk.PERSONA_TEMPLATE, seed=0,
    )
    cotangent = _target_mean(
        model, tokenizer, extraction_positive, target_layer, args.batch_size, args.max_length
    ) - _target_mean(
        model, tokenizer, extraction_negative, target_layer, args.batch_size, args.max_length
    )
    positive, negative = make_persona_pairs(
        tokenizer, n_pairs=args.n_pairs, thinking=True,
        persona_pairs=walk.PERSONAS, template=walk.PERSONA_TEMPLATE, seed=args.seed,
    )
    prompt_sets = {"positive": positive, "negative": negative}
    result = {
        "experiment_id": args.experiment_id,
        "model": args.model,
        "held_out_pair_seed": args.seed,
        "held_out_n_pairs": args.n_pairs,
        "target_layer": target_layer,
        "source_layers": list(layers),
        "source_readout": "mlp.up_proj",
        "target_cotangent_scope": target_scope,
        "vector_content_sha256": hashes,
        "metric": f"mean {target_scope} c dot h_target; c is recomputed from extraction seed 0",
        "predicted_first_order_delta_per_C": {},
        "realized_delta": {},
    }
    for label, prompts in prompt_sets.items():
        prediction = predicted_means(
            model, tokenizer, prompts, layers, target_layer, cotangent,
            args.batch_size, args.max_length, direction_by_layer, target_scope,
        )
        result["predicted_first_order_delta_per_C"][label] = summarize(prediction)
        baseline = target_means(
            model, tokenizer, prompts, target_layer, cotangent,
            args.batch_size, args.max_length, direction_by_layer, coefficient=0,
            target_scope=target_scope,
        )
        result["realized_delta"][label] = {}
        for coefficient in args.coefficients:
            steered = target_means(
                model, tokenizer, prompts, target_layer, cotangent,
                args.batch_size, args.max_length, direction_by_layer, coefficient,
                target_scope,
            )
            result["realized_delta"][label][str(coefficient)] = summarize(steered - baseline)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    logger.info("SHARED_VJP_MEDIATION_COMPLETE output={}", args.output)
    logger.info(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
