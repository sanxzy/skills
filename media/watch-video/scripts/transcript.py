"""Subtitle selection, timestamp normalization, and transcript quality gates."""

from __future__ import annotations

import html
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .common import (
        CommandResult,
        WatchVideoError,
        checked_timeout,
        run_command,
        safe_filename,
        safe_text,
    )
    from .resolve_media import _auth_arguments, find_yt_dlp
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        CommandResult,
        WatchVideoError,
        checked_timeout,
        run_command,
        safe_filename,
        safe_text,
    )
    from resolve_media import _auth_arguments, find_yt_dlp  # type: ignore


_TIME_RE = re.compile(
    r"^\s*(?P<start>(?:(?:\d{1,2}:)?\d{1,2}:)?\d{1,2}(?:[\.,]\d{1,3})?)"
    r"\s*-->\s*"
    r"(?P<end>(?:(?:\d{1,2}:)?\d{1,2}:)?\d{1,2}(?:[\.,]\d{1,3})?)"
)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str

    def as_dict(self) -> dict[str, object]:
        return {"start": self.start, "end": self.end, "text": self.text}


@dataclass(frozen=True)
class TranscriptQuality:
    # ``usable`` retains the strict quality verdict for provenance and
    # backwards-compatible callers. ``recoverable`` means deterministic
    # caption-format cleanup produced timestamped text suitable for the
    # always-on best-effort path.
    usable: bool
    raw_segments: int
    normalized_segments: int
    duplicate_segments: int
    rolling_segments: int
    unique_text_ratio: float
    note: str
    recoverable: bool = False
    confidence: str = "unavailable"

    def as_dict(self) -> dict[str, object]:
        return {
            "usable": self.usable,
            "strict_usable": self.usable,
            "recoverable": self.recoverable,
            "confidence": self.confidence,
            "raw_segments": self.raw_segments,
            "normalized_segments": self.normalized_segments,
            "duplicate_segments": self.duplicate_segments,
            "rolling_segments": self.rolling_segments,
            "unique_text_ratio": round(self.unique_text_ratio, 4),
            "note": self.note,
        }


@dataclass(frozen=True)
class SubtitleChoice:
    language: str
    source: str  # human or automatic


@dataclass(frozen=True)
class SubtitleResult:
    status: str
    choice: SubtitleChoice | None
    path: Path | None
    segments: tuple[TranscriptSegment, ...]
    quality: TranscriptQuality | None
    command: CommandResult | None
    warnings: tuple[str, ...]
    attempted: int = 0
    advertised: int = 0


def _time_seconds(value: str) -> float:
    text = value.strip().replace(",", ".")
    pieces = text.split(":")
    if len(pieces) == 2:
        minutes, seconds = pieces
        return float(minutes) * 60 + float(seconds)
    if len(pieces) == 3:
        hours, minutes, seconds = pieces
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    raise ValueError(f"invalid caption timestamp: {value}")


def clean_caption_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = html.unescape(value.replace("\ufeff", ""))
    text = _TAG_RE.sub("", text)
    text = text.replace("\r", " ").replace("\n", " ")
    return _SPACE_RE.sub(" ", text).strip()


