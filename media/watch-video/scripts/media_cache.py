"""Persistent per-URL video, WAV, and transcript cache outside run artifacts.

The semantic run directory remains workspace-local, while this cache prevents
repeated media downloads across tasks and projects.  A URL is represented by a
safe, human-readable directory key plus a hash of the normalized URL; the raw
URL is kept only in the local manifest for identity validation.
"""

from __future__ import annotations

import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit

try:
    from .common import (
        WatchVideoError,
        atomic_write_json,
        ensure_directory,
        file_sha256,
        normalize_url,
        read_json,
        safe_filename,
        short_hash,
    )
    from .media_assets import download_audio, download_video, extract_audio
    from .transcript_markdown import write_transcript_markdown
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        WatchVideoError,
        atomic_write_json,
        ensure_directory,
        file_sha256,
        normalize_url,
        read_json,
        safe_filename,
        short_hash,
    )
    from media_assets import download_audio, download_video, extract_audio  # type: ignore
    from transcript_markdown import write_transcript_markdown  # type: ignore


MEDIA_CACHE_VERSION = 1
MANIFEST_NAME = "000-manifest.json"
VIDEO_PREFIX = "001-video"
AUDIO_PREFIX = "006-audio"
AUDIO_NAME = f"{AUDIO_PREFIX}.wav"
TRANSCRIPT_NAME = "002-transcript.json"
TRANSCRIPT_SOURCE_NAME = "003-transcript-source.json"
TRANSCRIPT_RAW_NAME = "004-transcript.vtt"
TRANSCRIPT_MARKDOWN_NAME = "005-transcript.md"
VIDEO_EXTENSIONS = {
    ".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".flv", ".ts", ".3gp",
}


@dataclass(frozen=True)
class PersistentTranscript:
    payload: Mapping[str, Any]
    original_payload: Mapping[str, Any] | None
    path: Path
    original_path: Path | None
    raw_path: Path | None
    markdown_path: Path | None = None


@dataclass(frozen=True)
class VideoCache:
    key: str
    directory: Path
    video_path: Path
    manifest: Mapping[str, Any]

    @property
    def display_path(self) -> str:
        return f"~/.local/videos/{self.key}"

    @property
    def audio_path(self) -> Path | None:
        name = self.manifest.get("audio")
        if not isinstance(name, str):
            return None
        path = _child_file(self.directory, name)
        if path is None:
            return None
        expected_size = self.manifest.get("audio_size")
        if isinstance(expected_size, int) and not isinstance(expected_size, bool):
            try:
                if path.stat().st_size != expected_size:
                    return None
            except OSError:
                return None
        expected_hash = self.manifest.get("audio_sha256")
        if isinstance(expected_hash, str):
            try:
                if file_sha256(path) != expected_hash:
                    return None
            except WatchVideoError:
                return None
        return path

    @property
    def audio_display_path(self) -> str | None:
        path = self.audio_path
        return f"{self.display_path}/{path.name}" if path is not None else None

    @property
    def transcript_path(self) -> Path:
        return self.directory / TRANSCRIPT_NAME

    @property
    def raw_transcript_path(self) -> Path:
        return self.directory / TRANSCRIPT_RAW_NAME

    @property
    def transcript_markdown_path(self) -> Path:
        return self.directory / TRANSCRIPT_MARKDOWN_NAME

    def read_transcript(self) -> PersistentTranscript | None:
        name = self.manifest.get("transcript")
        if not isinstance(name, str):
            return None
        path = _child_file(self.directory, name)
        if path is None:
            return None
        try:
            payload = read_json(path)
        except WatchVideoError:
            return None
        if not isinstance(payload, dict):
            return None
        original_payload: Mapping[str, Any] | None = None
        original_path: Path | None = None
        original_name = self.manifest.get("transcript_original")
        if isinstance(original_name, str):
            original_path = _child_file(self.directory, original_name)
            if original_path is not None:
                try:
                    value = read_json(original_path)
                except WatchVideoError:
                    value = None
                if isinstance(value, dict):
                    original_payload = value
                else:
                    original_path = None
        raw_path = _child_file(self.directory, TRANSCRIPT_RAW_NAME)
        markdown_name = self.manifest.get("transcript_markdown", TRANSCRIPT_MARKDOWN_NAME)
        markdown_path = (
            _child_file(self.directory, markdown_name)
            if isinstance(markdown_name, str)
            else None
        )
        return PersistentTranscript(payload, original_payload, path, original_path, raw_path, markdown_path)


