"""Deterministic screenshot-to-UI-IR tools for visionless agents."""

__version__ = "1.0.0"


__all__ = ["Compiler", "__version__"]


def __getattr__(name: str):
    if name == "Compiler":
        from .compiler import Compiler

        return Compiler
    raise AttributeError(name)
