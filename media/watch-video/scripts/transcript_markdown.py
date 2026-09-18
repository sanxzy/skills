"""Deterministic Markdown presentation for normalized transcript JSON."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .common import (
        WatchVideoError,
        atomic_write_text,
        format_timestamp,
        read_json,
        safe_text,
    )
except ImportError:  # pragma: no cover - direct executable path
    from common import (  # type: ignore
        WatchVideoError,
        atomic_write_text,
        format_timestamp,
        read_json,
        safe_text,
    )


DEFAULT_MAX_GAP_SECONDS = 1.5
DEFAULT_MAX_BLOCK_SECONDS = 45.0
DEFAULT_MAX_BLOCK_CHARS = 900


@dataclass(frozen=True)
class TranscriptBlock:
    """One readable paragraph and the normalized cues it presents."""

    start: float
    end: float
    text: str
    segment_indexes: tuple[int, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "segment_indexes": list(self.segment_indexes),
        }


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _segment_value(item: object, name: str) -> object:
    if isinstance(item, Mapping):
        return item.get(name)
    if isinstance(item, (tuple, list)) and len(item) >= 3:
        position = {"start": 0, "end": 1, "text": 2}.get(name)
        return item[position] if position is not None else None
    return getattr(item, name, None)


def _normalized_segments(value: object) -> tuple[tuple[float, float, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise WatchVideoError("normalized transcript segments must be an array")
    result: list[tuple[float, float, str]] = []
    for index, item in enumerate(value, start=1):
        start = _number(_segment_value(item, "start"))
        end = _number(_segment_value(item, "end"))
        text = _segment_value(item, "text")
        if start is None or end is None or start < 0 or end <= start:
            raise WatchVideoError(f"normalized transcript segment {index} has invalid timestamps")
        if not isinstance(text, str) or not text.strip():
            raise WatchVideoError(f"normalized transcript segment {index} has no text")
        # Accepted normalized transcripts already have whitespace-normalized
        # cue text. Only remove outer whitespace here so the presentation does
        # not silently alter the semantic content of a valid cue.
        result.append((start, end, text.strip()))
    return tuple(result)


def _checked_limit(value: object, label: str, *, integer: bool = False) -> float | int:
    if integer:
        if type(value) is not int or value < 1:
            raise WatchVideoError(f"{label} must be a positive integer")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WatchVideoError(f"{label} must be a finite positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise WatchVideoError(f"{label} must be a finite positive number")
    return number


def group_transcript_segments(
    segments: Sequence[object],
    *,
    max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS,
    max_block_seconds: float = DEFAULT_MAX_BLOCK_SECONDS,
    max_block_chars: int = DEFAULT_MAX_BLOCK_CHARS,
) -> tuple[TranscriptBlock, ...]:
    """Merge nearby normalized cues without changing their order or text.

    The source sequence is intentionally not sorted: normalized JSON order is
    the evidence order. A block may contain overlapping cues, or a short gap,
    but never exceeds the configured duration or text-size bound. A cue that
    is itself larger than a bound remains a single block rather than being
    split and thereby detached from its source timestamp.
    """

    gap_limit = float(_checked_limit(max_gap_seconds, "maximum transcript gap"))
    duration_limit = float(_checked_limit(max_block_seconds, "maximum transcript block duration"))
    character_limit = int(_checked_limit(max_block_chars, "maximum transcript block length", integer=True))
    normalized = _normalized_segments(segments)
    if not normalized:
        return ()

    blocks: list[TranscriptBlock] = []
    current_indexes: list[int] = [0]
    current_start, current_end, current_text = normalized[0]
    for index, (start, end, text) in enumerate(normalized[1:], start=1):
        joined = f"{current_text} {text}"
        gap = start - current_end
        duration = end - current_start
        if gap <= gap_limit and duration <= duration_limit and len(joined) <= character_limit:
            current_indexes.append(index)
            # Overlapping cues still need one range covering every cue in the
            # block, so an earlier cue's later end is never truncated.
            current_end = max(current_end, end)
            current_text = joined
            continue
        blocks.append(TranscriptBlock(
            start=current_start,
            end=current_end,
            text=current_text,
            segment_indexes=tuple(current_indexes),
        ))
        current_indexes = [index]
        current_start, current_end, current_text = start, end, text
    blocks.append(TranscriptBlock(
        start=current_start,
        end=current_end,
        text=current_text,
        segment_indexes=tuple(current_indexes),
    ))
    return tuple(blocks)


def _markdown_timestamp(value: float) -> str:
    """Use compact MM:SS evidence until an hour requires HH:MM:SS."""

    formatted = format_timestamp(value)
    return formatted[3:] if formatted.startswith("00:") else formatted


def _header_value(value: object, fallback: str = "unknown") -> str:
    if not isinstance(value, str):
        return fallback
    text = value.replace("\r", " ").replace("\n", " ").strip()
    if not text:
        return fallback
    return text[:256]


def _metric(value: object) -> str:
    number = _number(value)
    if number is None:
        return "unknown"
    if number.is_integer():
        return str(int(number))
    return f"{number:.4f}".rstrip("0").rstrip(".")


def _quality_lines(payload: Mapping[str, Any]) -> list[str]:
    quality = payload.get("quality")
    if not isinstance(quality, Mapping):
        lines = ["- Quality: unknown"]
        warnings = payload.get("warnings")
        if isinstance(warnings, Sequence) and not isinstance(warnings, (str, bytes, bytearray)):
            for warning in warnings:
                if isinstance(warning, str) and warning.strip():
                    lines.append(f"- Warning: {_header_value(warning)}")
        return lines

    confidence = quality.get("confidence")
    if not isinstance(confidence, str) or not confidence.strip():
        strict = quality.get("strict_usable", quality.get("usable"))
        recoverable = quality.get("recoverable")
        confidence = (
            "high" if strict is True
            else "low-best-effort" if recoverable is True
            else "unknown"
        )
    lines = [f"- Quality: {_header_value(confidence)}"]
    metric_values = [
        ("raw", quality.get("raw_segments")),
        ("normalized", quality.get("normalized_segments")),
        ("duplicates", quality.get("duplicate_segments")),
        ("rolling", quality.get("rolling_segments")),
        ("unique-text-ratio", quality.get("unique_text_ratio")),
    ]
    available = [(name, value) for name, value in metric_values if value is not None]
    if available:
        lines.append("- Quality metrics: " + ", ".join(f"{name}={_metric(value)}" for name, value in available))

    note = quality.get("note")
    strict = quality.get("strict_usable", quality.get("usable"))
    is_warning = strict is False or confidence.casefold() not in {"high", "usable"}
    if isinstance(note, str) and note.strip():
        lines.append(f"- {'Warning' if is_warning else 'Note'}: {_header_value(note)}")
    warnings = quality.get("warnings")
    if isinstance(warnings, Sequence) and not isinstance(warnings, (str, bytes, bytearray)):
        for warning in warnings:
            if isinstance(warning, str) and warning.strip():
                lines.append(f"- Warning: {_header_value(warning)}")
    top_level_warnings = payload.get("warnings")
    if isinstance(top_level_warnings, Sequence) and not isinstance(top_level_warnings, (str, bytes, bytearray)):
        for warning in top_level_warnings:
            if isinstance(warning, str) and warning.strip():
                line = f"- Warning: {_header_value(warning)}"
                if line not in lines:
                    lines.append(line)
    return lines


def _language_value(payload: Mapping[str, Any], name: str) -> object:
    value = payload.get(name)
    if isinstance(value, str) and value.strip():
        return value
    return payload.get("language")


def _translation_lines(payload: Mapping[str, Any]) -> list[str]:
    performed = payload.get("translation_performed") is True
    if not performed:
        return ["- Translation: not performed"]
    provenance = payload.get("translation_provenance")
    detail = "performed"
    if isinstance(provenance, Mapping):
        method = provenance.get("method")
        origin = provenance.get("source")
        parts = [
            _header_value(item, "")
            for item in (method, origin)
            if isinstance(item, str) and item.strip()
        ]
        if parts:
            detail += " (" + ", ".join(parts) + ")"
    elif isinstance(provenance, str) and provenance.strip():
        detail += f" ({_header_value(provenance)})"
    return [
        f"- Translation: {detail}",
        "- Original transcript: retained separately",
    ]


def render_transcript_markdown(
    payload: Mapping[str, Any],
    *,
    max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS,
    max_block_seconds: float = DEFAULT_MAX_BLOCK_SECONDS,
    max_block_chars: int = DEFAULT_MAX_BLOCK_CHARS,
) -> str:
    """Render one normalized transcript payload without reading raw captions."""

    if not isinstance(payload, Mapping):
        raise WatchVideoError("normalized transcript artifact must be a JSON object")
    segments = _normalized_segments(payload.get("segments"))
    blocks = group_transcript_segments(
        segments,
        max_gap_seconds=max_gap_seconds,
        max_block_seconds=max_block_seconds,
        max_block_chars=max_block_chars,
    )
    source_language = _language_value(payload, "source_language")
    output_language = _language_value(payload, "output_language")
    lines = [
        "# Transcript",
        "",
        f"- Source: {_header_value(payload.get('source'))}",
        f"- Source language: {_header_value(source_language)}",
        f"- Output language: {_header_value(output_language)}",
        *_quality_lines(payload),
        *_translation_lines(payload),
        f"- Segments: {len(segments)}",
        f"- Blocks: {len(blocks)}",
        "",
    ]
    if not blocks:
        lines.append("No transcript segments available.")
    else:
        for block in blocks:
            # Normalized cues are normally one line. Keep an unexpected line
            # break inside the same paragraph so source content cannot create
            # a second Markdown block or alter the timestamp mapping.
            text = block.text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
            text = text.replace("\u2028", " ").replace("\u2029", " ")
            lines.append(
                f"[{_markdown_timestamp(block.start)}–{_markdown_timestamp(block.end)}] {text}"
            )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_transcript_markdown(
    source_path: Path,
    destination: Path | None = None,
    *,
    max_gap_seconds: float = DEFAULT_MAX_GAP_SECONDS,
    max_block_seconds: float = DEFAULT_MAX_BLOCK_SECONDS,
    max_block_chars: int = DEFAULT_MAX_BLOCK_CHARS,
) -> Path:
    """Read normalized JSON and atomically write its Markdown presentation."""

    source = Path(source_path)
    if not source.is_file() or source.is_symlink():
        raise WatchVideoError(f"normalized transcript artifact is not a regular file: {source}")
    value = read_json(source)
    markdown = render_transcript_markdown(
        value,
        max_gap_seconds=max_gap_seconds,
        max_block_seconds=max_block_seconds,
        max_block_chars=max_block_chars,
    )
    target = Path(destination) if destination is not None else source.with_suffix(".md")
    atomic_write_text(target, markdown)
    try:
        read_back = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise WatchVideoError(f"Could not read transcript Markdown artifact {target}: {safe_text(exc)}") from exc
    if read_back != markdown:
        raise WatchVideoError(f"Transcript Markdown read-back did not match: {target}")
    return target


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render normalized transcript JSON as readable Markdown")
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-gap-seconds", type=float, default=DEFAULT_MAX_GAP_SECONDS)
    parser.add_argument("--max-block-seconds", type=float, default=DEFAULT_MAX_BLOCK_SECONDS)
    parser.add_argument("--max-block-chars", type=int, default=DEFAULT_MAX_BLOCK_CHARS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        output = write_transcript_markdown(
            args.source,
            args.output,
            max_gap_seconds=args.max_gap_seconds,
            max_block_seconds=args.max_block_seconds,
            max_block_chars=args.max_block_chars,
        )
        print(json.dumps({"path": str(output)}, ensure_ascii=False))
        return 0
    except WatchVideoError as exc:
        print(json.dumps({"status": exc.status, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "DEFAULT_MAX_BLOCK_CHARS",
    "DEFAULT_MAX_BLOCK_SECONDS",
    "DEFAULT_MAX_GAP_SECONDS",
    "TranscriptBlock",
    "group_transcript_segments",
    "main",
    "render_transcript_markdown",
    "write_transcript_markdown",
]
