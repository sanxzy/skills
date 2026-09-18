"""Inspect visual inputs and local rendering prerequisites before implementation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

try:
    from ._common import (
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_report_path,
        checked_float,
        checked_text,
        normalize_image,
        parse_dimensions,
        run_entrypoint,
        write_json,
    )
except ImportError:  # pragma: no cover - direct executable path
    from _common import (  # type: ignore
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_report_path,
        checked_float,
        checked_text,
        normalize_image,
        parse_dimensions,
        run_entrypoint,
        write_json,
    )


_BROWSER_PATHS = (
    ("google-chrome", "google-chrome"),
    ("chromium", "chromium"),
    ("chromium-browser", "chromium-browser"),
    ("brave", "brave"),
    ("Google Chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ("Chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ("Brave Browser", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
)


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    pieces: list[int] = []
    for part in value.split(".")[:3]:
        digits = "".join(character for character in part if character.isdigit())
        if not digits:
            break
        pieces.append(int(digits))
    if not pieces:
        return None
    return tuple((pieces + [0, 0, 0])[:3])


def _inspect_image(path: object) -> dict[str, object]:
    image = normalize_image(path, background=(255, 255, 255))
    info = image.info.as_dict()
    width, height = image.image.size
    info.update({
        "dimensions": [width, height],
        "has_alpha": bool(info["alpha_composited"]),
        "likely_viewport": {
            "raster_dimensions": [width, height],
            "candidate_viewport": [width, height],
            "candidate_dpr": 1.0,
            "confidence": "unknown",
            "note": "raster dimensions alone do not prove CSS viewport or device pixel ratio",
        },
    })
    return info


def _discover_browsers(explicit: object | None = None) -> list[dict[str, object]]:
    candidates: list[tuple[str, str]] = []
    if explicit is not None:
        value = checked_text(explicit, "browser path", max_length=4096)
        candidates.append(("explicit", value))
    else:
        candidates.extend(_BROWSER_PATHS)
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for name, value in candidates:
        resolved: str | None = None
        path = Path(value).expanduser()
        if path.parent != Path(".") or "/" in value or "\\" in value:
            if path.is_file() and os.access(path, os.X_OK):
                resolved = str(path.resolve())
        else:
            found = shutil.which(value)
            if found:
                resolved = str(Path(found).resolve())
        if resolved is not None and resolved in seen:
            continue
        if resolved is not None:
            seen.add(resolved)
        rows.append({
            "name": name,
            "requested": value,
            "path": resolved,
            "status": "available" if resolved else "missing",
        })
    playwright = bool(importlib.util.find_spec("playwright"))
    rows.append({
        "name": "python-playwright",
        "requested": "playwright module",
        "path": None,
        "status": "available" if playwright else "missing",
        "note": "package availability does not prove that a browser binary is installed",
    })
    return rows


def _check_executable(value: str) -> dict[str, object]:
    text = checked_text(value, "required executable", max_length=4096)
    path = Path(text).expanduser()
    if path.parent != Path(".") or "/" in text or "\\" in text:
        available = path.is_file() and os.access(path, os.X_OK)
        resolved = str(path.resolve()) if available else None
    else:
        found = shutil.which(text)
        available = found is not None
        resolved = str(Path(found).resolve()) if found else None
    return {"requested": text, "path": resolved, "status": "available" if available else "missing"}


def _check_font_path(value: str) -> dict[str, object]:
    text = checked_text(value, "font path", max_length=4096)
    path = Path(text).expanduser()
    row: dict[str, object] = {"requested": text, "path": None, "certainty": "missing"}
    if not path.is_file() or path.is_symlink():
        return row
    row["path"] = str(path.resolve())
    try:
        from PIL import ImageFont

        ImageFont.truetype(str(path), size=16)
    except Exception as exc:
        row["certainty"] = "unknown"
        row["note"] = f"font file exists but could not be loaded: {exc}"
    else:
        row["certainty"] = "exact"
    return row


def _resolve_font_family(value: str) -> dict[str, object]:
    family = checked_text(value, "font family", max_length=256)
    binary = shutil.which("fc-match")
    if binary is None:
        return {
            "requested": family,
            "certainty": "unknown",
            "note": "fc-match is unavailable; a family name cannot be resolved without inspecting the target renderer",
        }
    try:
        result = subprocess.run(
            [binary, "--format=%{file}", family],
            capture_output=True,
            text=True,
            timeout=5.0,
            shell=False,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"requested": family, "certainty": "unknown", "note": f"font resolver failed: {exc}"}
    resolved = result.stdout.strip()
    if result.returncode != 0 or not resolved or not Path(resolved).is_file():
        return {"requested": family, "certainty": "missing", "note": "font family did not resolve to a readable file"}
    return {
        "requested": family,
        "resolved_path": str(Path(resolved).resolve()),
        "certainty": "unknown",
        "note": "family resolver found a file, but exact renderer face/weight loading is not proven",
    }


def _runtime_status(cwd: Path) -> dict[str, object]:
    try:
        import PIL

        version_text = str(getattr(PIL, "__version__", ""))
    except Exception:
        version_text = ""
    version = _version_tuple(version_text)
    expected = (cwd / ".venv").resolve()
    active = Path(sys.prefix).resolve()
    isolated = active == expected and sys.base_prefix != sys.prefix
    return {
        "python": sys.executable,
        "prefix": str(active),
        "expected_prefix": str(expected),
        "isolated": isolated,
        "pillow": {
            "version": version_text or None,
            "meets_requirement": version is not None and version >= (10, 0, 0),
        },
        "status": "ready" if isolated and version is not None and version >= (10, 0, 0) else "blocked",
    }


def preflight(
    references: Sequence[object],
    *,
    task_name: str,
    renders: Sequence[object] = (),
    viewport: str | None = None,
    dpr: float | None = None,
    browser_path: object | None = None,
    required_executables: Sequence[str] = (),
    font_paths: Sequence[str] = (),
    font_families: Sequence[str] = (),
    assets: Sequence[str] = (),
    output: object | None = None,
    cwd: object | None = None,
) -> dict[str, object]:
    if not references:
        raise PixelPerfectError("at least one reference is required")
    root = Path.cwd() if cwd is None else Path(cwd).expanduser()
    root = root.resolve(strict=True)
    requested_viewport = parse_dimensions(viewport, "viewport") if viewport is not None else None
    requested_dpr = None if dpr is None else checked_float(dpr, "DPR", minimum=0.1, maximum=8.0)
    image_rows = [_inspect_image(path) for path in references]
    render_rows = [_inspect_image(path) for path in renders]
    if requested_viewport is not None or requested_dpr is not None:
        for row in [*image_rows, *render_rows]:
            width, height = row["dimensions"]
            candidate_viewport = requested_viewport or (
                round(width / requested_dpr), round(height / requested_dpr)
            ) if requested_dpr else (width, height)
            row["likely_viewport"] = {
                "raster_dimensions": [width, height],
                "candidate_viewport": list(candidate_viewport),
                "candidate_dpr": requested_dpr or 1.0,
                "confidence": "provided",
                "note": "requested render condition; actual target capture still requires verification",
            }
    executables = [_check_executable(value) for value in required_executables]
    font_rows = [_check_font_path(value) for value in font_paths]
    font_rows.extend(_resolve_font_family(value) for value in font_families)
    asset_rows = []
    for value in assets:
        text = checked_text(value, "asset path", max_length=4096)
        path = Path(text).expanduser()
        asset_rows.append({
            "requested": text,
            "path": str(path.resolve()) if path.is_file() and not path.is_symlink() else None,
            "certainty": "exact" if path.is_file() and not path.is_symlink() else "missing",
        })
    browsers = _discover_browsers(browser_path)
    runtime = _runtime_status(root)
    warnings: list[str] = []
    if not any(row["status"] == "available" for row in browsers):
        warnings.append("no supported browser executable or Playwright module was discovered")
    if any(row["certainty"] in {"missing", "unknown"} for row in font_rows):
        warnings.append("one or more requested fonts are missing or not proven exact")
    if any(row["certainty"] == "missing" for row in asset_rows):
        warnings.append("one or more requested assets are missing")
    if any(row["status"] == "missing" for row in executables):
        warnings.append("one or more required executables are missing")
    if runtime["status"] != "ready":
        warnings.append("skill runtime is not isolated/ready; use the dispatcher runtime preflight")
    report: dict[str, object] = {
        "status": "complete",
        "operation": "preflight",
        "task_name": task_name,
        "platform": platform.platform(),
        "runtime": runtime,
        "references": image_rows,
        "renders": render_rows,
        "requested_conditions": {
            "viewport": list(requested_viewport) if requested_viewport else None,
            "dpr": requested_dpr,
            "note": "unknown conditions remain explicit; this command does not infer CSS viewport from raster dimensions",
        },
        "browsers": browsers,
        "executables": executables,
        "fonts": font_rows,
        "assets": asset_rows,
        "warnings": warnings,
        "readiness": "ready" if not warnings else "partial",
    }
    report_path = artifact_report_path(task_name, "preflight", output, cwd=root)
    report["artifacts"] = {"report": str(report_path.resolve())}
    write_json(report_path, report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = PixelPerfectArgumentParser(description="Inspect visual inputs and render prerequisites")
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--reference", action="append", required=True, type=Path)
    parser.add_argument("--render", action="append", default=[], type=Path)
    parser.add_argument("--viewport", help="expected WIDTHxHEIGHT")
    parser.add_argument("--dpr", type=float)
    parser.add_argument("--browser-path")
    parser.add_argument("--require-executable", action="append", default=[])
    parser.add_argument("--font-path", action="append", default=[])
    parser.add_argument("--font-family", action="append", default=[])
    parser.add_argument("--asset", action="append", default=[])
    parser.add_argument("--output", type=Path, help="optional numeric-prefixed JSON path under the task artifact directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = preflight(
        args.reference,
        task_name=args.task_name,
        renders=args.render,
        viewport=args.viewport,
        dpr=args.dpr,
        browser_path=args.browser_path,
        required_executables=args.require_executable,
        font_paths=args.font_path,
        font_families=args.font_family,
        assets=args.asset,
        output=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _entrypoint(argv: Sequence[str] | None = None) -> int:
    try:
        rerun = run_entrypoint(__file__, tuple(argv if argv is not None else sys.argv[1:]))
        if rerun is not None:
            return rerun
        return main(argv)
    except PixelPerfectError as exc:
        print(json.dumps({"status": exc.status, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_entrypoint())


__all__ = ["main", "preflight"]
