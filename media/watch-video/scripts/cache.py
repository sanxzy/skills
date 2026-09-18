"""Workspace-local semantic cache with traceable numeric artifact names.

A cache belongs to one user-visible task directory. It never stores raw
media or signed provider URLs; published JSON, transcript Markdown, and frame
files are staged and read back before the cache index is updated.
"""

from __future__ import annotations

import os
import re
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:
    from .common import (
        WatchVideoError,
        atomic_write_json,
        ensure_directory,
        normalize_url,
        owned_path,
        read_json,
        short_hash,
        workspace_root,
    )
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        WatchVideoError,
        atomic_write_json,
        ensure_directory,
        normalize_url,
        owned_path,
        read_json,
        short_hash,
        workspace_root,
    )


CACHE_VERSION = 3
_ENTRY_RE = re.compile(r"^(\d+)-entry-([0-9a-f]{24})$")
DEFAULT_CACHE_PROFILE = "best-effort-v1"


@dataclass(frozen=True)
class CacheHit:
    key: str
    directory: Path
    context: Mapping[str, Any]


def _replace_paths(value: object, old: str, new: str) -> object:
    if isinstance(value, str):
        if value == old:
            return new
        if value.startswith(old + "/") or value.startswith(old + os.sep):
            return new + value[len(old):]
        return value
    if isinstance(value, list):
        return [_replace_paths(item, old, new) for item in value]
    if isinstance(value, tuple):
        return tuple(_replace_paths(item, old, new) for item in value)
    if isinstance(value, dict):
        return {key: _replace_paths(item, old, new) for key, item in value.items()}
    return value


def _regular_file(path: Path) -> bool:
    try:
        return path.is_file() and not path.is_symlink() and path.stat().st_size > 0
    except OSError:
        return False


