"""Shared validation and durable-file helpers for local transcript extraction."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "1.0"
SKILL_VERSION = "1.0"
MODEL_ID = "openai/whisper-large-v3-turbo"
RUNTIME_MODEL = "dropbox-dash/faster-whisper-large-v3-turbo"
MODEL_RELATIVE_PATH = Path(".local/models/whisper-large-v3-turbo")
PYTHON_ENV_RELATIVE_PATH = Path(".local/models/.venv")
DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_TASK = "transcribe"
DEFAULT_BEAM_SIZE = 5
DEFAULT_VAD_FILTER = True
DEFAULT_WORD_TIMESTAMPS = True
DEFAULT_RESUME_OVERLAP_SECONDS = 2.0
TIMESTAMP_TOLERANCE_SECONDS = 0.25
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_ERROR_LENGTH = 8 * 1024
MIN_FREE_BYTES = 16 * 1024 * 1024


class TranscriptError(RuntimeError):
    """A bounded, structured local transcription failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str = "unknown",
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "code": self.code,
            "stage": self.stage,
            "message": safe_text(str(self)),
        }
        if self.details:
            result["details"] = dict(self.details)
        return result


def safe_text(value: object, limit: int = MAX_ERROR_LENGTH) -> str:
    try:
        text = str(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 20)] + "…[truncated]"


def safe_repr(value: object, limit: int = 240) -> str:
    try:
        text = repr(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 20)] + "…[truncated]"


def checked_text(value: object, label: str, *, max_length: int | None = None) -> str:
    if type(value) is not str or not value.strip():
        raise TranscriptError(
            "invalid_argument",
            f"{label} must be a non-blank string",
            stage="preflight",
        )
    text = value.strip()
    if max_length is not None and len(text) > max_length:
        raise TranscriptError(
            "invalid_argument",
            f"{label} is too long; maximum is {max_length} characters",
            stage="preflight",
        )
    return text


