"""Direct YouTube caption fallback for the watch-video pipeline.

The primary watch-video path uses yt-dlp for provider metadata and subtitle
files.  Some YouTube responses expose a usable caption track through the
Innertube player API even when yt-dlp cannot resolve the page.  This module
uses only the standard library to obtain that bounded caption evidence and
returns the same normalized ``SubtitleResult`` contract as ``transcript.py``.

Signed caption URLs and raw player responses stay inside this module.  They are
never placed in public metadata, artifacts, diagnostics, or warnings.
"""

from __future__ import annotations

import html
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

try:
    from .common import (
        MAX_METADATA_OUTPUT,
        WatchVideoError,
        atomic_write_text,
        checked_text,
        checked_timeout,
        ensure_directory,
        format_timestamp,
        normalize_url,
        safe_filename,
        safe_text,
    )
    from .transcript import (
        SubtitleResult,
        _all_subtitle_choices,
        _subtitle_choices,
        _subtitle_warning_summary,
        normalize_segments,
    )
except ImportError:  # pragma: no cover - direct executable path
    from common import (  # type: ignore
        MAX_METADATA_OUTPUT,
        WatchVideoError,
        atomic_write_text,
        checked_text,
        checked_timeout,
        ensure_directory,
        format_timestamp,
        normalize_url,
        safe_filename,
        safe_text,
    )
    from transcript import (  # type: ignore
        SubtitleResult,
        _all_subtitle_choices,
        _subtitle_choices,
        _subtitle_warning_summary,
        normalize_segments,
    )


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
YOUTUBE_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
API_KEY_PATTERNS = (
    re.compile(r'"INNERTUBE_API_KEY":"([^"]+)"'),
    re.compile(r'INNERTUBE_API_KEY\\":\\"([^\\"]+)\\"'),
)
XML_TEXT_RE = re.compile(
    r"<text\b[^>]*\bstart=\"([^\"]+)\"[^>]*\bdur=\"([^\"]+)\"[^>]*>(.*?)</text>",
    re.IGNORECASE | re.DOTALL,
)
MAX_CAPTION_BYTES = 8 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class YoutubeCaptionTrack:
    """Private caption-track identity; ``url`` must never leave this module."""

    language: str
    source: str
    url: str


@dataclass(frozen=True)
class YoutubeCaptionData:
    """Player metadata and private caption tracks obtained from YouTube."""

    video_id: str
    info: Mapping[str, Any]
    tracks: tuple[YoutubeCaptionTrack, ...]


HttpOpener = Callable[..., Any]


def youtube_video_id(url: str) -> str | None:
    """Return the video ID for a supported YouTube URL, if it is present."""

    try:
        parts = urlsplit(normalize_url(url))
    except WatchVideoError:
        return None
    host = (parts.hostname or "").casefold()
    if host not in YOUTUBE_HOSTS and host not in YOUTUBE_SHORT_HOSTS:
        return None
    if host in YOUTUBE_SHORT_HOSTS:
        candidate = parts.path.strip("/").split("/", 1)[0]
    else:
        query = parse_qs(parts.query)
        candidate = query.get("v", [""])[0]
        if not candidate:
            path_parts = [item for item in parts.path.split("/") if item]
            if len(path_parts) >= 2 and path_parts[0].casefold() in {"embed", "shorts", "live", "v", "e"}:
                candidate = path_parts[1]
    return candidate if VIDEO_ID_RE.fullmatch(candidate) else None


def is_youtube_url(url: str) -> bool:
    return youtube_video_id(url) is not None


def _read_bounded(response: Any, limit: int) -> bytes:
    length = None
    headers = getattr(response, "headers", None)
    if headers is not None:
        try:
            value = headers.get("Content-Length")
            if value is not None:
                length = int(value)
        except (TypeError, ValueError):
            length = None
    if length is not None and length > limit:
        raise WatchVideoError(
            "YouTube fallback response exceeded the bounded size limit",
            status="source_unavailable",
        )
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(READ_CHUNK_BYTES, limit - total + 1))
        if not chunk:
            break
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8")
        if not isinstance(chunk, bytes):
            raise WatchVideoError(
                "YouTube fallback returned a non-byte response",
                status="source_unavailable",
            )
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise WatchVideoError(
                "YouTube fallback response exceeded the bounded size limit",
                status="source_unavailable",
            )
    return b"".join(chunks)


def _http_failure(label: str, error: BaseException) -> WatchVideoError:
    status_code = getattr(error, "code", None)
    if status_code in {401, 403}:
        status = "authentication_required"
    else:
        status = "source_unavailable"
    # urllib exception messages may include a signed caption URL. Never echo it.
    detail = f"HTTP {status_code}" if isinstance(status_code, int) else type(error).__name__
    return WatchVideoError(f"YouTube {label} request failed: {detail}", status=status)


