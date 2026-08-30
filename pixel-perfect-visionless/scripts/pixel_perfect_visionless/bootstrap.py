"""Workspace-local dependency and OCR toolchain bootstrap."""

from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

ENV_RELATIVE_PATH = Path(".xzy-env") / "pixel-perfect-visionless"
ARTIFACT_RELATIVE_PATH = Path(".artifacts") / "pixel-perfect-visionless"
REQUIRED_PACKAGES = (
    ("Pillow>=10", "PIL"),
    ("numpy>=2", "numpy"),
    ("opencv-python-headless>=4.10", "cv2"),
    ("pytesseract>=0.3.13", "pytesseract"),
)
PLAYWRIGHT_PACKAGE = "playwright>=1.45,<2"
TESSERACT_ENV = "PIXEL_PERFECT_VISIONLESS_TESSERACT"


class BootstrapError(RuntimeError):
    """Raised when the required visionless toolchain cannot be prepared."""


@dataclass(frozen=True)
class CommandRecord:
    command: tuple[str, ...]
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "command": list(self.command),
            "returncode": self.returncode,
            "stdout": self.stdout[-4000:],
            "stderr": self.stderr[-4000:],
        }
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class Runtime:
    project_root: Path
    workspace_root: Path
    directory: Path
    python: Path
    packages: dict[str, str | None]
    tesseract: Path
    tesseract_version: str
    tesseract_languages: tuple[str, ...]
    warnings: list[str] = field(default_factory=list)
    commands: list[CommandRecord] = field(default_factory=list)
    playwright_available: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "project_root": str(self.project_root),
            "workspace_root": str(self.workspace_root),
            "directory": str(self.directory),
            "python": str(self.python),
            "packages": dict(self.packages),
            "tesseract": str(self.tesseract),
            "tesseract_version": self.tesseract_version,
            "tesseract_languages": list(self.tesseract_languages),
            "warnings": list(self.warnings),
            "commands": self.command_records(),
            "playwright_available": self.playwright_available,
        }

    def command_records(self) -> list[dict[str, object]]:
        return [record.as_dict() for record in self.commands]


def runtime_directory(workspace_root: Path) -> Path:
    return Path(workspace_root) / ENV_RELATIVE_PATH


def artifact_directory(workspace_root: Path) -> Path:
    return Path(workspace_root) / ARTIFACT_RELATIVE_PATH


def runtime_python(directory: Path) -> Path:
    if os.name == "nt":
        return directory / "Scripts" / "python.exe"
    return directory / "bin" / "python"


def _run(
    command: list[str],
    *,
    check: bool = True,
    timeout: float = 300.0,
    env: Mapping[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], CommandRecord]:
    try:
        result = subprocess.run(
            command,
            check=False,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=dict(env) if env is not None else None,
        )
        record = CommandRecord(
            tuple(command), result.returncode, result.stdout or "", result.stderr or ""
        )
    except subprocess.TimeoutExpired as exc:
        record = CommandRecord(tuple(command), None, error=f"timed out after {timeout:.1f}s")
        if check:
            raise BootstrapError(_command_failure(record)) from exc
        return subprocess.CompletedProcess(command, 124, "", record.error or ""), record
    except OSError as exc:
        record = CommandRecord(tuple(command), None, error=str(exc))
        if check:
            raise BootstrapError(_command_failure(record)) from exc
        return subprocess.CompletedProcess(command, 127, "", str(exc)), record
    if check and result.returncode != 0:
        raise BootstrapError(_command_failure(record))
    return result, record


def _command_failure(record: CommandRecord) -> str:
    command = shlex.join(record.command)
    detail = (record.error or record.stderr or record.stdout).strip()
    return f"Command failed ({record.returncode}): {command}" + (f"\n{detail[-2000:]}" if detail else "")


def _module_available(python: Path, module: str) -> bool:
    result, _ = _run([str(python), "-c", f"import {module}"], check=False, timeout=60)
    return result.returncode == 0


def _module_version(python: Path, distribution: str) -> str | None:
    script = (
        "import importlib.metadata as m; "
        f"print(m.version({distribution!r}))"
    )
    result, _ = _run([str(python), "-c", script], check=False, timeout=60)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _historical_commands(directory: Path) -> list[CommandRecord]:
    metadata = directory / "environment.json"
    if not metadata.is_file():
        return []
    try:
        values = json.loads(metadata.read_text(encoding="utf-8")).get("commands", [])
    except (OSError, json.JSONDecodeError, AttributeError):
        return []
    records = []
    for value in values:
        if not isinstance(value, dict) or not isinstance(value.get("command"), list):
            continue
        records.append(
            CommandRecord(
                tuple(str(item) for item in value["command"]),
                value.get("returncode"),
                str(value.get("stdout", "")),
                str(value.get("stderr", "")),
                value.get("error"),
            )
        )
    return records


