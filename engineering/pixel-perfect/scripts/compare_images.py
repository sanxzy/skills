"""Compare two renders with deterministic Pillow metrics."""

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
        comparison_report,
        json_result,
        load_ignore_mask,
        load_pair,
        load_regions,
        parse_hex_color,
        run_entrypoint,
    )
except ImportError:  # pragma: no cover - direct executable path
    from _common import (  # type: ignore
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_report_path,
        comparison_report,
        json_result,
        load_ignore_mask,
        load_pair,
        load_regions,
        parse_hex_color,
        run_entrypoint,
    )


def compare_images(
    reference: object,
    render: object,
    *,
    mode: str = "color-aware",
    tolerance: int = 0,
    background: str = "#ffffff",
    ignore_mask: object | None = None,
    mask_reason: str | None = None,
    regions: object | None = None,
    output: object | None = None,
    structure_background: str | None = None,
    structure_tolerance: int = 0,
) -> dict[str, object]:
    """Return and optionally persist the canonical comparison report."""

    color = parse_hex_color(background)
    pair = load_pair(reference, render, background=color)
    mask = load_ignore_mask(ignore_mask, pair.size)
    region_specs = load_regions(regions, pair.size)
    structure_color = (
        parse_hex_color(structure_background)
        if structure_background is not None
        else None
    )
    report = comparison_report(
        pair,
        mode=mode,
        tolerance=tolerance,
        ignore_mask=mask,
        ignore_mask_path=ignore_mask,
        mask_reason=mask_reason,
        regions=region_specs,
        structure_background=structure_color,
        structure_tolerance=structure_tolerance,
    )
    return json_result(report, output=output)


def _parser() -> argparse.ArgumentParser:
    parser = PixelPerfectArgumentParser(description="Measure visual differences between reference and render images")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--render", required=True, type=Path)
    parser.add_argument(
        "--mode",
        choices=("exact", "tolerant", "region-weighted", "edge", "color-aware"),
        default="color-aware",
    )
    parser.add_argument("--tolerance", type=int, default=0, help="per-channel difference ignored by changed-pixel metrics (0-255)")
    parser.add_argument("--background", default="#ffffff", help="opaque RGB backdrop for alpha images")
    parser.add_argument("--ignore-mask", type=Path, help="mask whose non-black pixels are excluded")
    parser.add_argument("--mask-reason", help="required explanation when --ignore-mask is used")
    parser.add_argument("--regions", type=Path, help="JSON list of weighted/critical regions")
    parser.add_argument("--structure-background", help="optional #RRGGBB canvas color for coarse content-bound geometry")
    parser.add_argument("--structure-tolerance", type=int, default=0)
    parser.add_argument("--task-name", required=True, help="historical artifact task directory name")
    parser.add_argument("--output", type=Path, help="optional numeric-prefixed JSON path under the task artifact directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = compare_images(
        args.reference,
        args.render,
        mode=args.mode,
        tolerance=args.tolerance,
        background=args.background,
        ignore_mask=args.ignore_mask,
        mask_reason=args.mask_reason,
        regions=args.regions,
        output=artifact_report_path(args.task_name, "compare", args.output),
        structure_background=args.structure_background,
        structure_tolerance=args.structure_tolerance,
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


__all__ = ["compare_images", "main"]
