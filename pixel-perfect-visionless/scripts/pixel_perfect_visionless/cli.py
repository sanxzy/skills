"""File-first CLI for the pixel-perfect-visionless skill."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .artifacts import ArtifactError, RunArtifacts
from .bootstrap import BootstrapError, ensure_environment, is_runtime_python


class CliError(RuntimeError):
    """Raised for a user-facing configuration error."""


def _runtime_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", default=".", help="Project checkout for local rendering (default: current directory)")
    parser.add_argument("--no-auto-setup", action="store_true", help="Do not create or install the workspace runtime")
    parser.add_argument("--output-dir", help="Artifact root relative to the invocation cwd")
    parser.add_argument("--runtime-ready", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--run-dir", help=argparse.SUPPRESS)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pixel-perfect-visionless",
        description="Compile screenshots into a deterministic UI IR for visionless agents.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup", help="Prepare and validate the complete OCR/visionless toolchain")
    _runtime_options(setup)
    setup.add_argument("--install-browser", action="store_true", help="Also install Playwright Chromium when no system browser exists")

    inspect = commands.add_parser("inspect", help="Persist reference image facts and toolchain evidence")
    _runtime_options(inspect)
    inspect.add_argument("--reference", required=True, help="Reference image path relative to cwd unless absolute")
    inspect.add_argument("--point", action="append", default=[], help="Pixel probe x,y (repeatable)")

    compile_command = commands.add_parser("compile", help="Compile one screenshot into UI IR and derived projections")
    _runtime_options(compile_command)
    compile_command.add_argument("--reference", required=True, help="Screenshot path relative to cwd unless absolute")
    compile_command.add_argument("--debug-artifacts", action="store_true", help="Persist preprocessing and detection overlays")

    render = commands.add_parser("render", help="Render one target at the reference viewport")
    _runtime_options(render)
    render.add_argument("--reference", help="Reference image used to derive viewport")
    render.add_argument("--viewport", help="Viewport WIDTHxHEIGHT when no reference is given")
    render.add_argument("--url", help="HTTP(S), file, data URL, or local workspace file")
    render.add_argument("--entry", help="Local entrypoint relative to project root")
    render.add_argument("--browser", help="Browser path or playwright")
    render.add_argument("--wait-ms", type=int, default=250)
    render.add_argument("--timeout", type=float, default=60.0)
    render.add_argument("--ready-selector")

    compare = commands.add_parser("compare", help="Persist pixel and structured differences for two screenshots")
    _runtime_options(compare)
    compare.add_argument("--reference", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--tolerance", type=int, default=10)
    compare.add_argument("--region", action="append", default=[], help="Named region name=x,y,width,height (repeatable)")
    compare.add_argument("--point", action="append", default=[], help="Pixel probe x,y (repeatable)")

    verify = commands.add_parser("verify", help="Render if needed, compare, and persist an acceptance verdict")
    _runtime_options(verify)
    verify.add_argument("--reference", required=True)
    verify.add_argument("--candidate")
    verify.add_argument("--url")
    verify.add_argument("--entry")
    verify.add_argument("--viewport")
    verify.add_argument("--browser")
    verify.add_argument("--wait-ms", type=int, default=250)
    verify.add_argument("--timeout", type=float, default=60.0)
    verify.add_argument("--ready-selector")
    verify.add_argument("--tolerance", type=int, default=10)
    verify.add_argument("--max-mae", type=float, default=10.0)
    verify.add_argument("--max-region-mae", type=float, default=None)
    verify.add_argument("--min-within-tolerance", type=float, default=0.85)
    verify.add_argument("--max-hotspot-mean-error", type=float, default=64.0)
    verify.add_argument("--region", action="append", default=[])
    verify.add_argument("--point", action="append", default=[])
    return parser


def _workspace() -> Path:
    return Path.cwd().resolve()


def _project_root(args: argparse.Namespace) -> Path:
    root = Path(args.project_root).expanduser()
    if not root.is_absolute():
        root = _workspace() / root
    root = root.resolve()
    if not root.is_dir():
        raise CliError(f"Project root is not a directory: {root}")
    return root


def _artifact_root(args: argparse.Namespace) -> Path | None:
    value = getattr(args, "output_dir", None)
    if value is None:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else _workspace() / path


def _operation_run(args: argparse.Namespace) -> RunArtifacts:
    run_dir = Path(args.run_dir).expanduser() if getattr(args, "run_dir", None) else None
    if run_dir is not None and not run_dir.is_absolute():
        run_dir = _workspace() / run_dir
    return RunArtifacts.from_workspace(
        _workspace(),
        args.command,
        output_root=_artifact_root(args),
        run_dir=run_dir,
    )


def _prepare_runtime(args: argparse.Namespace, writer: RunArtifacts, *, need_browser: bool = False) -> None:
    project = _project_root(args)
    needs_playwright = False
    if need_browser:
        from .browser import find_system_browser

        browser = getattr(args, "browser", None)
        needs_playwright = browser is not None and browser.lower() in {"playwright", "chromium-playwright"}
        if browser is None and find_system_browser() is None:
            needs_playwright = True
    runtime = ensure_environment(
        project,
        workspace_root=_workspace(),
        install=not args.no_auto_setup,
        need_playwright=needs_playwright,
    )
    if not args.runtime_ready and not is_runtime_python(runtime):
        script = Path(__file__).resolve().parents[1] / "pixel-perfect-visionless.py"
        forwarded = list(sys.argv[1:])
        if "--runtime-ready" not in forwarded:
            forwarded.append("--runtime-ready")
        if "--run-dir" not in forwarded:
            forwarded.extend(["--run-dir", str(writer.run_dir)])
        os.execv(str(runtime.python), [str(runtime.python), str(script), *forwarded])
        raise AssertionError("execv returned unexpectedly")


def _path(value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (_workspace() / path).resolve()


def _regions(values: list[str]) -> list[tuple[str, tuple[int, int, int, int]]]:
    from .images import parse_region

    return [parse_region(value) for value in values]


def _points(values: list[str]) -> list[tuple[int, int]]:
    from .images import parse_point

    return [parse_point(value) for value in values]


def _compiler(args: argparse.Namespace):
    from .compiler import Compiler

    return Compiler(
        workspace_root=_workspace(),
        project_root=_project_root(args),
        output_root=_artifact_root(args),
        install=not args.no_auto_setup,
    )


def _dispatch(args: argparse.Namespace, writer: RunArtifacts) -> dict[str, Any]:
    compiler = _compiler(args)
    if args.command == "setup":
        return compiler.setup(install_browser=args.install_browser, run_dir=writer.run_dir)
    if args.command == "inspect":
        return compiler.inspect(_path(args.reference), points=_points(args.point), run_dir=writer.run_dir)
    if args.command == "compile":
        return compiler.compile(_path(args.reference), debug_artifacts=args.debug_artifacts, run_dir=writer.run_dir)
    if args.command == "render":
        return compiler.render(
            url=args.url,
            entry=args.entry,
            reference=_path(args.reference),
            viewport=args.viewport,
            browser=args.browser,
            wait_ms=args.wait_ms,
            timeout=args.timeout,
            ready_selector=args.ready_selector,
            run_dir=writer.run_dir,
        )
    if args.command == "compare":
        return compiler.compare(
            _path(args.reference),
            _path(args.candidate),
            tolerance=args.tolerance,
            regions=_regions(args.region),
            points=_points(args.point),
            run_dir=writer.run_dir,
        )
    if args.command == "verify":
        return compiler.verify(
            _path(args.reference),
            candidate=_path(args.candidate),
            url=args.url,
            entry=args.entry,
            viewport=args.viewport,
            browser=args.browser,
            wait_ms=args.wait_ms,
            timeout=args.timeout,
            ready_selector=args.ready_selector,
            tolerance=args.tolerance,
            max_mae=args.max_mae,
            max_region_mae=args.max_region_mae,
            min_within_tolerance=args.min_within_tolerance,
            max_hotspot_mean_error=args.max_hotspot_mean_error,
            regions=_regions(args.region),
            points=_points(args.point),
            run_dir=writer.run_dir,
        )
    raise CliError(f"Unknown command: {args.command}")


def _pointer(status: str, writer: RunArtifacts) -> None:
    print(
        json.dumps(
            {
                "status": status,
                "operation": writer.operation,
                "run_dir": str(writer.run_dir),
                "result_json": str(writer.path("result.json")),
                "result_markdown": str(writer.path("result.md")),
            },
            sort_keys=True,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    writer: RunArtifacts | None = None
    try:
        writer = _operation_run(args)
        need_browser = args.command in {"render", "verify"} and (args.command == "render" or not args.candidate)
        _prepare_runtime(args, writer, need_browser=need_browser)
        result = _dispatch(args, writer)
        status = str(result.get("status", "ok"))
        _pointer(status, writer)
        return 0 if status in {"ok", "pass", "ready"} else 1
    except Exception as exc:
        if writer is None:
            try:
                writer = RunArtifacts.from_workspace(
                    _workspace(),
                    args.command,
                    output_root=_artifact_root(args),
                )
            except Exception:
                writer = None
        if writer is not None:
            try:
                writer.finalize({"status": "error", "operation": args.command, "error": str(exc), "error_type": type(exc).__name__})
            except Exception:
                pass
            _pointer("error", writer)
        else:
            print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2