def _install_python_packages(python: Path, specs: Iterable[tuple[str, str]]) -> CommandRecord:
    packages = [package for package, _ in specs]
    _, record = _run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            *packages,
        ],
        timeout=1800,
    )
    return record


def _ensure_venv(directory: Path, base_python: Path) -> Path:
    python = runtime_python(directory)
    if python.exists():
        return python
    directory.parent.mkdir(parents=True, exist_ok=True)
    if directory.exists() and any(directory.iterdir()):
        raise BootstrapError(f"Environment path exists but is not a usable virtualenv: {directory}")
    _run([str(base_python), "-m", "venv", str(directory)], timeout=300)
    if not python.exists():
        raise BootstrapError(f"Virtualenv creation did not produce {python}")
    return python


def _validate_python_packages(python: Path) -> dict[str, str | None]:
    missing = [module for _, module in REQUIRED_PACKAGES if not _module_available(python, module)]
    if missing:
        raise BootstrapError(
            "Required Python modules are unavailable in the visionless environment: "
            + ", ".join(missing)
        )
    return {
        package.split(">=", 1)[0].split("==", 1)[0]: _module_version(
            python, package.split(">=", 1)[0].split("==", 1)[0]
        )
        for package, _ in REQUIRED_PACKAGES
    }


def _tesseract_candidates() -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get(TESSERACT_ENV)
    if configured:
        candidates.append(Path(configured).expanduser())
    found = shutil.which("tesseract")
    if found:
        candidates.append(Path(found))
    candidates.extend(
        [
            Path("/opt/homebrew/bin/tesseract"),
            Path("/usr/local/bin/tesseract"),
            Path("/usr/bin/tesseract"),
            Path(os.environ.get("PROGRAMFILES", "")) / "Tesseract-OCR/tesseract.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Tesseract-OCR/tesseract.exe",
        ]
    )
    return candidates


def find_tesseract() -> Path | None:
    seen: set[str] = set()
    for candidate in _tesseract_candidates():
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    return None


def _package_manager() -> str | None:
    if platform.system() == "Darwin" and shutil.which("brew"):
        return "brew"
    for name in ("apt-get", "dnf", "choco", "winget"):
        if shutil.which(name):
            return name
    return None


def _privileged_command(manager: str, args: list[str]) -> list[str]:
    if manager in {"apt-get", "dnf"} and hasattr(os, "geteuid") and os.geteuid() != 0:
        sudo = shutil.which("sudo")
        if not sudo:
            raise BootstrapError(
                f"{manager} requires root privileges and non-interactive sudo is unavailable"
            )
        return [sudo, "-n", manager, *args]
    return [manager, *args]


def _install_tesseract(manager: str) -> list[CommandRecord]:
    commands: list[list[str]]
    if manager == "brew":
        commands = [["brew", "install", "tesseract"]]
    elif manager == "apt-get":
        commands = [
            _privileged_command("apt-get", ["update", "-y"]),
            _privileged_command("apt-get", ["install", "-y", "tesseract-ocr", "tesseract-ocr-eng"]),
        ]
    elif manager == "dnf":
        commands = [
            _privileged_command("dnf", ["install", "-y", "tesseract", "tesseract-langpack-eng"])
        ]
    elif manager == "choco":
        commands = [["choco", "install", "tesseract", "-y", "--no-progress"]]
    elif manager == "winget":
        commands = [[
            "winget",
            "install",
            "--id",
            "UB-Mannheim.TesseractOCR",
            "--exact",
            "--silent",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ]]
    else:
        raise BootstrapError("No supported package manager is available for Tesseract installation")

    records: list[CommandRecord] = []
    for command in commands:
        _, record = _run(command, timeout=900)
        records.append(record)
    return records


def _tesseract_details(executable: Path) -> tuple[str, tuple[str, ...]]:
    version_result, _ = _run([str(executable), "--version"], check=False, timeout=60)
    if version_result.returncode != 0:
        raise BootstrapError(f"Tesseract is not executable: {executable}")
    version_lines = (version_result.stdout or version_result.stderr).splitlines()
    if not version_lines:
        raise BootstrapError(f"Tesseract did not report a version: {executable}")
    version = version_lines[0].strip()
    languages_result, _ = _run([str(executable), "--list-langs"], check=False, timeout=60)
    if languages_result.returncode != 0:
        raise BootstrapError(
            f"Tesseract cannot list language data: {executable}\n{languages_result.stderr.strip()}"
        )
    languages = tuple(
        line.strip()
        for line in languages_result.stdout.splitlines()
        if line.strip() and not line.lower().startswith("list of available")
    )
    return version, languages


