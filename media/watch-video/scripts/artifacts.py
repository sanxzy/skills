"""Workspace-local, historically traceable artifact layout for watch-video."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

try:
    from .common import (
        WatchVideoError,
        ensure_directory,
        owned_path,
        safe_filename,
        short_hash,
        workspace_root,
    )
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        WatchVideoError,
        ensure_directory,
        owned_path,
        safe_filename,
        short_hash,
        workspace_root,
    )


_ATTEMPT_RE = re.compile(r"^(\d+)-attempt(?:-|$)")
_TASK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


@dataclass(frozen=True)
class TaskRun:
    """One immutable attempt namespace below a user-visible task directory."""

    workspace: Path
    task_name: str
    task_directory: Path
    attempt_directory: Path
    process_directory: Path
    state_path: Path
    events_path: Path
    metadata_path: Path
    transcript_path: Path
    transcript_markdown_path: Path
    transcript_source_path: Path
    timeline_path: Path
    frames_directory: Path
    context_path: Path

    def display(self, path: Path) -> str:
        """Return a workspace-relative path, never a `/tmp`/`/private` path."""

        target = Path(path)
        try:
            return target.resolve(strict=False).relative_to(self.workspace.resolve()).as_posix()
        except (OSError, ValueError) as exc:
            raise WatchVideoError(f"Artifact is outside the active workspace: {target}") from exc

    @property
    def attempt_name(self) -> str:
        return self.attempt_directory.name

    @property
    def task_path(self) -> str:
        return self.display(self.task_directory)

    def artifact_paths(self) -> dict[str, str]:
        return {
            "task_directory": self.display(self.task_directory),
            "attempt_directory": self.display(self.attempt_directory),
            "state": self.display(self.state_path),
            "progress": self.display(self.events_path),
        }


def normalize_task_name(
    normalized_url: str,
    intent: str | None = None,
    supplied: str | None = None,
) -> str:
    """Create a stable, user-readable directory name without path traversal."""

    if supplied is not None:
        value = str(supplied).strip()
        if not value:
            raise WatchVideoError("task name must not be blank")
        candidate = safe_filename(value, fallback="watch-video")
    else:
        # Keep the default task directory stable across different questions
        # about the same URL so the task-scoped semantic cache remains useful.
        candidate = f"video-{short_hash(normalized_url, 12)}"
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip(".-")
    if not candidate:
        candidate = f"video-{short_hash(normalized_url, 12)}"
    if not _TASK_RE.fullmatch(candidate):
        candidate = candidate[:80].rstrip(".-")
    if not candidate or not _TASK_RE.fullmatch(candidate):
        raise WatchVideoError("task name could not be normalized into a safe directory name")
    return candidate


def _next_attempt_number(task_directory: Path) -> int:
    highest = 0
    for child in task_directory.iterdir():
        if not child.is_dir() or child.is_symlink():
            continue
        match = _ATTEMPT_RE.match(child.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def create_task_run(
    workspace: str | Path,
    normalized_url: str,
    *,
    intent: str | None = None,
    task_name: str | None = None,
) -> TaskRun:
    """Create a new numeric attempt without overwriting historical attempts."""

    root = workspace_root(workspace)
    name = normalize_task_name(normalized_url, intent, task_name)
    task_directory = owned_path(root, ".artifacts", "watch-video", name)
    ensure_directory(task_directory)
    sequence = _next_attempt_number(task_directory)
    while True:
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        attempt_name = f"{sequence:03d}-attempt-{stamp}-{short_hash(normalized_url, 8)}"
        attempt_directory = task_directory / attempt_name
        try:
            attempt_directory.mkdir(parents=False, exist_ok=False)
            break
        except FileExistsError:
            sequence += 1
    process_directory = attempt_directory / "009-process-media"
    frames_directory = attempt_directory / "006-frames"
    ensure_directory(process_directory)
    # The remaining files use fixed numeric prefixes so a directory listing is
    # a readable chronological contract even when a stage is skipped.
    return TaskRun(
        workspace=root,
        task_name=name,
        task_directory=task_directory,
        attempt_directory=attempt_directory,
        process_directory=process_directory,
        state_path=attempt_directory / "001-state.json",
        events_path=attempt_directory / "002-events.jsonl",
        metadata_path=attempt_directory / "003-metadata.json",
        transcript_path=attempt_directory / "004-transcript.json",
        transcript_markdown_path=attempt_directory / "004-transcript.md",
        transcript_source_path=attempt_directory / "004-transcript-source.json",
        timeline_path=attempt_directory / "005-timeline.json",
        frames_directory=frames_directory,
        context_path=attempt_directory / "007-context.json",
    )


__all__ = ["TaskRun", "create_task_run", "normalize_task_name"]