def media_cache_key(url: str) -> str:
    normalized = normalize_url(url)
    parts = urlsplit(normalized)
    host = parts.hostname or "video"
    path_label = parts.path.strip("/").replace("/", "-") or "video"
    label = safe_filename(f"{host}-{path_label}", fallback="video")[:56].rstrip(".-")
    return f"{label}-{short_hash(normalized, 24)}"


def media_cache_base(root: str | Path | None = None) -> Path:
    value = Path(root).expanduser() if root is not None else Path.home() / ".local" / "videos"
    if value.exists() and value.is_symlink():
        raise WatchVideoError(f"persistent media cache root is a symlink: {value}")
    value = value.resolve(strict=False)
    return ensure_directory(value)


def _child_file(directory: Path, name: str) -> Path | None:
    candidate = Path(name)
    if candidate.is_absolute() or candidate.name != name:
        return None
    path = directory / candidate
    try:
        if not path.resolve(strict=False).is_relative_to(directory.resolve()):
            return None
    except OSError:
        return None
    if not path.is_file() or path.is_symlink() or path.stat().st_size <= 0:
        return None
    return path


def _manifest(directory: Path) -> dict[str, Any] | None:
    path = directory / MANIFEST_NAME
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = read_json(path)
    except WatchVideoError:
        return None
    return value if isinstance(value, dict) else None


def _cache_directory(url: str, root: str | Path | None = None) -> tuple[str, Path]:
    base = media_cache_base(root)
    key = media_cache_key(url)
    return key, base / key


def load_video(url: str, *, root: str | Path | None = None) -> VideoCache | None:
    normalized = normalize_url(url)
    key, directory = _cache_directory(normalized, root)
    if not directory.is_dir() or directory.is_symlink():
        return None
    manifest = _manifest(directory)
    if manifest is None:
        return None
    if manifest.get("version") != MEDIA_CACHE_VERSION or manifest.get("source_url") != normalized:
        return None
    name = manifest.get("video")
    if not isinstance(name, str):
        return None
    video = _child_file(directory, name)
    if video is None:
        return None
    expected_hash = manifest.get("sha256")
    if isinstance(expected_hash, str):
        try:
            if file_sha256(video) != expected_hash:
                return None
        except WatchVideoError:
            return None
    return VideoCache(key, directory, video, manifest)


def _remove_known_files(directory: Path, *, include_transcript: bool) -> None:
    prefixes = (VIDEO_PREFIX,) if not include_transcript else (
        "002-transcript", "003-transcript", "004-transcript", "005-transcript", AUDIO_PREFIX
    )
    for child in directory.iterdir():
        if child.is_symlink() or not child.is_file():
            continue
        if child.name == MANIFEST_NAME or any(child.name.startswith(prefix) for prefix in prefixes):
            try:
                child.unlink()
            except OSError:
                pass