def _cookie_header(cookies: str | None) -> str | None:
    if cookies is None:
        return None
    path = Path(checked_text(cookies, "cookies file", max_length=4096)).expanduser()
    if not path.is_file() or path.is_symlink():
        raise WatchVideoError(f"Cookies file is not a regular file: {path}")
    pairs: list[str] = []
    try:
        if path.stat().st_size > 1024 * 1024:
            raise WatchVideoError("Cookies file exceeds the bounded size limit")
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise WatchVideoError(f"Cookies file cannot be read: {safe_text(exc)}") from exc
    for line in lines:
        if not line or (line.startswith("#") and not line.startswith("#HttpOnly_")):
            continue
        fields = line.split("\t")
        if len(fields) != 7:
            continue
        domain = fields[0].removeprefix("#HttpOnly_").lstrip(".").casefold()
        if domain != "youtube.com" and domain != "google.com":
            continue
        name, value = fields[5].strip(), fields[6].strip()
        if name and "\r" not in name and "\n" not in name and "\r" not in value and "\n" not in value:
            pairs.append(f"{name}={value}")
    return "; ".join(pairs) if pairs else None


def _fetch_text(
    url: str,
    *,
    timeout: float,
    language: str | None = None,
    method: str = "GET",
    body: bytes | None = None,
    cookies: str | None = None,
    opener: HttpOpener | None = None,
    limit: int,
    label: str,
) -> str:
    headers = {"User-Agent": DEFAULT_USER_AGENT}
    if language:
        headers["Accept-Language"] = language
    cookie = _cookie_header(cookies)
    if cookie:
        headers["Cookie"] = cookie
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        response = (
            opener(request, timeout=timeout)
            if opener is not None
            else urlopen(request, timeout=timeout)
        )
        with response:
            raw = _read_bounded(response, limit)
    except HTTPError as exc:
        raise _http_failure(label, exc) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise _http_failure(label, exc) from exc
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WatchVideoError(
            f"YouTube {label} response was not valid UTF-8",
            status="source_unavailable",
        ) from exc


def _api_key(page: str) -> str:
    for pattern in API_KEY_PATTERNS:
        match = pattern.search(page)
        if match:
            return match.group(1)
    raise WatchVideoError(
        "YouTube watch page did not expose an Innertube API key",
        status="source_unavailable",
    )


def _text(value: object, *, limit: int = 12000) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return safe_text(value.strip(), limit)


def _positive_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _non_negative_int(value: object) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _track_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parts = urlsplit(value)
    except ValueError:
        return None
    host = (parts.hostname or "").casefold()
    if parts.scheme != "https" or (host != "youtube.com" and not host.endswith(".youtube.com")):
        return None
    if parts.username or parts.password or parts.port is not None:
        return None
    return value


def _player_info(
    player: Mapping[str, Any],
    video_id: str,
    tracks: Sequence[YoutubeCaptionTrack],
) -> dict[str, Any]:
    details = player.get("videoDetails")
    details = details if isinstance(details, Mapping) else {}
    info: dict[str, Any] = {
        "extractor_key": "Youtube",
        "id": _text(details.get("videoId"), limit=64) or video_id,
    }
    mapping = (
        ("title", "title"),
        ("description", "shortDescription"),
        ("uploader", "author"),
        ("creator", "author"),
        ("channel", "author"),
        ("language", "defaultAudioLanguage"),
    )
    for target, key in mapping:
        value = _text(details.get(key))
        if value is not None:
            info[target] = value
    duration = _positive_float(details.get("lengthSeconds"))
    if duration is not None:
        info["duration"] = duration
    view_count = _non_negative_int(details.get("viewCount"))
    if view_count is not None:
        info["view_count"] = view_count
    thumbnails = details.get("thumbnail")
    if isinstance(thumbnails, Mapping):
        rows = thumbnails.get("thumbnails")
        if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)):
            for row in reversed(rows):
                if isinstance(row, Mapping):
                    thumbnail = _text(row.get("url"), limit=4096)
                    if thumbnail is not None:
                        info["thumbnail"] = thumbnail
                        break

    microformat = player.get("microformat")
    if isinstance(microformat, Mapping):
        micro = microformat.get("playerMicroformatRenderer")
        if isinstance(micro, Mapping):
            upload_date = _text(micro.get("uploadDate"), limit=32) or _text(micro.get("publishDate"), limit=32)
            if upload_date is not None:
                info["upload_date"] = upload_date.replace("-", "")

    inventory: dict[str, dict[str, list[dict[str, str]]]] = {"human": {}, "automatic": {}}
    for track in tracks:
        inventory[track.source].setdefault(track.language, []).append({"ext": "xml"})
    if inventory["human"]:
        info["subtitles"] = inventory["human"]
    if inventory["automatic"]:
        info["automatic_captions"] = inventory["automatic"]
    return info


