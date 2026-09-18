"""Provision the skill-owned Python environment under ``<cwd>/.venv``.

This module intentionally uses only the standard library so it can run before
Pillow is available.  An existing virtual environment is reused in place and
only the skill's declared dependencies are installed or updated; it is never
cleared, deleted, or recreated implicitly.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


DEPENDENCIES = ("Pillow>=10",)
MAX_COMMAND_OUTPUT = 8 * 1024


class RuntimeBootstrapError(Exception):
    """A structured local-runtime failure."""

    def __init__(self, message: str, *, status: str = "tool_unavailable") -> None:
        super().__init__(message)
        self.status = status


# Keep the short internal name used by the small helpers while making the
# exception's inheritance explicit and unambiguous.
RuntimeError = RuntimeBootstrapError


class RuntimeArgumentParser(argparse.ArgumentParser):
    """Keep bootstrap CLI validation structured and bounded."""

    def error(self, message: str) -> None:
        raise RuntimeError(f"invalid arguments: {message}", status="invalid_input")


@dataclass(frozen=True)
class Runtime:
    cwd: Path
    directory: Path
    python: Path
    created: bool
    installed: tuple[str, ...]
    reused: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "cwd": str(self.cwd),
            "directory": str(self.directory),
            "python": str(self.python),
            "created": self.created,
            "reused": self.reused,
            "installed": list(self.installed),
            "dependencies": list(DEPENDENCIES),
        }


def _safe_text(value: object, limit: int = MAX_COMMAND_OUTPUT) -> str:
    try:
        text = str(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 18)] + "…[truncated]"


def _checked_cwd(value: str | Path | None = None) -> Path:
    candidate = Path.cwd() if value is None else Path(value).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError(f"Working directory does not exist: {candidate}") from exc
    if not resolved.is_dir():
        raise RuntimeError(f"Working directory is not a directory: {resolved}")
    return resolved


def _python_path(directory: Path) -> Path:
    if os.name == "nt":
        candidates = (directory / "Scripts" / "python.exe",)
    else:
        candidates = (
            directory / "bin" / "python",
            directory / "bin" / "python3",
            directory / "bin" / f"python{sys.version_info.major}.{sys.version_info.minor}",
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _read_cfg(directory: Path) -> dict[str, str]:
    path = directory / "pyvenv.cfg"
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(
            f"Existing {directory} is not a valid virtual environment (pyvenv.cfg is missing); "
            "it was left untouched",
            status="runtime_unusable",
        )
    values: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key.strip().casefold()] = value.strip()
    except OSError as exc:
        raise RuntimeError(f"Could not read existing virtual-environment metadata: {_safe_text(exc)}", status="runtime_unusable") from exc
    if values.get("include-system-site-packages", "false").casefold() != "false":
        raise RuntimeError(
            f"Existing {directory} enables system site packages; refusing to change or use it "
            "because the skill requires an isolated environment. The directory was left untouched",
            status="runtime_unusable",
        )
    return values


def _run(
    argv: Sequence[str],
    *,
    cwd: Path,
    timeout: float,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    if not argv or any(type(item) is not str or not item or "\x00" in item for item in argv):
        raise RuntimeError("runtime command arguments are malformed", status="runtime_unusable")
    try:
        return subprocess.run(
            list(argv),
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Runtime command timed out: {argv[0]}",
            status="runtime_unusable",
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(f"Runtime executable was not found: {argv[0]}", status="runtime_unusable") from exc
    except OSError as exc:
        raise RuntimeError(f"Could not start runtime command {argv[0]}: {_safe_text(exc)}", status="runtime_unusable") from exc


def _runtime_probe(python: Path, cwd: Path) -> None:
    probe = (
        "import pathlib, sys; "
        "root = pathlib.Path(sys.prefix).resolve(); "
        "expected = pathlib.Path(sys.argv[1]).resolve(); "
        "assert root == expected, (root, expected); "
        "assert sys.base_prefix != sys.prefix; "
        "print(sys.executable)"
    )
    result = _run([str(python), "-c", probe, str(python.parent.parent)], cwd=cwd, timeout=20.0, env=_runtime_env(cwd))
    if result.returncode != 0:
        detail = _safe_text(result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"Existing virtual environment failed its isolation probe: {detail or 'unknown probe failure'}; it was left untouched",
            status="runtime_unusable",
        )


def _runtime_env(cwd: Path, *, directory: Path | None = None) -> dict[str, str]:
    runtime_directory = directory or (cwd / ".venv")
    cache = runtime_directory / ".cache" / "pip"
    temp = runtime_directory / ".tmp"
    try:
        cache.mkdir(parents=True, exist_ok=True)
        temp.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"Could not prepare runtime-local cache/temp directories: {_safe_text(exc)}", status="runtime_unusable") from exc
    environment = dict(os.environ)
    for name in (
        "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONUSERBASE",
        "PIP_CONFIG_FILE", "PIP_TARGET", "PIP_USER", "PIP_PREFIX",
        "PIP_REQUIRE_VIRTUALENV",
    ):
        environment.pop(name, None)
    environment.update({
        "PYTHONNOUSERSITE": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_CACHE_DIR": str(cache),
        "TMPDIR": str(temp),
        "TMP": str(temp),
        "TEMP": str(temp),
    })
    return environment


def _create(cwd: Path, directory: Path) -> None:
    if directory.exists():
        raise RuntimeError(f"Refusing to create over existing path: {directory}", status="runtime_unusable")
    result = _run(
        [sys.executable, "-m", "venv", "--without-pip", str(directory)],
        cwd=cwd,
        timeout=120.0,
        env={
            key: value
            for key, value in os.environ.items()
            if key not in {"PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONUSERBASE"}
        } | {"PYTHONNOUSERSITE": "1"},
    )
    if result.returncode != 0:
        detail = _safe_text(result.stderr or result.stdout).strip()
        raise RuntimeError(f"Could not create {directory}: {detail or 'venv returned a failure'}", status="runtime_unusable")


def _ensure_pip(cwd: Path, directory: Path, python: Path) -> None:
    probe = _run(
        [str(python), "-c", "import pip"],
        cwd=cwd,
        timeout=20.0,
        env=_runtime_env(cwd, directory=directory),
    )
    if probe.returncode == 0:
        return
    result = _run(
        [str(python), "-m", "ensurepip", "--upgrade"],
        cwd=cwd,
        timeout=180.0,
        env=_runtime_env(cwd, directory=directory),
    )
    if result.returncode != 0:
        detail = _safe_text(result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"Existing virtual environment has no usable pip and ensurepip failed: {detail or 'unknown failure'}; it was left untouched",
            status="runtime_unusable",
        )


def _pillow_version(python: Path, cwd: Path, directory: Path) -> tuple[int, int, int] | None:
    probe = "import PIL; print(getattr(PIL, '__version__', ''))"
    result = _run([str(python), "-c", probe], cwd=cwd, timeout=20.0, env=_runtime_env(cwd, directory=directory))
    if result.returncode != 0:
        return None
    match = re.match(r"^\s*(\d+)(?:\.(\d+))?(?:\.(\d+))?", result.stdout.strip())
    if match is None:
        return None
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


def _install_missing(cwd: Path, directory: Path, python: Path) -> tuple[str, ...]:
    installed: list[str] = []
    version = _pillow_version(python, cwd, directory)
    if version is not None and version >= (10, 0, 0):
        return ()
    result = _run(
        [
            str(python), "-m", "pip", "install",
            "--isolated",
            "--disable-pip-version-check",
            "--no-input",
            "--cache-dir", str(directory / ".cache" / "pip"),
            "--upgrade-strategy", "only-if-needed",
            *DEPENDENCIES,
        ],
        cwd=cwd,
        timeout=900.0,
        env=_runtime_env(cwd, directory=directory),
    )
    if result.returncode != 0:
        detail = _safe_text(result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"Could not install skill dependencies into {directory}: {detail or 'pip returned a failure'}",
            status="tool_unavailable",
        )
    installed.extend(DEPENDENCIES)
    verified = _pillow_version(python, cwd, directory)
    if verified is None or verified < (10, 0, 0):
        raise RuntimeError(
            f"Dependency installation reported success but Pillow>=10 was not verified in {directory}",
            status="tool_unavailable",
        )
    return tuple(installed)


def ensure_runtime(cwd: str | Path | None = None) -> Runtime:
    """Create or safely update the isolated environment for one invocation."""

    root = _checked_cwd(cwd)
    directory = root / ".venv"
    created = False
    if directory.exists():
        if directory.is_symlink() or not directory.is_dir():
            raise RuntimeError(f"Existing {directory} is not a real directory; it was left untouched", status="runtime_unusable")
        _read_cfg(directory)
        reused = True
    else:
        _create(root, directory)
        created = True
        reused = False
    python = _python_path(directory)
    if not python.is_file():
        raise RuntimeError(f"Virtual-environment interpreter is missing in {directory}; the directory was left untouched", status="runtime_unusable")
    _runtime_probe(python, root)
    _ensure_pip(root, directory, python)
    installed = _install_missing(root, directory, python)
    _runtime_probe(python, root)
    return Runtime(root, directory, python, created, installed, reused)


def _script_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"Skill script is not a regular non-symlink file: {path}", status="runtime_unusable")
    return path.resolve()


def run_script(cwd: str | Path | None, script: str | Path, argv: Sequence[str]) -> int:
    runtime = ensure_runtime(cwd)
    script_path = _script_path(script)
    args = tuple(argv)
    if any(type(item) is not str or "\x00" in item for item in args):
        raise RuntimeError("skill script arguments must be strings without NUL bytes", status="invalid_input")
    environment = _runtime_env(runtime.cwd, directory=runtime.directory)
    try:
        result = subprocess.run(
            [str(runtime.python), str(script_path), *args],
            cwd=str(runtime.cwd),
            env=environment,
            shell=False,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"Could not start skill script {script_path}: {_safe_text(exc)}", status="runtime_unusable") from exc
    return int(result.returncode)


def _parser() -> argparse.ArgumentParser:
    parser = RuntimeArgumentParser(description="Prepare the pixel-perfect skill's workspace-local .venv")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--script", type=Path)
    parser.add_argument("script_args", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        if args.script is None:
            runtime = ensure_runtime(args.cwd)
            print(json.dumps({"status": "ready", "runtime": runtime.as_dict()}, ensure_ascii=False, indent=2))
            return 0
        script_args = tuple(args.script_args)
        if script_args and script_args[0] == "--":
            script_args = script_args[1:]
        return run_script(args.cwd, args.script, script_args)
    except RuntimeError as exc:
        print(json.dumps({"status": exc.status, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["DEPENDENCIES", "Runtime", "RuntimeArgumentParser", "RuntimeBootstrapError", "RuntimeError", "ensure_runtime", "main", "run_script"]