def _ensure_tesseract(*, install: bool) -> tuple[Path, str, tuple[str, ...], list[CommandRecord], list[str]]:
    records: list[CommandRecord] = []
    warnings: list[str] = []
    executable = find_tesseract()
    if executable is None and install:
        manager = _package_manager()
        if manager:
            try:
                records.extend(_install_tesseract(manager))
            except BootstrapError as exc:
                detail = (
                    f"Tesseract installation via {manager} failed: {exc}. "
                    "Install Tesseract with English language data and rerun setup."
                )
                raise BootstrapError(detail) from exc
            executable = find_tesseract()
        else:
            warnings.append("No supported package manager was found for Tesseract")
    if executable is None:
        raise BootstrapError(
            "Required Tesseract binary was not found. Install Tesseract with English "
            "language data, then rerun setup."
        )
    version, languages = _tesseract_details(executable)
    if "eng" not in languages:
        if install:
            manager = _package_manager()
            if manager:
                try:
                    if manager == "brew":
                        records.extend(_run(["brew", "install", "tesseract-lang"], timeout=900)[1:2])
                    elif manager == "apt-get":
                        records.append(_run(_privileged_command("apt-get", ["install", "-y", "tesseract-ocr-eng"]), timeout=900)[1])
                    elif manager == "dnf":
                        records.append(_run(_privileged_command("dnf", ["install", "-y", "tesseract-langpack-eng"]), timeout=900)[1])
                    elif manager == "choco":
                        records.append(_run(["choco", "install", "tesseract", "-y", "--no-progress"], timeout=900)[1])
                    elif manager == "winget":
                        records.append(_run(["winget", "upgrade", "--id", "UB-Mannheim.TesseractOCR", "--exact", "--silent", "--accept-package-agreements", "--accept-source-agreements"], timeout=900)[1])
                except BootstrapError as exc:
                    raise BootstrapError(
                        f"Tesseract is installed but English language data is missing; "
                        f"language-data installation failed: {exc}"
                    ) from exc
                executable = find_tesseract() or executable
                version, languages = _tesseract_details(executable)
        if "eng" not in languages:
            raise BootstrapError(
                f"Tesseract language data 'eng' is unavailable at {executable}. "
                "Install the English traineddata package and rerun setup."
            )
    return executable, version, languages, records, warnings


def ensure_environment(
    project_root: Path,
    *,
    workspace_root: Path,
    install: bool = True,
    need_playwright: bool = False,
    base_python: Path | None = None,
) -> Runtime:
    """Prepare and validate the complete visionless toolchain."""

    project_root = Path(project_root).expanduser().resolve()
    workspace_root = Path(workspace_root).expanduser().resolve()
    if not project_root.is_dir():
        raise BootstrapError(f"Project root is not a directory: {project_root}")
    if not workspace_root.is_dir():
        raise BootstrapError(f"Workspace root is not a directory: {workspace_root}")

    directory = runtime_directory(workspace_root)
    base_python = Path(base_python or sys.executable).expanduser().resolve()
    python = runtime_python(directory)
    if not python.exists():
        if not install:
            raise BootstrapError(
                f"Missing visionless environment at {directory}; rerun without --no-auto-setup"
            )
        python = _ensure_venv(directory, base_python)

    command_records: list[CommandRecord] = _historical_commands(directory)
    if install and any(not _module_available(python, module) for _, module in REQUIRED_PACKAGES):
        command_records.append(_install_python_packages(python, REQUIRED_PACKAGES))
    packages = _validate_python_packages(python)

    tesseract, tesseract_version, languages, tesseract_records, warnings = _ensure_tesseract(
        install=install
    )
    command_records.extend(tesseract_records)
    playwright_available = _module_available(python, "playwright")
    if need_playwright and not playwright_available:
        if not install:
            raise BootstrapError(
                "Playwright is required for browser rendering; rerun without --no-auto-setup"
            )
        _, record = _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-input",
                PLAYWRIGHT_PACKAGE,
            ],
            timeout=1800,
        )
        command_records.append(record)
        playwright_available = _module_available(python, "playwright")
        if not playwright_available:
            raise BootstrapError("Playwright installation completed but import still fails")

    runtime = Runtime(
        project_root=project_root,
        workspace_root=workspace_root,
        directory=directory,
        python=python,
        packages=packages,
        tesseract=tesseract,
        tesseract_version=tesseract_version,
        tesseract_languages=languages,
        warnings=warnings,
        commands=command_records,
        playwright_available=playwright_available,
    )
    if install:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "environment.json").write_text(
            json.dumps(runtime.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return runtime


def ensure_playwright_browser(runtime: Runtime, *, install: bool = True) -> None:
    """Install Playwright Chromium once when a system browser is unavailable."""

    marker = runtime.directory / ".chromium-ready"
    if marker.exists():
        return
    if not install:
        raise BootstrapError(
            "Playwright Chromium is not installed; rerun without --no-auto-setup"
        )
    _run([str(runtime.python), "-m", "playwright", "install", "chromium"], timeout=1800)
    marker.write_text("ready\n", encoding="utf-8")


def is_runtime_python(runtime: Runtime) -> bool:
    try:
        return Path(sys.prefix).resolve() == runtime.directory.resolve()
    except OSError:
        return False