def fetch_youtube_captions(
    url: str,
    *,
    timeout: float = 180.0,
    preferred_language: str | None = None,
    cookies: str | None = None,
    cookies_from_browser: str | None = None,
    opener: HttpOpener | None = None,
) -> YoutubeCaptionData:
    """Fetch YouTube player metadata and private caption-track URLs.

    The function does not fetch caption text yet, so callers can reuse the
    player response for metadata recovery and transcript acquisition.
    """

    video_id = youtube_video_id(url)
    if video_id is None:
        raise WatchVideoError(
            "direct YouTube caption fallback requires a supported YouTube URL",
            status="unsupported_source",
        )
    if cookies_from_browser is not None:
        raise WatchVideoError(
            "direct YouTube caption fallback cannot read browser cookies; retry with a cookies file or yt-dlp",
            status="tool_unavailable",
        )
    limit = checked_timeout(timeout, "YouTube caption fallback timeout")
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    page = _fetch_text(
        watch_url,
        timeout=limit,
        language=preferred_language,
        cookies=cookies,
        opener=opener,
        limit=MAX_METADATA_OUTPUT,
        label="watch page",
    )
    api_key = _api_key(page)
    player_url = "https://www.youtube.com/youtubei/v1/player?" + urlencode({"key": api_key})
    player_body = json.dumps(
        {
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "20.10.38",
                }
            },
            "videoId": video_id,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    player_text = _fetch_text(
        player_url,
        timeout=limit,
        language=preferred_language,
        method="POST",
        body=player_body,
        cookies=cookies,
        opener=opener,
        limit=MAX_METADATA_OUTPUT,
        label="player API",
    )
    try:
        player = json.loads(player_text)
    except json.JSONDecodeError as exc:
        raise WatchVideoError(
            "YouTube player API returned invalid JSON",
            status="source_unavailable",
        ) from exc
    if not isinstance(player, Mapping):
        raise WatchVideoError(
            "YouTube player API returned an invalid response",
            status="source_unavailable",
        )
    playability = player.get("playabilityStatus")
    playability = playability if isinstance(playability, Mapping) else {}
    playability_status = playability.get("status")
    if playability_status != "OK":
        status = "authentication_required" if playability_status in {"LOGIN_REQUIRED", "AGE_VERIFICATION_REQUIRED"} else "source_unavailable"
        raise WatchVideoError(f"YouTube player did not confirm video playability ({safe_text(playability_status, 64)})", status=status)

    captions = player.get("captions")
    captions = captions if isinstance(captions, Mapping) else {}
    tracklist = captions.get("playerCaptionsTracklistRenderer")
    if not isinstance(tracklist, Mapping):
        tracklist = player.get("playerCaptionsTracklistRenderer")
    track_rows = tracklist.get("captionTracks") if isinstance(tracklist, Mapping) else []
    tracks: list[YoutubeCaptionTrack] = []
    if isinstance(track_rows, Sequence) and not isinstance(track_rows, (str, bytes, bytearray)):
        for row in track_rows:
            if not isinstance(row, Mapping):
                continue
            language = _text(row.get("languageCode"), limit=128)
            base_url = _track_url(row.get("baseUrl") or row.get("url"))
            if language is None or base_url is None:
                continue
            source = "automatic" if row.get("kind") == "asr" else "human"
            tracks.append(YoutubeCaptionTrack(language=language, source=source, url=base_url))
    info = _player_info(player, video_id, tracks)
    if info.get("id") != video_id:
        raise WatchVideoError("YouTube player returned metadata for a different video", status="source_unavailable")
    return YoutubeCaptionData(video_id=video_id, info=info, tracks=tuple(tracks))


def _caption_records(xml_text: str) -> list[tuple[float, float, str]]:
    # Match only caption text nodes, not a general XML document: untrusted
    # external entities and entity-expansion payloads are never parsed.
    records: list[tuple[float, float, str]] = []
    for match in XML_TEXT_RE.finditer(xml_text):
        start = _positive_float(match.group(1))
        duration = _positive_float(match.group(2))
        if start is None or duration is None or duration <= 0:
            continue
        cleaned = _clean_fallback_text(match.group(3))
        if cleaned:
            records.append((start, start + duration, cleaned))
    return records


def _clean_fallback_text(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.replace("\r", " ").replace("\n", " ").split()).strip()


def _render_vtt(records: Sequence[tuple[float, float, str]]) -> str:
    lines = ["WEBVTT", ""]
    for start, end, text in records:
        lines.extend((f"{format_timestamp(start)} --> {format_timestamp(end)}", text, ""))
    return "\n".join(lines) + "\n"


