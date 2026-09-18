"""Run the smallest useful visual iteration: normalize, compare, and diff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

try:
    from ._common import (
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_report_path,
        artifact_stage,
        parse_hex_color,
        run_entrypoint,
        write_json,
    )
    from .analyze_grid import analyze_grid
    from .compare_images import compare_images
    from .generate_diff import generate_diff
    from .normalize_images import normalize_pair
except ImportError:  # pragma: no cover - direct executable path
    from _common import (  # type: ignore
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_report_path,
        artifact_stage,
        parse_hex_color,
        run_entrypoint,
        write_json,
    )
    from analyze_grid import analyze_grid  # type: ignore
    from compare_images import compare_images  # type: ignore
    from generate_diff import generate_diff  # type: ignore
    from normalize_images import normalize_pair  # type: ignore


def quick_run(
    reference: object,
    render: object,
    *,
    task_name: str,
    mode: str = "color-aware",
    tolerance: int = 0,
    background: str = "#ffffff",
    regions: object | None = None,
    with_grid: bool = False,
    grid: str = "4x4",
    cwd: object | None = None,
) -> dict[str, object]:
    """Create one append-only evidence chain without editing target code."""

    color = parse_hex_color(background)
    normalized = normalize_pair(
        reference,
        render,
        artifact_stage(task_name, "normalize", cwd=cwd),
        background=background,
    )
    normalized_reference = normalized["artifacts"]["reference"]
    normalized_render = normalized["artifacts"]["render"]
    comparison = compare_images(
        normalized_reference,
        normalized_render,
        mode=mode,
        tolerance=tolerance,
        background=background,
        regions=regions,
        output=artifact_report_path(task_name, "compare", cwd=cwd),
    )
    diff = generate_diff(
        normalized_reference,
        normalized_render,
        artifact_stage(task_name, "diff", cwd=cwd),
        tolerance=tolerance,
        background=background,
    )
    grid_result: dict[str, object] | None = None
    if with_grid:
        grid_result = analyze_grid(
            normalized_reference,
            normalized_render,
            grid=grid,
            tolerance=tolerance,
            background=background,
            output=artifact_report_path(task_name, "grid", cwd=cwd),
        )
    summary_path = artifact_report_path(task_name, "quick", cwd=cwd)
    summary: dict[str, object] = {
        "status": "complete",
        "operation": "quick",
        "task_name": task_name,
        "conditions": {
            "background": "#%02x%02x%02x" % color,
            "mode": mode,
            "tolerance": tolerance,
            "note": "quick mode performs mechanics only; inspect evidence and decide corrections as the agent",
        },
        "steps": [
            {"operation": "normalize", "artifacts": normalized["artifacts"]},
            {"operation": "compare", "artifacts": comparison.get("artifacts", {}), "metrics": comparison["metrics"]},
            {"operation": "diff", "artifacts": diff["artifacts"], "metrics": diff["metrics"]},
        ],
        "artifacts": {"report": str(summary_path.resolve())},
        "metrics": comparison["metrics"],
    }
    if grid_result is not None:
        summary["steps"].append({
            "operation": "grid",
            "artifacts": grid_result.get("artifacts", {}),
            "hotspots": grid_result.get("hotspots", []),
        })
    write_json(summary_path, summary)
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = PixelPerfectArgumentParser(description="Run normalize, compare, and diff for a fast visual iteration")
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--render", required=True, type=Path)
    parser.add_argument("--mode", choices=("exact", "tolerant", "region-weighted", "edge", "color-aware"), default="color-aware")
    parser.add_argument("--tolerance", type=int, default=0)
    parser.add_argument("--background", default="#ffffff")
    parser.add_argument("--regions", type=Path)
    parser.add_argument("--with-grid", action="store_true")
    parser.add_argument("--grid", default="4x4")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = quick_run(
        args.reference,
        args.render,
        task_name=args.task_name,
        mode=args.mode,
        tolerance=args.tolerance,
        background=args.background,
        regions=args.regions,
        with_grid=args.with_grid,
        grid=args.grid,
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


__all__ = ["main", "quick_run"]
