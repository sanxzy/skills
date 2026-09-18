"""Optional timestamp-preserving transcript translation adapter.

Translation is deliberately an explicit adapter boundary.  The script never
pretends that source-language text is translated: a configured shell-free
command must read a JSON chunk and write a JSON chunk with one translated text
per source segment.  Source timestamps are retained by this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .common import (
        MAX_COMMAND_OUTPUT,
        WatchVideoError,
        atomic_write_json,
        parse_command_template,
        read_json,
        run_command,
        safe_text,
    )
    from .transcript import TranscriptSegment
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        MAX_COMMAND_OUTPUT,
        WatchVideoError,
        atomic_write_json,
        parse_command_template,
        read_json,
        run_command,
        safe_text,
    )
    from transcript import TranscriptSegment  # type: ignore


MAX_TRANSLATION_CHUNK_SEGMENTS = 48
MAX_TRANSLATION_CHARS = 12_000


@dataclass(frozen=True)
class TranslationResult:
    status: str
    source_language: str
    target_language: str
    segments: tuple["TranscriptSegment", ...]
    chunks: int
    warnings: tuple[str, ...]


def _language_key(value: str) -> str:
    return value.casefold().replace("_", "-").strip()


def _same_language(source: str, target: str) -> bool:
    source_key = _language_key(source)
    target_key = _language_key(target)
    return source_key == target_key or source_key.split("-", 1)[0] == target_key.split("-", 1)[0]


def _absolute_directory(destination: Path) -> Path:
    directory = Path(destination).expanduser()
    if not directory.is_absolute():
        directory = Path.cwd() / directory
    directory = directory.resolve(strict=False)
    directory.mkdir(parents=True, exist_ok=True)
    if not directory.is_dir() or directory.is_symlink():
        raise WatchVideoError(f"translation destination is not a regular directory: {directory}")
    return directory


def _chunks(segments: Sequence["TranscriptSegment"]) -> tuple[tuple["TranscriptSegment", ...], ...]:
    result: list[tuple["TranscriptSegment", ...]] = []
    current: list["TranscriptSegment"] = []
    characters = 0
    for segment in segments:
        length = len(segment.text)
        if current and (
            len(current) >= MAX_TRANSLATION_CHUNK_SEGMENTS
            or characters + length > MAX_TRANSLATION_CHARS
        ):
            result.append(tuple(current))
            current = []
            characters = 0
        current.append(segment)
        characters += length
    if current:
        result.append(tuple(current))
    return tuple(result)


def _translated_texts(value: object) -> list[object]:
    if isinstance(value, Mapping):
        value = value.get("segments", value.get("translations"))
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return list(value)


def _translated_chunk(
    value: object,
    source_segments: Sequence["TranscriptSegment"],
) -> tuple["TranscriptSegment", ...]:
    values = _translated_texts(value)
    if len(values) != len(source_segments):
        raise WatchVideoError(
            f"translation returned {len(values)} segments for {len(source_segments)} source segments"
        )
    translated: list["TranscriptSegment"] = []
    for source, item in zip(source_segments, values):
        if isinstance(item, Mapping):
            text = item.get("text")
            supplied_start = item.get("start")
            supplied_end = item.get("end")
            if supplied_start is not None or supplied_end is not None:
                try:
                    if abs(float(supplied_start) - source.start) > 0.01 or abs(float(supplied_end) - source.end) > 0.01:
                        raise WatchVideoError("translation changed source timestamps")
                except (TypeError, ValueError) as exc:
                    raise WatchVideoError("translation returned invalid timestamps") from exc
        else:
            text = item
        if not isinstance(text, str) or not text.strip():
            raise WatchVideoError("translation returned an empty segment")
        cleaned = text.strip()
        if len(cleaned) > MAX_TRANSLATION_CHARS:
            raise WatchVideoError("translation returned an overlong segment")
        translated.append(TranscriptSegment(source.start, source.end, cleaned))
    return tuple(translated)


def translate_segments(
    segments: Sequence["TranscriptSegment"],
    *,
    source_language: str | None,
    target_language: str | None,
    destination: Path,
    command_template: str | None = None,
    timeout: float = 900.0,
    runner=None,
) -> TranslationResult:
    """Translate cleaned segments only through an explicitly configured adapter."""

    source = str(source_language or "").strip()
    target = str(target_language or "").strip()
    original = tuple(segments)
    if not target or not source or _same_language(source, target):
        return TranslationResult("not_needed", source, target, original, 0, ())
    if command_template is None:
        return TranslationResult(
            "unavailable",
            source,
            target,
            (),
            0,
            (
                f"target language {target} was requested but no translation adapter is configured; "
                f"retaining the cleaned {source} transcript",
            ),
        )
    output_dir = _absolute_directory(destination)
    tokens = parse_command_template(command_template, required=("{input}", "{output}"))
    translated: list["TranscriptSegment"] = []
    chunks = _chunks(original)
    sequence = 1
    for chunk_index, chunk in enumerate(chunks, start=1):
        input_path = output_dir / f"{sequence:03d}-translation-input-{chunk_index:04d}.json"
        sequence += 1
        output_path = output_dir / f"{sequence:03d}-translation-output-{chunk_index:04d}.json"
        sequence += 1
        atomic_write_json(input_path, {
            "source_language": source,
            "target_language": target,
            "segments": [segment.as_dict() for segment in chunk],
        })
        values = {
            "{input}": str(input_path),
            "{output}": str(output_path),
            "{source_language}": source,
            "{target_language}": target,
        }
        command: list[str] = []
        for token in tokens:
            expanded = token
            for placeholder, replacement in values.items():
                expanded = expanded.replace(placeholder, replacement)
            if "{" in expanded or "}" in expanded:
                return TranslationResult(
                    "unavailable",
                    source,
                    target,
                    (),
                    chunk_index - 1,
                    (f"translation command contains an unsupported placeholder: {token}",),
                )
            command.append(expanded)
        result = run_command(
            command,
            cwd=output_dir,
            timeout=timeout,
            runner=runner,
            output_limit=MAX_COMMAND_OUTPUT,
        )
        if not result.ok:
            detail = safe_text(result.stderr or result.stdout).strip()
            return TranslationResult(
                "unavailable",
                source,
                target,
                (),
                chunk_index - 1,
                (f"translation adapter failed: {detail or 'command returned a failure'}",),
            )
        if not output_path.is_file() or output_path.is_symlink():
            return TranslationResult(
                "unavailable",
                source,
                target,
                (),
                chunk_index - 1,
                ("translation adapter returned success without a JSON output file",),
            )
        try:
            value = read_json(output_path)
            translated.extend(_translated_chunk(value, chunk))
        except (OSError, WatchVideoError) as exc:
            return TranslationResult(
                "unavailable",
                source,
                target,
                (),
                chunk_index - 1,
                (f"translation output was rejected: {safe_text(exc)}",),
            )
    return TranslationResult("usable", source, target, tuple(translated), len(chunks), ())


__all__ = [
    "MAX_TRANSLATION_CHUNK_SEGMENTS",
    "MAX_TRANSLATION_CHARS",
    "TranslationResult",
    "translate_segments",
]
