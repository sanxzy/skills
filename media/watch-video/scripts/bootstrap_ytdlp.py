"""Provision yt-dlp in the invoking workspace's local ``.venv``.

This is deliberately separate from media resolution so setup has one clear
boundary.  It reuses a healthy local environment, installs only the yt-dlp
package through that environment's interpreter, and never writes to the
system Python installation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

try:  # Support both module and direct-script execution.
    from .common import (
        ToolUnavailableError,
        WatchVideoError,
        atomic_write_json,
        checked_timeout,
        ensure_directory,
        read_json,
        run_command,
        safe_text,
        workspace_root,
    )
except ImportError:  # pragma: no cover
    from common import (  # type: ignore
        ToolUnavailableError,
        WatchVideoError,
        atomic_write_json,
        checked_timeout,
        ensure_directory,
        read_json,
        run_command,
        safe_text,
        workspace_root,
    )


BOOTSTRAP_VERSION = 1
_MARKER_NAME = "001-watch-video-yt-dlp.json"
_PROBE_CODE = (
    "import yt_dlp.version; print(getattr(yt_dlp.version, '__version__', 'unknown'))"
)


@dataclass(frozen=True)
class LocalYtDlp:
    """A verified yt-dlp command owned by a local virtual environment."""

    venv: Path
    python: Path
    version: str

    @property
    def argv(self) -> tuple[str, ...]:
        return (str(self.python), "-m", "yt_dlp")

    @property
    def environment(self) -> dict[str, str]:
        return _venv_environment(self.venv)


_READY: dict[Path, LocalYtDlp] = {}
_FAILURES: dict[Path, str] = {}


def _workspace(value: str | Path | None) -> Path:
    return workspace_root(value)


def local_venv(cwd: str | Path | None = None) -> Path:
    """Return the exact ``<cwd>/.venv`` path, rejecting symlink escapes."""

    root = _workspace(cwd)
    target = root / ".venv"
    if target.is_symlink():
        raise ToolUnavailableError("yt-dlp", f"local .venv is a symlink and will not be followed: {target}")
    if target.exists() and not target.is_dir():
        raise ToolUnavailableError("yt-dlp", f"local .venv is not a directory: {target}")
    return target


def _python_candidates(venv: Path) -> tuple[Path, ...]:
    return (
        venv / "bin" / "python3",
        venv / "bin" / "python",
        venv / "Scripts" / "python.exe",
        venv / "Scripts" / "python",
    )


def venv_python(venv: Path) -> Path:
    for candidate in _python_candidates(venv):
        is_regular = candidate.is_file() and not candidate.is_symlink()
        is_interpreter_link = candidate.is_symlink() and candidate.resolve(strict=False).is_file()
        if (is_regular or is_interpreter_link) and os.access(candidate, os.X_OK):
            return candidate
    raise ToolUnavailableError("yt-dlp", f"local .venv has no runnable interpreter: {venv}")


def _isolated_venv(venv: Path) -> bool:
    config = venv / "pyvenv.cfg"
    if not config.is_file() or config.is_symlink():
        return False
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return False
    for line in lines:
        key, separator, value = line.partition("=")
        if separator and key.strip().casefold() == "include-system-site-packages":
            return value.strip().casefold() == "false"
    # Python's venv writes this setting.  An absent setting is not enough to
    # prove isolation for a pre-existing environment.
    return False


def _base_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in (
        "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONUSERBASE",
        "PIP_TARGET", "PIP_PREFIX", "PIP_USER", "PIP_CONFIG_FILE",
        "PIP_REQUIRE_VIRTUALENV", "PIP_FIND_LINKS",
    ):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _venv_environment(venv: Path) -> dict[str, str]:
    environment = _base_environment()
    cache = ensure_directory(venv / "pip-cache")
    temporary = ensure_directory(venv / "tmp")
    environment["PIP_CACHE_DIR"] = str(cache)
    environment["TMPDIR"] = str(temporary)
    environment["TMP"] = str(temporary)
    environment["TEMP"] = str(temporary)
    return environment


def _failure_detail(result) -> str:
    detail = safe_text(result.stderr or result.stdout).strip()
    if result.timed_out:
        return "setup command timed out"
    return detail or f"setup command exited with status {result.returncode}"


def _probe(
    python: Path,
    venv: Path,
    cwd: Path,
    *,
    timeout: float,
    runner=None,
) -> str | None:
    result = run_command(
        [str(python), "-c", _PROBE_CODE],
        cwd=cwd,
        timeout=checked_timeout(timeout, "yt-dlp probe timeout"),
        env=_venv_environment(venv),
        runner=runner,
    )
    if not result.ok:
        return None
    version = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    version = safe_text(version, 128).strip()
    return version if version and version.casefold() != "unknown" else None


def _write_marker(venv: Path, python: Path, version: str, *, ready: bool, error: str | None = None) -> None:
    payload: dict[str, Any] = {
        "version": BOOTSTRAP_VERSION,
        "ready": ready,
        "python": str(python),
        "yt_dlp_version": version,
        "updated_at": time.time(),
    }
    if error:
        payload["error"] = error
    atomic_write_json(venv / _MARKER_NAME, payload)


def _marker_is_current(venv: Path, python: Path) -> bool:
    marker = venv / _MARKER_NAME
    if not marker.is_file() or marker.is_symlink():
        return False
    try:
        value = read_json(marker)
    except WatchVideoError:
        return False
    return (
        isinstance(value, dict)
        and value.get("version") == BOOTSTRAP_VERSION
        and value.get("ready") is True
        and value.get("python") == str(python)
        and isinstance(value.get("yt_dlp_version"), str)
        and bool(value.get("yt_dlp_version"))
        and value.get("yt_dlp_version") != "unknown"
    )


def ensure_local_yt_dlp(
    cwd: str | Path | None = None,
    *,
    timeout: float = 900.0,
    runner=None,
) -> LocalYtDlp:
    """Ensure yt-dlp is importable from ``<cwd>/.venv`` and return its command."""

    root = _workspace(cwd)
    if root in _READY:
        return _READY[root]
    if root in _FAILURES:
        raise ToolUnavailableError("yt-dlp", _FAILURES[root])
    limit = checked_timeout(timeout, "yt-dlp setup timeout")
    venv = local_venv(root)
    try:
        if not venv.exists():
            result = run_command(
                [sys.executable, "-m", "venv", str(venv)],
                cwd=root,
                timeout=limit,
                env=_base_environment(),
                runner=runner,
            )
            if not result.ok:
                raise ToolUnavailableError("yt-dlp", f"could not create {venv}: {_failure_detail(result)}")
        if not _isolated_venv(venv):
            raise ToolUnavailableError(
                "yt-dlp",
                f"existing {venv} is not a verified isolated virtual environment; repair it before retrying",
            )
        python = venv_python(venv)
        version = _probe(python, venv, root, timeout=min(limit, 60.0), runner=runner)
        # A pre-existing venv without our verified marker is updated in place
        # once.  We never clear/recreate it, so unrelated packages and files
        # remain untouched.  A marker lets later runs avoid needless pip I/O.
        if version is None or not _marker_is_current(venv, python):
            install = run_command(
                [
                    str(python), "-m", "pip", "--isolated", "install",
                    "--disable-pip-version-check", "--no-input",
                    "--cache-dir", str(venv / "pip-cache"),
                    "--upgrade", "--upgrade-strategy", "only-if-needed", "yt-dlp",
                ],
                cwd=root,
                timeout=limit,
                env=_venv_environment(venv),
                runner=runner,
            )
            if not install.ok:
                detail = f"could not install yt-dlp in {venv}: {_failure_detail(install)}"
                try:
                    _write_marker(venv, python, "unknown", ready=False, error=detail)
                except WatchVideoError:
                    pass
                raise ToolUnavailableError("yt-dlp", detail)
            version = _probe(python, venv, root, timeout=min(limit, 60.0), runner=runner)
        if not version:
            detail = f"yt-dlp installation in {venv} did not pass its import probe"
            try:
                _write_marker(venv, python, "unknown", ready=False, error=detail)
            except WatchVideoError:
                pass
            raise ToolUnavailableError("yt-dlp", detail)
        _write_marker(venv, python, version, ready=True)
        tool = LocalYtDlp(venv=venv, python=python, version=version)
        _READY[root] = tool
        return tool
    except ToolUnavailableError as exc:
        _FAILURES[root] = str(exc)
        raise
    except Exception as exc:
        detail = f"local yt-dlp setup failed: {safe_text(exc)}"
        _FAILURES[root] = detail
        raise ToolUnavailableError("yt-dlp", detail) from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install yt-dlp into the invoking workspace's .venv")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=float, default=900.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        tool = ensure_local_yt_dlp(args.cwd, timeout=args.timeout)
        print(json.dumps({
            "status": "ready",
            "venv": str(tool.venv),
            "python": str(tool.python),
            "version": tool.version,
        }, ensure_ascii=False, indent=2))
        return 0
    except WatchVideoError as exc:
        print(json.dumps({"status": exc.status, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["BOOTSTRAP_VERSION", "LocalYtDlp", "ensure_local_yt_dlp", "local_venv", "main", "venv_python"]
