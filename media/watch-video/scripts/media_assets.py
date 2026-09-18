"""Bounded media downloads and FFmpeg/ffprobe adapters.

The orchestrator uses these helpers for bounded audio/video operations. All
subprocesses are shell-free; provider video downloads and persistent WAV
promotion are coordinated by ``media_cache.py``, while ASR-only audio and
sampled frames remain disposable run artifacts.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

try:
    from .common import (
        CommandResult,
        ToolUnavailableError,
        WatchVideoError,
        checked_text,
        checked_timeout,
        ensure_directory,
        format_timestamp,
        run_command,
        safe_text,
    )
    from .resolve_media import YtDlpTool, _auth_arguments, find_yt_dlp
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        CommandResult,
        ToolUnavailableError,
        WatchVideoError,
        checked_text,
        checked_timeout,
        ensure_directory,
        format_timestamp,
        run_command,
        safe_text,
    )
    from resolve_media import YtDlpTool, _auth_arguments, find_yt_dlp  # type: ignore


class AssetError(WatchVideoError):
    """A media asset could not be obtained or inspected."""


def find_binary(name: str, explicit: str | None = None) -> str:
    if explicit is not None:
        value = str(explicit).strip()
        if not value:
            raise ToolUnavailableError(name, "the explicit executable path is blank")
        path = Path(value).expanduser()
        if path.parent != Path(".") or "/" in value or "\\" in value:
            try:
                resolved = path.resolve(strict=True)
            except OSError as exc:
                raise ToolUnavailableError(name, f"executable is not runnable: {path}") from exc
            if not resolved.is_file() or not os.access(resolved, os.X_OK):
                raise ToolUnavailableError(name, f"executable is not runnable: {path}")
            return str(resolved)
        found = shutil.which(value)
        if found:
            return found
        raise ToolUnavailableError(name, f"executable was not found: {value}")
    found = shutil.which(name)
    if not found:
        raise ToolUnavailableError(name, "install it or provide an explicit executable")
    return found


def _download_command(
    tool: YtDlpTool,
    url: str,
    output_template: Path,
    *,
    mode: str,
    cookies: str | None,
    cookies_from_browser: str | None,
) -> list[str]:
    common = [
        *tool.argv,
        "--ignore-config",
        "--no-playlist",
        "--no-warnings",
        "--no-progress",
        "--newline",
        "--output",
        str(output_template),
        *_auth_arguments(cookies, cookies_from_browser),
    ]
    if mode == "audio":
        common.extend([
            "--format", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "wav",
            "--audio-quality", "0",
        ])
    elif mode == "video":
        common.extend([
            # Prefer separate best video + audio streams so the persistent
            # video cache can also supply the WAV without a second download.
            "--format", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        ])
    else:
        raise WatchVideoError(f"Unsupported media download mode: {mode}")
    return [*common, "--", url]


def _new_files(directory: Path, prefix: str, before: set[Path]) -> list[Path]:
    candidates = []
    for path in directory.glob(f"{prefix}.*"):
        if path in before or not path.is_file() or path.is_symlink():
            continue
        if path.name.endswith((".part", ".ytdl", ".tmp")):
            continue
        try:
            if path.stat().st_size > 0:
                candidates.append(path)
        except OSError:
            continue
    return sorted(candidates, key=lambda item: item.stat().st_mtime_ns)


def _download(
    url: str,
    destination: Path,
    *,
    mode: str,
    timeout: float,
    cookies: str | None,
    cookies_from_browser: str | None,
    yt_dlp: str | None,
    runner=None,
    file_prefix: str | None = None,
) -> tuple[Path, CommandResult, str]:
    directory = ensure_directory(destination)
    output_prefix = checked_text(
        file_prefix or ("audio" if mode == "audio" else "video"),
        "media file prefix",
        max_length=80,
    )
    if "/" in output_prefix or "\\" in output_prefix:
        raise WatchVideoError("media file prefix must be a single filename component")
    tool = find_yt_dlp(
        yt_dlp,
        timeout=timeout,
        runner=runner,
        auto_install=runner is None,
    )
    before = set(directory.glob(f"{output_prefix}.*"))
    result = run_command(
        _download_command(
            tool,
            url,
            directory / f"{output_prefix}.%(ext)s",
            mode=mode,
            cookies=cookies,
            cookies_from_browser=cookies_from_browser,
        ),
        cwd=directory,
        timeout=checked_timeout(timeout, f"{mode} download timeout"),
        env=tool.environment,
        runner=runner,
    )
    if not result.ok:
        detail = safe_text(result.stderr or result.stdout).strip()
        raise AssetError(
            f"Could not download {mode}: {detail or 'yt-dlp returned a failure'}",
            status="source_unavailable",
        )
    candidates = _new_files(directory, output_prefix, before)
    if not candidates:
        # A successful command without a newly materialized file is not proof
        # that an older or partial artifact is usable.
        raise AssetError(f"yt-dlp reported {mode} success but produced no newly materialized usable file")
    return candidates[-1], result, tool.name


def download_audio(
    url: str,
    destination: Path,
    *,
    timeout: float = 900.0,
    cookies: str | None = None,
    cookies_from_browser: str | None = None,
    yt_dlp: str | None = None,
    runner=None,
    file_prefix: str | None = None,
) -> tuple[Path, CommandResult, str]:
    return _download(
        url,
        destination,
        mode="audio",
        timeout=timeout,
        cookies=cookies,
        cookies_from_browser=cookies_from_browser,
        yt_dlp=yt_dlp,
        runner=runner,
        file_prefix=file_prefix,
    )


def download_video(
    url: str,
    destination: Path,
    *,
    timeout: float = 1200.0,
    cookies: str | None = None,
    cookies_from_browser: str | None = None,
    yt_dlp: str | None = None,
    runner=None,
    file_prefix: str | None = None,
) -> tuple[Path, CommandResult, str]:
    return _download(
        url,
        destination,
        mode="video",
        timeout=timeout,
        cookies=cookies,
        cookies_from_browser=cookies_from_browser,
        yt_dlp=yt_dlp,
        runner=runner,
        file_prefix=file_prefix,
    )


def extract_audio(
    media: Path,
    destination: Path,
    *,
    ffmpeg: str | None = None,
    timeout: float = 600.0,
    runner=None,
) -> Path:
    """Extract a local WAV without contacting the provider again."""

    source = Path(media)
    if not source.is_file() or source.is_symlink() or source.stat().st_size <= 0:
        raise AssetError(f"Video input is not a usable regular file: {source}")
    output = Path(destination)
    ensure_directory(output.parent)
    binary = find_binary("ffmpeg", ffmpeg)
    result = run_command(
        [
            binary,
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(source),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            "-y",
            str(output),
        ],
        timeout=checked_timeout(timeout, "audio extraction timeout"),
        runner=runner,
    )
    if not result.ok or not output.is_file() or output.is_symlink() or output.stat().st_size <= 0:
        detail = safe_text(result.stderr or result.stdout).strip()
        raise AssetError(
            f"Could not extract local audio: {detail or 'ffmpeg returned no usable WAV'}",
            status="source_unavailable",
        )
    return output


def probe_duration(
    media: Path,
    *,
    ffprobe: str | None = None,
    timeout: float = 30.0,
    runner=None,
) -> float | None:
    binary = find_binary("ffprobe", ffprobe)
    result = run_command(
        [
            binary,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media),
        ],
        timeout=checked_timeout(timeout, "ffprobe timeout"),
        runner=runner,
    )
    if not result.ok:
        return None
    try:
        value = float(result.stdout.strip())
    except (TypeError, ValueError):
        return None
    return value if math_is_finite_nonnegative(value) else None


_SCENE_TIME_RE = re.compile(r"(?:^|\s)pts_time:(\d+(?:\.\d+)?)")


def detect_scene_times(
    media: Path,
    *,
    ffmpeg: str | None = None,
    threshold: float = 0.30,
    timeout: float = 300.0,
    runner=None,
) -> tuple[float, ...]:
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not 0 < float(threshold) < 1:
        raise WatchVideoError("scene threshold must be between 0 and 1")
    binary = find_binary("ffmpeg", ffmpeg)
    filter_expression = f"select=gt(scene\\,{float(threshold):.3f}),showinfo"
    result = run_command(
        [
            binary,
            "-hide_banner",
            "-nostats",
            "-i", str(media),
            "-vf", filter_expression,
            "-an",
            "-f", "null",
            "-",
        ],
        timeout=checked_timeout(timeout, "scene detection timeout"),
        runner=runner,
    )
    # FFmpeg can return non-zero for a damaged tail while still yielding valid
    # showinfo timestamps.  The caller records the diagnostic and can still
    # use these candidates when present.
    values = sorted({float(match.group(1)) for match in _SCENE_TIME_RE.finditer(result.stderr)})
    return tuple(value for value in values if math_is_finite_nonnegative(value))


def math_is_finite_nonnegative(value: float) -> bool:
    import math

    return math.isfinite(value) and value >= 0


def extract_frame(
    media: Path,
    timestamp: float,
    destination: Path,
    *,
    ffmpeg: str | None = None,
    timeout: float = 60.0,
    runner=None,
) -> CommandResult:
    if not math_is_finite_nonnegative(float(timestamp)):
        raise WatchVideoError("frame timestamp must be finite and non-negative")
    target = Path(destination)
    ensure_directory(target.parent)
    binary = find_binary("ffmpeg", ffmpeg)
    result = run_command(
        [
            binary,
            "-hide_banner",
            "-loglevel", "error",
            "-ss", f"{float(timestamp):.6f}",
            "-i", str(media),
            "-frames:v", "1",
            "-vf", "scale=1280:-2:force_original_aspect_ratio=decrease",
            "-q:v", "3",
            "-y",
            str(target),
        ],
        timeout=checked_timeout(timeout, "frame extraction timeout"),
        runner=runner,
    )
    if not result.ok:
        raise AssetError(
            f"Could not extract frame at {format_timestamp(float(timestamp))}: "
            f"{safe_text(result.stderr or result.stdout).strip() or 'ffmpeg failed'}",
            status="source_unavailable",
        )
    if not target.is_file() or target.is_symlink() or target.stat().st_size <= 0:
        raise AssetError(
            f"FFmpeg reported a frame but produced no usable image at {target}",
            status="source_unavailable",
        )
    return result


def remove_temporary_media(directory: Path, *, keep: bool = False) -> list[str]:
    """Remove regular files below a disposable media dir without following links."""

    if keep:
        return []
    removed: list[str] = []
    path = Path(directory)
    if not path.exists() or path.is_symlink() or not path.is_dir():
        return removed
    files: list[Path] = []
    directories: list[Path] = []
    for child in path.rglob("*"):
        if child.is_symlink():
            continue
        if child.is_file():
            files.append(child)
        elif child.is_dir():
            directories.append(child)
    for child in sorted(files, key=lambda item: len(item.parts), reverse=True):
        try:
            child.unlink()
            removed.append(str(child.relative_to(path)))
        except OSError:
            # Cleanup warnings are reported by the caller; never delete a
            # path outside the run directory or follow a symlink.
            continue
    for child in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        try:
            child.rmdir()
        except OSError:
            pass
    return removed


__all__ = [
    "AssetError",
    "detect_scene_times",
    "download_audio",
    "extract_audio",
    "download_video",
    "extract_frame",
    "find_binary",
    "probe_duration",
    "remove_temporary_media",
]
