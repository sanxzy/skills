"""Stream local video/audio through the fixed Faster Whisper runtime.

This module is deliberately independent from remote-media downloaders.  The
public entrypoint accepts one readable local path and emits one structured
result; transcript text is persisted in the canonical JSON and checkpoint
artifacts rather than printed as diagnostic output.
"""

from __future__ import annotations

import argparse
import json
import re
import signal
import threading
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:
    from .checkpoint import Checkpoint, archive_artifact, archive_checkpoint, resume_compatible
    from .common import (
        DEFAULT_BEAM_SIZE,
        DEFAULT_COMPUTE_TYPE,
        DEFAULT_DEVICE,
        DEFAULT_RESUME_OVERLAP_SECONDS,
        DEFAULT_TASK,
        DEFAULT_VAD_FILTER,
        DEFAULT_WORD_TIMESTAMPS,
        SCHEMA_VERSION,
        SKILL_VERSION,
        TIMESTAMP_TOLERANCE_SECONDS,
        TranscriptError,
        atomic_write_json,
        checked_non_negative_number,
        display_path,
        ensure_directory,
        ensure_free_space,
        ensure_writable_parent,
        iso_utc,
        normalize_language,
        safe_text,
    )
    from .media_probe import MediaInfo, inspect_media, source_identity, validate_input_path
    from .model_runtime import (
        RuntimeDependencies,
        default_model_path,
        default_python_environment,
        fixed_model_provenance,
        inspect_runtime,
        load_local_model,
        shutdown_local_model,
        validate_model_directory,
    )
    from .normalize import (
        NormalizedSegment,
        language_from_info,
        normalize_segment,
        validate_segments,
    )
    from .projections import SUPPORTED_FORMATS, finalize_outputs, projection_paths
except ImportError:  # pragma: no cover - direct executable path
    from checkpoint import Checkpoint, archive_artifact, archive_checkpoint, resume_compatible  # type: ignore
    from common import (  # type: ignore
        DEFAULT_BEAM_SIZE,
        DEFAULT_COMPUTE_TYPE,
        DEFAULT_DEVICE,
        DEFAULT_RESUME_OVERLAP_SECONDS,
        DEFAULT_TASK,
        DEFAULT_VAD_FILTER,
        DEFAULT_WORD_TIMESTAMPS,
        SCHEMA_VERSION,
        SKILL_VERSION,
        TIMESTAMP_TOLERANCE_SECONDS,
        TranscriptError,
        atomic_write_json,
        checked_non_negative_number,
        display_path,
        ensure_directory,
        ensure_free_space,
        ensure_writable_parent,
        iso_utc,
        normalize_language,
        safe_text,
    )
    from media_probe import MediaInfo, inspect_media, source_identity, validate_input_path  # type: ignore
    from model_runtime import (  # type: ignore
        RuntimeDependencies,
        default_model_path,
        default_python_environment,
        fixed_model_provenance,
        inspect_runtime,
        load_local_model,
        shutdown_local_model,
        validate_model_directory,
    )
    from normalize import (  # type: ignore
        NormalizedSegment,
        language_from_info,
        normalize_segment,
        validate_segments,
    )
    from projections import SUPPORTED_FORMATS, finalize_outputs, projection_paths  # type: ignore


@dataclass(frozen=True)
class TranscriptionConfig:
    media_path: Path
    output: Path | None = None
    workspace: Path = field(default_factory=Path.cwd)
    task_name: str | None = None
    work_dir: Path | None = None
    language: str | None = None
    formats: tuple[str, ...] = ("json",)
    beam_size: int = DEFAULT_BEAM_SIZE
    vad_filter: bool = DEFAULT_VAD_FILTER
    word_timestamps: bool = DEFAULT_WORD_TIMESTAMPS
    resume: bool = False
    resume_overlap_seconds: float = DEFAULT_RESUME_OVERLAP_SECONDS
    include_hash: bool = False
    redact_paths: bool = False
    model_path: Path = field(default_factory=default_model_path)
    python_environment: Path = field(default_factory=default_python_environment)
    enforce_python_environment: bool = True


@dataclass(frozen=True)
class OutputPaths:
    workspace: Path
    task_name: str
    task_directory: Path
    canonical: Path
    partial: Path
    work_dir: Path
    checkpoint: Path


def _safe_stem(path: Path) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip(".-")
    return value[:100] or "media"


