"""Fixed local Faster Whisper runtime and model-loading boundary."""

from __future__ import annotations

import importlib
import gc
import importlib.metadata
import inspect as _inspect
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

try:
    from .common import (
        DEFAULT_COMPUTE_TYPE,
        DEFAULT_DEVICE,
        MODEL_ID,
        MODEL_RELATIVE_PATH,
        PYTHON_ENV_RELATIVE_PATH,
        RUNTIME_MODEL,
        TranscriptError,
        display_path,
        safe_text,
    )
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        DEFAULT_COMPUTE_TYPE,
        DEFAULT_DEVICE,
        MODEL_ID,
        MODEL_RELATIVE_PATH,
        PYTHON_ENV_RELATIVE_PATH,
        RUNTIME_MODEL,
        TranscriptError,
        display_path,
        safe_text,
    )


@dataclass(frozen=True)
class RuntimeDependencies:
    """The imported runtime surface needed by the orchestrator."""

    whisper_model_class: Any
    engine_version: str
    faster_whisper_module: Any


_MODEL_CACHE: dict[tuple[str, str, str], Any] = {}


def default_model_path() -> Path:
    return Path.home() / MODEL_RELATIVE_PATH


def default_python_environment() -> Path:
    return Path.home() / PYTHON_ENV_RELATIVE_PATH


def fixed_model_provenance(
    *,
    model_path: Path | None = None,
    python_environment: Path | None = None,
    engine_version: str | None = None,
    redact_paths: bool = False,
) -> dict[str, object]:
    configured_model_path = Path(model_path or default_model_path()).expanduser().resolve(strict=False)
    configured_python = Path(python_environment or default_python_environment()).expanduser().resolve(strict=False)
    return {
        "id": MODEL_ID,
        "runtime_model": RUNTIME_MODEL,
        "runtime_path": "~/.local/models/whisper-large-v3-turbo",
        "runtime_path_resolved": display_path(configured_model_path, redact=redact_paths),
        "python_environment": "~/.local/models/.venv",
        "python_environment_resolved": display_path(configured_python, redact=redact_paths),
        "engine": "faster-whisper",
        "engine_version": engine_version,
        "device": DEFAULT_DEVICE,
        "compute_type": DEFAULT_COMPUTE_TYPE,
    }


def validate_python_environment(
    expected: Path | None = None,
    *,
    enforce: bool = True,
) -> Path:
    """Require execution through the configured isolated environment."""

    target = Path(expected or default_python_environment()).expanduser().resolve(strict=False)
    if not enforce:
        return target
    if not target.is_dir() or target.is_symlink():
        raise TranscriptError(
            "python_environment_missing",
            "configured Python environment is missing or is not a regular directory",
            stage="preflight",
            details={"path": str(target)},
        )
    expected_python = target / "bin" / "python"
    if (
        not expected_python.is_file()
        or not expected_python.resolve(strict=False).is_file()
        or not os.access(expected_python, os.X_OK)
    ):
        raise TranscriptError(
            "python_environment_invalid",
            "configured Python environment has no usable bin/python executable",
            stage="preflight",
            details={"path": str(target)},
        )
    active_prefix = Path(sys.prefix).resolve(strict=False)
    if active_prefix != target:
        raise TranscriptError(
            "python_environment_mismatch",
            "transcription must run with the configured local Python environment",
            stage="preflight",
            details={"expected": str(target), "active": str(active_prefix)},
        )
    return target


def validate_model_directory(model_path: Path | None = None) -> Path:
    """Validate the local CTranslate2 model footprint without downloading."""

    target = Path(model_path or default_model_path()).expanduser().resolve(strict=False)
    if not target.is_dir() or target.is_symlink():
        raise TranscriptError(
            "model_missing",
            "configured local Whisper model directory is missing",
            stage="preflight",
            details={"path": str(target)},
        )
    # tokenizer.json is required as well: Faster Whisper otherwise falls back
    # to Tokenizer.from_pretrained(), which would violate the offline contract.
    required = (target / "model.bin", target / "config.json", target / "tokenizer.json")
    missing = [
        path.name
        for path in required
        if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0
    ]
    if missing:
        raise TranscriptError(
            "invalid_model",
            "configured directory does not contain a loadable CTranslate2 model",
            stage="preflight",
            details={"path": str(target), "missing": missing},
        )
    return target


