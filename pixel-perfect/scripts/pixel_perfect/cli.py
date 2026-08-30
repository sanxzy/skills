"""Public command-line interface for the pixel-perfect skill."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .bootstrap import (
    BootstrapError,
    Runtime,
    ensure_environment,
    is_runtime_python,
)
from .browser import BrowserError, find_system_browser
from .project import inspect_project
from .reporting import (
    verification_markdown,
    write_comparison_reports,
    write_json,
)


class CliError(RuntimeError):
    """Raised for a user-facing CLI error."""


def _add_runtime_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project checkout used for source inspection and local entrypoints (default: .)",
    )
    parser.add_argument(
        "--no-auto-setup",
        action="store_true",
        help="Do not create/install the workspace-local environment",
    )
    parser.add_argument(
        "--runtime-ready",
        action="store_true",
        help=argparse.SUPPRESS,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pixel-perfect",
        description="Render, compare, and diagnose UI screenshots with text-readable evidence.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup", help="Create or repair the workspace-local runtime")
    _add_runtime_options(setup)
    setup.add_argument(
        "--install-browser",
        action="store_true",
        help="Also install Playwright Chromium when no system browser is available",
    )

    inspect = commands.add_parser(
        "inspect", help="Inspect the reference image and project without rendering"
    )
    _add_runtime_options(inspect)
    inspect.add_argument("--reference", required=True, help="Reference image path")
    inspect.add_argument(
        "--output",
        help="JSON output path (relative to the invocation cwd unless absolute; default: .artifacts/pixel-perfect/inspection.json)",
    )
    inspect.add_argument(
        "--no-project",
        action="store_true",
        help="Omit project reconnaissance from the JSON report",
    )
    inspect.add_argument(
        "--point",
        action="append",
        default=[],
        help="Pixel probe x,y (repeatable)",
    )

    decompose = commands.add_parser(
        "decompose", help="Create a structured section plan from reference evidence"
    )
    _add_runtime_options(decompose)
    decompose.add_argument("--reference", required=True, help="Reference image path")
    decompose.add_argument(
        "--sections-file",
        help="Optional JSON array/object defining rich section contracts",
    )
    decompose.add_argument(
        "--section",
        action="append",
        default=[],
        help="Named section bounds: id=x,y,width,height (repeatable)",
    )
    decompose.add_argument(
        "--output-dir",
        default=".artifacts/pixel-perfect",
        help="Artifact/report directory relative to the invocation cwd",
    )

    render = commands.add_parser("render", help="Capture one deterministic viewport screenshot")
    _add_runtime_options(render)
    render.add_argument("--reference", help="Reference image; derives viewport dimensions")
    render.add_argument("--viewport", help="Viewport as WIDTHxHEIGHT when no reference is given")
    render.add_argument("--url", help="HTTP(S), file, data URL, or local file path")
    render.add_argument("--entry", help="Local entrypoint relative to the project root")
    render.add_argument(
        "--output",
        required=True,
        help="Screenshot output path (relative to the invocation cwd unless absolute)",
    )
    render.add_argument(
        "--browser",
        help="Browser executable path, or 'playwright' to force the bundled adapter",
    )
    render.add_argument("--wait-ms", type=int, default=250)
    render.add_argument("--timeout", type=float, default=60.0)
    render.add_argument("--ready-selector")
    render.add_argument(
        "--report",
        help="JSON render report path (relative to the invocation cwd unless absolute; default: next to the screenshot)",
    )

    compare = commands.add_parser(
        "compare", help="Compare two same-size images and write machine-readable reports"
    )
    _add_runtime_options(compare)
    compare.add_argument("--reference", required=True, help="Reference image path")
    compare.add_argument("--candidate", required=True, help="Rendered candidate image path")
    compare.add_argument(
        "--output-dir",
        default=".artifacts/pixel-perfect",
        help="Artifact/report directory relative to the invocation cwd",
    )
    compare.add_argument("--tolerance", type=int, default=10)
    compare.add_argument("--tile-size", type=int, default=64)
    compare.add_argument(
        "--region",
        action="append",
        default=[],
        help="Named region: name=x,y,width,height (repeatable)",
    )
    compare.add_argument(
        "--point",
        action="append",
        default=[],
        help="Pixel probe x,y (repeatable)",
    )

    verify = commands.add_parser(
        "verify", help="Render if needed, compare, smoke-check, and return an acceptance verdict"
    )
    _add_runtime_options(verify)
    verify.add_argument("--reference", required=True, help="Reference image path")
    verify.add_argument("--candidate", help="Existing candidate screenshot; otherwise render one")
    verify.add_argument("--url", help="HTTP(S), file, data URL, or local file path")
    verify.add_argument("--entry", help="Local entrypoint relative to the project root")
    verify.add_argument("--viewport", help="Override reference viewport as WIDTHxHEIGHT")
    verify.add_argument(
        "--responsive-viewport",
        action="append",
        default=[],
        help="Additional smoke viewport WIDTHxHEIGHT (repeatable)",
    )
    verify.add_argument("--browser")
    verify.add_argument("--wait-ms", type=int, default=250)
    verify.add_argument("--timeout", type=float, default=60.0)
    verify.add_argument("--ready-selector")
    verify.add_argument(
        "--output-dir",
        default=".artifacts/pixel-perfect",
        help="Artifact/report directory relative to the invocation cwd",
    )
    verify.add_argument("--tolerance", type=int, default=10)
    verify.add_argument("--tile-size", type=int, default=64)
    verify.add_argument("--max-mae", type=float, default=10.0)
    verify.add_argument(
        "--max-region-mae",
        type=float,
        default=None,
        help="Maximum mean error for each named region (default: max-mae * 1.5)",
    )
    verify.add_argument("--min-within-tolerance", type=float, default=0.85)
    verify.add_argument(
        "--max-hotspot-mean-error",
        type=float,
        default=64.0,
        help="Maximum mean error allowed in the hottest analysis tile",
    )
    verify.add_argument(
        "--region",
        action="append",
        default=[],
        help="Named region: name=x,y,width,height (repeatable)",
    )
    verify.add_argument(
        "--point",
        action="append",
        default=[],
        help="Pixel probe x,y (repeatable)",
    )
    verify.add_argument(
        "--previous-report",
        help="Previous comparison.json; checks overall and named-region MAE for regression",
    )
    verify.add_argument(
        "--regression-tolerance",
        type=float,
        default=0.5,
        help="Allowed MAE increase over --previous-report",
    )
    return parser


def _workspace_root() -> Path:
    return Path.cwd().resolve()


def _project_root(args: argparse.Namespace) -> Path:
    root = Path(args.project_root).expanduser()
    if not root.is_absolute():
        root = _workspace_root() / root
    root = root.resolve()
    if not root.is_dir():
        raise CliError(f"Project root is not a directory: {root}")
    return root


def _path(base: Path, value: str | None, default: str | None = None) -> Path | None:
    raw = value if value is not None else default
    if raw is None:
        return None
    result = Path(raw).expanduser()
    return result if result.is_absolute() else base / result


def _needs_playwright(browser: str | None) -> bool:
    if browser and browser.lower() in {"playwright", "chromium-playwright"}:
        return True
    return browser is None and find_system_browser() is None


def _prepare_runtime(
    args: argparse.Namespace,
    *,
    need_browser: bool = False,
) -> tuple[Path, Path, Runtime]:
    workspace = _workspace_root()
    root = _project_root(args)
    install = not args.no_auto_setup
    need_playwright = need_browser and _needs_playwright(getattr(args, "browser", None))
    runtime = ensure_environment(
        root,
        workspace_root=workspace,
        install=install,
        need_playwright=need_playwright,
    )

    if not args.runtime_ready and not is_runtime_python(runtime):
        script = Path(__file__).resolve().parents[1] / "pixel-perfect.py"
        forwarded = list(sys.argv[1:])
        if "--runtime-ready" not in forwarded:
            forwarded.append("--runtime-ready")
        os.execv(str(runtime.python), [str(runtime.python), str(script), *forwarded])
        raise AssertionError("execv returned unexpectedly")
    return root, workspace, runtime


def _json_print(data: dict[str, Any]) -> None:
    print(json.dumps(data, sort_keys=True))


def _pointer(
    status: str,
    operation: str,
    *,
    output_dir: Path | None = None,
    reports: dict[str, str] | None = None,
    artifacts: dict[str, str] | None = None,
    **context: Any,
) -> None:
    pointer: dict[str, Any] = {"status": status, "operation": operation}
    if output_dir is not None:
        pointer["output_dir"] = str(output_dir.resolve())
    if reports:
        pointer["reports"] = reports
    if artifacts:
        pointer["artifacts"] = artifacts
    pointer.update(context)
    _json_print(pointer)


def _default_artifact_dir(workspace: Path) -> Path:
    return workspace / ".artifacts" / "pixel-perfect"


def _render_report_path(output: Path) -> Path:
    report = output.with_suffix(".json")
    return report if report != output else output.with_name(f"{output.name}.report.json")


def _error_directory(args: argparse.Namespace, workspace: Path) -> Path:
    output_dir = getattr(args, "output_dir", None)
    if output_dir:
        path = _path(workspace, output_dir)
        assert path is not None
        return path
    for option in ("report", "output"):
        value = getattr(args, option, None)
        if value:
            path = _path(workspace, value)
            assert path is not None
            return path.parent
    return _default_artifact_dir(workspace)


def _persist_error(args: argparse.Namespace, workspace: Path, exc: Exception) -> Path | None:
    directory = _error_directory(args, workspace)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = directory / f"{args.command}-error-{timestamp}-{os.getpid()}.json"
    try:
        write_json(
            path,
            {
                "status": "error",
                "operation": args.command,
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        )
    except Exception:
        return None
    return path


def _error_summary(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return type(exc).__name__
    return message.splitlines()[0][:500]


def _parse_regions(values: list[str], size: tuple[int, int]) -> list[tuple[str, tuple[int, int, int, int]]]:
    from .images import parse_region

    parsed = [parse_region(value) for value in values]
    width, height = size
    for name, (x, y, region_width, region_height) in parsed:
        if x < 0 or y < 0 or x + region_width > width or y + region_height > height:
            raise CliError(
                f"Region {name!r} falls outside image {width}x{height}: "
                f"{x},{y},{region_width},{region_height}"
            )
    return parsed


def _parse_points(values: list[str], size: tuple[int, int]) -> list[tuple[int, int]]:
    from .images import parse_point, validate_points

    return validate_points([parse_point(value) for value in values], size)


def _cmd_decompose(args: argparse.Namespace) -> int:
    root, workspace, runtime = _prepare_runtime(args)
    from .decomposition import decomposition_markdown, load_and_build
    from .images import inspect_image

    reference = _path(workspace, args.reference)
    output_dir = _path(workspace, args.output_dir)
    sections_file = _path(workspace, args.sections_file)
    assert reference is not None and output_dir is not None
    if sections_file is not None and not sections_file.is_file():
        raise CliError(f"Sections file not found: {sections_file}")
    reference_info = inspect_image(reference)
    project_info = inspect_project(root)
    section_specs = [_parse_section(value) for value in args.section]
    plan = load_and_build(
        reference_info,
        project_info,
        sections_file=sections_file,
        section_specs=section_specs,
        reference_path=reference,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "decomposition.json"
    markdown_path = output_dir / "decomposition.md"
    plan["runtime"] = runtime.as_dict()
    write_json(json_path, plan)
    markdown_path.write_text(decomposition_markdown(plan), encoding="utf-8")
    _pointer(
        plan["status"],
        "decompose",
        output_dir=output_dir,
        reports={"json": str(json_path), "markdown": str(markdown_path)},
    )
    return 0


def _parse_section(value: str) -> tuple[str, tuple[int, int, int, int]]:
    from .images import parse_region

    return parse_region(value)


def _cmd_setup(args: argparse.Namespace) -> int:
    workspace = _workspace_root()
    root = _project_root(args)
    runtime = ensure_environment(
        root,
        workspace_root=workspace,
        install=not args.no_auto_setup,
        need_playwright=args.install_browser,
    )
    if args.install_browser and not args.no_auto_setup:
        from .browser import browser_plan

        browser_plan(runtime, explicit="playwright", install=True)
    report_path = _default_artifact_dir(workspace) / "setup.json"
    write_json(
        report_path,
        {
            "status": "ready",
            "operation": "setup",
            "runtime": runtime.as_dict(),
        },
    )
    _pointer(
        "ready",
        "setup",
        output_dir=report_path.parent,
        reports={"json": str(report_path)},
        runtime_dir=str(runtime.directory),
        runtime_python=str(runtime.python),
    )
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    root, workspace, runtime = _prepare_runtime(args)
    from .images import inspect_image, parse_point
    reference = _path(workspace, args.reference)
    assert reference is not None
    image_report = inspect_image(
        reference, points=[parse_point(value) for value in args.point]
    )
    report_path = _path(workspace, args.output)
    if report_path is None:
        report_path = _default_artifact_dir(workspace) / "inspection.json"
    result: dict[str, Any] = {
        "status": "ok",
        "reference": image_report,
        "runtime": runtime.as_dict(),
        "report": str(report_path),
    }
    if not args.no_project:
        result["project"] = inspect_project(root)
    write_json(report_path, result)
    _pointer(
        "ok",
        "inspect",
        output_dir=report_path.parent,
        reports={"json": str(report_path)},
        reference=str(reference),
        viewport=image_report["viewport"],
    )
    return 0


def _reference_viewport(workspace: Path, reference: str | None, viewport: str | None) -> str:
    from .images import inspect_image, parse_viewport

    if viewport:
        parse_viewport(viewport)
        return viewport
    if not reference:
        raise CliError("Provide --reference or --viewport")
    reference_path = _path(workspace, reference)
    assert reference_path is not None
    info = inspect_image(reference_path)
    return info["viewport"]


def _cmd_render(args: argparse.Namespace) -> int:
    root, workspace, runtime = _prepare_runtime(args, need_browser=True)
    from .rendering import render_target, resolve_target_url
    reference = _path(workspace, args.reference)
    viewport = _reference_viewport(workspace, args.reference, args.viewport)
    url = resolve_target_url(root, workspace_root=workspace, url=args.url, entry=args.entry)
    output = _path(workspace, args.output)
    assert output is not None
    result = render_target(
        runtime,
        url=url,
        output=output,
        viewport=viewport,
        browser=args.browser,
        wait_ms=args.wait_ms,
        timeout=args.timeout,
        ready_selector=args.ready_selector,
        install=not args.no_auto_setup,
    )
    result["status"] = "ok"
    result["viewport"] = viewport
    result["runtime"] = runtime.as_dict()
    if reference:
        result["reference"] = str(reference)
    report_path = _path(workspace, args.report) or _render_report_path(output)
    result["report"] = str(report_path)
    write_json(report_path, result)
    _pointer(
        "ok",
        "render",
        output_dir=report_path.parent,
        reports={"json": str(report_path)},
        artifacts={"candidate": str(output)},
        viewport=viewport,
    )
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    root, workspace, runtime = _prepare_runtime(args)
    from .images import compare_images, inspect_image, save_visual_artifacts
    reference = _path(workspace, args.reference)
    candidate = _path(workspace, args.candidate)
    output_dir = _path(workspace, args.output_dir)
    assert reference is not None and candidate is not None and output_dir is not None
    reference_info = inspect_image(reference)
    image_size = (reference_info["width"], reference_info["height"])
    regions = _parse_regions(args.region, image_size)
    points = _parse_points(args.point, image_size)
    report, reference_image, candidate_image = compare_images(
        reference,
        candidate,
        regions=regions,
        tolerance=args.tolerance,
        tile_size=args.tile_size,
        points=points,
    )
    artifacts = save_visual_artifacts(
        reference_image, candidate_image, output_dir, tolerance=args.tolerance
    )
    reports = write_comparison_reports(report, output_dir)
    _pointer(
        "ok",
        "compare",
        output_dir=output_dir,
        reports=reports,
        artifacts=artifacts,
        reference=str(reference.resolve()),
        candidate=str(candidate.resolve()),
        viewport=report["viewport"],
    )
    return 0


def _comparison_checks(
    report: dict[str, Any],
    *,
    max_mae: float,
    max_region_mae: float | None,
    min_within: float,
    max_hotspot: float,
) -> list[dict[str, Any]]:
    metrics = report["metrics"]
    checks = [
        {
            "name": "dimensions",
            "status": "pass",
            "detail": f"reference and candidate are both {report['viewport']}",
        },
        {
            "name": "mean_abs_error",
            "status": "pass" if metrics["mean_abs_error"] <= max_mae else "fail",
            "detail": f"{metrics['mean_abs_error']:.4f} <= {max_mae:.4f}",
        },
        {
            "name": "within_tolerance_fraction",
            "status": "pass"
            if metrics["within_tolerance_fraction"] >= min_within
            else "fail",
            "detail": f"{metrics['within_tolerance_fraction']:.4f} >= {min_within:.4f}",
        },
    ]
    hotspots = metrics.get("tile_hotspots", [])
    hottest = hotspots[0]["mean_error"] if hotspots else 0.0
    checks.append(
        {
            "name": "hottest_tile",
            "status": "pass" if hottest <= max_hotspot else "fail",
            "detail": f"{hottest:.4f} <= {max_hotspot:.4f}",
        }
    )
    if report.get("regions"):
        region_limit = max_region_mae if max_region_mae is not None else max_mae * 1.5
        for region in report["regions"]:
            checks.append(
                {
                    "name": f"region_{region['name']}_mean_abs_error",
                    "status": "pass"
                    if region["mean_abs_error"] <= region_limit
                    else "fail",
                    "detail": f"{region['mean_abs_error']:.4f} <= {region_limit:.4f}",
                }
            )
    return checks


def _regression_checks(
    current: dict[str, Any], previous_path: Path | None, allowed_increase: float
) -> list[dict[str, Any]]:
    if previous_path is None:
        return []
    if not previous_path.is_file():
        raise CliError(f"Previous report not found: {previous_path}")
    try:
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        previous_mae = float(previous["metrics"]["mean_abs_error"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise CliError(f"Invalid previous comparison report: {previous_path}: {exc}") from exc
    current_mae = float(current["metrics"]["mean_abs_error"])
    checks = [
        {
            "name": "no_mae_regression",
            "status": "pass" if current_mae <= previous_mae + allowed_increase else "fail",
            "detail": f"current {current_mae:.4f} <= previous {previous_mae:.4f} + {allowed_increase:.4f}",
        }
    ]
    previous_regions = {
        region.get("name"): region
        for region in previous.get("regions", [])
        if region.get("name")
    }
    for region in current.get("regions", []):
        previous_region = previous_regions.get(region.get("name"))
        if previous_region is None:
            continue
        current_region_mae = float(region["mean_abs_error"])
        previous_region_mae = float(previous_region["mean_abs_error"])
        checks.append(
            {
                "name": f"no_region_regression_{region['name']}",
                "status": "pass"
                if current_region_mae <= previous_region_mae + allowed_increase
                else "fail",
                "detail": f"current {current_region_mae:.4f} <= previous {previous_region_mae:.4f} + {allowed_increase:.4f}",
            }
        )
    return checks


def _cmd_verify(args: argparse.Namespace) -> int:
    root, workspace, runtime = _prepare_runtime(args, need_browser=args.candidate is None or bool(args.responsive_viewport))
    from .images import compare_images, inspect_image, parse_viewport, save_visual_artifacts
    from .rendering import render_target, resolve_target_url, smoke_check
    reference = _path(workspace, args.reference)
    output_dir = _path(workspace, args.output_dir)
    assert reference is not None and output_dir is not None
    output_dir.mkdir(parents=True, exist_ok=True)
    reference_info = inspect_image(reference)
    viewport = args.viewport or reference_info["viewport"]
    parse_viewport(viewport)
    image_size = (reference_info["width"], reference_info["height"])
    regions = _parse_regions(args.region, image_size)
    points = _parse_points(args.point, image_size)

    render_result: dict[str, Any] | None = None
    if args.candidate:
        candidate = _path(workspace, args.candidate)
        assert candidate is not None
    else:
        url = resolve_target_url(root, workspace_root=workspace, url=args.url, entry=args.entry)
        candidate = output_dir / "candidate.png"
        render_result = render_target(
            runtime,
            url=url,
            output=candidate,
            viewport=viewport,
            browser=args.browser,
            wait_ms=args.wait_ms,
            timeout=args.timeout,
            ready_selector=args.ready_selector,
            install=not args.no_auto_setup,
        )

    report, reference_image, candidate_image = compare_images(
        reference,
        candidate,
        regions=regions,
        tolerance=args.tolerance,
        tile_size=args.tile_size,
        points=points,
    )
    artifacts = save_visual_artifacts(
        reference_image, candidate_image, output_dir, tolerance=args.tolerance
    )
    comparison_reports = write_comparison_reports(report, output_dir)
    checks = _comparison_checks(
        report,
        max_mae=args.max_mae,
        max_region_mae=args.max_region_mae,
        min_within=args.min_within_tolerance,
        max_hotspot=args.max_hotspot_mean_error,
    )

    smoke = smoke_check(candidate)
    checks.append(
        {
            "name": "candidate_smoke",
            "status": smoke["status"],
            "detail": f"{smoke['sample_unique_colors']} sampled colors; non_flat={smoke['non_flat']}",
        }
    )
    if render_result is not None:
        browser_errors = render_result.get("console_errors", []) + render_result.get("page_errors", [])
        checks.append(
            {
                "name": "browser_runtime_errors",
                "status": "pass" if not browser_errors else "fail",
                "detail": "none" if not browser_errors else "; ".join(browser_errors[:5]),
            }
        )

    responsive_results = []
    for index, responsive_viewport in enumerate(args.responsive_viewport, start=1):
        parse_viewport(responsive_viewport)
        url = resolve_target_url(root, workspace_root=workspace, url=args.url, entry=args.entry)
        responsive_output = output_dir / f"responsive-{index}.png"
        responsive_render = render_target(
            runtime,
            url=url,
            output=responsive_output,
            viewport=responsive_viewport,
            browser=args.browser,
            wait_ms=args.wait_ms,
            timeout=args.timeout,
            ready_selector=args.ready_selector,
            install=not args.no_auto_setup,
        )
        responsive_smoke = smoke_check(responsive_output)
        responsive_results.append(
            {
                "viewport": responsive_viewport,
                "render": responsive_render,
                "smoke": responsive_smoke,
            }
        )
        responsive_errors = responsive_render.get("console_errors", []) + responsive_render.get("page_errors", [])
        checks.append(
            {
                "name": f"responsive_smoke_{responsive_viewport}",
                "status": "pass"
                if responsive_smoke["status"] == "pass" and not responsive_errors
                else "fail",
                "detail": "rendered and non-flat"
                if responsive_smoke["status"] == "pass" and not responsive_errors
                else "responsive render or runtime errors detected",
            }
        )

    checks.extend(
        _regression_checks(
            report,
            _path(workspace, args.previous_report),
            args.regression_tolerance,
        )
    )

    passed = all(check["status"] == "pass" for check in checks)
    result = {
        "status": "pass" if passed else "fail",
        "viewport": viewport,
        "candidate": str(candidate.resolve()),
        "reference": str(reference.resolve()),
        "checks": checks,
        "comparison": report,
        "artifacts": artifacts,
        "reports": comparison_reports,
        "smoke": smoke,
        "responsive": responsive_results,
        "render": render_result,
        "warnings": list(runtime.warnings),
        "runtime": runtime.as_dict(),
    }
    verification_json = output_dir / "verification.json"
    verification_md = output_dir / "verification.md"
    result["verification_reports"] = {
        "json": str(verification_json),
        "markdown": str(verification_md),
    }
    write_json(verification_json, result)
    verification_md.write_text(verification_markdown(result), encoding="utf-8")
    _pointer(
        result["status"],
        "verify",
        output_dir=output_dir,
        reports={
            "comparison_json": comparison_reports["json"],
            "comparison_markdown": comparison_reports["markdown"],
            "verification_json": str(verification_json),
            "verification_markdown": str(verification_md),
        },
        artifacts={**artifacts, "candidate": str(candidate.resolve())},
        reference=str(reference.resolve()),
        viewport=viewport,
        failed_checks=[check["name"] for check in checks if check["status"] != "pass"],
    )
    return 0 if passed else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "setup":
            return _cmd_setup(args)
        if args.command == "inspect":
            return _cmd_inspect(args)
        if args.command == "decompose":
            return _cmd_decompose(args)
        if args.command == "render":
            return _cmd_render(args)
        if args.command == "compare":
            return _cmd_compare(args)
        if args.command == "verify":
            return _cmd_verify(args)
        raise CliError(f"Unknown command: {args.command}")
    except (BootstrapError, BrowserError, CliError, RuntimeError, ValueError) as exc:
        error_report = _persist_error(args, _workspace_root(), exc)
        payload: dict[str, Any] = {
            "status": "error",
            "operation": args.command,
            "error": _error_summary(exc),
        }
        if error_report is not None:
            payload.update(
                {
                    "output_dir": str(error_report.parent.resolve()),
                    "error_report": str(error_report.resolve()),
                }
            )
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)
        return 2
