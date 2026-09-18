"""Periodic frame selection and timestamp-grounded frame extraction."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

try:
    from .common import DEFAULT_FRAME_INTERVAL, WatchVideoError, checked_timeout, format_timestamp
    from .media_assets import extract_frame
except ImportError:  # pragma: no cover
    from common import DEFAULT_FRAME_INTERVAL, WatchVideoError, checked_timeout, format_timestamp  # type: ignore
    from media_assets import extract_frame  # type: ignore


@dataclass
class FrameCandidate:
    timestamp: float
    signals: set[str] = field(default_factory=set)

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": round(self.timestamp, 6),
            "signals": sorted(self.signals),
        }


@dataclass(frozen=True)
class FrameSamplingResult:
    frames: tuple[dict[str, object], ...]
    candidates: tuple[FrameCandidate, ...]
    warnings: tuple[str, ...]
    alignment_status: str = "unavailable"
    aligned_frames: int = 0


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _bounds(
    duration: float,
    ranges: Sequence[tuple[float, float]] | None,
) -> tuple[tuple[float, float], ...]:
    if not math.isfinite(duration) or duration <= 0:
        raise WatchVideoError("frame sampling needs a positive finite video duration")
    if not ranges:
        return ((0.0, duration),)
    checked: list[tuple[float, float]] = []
    for start, end in ranges:
        if not all(math.isfinite(float(value)) for value in (start, end)):
            raise WatchVideoError("frame focus ranges must contain finite timestamps")
        left = max(0.0, min(duration, float(start)))
        right = max(0.0, min(duration, float(end)))
        if right > left:
            checked.append((left, right))
    if not checked:
        raise WatchVideoError("frame focus ranges do not intersect the video")
    return tuple(sorted(checked))


def _in_bounds(timestamp: float, bounds: Sequence[tuple[float, float]]) -> bool:
    return any(left - 1e-9 <= timestamp <= right + 1e-9 for left, right in bounds)


def _add_candidate(
    values: list[FrameCandidate],
    timestamp: object,
    signal: str,
    bounds: Sequence[tuple[float, float]],
) -> None:
    number = _number(timestamp)
    if number is None or not _in_bounds(number, bounds):
        return
    for existing in values:
        if abs(existing.timestamp - number) <= 1e-9:
            existing.signals.add(signal)
            return
    values.append(FrameCandidate(timestamp=number, signals={signal}))


def _value(item: object, *names: str) -> float | None:
    if isinstance(item, Mapping):
        for name in names:
            value = _number(item.get(name))
            if value is not None:
                return value
    else:
        for name in names:
            value = _number(getattr(item, name, None))
            if value is not None:
                return value
    return None


def _nearby_speech(
    timestamp: float,
    transcript: Sequence[object],
    *,
    max_gap: float = 15.0,
) -> list[dict[str, object]]:
    """Return the closest timestamped speech interval for agent verification."""

    matches: list[tuple[float, int, float, float]] = []
    for index, item in enumerate(transcript, start=1):
        start = _value(item, "start")
        end = _value(item, "end")
        if start is None or end is None or end <= start:
            continue
        if timestamp < start:
            distance = start - timestamp
        elif timestamp > end:
            distance = timestamp - end
        else:
            distance = 0.0
        if distance <= max_gap:
            matches.append((distance, index, start, end))
    if not matches:
        return []
    matches.sort(key=lambda value: (value[0], value[2], value[1]))
    return [
        {
            "id": f"speech-{index:04d}",
            "start": round(start, 3),
            "end": round(end, 3),
            "distance": round(distance, 3),
        }
        for distance, index, start, end in matches[:1]
    ]


def _validate_frame_interval(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WatchVideoError("frame_interval must be a finite positive number")
    interval = float(value)
    if not math.isfinite(interval) or interval <= 0:
        raise WatchVideoError("frame_interval must be a finite positive number")
    return interval


def select_timestamps(
    duration: float,
    *,
    requested_times: Sequence[float] = (),
    focus_ranges: Sequence[tuple[float, float]] | None = None,
    frame_interval: float = DEFAULT_FRAME_INTERVAL,
) -> tuple[FrameCandidate, ...]:
    """Generate every periodic frame timestamp plus explicit requests."""

    interval = _validate_frame_interval(frame_interval)
    bounds = _bounds(float(duration), focus_ranges)
    candidates: list[FrameCandidate] = []
    for left, right in bounds:
        # Keep the schedule anchored at each range start. The explicit end
        # candidate preserves coverage when the interval does not divide it.
        steps = int(math.floor((right - left) / interval + 1e-9))
        for index in range(steps + 1):
            timestamp = left + index * interval
            if timestamp > right + 1e-9:
                break
            _add_candidate(candidates, timestamp, "interval", bounds)
        _add_candidate(candidates, right, "range-boundary", bounds)
    for timestamp in requested_times:
        _add_candidate(candidates, timestamp, "requested", bounds)

    # Seeking exactly at container duration is commonly EOF rather than the
    # final decodable frame. Preserve the boundary signal but move it into a
    # small last-frame neighborhood before invoking FFmpeg.
    safe_endpoint = max(0.0, float(duration) - min(0.05, float(duration) * 0.1))
    adjusted: list[FrameCandidate] = []
    for candidate in sorted(candidates, key=lambda item: item.timestamp):
        if abs(candidate.timestamp - float(duration)) <= 1e-9:
            candidate.timestamp = safe_endpoint
            candidate.signals.add("end-near-boundary")
        duplicate = next(
            (item for item in adjusted if abs(item.timestamp - candidate.timestamp) <= 1e-9),
            None,
        )
        if duplicate is not None:
            duplicate.signals.update(candidate.signals)
        else:
            adjusted.append(candidate)
    return tuple(adjusted)


def sample_frames(
    video: Path,
    destination: Path,
    duration: float,
    *,
    transcript: Sequence[object] = (),
    requested_times: Sequence[float] = (),
    focus_ranges: Sequence[tuple[float, float]] | None = None,
    frame_interval: float = DEFAULT_FRAME_INTERVAL,
    ffmpeg: str | None = None,
    timeout: float = 300.0,
    runner=None,
) -> FrameSamplingResult:
    """Extract every periodic frame and keep timestamp/alignment failures visible."""

    output_dir = Path(destination)
    output_dir.mkdir(parents=True, exist_ok=True)
    _bounds(float(duration), focus_ranges)
    warnings: list[str] = []
    if focus_ranges:
        for start, end in focus_ranges:
            if float(start) < 0 or float(end) > float(duration):
                warnings.append(
                    f"focus range {format_timestamp(max(0.0, float(start)))}-"
                    f"{format_timestamp(max(0.0, float(end)))} was clipped to the video bounds"
                )
    for requested in requested_times:
        number = _number(requested)
        if number is None or number < 0 or number > float(duration):
            warnings.append(f"requested frame timestamp {requested!r} is outside the video duration and was ignored")
        elif abs(number - float(duration)) <= 1e-9:
            warnings.append(f"requested frame timestamp {requested!r} was moved just before EOF for decodable evidence")
    candidates = select_timestamps(
        duration,
        requested_times=requested_times,
        focus_ranges=focus_ranges,
        frame_interval=frame_interval,
    )
    frames: list[dict[str, object]] = []
    aligned_frames = 0
    for index, candidate in enumerate(candidates, start=1):
        name = f"{index:06d}-frame-{int(round(candidate.timestamp * 1_000_000)):015d}.jpg"
        path = output_dir / name
        try:
            extract_frame(
                Path(video),
                candidate.timestamp,
                path,
                ffmpeg=ffmpeg,
                timeout=checked_timeout(timeout, "frame extraction timeout"),
                runner=runner,
            )
        except WatchVideoError as exc:
            warnings.append(f"frame at {format_timestamp(candidate.timestamp)} was not extracted: {exc}")
            continue
        nearby_speech = _nearby_speech(candidate.timestamp, transcript)
        if nearby_speech:
            aligned_frames += 1
        frames.append({
            "timestamp": round(candidate.timestamp, 6),
            "path": str(path),
            "signals": sorted(candidate.signals),
            "speech_interval_ids": [item["id"] for item in nearby_speech],
            "nearby_speech_intervals": nearby_speech,
        })
    if candidates and not frames:
        warnings.append("no selected frame could be materialized")
    if not transcript:
        alignment_status = "unavailable"
    elif not frames:
        alignment_status = "unavailable"
    elif aligned_frames == len(frames):
        alignment_status = "aligned"
    else:
        alignment_status = "partial"
        warnings.append(
            f"visual/transcript alignment attached nearby speech to {aligned_frames} of {len(frames)} frames"
        )
    return FrameSamplingResult(
        frames=tuple(frames),
        candidates=tuple(candidates),
        warnings=tuple(warnings),
        alignment_status=alignment_status,
        aligned_frames=aligned_frames,
    )


__all__ = [
    "FrameCandidate",
    "FrameSamplingResult",
    "sample_frames",
    "select_timestamps",
]