def ensure_video(
    url: str,
    *,
    source: Mapping[str, Any] | None = None,
    root: str | Path | None = None,
    refresh: bool = False,
    timeout: float = 1200.0,
    cookies: str | None = None,
    cookies_from_browser: str | None = None,
    yt_dlp: str | None = None,
    runner=None,
) -> tuple[VideoCache, bool, str]:
    """Return a verified cached video, downloading it once when absent/stale."""

    normalized = normalize_url(url)
    existing = load_video(normalized, root=root)
    if not refresh and existing is not None:
        return existing, False, "cache"
    key, directory = _cache_directory(normalized, root)
    ensure_directory(directory)
    staging = directory / f"000-download-{uuid.uuid4().hex}"
    ensure_directory(staging)
    try:
        downloaded, _, tool = download_video(
            normalized,
            staging,
            timeout=timeout,
            cookies=cookies,
            cookies_from_browser=cookies_from_browser,
            yt_dlp=yt_dlp,
            runner=runner,
            file_prefix=VIDEO_PREFIX,
        )
        suffix = downloaded.suffix.casefold() or ".mp4"
        if suffix not in VIDEO_EXTENSIONS:
            raise WatchVideoError(f"yt-dlp produced an unexpected video extension: {suffix}")
        target = directory / f"{VIDEO_PREFIX}{suffix}"
        os.replace(downloaded, target)
        for child in directory.iterdir():
            if child == target or child == staging or child.name == MANIFEST_NAME:
                continue
            if child.is_file() and not child.is_symlink() and child.name.startswith(VIDEO_PREFIX):
                try:
                    child.unlink()
                except OSError:
                    pass
        # A refreshed video invalidates any transcript tied to the previous
        # media bytes. The old files are removed only after a new video exists.
        _remove_known_files(directory, include_transcript=True)
        manifest: dict[str, Any] = {
            "version": MEDIA_CACHE_VERSION,
            "source_url": normalized,
            "video": target.name,
            "sha256": file_sha256(target),
            "size": target.stat().st_size,
            "downloaded_at": time.time(),
        }
        if source:
            safe_source = {
                key_name: value for key_name, value in source.items()
                if key_name not in {"url", "available_formats", "available_subtitles"}
            }
            manifest["source"] = safe_source
        atomic_write_json(directory / MANIFEST_NAME, manifest)
        cached = load_video(normalized, root=root)
        if cached is None:
            raise WatchVideoError("persistent video cache read-back failed")
        return cached, True, tool
    except Exception:
        # A refresh is an explicit attempt, not permission to discard the
        # last verified local copy when the provider is temporarily unavailable.
        fallback = load_video(normalized, root=root) if existing is not None else None
        if fallback is not None:
            return fallback, False, "cache-fallback"
        raise
    finally:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging, ignore_errors=True)


def ensure_audio(
    cache: VideoCache,
    *,
    url: str | None = None,
    ffmpeg: str | None = None,
    timeout: float = 600.0,
    cookies: str | None = None,
    cookies_from_browser: str | None = None,
    yt_dlp: str | None = None,
    runner=None,
) -> tuple[VideoCache, bool]:
    """Create or reuse the persistent WAV derived from a verified video.

    Older caches may contain a video-only representation. In that case, use a
    bounded provider audio download when the source URL is available, without
    replacing or re-downloading the cached video.
    """

    existing = cache.audio_path
    if existing is not None:
        return cache, False

    staging = cache.directory / f"000-audio-{uuid.uuid4().hex}"
    ensure_directory(staging)
    audio_source = "video"
    try:
        try:
            extracted = extract_audio(
                cache.video_path,
                staging / AUDIO_NAME,
                ffmpeg=ffmpeg,
                timeout=timeout,
                runner=runner,
            )
        except WatchVideoError as local_error:
            if url is None:
                raise
            try:
                extracted, _, _ = download_audio(
                    normalize_url(url),
                    staging,
                    timeout=timeout,
                    cookies=cookies,
                    cookies_from_browser=cookies_from_browser,
                    yt_dlp=yt_dlp,
                    runner=runner,
                    file_prefix="001-audio",
                )
                audio_source = "provider"
            except WatchVideoError as provider_error:
                raise WatchVideoError(
                    "Could not create persistent WAV from cached video "
                    f"({local_error}); provider audio fallback failed: {provider_error}",
                    status=provider_error.status,
                ) from provider_error

        target = cache.directory / AUDIO_NAME
        os.replace(extracted, target)

        previous_name = cache.manifest.get("audio")
        if isinstance(previous_name, str) and previous_name != target.name:
            previous = _child_file(cache.directory, previous_name)
            if previous is not None:
                try:
                    previous.unlink()
                except OSError:
                    pass

        manifest = dict(cache.manifest)
        manifest["audio"] = target.name
        manifest["audio_sha256"] = file_sha256(target)
        manifest["audio_size"] = target.stat().st_size
        manifest["audio_format"] = "wav"
        manifest["audio_source"] = audio_source
        manifest["audio_stored_at"] = time.time()
        atomic_write_json(cache.directory / MANIFEST_NAME, manifest)
        refreshed = VideoCache(cache.key, cache.directory, cache.video_path, manifest)
        if refreshed.audio_path is None:
            raise WatchVideoError("persistent audio cache read-back failed")
        return refreshed, True
    finally:
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging, ignore_errors=True)


