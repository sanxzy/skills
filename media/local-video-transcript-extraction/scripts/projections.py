"""Canonical JSON finalization and deterministic TXT/SRT/VTT projections."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Sequence

try:
    from .common import (
        SCHEMA_VERSION,
        TranscriptError,
        atomic_write_json,
        atomic_write_text,
        ensure_directory,
        read_json,
        safe_text,
    )
    from .normalize import NormalizedSegment, segment_from_dict, validate_segments
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        SCHEMA_VERSION,
        TranscriptError,
        atomic_write_json,
        atomic_write_text,
        ensure_directory,
        read_json,
        safe_text,
    )
    from normalize import NormalizedSegment, segment_from_dict, validate_segments  # type: ignore


SUPPORTED_FORMATS = frozenset({"json", "txt", "srt", "vtt"})


def projection_paths(canonical_path: Path, formats: Sequence[str]) -> dict[str, Path]:
    canonical = Path(canonical_path).resolve(strict=False)
    result: dict[str, Path] = {"json": canonical}
    for value in formats:
        fmt = str(value).casefold().strip()
        if fmt not in SUPPORTED_FORMATS:
            raise TranscriptError(
                "invalid_argument",
                f"unsupported output format: {value}",
                stage="preflight",
            )
        if fmt != "json":
            result[fmt] = canonical.with_suffix(f".{fmt}")
    return result


def _timestamp(value: float, *, comma: bool = False) -> str:
    milliseconds = max(0, int(round(float(value) * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    separator = "," if comma else "."
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{millis:03d}"


def _segments_from_payload(payload: Mapping[str, object]) -> tuple[NormalizedSegment, ...]:
    rows = payload.get("segments")
    if not isinstance(rows, list):
        raise TranscriptError(
            "canonical_invalid",
            "canonical transcript segments must be a list",
            stage="finalizing",
        )
    source = payload.get("source")
    duration: float | None = None
    if isinstance(source, Mapping):
        value = source.get("duration_seconds")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            duration = float(value)
    try:
        segments = tuple(segment_from_dict(row, duration=duration) for row in rows)
        validate_segments(segments, duration=duration)
    except TranscriptError as exc:
        if exc.code == "checkpoint_corrupt":
            raise TranscriptError(
                "canonical_invalid",
                str(exc),
                stage="finalizing",
                details=exc.details,
            ) from exc
        raise
    return segments


def _render_txt(segments: Sequence[NormalizedSegment]) -> str:
    return "\n".join(
        f"[{_timestamp(segment.start)} - {_timestamp(segment.end)}] {segment.text}"
        for segment in segments
    ) + ("\n" if segments else "")


def _render_srt(segments: Sequence[NormalizedSegment]) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            f"{index}\n"
            f"{_timestamp(segment.start, comma=True)} --> {_timestamp(segment.end, comma=True)}\n"
            f"{segment.text}\n"
        )
    return "\n".join(blocks)


def _render_vtt(segments: Sequence[NormalizedSegment]) -> str:
    blocks = ["WEBVTT", ""]
    for segment in segments:
        blocks.extend(
            [
                f"{_timestamp(segment.start)} --> {_timestamp(segment.end)}",
                segment.text,
                "",
            ]
        )
    return "\n".join(blocks)


def _render(format_name: str, segments: Sequence[NormalizedSegment]) -> str:
    if format_name == "txt":
        return _render_txt(segments)
    if format_name == "srt":
        return _render_srt(segments)
    if format_name == "vtt":
        return _render_vtt(segments)
    raise TranscriptError(
        "invalid_argument",
        f"unsupported projection format: {format_name}",
        stage="finalizing",
    )


def _remove(path: Path) -> None:
    try:
        if path.exists() or path.is_symlink():
            path.unlink()
    except OSError:
        pass


def finalize_outputs(
    payload: Mapping[str, object],
    *,
    canonical_path: Path,
    work_dir: Path,
    formats: Sequence[str],
    output_labels: Mapping[str, object] | None = None,
) -> tuple[dict[str, object], dict[str, Path]]:
    """Stage all artifacts, validate them, then atomically commit the set.

    The canonical JSON is read back before any projection is rendered. A
    failed projection therefore cannot leave a newly published JSON document
    claiming completion.
    """

    if payload.get("schema_version") != SCHEMA_VERSION:
        raise TranscriptError(
            "canonical_invalid",
            "canonical transcript has an unsupported schema version",
            stage="finalizing",
        )
    if payload.get("status") != "completed":
        raise TranscriptError(
            "canonical_invalid",
            "only a completed document can be finalized",
            stage="finalizing",
        )
    segments = _segments_from_payload(payload)
    paths = projection_paths(canonical_path, formats)
    output_map = {
        name: str(output_labels[name]) if output_labels is not None and name in output_labels else str(path)
        for name, path in paths.items()
    }
    candidate = dict(payload)
    candidate["outputs"] = output_map
    candidate["schema_version"] = SCHEMA_VERSION

    finalizing_dir = ensure_directory(Path(work_dir) / "finalizing", label="finalization directory")
    stage_canonical = finalizing_dir / ".canonical-stage.json"
    stage_files: dict[str, Path] = {}
    atomic_write_json(stage_canonical, candidate)
    read_back = read_json(stage_canonical)
    if not isinstance(read_back, Mapping) or read_back.get("status") != "completed":
        _remove(stage_canonical)
        raise TranscriptError(
            "canonical_invalid",
            "staged canonical transcript failed read-back validation",
            stage="finalizing",
        )
    for format_name in sorted(paths):
        if format_name == "json":
            continue
        stage_path = finalizing_dir / f".{format_name}.stage"
        try:
            atomic_write_text(stage_path, _render(format_name, segments))
        except Exception:
            _remove(stage_canonical)
            for path in stage_files.values():
                _remove(path)
            raise
        stage_files[format_name] = stage_path

    targets: list[tuple[str, Path, Path]] = [("json", stage_canonical, paths["json"])]
    targets.extend((name, stage, paths[name]) for name, stage in stage_files.items())
    backups: list[tuple[Path, Path]] = []
    committed: list[Path] = []
    try:
        for index, (_, _, target) in enumerate(targets, start=1):
            target = target.resolve(strict=False)
            if target.exists() or target.is_symlink():
                if target.is_symlink() or not target.is_file():
                    raise TranscriptError(
                        "output_write_failed",
                        f"output target is not a regular file: {target}",
                        stage="finalizing",
                        details={"path": str(target)},
                    )
                backup = finalizing_dir / f".backup-{index:02d}-{target.name}"
                if backup.exists() or backup.is_symlink():
                    _remove(backup)
                os.replace(target, backup)
                backups.append((target, backup))
        for _, stage, target in targets:
            os.replace(stage, target)
            committed.append(target)
    except Exception as exc:
        for target in reversed(committed):
            _remove(target)
        for target, backup in reversed(backups):
            try:
                if backup.exists() or backup.is_symlink():
                    os.replace(backup, target)
            except OSError:
                pass
        for _, stage, _ in targets:
            _remove(stage)
        if isinstance(exc, TranscriptError):
            raise
        raise TranscriptError(
            "output_write_failed",
            f"could not commit transcript outputs: {safe_text(exc)}",
            stage="finalizing",
        ) from exc
    finally:
        for _, backup in backups:
            _remove(backup)
        for _, stage, _ in targets:
            _remove(stage)
        try:
            finalizing_dir.rmdir()
        except OSError:
            pass

    final_payload = read_json(paths["json"])
    if not isinstance(final_payload, Mapping) or final_payload.get("status") != "completed":
        raise TranscriptError(
            "canonical_invalid",
            "committed canonical transcript failed read-back validation",
            stage="finalizing",
        )
    for name, path in paths.items():
        if not path.is_file() or path.is_symlink():
            raise TranscriptError(
                "output_write_failed",
                f"committed output is not readable: {path}",
                stage="finalizing",
                details={"format": name},
            )
    return dict(final_payload), paths


__all__ = [
    "SUPPORTED_FORMATS",
    "finalize_outputs",
    "projection_paths",
]
