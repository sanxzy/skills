"""Optional speech-to-text adapters with a stable transcript result shape.

No model is downloaded by this module.  An installed ``whisper``/
``mlx_whisper`` command or an explicitly supplied shell-free command template
is used when available; otherwise the caller receives an actionable warning
and can continue with visual evidence.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .common import (
        CommandResult,
        WatchVideoError,
        checked_text,
        checked_timeout,
        parse_command_template,
        run_command,
        safe_text,
        trusted_module_available,
    )
    from .transcript import (
        TranscriptQuality,
        TranscriptSegment,
        normalize_segments,
        parse_caption_file,
    )
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        CommandResult,
        WatchVideoError,
        checked_text,
        checked_timeout,
        parse_command_template,
        run_command,
        safe_text,
        trusted_module_available,
    )
    from transcript import (  # type: ignore
        TranscriptQuality,
        TranscriptSegment,
        normalize_segments,
        parse_caption_file,
    )


@dataclass(frozen=True)
class AsrTool:
    argv: tuple[str, ...]
    name: str


@dataclass(frozen=True)
class AsrResult:
    status: str
    engine: str | None
    model: str | None
    path: Path | None
    segments: tuple[TranscriptSegment, ...]
    quality: TranscriptQuality | None
    command: CommandResult | None
    warnings: tuple[str, ...]


def find_asr_tool(engine: str = "auto") -> AsrTool | None:
    mode = checked_text(engine, "ASR engine", max_length=64).casefold()
    if mode == "none":
        return None
    if mode not in {"auto", "whisper", "mlx-whisper", "mlx_whisper"}:
        raise WatchVideoError("ASR engine must be auto, whisper, mlx-whisper, or none")

    if mode in {"auto", "mlx-whisper", "mlx_whisper"}:
        found = shutil.which("mlx_whisper")
        if found:
            return AsrTool((found,), "mlx_whisper")
        if mode != "whisper" and trusted_module_available("mlx_whisper"):
            return AsrTool((sys.executable, "-m", "mlx_whisper"), "mlx_whisper")
    if mode in {"auto", "whisper"}:
        found = shutil.which("whisper")
        if found:
            return AsrTool((found,), "whisper")
        if trusted_module_available("whisper"):
            return AsrTool((sys.executable, "-m", "whisper"), "whisper")
    return None


def _command_for_tool(
    tool: AsrTool,
    audio: Path,
    output_dir: Path,
    *,
    model: str,
    language: str | None,
) -> list[str]:
    if tool.name == "whisper":
        args = [
            *tool.argv,
            str(audio),
            "--output_dir", str(output_dir),
            "--output_format", "json",
            "--model", model,
        ]
        if language:
            args.extend(["--language", language])
        return args
    args = [
        *tool.argv,
        str(audio),
        "--output-dir", str(output_dir),
        "--output-format", "json",
        "--model", model,
    ]
    if language:
        args.extend(["--language", language])
    return args


def _custom_command(
    template: str,
    audio: Path,
    output_dir: Path,
    *,
    model: str,
    language: str | None,
) -> list[str]:
    tokens = parse_command_template(template)
    values = {
        "{audio}": str(audio),
        "{output_dir}": str(output_dir),
        "{model}": model,
        "{language}": language or "",
    }
    result: list[str] = []
    for token in tokens:
        expanded = token
        for placeholder, value in values.items():
            expanded = expanded.replace(placeholder, value)
        if "{" in expanded or "}" in expanded:
            raise WatchVideoError(f"ASR command contains an unsupported placeholder: {token}")
        result.append(expanded)
    return result


def _asr_json_records(value: object) -> list[tuple[float, float, str]]:
    if not isinstance(value, Mapping):
        return []
    segments = value.get("segments")
    if not isinstance(segments, Sequence) or isinstance(segments, (str, bytes, bytearray)):
        return []
    records: list[tuple[float, float, str]] = []
    for item in segments:
        if not isinstance(item, Mapping):
            continue
        try:
            start = float(item.get("start"))
            end = float(item.get("end"))
        except (TypeError, ValueError):
            continue
        text = item.get("text", "")
        if end > start and isinstance(text, str) and text.strip():
            records.append((start, end, text))
    return records


def _parse_asr_file(path: Path) -> tuple[tuple[TranscriptSegment, ...], TranscriptQuality] | None:
    try:
        if path.suffix.casefold() == ".json":
            value = json.loads(path.read_text(encoding="utf-8"))
            records = _asr_json_records(value)
            if records:
                return normalize_segments(records)
        if path.suffix.casefold() in {".vtt", ".srt", ".json3", ".ttml", ".srv3"}:
            return parse_caption_file(path)
    except (OSError, UnicodeError, json.JSONDecodeError, WatchVideoError):
        return None
    return None


def _output_files(directory: Path, before: set[Path]) -> list[Path]:
    extensions = {".json", ".vtt", ".srt", ".json3", ".ttml", ".srv3"}
    paths = [
        path for path in directory.iterdir()
        if path.is_file() and not path.is_symlink() and path not in before
        and path.suffix.casefold() in extensions and path.stat().st_size > 0
    ]
    priority = {".json": 0, ".vtt": 1, ".srt": 2, ".json3": 3, ".ttml": 4, ".srv3": 5}
    return sorted(paths, key=lambda path: (priority.get(path.suffix.casefold(), 9), path.name))


def transcribe_audio(
    audio: Path,
    destination: Path,
    *,
    engine: str = "auto",
    command_template: str | None = None,
    model: str | None = None,
    language: str | None = None,
    timeout: float = 1800.0,
    runner=None,
) -> AsrResult:
    """Run one bounded ASR attempt and accept only timestamped output."""

    audio_path = Path(audio)
    if not audio_path.is_file() or audio_path.is_symlink() or audio_path.stat().st_size <= 0:
        raise WatchVideoError(f"Audio input is not a usable regular file: {audio_path}")
    output_dir = Path(destination)
    output_dir.mkdir(parents=True, exist_ok=True)
    chosen_model = checked_text(
        model or os.environ.get("WATCH_VIDEO_WHISPER_MODEL", "base"),
        "ASR model",
        max_length=256,
    )
    if command_template is not None:
        command = _custom_command(
            command_template,
            audio_path,
            output_dir,
            model=chosen_model,
            language=language,
        )
        engine_name = "custom"
    else:
        tool = find_asr_tool(engine)
        if tool is None:
            return AsrResult(
                "unavailable", None, chosen_model, None, (), None, None,
                ("no supported ASR executable or module is available",),
            )
        command = _command_for_tool(
            tool,
            audio_path,
            output_dir,
            model=chosen_model,
            language=language,
        )
        engine_name = tool.name
    before = set(output_dir.iterdir())
    result = run_command(
        command,
        cwd=output_dir,
        timeout=checked_timeout(timeout, "ASR timeout"),
        runner=runner,
    )
    if not result.ok:
        detail = safe_text(result.stderr or result.stdout).strip()
        return AsrResult(
            "unavailable", engine_name, chosen_model, None, (), None, result,
            (f"ASR failed: {detail or 'the speech-to-text command returned a failure'}",),
        )
    warnings: list[str] = []
    for path in _output_files(output_dir, before):
        parsed = _parse_asr_file(path)
        if parsed is None:
            warnings.append(f"ignored ASR output without usable timestamps: {path.name}")
            continue
        segments, quality = parsed
        if quality.usable or quality.recoverable:
            status = "usable" if quality.usable else "best_effort"
            if not quality.usable:
                warnings.append(
                    f"using best-effort ASR text after the strict quality gate rejected the output: {quality.note}"
                )
            return AsrResult(status, engine_name, chosen_model, path, segments, quality, result, tuple(warnings))
        warnings.append(f"ASR output failed the transcript quality gate: {quality.note}")
    return AsrResult(
        "unusable", engine_name, chosen_model, None, (), None, result,
        tuple(warnings) or ("ASR returned no usable timestamped output",),
    )


def asr_artifact(
    result: AsrResult,
    *,
    language: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "source": "asr",
        "engine": result.engine,
        "model": result.model,
        "quality": result.quality.as_dict() if result.quality else None,
        "segments": [segment.as_dict() for segment in result.segments],
    }
    if language:
        payload["language"] = language
    return payload


__all__ = [
    "AsrResult",
    "AsrTool",
    "asr_artifact",
    "find_asr_tool",
    "transcribe_audio",
]