def _engine_version(module: Any) -> str:
    try:
        value = importlib.metadata.version("faster-whisper")
        if value:
            return str(value)
    except importlib.metadata.PackageNotFoundError:
        pass
    value = getattr(module, "__version__", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "unknown"


def inspect_runtime(
    *,
    python_environment: Path | None = None,
    enforce_python_environment: bool = True,
) -> RuntimeDependencies:
    """Check imports only; model construction remains a later side effect."""

    validate_python_environment(
        python_environment,
        enforce=enforce_python_environment,
    )
    try:
        module = importlib.import_module("faster_whisper")
    except Exception as exc:
        raise TranscriptError(
            "dependency_unavailable",
            "faster-whisper is not installed in the configured Python environment",
            stage="preflight",
            details={"reason": safe_text(exc)},
        ) from exc
    try:
        importlib.import_module("av")
    except Exception as exc:
        raise TranscriptError(
            "dependency_unavailable",
            "PyAV is not installed in the configured Python environment",
            stage="preflight",
            details={"reason": safe_text(exc)},
        ) from exc
    model_class = getattr(module, "WhisperModel", None)
    if model_class is None or not callable(model_class):
        raise TranscriptError(
            "dependency_unavailable",
            "faster-whisper does not expose WhisperModel",
            stage="preflight",
        )
    return RuntimeDependencies(
        whisper_model_class=model_class,
        engine_version=_engine_version(module),
        faster_whisper_module=module,
    )


def load_local_model(
    model_path: Path | None = None,
    *,
    runtime: RuntimeDependencies,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    loader: Callable[..., Any] | None = None,
) -> Any:
    """Load and cache only the explicitly configured local model."""

    target = validate_model_directory(model_path)
    key = (str(target), device, compute_type)
    if loader is None and key in _MODEL_CACHE:
        return _MODEL_CACHE[key]
    constructor = loader or runtime.whisper_model_class
    kwargs: dict[str, object] = {
        "device": device,
        "compute_type": compute_type,
    }
    # Current Faster Whisper releases expose this flag. Only pass it when the
    # selected constructor accepts it so hermetic adapters with the smaller
    # documented call surface remain valid; the existing local directory still
    # prevents model-name downloads.
    try:
        signature = _inspect.signature(constructor)
        accepts_kwargs = any(
            parameter.kind == _inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        )
        if "local_files_only" in signature.parameters or accepts_kwargs:
            kwargs["local_files_only"] = True
    except (TypeError, ValueError):
        pass
    try:
        model = constructor(
            str(target),
            **kwargs,
        )
    except Exception as exc:
        raise TranscriptError(
            "invalid_model",
            "the configured CTranslate2 Whisper model could not be loaded",
            stage="loading_model",
            details={"path": str(target), "reason": safe_text(exc)},
        ) from exc
    if loader is None:
        _MODEL_CACHE[key] = model
    return model


def clear_model_cache() -> None:
    """Test/process lifecycle seam; production callers normally reuse the cache."""

    _MODEL_CACHE.clear()


def shutdown_local_model() -> None:
    """Release CTranslate2 workers before interpreter shutdown."""

    clear_model_cache()
    gc.collect()


__all__ = [
    "RuntimeDependencies",
    "clear_model_cache",
    "default_model_path",
    "default_python_environment",
    "fixed_model_provenance",
    "inspect_runtime",
    "load_local_model",
    "shutdown_local_model",
    "validate_model_directory",
    "validate_python_environment",
]