def _normalise_formats(values: Sequence[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        for item in str(value).split(","):
            fmt = item.strip().casefold()
            if not fmt:
                continue
            if fmt not in SUPPORTED_FORMATS:
                raise TranscriptError(
                    "invalid_argument",
                    f"unsupported output format: {fmt}",
                    stage="preflight",
                )
            if fmt not in result:
                result.append(fmt)
    if "json" not in result:
        result.insert(0, "json")
    return tuple(result)


def _safe_task_name(value: str | None, media_path: Path) -> str:
    if value is not None:
        raw = value.strip()
        if not raw:
            raise TranscriptError(
                "invalid_argument",
                "task_name must not be blank",
                stage="preflight",
            )
    else:
        raw = media_path.stem
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", raw).strip(".-")
    if not name:
        name = "transcript"
    return name[:80].rstrip(".-") or "transcript"


def _under_directory(path: Path, directory: Path, *, label: str) -> Path:
    candidate = Path(path).expanduser().resolve(strict=False)
    try:
        candidate.relative_to(directory.resolve(strict=False))
    except ValueError as exc:
        raise TranscriptError(
            "invalid_path",
            f"{label} must remain under the task artifact directory",
            stage="preflight",
            details={"path": str(candidate), "task_directory": str(directory)},
        ) from exc
    return candidate


def resolve_output_paths(config: TranscriptionConfig, media_path: Path) -> OutputPaths:
    workspace = ensure_directory(config.workspace, label="workspace")
    task_name = _safe_task_name(config.task_name, media_path)
    artifact_root = ensure_directory(
        _under_directory(
            workspace / ".artifacts" / "transcript",
            workspace,
            label="transcript artifact root",
        ),
        label="transcript artifact root",
    )
    task_directory = ensure_directory(
        _under_directory(artifact_root / task_name, workspace, label="transcript task directory"),
        label="transcript task directory",
    )
    requested = Path(config.output).expanduser() if config.output is not None else None
    if requested is None:
        canonical = task_directory / f"{_safe_stem(media_path)}.transcript.json"
    else:
        if requested.exists() and requested.is_symlink():
            raise TranscriptError(
                "invalid_path",
                "output destination must not be a symlink",
                stage="preflight",
                details={"path": str(requested)},
            )
        if requested.exists() and requested.is_dir():
            output_directory = _under_directory(requested, task_directory, label="output directory")
            canonical = output_directory / f"{_safe_stem(media_path)}.transcript.json"
        elif requested.suffix.casefold() == ".json":
            canonical = _under_directory(requested, task_directory, label="canonical output")
        elif requested.exists():
            raise TranscriptError(
                "invalid_path",
                "output must be a directory or a .json canonical path inside the task artifact directory",
                stage="preflight",
                details={"path": str(requested)},
            )
        else:
            output_directory = _under_directory(requested, task_directory, label="output directory")
            output_directory = ensure_directory(output_directory, label="output directory")
            canonical = output_directory / f"{_safe_stem(media_path)}.transcript.json"
    if canonical.exists() and canonical.is_symlink():
        raise TranscriptError(
            "invalid_path",
            "canonical output must not be a symlink",
            stage="preflight",
            details={"path": str(canonical)},
        )
    canonical = _under_directory(canonical, task_directory, label="canonical output")
    if canonical == media_path.resolve(strict=False):
        raise TranscriptError(
            "invalid_path",
            "transcript output must not overwrite the input media",
            stage="preflight",
            details={"path": str(canonical)},
        )
    canonical = ensure_writable_parent(canonical, label="canonical output")
    raw_work = (
        Path(config.work_dir).expanduser()
        if config.work_dir is not None
        else task_directory / ".work"
    )
    work = _under_directory(raw_work, task_directory, label="working directory")
    work = ensure_directory(work, label="working directory")
    ensure_free_space((task_directory, work))
    partial = canonical.with_name(canonical.stem + ".partial.json")
    checkpoint = work / "checkpoint.jsonl"
    return OutputPaths(
        workspace=workspace,
        task_name=task_name,
        task_directory=task_directory,
        canonical=canonical,
        partial=partial,
        work_dir=work,
        checkpoint=checkpoint,
    )


def _validate_config(config: TranscriptionConfig) -> TranscriptionConfig:
    if not isinstance(config.media_path, Path):
        raise TranscriptError("invalid_argument", "media_path must be a filesystem path", stage="preflight")
    if config.output is not None and not isinstance(config.output, Path):
        raise TranscriptError("invalid_argument", "output must be a filesystem path when supplied", stage="preflight")
    if not isinstance(config.workspace, Path):
        raise TranscriptError("invalid_argument", "workspace must be a filesystem path", stage="preflight")
    if config.task_name is not None and not isinstance(config.task_name, str):
        raise TranscriptError("invalid_argument", "task_name must be text when supplied", stage="preflight")
    if type(config.beam_size) is not int or not 1 <= config.beam_size <= 100:
        raise TranscriptError(
            "invalid_argument",
            "beam_size must be an integer between 1 and 100",
            stage="preflight",
        )
    if config.word_timestamps is not True:
        raise TranscriptError(
            "invalid_argument",
            "word_timestamps cannot be disabled because word-level timing is part of the contract",
            stage="preflight",
        )
    if type(config.vad_filter) is not bool:
        raise TranscriptError("invalid_argument", "vad_filter must be boolean", stage="preflight")
    language = normalize_language(config.language)
    overlap = checked_non_negative_number(
        config.resume_overlap_seconds,
        "resume overlap",
        maximum=60.0,
    )
    formats = _normalise_formats(config.formats)
    return replace(
        config,
        language=language,
        formats=formats,
        resume_overlap_seconds=overlap,
    )


def _settings(config: TranscriptionConfig) -> dict[str, object]:
    return {
        "task": DEFAULT_TASK,
        "beam_size": config.beam_size,
        "vad_filter": config.vad_filter,
        "word_timestamps": True,
        "device": DEFAULT_DEVICE,
        "compute_type": DEFAULT_COMPUTE_TYPE,
    }


def _resume_source(identity: Mapping[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in identity.items()
        if key in {"path_key", "byte_size", "mtime_ns", "content_hash"}
    }


def _source_from_identity(identity: Mapping[str, object], *, redact: bool) -> dict[str, object]:
    result: dict[str, object] = {
        "path": "<redacted>" if redact else identity.get("path"),
        "byte_size": identity.get("byte_size"),
    }
    if "content_hash" in identity:
        result["content_hash"] = identity["content_hash"]
    return result


def _language_default(config: TranscriptionConfig) -> dict[str, object]:
    return {
        "code": config.language,
        "source": "explicit" if config.language else "detected",
        "probability": None,
    }


def _resume_signature(
    config: TranscriptionConfig,
    identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "source": _resume_source(identity),
        "model": {
            "id": provenance.get("id"),
            "runtime_model": provenance.get("runtime_model"),
            "runtime_path": provenance.get("runtime_path"),
            "engine": provenance.get("engine"),
            "engine_version": provenance.get("engine_version"),
            "device": provenance.get("device"),
            "compute_type": provenance.get("compute_type"),
        },
        "settings": _settings(config),
        "language_request": config.language,
    }


def _header(
    config: TranscriptionConfig,
    identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "skill_version": SKILL_VERSION,
        "status": "queued",
        "created_at": iso_utc(),
        "source_identity": dict(identity),
        "source": dict(identity),
        "model": dict(provenance),
        "settings": _settings(config),
        "language_request": config.language,
        "resume_overlap_seconds": config.resume_overlap_seconds,
        "resume_signature": _resume_signature(config, identity, provenance),
    }


def _prepare_checkpoint(
    paths: OutputPaths,
    config: TranscriptionConfig,
    header: Mapping[str, object],
) -> tuple[Checkpoint, list[str], bool, dict[str, object] | None]:
    """Return checkpoint, warnings, resumed flag, and an existing result."""

    warnings: list[str] = []
    target = paths.checkpoint
    if target.exists():
        if config.resume:
            try:
                checkpoint = Checkpoint.load(target)
            except TranscriptError:
                archived = archive_checkpoint(target)
                warnings.append(
                    "resume checkpoint was unreadable and was preserved before starting a fresh attempt"
                    + (f": {archived.name}" if archived else "")
                )
            else:
                compatible = resume_compatible(checkpoint, header["resume_signature"])
                if checkpoint.recovered_trailing_record:
                    warnings.append("resume ignored an incomplete trailing checkpoint record after an interruption")
                if checkpoint.status == "completed" and compatible:
                    try:
                        value = json.loads(paths.canonical.read_text(encoding="utf-8"))
                    except (OSError, UnicodeError, json.JSONDecodeError):
                        value = None
                    if isinstance(value, Mapping) and value.get("status") == "completed":
                        requested_outputs = projection_paths(paths.canonical, config.formats)
                        if all(path.is_file() and not path.is_symlink() for path in requested_outputs.values()):
                            return checkpoint, warnings, True, dict(value)
                        archived = archive_checkpoint(target)
                        warnings.append(
                            "completed canonical output was reusable but a requested projection was missing; "
                            "the terminal checkpoint was preserved and a fresh run will recreate the output set"
                            + (f": {archived.name}" if archived else "")
                        )
                    else:
                        archived = archive_checkpoint(target)
                        warnings.append(
                            "completed checkpoint had no readable canonical output; a fresh attempt was started"
                            + (f": {archived.name}" if archived else "")
                        )
                elif checkpoint.status != "completed" and compatible:
                    warnings.append("resumed from a compatible durable checkpoint")
                    return checkpoint, warnings, True, None
                else:
                    archived = archive_checkpoint(target)
                    warnings.append(
                        "existing checkpoint did not match the current source/model/settings, or its completed "
                        "artifact was not reusable; it was preserved and processing restarted from the beginning"
                        + (f": {archived.name}" if archived else "")
                    )
        else:
            archived = archive_checkpoint(target)
            warnings.append(
                "a fresh attempt was requested implicitly; the previous checkpoint was preserved"
                + (f": {archived.name}" if archived else "")
            )
    elif config.resume:
        warnings.append("resume was requested but no checkpoint exists; processing started from the beginning")
    if paths.partial.exists():
        archived_partial = archive_artifact(paths.partial)
        warnings.append(
            "the previous partial artifact was preserved before starting a fresh attempt"
            + (f": {archived_partial.name}" if archived_partial else "")
        )
    checkpoint = Checkpoint.create(target, header, retain_segments=False)
    return checkpoint, warnings, False, None


def _progress_document(
    progress: Mapping[str, object],
    duration: float | None,
) -> dict[str, object]:
    value = progress.get("last_durable_media_timestamp", 0.0)
    try:
        timestamp = max(0.0, float(value))
    except (TypeError, ValueError):
        timestamp = 0.0
    try:
        elapsed = max(0.0, float(progress.get("elapsed_seconds", 0.0)))
    except (TypeError, ValueError):
        elapsed = 0.0
    percentage: float | None = None
    if duration is not None and duration > 0:
        percentage = min(100.0, max(0.0, timestamp / duration * 100.0))
    return {
        "last_durable_media_timestamp": timestamp,
        "completed_segment_count": int(progress.get("completed_segment_count", 0) or 0),
        "last_durable_segment_id": progress.get("last_durable_segment_id"),
        "percentage": percentage,
        "elapsed_seconds": elapsed,
        "last_checkpoint_at": progress.get("last_checkpoint_at", iso_utc()),
    }


def _redact_error(value: object, *, redact_paths: bool) -> object:
    if not redact_paths:
        return value
    path_keys = {"path", "expected", "active", "media_path", "model_path", "python_environment"}
    if isinstance(value, Mapping):
        return {
            key: (
                "<redacted>"
                if str(key).casefold() in path_keys and isinstance(item, str)
                else _redact_error(item, redact_paths=True)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_error(item, redact_paths=True) for item in value]
    return value


def _document(
    *,
    status: str,
    source: Mapping[str, object],
    model: Mapping[str, object],
    language: Mapping[str, object],
    settings: Mapping[str, object],
    segments: Sequence[NormalizedSegment],
    progress: Mapping[str, object],
    duration: float | None,
    outputs: Mapping[str, object],
    error: Mapping[str, object] | None,
    warnings: Sequence[str],
    redact_paths: bool = False,
) -> dict[str, object]:
    result: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "source": dict(source),
        "model": dict(model),
        "language": dict(language),
        "settings": dict(settings),
        "segments": [segment.as_dict() for segment in segments],
        "progress": _progress_document(progress, duration),
        "outputs": dict(outputs),
        "diagnostics": {
            "speech_detected": bool(segments),
            "no_speech_detected": status == "completed" and not bool(segments),
        },
    }
    if error is not None:
        redacted_error = _redact_error(error, redact_paths=redact_paths)
        result["error"] = dict(redacted_error) if isinstance(redacted_error, Mapping) else redacted_error
    if warnings:
        result["warnings"] = list(dict.fromkeys(str(item) for item in warnings if str(item)))
    return result


def _artifact_display(path: Path, paths: OutputPaths, *, redact: bool) -> str:
    if redact:
        return "<redacted>"
    try:
        relative = Path(path).resolve(strict=False).relative_to(paths.workspace.resolve(strict=False))
    except (OSError, ValueError):
        return display_path(path)
    return "./" + relative.as_posix()


def _result_with_checkpoint(
    document: Mapping[str, object],
    paths: OutputPaths,
    *,
    redact_paths: bool,
) -> dict[str, object]:
    result = dict(document)
    # The checkpoint is an operational handle, not part of the canonical
    # completed artifact. It is included in the command result for recovery.
    result["checkpoint"] = _artifact_display(paths.checkpoint, paths, redact=redact_paths)
    result["artifacts"] = {
        "task_name": paths.task_name,
        "task_directory": _artifact_display(paths.task_directory, paths, redact=redact_paths),
        "work_directory": _artifact_display(paths.work_dir, paths, redact=redact_paths),
        "checkpoint": _artifact_display(paths.checkpoint, paths, redact=redact_paths),
        "partial": _artifact_display(paths.partial, paths, redact=redact_paths),
    }
    return result


def _persist_incomplete(
    *,
    checkpoint: Checkpoint,
    paths: OutputPaths,
    status: str,
    error: Mapping[str, object] | None,
    source: Mapping[str, object],
    model: Mapping[str, object],
    language: Mapping[str, object],
    duration: float | None,
    warnings: list[str],
    config: TranscriptionConfig,
) -> dict[str, object]:
    persistence_error: TranscriptError | None = None
    try:
        checkpoint.append_status(status, error=error)
    except TranscriptError as exc:
        persistence_error = exc
        warnings.append(f"could not persist terminal checkpoint status: {safe_text(exc)}")
    if persistence_error is not None:
        error = {
            "code": "checkpoint_write_failed",
            "stage": "persistence",
            "message": "durable terminal status could not be recorded",
            "details": {"cause": safe_text(error or persistence_error.as_dict())},
        }
        status = "partial" if checkpoint.segment_count else "failed"
    try:
        durable_segments = checkpoint.read_segments()
    except TranscriptError as exc:
        warnings.append(f"durable checkpoint could not be read back for the partial artifact: {safe_text(exc)}")
        durable_segments = ()
        error = {
            "code": "checkpoint_read_failed",
            "stage": "persistence",
            "message": "durable segments could not be read back for the partial artifact",
            "details": {"cause": safe_text(error or exc.as_dict())},
        }
    outputs = {
        "checkpoint": _artifact_display(paths.checkpoint, paths, redact=config.redact_paths),
        "partial": _artifact_display(paths.partial, paths, redact=config.redact_paths),
    }
    document = _document(
        status=status,
        source=source,
        model=model,
        language=language,
        settings=_settings(config),
        segments=durable_segments,
        progress=checkpoint.progress,
        duration=duration,
        outputs=outputs,
        error=error,
        warnings=warnings,
        redact_paths=config.redact_paths,
    )
    try:
        atomic_write_json(paths.partial, document)
        read_back = json.loads(paths.partial.read_text(encoding="utf-8"))
        if not isinstance(read_back, Mapping) or read_back.get("status") != status:
            raise TranscriptError(
                "artifact_read_failed",
                "partial artifact read-back did not preserve its status",
                stage="finalizing",
            )
    except TranscriptError as exc:
        warnings.append(f"partial artifact could not be written: {safe_text(exc)}")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        warnings.append(f"partial artifact could not be read back: {safe_text(exc)}")
    return _result_with_checkpoint(document, paths, redact_paths=config.redact_paths) | {
        "partial": _artifact_display(paths.partial, paths, redact=config.redact_paths),
    }


def _minimal_failure(
    config: TranscriptionConfig,
    error: TranscriptError,
    *,
    paths: OutputPaths | None = None,
    identity: Mapping[str, object] | None = None,
    provenance: Mapping[str, object] | None = None,
    warnings: Sequence[str] = (),
) -> dict[str, object]:
    source = dict(identity or {"path": display_path(Path(config.media_path), redact=config.redact_paths)})
    if config.redact_paths:
        source["path"] = "<redacted>"
    model = dict(
        provenance
        or fixed_model_provenance(
            model_path=config.model_path,
            python_environment=config.python_environment,
            redact_paths=config.redact_paths,
        )
    )
    language = _language_default(config)
    outputs: dict[str, object] = {}
    if paths is not None:
        outputs = {
            "checkpoint": _artifact_display(paths.checkpoint, paths, redact=config.redact_paths),
            "partial": _artifact_display(paths.partial, paths, redact=config.redact_paths),
        }
    document = _document(
        status="failed",
        source=source,
        model=model,
        language=language,
        settings=_settings(config),
        segments=(),
        progress={
            "last_durable_media_timestamp": 0.0,
            "completed_segment_count": 0,
            "last_durable_segment_id": None,
            "elapsed_seconds": 0.0,
            "last_checkpoint_at": iso_utc(),
        },
        duration=None,
        outputs=outputs,
        error=error.as_dict(),
        warnings=warnings,
        redact_paths=config.redact_paths,
    )
    return _result_with_checkpoint(document, paths, redact_paths=config.redact_paths) if paths else document


def _duplicate_segment(left: NormalizedSegment, right: NormalizedSegment) -> bool:
    return (
        left.text.casefold() == right.text.casefold()
        and abs(left.start - right.start) <= TIMESTAMP_TOLERANCE_SECONDS
        and abs(left.end - right.end) <= TIMESTAMP_TOLERANCE_SECONDS
    )


def _validate_model_language(model: Any, language: str | None) -> None:
    if language is None:
        return
    try:
        supported = getattr(model, "supported_languages", None)
        if callable(supported):
            supported = supported()
    except Exception as exc:
        raise TranscriptError(
            "runtime_contract_failed",
            "could not inspect the model's supported language list",
            stage="loading_model",
            details={"reason": safe_text(exc)},
        ) from exc
    if not isinstance(supported, (list, tuple, set, frozenset)):
        return
    allowed = {
        str(value).casefold().replace("_", "-").strip()
        for value in supported
        if str(value).strip()
    }
    base = language.split("-", 1)[0]
    if language not in allowed and base not in allowed:
        raise TranscriptError(
            "invalid_language",
            "the configured model does not support the requested language",
            stage="loading_model",
            details={"language": language},
        )


def _transcribe_kwargs(
    config: TranscriptionConfig,
    *,
    language: str | None,
    resume_start: float | None,
) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "task": DEFAULT_TASK,
        "beam_size": config.beam_size,
        "vad_filter": config.vad_filter,
        "word_timestamps": True,
    }
    if language:
        kwargs["language"] = language
    if resume_start is not None:
        kwargs["clip_timestamps"] = f"{resume_start:.3f},0"
    return kwargs


def run_transcription(
    config: TranscriptionConfig,
    *,
    runtime: RuntimeDependencies | None = None,
    model: Any | None = None,
    media: MediaInfo | None = None,
    cancel_event: threading.Event | None = None,
    model_loader: Callable[..., Any] | None = None,
) -> dict[str, object]:
    """Run one local transcription attempt and return a structured result."""

    config = _validate_config(config)
    paths: OutputPaths | None = None
    identity: dict[str, object] | None = None
    provenance: dict[str, object] | None = None
    checkpoint: Checkpoint | None = None
    warnings: list[str] = []
    source: dict[str, object] = {}
    language: dict[str, object] = _language_default(config)
    duration: float | None = None
    started = time.monotonic()
    event = cancel_event or threading.Event()
    try:
        input_path = validate_input_path(config.media_path)
        paths = resolve_output_paths(config, input_path)
        identity = source_identity(
            input_path,
            include_hash=config.include_hash,
            redact_path=config.redact_paths,
        )
        if runtime is None:
            runtime = inspect_runtime(
                python_environment=config.python_environment,
                enforce_python_environment=config.enforce_python_environment,
            )
        validate_model_directory(config.model_path)
        provenance = fixed_model_provenance(
            model_path=config.model_path,
            python_environment=config.python_environment,
            engine_version=runtime.engine_version,
            redact_paths=config.redact_paths,
        )
        header = _header(config, identity, provenance)
        checkpoint, checkpoint_warnings, resumed, existing_result = _prepare_checkpoint(
            paths,
            config,
            header,
        )
        warnings.extend(checkpoint_warnings)
        if existing_result is not None:
            existing_result = dict(existing_result)
            existing_result.setdefault("warnings", [])
            existing_result["warnings"] = list(dict.fromkeys(list(existing_result["warnings"]) + warnings))
            return _result_with_checkpoint(
                existing_result,
                paths,
                redact_paths=config.redact_paths,
            )

        checkpoint.append_status("preflighting")
        checkpoint.append_source(_source_from_identity(identity, redact=config.redact_paths))
        checkpoint.append_status("loading_model")
        if model is None:
            model = load_local_model(
                config.model_path,
                runtime=runtime,
                device=DEFAULT_DEVICE,
                compute_type=DEFAULT_COMPUTE_TYPE,
                loader=model_loader,
            )
        _validate_model_language(model, config.language)
        checkpoint.append_status("decoding")
        media_info = media or inspect_media(
            input_path,
            include_hash=config.include_hash,
        )
        if media_info.path.resolve(strict=False) != input_path.resolve(strict=False):
            raise TranscriptError(
                "input_identity_changed",
                "media inspection returned a different input path",
                stage="decoding",
            )
        current_identity = source_identity(
            input_path,
            include_hash=config.include_hash,
            redact_path=config.redact_paths,
        )
        if _resume_source(current_identity) != _resume_source(identity):
            raise TranscriptError(
                "input_identity_changed",
                "input media changed between preflight and decoding",
                stage="decoding",
            )
        duration = media_info.duration_seconds
        source = media_info.as_source(redact_path=config.redact_paths)
        checkpoint.append_source(source)
        checkpoint.append_status("transcribing")

        previous_language = checkpoint.language
        language_arg = config.language
        if (
            language_arg is None
            and resumed
            and isinstance(previous_language, Mapping)
            and previous_language.get("source") == "detected"
            and isinstance(previous_language.get("code"), str)
        ):
            language_arg = previous_language["code"]
        resume_start: float | None = None
        existing_segments = list(checkpoint.segments) if resumed else []
        prefix_count = len(existing_segments)
        prefix_last: NormalizedSegment | None = None
        if resumed and existing_segments:
            last_timestamp = checkpoint.progress.get("last_durable_media_timestamp", 0.0)
            try:
                last_value = max(0.0, float(last_timestamp))
            except (TypeError, ValueError):
                last_value = existing_segments[-1].end
            resume_start = max(0.0, last_value - config.resume_overlap_seconds)
            prefix_count = sum(
                1
                for segment in existing_segments
                if segment.end <= resume_start + TIMESTAMP_TOLERANCE_SECONDS
            )
            prefix_last = existing_segments[prefix_count - 1] if prefix_count else None
        had_resume_segments = bool(existing_segments)
        if resumed:
            # Resume inspection needs the old segment list only long enough to
            # identify the overlap prefix. New and fresh segments remain in
            # the durable journal, not in an ever-growing process list.
            checkpoint.release_segments()
        del existing_segments
        try:
            transcribe_result = model.transcribe(
                str(input_path),
                **_transcribe_kwargs(
                    config,
                    language=language_arg,
                    resume_start=resume_start,
                ),
            )
        except Exception as exc:
            raise TranscriptError(
                "transcription_failed",
                "Faster Whisper could not start transcription",
                stage="transcribing",
                details={"reason": safe_text(exc)},
            ) from exc
        try:
            raw_segments, info = transcribe_result
        except (TypeError, ValueError) as exc:
            raise TranscriptError(
                "runtime_contract_failed",
                "Faster Whisper did not return a segment iterator and info object",
                stage="transcribing",
                details={"reason": safe_text(exc)},
            ) from exc
        language = language_from_info(info, config.language)
        if resumed and previous_language and language.get("code") is None:
            language = dict(previous_language)
        checkpoint.append_language(language)

        current_last = prefix_last if resumed and had_resume_segments else checkpoint.last_segment
        replaced_overlap = not (resumed and had_resume_segments)
        processed_timestamp = checkpoint.progress.get("last_durable_media_timestamp", 0.0)
        try:
            processed_value = float(processed_timestamp)
        except (TypeError, ValueError):
            processed_value = current_last.end if current_last else 0.0
        try:
            generator = iter(raw_segments)
        except Exception as exc:
            raise TranscriptError(
                "transcription_failed",
                "Faster Whisper did not provide an iterable segment stream",
                stage="transcribing",
                details={"reason": safe_text(exc)},
            ) from exc
        cancelled = False
        while True:
            if event.is_set():
                cancelled = True
                break
            try:
                raw_segment = next(generator)
            except StopIteration:
                break
            except Exception as exc:
                raise TranscriptError(
                    "transcription_failed",
                    "Faster Whisper stopped while generating transcript segments",
                    stage="transcribing",
                    details={"reason": safe_text(exc)},
                ) from exc
            normalized = normalize_segment(
                raw_segment,
                0,
                duration=duration,
            )
            if normalized is None:
                continue
            if resumed and not replaced_overlap:
                # A defensive filter for runtimes that ignore clip_timestamps.
                boundary = resume_start if resume_start is not None else 0.0
                if normalized.end <= boundary + TIMESTAMP_TOLERANCE_SECONDS:
                    continue
                if normalized.start < boundary - TIMESTAMP_TOLERANCE_SECONDS:
                    continue
                checkpoint.append_truncate(prefix_count, last_segment=prefix_last)
                current_last = checkpoint.last_segment
                replaced_overlap = True
            candidate = replace(normalized, id=checkpoint.segment_count)
            if current_last and _duplicate_segment(current_last, candidate):
                continue
            if current_last and (
                candidate.start < current_last.start
                or candidate.end < current_last.end
            ):
                raise TranscriptError(
                    "segment_order_invalid",
                    "new transcript segment is out of source order",
                    stage="transcribing",
                    details={"segment_id": candidate.id},
                )
            checkpoint.append_segment(candidate)
            current_last = candidate
            processed_value = max(processed_value, candidate.end)
            checkpoint.append_progress(
                processed_value,
                elapsed_seconds=time.monotonic() - started,
            )
        if event.is_set():
            cancelled = True
        if cancelled:
            cancellation = {
                "code": "cancelled",
                "stage": "transcribing",
                "message": "transcription stopped after the caller requested cancellation",
            }
            return _persist_incomplete(
                checkpoint=checkpoint,
                paths=paths,
                status="cancelled",
                error=cancellation,
                source=source or _source_from_identity(identity, redact=config.redact_paths),
                model=provenance,
                language=language,
                duration=duration,
                warnings=warnings,
                config=config,
            )
        if duration is not None and duration > 0:
            processed_value = max(processed_value, duration)
        checkpoint.append_progress(
            processed_value,
            elapsed_seconds=time.monotonic() - started,
        )
        segments_for_output = checkpoint.read_segments()
        validate_segments(segments_for_output, duration=duration)
        checkpoint.append_status("finalizing")
        output_paths = projection_paths(paths.canonical, config.formats)
        expected_outputs = {
            name: _artifact_display(path, paths, redact=config.redact_paths)
            for name, path in output_paths.items()
        }
        completed_document = _document(
            status="completed",
            source=source or _source_from_identity(identity, redact=config.redact_paths),
            model=provenance,
            language=language,
            settings=_settings(config),
            segments=segments_for_output,
            progress=checkpoint.progress,
            duration=duration,
            outputs=expected_outputs,
            error=None,
            warnings=warnings,
        )
        final_document, committed_paths = finalize_outputs(
            completed_document,
            canonical_path=paths.canonical,
            work_dir=paths.work_dir,
            formats=config.formats,
            output_labels=expected_outputs,
        )
        checkpoint.append_status("completed")
        # Re-read the journal after the final output commit. A completed result
        # is returned only when both the canonical artifact and checkpoint are
        # structurally readable.
        persisted = Checkpoint.load(paths.checkpoint, retain_segments=False)
        if persisted.status != "completed" or persisted.segment_count != len(segments_for_output):
            raise TranscriptError(
                "checkpoint_read_failed",
                "completed checkpoint read-back did not match the committed transcript",
                stage="finalizing",
            )
        result = _result_with_checkpoint(
            final_document,
            paths,
            redact_paths=config.redact_paths,
        )
        result["outputs"] = {
            name: _artifact_display(path, paths, redact=config.redact_paths)
            for name, path in committed_paths.items()
        }
        return result
    except KeyboardInterrupt:
        if checkpoint is not None and paths is not None:
            error = {
                "code": "cancelled",
                "stage": "transcribing",
                "message": "transcription was interrupted by the caller",
            }
            return _persist_incomplete(
                checkpoint=checkpoint,
                paths=paths,
                status="cancelled",
                error=error,
                source=source or _source_from_identity(identity or {}, redact=config.redact_paths),
                model=provenance or fixed_model_provenance(
                    model_path=config.model_path,
                    python_environment=config.python_environment,
                    redact_paths=config.redact_paths,
                ),
                language=language,
                duration=duration,
                warnings=warnings,
                config=config,
            )
        return _minimal_failure(
            config,
            TranscriptError("cancelled", "transcription was interrupted by the caller", stage="transcribing"),
            paths=paths,
            identity=identity,
            provenance=provenance,
            warnings=warnings,
        )
    except TranscriptError as exc:
        if checkpoint is not None and paths is not None:
            durable_source = source or _source_from_identity(identity or {}, redact=config.redact_paths)
            durable_model = provenance or fixed_model_provenance(
                model_path=config.model_path,
                python_environment=config.python_environment,
                redact_paths=config.redact_paths,
            )
            durable_language = language or _language_default(config)
            status = "partial" if checkpoint.segment_count else "failed"
            return _persist_incomplete(
                checkpoint=checkpoint,
                paths=paths,
                status=status,
                error=exc.as_dict(),
                source=durable_source,
                model=durable_model,
                language=durable_language,
                duration=duration,
                warnings=warnings,
                config=config,
            )
        return _minimal_failure(
            config,
            exc,
            paths=paths,
            identity=identity,
            provenance=provenance,
            warnings=warnings,
        )
    except Exception as exc:  # Never leak an unstructured runtime failure to callers.
        wrapped = TranscriptError(
            "unexpected_failure",
            "local transcription failed unexpectedly",
            stage="transcribing" if checkpoint is not None else "preflight",
            details={"reason": safe_text(exc)},
        )
        if checkpoint is not None and paths is not None:
            return _persist_incomplete(
                checkpoint=checkpoint,
                paths=paths,
                status="partial" if checkpoint.segment_count else "failed",
                error=wrapped.as_dict(),
                source=source or _source_from_identity(identity or {}, redact=config.redact_paths),
                model=provenance or fixed_model_provenance(
                    model_path=config.model_path,
                    python_environment=config.python_environment,
                    redact_paths=config.redact_paths,
                ),
                language=language,
                duration=duration,
                warnings=warnings,
                config=config,
            )
        return _minimal_failure(
            config,
            wrapped,
            paths=paths,
            identity=identity,
            provenance=provenance,
            warnings=warnings,
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract a timestamped local transcript with the pre-downloaded Faster Whisper Turbo model."
    )
    parser.add_argument("media_path", help="readable local video or audio path")
    parser.add_argument(
        "-o",
        "--output",
        help="optional .json path or directory inside ./.artifacts/transcript/<task_name>/",
    )
    parser.add_argument("--workspace", help="active workspace root; defaults to the current directory")
    parser.add_argument("--task-name", help="artifact task directory name; defaults to the media stem")
    parser.add_argument("--work-dir", help="checkpoint/working directory inside the task artifact directory")
    parser.add_argument("--language", help="supported language code override, for example id")
    parser.add_argument(
        "--format",
        dest="formats",
        action="append",
        default=["json"],
        help="derived output format: txt, srt, or vtt (repeatable or comma-separated)",
    )
    parser.add_argument("--beam-size", type=int, default=DEFAULT_BEAM_SIZE)
    parser.add_argument("--no-vad-filter", action="store_true", help="disable voice activity filtering")
    parser.add_argument("--resume", action="store_true", help="resume a compatible checkpoint")
    parser.add_argument(
        "--resume-overlap",
        type=float,
        default=DEFAULT_RESUME_OVERLAP_SECONDS,
        help="seconds to reprocess before the durable checkpoint (default: 2)",
    )
    parser.add_argument("--hash-source", action="store_true", help="record a SHA-256 source hash")
    parser.add_argument("--redact-paths", action="store_true", help="omit local source paths from artifacts")
    parser.add_argument("--version", action="version", version=f"local-video-transcript-extraction {SKILL_VERSION}")
    return parser


def config_from_args(args: argparse.Namespace) -> TranscriptionConfig:
    return TranscriptionConfig(
        media_path=Path(args.media_path),
        output=Path(args.output) if args.output else None,
        workspace=Path(args.workspace) if args.workspace else Path.cwd(),
        task_name=args.task_name,
        work_dir=Path(args.work_dir) if args.work_dir else None,
        language=args.language,
        formats=tuple(args.formats),
        beam_size=args.beam_size,
        vad_filter=not args.no_vad_filter,
        resume=args.resume,
        resume_overlap_seconds=args.resume_overlap,
        include_hash=args.hash_source,
        redact_paths=args.redact_paths,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    cancel_event = threading.Event()
    previous_handlers: dict[int, Any] = {}

    def request_cancel(signum: int, frame: Any) -> None:
        cancel_event.set()

    for signal_number in (signal.SIGINT, signal.SIGTERM):
        try:
            previous_handlers[signal_number] = signal.getsignal(signal_number)
            signal.signal(signal_number, request_cancel)
        except (OSError, RuntimeError, ValueError):
            # Direct library callers can supply their own event; a non-main
            # thread cannot install process signal handlers.
            continue
    try:
        try:
            config = config_from_args(args)
            result = run_transcription(config, cancel_event=cancel_event)
        except TranscriptError as exc:
            result = {
                "schema_version": SCHEMA_VERSION,
                "status": "failed",
                "error": exc.as_dict(),
            }
        except Exception as exc:
            result = {
                "schema_version": SCHEMA_VERSION,
                "status": "failed",
                "error": {
                    "code": "unexpected_failure",
                    "stage": "preflight",
                    "message": "could not prepare the transcription request",
                    "details": {"reason": safe_text(exc)},
                },
            }
    finally:
        for signal_number, previous in previous_handlers.items():
            try:
                signal.signal(signal_number, previous)
            except (OSError, RuntimeError, ValueError):
                pass
        # CTranslate2 owns native worker threads. Releasing the process cache
        # before Python teardown avoids native mutex shutdown races on macOS.
        shutdown_local_model()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    status = result.get("status") if isinstance(result, Mapping) else None
    return 0 if status == "completed" else (2 if status in {"partial", "cancelled"} else 1)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "OutputPaths",
    "TranscriptionConfig",
    "config_from_args",
    "main",
    "resolve_output_paths",
    "run_transcription",
]
