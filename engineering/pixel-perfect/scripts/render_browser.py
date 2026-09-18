"""Render a URL/local HTML file with a bounded headless browser adapter.

The adapter prefers an installed Python Playwright backend and otherwise uses a
native Chrome/Chromium headless screenshot.  It performs browser mechanics only;
the agent still owns target selection, semantic state, and evidence review.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit

try:
    from ._common import (
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_stage,
        checked_float,
        checked_text,
        input_path,
        normalize_image,
        parse_dimensions,
        parse_point,
        run_entrypoint,
        write_json,
    )
except ImportError:  # pragma: no cover - direct executable path
    from _common import (  # type: ignore
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_stage,
        checked_float,
        checked_text,
        input_path,
        normalize_image,
        parse_dimensions,
        parse_point,
        run_entrypoint,
        write_json,
    )


_BROWSER_CANDIDATES = (
    ("google-chrome", "google-chrome"),
    ("chromium", "chromium"),
    ("chromium-browser", "chromium-browser"),
    ("brave", "brave"),
    ("Google Chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ("Chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ("Brave Browser", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
)


class BrowserRenderError(PixelPerfectError):
    """A target browser could not produce the requested screenshot."""


def _browser_path(explicit: object | None = None) -> tuple[str, str]:
    if explicit is not None:
        value = checked_text(explicit, "browser path", max_length=4096)
        path = Path(value).expanduser()
        if path.parent != Path(".") or "/" in value or "\\" in value:
            if path.is_file() and os.access(path, os.X_OK):
                return "explicit", str(path.resolve())
        else:
            found = shutil.which(value)
            if found:
                return "explicit", str(Path(found).resolve())
        raise BrowserRenderError(f"browser executable is unavailable: {value}", status="tool_unavailable")
    for name, value in _BROWSER_CANDIDATES:
        path = Path(value).expanduser()
        if path.parent != Path(".") or "/" in value or "\\" in value:
            if path.is_file() and os.access(path, os.X_OK):
                return name, str(path.resolve())
        else:
            found = shutil.which(value)
            if found:
                return name, str(Path(found).resolve())
    raise BrowserRenderError(
        "no Chrome/Chromium executable was found; install/provide one or use an installed Playwright browser",
        status="tool_unavailable",
    )


def _target_url(value: object) -> str:
    raw = str(value) if isinstance(value, Path) else value
    text = checked_text(raw, "browser target", max_length=16_384)
    parts = urlsplit(text)
    if parts.scheme.casefold() in {"http", "https"} and parts.netloc:
        if parts.username is not None or parts.password is not None:
            raise PixelPerfectError("browser target URL must not contain embedded credentials", status="invalid_input")
        return text
    path = input_path(text, "browser target file")
    return path.resolve().as_uri()


def _wait_ms(value: object) -> int:
    if type(value) is not int or value < 0 or value > 300_000:
        raise PixelPerfectError("wait milliseconds must be an integer between 0 and 300000")
    return value


def _write_browser_screenshot(
    target: str,
    output: Path,
    *,
    viewport: tuple[int, int],
    dpr: float,
    wait_ms: int,
    wait_for_fonts: bool,
    disable_animations: bool,
    scroll: tuple[int, int],
    wait_selector: str | None,
    full_page: bool,
    theme: str,
    timeout: float,
    backend: str,
    browser_path: object | None,
) -> tuple[str, str | None, list[str]]:
    warnings: list[str] = []
    playwright_available = importlib.util.find_spec("playwright") is not None
    selected_backend = backend
    if selected_backend == "auto":
        selected_backend = "playwright" if playwright_available else "chrome"
    if selected_backend == "playwright":
        if not playwright_available:
            raise BrowserRenderError(
                "Python Playwright is unavailable in the skill venv; choose --backend chrome or install it in the project venv",
                status="tool_unavailable",
            )
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                launch: dict[str, object] = {"headless": True}
                if browser_path is not None:
                    _, resolved_browser = _browser_path(browser_path)
                    launch["executable_path"] = resolved_browser
                browser = playwright.chromium.launch(**launch)
                try:
                    context_args: dict[str, object] = {
                        "viewport": {"width": viewport[0], "height": viewport[1]},
                        "device_scale_factor": dpr,
                    }
                    if theme in {"light", "dark"}:
                        context_args["color_scheme"] = theme
                    context = browser.new_context(**context_args)
                    try:
                        page = context.new_page()
                        page.goto(target, wait_until="domcontentloaded", timeout=int(timeout * 1000))
                        if disable_animations:
                            page.add_style_tag(content=(
                                "*, *::before, *::after {"
                                " animation: none !important; transition: none !important;"
                                " caret-color: transparent !important; }"
                            ))
                        if wait_for_fonts:
                            page.evaluate("document.fonts ? document.fonts.ready : Promise.resolve()")
                        if wait_selector:
                            page.wait_for_selector(wait_selector, state="visible", timeout=int(timeout * 1000))
                        page.evaluate("([x, y]) => window.scrollTo(x, y)", list(scroll))
                        if wait_ms:
                            page.wait_for_timeout(wait_ms)
                        page.screenshot(path=str(output), full_page=full_page, animations="disabled" if disable_animations else "allow")
                    finally:
                        context.close()
                finally:
                    browser.close()
            return "playwright", None, warnings
        except PixelPerfectError:
            raise
        except Exception as exc:
            raise BrowserRenderError(f"Playwright browser render failed: {exc}", status="render_failed") from exc
    if selected_backend != "chrome":
        raise PixelPerfectError("browser backend must be auto, playwright, or chrome", status="invalid_input")
    name, binary = _browser_path(browser_path)
    command = [
        binary,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--hide-scrollbars",
        "--run-all-compositor-stages-before-draw",
        f"--window-size={viewport[0]},{viewport[1]}",
        f"--force-device-scale-factor={dpr:g}",
        f"--virtual-time-budget={wait_ms}",
        f"--screenshot={output}",
        target,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise BrowserRenderError("Chrome headless render timed out", status="render_failed") from exc
    except OSError as exc:
        raise BrowserRenderError(f"could not start Chrome headless render: {exc}", status="tool_unavailable") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise BrowserRenderError(f"Chrome headless render failed: {detail or 'non-zero exit'}", status="render_failed")
    unsupported: list[str] = []
    if wait_for_fonts:
        unsupported.append("font-loading completion")
    if disable_animations:
        unsupported.append("animation disabling")
    if wait_selector:
        unsupported.append("selector wait")
    if scroll != (0, 0):
        unsupported.append("scroll position")
    if theme != "system":
        unsupported.append("color theme")
    if full_page:
        unsupported.append("full-page capture")
    if unsupported:
        warnings.append("Chrome CLI rendered, but could not prove: " + ", ".join(unsupported))
    return f"chrome:{name}", "requested browser controls were not all available" if warnings else None, warnings


def render_browser(
    target: object,
    *,
    task_name: str,
    viewport: str = "1280x720",
    dpr: float = 1.0,
    wait_ms: int = 500,
    wait_for_fonts: bool = False,
    disable_animations: bool = False,
    scroll: tuple[int, int] = (0, 0),
    wait_selector: str | None = None,
    full_page: bool = False,
    theme: str = "system",
    timeout: float = 60.0,
    backend: str = "auto",
    browser_path: object | None = None,
    output_dir_value: object | None = None,
    cwd: object | None = None,
) -> dict[str, object]:
    """Render one browser state to a numeric-prefixed task artifact."""

    dimensions = parse_dimensions(viewport, "viewport")
    dpr = checked_float(dpr, "DPR", minimum=0.1, maximum=8.0)
    wait_ms = _wait_ms(wait_ms)
    timeout = checked_float(timeout, "browser timeout", minimum=1.0, maximum=600.0)
    if theme not in {"system", "light", "dark"}:
        raise PixelPerfectError("theme must be system, light, or dark", status="invalid_input")
    if wait_selector is not None:
        wait_selector = checked_text(wait_selector, "wait selector", max_length=4096)
    target_url = _target_url(target)
    if len(scroll) != 2 or any(type(value) is not int or value < 0 for value in scroll):
        raise PixelPerfectError("scroll must contain two non-negative integers", status="invalid_input")
    directory = artifact_stage(task_name, "browser", output_dir_value, cwd=cwd)
    screenshot_path = directory / "001-browser.png"
    backend_name, limitation, warnings = _write_browser_screenshot(
        target_url,
        screenshot_path,
        viewport=dimensions,
        dpr=dpr,
        wait_ms=wait_ms,
        wait_for_fonts=wait_for_fonts,
        disable_animations=disable_animations,
        scroll=scroll,
        wait_selector=wait_selector,
        full_page=full_page,
        theme=theme,
        timeout=timeout,
        backend=backend,
        browser_path=browser_path,
    )
    try:
        inspected = normalize_image(screenshot_path, background=(255, 255, 255))
    except PixelPerfectError:
        raise
    actual_dimensions = list(inspected.image.size)
    if actual_dimensions != list(dimensions):
        warnings.append(
            f"rendered raster dimensions {actual_dimensions} differ from requested CSS viewport {list(dimensions)}; DPR/engine output must be checked"
        )
    manifest_path = directory / "002-manifest.json"
    result: dict[str, object] = {
        "status": "partial" if warnings or limitation else "complete",
        "operation": "browser-render",
        "task_name": task_name,
        "target": target_url,
        "backend": backend_name,
        "conditions": {
            "viewport": list(dimensions),
            "dpr": dpr,
            "wait_ms": wait_ms,
            "wait_for_fonts": wait_for_fonts,
            "disable_animations": disable_animations,
            "scroll": list(scroll),
            "wait_selector": wait_selector,
            "full_page": full_page,
            "theme": theme,
            "timeout_seconds": timeout,
        },
        "requested_output_dimensions": [
            round(dimensions[0] * dpr), round(dimensions[1] * dpr)
        ],
        "actual_output_dimensions": actual_dimensions,
        "image": inspected.info.as_dict(),
        "warnings": warnings,
        "limitations": [limitation] if limitation else [],
        "artifacts": {
            "directory": str(directory.resolve()),
            "screenshot": str(screenshot_path.resolve()),
            "manifest": str(manifest_path.resolve()),
        },
        "agent_boundary": "browser mechanics are observed here; the agent must inspect the target state and verify semantics/behavior",
    }
    write_json(manifest_path, result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = PixelPerfectArgumentParser(description="Render a URL or local HTML file with a deterministic browser adapter")
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--viewport", default="1280x720")
    parser.add_argument("--dpr", type=float, default=1.0)
    parser.add_argument("--wait-ms", type=int, default=500)
    parser.add_argument("--wait-for-fonts", action="store_true")
    parser.add_argument("--disable-animations", action="store_true")
    parser.add_argument("--scroll", type=parse_point, default=(0, 0))
    parser.add_argument("--wait-selector")
    parser.add_argument("--full-page", action="store_true")
    parser.add_argument("--theme", choices=("system", "light", "dark"), default="system")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--backend", choices=("auto", "playwright", "chrome"), default="auto")
    parser.add_argument("--browser-path")
    parser.add_argument("--output-dir", type=Path, help="optional empty numeric-prefixed stage under .artifacts/pixel-perfect/<task-name>")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = render_browser(
        args.target,
        task_name=args.task_name,
        viewport=args.viewport,
        dpr=args.dpr,
        wait_ms=args.wait_ms,
        wait_for_fonts=args.wait_for_fonts,
        disable_animations=args.disable_animations,
        scroll=args.scroll,
        wait_selector=args.wait_selector,
        full_page=args.full_page,
        theme=args.theme,
        timeout=args.timeout,
        backend=args.backend,
        browser_path=args.browser_path,
        output_dir_value=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "complete" else 2


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


__all__ = ["main", "render_browser"]