def _timed_blocks(text: str) -> list[tuple[float, float, str]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    records: list[tuple[float, float, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        upper = line.upper()
        if upper == "WEBVTT" or upper.startswith(("NOTE", "STYLE", "REGION")):
            index += 1
            while index < len(lines) and lines[index].strip():
                index += 1
            continue
        match = _TIME_RE.match(line)
        if match is None and index + 1 < len(lines):
            match = _TIME_RE.match(lines[index + 1].strip())
            if match is not None:
                index += 1  # Skip a cue identifier.
        if match is None:
            index += 1
            continue
        try:
            start = _time_seconds(match.group("start"))
            end = _time_seconds(match.group("end"))
        except (TypeError, ValueError):
            index += 1
            continue
        index += 1
        payload: list[str] = []
        while index < len(lines) and lines[index].strip():
            payload.append(lines[index])
            index += 1
        text_value = clean_caption_text(" ".join(payload))
        if end > start and text_value:
            records.append((start, end, text_value))
    return records


def _json3_segments(value: object) -> list[tuple[float, float, str]]:
    if not isinstance(value, Mapping):
        return []
    events = value.get("events")
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        return []
    records: list[tuple[float, float, str]] = []
    for event in events:
        if not isinstance(event, Mapping):
            continue
        start_ms = event.get("tStartMs")
        duration_ms = event.get("dDurationMs")
        try:
            start = float(start_ms) / 1000
            end = start + float(duration_ms or 0) / 1000
        except (TypeError, ValueError):
            continue
        pieces = event.get("segs")
        if isinstance(pieces, Sequence) and not isinstance(pieces, (str, bytes, bytearray)):
            text = "".join(
                piece.get("utf8", "")
                for piece in pieces
                if isinstance(piece, Mapping) and isinstance(piece.get("utf8", ""), str)
            )
        else:
            text = event.get("utf8", "")
        text = clean_caption_text(text)
        if end > start and text:
            records.append((start, end, text))
    return records


def parse_caption_text(text: str, *, format_hint: str | None = None) -> list[tuple[float, float, str]]:
    if not isinstance(text, str):
        raise WatchVideoError("caption content must be text")
    hint = (format_hint or "").casefold()
    if hint in {"json", "json3"} or text.lstrip().startswith("{"):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = None
        if value is not None:
            parsed = _json3_segments(value)
            if parsed:
                return parsed
    return _timed_blocks(text)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w']+", text.casefold(), flags=re.UNICODE)


def _overlap_count(previous: str, current: str) -> int:
    left = _tokens(previous)
    right = _tokens(current)
    if len(left) < 2 or len(right) < 2:
        return 0
    maximum = min(len(left), len(right))
    for size in range(maximum, 1, -1):
        if left[-size:] == right[:size]:
            return size
    return 0


def normalize_segments(
    records: Sequence[tuple[float, float, str]],
) -> tuple[tuple[TranscriptSegment, ...], TranscriptQuality]:
    """Normalize cues and reject rolling-window caption tracks as unusable.

    Rolling captions often repeat the previous window while appending a few
    new words.  We remove only high-confidence adjacent overlaps; a track is
    rejected when duplication remains dominant, so a caller can use ASR
    instead of silently making a bad transcript canonical.
    """

    raw_count = len(records)
    ordered: list[tuple[float, float, str]] = []
    for record in records:
        try:
            start, end, text = record
            start_number = float(start)
            end_number = float(end)
        except (TypeError, ValueError):
            continue
        cleaned = clean_caption_text(text)
        if start_number < 0 or end_number <= start_number or not cleaned:
            continue
        ordered.append((start_number, end_number, cleaned))
    ordered.sort(key=lambda item: (item[0], item[1]))

    normalized: list[TranscriptSegment] = []
    duplicate_count = 0
    rolling_count = 0
    previous_raw_text: str | None = None
    previous_raw_end: float | None = None
    for start, end, raw_text in ordered:
        text = raw_text
        if previous_raw_text is not None and previous_raw_end is not None:
            gap = start - previous_raw_end
            if raw_text.casefold() == previous_raw_text.casefold() and gap <= 2.0:
                duplicate_count += 1
                previous_raw_text = raw_text
                previous_raw_end = end
                continue
            overlap = _overlap_count(previous_raw_text, raw_text)
            previous_tokens = _tokens(previous_raw_text)
            current_tokens = _tokens(raw_text)
            if gap <= 2.0 and overlap >= max(2, int(min(len(previous_tokens), len(current_tokens)) * 0.6)):
                remainder = current_tokens[overlap:]
                if remainder:
                    text = " ".join(remainder)
                    rolling_count += 1
                else:
                    duplicate_count += 1
                    previous_raw_text = raw_text
                    previous_raw_end = end
                    continue
        normalized.append(TranscriptSegment(start=start, end=end, text=text))
        previous_raw_text = raw_text
        previous_raw_end = end

    texts = [segment.text.casefold() for segment in normalized]
    unique_ratio = len(set(texts)) / len(texts) if texts else 0.0
    duplicate_ratio = (duplicate_count + rolling_count) / raw_count if raw_count else 1.0
    usable = bool(normalized) and duplicate_ratio < 0.55 and unique_ratio >= 0.35
    if not normalized:
        note = "no valid timestamped caption cues"
    elif not usable:
        note = "caption cues contain dominant duplicate or rolling windows"
    elif duplicate_count or rolling_count:
        note = "caption cues normalized with bounded duplicate/rolling cleanup"
    else:
        note = "timestamped caption cues are usable"
    recoverable = bool(normalized)
    quality = TranscriptQuality(
        usable=usable,
        raw_segments=raw_count,
        normalized_segments=len(normalized),
        duplicate_segments=duplicate_count,
        rolling_segments=rolling_count,
        unique_text_ratio=unique_ratio,
        note=note,
        recoverable=recoverable,
        confidence="high" if usable else ("low-best-effort" if recoverable else "unavailable"),
    )
    return tuple(normalized), quality


def parse_caption_file(path: Path) -> tuple[tuple[TranscriptSegment, ...], TranscriptQuality]:
    target = Path(path)
    try:
        content = target.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise WatchVideoError(f"Could not read caption file {target}: {safe_text(exc)}") from exc
    records = parse_caption_text(content, format_hint=target.suffix.lstrip("."))
    return normalize_segments(records)


DEFAULT_MAX_SUBTITLE_ATTEMPTS = 6
MAX_SUBTITLE_ATTEMPTS = 24


def _normalized_language(value: str) -> str:
    return value.casefold().replace("_", "-").strip()


def _language_score(language: str, preferred: Sequence[str]) -> tuple[int, int, str]:
    normalized = _normalized_language(language)
    base = normalized.split("-", 1)[0]
    for index, item in enumerate(preferred):
        wanted = _normalized_language(item)
        wanted_base = wanted.split("-", 1)[0]
        if normalized == wanted:
            return (0, index, normalized)
        if base == wanted_base:
            return (1, index, normalized)
    return (2, len(preferred), normalized)


def _all_subtitle_choices(info: Mapping[str, Any]) -> tuple[SubtitleChoice, ...]:
    choices: list[SubtitleChoice] = []
    for source, key in (("human", "subtitles"), ("automatic", "automatic_captions")):
        tracks = info.get(key)
        if not isinstance(tracks, Mapping):
            continue
        for language in tracks.keys():
            if isinstance(language, str) and language.strip():
                choices.append(SubtitleChoice(language=language, source=source))
    return tuple(choices)


def _preferred_languages(
    info: Mapping[str, Any],
    preferred_languages: Sequence[str],
) -> tuple[str, ...]:
    values: list[str] = []
    for item in preferred_languages:
        if not isinstance(item, str):
            continue
        values.extend(part.strip() for part in item.split(",") if part.strip())
    source_language = info.get("language")
    fallbacks = [
        source_language.strip() if isinstance(source_language, str) and source_language.strip() else None,
        "en",
        "id",
    ]
    result: list[str] = []
    for item in (*values, *fallbacks):
        if not isinstance(item, str) or not item.strip():
            continue
        normalized = _normalized_language(item)
        if normalized and normalized not in {_normalized_language(value) for value in result}:
            result.append(item.strip())
    return tuple(result)


def _language_match_rank(language: str, wanted: str) -> int | None:
    actual = _normalized_language(language)
    target = _normalized_language(wanted)
    if actual == target:
        return 0
    actual_base = actual.split("-", 1)[0]
    target_base = target.split("-", 1)[0]
    if actual_base == target_base:
        # This intentionally includes variants such as ``id-orig`` when the
        # requested target is ``id``.
        return 1
    if actual.startswith(target + "-") or target.startswith(actual + "-"):
        return 2
    return None


def _subtitle_choices(
    info: Mapping[str, Any],
    preferred_languages: Sequence[str] = (),
    *,
    max_attempts: int | None = None,
    target_first: bool = False,
) -> tuple[SubtitleChoice, ...]:
    all_choices = _all_subtitle_choices(info)
    preferred = _preferred_languages(info, preferred_languages)
    if not target_first:
        ordered = sorted(
            all_choices,
            key=lambda choice: (
                0 if choice.source == "human" else 1,
                *_language_score(choice.language, preferred),
            ),
        )
    else:
        # For an explicit target, match the requested language before trying
        # an unrelated human track. Within a language, human subtitles still
        # precede automatic captions. Fallback languages are deliberately
        # limited to the source language, English, Indonesian, and one best
        # remaining advertised track.
        ordered = []
        seen: set[tuple[str, str]] = set()
        for wanted in preferred:
            matches = sorted(
                (
                    choice for choice in all_choices
                    if _language_match_rank(choice.language, wanted) is not None
                ),
                key=lambda choice: (
                    (
                        _language_match_rank(choice.language, wanted)
                        if _language_match_rank(choice.language, wanted) is not None
                        else 99
                    ),
                    0 if choice.source == "human" else 1,
                    _normalized_language(choice.language),
                ),
            )
            for choice in matches:
                key = (choice.source, _normalized_language(choice.language))
                if key not in seen:
                    ordered.append(choice)
                    seen.add(key)
        for source in ("human", "automatic"):
            remaining = sorted(
                (
                    choice for choice in all_choices
                    if (choice.source, _normalized_language(choice.language)) not in seen
                ),
                key=lambda choice: (
                    0 if choice.source == source else 1,
                    *_language_score(choice.language, preferred),
                ),
            )
            if remaining:
                choice = remaining[0]
                ordered.append(choice)
                seen.add((choice.source, _normalized_language(choice.language)))
    if max_attempts is not None:
        ordered = ordered[:max_attempts]
    return tuple(ordered)


def choose_subtitle_track(
    info: Mapping[str, Any],
    preferred_languages: Sequence[str] = (),
) -> SubtitleChoice | None:
    # Preserve the helper's established human-first selection semantics;
    # acquisition uses the target-first bounded policy below.
    choices = _subtitle_choices(info, preferred_languages)
    return choices[0] if choices else None


def _subtitle_files(directory: Path, before: set[Path]) -> list[Path]:
    extensions = {".vtt", ".srt", ".json3", ".json", ".ttml", ".srv3"}
    files = [
        path for path in directory.glob("001-subtitle.*")
        if path.is_file() and not path.is_symlink() and path not in before
        and path.suffix.casefold() in extensions and path.stat().st_size > 0
    ]
    priority = {".vtt": 0, ".srt": 1, ".json3": 2, ".json": 3, ".ttml": 4, ".srv3": 5}
    return sorted(files, key=lambda path: (priority.get(path.suffix.casefold(), 9), path.name))


def _rate_limited(detail: str) -> bool:
    lowered = detail.casefold()
    return "429" in lowered or "too many requests" in lowered or "rate limit" in lowered


def _subtitle_warning_summary(
    *,
    advertised: int,
    attempted: int,
    failures: Sequence[tuple[SubtitleChoice, str]],
    no_files: Sequence[SubtitleChoice],
    quality_failures: Sequence[tuple[SubtitleChoice, TranscriptQuality]],
    parse_failures: int = 0,
    selected: SubtitleChoice | None = None,
    selected_quality: TranscriptQuality | None = None,
) -> list[str]:
    warnings: list[str] = []
    if advertised > attempted:
        warnings.append(
            f"subtitle attempts were bounded at {attempted}; "
            f"{advertised - attempted} of {advertised} advertised tracks were not requested"
        )
    rate_limited = [item for item in failures if _rate_limited(item[1])]
    if rate_limited:
        warnings.append(f"{len(rate_limited)} subtitle language attempts returned HTTP 429 (rate limited)")
    other_failures = [item for item in failures if not _rate_limited(item[1])]
    for choice, detail in other_failures[:2]:
        warnings.append(
            f"{choice.source} subtitle download for {choice.language} failed: "
            f"{detail or 'yt-dlp returned a failure'}"
        )
    if len(other_failures) > 2:
        warnings.append(f"{len(other_failures) - 2} additional subtitle download failures were aggregated")
    if no_files:
        if len(no_files) == 1:
            choice = no_files[0]
            warnings.append(f"yt-dlp returned no {choice.source} subtitle file for {choice.language}")
        else:
            warnings.append(f"{len(no_files)} subtitle language attempts returned no file")
    if parse_failures:
        warnings.append(f"{parse_failures} downloaded subtitle file(s) could not be parsed")
    if quality_failures:
        warnings.append(
            f"{len(quality_failures)} subtitle track(s) failed the strict rolling/duplicate quality gate; "
            "recoverable text may still be used as low-confidence best effort"
        )
    if selected is not None and selected_quality is not None and not selected_quality.usable:
        warnings.append(
            f"using best-effort cleaned {selected.source} subtitles in {selected.language}; "
            f"strict quality was rejected ({selected_quality.note}) and recognition errors may remain"
        )
    return warnings


def acquire_subtitles(
    url: str,
    info: Mapping[str, Any],
    destination: Path,
    *,
    preferred_languages: Sequence[str] = (),
    max_attempts: int = DEFAULT_MAX_SUBTITLE_ATTEMPTS,
    timeout: float = 180.0,
    cookies: str | None = None,
    cookies_from_browser: str | None = None,
    yt_dlp: str | None = None,
    runner=None,
) -> SubtitleResult:
    """Try a bounded target-first set of tracks before ASR.

    Caption cleanup is always best effort: strict metrics remain in the
    returned quality record, but any non-empty recoverable result is returned
    with a low-confidence status rather than discarded.
    """

    if type(max_attempts) is not int or not 1 <= max_attempts <= MAX_SUBTITLE_ATTEMPTS:
        raise WatchVideoError(
            f"max subtitle attempts must be an integer between 1 and {MAX_SUBTITLE_ATTEMPTS}"
        )
    all_choices = _all_subtitle_choices(info)
    choices = _subtitle_choices(
        info,
        preferred_languages,
        max_attempts=max_attempts,
        target_first=True,
    )
    if not choices:
        return SubtitleResult(
            status="unavailable",
            choice=None,
            path=None,
            segments=(),
            quality=None,
            command=None,
            warnings=("no human or automatic subtitle track was advertised",),
            attempted=0,
            advertised=len(all_choices),
        )
    raw_directory = Path(destination).expanduser()
    if not raw_directory.is_absolute():
        raw_directory = Path.cwd() / raw_directory
    directory = raw_directory.resolve(strict=False)
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir() or directory.is_symlink():
        raise WatchVideoError(f"subtitle destination is not a regular directory: {directory}")
    tool = find_yt_dlp(
        yt_dlp,
        timeout=timeout,
        runner=runner,
        auto_install=runner is None,
    )
    failures: list[tuple[SubtitleChoice, str]] = []
    no_files: list[SubtitleChoice] = []
    quality_failures: list[tuple[SubtitleChoice, TranscriptQuality]] = []
    parse_failures = 0
    last_command: CommandResult | None = None
    saw_file = False
    for index, choice in enumerate(choices, start=1):
        attempt_dir = directory / f"{index:03d}-{choice.source}-{safe_filename(choice.language, fallback='language')}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        args = [
            *tool.argv,
            "--ignore-config",
            "--no-playlist",
            "--no-warnings",
            "--no-progress",
            "--skip-download",
            "--sub-langs", choice.language,
            "--sub-format", "vtt",
            "--output", str(attempt_dir / "001-subtitle.%(ext)s"),
            "--write-auto-subs" if choice.source == "automatic" else "--write-subs",
            *_auth_arguments(cookies, cookies_from_browser),
            "--", url,
        ]
        command = run_command(
            args,
            cwd=attempt_dir,
            timeout=checked_timeout(timeout, "subtitle timeout"),
            env=tool.environment,
            runner=runner,
        )
        last_command = command
        if not command.ok:
            failures.append((choice, safe_text(command.stderr or command.stdout).strip()))
            continue
        files = _subtitle_files(attempt_dir, set())
        if not files:
            no_files.append(choice)
            continue
        saw_file = True
        for path in files:
            try:
                segments, quality = parse_caption_file(path)
            except WatchVideoError:
                parse_failures += 1
                continue
            if quality.usable or quality.recoverable:
                status = "usable" if quality.usable else "best_effort"
                warnings = _subtitle_warning_summary(
                    advertised=len(all_choices),
                    attempted=index,
                    failures=failures,
                    no_files=no_files,
                    quality_failures=quality_failures,
                    parse_failures=parse_failures,
                    selected=choice,
                    selected_quality=quality,
                )
                return SubtitleResult(
                    status=status,
                    choice=choice,
                    path=path,
                    segments=segments,
                    quality=quality,
                    command=command,
                    warnings=tuple(warnings),
                    attempted=index,
                    advertised=len(all_choices),
                )
            quality_failures.append((choice, quality))
    warnings = _subtitle_warning_summary(
        advertised=len(all_choices),
        attempted=len(choices),
        failures=failures,
        no_files=no_files,
        quality_failures=quality_failures,
        parse_failures=parse_failures,
    )
    if not warnings:
        warnings.append("no usable timestamped subtitle track was returned")
    return SubtitleResult(
        status="unusable" if saw_file else "unavailable",
        choice=choices[0],
        path=None,
        segments=(),
        quality=None,
        command=last_command,
        warnings=tuple(warnings),
        attempted=len(choices),
        advertised=len(all_choices),
    )


def segments_from_artifact(value: object) -> tuple[TranscriptSegment, ...]:
    """Validate persisted normalized segments before reusing them."""

    if not isinstance(value, Mapping):
        return ()
    rows = value.get("segments")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return ()
    segments: list[TranscriptSegment] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        try:
            start = float(row.get("start"))
            end = float(row.get("end"))
        except (TypeError, ValueError):
            continue
        text = row.get("text")
        if math.isfinite(start) and math.isfinite(end) and 0 <= start < end and isinstance(text, str) and text.strip():
            segments.append(TranscriptSegment(start, end, text.strip()))
    return tuple(segments)


def transcript_artifact(
    segments: Sequence[TranscriptSegment],
    quality: TranscriptQuality,
    *,
    source: str,
    language: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "source": source,
        "quality": quality.as_dict(),
        "segments": [segment.as_dict() for segment in segments],
    }
    if language:
        result["language"] = language
    return result


__all__ = [
    "DEFAULT_MAX_SUBTITLE_ATTEMPTS",
    "MAX_SUBTITLE_ATTEMPTS",
    "SubtitleChoice",
    "SubtitleResult",
    "TranscriptQuality",
    "TranscriptSegment",
    "acquire_subtitles",
    "choose_subtitle_track",
    "clean_caption_text",
    "normalize_segments",
    "parse_caption_file",
    "parse_caption_text",
    "segments_from_artifact",
    "transcript_artifact",
]
