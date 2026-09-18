"""Resolve one remote video through yt-dlp and normalize safe metadata.

This module does not download media.  It performs the cheap metadata request
first, hides signed format URLs from the public context, and exposes a command
runner seam so the resolver can be tested without a network.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:  # Support both ``python -m scripts.resolve_media`` and direct execution.
    from .bootstrap_ytdlp import ensure_local_yt_dlp, local_venv
    from .common import (
        CommandResult,
        MAX_METADATA_OUTPUT,
        ToolUnavailableError,
        WatchVideoError,
        checked_text,
        checked_timeout,
        classify_extractor_failure,
        normalize_url,
        optional_float,
        optional_int,
        run_command,
        safe_text,
        trusted_module_available,
    )
except ImportError:  # pragma: no cover - exercised by the executable helper
    from bootstrap_ytdlp import ensure_local_yt_dlp, local_venv  # type: ignore
    from common import (  # type: ignore
        CommandResult,
        MAX_METADATA_OUTPUT,
        ToolUnavailableError,
        WatchVideoError,
        checked_text,
        checked_timeout,
        classify_extractor_failure,
        normalize_url,
        optional_float,
        optional_int,
        run_command,
        safe_text,
        trusted_module_available,
    )


@dataclass(frozen=True)
class YtDlpTool:
    """Shell-free command prefix and human-readable tool identity."""

    argv: tuple[str, ...]
    name: str
    environment: Mapping[str, str] | None = None


@dataclass(frozen=True)
class ResolvedMedia:
    """Raw extractor information plus the normalized public source record."""

    url: str
    info: Mapping[str, Any]
    source: Mapping[str, Any]
    command: CommandResult
    tool: str

    @property
    def duration(self) -> float | None:
        return optional_float(self.info.get("duration"))


_SUBTITLE_FORMAT_KEYS = (
    "ext", "name", "url", "protocol", "quality", "preference",
)
_FORMAT_KEYS = (
    "format_id", "ext", "width", "height", "fps", "vcodec", "acodec",
    "filesize", "filesize_approx", "tbr", "abr", "vbr", "format_note",
)


def find_yt_dlp(
    explicit: str | None = None,
    *,
    cwd: str | Path | None = None,
    timeout: float = 900.0,
    runner=None,
    auto_install: bool = True,
) -> YtDlpTool:
    """Find yt-dlp, bootstrapping ``<cwd>/.venv`` when it is absent."""

    if explicit is not None:
        value = checked_text(explicit, "yt-dlp executable", max_length=4096)
        path = Path(value).expanduser()
        if path.parent != Path(".") or "/" in value or "\\" in value:
            if not path.is_file() or not os.access(path, os.X_OK):
                raise ToolUnavailableError("yt-dlp", f"executable is not runnable: {path}")
            return YtDlpTool((str(path.resolve()),), "yt-dlp")
        resolved = shutil.which(value)
        if resolved:
            return YtDlpTool((resolved,), value)
        raise ToolUnavailableError("yt-dlp", f"executable was not found: {value}")

    local = local_venv(cwd)
    if local.exists():
        configured = ensure_local_yt_dlp(cwd, timeout=timeout, runner=runner)
        return YtDlpTool(
            configured.argv,
            f"local .venv yt-dlp {configured.version}",
            configured.environment,
        )
    found = shutil.which("yt-dlp")
    if found:
        return YtDlpTool((found,), "yt-dlp")
    if trusted_module_available("yt_dlp"):
        return YtDlpTool((sys.executable, "-m", "yt_dlp"), "python -m yt_dlp")
    if not auto_install:
        raise ToolUnavailableError(
            "yt-dlp",
            "automatic setup is disabled for an injected command runner; provide an explicit executable",
        )
    local = ensure_local_yt_dlp(cwd, timeout=timeout, runner=runner)
    return YtDlpTool(local.argv, f"local .venv yt-dlp {local.version}", local.environment)


def _auth_arguments(
    cookies: str | None,
    cookies_from_browser: str | None,
) -> tuple[str, ...]:
    if cookies is not None and cookies_from_browser is not None:
        raise WatchVideoError("Specify either cookies or cookies-from-browser, not both")
    if cookies is not None:
        path = Path(checked_text(cookies, "cookies file", max_length=4096)).expanduser()
        try:
            if not path.is_file() or path.is_symlink():
                raise WatchVideoError(f"Cookies file is not a regular file: {path}")
        except OSError as exc:
            raise WatchVideoError(f"Cookies file cannot be inspected: {safe_text(exc)}") from exc
        return ("--cookies", str(path.resolve()))
    if cookies_from_browser is not None:
        browser = checked_text(cookies_from_browser, "browser cookie source", max_length=256)
        if any(character.isspace() for character in browser) or browser.startswith("-"):
            raise WatchVideoError("browser cookie source must be a compact yt-dlp browser name")
        return ("--cookies-from-browser", browser)
    return ()


def _command(
    tool: YtDlpTool,
    url: str,
    *,
    cookies: str | None,
    cookies_from_browser: str | None,
) -> list[str]:
    return [
        *tool.argv,
        "--ignore-config",
        "--no-playlist",
        "--no-warnings",
        "--dump-single-json",
        "--skip-download",
        *_auth_arguments(cookies, cookies_from_browser),
        "--",
        url,
    ]


def _json_from_output(text: str) -> dict[str, Any] | None:
    """Read extractor JSON even if a wrapper emitted harmless log lines."""

    stripped = text.strip()
    if not stripped:
        return None
    try:
        value = json.loads(stripped)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    candidates: list[tuple[int, int, int, dict[str, Any]]] = []
    root_markers = {
        "extractor_key", "extractor", "id", "webpage_url", "title",
        "duration", "formats", "subtitles", "automatic_captions",
    }
    for index, character in enumerate(stripped):
        if character != "{":
            continue
        try:
            value, end = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            marker_score = len(root_markers.intersection(value))
            # Prefer a likely extractor root and, within the same score, the
            # largest complete object. Truncation is rejected by
            # resolve_media before this parser is called.
            candidates.append((marker_score, end, -index, value))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    return candidates[0][3]


def _string(value: object, *, limit: int = 4096) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return safe_text(value.strip(), limit)


def _language_tracks(info: Mapping[str, Any]) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    for source_name, key in (("human", "subtitles"), ("automatic", "automatic_captions")):
        values = info.get(key)
        if not isinstance(values, Mapping):
            continue
        for language in sorted((str(item) for item in values.keys()), key=str.casefold):
            formats = values.get(language)
            format_rows: list[dict[str, Any]] = []
            if isinstance(formats, Sequence) and not isinstance(formats, (str, bytes, bytearray)):
                for item in formats:
                    if not isinstance(item, Mapping):
                        continue
                    row = {
                        field: item[field]
                        for field in _SUBTITLE_FORMAT_KEYS
                        if field in item and field != "url"
                    }
                    if row:
                        format_rows.append(row)
            track: dict[str, Any] = {"language": language, "source": source_name}
            if format_rows:
                track["formats"] = format_rows
            tracks.append(track)
    return tracks


def _format_rows(info: Mapping[str, Any]) -> list[dict[str, Any]]:
    formats = info.get("formats")
    if not isinstance(formats, Sequence) or isinstance(formats, (str, bytes, bytearray)):
        return []
    rows: list[dict[str, Any]] = []
    for item in formats:
        if not isinstance(item, Mapping):
            continue
        row: dict[str, Any] = {}
        for field in _FORMAT_KEYS:
            if field not in item:
                continue
            value = item[field]
            if field in {"width", "height", "filesize", "filesize_approx"}:
                value = optional_int(value)
            elif field in {"fps", "tbr", "abr", "vbr"}:
                value = optional_float(value)
            elif field in {"format_id", "ext", "vcodec", "acodec", "format_note"}:
                value = _string(value)
            if value is not None:
                row[field] = value
        if row:
            rows.append(row)
    return rows


def _chapters(info: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = info.get("chapters")
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        return []
    rows: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, Mapping):
            continue
        start = optional_float(item.get("start_time", item.get("start")))
        end = optional_float(item.get("end_time", item.get("end")))
        title = _string(item.get("title"))
        if start is None or end is None or end <= start:
            continue
        row: dict[str, Any] = {"start": start, "end": end}
        if title is not None:
            row["title"] = title
        rows.append(row)
    return rows


def normalize_metadata(info: Mapping[str, Any], url: str) -> dict[str, Any]:
    """Expose only useful metadata; never expose signed media URLs."""

    normalized_url = normalize_url(url)
    extractor = _string(info.get("extractor_key")) or _string(info.get("extractor"))
    platform = (extractor or "unknown").casefold()
    source: dict[str, Any] = {"url": normalized_url, "platform": platform}

    mappings = (
        ("id", "id"),
        ("title", "title"),
        ("description", "description"),
        ("creator", "creator"),
        ("uploader", "uploader"),
        ("channel", "channel"),
        ("account", "account"),
        ("upload_date", "upload_date"),
        ("language", "language"),
        ("thumbnail", "thumbnail"),
    )
    for target, key in mappings:
        if target in source:
            continue
        value = _string(info.get(key), limit=12000 if key == "description" else 4096)
        if value is not None:
            source[target] = value
            if key == "description" and isinstance(info.get(key), str) and len(info[key]) > 12000:
                source["description_truncated"] = True
    if "creator" not in source:
        value = _string(info.get("uploader"))
        if value is not None:
            source["creator"] = value
    duration = optional_float(info.get("duration"))
    if duration is not None and duration >= 0:
        source["duration"] = duration
    views = optional_int(info.get("view_count"))
    if views is not None and views >= 0:
        source["view_count"] = views
    tracks = _language_tracks(info)
    if tracks:
        source["available_subtitles"] = tracks
    formats = _format_rows(info)
    if formats:
        source["available_formats"] = formats
    chapters = _chapters(info)
    if chapters:
        source["chapters"] = chapters
    return source


def resolve_media(
    url: str,
    *,
    timeout: float = 120.0,
    cookies: str | None = None,
    cookies_from_browser: str | None = None,
    yt_dlp: str | None = None,
    runner=None,
) -> ResolvedMedia:
    """Fetch metadata and fail with a stable, honest source status."""

    normalized = normalize_url(url)
    limit = checked_timeout(timeout, "metadata timeout")
    tool = find_yt_dlp(
        yt_dlp,
        timeout=timeout,
        runner=runner,
        auto_install=runner is None,
    )
    result = run_command(
        _command(tool, normalized, cookies=cookies, cookies_from_browser=cookies_from_browser),
        timeout=limit,
        env=tool.environment,
        runner=runner,
        output_limit=MAX_METADATA_OUTPUT,
    )
    if result.output_truncated:
        raise WatchVideoError(
            "yt-dlp metadata exceeded the bounded structured-output limit; "
            "the incomplete JSON was rejected",
            status="source_unavailable",
        )
    if not result.ok:
        status, reason = classify_extractor_failure(result)
        detail = safe_text(result.stderr or result.stdout).strip()
        suffix = f" Provider detail: {detail}" if detail else "."
        raise WatchVideoError(f"yt-dlp failed: {reason}.{suffix}", status=status)
    info = _json_from_output(result.stdout)
    if info is None:
        raise WatchVideoError(
            "yt-dlp returned no usable metadata JSON",
            status="source_unavailable",
        )
    return ResolvedMedia(
        url=normalized,
        info=info,
        source=normalize_metadata(info, normalized),
        command=result,
        tool=tool.name,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve video metadata with yt-dlp")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--cookies")
    parser.add_argument("--cookies-from-browser", dest="cookies_from_browser")
    parser.add_argument("--yt-dlp", dest="yt_dlp")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        resolved = resolve_media(
            args.url,
            timeout=args.timeout,
            cookies=args.cookies,
            cookies_from_browser=args.cookies_from_browser,
            yt_dlp=args.yt_dlp,
        )
        print(json.dumps({"status": "complete", "source": resolved.source}, ensure_ascii=False, indent=2))
        return 0
    except WatchVideoError as exc:
        print(json.dumps({"status": exc.status, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":  # pragma: no cover - exercised by CLI smoke tests
    raise SystemExit(main())


__all__ = [
    "ResolvedMedia",
    "YtDlpTool",
    "find_yt_dlp",
    "normalize_metadata",
    "resolve_media",
]
