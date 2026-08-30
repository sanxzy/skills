"""Local target resolution and browser rendering helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .bootstrap import Runtime
from .browser import capture
from .images import ImageAnalysisError, parse_viewport


def resolve_target_url(project_root: Path, *, workspace_root: Path, url: str | None = None, entry: str | None = None) -> str:
    if url:
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https", "file", "data"}:
            return url
        candidate = Path(url).expanduser()
        if not candidate.is_absolute():
            candidate = workspace_root / candidate
        if candidate.is_file():
            return candidate.resolve().as_uri()
        raise ImageAnalysisError(f"Target URL must include http(s)/file scheme or name an existing workspace file: {url}")
    candidate = Path(entry).expanduser() if entry else project_root / "index.html"
    if not candidate.is_absolute():
        candidate = project_root / candidate
    if not candidate.is_file():
        raise ImageAnalysisError(
            f"No render target found at {candidate}. Provide --url for a running server or --entry for a local HTML entrypoint."
        )
    return candidate.resolve().as_uri()


def render_target(runtime: Runtime, *, url: str, output: Path, viewport: str, browser: str | None = None, wait_ms: int = 250, timeout: float = 60.0, ready_selector: str | None = None, install: bool = True) -> dict[str, Any]:
    width, height = parse_viewport(viewport)
    return capture(runtime, url=url, output=output, width=width, height=height, browser=browser, wait_ms=wait_ms, timeout=timeout, ready_selector=ready_selector, install=install)