def _track_choices(
    data: YoutubeCaptionData,
    preferred_languages: Sequence[str],
    max_attempts: int,
) -> tuple[list[tuple[Any, YoutubeCaptionTrack]], int]:
    all_choices = _all_subtitle_choices(data.info)
    choices = _subtitle_choices(
        data.info,
        preferred_languages,
        max_attempts=max_attempts,
        target_first=True,
    )
    by_key: dict[tuple[str, str], YoutubeCaptionTrack] = {}
    for track in data.tracks:
        by_key.setdefault((track.source, track.language.casefold()), track)
    selected: list[tuple[Any, YoutubeCaptionTrack]] = []
    for choice in choices:
        track = by_key.get((choice.source, choice.language.casefold()))
        if track is not None:
            selected.append((choice, track))
    return selected, len(all_choices)


def acquire_youtube_subtitles(
    data: YoutubeCaptionData,
    destination: Path,
    *,
    preferred_languages: Sequence[str] = (),
    max_attempts: int = 6,
    timeout: float = 180.0,
    cookies: str | None = None,
    opener: HttpOpener | None = None,
):
    """Fetch and normalize one bounded YouTube caption track.

    The return value is the existing ``transcript.SubtitleResult`` type.  The
    import remains local to avoid making transcript parsing depend on this
    network adapter during module initialization.
    """

    if type(max_attempts) is not int or not 1 <= max_attempts <= 24:
        raise WatchVideoError("max subtitle attempts must be an integer between 1 and 24")
    raw_directory = Path(destination).expanduser()
    if not raw_directory.is_absolute():
        raw_directory = Path.cwd() / raw_directory
    directory = ensure_directory(raw_directory.resolve(strict=False))
    selected, advertised = _track_choices(data, preferred_languages, max_attempts)
    if not selected:
        return SubtitleResult(
            status="unavailable",
            choice=None,
            path=None,
            segments=(),
            quality=None,
            command=None,
            warnings=("YouTube player exposed no caption track matching the bounded language policy",),
            attempted=0,
            advertised=advertised,
        )
    failures: list[tuple[Any, str]] = []
    no_files: list[Any] = []
    quality_failures: list[tuple[Any, Any]] = []
    saw_file = False
    selected_limit = checked_timeout(timeout, "YouTube subtitle fallback timeout")
    for index, (choice, track) in enumerate(selected, start=1):
        attempt_dir = directory / f"{index:03d}-{choice.source}-{safe_filename(choice.language, fallback='language')}"
        ensure_directory(attempt_dir)
        transcript_url = re.sub(r"&fmt=[^&]+", "", track.url)
        try:
            body = _fetch_text(
                transcript_url,
                timeout=selected_limit,
                language=choice.language,
                cookies=cookies,
                opener=opener,
                limit=MAX_CAPTION_BYTES,
                label="caption track",
            )
            records = _caption_records(body)
            if not records:
                no_files.append(choice)
                continue
            saw_file = True
            segments, quality = normalize_segments(records)
            if not quality.recoverable:
                quality_failures.append((choice, quality))
                continue
            raw_path = attempt_dir / "001-subtitle.vtt"
            atomic_write_text(raw_path, _render_vtt(records))
            warnings = _subtitle_warning_summary(
                advertised=advertised,
                attempted=index,
                failures=failures,
                no_files=no_files,
                quality_failures=quality_failures,
                parse_failures=0,
                selected=choice,
                selected_quality=quality,
            )
            warnings.insert(0, "direct YouTube caption-track fallback was used")
            return SubtitleResult(
                status="usable" if quality.usable else "best_effort",
                choice=choice,
                path=raw_path,
                segments=segments,
                quality=quality,
                command=None,
                warnings=tuple(warnings),
                attempted=index,
                advertised=advertised,
            )
        except WatchVideoError as exc:
            failures.append((choice, safe_text(exc)))
    warnings = _subtitle_warning_summary(
        advertised=advertised,
        attempted=len(selected),
        failures=failures,
        no_files=no_files,
        quality_failures=quality_failures,
        parse_failures=0,
    )
    if not warnings:
        warnings.append("YouTube caption fallback returned no usable timestamped track")
    warnings.insert(0, "direct YouTube caption-track fallback did not produce a usable transcript")
    first_choice = selected[0][0] if selected else None
    return SubtitleResult(
        status="unusable" if saw_file else "unavailable",
        choice=first_choice,
        path=None,
        segments=(),
        quality=None,
        command=None,
        warnings=tuple(warnings),
        attempted=len(selected),
        advertised=advertised,
    )


__all__ = [
    "YoutubeCaptionData",
    "YoutubeCaptionTrack",
    "acquire_youtube_subtitles",
    "fetch_youtube_captions",
    "is_youtube_url",
    "youtube_video_id",
]
