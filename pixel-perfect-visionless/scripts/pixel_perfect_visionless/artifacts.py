"""Persistent, immutable run directories for compiler outputs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .bootstrap import artifact_directory


class ArtifactError(RuntimeError):
    """Raised when a persistent artifact cannot be written."""


class RunArtifacts:
    """Write all operation outputs under one persistent run directory."""

    def __init__(self, *, root: Path, operation: str, run_dir: Path | None = None):
        self.root = Path(root).expanduser().resolve()
        self.operation = operation
        self.run_dir = (run_dir or self._new_run_dir()).expanduser().resolve()
        if run_dir is not None:
            try:
                self.run_dir.relative_to(self.root)
            except ValueError as exc:
                raise ArtifactError(f"Artifact run directory must be inside artifact root: {self.run_dir}") from exc
            if (self.run_dir / "result.json").is_file():
                raise ArtifactError(f"Completed artifact run is immutable: {self.run_dir}")
        try:
            self.run_dir.mkdir(parents=True, exist_ok=False if run_dir is None else True)
        except OSError as exc:
            raise ArtifactError(f"Could not create artifact run directory {self.run_dir}: {exc}") from exc
        self.started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._write_json(
            self.run_dir / "run.json",
            {
                "operation": self.operation,
                "status": "running",
                "run_dir": str(self.run_dir),
                "started_at": self.started_at,
            },
        )

    @classmethod
    def from_workspace(
        cls,
        workspace_root: Path,
        operation: str,
        *,
        output_root: Path | None = None,
        run_dir: Path | None = None,
    ) -> "RunArtifacts":
        root = Path(output_root) if output_root is not None else artifact_directory(Path(workspace_root))
        if not root.is_absolute():
            root = Path(workspace_root) / root
        return cls(root=root, operation=operation, run_dir=run_dir)

    def _new_run_dir(self) -> Path:
        runs = self.root / "runs"
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        base_name = f"{timestamp}-{self.operation}"
        candidate = runs / base_name
        suffix = 2
        while candidate.exists():
            candidate = runs / f"{base_name}-{suffix:02d}"
            suffix += 1
        return candidate

    def path(self, name: str | Path) -> Path:
        path = self.run_dir / Path(name)
        try:
            path.resolve().relative_to(self.run_dir)
        except ValueError as exc:
            raise ArtifactError(f"Artifact path escapes run directory: {name}") from exc
        return path

    def write_json(self, name: str | Path, data: Any) -> Path:
        path = self.path(name)
        self._write_json(path, data)
        return path

    def _write_json(self, path: Path, data: Any) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.tmp")
            temporary.write_text(
                json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        except (OSError, TypeError, ValueError) as exc:
            raise ArtifactError(f"Could not write JSON artifact {path}: {exc}") from exc

    def write_text(self, name: str | Path, content: str) -> Path:
        path = self.path(name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise ArtifactError(f"Could not write text artifact {path}: {exc}") from exc
        return path

    def write_bytes(self, name: str | Path, content: bytes) -> Path:
        path = self.path(name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        except OSError as exc:
            raise ArtifactError(f"Could not write binary artifact {path}: {exc}") from exc
        return path

    def write_image(self, name: str | Path, image: Any, **kwargs: Any) -> Path:
        path = self.path(name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path, **kwargs)
        except Exception as exc:
            raise ArtifactError(f"Could not write image artifact {path}: {exc}") from exc
        return path

    def write_manifest(self, manifest: dict[str, Any]) -> Path:
        return self.write_json("manifest.json", manifest)

    def finalize(self, result: dict[str, Any], *, markdown: str | None = None) -> dict[str, str]:
        completed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        result = {
            **result,
            "run": {
                "operation": self.operation,
                "run_dir": str(self.run_dir),
                "started_at": self.started_at,
                "completed_at": completed_at,
            },
        }
        result_path = self.write_json("result.json", result)
        markdown_content = markdown or generic_markdown(result)
        markdown_path = self.write_text("result.md", markdown_content)
        self._write_json(
            self.run_dir / "run.json",
            {
                "operation": self.operation,
                "status": result.get("status", "unknown"),
                "run_dir": str(self.run_dir),
                "started_at": self.started_at,
                "completed_at": completed_at,
            },
        )
        self._update_latest(result_path)
        return {"result_json": str(result_path), "result_markdown": str(markdown_path)}

    def _update_latest(self, result_path: Path) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            latest = self.root / "latest.json"
            temporary = latest.with_name(".latest.json.tmp")
            temporary.write_text(
                json.dumps(
                    {
                        "operation": self.operation,
                        "status": json.loads(result_path.read_text(encoding="utf-8")).get("status"),
                        "run_dir": str(self.run_dir),
                        "result": str(result_path),
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temporary.replace(latest)
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"Could not update latest artifact pointer {self.root / 'latest.json'}: {exc}") from exc


def generic_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Pixel-perfect visionless result",
        "",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Operation: `{result.get('operation', result.get('run', {}).get('operation', 'unknown'))}`",
        f"- Run directory: `{result.get('run', {}).get('run_dir', 'unknown')}`",
    ]
    if result.get("error"):
        lines.extend(["", "## Error", "", f"{result['error']}"])
    if result.get("diagnostics"):
        lines.extend(["", "## Diagnostics", ""])
        lines.extend(f"- {item}" for item in result["diagnostics"])
    return "\n".join(lines) + "\n"
