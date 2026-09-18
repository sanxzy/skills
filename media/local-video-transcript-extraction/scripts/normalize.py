"""Normalize Faster Whisper segments and enforce timestamp invariants."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

try:
    from .common import (
        TIMESTAMP_TOLERANCE_SECONDS,
        TranscriptError,
        finite_number,
        get_value,
        normalize_text,
        optional_number,
    )
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        TIMESTAMP_TOLERANCE_SECONDS,
        TranscriptError,
        finite_number,
        get_value,
        normalize_text,
        optional_number,
    )


@dataclass(frozen=True)
class NormalizedWord:
    start: float
    end: float
    text: str
    probability: float | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }
        if self.probability is not None:
            result["probability"] = self.probability
        return result


@dataclass(frozen=True)
class NormalizedSegment:
    id: int
    start: float
    end: float
    text: str
    words: tuple[NormalizedWord, ...] = ()
    avg_logprob: float | None = None
    no_speech_prob: float | None = None
    compression_ratio: float | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "words": [word.as_dict() for word in self.words],
        }
        if self.avg_logprob is not None:
            result["avg_logprob"] = self.avg_logprob
        if self.no_speech_prob is not None:
            result["no_speech_prob"] = self.no_speech_prob
        if self.compression_ratio is not None:
            result["compression_ratio"] = self.compression_ratio
        return result


def _invalid(code: str, message: str, *, details: Mapping[str, object] | None = None) -> TranscriptError:
    return TranscriptError(code, message, stage="transcribing", details=details)


def _word_records(raw_words: object) -> list[object]:
    if raw_words is None:
        return []
    if isinstance(raw_words, (str, bytes, bytearray)):
        raise _invalid("invalid_word_data", "segment words must be a sequence")
    try:
        return list(raw_words)  # type: ignore[arg-type]
    except TypeError as exc:
        raise _invalid("invalid_word_data", "segment words must be a sequence") from exc


def _word_from_raw(raw: object, segment: NormalizedSegment | None = None) -> NormalizedWord:
    start_value = get_value(raw, "start")
    end_value = get_value(raw, "end")
    try:
        start = finite_number(start_value, "word start", non_negative=True)
        end = finite_number(end_value, "word end", non_negative=True)
    except TranscriptError as exc:
        raise _invalid(exc.code, str(exc), details=exc.details) from exc
    if end <= start:
        raise _invalid("invalid_word_timestamp", "word end must be greater than word start")
    text = normalize_text(get_value(raw, "word", get_value(raw, "text", "")))
    if not text:
        raise _invalid("invalid_word_data", "word text must not be blank")
    probability = optional_number(get_value(raw, "probability"), "word probability")
    if probability is not None and not 0 <= probability <= 1:
        raise _invalid("invalid_diagnostic", "word probability must be between 0 and 1")
    if segment is not None:
        tolerance = TIMESTAMP_TOLERANCE_SECONDS
        if start < segment.start - tolerance or end > segment.end + tolerance:
            raise _invalid(
                "invalid_word_timestamp",
                "word timestamps must remain within the parent segment",
                details={"segment_id": segment.id},
            )
    return NormalizedWord(start=start, end=end, text=text, probability=probability)


def normalize_segment(
    raw: object,
    segment_id: int,
    *,
    duration: float | None = None,
    tolerance: float = TIMESTAMP_TOLERANCE_SECONDS,
) -> NormalizedSegment | None:
    """Convert one Faster Whisper segment into the canonical stable shape.

    Empty decoder records are ignored. Any non-empty record with invalid timing
    is fatal so the caller cannot publish a misleading completed transcript.
    """

    if type(segment_id) is not int or segment_id < 0:
        raise _invalid("invalid_segment_id", "segment identifier must be a non-negative integer")
    try:
        start = finite_number(get_value(raw, "start"), "segment start", non_negative=True)
        end = finite_number(get_value(raw, "end"), "segment end", non_negative=True)
    except TranscriptError as exc:
        raise _invalid(exc.code, str(exc), details=exc.details) from exc
    if end <= start:
        raise _invalid("invalid_timestamp", "segment end must be greater than segment start")
    if duration is not None and end > duration + tolerance:
        raise _invalid(
            "timestamp_out_of_range",
            "segment timestamp exceeds the known media duration",
            details={"segment_id": segment_id, "duration_seconds": duration},
        )
    text = normalize_text(get_value(raw, "text", ""))
    if not text:
        return None
    avg_logprob = optional_number(get_value(raw, "avg_logprob"), "avg_logprob")
    no_speech_prob = optional_number(get_value(raw, "no_speech_prob"), "no_speech_prob")
    if no_speech_prob is not None and not 0 <= no_speech_prob <= 1:
        raise _invalid("invalid_diagnostic", "no_speech_prob must be between 0 and 1")
    compression_ratio = optional_number(get_value(raw, "compression_ratio"), "compression_ratio")
    provisional = NormalizedSegment(
        id=segment_id,
        start=start,
        end=end,
        text=text,
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
        compression_ratio=compression_ratio,
    )
    raw_words = _word_records(get_value(raw, "words"))
    if not raw_words:
        raise _invalid(
            "invalid_word_data",
            "non-empty segments must include word-level timestamps",
            details={"segment_id": segment_id},
        )
    words = tuple(
        _word_from_raw(word, provisional)
        for word in raw_words
    )
    previous: NormalizedWord | None = None
    for word in words:
        if previous is not None and (word.start < previous.start or word.end < previous.end):
            raise _invalid(
                "invalid_word_order",
                "word timestamps must remain in source order",
                details={"segment_id": segment_id},
            )
        previous = word
    return NormalizedSegment(
        id=provisional.id,
        start=provisional.start,
        end=provisional.end,
        text=provisional.text,
        words=words,
        avg_logprob=provisional.avg_logprob,
        no_speech_prob=provisional.no_speech_prob,
        compression_ratio=provisional.compression_ratio,
    )


def segment_from_dict(value: object, *, duration: float | None = None) -> NormalizedSegment:
    if not isinstance(value, Mapping):
        raise TranscriptError(
            "checkpoint_corrupt",
            "checkpoint segment is not an object",
            stage="persistence",
        )
    segment_id = value.get("id")
    if type(segment_id) is not int or segment_id < 0:
        raise TranscriptError(
            "checkpoint_corrupt",
            "checkpoint segment id is invalid",
            stage="persistence",
        )
    try:
        segment = normalize_segment(value, segment_id, duration=duration)
    except TranscriptError as exc:
        raise TranscriptError(
            "checkpoint_corrupt",
            f"checkpoint segment is invalid: {exc}",
            stage="persistence",
            details=exc.details,
        ) from exc
    if segment is None:
        raise TranscriptError(
            "checkpoint_corrupt",
            "checkpoint segment text is blank",
            stage="persistence",
        )
    return segment


def validate_segments(
    segments: Sequence[NormalizedSegment],
    *,
    duration: float | None = None,
    tolerance: float = TIMESTAMP_TOLERANCE_SECONDS,
) -> None:
    previous: NormalizedSegment | None = None
    for expected_id, segment in enumerate(segments):
        if segment.id != expected_id:
            raise TranscriptError(
                "segment_order_invalid",
                "segment identifiers must be unique and monotonically increasing",
                stage="finalizing",
                details={"expected_id": expected_id, "actual_id": segment.id},
            )
        if not math.isfinite(segment.start) or not math.isfinite(segment.end):
            raise TranscriptError(
                "invalid_timestamp",
                "segment timestamps must be finite",
                stage="finalizing",
            )
        if segment.start < 0 or segment.end <= segment.start:
            raise TranscriptError(
                "invalid_timestamp",
                "segment timestamps must be non-negative and ordered",
                stage="finalizing",
                details={"segment_id": segment.id},
            )
        if duration is not None and segment.end > duration + tolerance:
            raise TranscriptError(
                "timestamp_out_of_range",
                "segment timestamp exceeds the known media duration",
                stage="finalizing",
                details={"segment_id": segment.id, "duration_seconds": duration},
            )
        if previous is not None and (segment.start < previous.start or segment.end < previous.end):
            raise TranscriptError(
                "segment_order_invalid",
                "segment timestamps must remain in source order",
                stage="finalizing",
                details={"segment_id": segment.id},
            )
        previous_word: NormalizedWord | None = None
        for word in segment.words:
            if word.start < segment.start - tolerance or word.end > segment.end + tolerance:
                raise TranscriptError(
                    "invalid_word_timestamp",
                    "word timestamps must remain within the parent segment",
                    stage="finalizing",
                    details={"segment_id": segment.id},
                )
            if previous_word is not None and (word.start < previous_word.start or word.end < previous_word.end):
                raise TranscriptError(
                    "invalid_word_order",
                    "word timestamps must remain in source order",
                    stage="finalizing",
                    details={"segment_id": segment.id},
                )
            previous_word = word
        previous = segment


def language_from_info(info: object, requested: str | None) -> dict[str, object]:
    detected = get_value(info, "language")
    if not isinstance(detected, str) or not detected.strip():
        detected_code: str | None = None
    else:
        detected_code = detected.strip().casefold().replace("_", "-")
    probability = get_value(info, "language_probability")
    try:
        probability_value = optional_number(probability, "language probability")
    except TranscriptError:
        probability_value = None
    if probability_value is not None and not 0 <= probability_value <= 1:
        probability_value = None
    if requested:
        return {
            "code": requested,
            "source": "explicit",
            "probability": probability_value,
        }
    return {
        "code": detected_code,
        "source": "detected",
        "probability": probability_value,
    }


__all__ = [
    "NormalizedSegment",
    "NormalizedWord",
    "language_from_info",
    "normalize_segment",
    "segment_from_dict",
    "validate_segments",
]
