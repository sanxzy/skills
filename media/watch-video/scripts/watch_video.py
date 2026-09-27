"""Orchestrate the watch-video extraction pipeline.

The command emits one JSON object. It reuses or persists one provider video
per normalized URL, obtains the least expensive trustworthy transcript
available from local/cache/provider sources, writes a compact timeline, and
preserves every limitation as a warning or stable status.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .artifacts import TaskRun, create_task_run
    from .cache import CacheHit, CacheStore
    from .common import (
        DEFAULT_FRAME_INTERVAL,
        WatchVideoError,
        atomic_append_jsonl,
        atomic_write_json,
        checked_text,
        checked_timeout,
        ensure_directory,
        intent_is_selective,
        intent_needs_visual,
        normalize_url,
        optional_float,
        owned_path,
        parse_time_range,
        parse_timestamp,
        read_json,
        safe_text,
        short_hash,
        WATCH_VIDEO_VERSION,
        workspace_root,
    )
    from .frame_sampler import sample_frames
    from .media_assets import (
        download_audio,
        extract_audio,
        probe_duration,
        remove_temporary_media,
    )
    from .media_cache import PersistentTranscript, VideoCache, ensure_audio, ensure_video, store_transcript, update_source
    from .resolve_media import normalize_metadata, resolve_media
    from .youtube_caption_fallback import acquire_youtube_subtitles, fetch_youtube_captions, is_youtube_url
    from .timeline import build_timeline, focus_ranges_from_matches, search_transcript
    from .transcribe_audio import asr_artifact, find_asr_tool, transcribe_audio
    from .translate_transcript import translate_segments
    from .transcript_markdown import write_transcript_markdown
    from .transcript import (
        SubtitleResult,
        TranscriptSegment,
        acquire_subtitles,
        segments_from_artifact,
        DEFAULT_MAX_SUBTITLE_ATTEMPTS,
    )
except ImportError:  # pragma: no cover - direct executable path
    from artifacts import TaskRun, create_task_run  # type: ignore
    from cache import CacheHit, CacheStore  # type: ignore
    from common import (  # type: ignore
        DEFAULT_FRAME_INTERVAL,
        WatchVideoError,
        atomic_append_jsonl,
        atomic_write_json,
        checked_text,
        checked_timeout,
        ensure_directory,
        intent_is_selective,
        intent_needs_visual,
        normalize_url,
        optional_float,
        owned_path,
        parse_time_range,
        parse_timestamp,
        read_json,
        safe_text,
        short_hash,
        WATCH_VIDEO_VERSION,
        workspace_root,
    )
    from frame_sampler import sample_frames  # type: ignore
    from media_assets import (  # type: ignore
        download_audio,
        extract_audio,
        probe_duration,
        remove_temporary_media,
    )
    from media_cache import PersistentTranscript, VideoCache, ensure_audio, ensure_video, store_transcript, update_source  # type: ignore
    from resolve_media import normalize_metadata, resolve_media  # type: ignore
    from youtube_caption_fallback import acquire_youtube_subtitles, fetch_youtube_captions, is_youtube_url  # type: ignore
    from timeline import build_timeline, focus_ranges_from_matches, search_transcript  # type: ignore
    from transcribe_audio import asr_artifact, find_asr_tool, transcribe_audio  # type: ignore
    from translate_transcript import translate_segments  # type: ignore
    from transcript_markdown import write_transcript_markdown  # type: ignore
    from transcript import (  # type: ignore
        SubtitleResult,
        TranscriptSegment,
        acquire_subtitles,
        segments_from_artifact,
        DEFAULT_MAX_SUBTITLE_ATTEMPTS,
    )


@dataclass(frozen=True)
class WatchConfig:
    url: str
    intent: str | None = None
    range_spec: str | None = None
    visual: str = "auto"
    cache: str = "auto"
    workspace: Path = field(default_factory=Path.cwd)
    # Test/integration seam; production defaults to ~/.local/videos.
    media_cache_root: Path | None = None
    frame_interval: float = DEFAULT_FRAME_INTERVAL
    max_subtitle_attempts: int = DEFAULT_MAX_SUBTITLE_ATTEMPTS
    preferred_languages: tuple[str, ...] = ()
    requested_timestamps: tuple[float, ...] = ()
    metadata_timeout: float = 120.0
    download_timeout: float = 1200.0
    asr_timeout: float = 1800.0
    cookies: str | None = None
    cookies_from_browser: str | None = None
    yt_dlp: str | None = None
    ffmpeg: str | None = None
    ffprobe: str | None = None
    asr_engine: str = "auto"
    asr_command: str | None = None
    asr_model: str | None = None
    translation_command: str | None = None
    translation_timeout: float = 900.0
    task_name: str | None = None
    # Backward-compatible alias; new runs use task_name.
    run_id: str | None = None
    keep_media: bool = False


def _unique(items: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _path_from_artifact(value: object) -> Path | None:
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _transcript_from_context(
    context: Mapping[str, Any],
    workspace: Path,
) -> list[dict[str, object]]:
    artifacts = context.get("artifacts")
    if not isinstance(artifacts, Mapping):
        return []
    path = _path_from_artifact(artifacts.get("transcript"))
    if path is None:
        return []
    if not path.is_absolute():
        path = workspace / path
    if not path.is_file():
        return []
    try:
        value = read_json(path)
    except WatchVideoError:
        return []
    segments = value.get("segments") if isinstance(value, Mapping) else None
    return [item for item in segments if isinstance(item, dict)] if isinstance(segments, list) else []


def _cache_hit_context(
    hit: CacheHit,
    *,
    run: TaskRun,
    normalized_url: str,
    intent: str | None,
    range_spec: str | None,
    visual: str,
    frame_interval: float,
    target_language: str | None = None,
) -> dict[str, object]:
    context = json.loads(json.dumps(hit.context, ensure_ascii=False))
    request: dict[str, object] = {
        "url": normalized_url,
        "visual": visual,
        "cache": "auto",
        "frame_interval": frame_interval,
        "task_name": run.task_name,
        "attempt": run.attempt_name,
    }
    if target_language:
        request["target_language"] = target_language
    request["transcript_policy"] = "best-effort"
    if intent:
        request["intent"] = intent
    if range_spec:
        source = context.get("source")
        duration = optional_float(source.get("duration")) if isinstance(source, Mapping) else None
        parsed_range = parse_time_range(range_spec, duration=duration)
        request["range"] = list(parsed_range) if parsed_range else range_spec
    context["request"] = request
    context["extraction_status"] = context.get("extraction_status", context.get("status", "partial"))
    retrieval: dict[str, object] = {}
    transcript = _transcript_from_context(context, run.workspace)
    source = context.get("source")
    duration = optional_float(source.get("duration")) if isinstance(source, Mapping) else None
    if intent and intent_is_selective(intent) and transcript:
        matches = search_transcript(transcript, intent, duration=duration)
        retrieval["query"] = intent
        retrieval["matches"] = list(matches)
        if duration and matches:
            retrieval["focus_ranges"] = [list(item) for item in focus_ranges_from_matches(matches, duration=duration)]
    if range_spec:
        retrieval["requested_range"] = request.get("range", range_spec)
    if retrieval:
        context["retrieval"] = retrieval
    artifacts = context.get("artifacts")
    if isinstance(artifacts, dict):
        artifacts["task_directory"] = run.display(run.task_directory)
        artifacts["attempt_directory"] = run.display(run.attempt_directory)
        artifacts["run_directory"] = run.display(run.attempt_directory)
        artifacts["context"] = run.display(run.context_path)
        artifacts["state"] = run.display(run.state_path)
        artifacts["progress"] = run.display(run.events_path)
        artifacts["cache_directory"] = run.display(hit.directory)
    context["cache"] = {"hit": True, "key": hit.key, "directory": run.display(hit.directory)}
    return context


class _RunJournal:
    """Persist initialization and append-only stage observations."""

    def __init__(self, run: TaskRun, request: Mapping[str, object]) -> None:
        self.run = run
        self.state_path = run.state_path
        self.events_path = run.events_path
        self.state: dict[str, object] = {
            "version": 1,
            "status": "running",
            "started_at": time.time(),
            "request": dict(request),
            "task_name": run.task_name,
            "attempt": run.attempt_name,
            "completed_steps": [],
        }
        atomic_write_json(self.state_path, self.state)
        atomic_append_jsonl(self.events_path, {"event": "run_initialized", "at": time.time()})

    def record(self, step: str, status: str, **details: object) -> None:
        completed = self.state.get("completed_steps")
        if not isinstance(completed, list):
            completed = []
            self.state["completed_steps"] = completed
        if status in {"complete", "skipped"} and step not in completed:
            completed.append(step)
        self.state["last_step"] = step
        self.state["last_status"] = status
        atomic_append_jsonl(self.events_path, {"event": step, "status": status, "at": time.time(), **details})
        atomic_write_json(self.state_path, self.state)

    def finish(self, status: str) -> None:
        self.state["status"] = status
        self.state["finished_at"] = time.time()
        atomic_append_jsonl(self.events_path, {"event": "run_finished", "status": status, "at": time.time()})
        atomic_write_json(self.state_path, self.state)


def _prepare_run(workspace: Path, normalized_url: str, config: WatchConfig) -> tuple[TaskRun, _RunJournal]:
    requested_name = config.task_name or config.run_id
    run = create_task_run(
        workspace,
        normalized_url,
        intent=config.intent,
        task_name=requested_name,
    )
    request: dict[str, object] = {
        "url": normalized_url,
        "visual": config.visual,
        "cache": config.cache,
        "frame_interval": config.frame_interval,
        "task_name": run.task_name,
        "attempt": run.attempt_name,
        "transcript_policy": "best-effort",
    }
    if _target_language(config):
        request["target_language"] = _target_language(config)
    if config.intent:
        request["intent"] = config.intent
    if config.range_spec:
        request["range"] = config.range_spec
    journal = _RunJournal(run, request)
    return run, journal


def _write_metadata(path: Path, source: Mapping[str, object]) -> Path:
    atomic_write_json(path, dict(source))
    return path


def _write_transcript(path: Path, payload: Mapping[str, object]) -> Path:
    atomic_write_json(path, dict(payload))
    return path


def _write_timeline(path: Path, timeline: Sequence[Mapping[str, object]]) -> Path:
    atomic_write_json(path, {"segments": list(timeline)})
    return path


def _failure_context(
    normalized_url: str,
    config: WatchConfig,
    run: TaskRun,
    journal: _RunJournal,
    *,
    status: str,
    error: str,
    warnings: Sequence[str] = (),
    media_cache: VideoCache | None = None,
) -> dict[str, object]:
    all_warnings = _unique(list(warnings))
    context: dict[str, object] = {
        "status": status,
        "extraction_status": status,
        "request": {
            "url": normalized_url,
            "visual": config.visual,
            "cache": config.cache,
            "frame_interval": config.frame_interval,
            "task_name": run.task_name,
            "attempt": run.attempt_name,
            "transcript_policy": "best-effort",
            **({"target_language": _target_language(config)} if _target_language(config) else {}),
            **({"intent": config.intent} if config.intent else {}),
            **({"range": config.range_spec} if config.range_spec else {}),
        },
        "source": {"url": normalized_url},
        "content": {
            "transcript_available": False,
            "audio_available": bool(media_cache is not None and media_cache.audio_path is not None),
            "visual_sampling_performed": False,
            "transcript_policy": "best-effort",
            "transcript_translation_performed": False,
            "visual_transcript_alignment": {
                "status": "unavailable",
                "frames_total": 0,
                "frames_with_nearby_speech": 0,
            },
        },
        "timeline": [],
        "artifacts": {
            "task_directory": run.display(run.task_directory),
            "attempt_directory": run.display(run.attempt_directory),
            "run_directory": run.display(run.attempt_directory),
            "context": run.display(run.context_path),
            "state": run.display(journal.state_path),
            "progress": run.display(journal.events_path),
            **({"media_cache": media_cache.display_path} if media_cache is not None else {}),
        },
        "warnings": all_warnings,
        "errors": [error],
        "analysis": {"status": "not_run"},
    }
    if media_cache is not None:
        audio_display_path = media_cache.audio_display_path
        if audio_display_path is not None:
            context["artifacts"]["audio"] = audio_display_path
    atomic_write_json(run.context_path, context)
    journal.finish(status)
    return read_json(run.context_path)


def _duration_from_evidence(
    source: Mapping[str, object],
    transcript: Sequence[TranscriptSegment],
    chapters: Sequence[Mapping[str, object]],
) -> float | None:
    duration = optional_float(source.get("duration"))
    if duration is not None and duration > 0:
        return duration
    values: list[float] = []
    for segment in transcript:
        values.append(segment.end)
    for chapter in chapters:
        value = optional_float(chapter.get("end"))
        if value is not None:
            values.append(value)
    return max(values) if values else None


def _parse_requested_timestamps(values: Sequence[object]) -> tuple[float, ...]:
    return tuple(parse_timestamp(value, "requested timestamp") for value in values)


def _effective_range(config: WatchConfig, duration: float | None) -> tuple[float, float] | None:
    if config.range_spec is None:
        return None
    return parse_time_range(config.range_spec, duration=duration)


def _cache_profile(config: WatchConfig) -> str:
    """Describe extraction-affecting options without storing command secrets."""

    languages = tuple(
        item.casefold().replace("_", "-").strip()
        for item in config.preferred_languages
        if isinstance(item, str) and item.strip()
    )
    return json.dumps(
        {
            "skill": WATCH_VIDEO_VERSION,
            "transcript_policy": "best-effort",
            "frame_interval": float(config.frame_interval),
            "languages": languages,
            "max_subtitle_attempts": config.max_subtitle_attempts,
            "asr_engine": config.asr_engine,
            "asr_model": config.asr_model or "",
            "asr_adapter": short_hash(config.asr_command) if config.asr_command else "",
            "translation_adapter": short_hash(config.translation_command) if config.translation_command else "",
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _language_matches(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    left_key = left.casefold().replace("_", "-").strip()
    right_key = right.casefold().replace("_", "-").strip()
    return left_key == right_key or left_key.split("-", 1)[0] == right_key.split("-", 1)[0]


def _target_language(config: WatchConfig) -> str | None:
    for value in config.preferred_languages:
        if isinstance(value, str) and value.strip():
            return value.strip().split(",", 1)[0]
    return None


def _transcript_payload(
    segments: Sequence[TranscriptSegment],
    quality: Mapping[str, object] | None,
    *,
    source: str,
    source_language: str | None,
    output_language: str | None,
    translation_performed: bool = False,
    translation_provenance: Mapping[str, object] | str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "source": source,
        "source_language": source_language,
        "output_language": output_language,
        "translation_performed": translation_performed,
        "quality": dict(quality) if isinstance(quality, Mapping) else None,
        "segments": [segment.as_dict() for segment in segments],
    }
    if output_language:
        payload["language"] = output_language
    if translation_performed:
        if isinstance(translation_provenance, Mapping):
            payload["translation_provenance"] = dict(translation_provenance)
        elif isinstance(translation_provenance, str) and translation_provenance.strip():
            payload["translation_provenance"] = translation_provenance.strip()
        else:
            payload["translation_provenance"] = "explicit adapter"
    return payload


def _source_from_media_manifest(
    media_cache: VideoCache,
    normalized_url: str,
) -> tuple[dict[str, object], dict[str, object]] | None:
    value = media_cache.manifest.get("source")
    if not isinstance(value, Mapping):
        return None
    source = dict(value)
    source["url"] = normalized_url
    info: dict[str, object] = {
        key: source[key]
        for key in ("duration", "chapters", "language")
        if key in source
    }
    return source, info


def _cached_transcript_candidate(
    persistent: PersistentTranscript,
    target_language: str | None,
) -> tuple[
    tuple[TranscriptSegment, ...],
    str | None,
    str | None,
    str | None,
    Mapping[str, object] | None,
    Path | None,
]:
    """Select cached source/target text without treating it as trusted prose."""

    payload = persistent.payload
    original = persistent.original_payload
    output_language = payload.get("output_language", payload.get("language"))
    output_language = output_language if isinstance(output_language, str) else None
    source_language = payload.get("source_language", output_language)
    source_language = source_language if isinstance(source_language, str) else None
    selected_payload: Mapping[str, object] = payload
    if target_language and not _language_matches(output_language, target_language):
        if original is not None and segments_from_artifact(original):
            selected_payload = original
            source_language_value = original.get("output_language", original.get("language", source_language))
            source_language = source_language_value if isinstance(source_language_value, str) else source_language
    segments = segments_from_artifact(selected_payload)
    if not segments:
        return (), None, None, None, None, None
    # The current attempt reuses a persistent artifact; preserve detailed
    # source-language provenance separately rather than labeling cached text as
    # a fresh provider acquisition.
    source_name = "cached"
    selected_quality = selected_payload.get("quality")
    quality = selected_quality if isinstance(selected_quality, Mapping) else None
    selected_output = selected_payload.get("output_language", selected_payload.get("language", source_language))
    selected_output = selected_output if isinstance(selected_output, str) else source_language
    if target_language and _language_matches(selected_output, target_language):
        selected_output = target_language
    return (
        segments,
        source_name,
        source_language,
        selected_output,
        quality,
        persistent.raw_path,
    )


def _cleanup_failed_run(run: TaskRun, config: WatchConfig, warnings: list[str]) -> None:
    process_directory = run.process_directory
    if config.keep_media:
        warnings.append(
            "temporary media was retained by explicit request: "
            + run.display(process_directory)
        )
        return
    remove_temporary_media(process_directory, keep=False)
    remaining = [
        str(path.relative_to(process_directory))
        for path in process_directory.rglob("*")
        if path.is_file() and not path.is_symlink()
    ]
    if remaining:
        warnings.append(
            "temporary media cleanup left files in place: "
            + ", ".join(sorted(remaining))
        )


def run_watch(config: WatchConfig, *, runner=None) -> dict[str, object]:
    """Run the complete extraction flow and return the read-back context."""

    normalized_url = normalize_url(config.url)
    if config.visual not in {"auto", "never", "always"}:
        raise WatchVideoError("visual mode must be auto, never, or always")
    if config.cache not in {"auto", "refresh", "off"}:
        raise WatchVideoError("cache mode must be auto, refresh, or off")
    if isinstance(config.frame_interval, bool) or not isinstance(config.frame_interval, (int, float)):
        raise WatchVideoError("frame_interval must be a finite positive number")
    if not math.isfinite(float(config.frame_interval)) or float(config.frame_interval) <= 0:
        raise WatchVideoError("frame_interval must be a finite positive number")
    if type(config.max_subtitle_attempts) is not int or not 1 <= config.max_subtitle_attempts <= 24:
        raise WatchVideoError("max_subtitle_attempts must be an integer between 1 and 24")
    if config.intent is not None:
        checked_text(config.intent, "intent", max_length=8192)
    workspace = workspace_root(config.workspace)
    run, journal = _prepare_run(workspace, normalized_url, config)
    warnings: list[str] = []
    try:
        needs_visual = config.visual == "always" or (
            config.visual == "auto" and intent_needs_visual(config.intent)
        )
        cache_profile = _cache_profile(config)
        persistent_video: VideoCache | None = None
        media_tool: str | None = None
        try:
            persistent_video, downloaded, media_tool = ensure_video(
                normalized_url,
                root=config.media_cache_root,
                refresh=config.cache == "refresh",
                timeout=config.download_timeout,
                cookies=config.cookies,
                cookies_from_browser=config.cookies_from_browser,
                yt_dlp=config.yt_dlp,
                runner=runner,
            )
            if media_tool == "cache-fallback":
                warnings.append(
                    "video refresh was unavailable; the previous verified local video was retained"
                )
            journal.record(
                "media_cache",
                "downloaded" if downloaded else "hit",
                cache_path=persistent_video.display_path,
                tool=media_tool,
            )
        except WatchVideoError as exc:
            warnings.append(f"persistent video cache unavailable: {exc}")
            journal.record("media_cache", "unavailable")
        if persistent_video is not None:
            try:
                refreshed_video, audio_created = ensure_audio(
                    persistent_video,
                    url=normalized_url,
                    ffmpeg=config.ffmpeg,
                    timeout=min(config.asr_timeout, 600.0),
                    cookies=config.cookies,
                    cookies_from_browser=config.cookies_from_browser,
                    yt_dlp=config.yt_dlp,
                    runner=runner,
                )
                persistent_video = refreshed_video
                journal.record(
                    "audio_cache",
                    "created" if audio_created else "hit",
                    cache_path=persistent_video.audio_display_path,
                )
            except WatchVideoError as exc:
                warnings.append(f"persistent WAV audio cache unavailable: {exc}")
                journal.record("audio_cache", "unavailable")
        cache_store = (
            CacheStore(workspace, task_directory=run.task_directory)
            if config.cache != "off" else None
        )
        if cache_store is not None and config.cache == "auto":
            cache_requires_fresh_visual_scope = needs_visual and (
                config.range_spec is not None
                or bool(config.intent and intent_is_selective(config.intent))
            )
            cached = None if cache_requires_fresh_visual_scope else cache_store.lookup(
                normalized_url,
                needs_visual=needs_visual,
                profile=cache_profile,
            )
            if cached is not None:
                context = _cache_hit_context(
                    cached,
                    run=run,
                    normalized_url=normalized_url,
                    intent=config.intent,
                    range_spec=config.range_spec,
                    visual=config.visual,
                    frame_interval=config.frame_interval,
                    target_language=_target_language(config),
                )
                if persistent_video is not None:
                    context.setdefault("artifacts", {})["media_cache"] = persistent_video.display_path
                    audio_display_path = persistent_video.audio_display_path
                    if audio_display_path is not None:
                        context["artifacts"]["audio"] = audio_display_path
                    cached_content = context.get("content")
                    if isinstance(cached_content, dict):
                        cached_content["audio_available"] = audio_display_path is not None
                context["warnings"] = _unique(
                    list(context.get("warnings", [])) + warnings
                )
                atomic_write_json(run.context_path, context)
                journal.record("cache_lookup", "complete", hit=True)
                journal.record("context", "complete", final_status=str(context.get("status", "complete")))
                journal.finish(str(context.get("status", "complete")))
                return read_json(run.context_path)
        journal.record("cache_lookup", "skipped" if cache_store is None else "complete", hit=False)

        resolved_info: Mapping[str, object]
        resolved_tool: str
        direct_youtube = None
        local_source = (
            _source_from_media_manifest(persistent_video, normalized_url)
            if persistent_video is not None and (
                config.cache != "refresh" or media_tool == "cache-fallback"
            )
            else None
        )
        if local_source is not None:
            source, resolved_info = local_source
            resolved_tool = "persistent local video manifest"
            warnings.append("provider metadata was reused from the persistent local video cache")
            journal.record("metadata", "cached", tool=resolved_tool)
        else:
            try:
                resolved = resolve_media(
                    normalized_url,
                    timeout=config.metadata_timeout,
                    cookies=config.cookies,
                    cookies_from_browser=config.cookies_from_browser,
                    yt_dlp=config.yt_dlp,
                    runner=runner,
                )
            except WatchVideoError as exc:
                # A provider-specific yt-dlp failure need not mean that the
                # public YouTube player has no timestamped caption track.
                # Do not use this path to bypass explicit authentication or
                # an invalid local tool configuration.
                if is_youtube_url(normalized_url) and exc.status == "source_unavailable":
                    try:
                        direct_youtube = fetch_youtube_captions(
                            normalized_url,
                            timeout=config.metadata_timeout,
                            preferred_language=_target_language(config),
                            cookies=config.cookies,
                            cookies_from_browser=config.cookies_from_browser,
                        )
                    except WatchVideoError as fallback_error:
                        if fallback_error.status == "authentication_required":
                            return _failure_context(
                                normalized_url, config, run, journal,
                                status=fallback_error.status, error=str(fallback_error),
                                warnings=warnings, media_cache=persistent_video,
                            )
                        warnings.append(f"direct YouTube caption fallback unavailable: {fallback_error}")
                if direct_youtube is None:
                    return _failure_context(
                        normalized_url,
                        config,
                        run,
                        journal,
                        status=exc.status,
                        error=str(exc),
                        warnings=warnings,
                        media_cache=persistent_video,
                    )
                resolved_info = direct_youtube.info
                source = normalize_metadata(resolved_info, normalized_url)
                resolved_tool = "YouTube player caption fallback"
                warnings.append("yt-dlp metadata unavailable; safe metadata was recovered from the YouTube player")
            else:
                source = dict(resolved.source)
                resolved_info = resolved.info
                resolved_tool = resolved.tool
            if persistent_video is not None:
                try:
                    refreshed_media_cache = update_source(persistent_video, source)
                    if refreshed_media_cache is not None:
                        persistent_video = refreshed_media_cache
                except WatchVideoError as exc:
                    warnings.append(f"persistent media metadata update unavailable: {exc}")
            journal.record("metadata", "complete", tool=resolved_tool)
        metadata_path = _write_metadata(run.metadata_path, source)

        transcript_segments: tuple[TranscriptSegment, ...] = ()
        transcript_source: str | None = None
        transcript_source_language: str | None = None
        transcript_output_language: str | None = None
        transcript_quality: Mapping[str, object] | None = None
        transcript_path: Path | None = None
        transcript_markdown_path: Path | None = None
        transcript_original_path: Path | None = None
        transcript_original_payload: Mapping[str, object] | None = None
        transcript_raw_path: Path | None = None
        transcript_translation_performed = False
        target_language = _target_language(config)

        if persistent_video is not None:
            persistent_transcript = persistent_video.read_transcript()
            if persistent_transcript is not None:
                candidate = _cached_transcript_candidate(persistent_transcript, target_language)
                (
                    transcript_segments,
                    transcript_source,
                    transcript_source_language,
                    transcript_output_language,
                    transcript_quality,
                    transcript_raw_path,
                ) = candidate
                cached_payload = persistent_transcript.payload
                cached_output_language = cached_payload.get(
                    "output_language", cached_payload.get("language")
                )
                cached_matches_target = (
                    target_language is None
                    or _language_matches(
                        cached_output_language if isinstance(cached_output_language, str) else None,
                        target_language,
                    )
                )
                if transcript_segments:
                    transcript_translation_performed = (
                        cached_payload.get("translation_performed") is True
                        and cached_matches_target
                    )
                    if transcript_translation_performed:
                        transcript_original_payload = persistent_transcript.original_payload
                    warnings.append(
                        "reused the verified transcript from the persistent local video cache"
                    )
                    if isinstance(transcript_quality, Mapping) and transcript_quality.get("confidence") == "low-best-effort":
                        warnings.append("reused transcript is low-confidence best effort after strict quality rejection")
                    journal.record("transcript_cache", "hit")

        subtitle: SubtitleResult | None = None
        if not transcript_segments and direct_youtube is None:
            try:
                subtitle = acquire_subtitles(
                    normalized_url,
                    resolved_info,
                    run.process_directory / "001-subtitles",
                    preferred_languages=config.preferred_languages,
                    max_attempts=config.max_subtitle_attempts,
                    timeout=min(config.download_timeout, 300.0),
                    cookies=config.cookies,
                    cookies_from_browser=config.cookies_from_browser,
                    yt_dlp=config.yt_dlp,
                    runner=runner,
                )
            except WatchVideoError as exc:
                warnings.append(f"subtitle acquisition unavailable: {exc}")
        if isinstance(subtitle, SubtitleResult):
            warnings.extend(subtitle.warnings)
            if subtitle.status in {"usable", "best_effort"} and subtitle.quality is not None:
                transcript_segments = subtitle.segments
                transcript_source = subtitle.choice.source if subtitle.choice else "subtitle"
                transcript_source_language = subtitle.choice.language if subtitle.choice else None
                transcript_output_language = transcript_source_language
                transcript_quality = subtitle.quality.as_dict()
                transcript_raw_path = subtitle.path
                if subtitle.status == "best_effort":
                    warnings.append(
                        "transcript uses always-on best-effort caption cleaning; strict quality metrics remain in the artifact"
                    )
                journal.record(
                    "transcript",
                    "complete",
                    source=transcript_source,
                    quality=subtitle.status,
                    attempts=subtitle.attempted,
                )
            else:
                journal.record("subtitle", subtitle.status)

        if not transcript_segments and is_youtube_url(normalized_url):
            try:
                if direct_youtube is None:
                    direct_youtube = fetch_youtube_captions(
                        normalized_url,
                        timeout=config.metadata_timeout,
                        preferred_language=target_language,
                        cookies=config.cookies,
                        cookies_from_browser=config.cookies_from_browser,
                    )
                fallback_subtitle = acquire_youtube_subtitles(
                    direct_youtube,
                    run.process_directory / "001-subtitles" / "007-direct-youtube",
                    preferred_languages=config.preferred_languages,
                    max_attempts=config.max_subtitle_attempts,
                    timeout=min(config.download_timeout, 300.0),
                    cookies=config.cookies,
                )
                warnings.extend(fallback_subtitle.warnings)
                if fallback_subtitle.status in {"usable", "best_effort"} and fallback_subtitle.quality is not None:
                    transcript_segments = fallback_subtitle.segments
                    transcript_source = fallback_subtitle.choice.source if fallback_subtitle.choice else "automatic"
                    transcript_source_language = fallback_subtitle.choice.language if fallback_subtitle.choice else None
                    transcript_output_language = transcript_source_language
                    transcript_quality = fallback_subtitle.quality.as_dict()
                    transcript_raw_path = fallback_subtitle.path
                    journal.record(
                        "transcript", "complete", source=transcript_source,
                        adapter="direct_youtube_caption", quality=fallback_subtitle.status,
                        attempts=fallback_subtitle.attempted,
                    )
                else:
                    journal.record("youtube_caption_fallback", fallback_subtitle.status)
            except WatchVideoError as exc:
                warnings.append(f"direct YouTube caption fallback unavailable: {exc}")
                journal.record("youtube_caption_fallback", "unavailable")

        if not transcript_segments:
            asr_available = config.asr_command is not None
            if not asr_available:
                try:
                    asr_available = find_asr_tool(config.asr_engine) is not None
                except WatchVideoError as exc:
                    warnings.append(f"ASR capability check failed: {exc}")
            if not asr_available:
                warnings.append("audio fallback skipped because no ASR capability is available")
                journal.record("asr", "unavailable")
            else:
                audio_path: Path | None = None
                try:
                    cached_audio = persistent_video.audio_path if persistent_video is not None else None
                    if cached_audio is not None:
                        audio_path = cached_audio
                        journal.record("audio", "cached", source="persistent_audio")
                    elif persistent_video is not None:
                        audio_path = extract_audio(
                            persistent_video.video_path,
                            run.process_directory / "002-audio" / "001-audio.wav",
                            ffmpeg=config.ffmpeg,
                            timeout=min(config.asr_timeout, 600.0),
                            runner=runner,
                        )
                        journal.record("audio", "complete", source="persistent_video")
                    else:
                        audio_path, _, _ = download_audio(
                            normalized_url,
                            run.process_directory / "002-audio",
                            timeout=config.download_timeout,
                            cookies=config.cookies,
                            cookies_from_browser=config.cookies_from_browser,
                            yt_dlp=config.yt_dlp,
                            runner=runner,
                            file_prefix="001-audio",
                        )
                        journal.record("audio", "complete", source="provider")
                except WatchVideoError as exc:
                    warnings.append(f"audio fallback unavailable: {exc}")
                    journal.record("audio", "unavailable")
                if audio_path is not None:
                    try:
                        asr = transcribe_audio(
                            audio_path,
                            run.process_directory / "003-asr",
                            engine=config.asr_engine,
                            command_template=config.asr_command,
                            model=config.asr_model,
                            language=target_language,
                            timeout=config.asr_timeout,
                            runner=runner,
                        )
                        warnings.extend(asr.warnings)
                        if asr.status in {"usable", "best_effort"} and asr.quality is not None:
                            transcript_segments = asr.segments
                            transcript_source = "asr"
                            transcript_source_language = target_language
                            transcript_output_language = target_language
                            transcript_quality = asr.quality.as_dict()
                            if asr.status == "best_effort":
                                warnings.append("ASR transcript is low-confidence best effort after strict quality rejection")
                            journal.record("transcript", "complete", source="asr", quality=asr.status)
                        else:
                            journal.record("asr", asr.status)
                    except WatchVideoError as exc:
                        warnings.append(f"ASR fallback unavailable: {exc}")
                        journal.record("asr", "unavailable")

        if transcript_segments:
            if transcript_output_language is None:
                transcript_output_language = transcript_source_language
            if (
                target_language
                and transcript_output_language
                and not _language_matches(transcript_output_language, target_language)
            ):
                translation = translate_segments(
                    transcript_segments,
                    source_language=transcript_output_language,
                    target_language=target_language,
                    destination=run.process_directory / "005-translation",
                    command_template=config.translation_command,
                    timeout=config.translation_timeout,
                    runner=runner,
                )
                warnings.extend(translation.warnings)
                if translation.status == "usable":
                    transcript_original_payload = _transcript_payload(
                        transcript_segments,
                        transcript_quality,
                        source=transcript_source or "transcript",
                        source_language=transcript_source_language or transcript_output_language,
                        output_language=transcript_output_language,
                    )
                    atomic_write_json(run.transcript_source_path, transcript_original_payload)
                    transcript_original_path = run.transcript_source_path
                    transcript_segments = translation.segments
                    transcript_output_language = target_language
                    transcript_translation_performed = True
                    journal.record("translation", "complete", chunks=translation.chunks)
                else:
                    journal.record("translation", translation.status)

            if transcript_translation_performed and transcript_original_payload is not None and transcript_original_path is None:
                atomic_write_json(run.transcript_source_path, transcript_original_payload)
                transcript_original_path = run.transcript_source_path
            translation_provenance: Mapping[str, object] | None = None
            if transcript_translation_performed:
                original_source = (
                    transcript_original_payload.get("source")
                    if isinstance(transcript_original_payload, Mapping)
                    and isinstance(transcript_original_payload.get("source"), str)
                    else transcript_source or "transcript"
                )
                translation_provenance = {
                    "method": "explicit adapter",
                    "source": original_source,
                }
            selected_payload = _transcript_payload(
                transcript_segments,
                transcript_quality,
                source="translated" if transcript_translation_performed else (transcript_source or "transcript"),
                source_language=transcript_source_language,
                output_language=transcript_output_language,
                translation_performed=transcript_translation_performed,
                translation_provenance=translation_provenance,
            )
            transcript_path = _write_transcript(run.transcript_path, selected_payload)
            transcript_markdown_path = write_transcript_markdown(
                transcript_path,
                run.transcript_markdown_path,
            )
            journal.record(
                "transcript_markdown",
                "complete",
                path=run.display(transcript_markdown_path),
            )
            if persistent_video is not None:
                try:
                    stored_transcript = store_transcript(
                        persistent_video,
                        selected_payload,
                        original_payload=transcript_original_payload,
                        raw_path=transcript_raw_path,
                    )
                    if stored_transcript is None:
                        warnings.append("persistent transcript cache did not pass read-back validation")
                    else:
                        journal.record("transcript_cache", "stored")
                except WatchVideoError as exc:
                    warnings.append(f"persistent transcript cache write unavailable: {exc}")
        else:
            warnings.append("no usable timestamped transcript was obtained")
            journal.record("transcript", "unavailable")

        chapters = source.get("chapters") if isinstance(source.get("chapters"), list) else []
        chapters = [item for item in chapters if isinstance(item, dict)]
        duration = _duration_from_evidence(source, transcript_segments, chapters)
        requested_range = _effective_range(config, duration) if config.range_spec else None
        matches: tuple[dict[str, object], ...] = ()
        focus_ranges: tuple[tuple[float, float], ...] = ()
        if config.intent and intent_is_selective(config.intent) and transcript_segments:
            matches = search_transcript(
                [segment.as_dict() for segment in transcript_segments],
                config.intent,
                duration=duration,
            )
            if duration and matches:
                focus_ranges = focus_ranges_from_matches(matches, duration=duration)
            if not matches:
                warnings.append("selective intent did not match the available transcript; no focused range was established")
        if requested_range is not None:
            focus_ranges = (requested_range,)

        frame_records: list[dict[str, object]] = []
        visual_alignment: dict[str, object] = {
            "status": "not_requested" if not needs_visual else "unavailable",
            "frames_total": 0,
            "frames_with_nearby_speech": 0,
        }
        if needs_visual:
            video_path = persistent_video.video_path if persistent_video is not None else None
            if video_path is None:
                warnings.append("visual media unavailable because the persistent local video cache has no verified video")
                journal.record("video", "unavailable")
            else:
                journal.record("video", "complete", source="persistent_cache")
                if duration is None:
                    try:
                        duration = probe_duration(video_path, ffprobe=config.ffprobe, timeout=60.0, runner=runner)
                    except WatchVideoError as exc:
                        warnings.append(f"video duration probe unavailable: {exc}")
                if duration and duration > 0 and config.range_spec:
                    requested_range = _effective_range(config, duration)
                    focus_ranges = (requested_range,) if requested_range else focus_ranges
                if duration and duration > 0:
                    if "duration" not in source:
                        source["duration"] = duration
                        metadata_path = _write_metadata(run.metadata_path, source)
                    try:
                        sampled = sample_frames(
                            video_path,
                            run.frames_directory,
                            duration,
                            transcript=[segment.as_dict() for segment in transcript_segments],
                            requested_times=config.requested_timestamps,
                            focus_ranges=focus_ranges or None,
                            frame_interval=config.frame_interval,
                            ffmpeg=config.ffmpeg,
                            timeout=min(config.download_timeout, 600.0),
                            runner=runner,
                        )
                        frame_records = [
                            {
                                **item,
                                "path": run.display(Path(item["path"])),
                            }
                            for item in sampled.frames
                        ]
                        warnings.extend(sampled.warnings)
                        visual_alignment = {
                            "status": sampled.alignment_status,
                            "frames_total": len(frame_records),
                            "frames_with_nearby_speech": sampled.aligned_frames,
                        }
                        journal.record(
                            "frames",
                            "complete" if frame_records else "partial",
                            count=len(frame_records),
                        )
                        journal.record(
                            "alignment",
                            sampled.alignment_status,
                            **{
                                key: value for key, value in visual_alignment.items()
                                if key != "status"
                            },
                        )
                    except WatchVideoError as exc:
                        warnings.append(f"visual sampling unavailable: {exc}")
                        journal.record("frames", "unavailable")
                else:
                    warnings.append("visual sampling skipped because video duration is unavailable")
                    journal.record("frames", "unavailable")
        else:
            journal.record("frames", "skipped")

        if duration is None:
            warnings.append("timeline unavailable because no positive duration was established")
            timeline_records: list[dict[str, object]] = []
        else:
            timeline_records = [
                item.as_dict()
                for item in build_timeline(
                    duration,
                    transcript=[segment.as_dict() for segment in transcript_segments],
                    chapters=chapters,
                    frames=frame_records,
                )
            ]
        timeline_path = _write_timeline(run.timeline_path, timeline_records)
        journal.record("timeline", "complete" if timeline_records else "partial", segments=len(timeline_records))

        artifacts: dict[str, object] = {
            "task_directory": run.display(run.task_directory),
            "attempt_directory": run.display(run.attempt_directory),
            "run_directory": run.display(run.attempt_directory),
            "context": run.display(run.context_path),
            "metadata": run.display(metadata_path),
            "timeline": run.display(timeline_path),
            "state": run.display(journal.state_path),
            "progress": run.display(journal.events_path),
        }
        if persistent_video is not None:
            artifacts["media_cache"] = persistent_video.display_path
            audio_display_path = persistent_video.audio_display_path
            if audio_display_path is not None:
                artifacts["audio"] = audio_display_path
        if transcript_path is not None:
            artifacts["transcript"] = run.display(transcript_path)
        if transcript_markdown_path is not None:
            artifacts["transcript_markdown"] = run.display(transcript_markdown_path)
        if transcript_original_path is not None:
            artifacts["transcript_original"] = run.display(transcript_original_path)
        if transcript_translation_performed and transcript_path is not None:
            artifacts["transcript_target"] = run.display(transcript_path)
        if frame_records:
            artifacts["frames"] = frame_records
        content: dict[str, object] = {
            "transcript_available": bool(transcript_segments),
            "audio_available": bool(persistent_video is not None and persistent_video.audio_path is not None),
            "visual_sampling_performed": bool(frame_records),
            "visual_analysis_required": bool(needs_visual),
            "visual_transcript_alignment": visual_alignment,
            "transcript_policy": "best-effort",
        }
        if transcript_source:
            content["transcript_source"] = transcript_source
        if transcript_quality is not None:
            content["transcript_quality"] = transcript_quality.get("confidence", "unknown")
            content["transcript_quality_metrics"] = dict(transcript_quality)
        if transcript_source_language:
            content["transcript_source_language"] = transcript_source_language
        if transcript_output_language:
            content["transcript_output_language"] = transcript_output_language
            content["language"] = transcript_output_language
        content["transcript_translation_performed"] = transcript_translation_performed
        request: dict[str, object] = {
            "url": normalized_url,
            "visual": config.visual,
            "cache": config.cache,
            "frame_interval": config.frame_interval,
            "task_name": run.task_name,
            "attempt": run.attempt_name,
            "transcript_policy": "best-effort",
        }
        if target_language:
            request["target_language"] = target_language
        if config.intent:
            request["intent"] = config.intent
        if config.range_spec:
            request["range"] = list(requested_range) if requested_range else config.range_spec
        retrieval: dict[str, object] = {}
        if config.intent and intent_is_selective(config.intent):
            retrieval["query"] = config.intent
            retrieval["matches"] = list(matches)
            if focus_ranges:
                retrieval["focus_ranges"] = [list(item) for item in focus_ranges]
        elif requested_range:
            retrieval["requested_range"] = list(requested_range)
        has_channel = bool(transcript_segments or frame_records)
        visual_requirement_met = not needs_visual or bool(frame_records)
        status = "complete" if has_channel and visual_requirement_met else "partial"
        context = {
            "status": status,
            "extraction_status": status,
            "request": request,
            "source": source,
            "content": content,
            "analysis": {"status": "pending_agent_synthesis"},
            "timeline": timeline_records,
            "artifacts": artifacts,
            "warnings": _unique(warnings),
        }
        if retrieval:
            context["retrieval"] = retrieval
        context_path = run.context_path
        atomic_write_json(context_path, context)
        journal.record("context", "complete", final_status=status)
        if cache_store is not None:
            stored = cache_store.store(
                normalized_url,
                source,
                run.attempt_directory,
                artifact_files={
                    "context": run.context_path,
                    "metadata": run.metadata_path,
                    "timeline": run.timeline_path,
                    "transcript": run.transcript_path,
                    "transcript_markdown": run.transcript_markdown_path,
                    "frames": run.frames_directory,
                    "transcript_original": run.transcript_source_path,
                },
                profile=cache_profile,
            ) if config.cache in {"auto", "refresh"} else None
            cache_payload: dict[str, object] = {"hit": False, "stored": stored is not None}
            if stored is not None:
                cache_payload["key"] = stored.key
                cache_payload["directory"] = run.display(stored.directory)
            elif cache_store.last_error:
                warnings.append(f"semantic cache publication failed: {cache_store.last_error}")
            context["cache"] = cache_payload
            context["warnings"] = _unique(warnings)
            atomic_write_json(context_path, context)
            journal.record("cache_store", "complete" if stored is not None else "partial", stored=stored is not None)
        removed = remove_temporary_media(run.process_directory, keep=config.keep_media)
        if config.keep_media:
            context.setdefault("artifacts", {})["temporary_media"] = run.display(run.process_directory)
        else:
            if removed:
                context.setdefault("cleanup", {})["removed_media"] = removed
            remaining = [
                str(path.relative_to(run.process_directory))
                for path in run.process_directory.rglob("*")
                if path.is_file() and not path.is_symlink()
            ]
            if remaining:
                warnings.append(
                    "temporary media cleanup left files in place: "
                    + ", ".join(sorted(remaining))
                )
        context["warnings"] = _unique(warnings)
        atomic_write_json(context_path, context)
        journal.finish(status)
        return read_json(context_path)
    except WatchVideoError as exc:
        warnings.append(str(exc))
        _cleanup_failed_run(run, config, warnings)
        return _failure_context(
            normalized_url,
            config,
            run,
            journal,
            status=exc.status,
            error=str(exc),
            warnings=warnings,
            media_cache=persistent_video,
        )
    except Exception as exc:  # Keep the CLI structured even for unexpected adapter failures.
        message = f"unexpected watch-video failure: {safe_text(exc)}"
        warnings.append(message)
        _cleanup_failed_run(run, config, warnings)
        return _failure_context(
            normalized_url,
            config,
            run,
            journal,
            status="failed",
            error=message,
            warnings=warnings,
            media_cache=persistent_video,
        )


def _frame_rate_to_interval(value: str) -> float:
    try:
        rate = float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("FPS must be a finite positive number") from exc
    if not math.isfinite(rate) or rate <= 0:
        raise argparse.ArgumentTypeError("FPS must be a finite positive number")
    return 1.0 / rate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract structured, timestamp-grounded context from a video URL")
    parser.add_argument("url")
    parser.add_argument("--intent")
    parser.add_argument("--range", dest="range_spec")
    parser.add_argument("--visual", choices=("auto", "never", "always"), default="auto")
    parser.add_argument(
        "--cache",
        choices=("auto", "refresh", "off"),
        default="auto",
        help="reuse local/semantic caches; refresh replaces persistent video/audio",
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    frame_group = parser.add_mutually_exclusive_group()
    frame_group.add_argument(
        "--frame-interval",
        type=float,
        default=DEFAULT_FRAME_INTERVAL,
        metavar="SECONDS",
        help="seconds between periodic frames (default: 5; 0.5 means 2 FPS)",
    )
    frame_group.add_argument(
        "--fps",
        "--frames-per-second",
        dest="frame_interval",
        type=_frame_rate_to_interval,
        metavar="FPS",
        help="periodic frame rate; equivalent to --frame-interval 1/FPS",
    )
    parser.add_argument(
        "--max-subtitle-attempts",
        type=int,
        default=DEFAULT_MAX_SUBTITLE_ATTEMPTS,
        help="bound subtitle language downloads (default: 6)",
    )
    parser.add_argument("--language", dest="languages", action="append", default=[])
    parser.add_argument("--timestamp", dest="timestamps", action="append", default=[])
    parser.add_argument("--metadata-timeout", type=float, default=120.0)
    parser.add_argument("--download-timeout", type=float, default=1200.0)
    parser.add_argument("--asr-timeout", type=float, default=1800.0)
    parser.add_argument("--cookies")
    parser.add_argument("--cookies-from-browser", dest="cookies_from_browser")
    parser.add_argument("--yt-dlp", dest="yt_dlp")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    parser.add_argument("--asr-engine", choices=("auto", "whisper", "mlx-whisper", "none"), default="auto")
    parser.add_argument("--asr-command")
    parser.add_argument("--asr-model")
    parser.add_argument(
        "--translation-command",
        help="shell-free template using {input} and {output} JSON placeholders",
    )
    parser.add_argument("--translation-timeout", type=float, default=900.0)
    parser.add_argument("--task-name", help="user-visible artifact directory name")
    parser.add_argument("--run-id", help=argparse.SUPPRESS)
    parser.add_argument("--keep-media", action="store_true")
    return parser


def _config_from_args(args: argparse.Namespace) -> WatchConfig:
    if args.task_name and args.run_id:
        raise WatchVideoError("Specify either --task-name or the deprecated --run-id, not both")
    languages: list[str] = []
    for value in args.languages:
        languages.extend(part.strip() for part in value.split(",") if part.strip())
    return WatchConfig(
        url=args.url,
        intent=args.intent,
        range_spec=args.range_spec,
        visual=args.visual,
        cache=args.cache,
        workspace=args.workspace,
        frame_interval=args.frame_interval,
        max_subtitle_attempts=args.max_subtitle_attempts,
        preferred_languages=tuple(languages),
        requested_timestamps=_parse_requested_timestamps(args.timestamps),
        metadata_timeout=checked_timeout(args.metadata_timeout, "metadata timeout"),
        download_timeout=checked_timeout(args.download_timeout, "download timeout"),
        asr_timeout=checked_timeout(args.asr_timeout, "ASR timeout"),
        cookies=args.cookies,
        cookies_from_browser=args.cookies_from_browser,
        yt_dlp=args.yt_dlp,
        ffmpeg=args.ffmpeg,
        ffprobe=args.ffprobe,
        asr_engine=args.asr_engine,
        asr_command=args.asr_command,
        asr_model=args.asr_model,
        translation_command=args.translation_command,
        translation_timeout=checked_timeout(args.translation_timeout, "translation timeout"),
        task_name=args.task_name,
        run_id=args.run_id,
        keep_media=args.keep_media,
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        config = _config_from_args(args)
        result = run_watch(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") in {"complete", "partial"} else 2
    except WatchVideoError as exc:
        print(json.dumps({"status": exc.status, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["WatchConfig", "main", "run_watch"]