def checked_positive_number(value: object, label: str, *, maximum: float = 3600.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TranscriptError(
            "invalid_argument",
            f"{label} must be a finite positive number",
            stage="preflight",
        )
    number = float(value)
    if not math.isfinite(number) or number <= 0 or number > maximum:
        raise TranscriptError(
            "invalid_argument",
            f"{label} must be between 0 and {maximum:g} seconds",
            stage="preflight",
        )
    return number


def checked_non_negative_number(value: object, label: str, *, maximum: float = 3600.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TranscriptError(
            "invalid_argument",
            f"{label} must be a finite non-negative number",
            stage="preflight",
        )
    number = float(value)
    if not math.isfinite(number) or number < 0 or number > maximum:
        raise TranscriptError(
            "invalid_argument",
            f"{label} must be between 0 and {maximum:g} seconds",
            stage="preflight",
        )
    return number


def finite_number(value: object, label: str, *, non_negative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TranscriptError(
            "invalid_timestamp",
            f"{label} must be a finite number",
            stage="transcribing",
        )
    number = float(value)
    if not math.isfinite(number) or (non_negative and number < 0):
        raise TranscriptError(
            "invalid_timestamp",
            f"{label} must be finite and non-negative",
            stage="transcribing",
        )
    return number


def optional_number(value: object, label: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TranscriptError(
            "invalid_diagnostic",
            f"{label} must be numeric when present",
            stage="transcribing",
        )
    number = float(value)
    if not math.isfinite(number):
        raise TranscriptError(
            "invalid_diagnostic",
            f"{label} must be finite when present",
            stage="transcribing",
        )
    return number


def normalize_language(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise TranscriptError(
            "invalid_language",
            "language must be a supported language code",
            stage="preflight",
        )
    code = value.strip().casefold().replace("_", "-")
    if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})?", code):
        raise TranscriptError(
            "invalid_language",
            "language must be a supported alphabetic language code such as en or id",
            stage="preflight",
        )
    # Faster Whisper accepts its canonical base language codes rather than
    # locale tags; preserve a valid caller tag only as a normalized base code.
    return code.split("-", 1)[0]


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.replace("\ufeff", "")).strip()


def ensure_directory(path: Path, *, label: str = "directory") -> Path:
    target = Path(path).expanduser()
    try:
        if target.exists() and (target.is_symlink() or not target.is_dir()):
            raise TranscriptError(
                "invalid_path",
                f"{label} is not a regular directory: {target}",
                stage="preflight",
            )
        target.mkdir(parents=True, exist_ok=True)
    except TranscriptError:
        raise
    except OSError as exc:
        raise TranscriptError(
            "output_unavailable",
            f"could not create {label}: {safe_text(exc)}",
            stage="preflight",
            details={"path": str(target)},
        ) from exc
    if target.is_symlink() or not target.is_dir():
        raise TranscriptError(
            "invalid_path",
            f"{label} is not a regular directory: {target}",
            stage="preflight",
        )
    if not os.access(target, os.W_OK):
        raise TranscriptError(
            "output_unavailable",
            f"{label} is not writable: {target}",
            stage="preflight",
        )
    return target.resolve(strict=False)


def ensure_writable_parent(path: Path, *, label: str = "output") -> Path:
    target = Path(path).expanduser()
    parent = ensure_directory(target.parent, label=f"{label} parent")
    if target.exists() and target.is_symlink():
        raise TranscriptError(
            "invalid_path",
            f"{label} must not be a symlink: {target}",
            stage="preflight",
        )
    if target.exists() and not target.is_file():
        raise TranscriptError(
            "invalid_path",
            f"{label} is not a regular file: {target}",
            stage="preflight",
        )
    if not os.access(parent, os.W_OK):
        raise TranscriptError(
            "output_unavailable",
            f"{label} parent is not writable: {parent}",
            stage="preflight",
        )
    return target.resolve(strict=False)


def ensure_free_space(paths: tuple[Path, ...], *, minimum_bytes: int = MIN_FREE_BYTES) -> None:
    if type(minimum_bytes) is not int or minimum_bytes < 0:
        raise TranscriptError(
            "invalid_argument",
            "minimum free space must be a non-negative integer",
            stage="preflight",
        )
    seen: set[Path] = set()
    for value in paths:
        target = Path(value).expanduser().resolve(strict=False)
        if target in seen:
            continue
        seen.add(target)
        try:
            free = int(shutil.disk_usage(target).free)
        except OSError as exc:
            raise TranscriptError(
                "storage_unavailable",
                "could not determine free local storage for transcript artifacts",
                stage="preflight",
                details={"path": str(target), "reason": safe_text(exc)},
            ) from exc
        if free < minimum_bytes:
            raise TranscriptError(
                "storage_unavailable",
                "insufficient local storage for checkpoint and transcript outputs",
                stage="preflight",
                details={"path": str(target), "free_bytes": free, "minimum_bytes": minimum_bytes},
            )


def atomic_write_text(path: Path, text: str) -> None:
    target = Path(path)
    ensure_directory(target.parent, label="artifact parent")
    prefix_match = re.match(r"^(\d{3})-", target.name)
    prefix = f"{prefix_match.group(1)}-tmp-" if prefix_match else f".{target.name}."
    fd, temporary_name = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=str(target.parent))
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    if not target.is_file() or target.is_symlink():
        raise TranscriptError(
            "output_unavailable",
            f"atomic write did not produce a regular file: {target}",
            stage="finalizing",
        )


def atomic_write_json(path: Path, value: object) -> None:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    except (TypeError, ValueError) as exc:
        raise TranscriptError(
            "serialization_failed",
            f"could not serialize JSON artifact: {safe_text(exc)}",
            stage="finalizing",
        ) from exc
    atomic_write_text(path, text)
    read_json(path)


def read_json(path: Path) -> Any:
    target = Path(path)
    try:
        if target.stat().st_size > MAX_JSON_BYTES:
            raise TranscriptError(
                "artifact_too_large",
                f"JSON artifact is too large to read: {target}",
                stage="finalizing",
            )
        with target.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except TranscriptError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TranscriptError(
            "artifact_read_failed",
            f"could not read JSON artifact: {safe_text(exc)}",
            stage="finalizing",
            details={"path": str(target)},
        ) from exc


def append_jsonl(path: Path, record: Mapping[str, object]) -> None:
    target = Path(path)
    ensure_directory(target.parent, label="checkpoint parent")
    try:
        line = json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n"
    except (TypeError, ValueError) as exc:
        raise TranscriptError(
            "checkpoint_write_failed",
            f"could not serialize checkpoint record: {safe_text(exc)}",
            stage="persistence",
        ) from exc
    try:
        with target.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
        encoded = line.encode("utf-8")
        with target.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            if stream.tell() < len(encoded):
                raise OSError("checkpoint file is shorter than the appended record")
            stream.seek(-len(encoded), os.SEEK_END)
            if stream.read(len(encoded)) != encoded:
                raise OSError("checkpoint read-back did not match the appended record")
    except TranscriptError:
        raise
    except OSError as exc:
        raise TranscriptError(
            "checkpoint_write_failed",
            f"could not persist checkpoint record: {safe_text(exc)}",
            stage="persistence",
            details={"path": str(target)},
        ) from exc


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise TranscriptError(
            "input_unavailable",
            f"could not hash input media: {safe_text(exc)}",
            stage="preflight",
            details={"path": str(path)},
        ) from exc
    return digest.hexdigest()


def path_key(path: Path) -> str:
    return hashlib.sha256(str(path.resolve(strict=False)).encode("utf-8")).hexdigest()


def now_epoch() -> float:
    import time

    return time.time()


def iso_utc(epoch: float | None = None) -> str:
    import datetime as _datetime
    import time

    value = time.time() if epoch is None else float(epoch)
    return _datetime.datetime.fromtimestamp(value, _datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def display_path(path: Path, *, redact: bool = False) -> str:
    return "<redacted>" if redact else str(Path(path).resolve(strict=False))


def get_value(value: object, key: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


__all__ = [
    "DEFAULT_BEAM_SIZE",
    "DEFAULT_COMPUTE_TYPE",
    "DEFAULT_DEVICE",
    "DEFAULT_RESUME_OVERLAP_SECONDS",
    "DEFAULT_TASK",
    "DEFAULT_VAD_FILTER",
    "DEFAULT_WORD_TIMESTAMPS",
    "MIN_FREE_BYTES",
    "MODEL_ID",
    "MODEL_RELATIVE_PATH",
    "PYTHON_ENV_RELATIVE_PATH",
    "RUNTIME_MODEL",
    "SCHEMA_VERSION",
    "SKILL_VERSION",
    "TIMESTAMP_TOLERANCE_SECONDS",
    "TranscriptError",
    "append_jsonl",
    "atomic_write_json",
    "atomic_write_text",
    "checked_non_negative_number",
    "checked_positive_number",
    "checked_text",
    "display_path",
    "ensure_directory",
    "ensure_free_space",
    "ensure_writable_parent",
    "file_sha256",
    "finite_number",
    "get_value",
    "iso_utc",
    "normalize_language",
    "normalize_text",
    "now_epoch",
    "optional_number",
    "path_key",
    "read_json",
    "safe_repr",
    "safe_text",
]
