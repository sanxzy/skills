"""Build a compact timestamped timeline and retrieve relevant transcript spans."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .common import WatchVideoError, optional_float, safe_text
except ImportError:  # pragma: no cover
    from common import WatchVideoError, optional_float, safe_text  # type: ignore


_WORD_RE = re.compile(r"[\w'-]+", flags=re.UNICODE)
_STOPWORDS = {
    "a", "about", "all", "an", "and", "are", "as", "at", "be", "by", "can", "do",
    "explain", "for", "from", "how", "i", "in", "is", "it", "me", "of", "on", "or",
    "please", "show", "that", "the", "their", "this", "to", "understand", "what", "where",
    "which", "with", "you", "video", "when", "does", "they", "discuss", "talk", "tell",
}


@dataclass(frozen=True)
class TimelineSegment:
    start: float
    end: float
    speech: str | None
    frames: tuple[dict[str, object], ...]
    title: str | None = None

    def as_dict(self) -> dict[str, object]:
        value: dict[str, object] = {"start": self.start, "end": self.end}
        if self.title:
            value["title"] = self.title
        if self.speech:
            value["speech"] = self.speech
        if self.frames:
            value["frames"] = list(self.frames)
        return value


def _number(value: object) -> float | None:
    return optional_float(value)


def _segment_bounds(item: object) -> tuple[float, float] | None:
    if not isinstance(item, Mapping):
        start = _number(getattr(item, "start", None))
        end = _number(getattr(item, "end", None))
    else:
        start = _number(item.get("start"))
        end = _number(item.get("end"))
    if start is None or end is None or start < 0 or end <= start:
        return None
    return start, end


def _segment_text(item: object) -> str:
    if isinstance(item, Mapping):
        value = item.get("text", "")
    else:
        value = getattr(item, "text", "")
    return value.strip() if isinstance(value, str) else ""


def _overlaps(start: float, end: float, left: float, right: float) -> bool:
    return start < right and end > left


def _clip_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 15)].rstrip() + " …[truncated]"


def _chapter_title(item: object) -> str | None:
    if isinstance(item, Mapping):
        value = item.get("title")
    else:
        value = getattr(item, "title", None)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _frame_bounds(item: object) -> float | None:
    if isinstance(item, Mapping):
        return _number(item.get("timestamp"))
    return _number(getattr(item, "timestamp", None))


def _frame_reference(item: object) -> dict[str, object] | None:
    timestamp = _frame_bounds(item)
    if timestamp is None:
        return None
    result: dict[str, object] = {"timestamp": round(timestamp, 3)}
    if isinstance(item, Mapping):
        path = item.get("path")
        signals = item.get("signals")
    else:
        path = getattr(item, "path", None)
        signals = getattr(item, "signals", None)
    if isinstance(path, str) and path:
        result["path"] = path
    if isinstance(signals, Sequence) and not isinstance(signals, (str, bytes, bytearray)):
        result["signals"] = [str(value) for value in signals]
    return result


def _make_ranges(
    duration: float,
    chapters: Sequence[object],
    transcript: Sequence[object],
    frames: Sequence[object],
    max_segment_seconds: float,
) -> list[tuple[float, float, str | None]]:
    if chapters:
        result: list[tuple[float, float, str | None]] = []
        for item in chapters:
            bounds = _segment_bounds(item)
            if bounds is None:
                continue
            start, end = max(0.0, bounds[0]), min(duration, bounds[1])
            if end > start:
                result.append((start, end, _chapter_title(item)))
        if result:
            covered: list[tuple[float, float, str | None]] = []
            cursor = 0.0
            for start, end, title in sorted(result, key=lambda item: (item[0], item[1])):
                if start > cursor:
                    covered.append((cursor, start, None))
                clipped_start = max(cursor, start)
                if end > clipped_start:
                    covered.append((clipped_start, end, title))
                    cursor = max(cursor, end)
            if cursor < duration:
                covered.append((cursor, duration, None))
            return covered

    valid_transcript = [bounds for item in transcript if (bounds := _segment_bounds(item)) is not None]
    if valid_transcript:
        result = []
        chunk_start = valid_transcript[0][0]
        chunk_end = chunk_start
        for start, end in valid_transcript:
            if chunk_end > chunk_start and start - chunk_start >= max_segment_seconds:
                result.append((chunk_start, chunk_end, None))
                chunk_start = start
            chunk_end = max(chunk_end, end)
        result.append((chunk_start, chunk_end, None))
        if result[0][0] > 0:
            result.insert(0, (0.0, result[0][0], None))
        if result[-1][1] < duration:
            result.append((result[-1][1], duration, None))
        return result

    frame_times = sorted({value for item in frames if (value := _frame_bounds(item)) is not None and 0 <= value <= duration})
    if frame_times:
        boundaries = [0.0, *frame_times, duration]
        result = []
        for left, right in zip(boundaries, boundaries[1:]):
            if right > left:
                result.append((left, right, None))
        return result
    return [(0.0, duration, None)]


def build_timeline(
    duration: float,
    *,
    transcript: Sequence[object] = (),
    chapters: Sequence[object] = (),
    frames: Sequence[object] = (),
    max_segment_seconds: float = 90.0,
    max_speech_chars: int = 1200,
) -> tuple[TimelineSegment, ...]:
    if not isinstance(duration, (int, float)) or isinstance(duration, bool) or duration <= 0:
        raise WatchVideoError("timeline duration must be a positive number")
    if not isinstance(max_segment_seconds, (int, float)) or isinstance(max_segment_seconds, bool) or max_segment_seconds <= 0:
        raise WatchVideoError("max segment duration must be positive")
    if type(max_speech_chars) is not int or max_speech_chars < 80:
        raise WatchVideoError("max speech chars must be an integer of at least 80")
    total = float(duration)
    ranges = _make_ranges(total, chapters, transcript, frames, float(max_segment_seconds))
    output: list[TimelineSegment] = []
    for start, end, title in ranges:
        speech_parts = [
            _segment_text(item)
            for item in transcript
            if (bounds := _segment_bounds(item)) is not None
            and _overlaps(bounds[0], bounds[1], start, end)
            and _segment_text(item)
        ]
        frame_refs = [
            reference for item in frames
            if (reference := _frame_reference(item)) is not None
            and start - 0.001 <= float(reference["timestamp"]) <= end + 0.001
        ]
        output.append(TimelineSegment(
            start=round(max(0.0, start), 3),
            end=round(min(total, end), 3),
            title=title,
            speech=_clip_text(" ".join(speech_parts), max_speech_chars) or None,
            frames=tuple(frame_refs),
        ))
    return tuple(output)


def _query_terms(query: str) -> tuple[str, ...]:
    return tuple(
        word.casefold() for word in _WORD_RE.findall(query)
        if len(word) > 1 and word.casefold() not in _STOPWORDS
    )


def _term_variants(term: str) -> tuple[str, ...]:
    variants = [term]
    if term.endswith("ing") and len(term) > 5:
        stem = term[:-3]
        variants.append(stem)
        if stem.endswith("ch"):
            variants.append(stem + "e")
    elif term.endswith("ed") and len(term) > 4:
        variants.append(term[:-2])
    return tuple(dict.fromkeys(variants))


def search_transcript(
    segments: Sequence[object],
    query: str,
    *,
    max_matches: int = 5,
    context_seconds: float = 20.0,
    duration: float | None = None,
) -> tuple[dict[str, object], ...]:
    """Return evidence-ranked matches; never execute or interpret the text."""

    if not isinstance(query, str) or not query.strip():
        return ()
    if type(max_matches) is not int or max_matches < 1 or max_matches > 20:
        raise WatchVideoError("max transcript matches must be between 1 and 20")
    if not isinstance(context_seconds, (int, float)) or isinstance(context_seconds, bool) or context_seconds < 0:
        raise WatchVideoError("transcript context seconds must be non-negative")
    terms = _query_terms(query)
    if not terms:
        return ()
    scored: list[dict[str, object]] = []
    phrase = " ".join(terms)
    for item in segments:
        bounds = _segment_bounds(item)
        text = _segment_text(item)
        if bounds is None or not text:
            continue
        lowered = text.casefold()
        present = sum(1 for term in terms if any(variant in lowered for variant in _term_variants(term)))
        if not present:
            continue
        score = present / len(terms)
        if phrase and phrase in lowered:
            score += 0.5
        scored.append({
            "start": round(bounds[0], 3),
            "end": round(bounds[1], 3),
            "score": round(score, 4),
            "snippet": _clip_text(text, 320),
        })
    scored.sort(key=lambda item: (-float(item["score"]), float(item["start"])))
    return tuple(scored[:max_matches])


def focus_ranges_from_matches(
    matches: Sequence[Mapping[str, object]],
    *,
    duration: float,
    context_seconds: float = 20.0,
) -> tuple[tuple[float, float], ...]:
    if duration <= 0:
        raise WatchVideoError("focus-range duration must be positive")
    ranges: list[tuple[float, float]] = []
    for match in matches:
        start = _number(match.get("start"))
        end = _number(match.get("end"))
        if start is None or end is None or end <= start:
            continue
        ranges.append((max(0.0, start - context_seconds), min(duration, end + context_seconds)))
    if not ranges:
        return ()
    ranges.sort()
    merged: list[list[float]] = []
    for start, end in ranges:
        if merged and start <= merged[-1][1] + 1.0:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return tuple((round(start, 3), round(end, 3)) for start, end in merged)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WatchVideoError(f"Could not read timeline input {path}: {safe_text(exc)}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a compact video timeline")
    parser.add_argument("--duration", required=True, type=float)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--chapters", type=Path)
    parser.add_argument("--frames", type=Path)
    parser.add_argument("--query")
    return parser


def _payload(value: Any, key: str | None = None) -> list[object]:
    if isinstance(value, list):
        return value
    if isinstance(value, Mapping) and key and isinstance(value.get(key), list):
        return value[key]
    return []


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        transcript = _payload(_read_json(args.transcript), "segments") if args.transcript else []
        chapters = _payload(_read_json(args.chapters), "chapters") if args.chapters else []
        frames = _payload(_read_json(args.frames), "frames") if args.frames else []
        payload: dict[str, object] = {
            "timeline": [item.as_dict() for item in build_timeline(
                args.duration,
                transcript=transcript,
                chapters=chapters,
                frames=frames,
            )],
        }
        if args.query:
            payload["matches"] = list(search_transcript(transcript, args.query))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except WatchVideoError as exc:
        print(json.dumps({"status": exc.status, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "TimelineSegment",
    "build_timeline",
    "focus_ranges_from_matches",
    "search_transcript",
]
