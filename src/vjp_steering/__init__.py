from contextlib import contextmanager

from .vjp import vjp_delta


@contextmanager
def steer(model, vector, C: float):
    with vector(model, C=C):
        yield model


__all__ = ["steer", "vjp_delta"]
