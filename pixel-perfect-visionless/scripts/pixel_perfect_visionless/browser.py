"""Browser discovery and deterministic screenshot capture."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .bootstrap import BootstrapError, Runtime, ensure_playwright_browser


class BrowserError(RuntimeError):
    """Raised when a browser cannot produce the requested screenshot."""


@dataclass(frozen=True)
class Browser:
    engine: str
    executable: Path | None = None


def _candidates() -> list[Path]:
    home = Path.home()
    values: list[Path] = []
    explicit = os.environ.get("PIXEL_PERFECT_VISIONLESS_BROWSER")
    if explicit:
        values.append(Path(explicit).expanduser())
    for command in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(command)
        if found:
            values.append(Path(found))
    values.extend(
        [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
            home / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            home / "Applications/Chromium.app/Contents/MacOS/Chromium",
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        ]
    )
    return values


def find_system_browser(explicit: str | None = None) -> Browser | None:
    if explicit and explicit.lower() in {"playwright", "chromium-playwright"}:
        return None
    candidates = [Path(explicit).expanduser()] if explicit else _candidates()
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return Browser("chrome-cli", candidate)
    return None


def browser_plan(runtime: Runtime, *, explicit: str | None = None, install: bool = True) -> Browser:
    system = find_system_browser(explicit)
    if system:
        return system
    if explicit and explicit.lower() not in {"playwright", "chromium-playwright"}:
        raise BrowserError(f"Browser executable not found or not executable: {explicit}")
    if not runtime.playwright_available:
        raise BrowserError("No system browser found and Playwright is unavailable; rerun setup without --no-auto-setup.")
    try:
        ensure_playwright_browser(runtime, install=install)
    except BootstrapError as exc:
        raise BrowserError(str(exc)) from exc
    return Browser("playwright")


def _chrome_command(browser: Browser, url: str, output: Path, width: int, height: int, wait_ms: int) -> list[str]:
    command = [
        str(browser.executable),
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={width},{height}",
        f"--screenshot={output}",
    ]
    if wait_ms > 0:
        command.append(f"--virtual-time-budget={wait_ms}")
    command.append(url)
    return command


def _capture_chrome(browser: Browser, url: str, output: Path, width: int, height: int, wait_ms: int, timeout: float) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = _chrome_command(browser, url, output, width, height, wait_ms)
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise BrowserError(f"Browser timed out after {timeout:.1f}s: {url}") from exc
    except OSError as exc:
        raise BrowserError(f"Could not start browser: {exc}") from exc
    if not output.is_file():
        detail = (result.stderr or result.stdout or "").strip()
        raise BrowserError("Browser completed without producing a screenshot" + (f": {detail[-1000:]}" if detail else ""))
    if result.returncode:
        detail = (result.stderr or result.stdout or "").strip()
        raise BrowserError(
            f"Browser exited with status {result.returncode}"
            + (f": {detail[-1000:]}" if detail else "")
        )
    warnings = [result.stderr.strip()[-1000:]] if result.stderr.strip() else []
    return {"engine": browser.engine, "url": url, "output": str(output), "warnings": warnings, "console_capture": False}


def _capture_playwright(runtime: Runtime, url: str, output: Path, width: int, height: int, wait_ms: int, timeout: float, ready_selector: str | None) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise BrowserError("Playwright is not importable in the active environment; rerun setup.") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(url, wait_until="load", timeout=int(timeout * 1000))
            if ready_selector:
                page.wait_for_selector(ready_selector, timeout=int(timeout * 1000))
            if wait_ms > 0:
                page.wait_for_timeout(wait_ms)
            page.screenshot(path=str(output), full_page=False)
            browser.close()
    except Exception as exc:
        raise BrowserError(f"Playwright could not render {url}: {exc}") from exc
    return {"engine": "playwright", "url": url, "output": str(output), "warnings": [], "console_errors": console_errors, "page_errors": page_errors, "console_capture": True}


def capture(runtime: Runtime, *, url: str, output: Path, width: int, height: int, browser: str | None = None, wait_ms: int = 250, timeout: float = 60.0, ready_selector: str | None = None, install: bool = True) -> dict[str, Any]:
    selected = browser_plan(runtime, explicit=browser, install=install)
    if selected.engine == "chrome-cli":
        if ready_selector:
            raise BrowserError("--ready-selector requires Playwright; use --browser playwright")
        result = _capture_chrome(selected, url, output, width, height, wait_ms, timeout)
    else:
        result = _capture_playwright(runtime, url, output, width, height, wait_ms, timeout, ready_selector)
    try:
        from PIL import Image

        with Image.open(output) as image:
            actual = image.size
    except Exception as exc:
        raise BrowserError(f"Screenshot is unreadable: {output}: {exc}") from exc
    result["size"] = {"width": actual[0], "height": actual[1]}
    if actual != (width, height):
        raise BrowserError(f"Screenshot size {actual[0]}x{actual[1]} does not match requested viewport {width}x{height}")
    return result
