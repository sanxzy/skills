"""Local media validation and duration inspection through PyAV."""

from __future__ import annotations

import importlib
import math
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from .common import (
        TranscriptError,
        file_sha256,
        path_key,
        safe_text,
    )
except ImportError:  # pragma: no cover
    from common import TranscriptError, file_sha256, path_key, safe_text  # type: ignore


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    media_type: str
    byte_size: int
    duration_seconds: float | None
    content_hash: str | None = None

    def source_identity(self, *, redact_path: bool = False) -> dict[str, object]:
        source_path = "<redacted>" if redact_path else str(self.path)
        result: dict[str, object] = {
            "path": source_path,
            "path_key": path_key(self.path),
            "byte_size": self.byte_size,
            "mtime_ns": self.path.stat().st_mtime_ns,
        }
        if self.content_hash:
            result["content_hash"] = self.content_hash
        return result

    def as_source(self, *, redact_path: bool = False) -> dict[str, object]:
        result: dict[str, object] = {
            "path": "<redacted>" if redact_path else str(self.path),
            "media_type": self.media_type,
            "byte_size": self.byte_size,
            "duration_seconds": self.duration_seconds,
        }
        if self.content_hash:
            result["content_hash"] = self.content_hash
        return result


def validate_input_path(path: Path) -> Path:
    raw = str(path).strip()
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:/{1,2}", raw):
        raise TranscriptError(
            "remote_input_unsupported",
            "this skill accepts local filesystem paths only; resolve remote media upstream",
            stage="preflight",
        )
    candidate = Path(path).expanduser().resolve(strict=False)
    try:
        info = candidate.stat()
    except OSError as exc:
        raise TranscriptError(
            "input_missing",
            "input media does not exist or cannot be inspected",
            stage="preflight",
            details={"path": str(candidate), "reason": safe_text(exc)},
        ) from exc
    if not stat.S_ISREG(info.st_mode):
        raise TranscriptError(
            "input_unreadable",
            "input media must be a readable regular file",
            stage="preflight",
            details={"path": str(candidate)},
        )
    if info.st_size <= 0:
        raise TranscriptError(
            "input_empty",
            "input media is empty",
            stage="preflight",
            details={"path": str(candidate)},
        )
    if not os.access(candidate, os.R_OK):
        raise TranscriptError(
            "input_unreadable",
            "input media is not readable",
            stage="preflight",
            details={"path": str(candidate)},
        )
    try:
        with candidate.open("rb") as stream:
            stream.read(1)
    except OSError as exc:
        raise TranscriptError(
            "input_unreadable",
            "input media could not be opened for reading",
            stage="preflight",
            details={"path": str(candidate), "reason": safe_text(exc)},
        ) from exc
    return candidate


def source_identity(path: Path, *, include_hash: bool = False, redact_path: bool = False) -> dict[str, object]:
    candidate = validate_input_path(path)
    info = candidate.stat()
    result: dict[str, object] = {
        "path": "<redacted>" if redact_path else str(candidate),
        "path_key": path_key(candidate),
        "byte_size": int(info.st_size),
        "mtime_ns": int(info.st_mtime_ns),
    }
    if include_hash:
        result["content_hash"] = file_sha256(candidate)
    return result


def _duration_from_container(container: Any, av_module: Any) -> float | None:
    candidates: list[float] = []
    value = getattr(container, "duration", None)
    try:
        if value is not None:
            # PyAV container durations use AV_TIME_BASE units (microseconds).
            number = float(value) / float(getattr(av_module, "time_base", 1_000_000))
            if math.isfinite(number) and number > 0:
                candidates.append(number)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    for stream in list(getattr(container, "streams", ())):
        duration = getattr(stream, "duration", None)
        time_base = getattr(stream, "time_base", None)
        if duration is None or time_base is None:
            continue
        try:
            number = float(duration * time_base)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number > 0:
            candidates.append(number)
    return max(candidates) if candidates else None


def inspect_media(path: Path, *, include_hash: bool = False) -> MediaInfo:
    """Open the file via PyAV and expose safe media metadata only."""

    candidate = validate_input_path(path)
    try:
        av_module = importlib.import_module("av")
    except Exception as exc:
        raise TranscriptError(
            "dependency_unavailable",
            "PyAV is required to inspect local media",
            stage="decoding",
            details={"reason": safe_text(exc)},
        ) from exc
    try:
        container = av_module.open(str(candidate), mode="r")
    except Exception as exc:
        raise TranscriptError(
            "media_decode_failed",
            "PyAV could not open the input media",
            stage="decoding",
            details={"path": str(candidate), "reason": safe_text(exc)},
        ) from exc
    try:
        streams = list(getattr(container, "streams", ()))
        stream_types = {
            str(getattr(stream, "type", "")).casefold()
            for stream in streams
        }
        if not stream_types.intersection({"audio", "video"}):
            raise TranscriptError(
                "unsupported_media",
                "input media contains no audio or video stream",
                stage="decoding",
                details={"path": str(candidate)},
            )
        media_type = "video" if "video" in stream_types else "audio"
        duration = _duration_from_container(container, av_module)
    except TranscriptError:
        raise
    except Exception as exc:
        raise TranscriptError(
            "media_decode_failed",
            "PyAV could not inspect the input media streams",
            stage="decoding",
            details={"path": str(candidate), "reason": safe_text(exc)},
        ) from exc
    finally:
        try:
            container.close()
        except Exception:
            pass
    content_hash = file_sha256(candidate) if include_hash else None
    return MediaInfo(
        path=candidate,
        media_type=media_type,
        byte_size=candidate.stat().st_size,
        duration_seconds=duration,
        content_hash=content_hash,
    )


__all__ = [
    "MediaInfo",
    "inspect_media",
    "source_identity",
    "validate_input_path",
]
