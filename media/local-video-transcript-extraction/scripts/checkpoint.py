"""Append-only checkpoint journal with explicit resume compatibility."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


try:
    from .common import (
        SCHEMA_VERSION,
        TranscriptError,
        append_jsonl,
        atomic_write_text,
        iso_utc,
        safe_text,
    )
    from .normalize import NormalizedSegment, segment_from_dict
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        SCHEMA_VERSION,
        TranscriptError,
        append_jsonl,
        atomic_write_text,
        iso_utc,
        safe_text,
    )
    from normalize import NormalizedSegment, segment_from_dict  # type: ignore


@dataclass(frozen=True)
class CheckpointSnapshot:
    header: dict[str, object]
    source: dict[str, object]
    language: dict[str, object] | None
    segments: tuple[NormalizedSegment, ...]
    progress: dict[str, object]
    status: str
    error: dict[str, object] | None


class Checkpoint:
    """The in-memory view of an append-only JSONL checkpoint."""

    def __init__(
        self,
        path: Path,
        header: Mapping[str, object],
        *,
        retain_segments: bool = True,
    ) -> None:
        self.path = Path(path)
        self.header = dict(header)
        self.retain_segments = retain_segments
        self.source: dict[str, object] = dict(header.get("source", {})) if isinstance(header.get("source"), Mapping) else {}
        self.language: dict[str, object] | None = None
        self.segments: list[NormalizedSegment] = []
        self.segment_count = 0
        self.last_segment: NormalizedSegment | None = None
        self.progress: dict[str, object] = {
            "last_durable_media_timestamp": 0.0,
            "last_durable_segment_id": None,
            "completed_segment_count": 0,
            "elapsed_seconds": 0.0,
            "last_checkpoint_at": iso_utc(),
        }
        self.status = str(header.get("status", "running"))
        self.error: dict[str, object] | None = None
        self.recovered_trailing_record = False

    @classmethod
    def create(
        cls,
        path: Path,
        header: Mapping[str, object],
        *,
        retain_segments: bool = True,
    ) -> "Checkpoint":
        target = Path(path)
        record = {"record_type": "header", **dict(header)}
        try:
            encoded = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        except (TypeError, ValueError) as exc:
            raise TranscriptError(
                "checkpoint_write_failed",
                f"could not serialize checkpoint header: {safe_text(exc)}",
                stage="persistence",
            ) from exc
        atomic_write_text(target, encoded)
        checkpoint = cls(target, record, retain_segments=retain_segments)
        checkpoint._read_back_header()
        return checkpoint

    @classmethod
    def load(
        cls,
        path: Path,
        *,
        retain_segments: bool = True,
    ) -> "Checkpoint":
        target = Path(path)
        try:
            if not target.is_file() or target.is_symlink():
                raise TranscriptError(
                    "checkpoint_missing",
                    "checkpoint file does not exist",
                    stage="persistence",
                    details={"path": str(target)},
                )
            if target.stat().st_size > 128 * 1024 * 1024:
                raise TranscriptError(
                    "checkpoint_too_large",
                    "checkpoint file is too large to read",
                    stage="persistence",
                    details={"path": str(target)},
                )
            repair_offset: int | None = None
            append_separator = False
            with target.open("r", encoding="utf-8") as stream:
                first_line = stream.readline()
                if not first_line:
                    raise TranscriptError("checkpoint_corrupt", "checkpoint is empty", stage="persistence")
                try:
                    first = json.loads(first_line)
                except (json.JSONDecodeError, TypeError) as exc:
                    raise TranscriptError(
                        "checkpoint_corrupt",
                        "checkpoint header is not valid JSON",
                        stage="persistence",
                    ) from exc
                if not isinstance(first, Mapping) or first.get("record_type") != "header":
                    raise TranscriptError("checkpoint_corrupt", "checkpoint has no header record", stage="persistence")
                header = dict(first)
                if header.get("schema_version") != SCHEMA_VERSION:
                    raise TranscriptError(
                        "checkpoint_incompatible",
                        "checkpoint schema version is not supported",
                        stage="persistence",
                        details={"schema_version": header.get("schema_version")},
                    )
                checkpoint = cls(target, header, retain_segments=retain_segments)
                if not first_line.endswith("\n"):
                    append_separator = True
                line_number = 1
                while True:
                    line_offset = stream.tell()
                    line = stream.readline()
                    if not line:
                        break
                    line_number += 1
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except (json.JSONDecodeError, TypeError) as exc:
                        if not line.endswith("\n"):
                            # A process interruption can leave only the final
                            # append without its terminating newline. Earlier
                            # fsynced records remain the durable checkpoint.
                            repair_offset = line_offset
                            checkpoint.recovered_trailing_record = True
                            break
                        raise TranscriptError(
                            "checkpoint_corrupt",
                            f"checkpoint record {line_number} is not valid JSON",
                            stage="persistence",
                        ) from exc
                    if not isinstance(record, Mapping):
                        raise TranscriptError(
                            "checkpoint_corrupt",
                            f"checkpoint record {line_number} is not an object",
                            stage="persistence",
                        )
                    checkpoint._apply_record(record, line_number=line_number)
                    if not line.endswith("\n"):
                        append_separator = True
            if repair_offset is not None:
                # Use the same text wrapper for the opaque tell/seek cookie;
                # UTF-8 transcript text must not be truncated by a guessed byte
                # offset.
                with target.open("r+", encoding="utf-8", newline="") as repair:
                    repair.seek(repair_offset)
                    repair.truncate()
                    repair.flush()
                    os.fsync(repair.fileno())
            elif append_separator:
                with target.open("a", encoding="utf-8", newline="\n") as repair:
                    repair.write("\n")
                    repair.flush()
                    os.fsync(repair.fileno())
        except TranscriptError:
            raise
        except (OSError, UnicodeError) as exc:
            raise TranscriptError(
                "checkpoint_read_failed",
                f"could not read checkpoint: {safe_text(exc)}",
                stage="persistence",
                details={"path": str(target)},
            ) from exc
        checkpoint._normalize_loaded_state()
        checkpoint._read_back_header()
        return checkpoint

    def _read_back_header(self) -> None:
        try:
            with self.path.open("r", encoding="utf-8") as stream:
                first_line = stream.readline()
            value = json.loads(first_line)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TranscriptError(
                "checkpoint_read_failed",
                f"checkpoint read-back failed: {safe_text(exc)}",
                stage="persistence",
                details={"path": str(self.path)},
            ) from exc
        if not isinstance(value, Mapping) or value.get("record_type") != "header":
            raise TranscriptError(
                "checkpoint_corrupt",
                "checkpoint read-back did not contain its header",
                stage="persistence",
            )

    def _apply_record(self, record: Mapping[str, object], *, line_number: int) -> None:
        record_type = record.get("record_type")
        if record_type == "source":
            value = record.get("source")
            if not isinstance(value, Mapping):
                raise TranscriptError(
                    "checkpoint_corrupt",
                    f"checkpoint source record {line_number} is invalid",
                    stage="persistence",
                )
            self.source = dict(value)
            return
        if record_type == "language":
            value = record.get("language")
            if not isinstance(value, Mapping):
                raise TranscriptError(
                    "checkpoint_corrupt",
                    f"checkpoint language record {line_number} is invalid",
                    stage="persistence",
                )
            self.language = dict(value)
            return
        if record_type == "truncate":
            keep_count = record.get("keep_count")
            if type(keep_count) is not int or keep_count < 0 or keep_count > self.segment_count:
                raise TranscriptError(
                    "checkpoint_corrupt",
                    f"checkpoint truncate record {line_number} is invalid",
                    stage="persistence",
                )
            if self.retain_segments:
                self.segments = self.segments[:keep_count]
            self.segment_count = keep_count
            last_value = record.get("last_segment")
            if isinstance(last_value, Mapping):
                self.last_segment = segment_from_dict(last_value)
                if self.last_segment.id != keep_count - 1:
                    raise TranscriptError(
                        "checkpoint_corrupt",
                        f"checkpoint truncate record {line_number} has an invalid last segment",
                        stage="persistence",
                    )
            elif keep_count == 0:
                self.last_segment = None
            elif self.retain_segments and self.segments:
                self.last_segment = self.segments[-1]
            else:
                self.last_segment = None
            timestamp = record.get("last_durable_media_timestamp")
            if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
                self.progress["last_durable_media_timestamp"] = float(timestamp)
            self.progress["completed_segment_count"] = self.segment_count
            self.progress["last_durable_segment_id"] = self.last_segment.id if self.last_segment else None
            self.progress["last_checkpoint_at"] = record.get("at", iso_utc())
            return
        if record_type == "segment":
            value = record.get("segment")
            try:
                segment = segment_from_dict(value)
            except TranscriptError as exc:
                raise TranscriptError(
                    "checkpoint_corrupt",
                    f"checkpoint segment record {line_number} is invalid: {exc}",
                    stage="persistence",
                    details=exc.details,
                ) from exc
            if segment.id != self.segment_count:
                raise TranscriptError(
                    "checkpoint_corrupt",
                    f"checkpoint segment record {line_number} is not contiguous",
                    stage="persistence",
                )
            if self.retain_segments:
                self.segments.append(segment)
            self.segment_count += 1
            self.last_segment = segment
            return
        if record_type == "progress":
            value = record.get("progress")
            if not isinstance(value, Mapping):
                raise TranscriptError(
                    "checkpoint_corrupt",
                    f"checkpoint progress record {line_number} is invalid",
                    stage="persistence",
                )
            self.progress = dict(value)
            return
        if record_type == "status":
            status = record.get("status")
            if not isinstance(status, str) or not status:
                raise TranscriptError(
                    "checkpoint_corrupt",
                    f"checkpoint status record {line_number} is invalid",
                    stage="persistence",
                )
            self.status = status
            error = record.get("error")
            self.error = dict(error) if isinstance(error, Mapping) else None
            return
        # Unknown records are retained in the file and ignored for forward
        # compatibility; all records that affect recovery are explicit above.

    def _normalize_loaded_state(self) -> None:
        if self.retain_segments:
            self.segment_count = len(self.segments)
            self.last_segment = self.segments[-1] if self.segments else None
        self.progress["completed_segment_count"] = self.segment_count
        self.progress["last_durable_segment_id"] = self.last_segment.id if self.last_segment else None
        value = self.progress.get("last_durable_media_timestamp", 0.0)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            value = self.last_segment.end if self.last_segment else 0.0
        segment_timestamp = self.last_segment.end if self.last_segment else 0.0
        self.progress["last_durable_media_timestamp"] = max(float(value), segment_timestamp)
        self.progress.setdefault("elapsed_seconds", 0.0)
        self.progress.setdefault("last_checkpoint_at", iso_utc())

    def _append(self, record: Mapping[str, object]) -> None:
        append_jsonl(self.path, record)

    def append_source(self, source: Mapping[str, object]) -> None:
        record = {"record_type": "source", "source": dict(source), "at": iso_utc()}
        self._append(record)
        self.source = dict(source)

    def append_language(self, language: Mapping[str, object]) -> None:
        record = {"record_type": "language", "language": dict(language), "at": iso_utc()}
        self._append(record)
        self.language = dict(language)

    def append_truncate(
        self,
        keep_count: int,
        *,
        last_segment: NormalizedSegment | None = None,
    ) -> None:
        if type(keep_count) is not int or keep_count < 0 or keep_count > self.segment_count:
            raise TranscriptError(
                "checkpoint_write_failed",
                "checkpoint truncate count is invalid",
                stage="persistence",
            )
        if self.retain_segments:
            kept = self.segments[:keep_count]
        elif last_segment is not None:
            if keep_count == 0:
                kept = []
            elif last_segment.id == keep_count - 1:
                kept = [last_segment]
            else:
                raise TranscriptError(
                    "checkpoint_write_failed",
                    "provided truncate tail does not match the keep count",
                    stage="persistence",
                )
        elif keep_count == self.segment_count:
            kept = [self.last_segment] if self.last_segment is not None else []
        else:
            kept = list(self.read_segments())[:keep_count]
        if last_segment is not None and keep_count:
            expected_tail = kept[-1] if kept else None
            if expected_tail is not None and expected_tail != last_segment:
                raise TranscriptError(
                    "checkpoint_write_failed",
                    "provided truncate tail does not match retained segments",
                    stage="persistence",
                )
        kept_last = last_segment if keep_count and last_segment is not None else (kept[-1] if kept else None)
        timestamp = kept_last.end if kept_last else 0.0
        record = {
            "record_type": "truncate",
            "keep_count": keep_count,
            "last_segment": kept_last.as_dict() if kept_last else None,
            "last_durable_media_timestamp": timestamp,
            "at": iso_utc(),
        }
        self._append(record)
        if self.retain_segments:
            self.segments = kept
        self.segment_count = keep_count
        self.last_segment = kept_last
        self.progress.update(
            {
                "last_durable_media_timestamp": timestamp,
                "last_durable_segment_id": kept_last.id if kept_last else None,
                "completed_segment_count": keep_count,
                "last_checkpoint_at": record["at"],
            }
        )

    def append_segment(self, segment: NormalizedSegment) -> None:
        if segment.id != self.segment_count:
            raise TranscriptError(
                "checkpoint_write_failed",
                "segment id does not continue the durable checkpoint",
                stage="persistence",
                details={"expected_id": self.segment_count, "actual_id": segment.id},
            )
        record = {
            "record_type": "segment",
            "segment": segment.as_dict(),
            "at": iso_utc(),
        }
        self._append(record)
        if self.retain_segments:
            self.segments.append(segment)
        self.segment_count += 1
        self.last_segment = segment

    def append_progress(
        self,
        processed_timestamp: float,
        *,
        elapsed_seconds: float,
    ) -> None:
        at = iso_utc()
        record_progress: dict[str, object] = {
            "last_durable_media_timestamp": float(processed_timestamp),
            "last_durable_segment_id": self.last_segment.id if self.last_segment else None,
            "completed_segment_count": self.segment_count,
            "elapsed_seconds": max(0.0, float(elapsed_seconds)),
            "last_checkpoint_at": at,
        }
        self._append({"record_type": "progress", "progress": record_progress, "at": at})
        self.progress = record_progress

    def read_segments(self) -> tuple[NormalizedSegment, ...]:
        """Read the current journal view only when finalization/recovery needs it."""

        if self.retain_segments:
            return tuple(self.segments)
        loaded = Checkpoint.load(self.path, retain_segments=True)
        return tuple(loaded.segments)

    def release_segments(self) -> None:
        """Drop the in-memory transcript while retaining durable counters/tail."""

        self.segments.clear()
        self.retain_segments = False

    def append_status(
        self,
        status: str,
        *,
        error: Mapping[str, object] | None = None,
    ) -> None:
        record: dict[str, object] = {
            "record_type": "status",
            "status": status,
            "at": iso_utc(),
        }
        if error is not None:
            record["error"] = dict(error)
        self._append(record)
        self.status = status
        self.error = dict(error) if error is not None else None

    def snapshot(self) -> CheckpointSnapshot:
        return CheckpointSnapshot(
            header=dict(self.header),
            source=dict(self.source),
            language=dict(self.language) if self.language is not None else None,
            segments=self.read_segments(),
            progress=dict(self.progress),
            status=self.status,
            error=dict(self.error) if self.error is not None else None,
        )


def archive_artifact(path: Path) -> Path | None:
    """Move an old recovery artifact aside without overwriting history."""

    target = Path(path)
    if not target.exists():
        return None
    if target.is_symlink() or not target.is_file():
        raise TranscriptError(
            "checkpoint_corrupt",
            "existing recovery artifact is not a regular file",
            stage="persistence",
            details={"path": str(target)},
        )
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    for index in range(1, 1000):
        candidate = target.with_name(f"{target.stem}.previous-{stamp}-{index:03d}{target.suffix}")
        if candidate.exists():
            continue
        try:
            os.replace(target, candidate)
        except OSError as exc:
            raise TranscriptError(
                "checkpoint_write_failed",
                f"could not preserve the previous recovery artifact: {safe_text(exc)}",
                stage="persistence",
                details={"path": str(target)},
            ) from exc
        return candidate
    raise TranscriptError(
        "checkpoint_write_failed",
        "could not allocate a unique previous recovery artifact name",
        stage="persistence",
    )


def archive_checkpoint(path: Path) -> Path | None:
    """Move an old journal aside without overwriting another attempt."""

    return archive_artifact(path)


def resume_compatible(
    checkpoint: Checkpoint,
    expected_signature: Mapping[str, object],
) -> bool:
    actual = checkpoint.header.get("resume_signature")
    return isinstance(actual, Mapping) and dict(actual) == dict(expected_signature)


__all__ = [
    "Checkpoint",
    "CheckpointSnapshot",
    "archive_artifact",
    "archive_checkpoint",
    "resume_compatible",
]
