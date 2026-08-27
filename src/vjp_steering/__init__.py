from contextlib import contextmanager

from .vjp import j_word, vjp_delta, vjp_mlp_up_shrink


@contextmanager
def steer(model, vector, C: float):
    with vector(model, C=C):
        yield model


__all__ = ["j_word", "steer", "vjp_delta", "vjp_mlp_up_shrink"]