def update_source(cache: VideoCache, source: Mapping[str, Any]) -> VideoCache | None:
    """Record safe resolved metadata without changing the cached media bytes."""

    if not isinstance(source, Mapping):
        return None
    manifest = dict(cache.manifest)
    manifest["source"] = {
        key_name: value for key_name, value in source.items()
        if key_name not in {"url", "available_formats", "available_subtitles"}
    }
    atomic_write_json(cache.directory / MANIFEST_NAME, manifest)
    return VideoCache(cache.key, cache.directory, cache.video_path, manifest)


def store_transcript(
    cache: VideoCache,
    payload: Mapping[str, Any],
    *,
    original_payload: Mapping[str, Any] | None = None,
    raw_path: Path | None = None,
) -> PersistentTranscript | None:
    """Persist normalized transcript evidence beside a verified video."""

    if not isinstance(payload, Mapping):
        return None
    atomic_write_json(cache.directory / TRANSCRIPT_NAME, dict(payload))
    original_path: Path | None = None
    if original_payload is not None:
        atomic_write_json(cache.directory / TRANSCRIPT_SOURCE_NAME, dict(original_payload))
        original_path = cache.directory / TRANSCRIPT_SOURCE_NAME
    else:
        stale_original = cache.directory / TRANSCRIPT_SOURCE_NAME
        if stale_original.is_file() and not stale_original.is_symlink():
            stale_original.unlink(missing_ok=True)
    if raw_path is not None:
        raw = Path(raw_path)
        raw_target = cache.directory / TRANSCRIPT_RAW_NAME
        if raw.is_file() and not raw.is_symlink() and raw.stat().st_size > 0:
            if raw.resolve() != raw_target.resolve():
                shutil.copy2(raw, raw_target)
    else:
        stale_raw = cache.directory / TRANSCRIPT_RAW_NAME
        if stale_raw.is_file() and not stale_raw.is_symlink():
            stale_raw.unlink(missing_ok=True)

    markdown_target = cache.directory / TRANSCRIPT_MARKDOWN_NAME
    # Derive the persistent presentation from the JSON just written. This
    # keeps the Markdown a presentation layer rather than a second transcript
    # supplied independently by a caller, and never inspects raw subtitle media.
    write_transcript_markdown(cache.directory / TRANSCRIPT_NAME, markdown_target)
    manifest = dict(cache.manifest)
    manifest["transcript"] = TRANSCRIPT_NAME
    manifest["transcript_markdown"] = TRANSCRIPT_MARKDOWN_NAME
    if original_path is not None:
        manifest["transcript_original"] = TRANSCRIPT_SOURCE_NAME
    else:
        manifest.pop("transcript_original", None)
    manifest["transcript_source_language"] = payload.get("source_language", payload.get("language"))
    manifest["transcript_output_language"] = payload.get("output_language", payload.get("language"))
    manifest["transcript_stored_at"] = time.time()
    atomic_write_json(cache.directory / MANIFEST_NAME, manifest)
    refreshed_cache = VideoCache(cache.key, cache.directory, cache.video_path, manifest)
    return refreshed_cache.read_transcript()


__all__ = [
    "MANIFEST_NAME",
    "MEDIA_CACHE_VERSION",
    "PersistentTranscript",
    "TRANSCRIPT_MARKDOWN_NAME",
    "TRANSCRIPT_NAME",
    "TRANSCRIPT_RAW_NAME",
    "TRANSCRIPT_SOURCE_NAME",
    "VIDEO_EXTENSIONS",
    "VIDEO_PREFIX",
    "AUDIO_NAME",
    "AUDIO_PREFIX",
    "VideoCache",
    "ensure_audio",
    "ensure_video",
    "load_video",
    "media_cache_base",
    "media_cache_key",
    "store_transcript",
    "update_source",
]
