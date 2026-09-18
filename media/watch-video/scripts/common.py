"""Shared validation, subprocess, path, and time helpers for watch-video.

The helpers deliberately use shell-free subprocesses and explicit bounded
outputs.  The rest of the skill treats media and all text obtained from it as
untrusted data; this module owns only transport and local artifact mechanics.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


WATCH_VIDEO_VERSION = "2.2"
MAX_COMMAND_OUTPUT = 64 * 1024
# Metadata contains large format/caption inventories; keep its structured
# output on a larger but still bounded channel instead of silently truncating
# it to the diagnostic limit.
MAX_METADATA_OUTPUT = 4 * 1024 * 1024
MAX_ERROR_TEXT = 8 * 1024
MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_INTENT_LENGTH = 8 * 1024
DEFAULT_COMMAND_TIMEOUT = 120.0
DEFAULT_FRAME_INTERVAL = 5.0


class WatchVideoError(RuntimeError):
    """A user-actionable watch-video failure with a stable status."""

    def __init__(self, message: str, *, status: str = "failed") -> None:
        super().__init__(message)
        self.status = status


class ToolUnavailableError(WatchVideoError):
    """A required external capability is not available."""

    def __init__(self, tool: str, detail: str = "") -> None:
        suffix = f": {detail}" if detail else ""
        super().__init__(f"Required tool is unavailable: {tool}{suffix}", status="tool_unavailable")
        self.tool = tool


@dataclass(frozen=True)
class CommandResult:
    """Bounded result from one shell-free external command."""

    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    output_truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


CommandRunner = Callable[..., Any]


def safe_text(value: object, limit: int = MAX_ERROR_TEXT) -> str:
    """Render an external value without allowing unbounded diagnostics."""

    try:
        text = str(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 24)] + "…[truncated]"


def safe_repr(value: object, limit: int = 240) -> str:
    try:
        text = repr(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    return text if len(text) <= limit else text[: limit - 16] + "…[truncated]"


def checked_text(value: object, label: str, *, max_length: int | None = None) -> str:
    if type(value) is not str or not value.strip():
        raise WatchVideoError(f"{label} must be a non-blank string, got {safe_repr(value)}")
    text = value.strip()
    if max_length is not None and len(text) > max_length:
        raise WatchVideoError(f"{label} is too long; maximum is {max_length} characters")
    return text


def checked_timeout(value: object, label: str = "timeout", *, maximum: float = 3600.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WatchVideoError(f"{label} must be a finite positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0 or number > maximum:
        raise WatchVideoError(f"{label} must be between 0 and {maximum:g} seconds")
    return number


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: float = DEFAULT_COMMAND_TIMEOUT,
    env: Mapping[str, str] | None = None,
    runner: CommandRunner | None = None,
    output_limit: int = MAX_COMMAND_OUTPUT,
) -> CommandResult:
    """Run a validated command without a shell and with bounded output.

    ``runner`` is an injection seam for hermetic tests.  A real invocation
    never interpolates media text into a shell command.
    """

    try:
        args = tuple(argv)
    except Exception as exc:
        raise WatchVideoError("command arguments must be an iterable of strings") from exc
    if not args or any(type(item) is not str or not item or "\x00" in item for item in args):
        raise WatchVideoError("command arguments must be non-empty strings without NUL bytes")
    limit = checked_timeout(timeout)
    if isinstance(output_limit, bool) or not isinstance(output_limit, int) or output_limit <= 0:
        raise WatchVideoError("command output limit must be a positive integer")
    if cwd is not None and not isinstance(cwd, Path):
        cwd = Path(cwd)
    execute = runner or subprocess.run
    kwargs: dict[str, Any] = {
        "cwd": str(cwd) if cwd is not None else None,
        "check": False,
        "capture_output": True,
        "text": True,
        "timeout": limit,
        "shell": False,
    }
    if env is not None:
        kwargs["env"] = dict(env)
    try:
        completed = execute(list(args), **kwargs)
    except subprocess.TimeoutExpired as exc:
        stdout, stdout_truncated = _bounded_output(getattr(exc, "stdout", ""), output_limit)
        stderr, stderr_truncated = _bounded_output(getattr(exc, "stderr", ""), output_limit)
        return CommandResult(
            returncode=None,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
            output_truncated=stdout_truncated or stderr_truncated,
        )
    except FileNotFoundError as exc:
        raise ToolUnavailableError(args[0], "executable was not found") from exc
    except OSError as exc:
        raise WatchVideoError(f"Could not start external command {args[0]}: {safe_text(exc)}") from exc
    except Exception as exc:
        raise WatchVideoError(f"External command runner failed: {safe_text(exc)}") from exc

    stdout, stdout_truncated = _bounded_output(getattr(completed, "stdout", ""), output_limit)
    stderr, stderr_truncated = _bounded_output(getattr(completed, "stderr", ""), output_limit)
    return CommandResult(
        returncode=_coerce_returncode(getattr(completed, "returncode", None)),
        stdout=stdout,
        stderr=stderr,
        timed_out=False,
        output_truncated=stdout_truncated or stderr_truncated,
    )


def _coerce_returncode(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is int:
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bounded_output(value: object, limit: int = MAX_COMMAND_OUTPUT) -> tuple[str, bool]:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if value is None:
        return "", False
    try:
        text = str(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    if len(text) <= limit:
        return text, False
    return safe_text(text, limit), True


def workspace_root(value: str | Path | None = None) -> Path:
    root = Path.cwd() if value is None else Path(value).expanduser()
    try:
        resolved = root.resolve(strict=True)
    except OSError as exc:
        raise WatchVideoError(f"Workspace does not exist: {root}") from exc
    if not resolved.is_dir():
        raise WatchVideoError(f"Workspace is not a directory: {resolved}")
    return resolved


def owned_path(root: Path, *parts: str) -> Path:
    """Resolve a path below ``root`` and reject traversal/symlink escapes."""

    base = workspace_root(root)
    if any(type(part) is not str or not part or Path(part).is_absolute() for part in parts):
        raise WatchVideoError("artifact path components must be relative non-blank strings")
    candidate = base.joinpath(*parts)
    try:
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(base):
            raise WatchVideoError(f"Artifact path escapes the workspace: {candidate}")
        # Check the nearest existing ancestor as well.  ``resolve`` catches
        # existing symlinks; this makes the boundary explicit for diagnostics.
        ancestor = candidate
        while not ancestor.exists() and ancestor != ancestor.parent:
            ancestor = ancestor.parent
        if ancestor.exists() and not ancestor.resolve().is_relative_to(base):
            raise WatchVideoError(f"Artifact path escapes through a symlink: {candidate}")
    except OSError as exc:
        raise WatchVideoError(f"Could not validate artifact path: {candidate}") from exc
    # Return the lexical child path after validating its canonical target so
    # callers can still reject a symlink at the final owned boundary.
    return candidate


def ensure_directory(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir() or path.is_symlink():
        raise WatchVideoError(f"Artifact directory is not a real directory: {path}")
    return path


def atomic_write_text(path: Path, text: str) -> None:
    """Write and replace one owned file, then verify that it is readable."""

    target = Path(path)
    ensure_directory(target.parent)
    numeric_prefix = re.match(r"^(\d{3})-", target.name)
    temporary_prefix = (
        f"{numeric_prefix.group(1)}-tmp-"
        if numeric_prefix
        else f".{target.name}."
    )
    fd, temporary_name = tempfile.mkstemp(prefix=temporary_prefix, suffix=".tmp", dir=str(target.parent))
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
        raise WatchVideoError(f"Atomic write did not produce a regular file: {target}")


def atomic_write_json(path: Path, value: object) -> None:
    try:
        text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    except (TypeError, ValueError) as exc:
        raise WatchVideoError(f"Could not serialize JSON artifact {path}: {safe_text(exc)}") from exc
    atomic_write_text(path, text)
    read_json(path)


def read_json(path: Path) -> Any:
    target = Path(path)
    try:
        if target.stat().st_size > MAX_JSON_BYTES:
            raise WatchVideoError(f"JSON artifact is too large to read: {target}")
        with target.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except WatchVideoError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WatchVideoError(f"Could not read JSON artifact {target}: {safe_text(exc)}") from exc


def atomic_append_jsonl(path: Path, record: Mapping[str, object]) -> None:
    """Append a small progress observation and verify the appended line."""

    target = Path(path)
    ensure_directory(target.parent)
    try:
        line = json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n"
    except (TypeError, ValueError) as exc:
        raise WatchVideoError(f"Could not serialize progress record: {safe_text(exc)}") from exc
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())
    expected = line.encode("utf-8")
    with target.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() < len(expected):
            raise WatchVideoError(f"Progress record was not persisted: {target}")
        stream.seek(-len(expected), os.SEEK_END)
        if stream.read(len(expected)) != expected:
            raise WatchVideoError(f"Progress record read-back did not match: {target}")


def parse_timestamp(value: object, label: str = "timestamp") -> float:
    if isinstance(value, bool):
        raise WatchVideoError(f"{label} must be a finite non-negative timestamp")
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise WatchVideoError(f"{label} must not be blank")
        pieces = text.replace(",", ".").split(":")
        if len(pieces) not in {1, 2, 3}:
            raise WatchVideoError(f"{label} must use seconds, MM:SS, or HH:MM:SS")
        try:
            numbers = [float(piece) for piece in pieces]
        except ValueError as exc:
            raise WatchVideoError(f"{label} contains an invalid time: {safe_repr(value)}") from exc
        if len(numbers) == 1:
            number = numbers[0]
        elif len(numbers) == 2:
            minutes, seconds = numbers
            number = minutes * 60 + seconds
        else:
            hours, minutes, seconds = numbers
            number = hours * 3600 + minutes * 60 + seconds
    else:
        raise WatchVideoError(f"{label} must be a timestamp, got {safe_repr(value)}")
    if not math.isfinite(number) or number < 0:
        raise WatchVideoError(f"{label} must be finite and non-negative")
    return number


def parse_time_range(value: str | None, *, duration: float | None = None) -> tuple[float, float] | None:
    if value is None:
        return None
    text = checked_text(value, "range", max_length=80)
    if "-" not in text:
        raise WatchVideoError("range must use START-END, for example 12:30-18:00")
    start_text, end_text = text.split("-", 1)
    start = parse_timestamp(start_text, "range start")
    end = parse_timestamp(end_text, "range end")
    if end <= start:
        raise WatchVideoError("range end must be greater than range start")
    if duration is not None and end > duration + 0.001:
        raise WatchVideoError("range end is beyond the known video duration")
    return start, end


def format_timestamp(value: float) -> str:
    number = max(0.0, float(value))
    milliseconds = int(round(number * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def normalize_url(value: object) -> str:
    raw = checked_text(value, "video URL", max_length=16_384)
    try:
        parts = urlsplit(raw)
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise WatchVideoError(f"Video URL is malformed: {safe_text(exc)}", status="unsupported_source") from exc
    if parts.scheme.lower() not in {"http", "https"} or not host:
        raise WatchVideoError("Video URL must use http or https and include a host", status="unsupported_source")
    if parts.username is not None or parts.password is not None:
        raise WatchVideoError("Video URL must not contain embedded credentials", status="unsupported_source")
    host_text = host.lower()
    if ":" in host_text and not host_text.startswith("["):
        host_text = f"[{host_text}]"
    netloc = host_text
    if port is not None:
        netloc += f":{port}"
    dropped = {"si", "feature", "fbclid", "gclid", "igshid", "ref", "ref_src"}
    query: list[tuple[str, str]] = []
    for key, item in parse_qsl(parts.query, keep_blank_values=True):
        lower = key.casefold()
        if lower in dropped or lower.startswith("utm_"):
            continue
        query.append((key, item))
    return urlunsplit((parts.scheme.lower(), netloc, parts.path, urlencode(query, doseq=True), ""))


def short_hash(value: str, length: int = 24) -> str:
    if length < 8:
        raise WatchVideoError("hash length is too short")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def trusted_module_available(module_name: str) -> bool:
    """Allow module execution only from the active interpreter roots."""

    if type(module_name) is not str or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\.]*", module_name):
        return False
    try:
        spec = importlib.util.find_spec(module_name)
        origin = getattr(spec, "origin", None) if spec is not None else None
        if not isinstance(origin, str) or origin in {"built-in", "frozen"}:
            return False
        candidate = Path(origin).resolve(strict=True)
        roots = {Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()}
        return any(candidate.is_relative_to(root) for root in roots)
    except (ImportError, OSError, ValueError):
        return False


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise WatchVideoError(f"Could not hash artifact {path}: {safe_text(exc)}") from exc
    return digest.hexdigest()


def safe_filename(value: object, fallback: str = "artifact", *, suffix: str = "") -> str:
    text = str(value) if isinstance(value, str) else ""
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip(".-")
    if not text:
        text = fallback
    return text[:120] + suffix


def parse_command_template(value: str, *, required: Iterable[str] = ("{audio}", "{output_dir}")) -> tuple[str, ...]:
    text = checked_text(value, "ASR command", max_length=4096)
    try:
        tokens = tuple(shlex.split(text))
    except ValueError as exc:
        raise WatchVideoError(f"ASR command is not valid shell-free syntax: {safe_text(exc)}") from exc
    if not tokens:
        raise WatchVideoError("ASR command must not be empty")
    for placeholder in required:
        if placeholder not in tokens:
            raise WatchVideoError(f"ASR command must contain the {placeholder} placeholder")
    return tokens


def classify_extractor_failure(result: CommandResult) -> tuple[str, str]:
    detail = safe_text(result.stderr or result.stdout).strip()
    lowered = detail.casefold()
    if result.timed_out or "timed out" in lowered or "timeout" in lowered:
        return "source_unavailable", "media extraction timed out"
    if any(term in lowered for term in (
        "unsupported url", "no suitable extractor", "not a valid url", "unsupported site",
    )):
        return "unsupported_source", "yt-dlp does not support this URL"
    if any(term in lowered for term in (
        "login", "sign in", "private video", "age-restricted", "age verification",
        "authentication", "cookies", "members-only", "confirm you're not a bot",
    )):
        return "authentication_required", "the provider requires authentication or verification"
    if any(term in lowered for term in (
        "geo-restricted", "not available in your country", "http error 403", "forbidden",
    )):
        return "source_unavailable", "the provider did not make the media available"
    return "source_unavailable", "the provider or network did not return usable media"


def intent_needs_visual(intent: str | None) -> bool:
    if not intent:
        return False
    lowered = intent.casefold()
    return bool(re.search(
        r"\b(show|shown|screen|ui|interface|terminal|code|command|frame|visual|look|"
        r"demonstrat|scene|gesture|camera|diagram|slide|layout|on-screen|what happens)\b",
        lowered,
    ))


def intent_is_selective(intent: str | None) -> bool:
    if not intent:
        return False
    lowered = intent.casefold()
    return bool(re.search(
        r"\b(where|when|find|only|part|section|discuss|mention|around|timestamp|"
        r"extract|specific|focus|caching|authentication|login)\b",
        lowered,
    ))


def optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def optional_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if type(value) is int:
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return None


__all__ = [
    "CommandResult",
    "DEFAULT_COMMAND_TIMEOUT",
    "DEFAULT_FRAME_INTERVAL",
    "ToolUnavailableError",
    "WatchVideoError",
    "atomic_append_jsonl",
    "atomic_write_json",
    "atomic_write_text",
    "checked_text",
    "checked_timeout",
    "classify_extractor_failure",
    "ensure_directory",
    "file_sha256",
    "format_timestamp",
    "intent_is_selective",
    "intent_needs_visual",
    "normalize_url",
    "optional_float",
    "optional_int",
    "owned_path",
    "parse_command_template",
    "parse_time_range",
    "parse_timestamp",
    "read_json",
    "run_command",
    "safe_filename",
    "safe_repr",
    "safe_text",
    "short_hash",
    "trusted_module_available",
    "workspace_root",
]