class CacheStore:
    """A task-scoped atomic cache indexed by normalized URL and identity."""

    def __init__(
        self,
        workspace: str | Path,
        *,
        task_directory: str | Path | None = None,
    ) -> None:
        self.workspace = workspace_root(workspace)
        if task_directory is None:
            task_directory = owned_path(
                self.workspace,
                ".artifacts",
                "watch-video",
                "default-task",
            )
        else:
            task_directory = Path(task_directory)
            try:
                if not task_directory.resolve(strict=False).is_relative_to(self.workspace):
                    raise WatchVideoError("cache task directory must stay inside the workspace")
            except OSError as exc:
                raise WatchVideoError("cache task directory could not be validated") from exc
        self.task_directory = ensure_directory(Path(task_directory))
        self.root = ensure_directory(self.task_directory / "000-cache")
        self.index_path = self.root / "000-index.json"
        self.last_error: str | None = None

    def _display(self, path: Path) -> str:
        try:
            return Path(path).resolve(strict=False).relative_to(self.workspace.resolve()).as_posix()
        except (OSError, ValueError) as exc:
            raise WatchVideoError(f"Cache artifact is outside the workspace: {path}") from exc

    def _resolve_artifact(self, value: object) -> Path | None:
        if not isinstance(value, str) or not value:
            return None
        path = Path(value)
        return path if path.is_absolute() else self.workspace / path

    def _inside(self, path: Path, directory: Path) -> bool:
        try:
            return path.resolve(strict=False).is_relative_to(directory.resolve())
        except OSError:
            return False

    def _index(self) -> dict[str, Any]:
        empty = {"version": CACHE_VERSION, "urls": {}, "identities": {}, "entries": {}}
        if not self.index_path.exists():
            return empty
        try:
            value = read_json(self.index_path)
        except WatchVideoError:
            return empty
        if not isinstance(value, dict) or value.get("version") != CACHE_VERSION:
            return empty
        return {
            "version": CACHE_VERSION,
            "urls": dict(value.get("urls")) if isinstance(value.get("urls"), dict) else {},
            "identities": dict(value.get("identities")) if isinstance(value.get("identities"), dict) else {},
            "entries": dict(value.get("entries")) if isinstance(value.get("entries"), dict) else {},
        }

    @staticmethod
    def identity(
        url: str,
        source: Mapping[str, Any] | None = None,
        *,
        profile: str = DEFAULT_CACHE_PROFILE,
    ) -> str:
        normalized = normalize_url(url)
        platform = source.get("platform") if isinstance(source, Mapping) else None
        video_id = source.get("id") if isinstance(source, Mapping) else None
        if isinstance(platform, str) and isinstance(video_id, str) and platform and video_id:
            base = f"id:{platform.casefold()}:{video_id}"
        else:
            base = f"url:{normalized}"
        return f"{base}|profile:{profile}"

    @staticmethod
    def _url_index_key(url: str, profile: str) -> str:
        return f"{normalize_url(url)}|profile:{profile}"

    def _entry_name(self, key: str, index: Mapping[str, Any], *, allocate: bool = False) -> str | None:
        entries = index.get("entries")
        existing = entries.get(key) if isinstance(entries, Mapping) else None
        if isinstance(existing, str) and _ENTRY_RE.fullmatch(existing):
            return existing
        if not allocate:
            return None
        highest = 0
        for child in self.root.iterdir():
            if not child.is_dir() or child.is_symlink():
                continue
            match = _ENTRY_RE.match(child.name)
            if match:
                highest = max(highest, int(match.group(1)))
        return f"{highest + 1:03d}-entry-{key}"

    def _entry(self, key: str, index: Mapping[str, Any], *, allocate: bool = False) -> Path | None:
        if not re.fullmatch(r"[0-9a-f]{24}", key):
            return None
        name = self._entry_name(key, index, allocate=allocate)
        return self.root / name if name else None

    def lookup(
        self,
        url: str,
        *,
        needs_visual: bool = False,
        profile: str = DEFAULT_CACHE_PROFILE,
    ) -> CacheHit | None:
        normalized = normalize_url(url)
        index = self._index()
        identity_key = self.identity(normalized, profile=profile)
        url_key = self._url_index_key(normalized, profile)
        key = index["urls"].get(url_key) or index["identities"].get(identity_key)
        if not isinstance(key, str):
            return None
        directory = self._entry(key, index)
        if directory is None:
            return None
        context_path = directory / "007-context.json"
        manifest_path = directory / "000-manifest.json"
        if not _regular_file(context_path) or not _regular_file(manifest_path):
            return None
        try:
            context = read_json(context_path)
            manifest = read_json(manifest_path)
        except WatchVideoError:
            return None
        if not isinstance(context, dict) or not isinstance(manifest, dict):
            return None
        if context.get("status") != "complete":
            return None
        if context.get("extraction_status", "complete") != "complete":
            return None
        if (
            manifest.get("version") != CACHE_VERSION
            or manifest.get("source_url") != normalized
            or manifest.get("key") != key
        ):
            return None
        if manifest.get("profile") != profile:
            return None
        source = context.get("source")
        if not isinstance(source, dict) or source.get("url") != normalized:
            return None
        artifacts = context.get("artifacts")
        if not isinstance(artifacts, dict):
            return None
        for name in ("metadata", "timeline"):
            artifact_path = self._resolve_artifact(artifacts.get(name))
            if artifact_path is None or not self._inside(artifact_path, directory) or not _regular_file(artifact_path):
                return None
        content = context.get("content")
        if not isinstance(content, dict) or content.get("transcript_policy") != "best-effort":
            return None
        transcript_available = content.get("transcript_available") is True
        if transcript_available:
            transcript_path = self._resolve_artifact(artifacts.get("transcript"))
            if transcript_path is None or not self._inside(transcript_path, directory) or not _regular_file(transcript_path):
                return None
            transcript_markdown_path = self._resolve_artifact(artifacts.get("transcript_markdown"))
            if (
                transcript_markdown_path is None
                or not self._inside(transcript_markdown_path, directory)
                or not _regular_file(transcript_markdown_path)
            ):
                return None
            if isinstance(content, dict) and content.get("transcript_translation_performed") is True:
                original_path = self._resolve_artifact(artifacts.get("transcript_original"))
                if original_path is None or not self._inside(original_path, directory) or not _regular_file(original_path):
                    return None
        if needs_visual:
            frames = artifacts.get("frames", [])
            if not isinstance(frames, list) or not frames:
                return None
            if transcript_available:
                alignment = content.get("visual_transcript_alignment")
                if not isinstance(alignment, dict) or alignment.get("status") not in {"aligned", "partial"}:
                    return None
            for item in frames:
                if not isinstance(item, dict):
                    return None
                frame_path = self._resolve_artifact(item.get("path"))
                if frame_path is None or not self._inside(frame_path, directory) or not _regular_file(frame_path):
                    return None
                if transcript_available:
                    if not isinstance(item.get("speech_interval_ids"), list) or not isinstance(item.get("nearby_speech_intervals"), list):
                        return None
        return CacheHit(key=key, directory=directory, context=context)

    def store(
        self,
        url: str,
        source: Mapping[str, Any],
        run_directory: Path,
        *,
        artifact_files: Mapping[str, Path] | None = None,
        profile: str = DEFAULT_CACHE_PROFILE,
    ) -> CacheHit | None:
        """Publish one complete semantic attempt atomically."""

        self.last_error = None
        normalized = normalize_url(url)
        run_dir = Path(run_directory)
        files = {
            "context": run_dir / "007-context.json",
            "metadata": run_dir / "003-metadata.json",
            "timeline": run_dir / "005-timeline.json",
            "transcript": run_dir / "004-transcript.json",
            "transcript_markdown": run_dir / "004-transcript.md",
            "transcript_original": run_dir / "004-transcript-source.json",
            "frames": run_dir / "006-frames",
        }
        if artifact_files:
            files.update({key: Path(value) for key, value in artifact_files.items()})
        required = (files["context"], files["metadata"], files["timeline"])
        if not all(_regular_file(path) for path in required):
            self.last_error = "required semantic artifacts are missing"
            return None
        try:
            context_before = read_json(files["context"])
        except WatchVideoError as exc:
            self.last_error = str(exc)
            return None
        if not isinstance(context_before, dict) or context_before.get("status") != "complete":
            self.last_error = "only complete extraction contexts are eligible for cache publication"
            return None
        if context_before.get("extraction_status", "complete") != "complete":
            self.last_error = "only complete extraction contexts are eligible for cache publication"
            return None
        content_before = context_before.get("content")
        if not isinstance(content_before, dict) or content_before.get("transcript_policy") != "best-effort":
            self.last_error = "cache context does not declare the supported transcript policy"
            return None
        if content_before.get("transcript_available") is True:
            if not _regular_file(files["transcript"]):
                self.last_error = "cache context declares a transcript but its artifact is missing"
                return None
            if not _regular_file(files["transcript_markdown"]):
                self.last_error = "cache context declares a transcript but its Markdown artifact is missing"
                return None
        if content_before.get("transcript_translation_performed") is True and not _regular_file(files["transcript_original"]):
            self.last_error = "cache context declares a translation but its source artifact is missing"
            return None
        if content_before.get("visual_analysis_required") is True:
            frames = context_before.get("artifacts", {}).get("frames") if isinstance(context_before.get("artifacts"), dict) else None
            if not isinstance(frames, list) or not frames:
                self.last_error = "cache context declares visual analysis but has no frame evidence"
                return None
        identity = self.identity(normalized, source, profile=profile)
        key = short_hash(identity)
        index = self._index()
        target = self._entry(key, index, allocate=True)
        if target is None:
            return None
        temporary = self.root / f"000-tmp-{uuid.uuid4().hex}"
        backup = self.root / f"000-old-{uuid.uuid4().hex}"
        try:
            ensure_directory(temporary)
            copy_paths = {
                "context": temporary / "007-context.json",
                "metadata": temporary / "003-metadata.json",
                "timeline": temporary / "005-timeline.json",
                "transcript": temporary / "004-transcript.json",
                "transcript_markdown": temporary / "004-transcript.md",
                "transcript_original": temporary / "004-transcript-source.json",
            }
            for name, destination in copy_paths.items():
                source_path = files[name]
                if _regular_file(source_path):
                    shutil.copy2(source_path, destination)
            frame_source = files["frames"]
            if frame_source.is_dir() and not frame_source.is_symlink():
                frame_destination = temporary / "006-frames"
                ensure_directory(frame_destination)
                for child in frame_source.iterdir():
                    if _regular_file(child):
                        shutil.copy2(child, frame_destination / child.name)
            context = read_json(copy_paths["context"])
            if not isinstance(context, dict):
                raise WatchVideoError("run context is not a JSON object")
            old_display = self._display(run_dir)
            new_display = self._display(target)
            context = _replace_paths(context, old_display, new_display)
            old_absolute = str(run_dir.resolve(strict=False))
            context = _replace_paths(context, old_absolute, new_display)
            atomic_write_json(copy_paths["context"], context)
            atomic_write_json(temporary / "000-manifest.json", {
                "version": CACHE_VERSION,
                "key": key,
                "identity": identity,
                "profile": profile,
                "source_url": normalized,
                "stored_at": time.time(),
            })
            if target.exists():
                if target.is_symlink():
                    raise WatchVideoError("cache entry is a symlink")
                target.rename(backup)
            temporary.rename(target)
            if backup.exists():
                shutil.rmtree(backup)
            index["entries"][key] = target.name
            index["urls"][self._url_index_key(normalized, profile)] = key
            index["identities"][identity] = key
            index["identities"][self.identity(normalized, profile=profile)] = key
            atomic_write_json(self.index_path, index)
            hit = self.lookup(normalized, needs_visual=False, profile=profile)
            if hit is None:
                raise WatchVideoError("cache read-back did not produce a valid context")
            return hit
        except Exception as exc:
            self.last_error = str(exc)
            if target.exists() and backup.exists():
                try:
                    shutil.rmtree(target)
                    backup.rename(target)
                except OSError:
                    pass
            elif backup.exists() and not target.exists():
                try:
                    backup.rename(target)
                except OSError:
                    pass
            try:
                if temporary.exists():
                    shutil.rmtree(temporary)
            except OSError:
                pass
            return None


__all__ = ["CACHE_VERSION", "DEFAULT_CACHE_PROFILE", "CacheHit", "CacheStore"]
