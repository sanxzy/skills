"""Localize visual error with a bounded adaptive Pillow grid."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

try:
    from ._common import (
        MAX_GRID_LEAVES,
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_report_path,
        checked_float,
        checked_int,
        crop_box,
        include_mask,
        json_result,
        load_ignore_mask,
        load_pair,
        metrics_for_images,
        parse_grid_spec,
        parse_hex_color,
        run_entrypoint,
        split_axis,
    )
except ImportError:  # pragma: no cover - direct executable path
    from _common import (  # type: ignore
        MAX_GRID_LEAVES,
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_report_path,
        checked_float,
        checked_int,
        crop_box,
        include_mask,
        json_result,
        load_ignore_mask,
        load_pair,
        metrics_for_images,
        parse_grid_spec,
        parse_hex_color,
        run_entrypoint,
        split_axis,
    )


def _cell_metrics(pair, mask, bbox: tuple[int, int, int, int], tolerance: int) -> dict[str, object]:
    local_mask = crop_box(mask, bbox)
    considered = sum(local_mask.histogram()[1:])
    if considered == 0:
        width, height = bbox[2], bbox[3]
        return {
            "width": width,
            "height": height,
            "total_pixels": width * height,
            "considered_pixels": 0,
            "ignored_pixels": width * height,
            "raw_changed_pixels": 0,
            "changed_pixels": 0,
            "difference_percentage": 0.0,
            "raw_difference_percentage": 0.0,
            "mean_color_difference": 0.0,
            "weighted_color_difference": 0.0,
            "tolerated_weighted_color_difference": 0.0,
            "color_similarity": 1.0,
            "tolerant_color_similarity": 1.0,
            "max_channel_mean_difference": 0.0,
            "bbox": None,
            "mean_edge_difference": None,
            "edge_changed_pixels": None,
            "edge_similarity": None,
            "similarity_score": 1.0,
            "mask_excluded": True,
        }
    result = metrics_for_images(
        crop_box(pair.reference.image, bbox),
        crop_box(pair.render.image, bbox),
        local_mask,
        tolerance=tolerance,
        calculate_edges=False,
    )
    result["mask_excluded"] = False
    return result


def _severity(metrics: dict[str, object]) -> float:
    percentage = float(metrics.get("difference_percentage", 0.0)) / 100.0
    mean_color = float(metrics.get("mean_color_difference", 0.0)) / 255.0
    return max(percentage, mean_color)


def _cell(path: str, level: int, bbox: tuple[int, int, int, int], metrics: dict[str, object]) -> dict[str, object]:
    return {
        "path": path,
        "level": level,
        "bbox": list(bbox),
        "severity": round(_severity(metrics), 6),
        "metrics": metrics,
    }


def _children(cell: dict[str, object], pair, mask, tolerance: int) -> list[dict[str, object]]:
    x, y, width, height = (int(value) for value in cell["bbox"])
    horizontal = split_axis(width, 2)
    vertical = split_axis(height, 2)
    children: list[dict[str, object]] = []
    for index, (top, bottom) in enumerate(vertical):
        for column, (left, right) in enumerate(horizontal):
            bbox = (x + left, y + top, right - left, bottom - top)
            child_path = f"{cell['path']}.{index * 2 + column + 1}"
            metrics = _cell_metrics(pair, mask, bbox, tolerance)
            children.append(_cell(child_path, int(cell["level"]) + 1, bbox, metrics))
    return children


def analyze_grid(
    reference: object,
    render: object,
    *,
    grid: str = "4x4",
    tolerance: int = 0,
    refine_threshold: float = 0.05,
    min_cell: int = 32,
    max_depth: int = 3,
    max_leaves: int = 256,
    top: int = 12,
    background: str = "#ffffff",
    ignore_mask: object | None = None,
    mask_reason: str | None = None,
    output: object | None = None,
) -> dict[str, object]:
    """Return coarse and refined full-image coordinates for high-error cells."""

    if ignore_mask is not None and not mask_reason:
        raise PixelPerfectError("an ignore mask requires an explicit --mask-reason")
    color = parse_hex_color(background)
    rows, columns = parse_grid_spec(grid)
    threshold = checked_float(refine_threshold, "refine threshold", minimum=0.0, maximum=1.0)
    minimum = checked_int(min_cell, "minimum cell size", minimum=1, maximum=4096)
    depth = checked_int(max_depth, "maximum grid depth", minimum=0, maximum=8)
    leaves_limit = checked_int(max_leaves, "maximum grid leaves", minimum=rows * columns, maximum=MAX_GRID_LEAVES)
    top_limit = checked_int(top, "hotspot count", minimum=1, maximum=100)
    pair = load_pair(reference, render, background=color)
    ignored = load_ignore_mask(ignore_mask, pair.size)
    mask = include_mask(ignored, pair.size)
    global_metrics = metrics_for_images(pair.reference.image, pair.render.image, mask, tolerance=tolerance)
    width, height = pair.size
    x_ranges = split_axis(width, columns)
    y_ranges = split_axis(height, rows)
    leaves: dict[str, dict[str, object]] = {}
    coarse: list[dict[str, object]] = []
    for row, (top_y, bottom_y) in enumerate(y_ranges):
        for column, (left_x, right_x) in enumerate(x_ranges):
            bbox = (left_x, top_y, right_x - left_x, bottom_y - top_y)
            path = f"r{row + 1}c{column + 1}"
            cell = _cell(path, 0, bbox, _cell_metrics(pair, mask, bbox, tolerance))
            coarse.append(cell)
            leaves[path] = cell

    refined_paths: list[str] = []
    while True:
        candidates = [
            item for item in leaves.values()
            if int(item["level"]) < depth
            and int(item["bbox"][2]) > minimum
            and int(item["bbox"][3]) > minimum
            and float(item["severity"]) > threshold
        ]
        if not candidates:
            break
        if len(leaves) + 3 > leaves_limit:
            break
        target = max(candidates, key=lambda item: (float(item["severity"]), -int(item["level"]), str(item["path"])))
        path = str(target["path"])
        del leaves[path]
        for child in _children(target, pair, mask, tolerance):
            leaves[str(child["path"])] = child
        refined_paths.append(path)

    leaves_list = sorted(leaves.values(), key=lambda item: tuple(int(value) for value in item["bbox"]))
    hotspots = sorted(
        leaves_list,
        key=lambda item: (-float(item["severity"]), str(item["path"])),
    )[:top_limit]
    if candidates and len(leaves) + 3 > leaves_limit:
        termination = "max-leaves"
    elif candidates:
        termination = "depth-or-min-cell"
    else:
        termination = "threshold-or-boundary"
    report: dict[str, object] = {
        "status": "complete",
        "operation": "adaptive-grid",
        "reference": pair.reference.info.as_dict(),
        "render": pair.render.info.as_dict(),
        "conditions": {
            "dimensions": list(pair.size),
            "background": "#%02x%02x%02x" % color,
            "tolerance": tolerance,
            "ignore_mask": str(Path(ignore_mask).expanduser().resolve()) if ignore_mask is not None else None,
            "mask_reason": mask_reason,
            "mask_semantics": "non-black mask pixels are excluded from comparison",
        },
        "global_metrics": global_metrics,
        "grid": {
            "rows": rows,
            "columns": columns,
            "refine_threshold": threshold,
            "minimum_cell": minimum,
            "maximum_depth": depth,
            "maximum_leaves": leaves_limit,
            "refined_paths": refined_paths,
            "termination": termination,
            "coordinate_space": "full normalized image pixels; bbox is [x, y, width, height]",
        },
        "coarse_cells": coarse,
        "leaves": leaves_list,
        "hotspots": hotspots,
    }
    return json_result(report, output=output)


def _parser() -> argparse.ArgumentParser:
    parser = PixelPerfectArgumentParser(description="Analyze visual error with an adaptive full-image grid")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--render", required=True, type=Path)
    parser.add_argument("--grid", default="4x4", help="coarse ROWSxCOLUMNS grid")
    parser.add_argument("--tolerance", type=int, default=0)
    parser.add_argument("--refine-threshold", type=float, default=0.05, help="refine cells whose severity exceeds this 0-1 value")
    parser.add_argument("--min-cell", type=int, default=32)
    parser.add_argument("--max-depth", type=int, default=3)
    parser.add_argument("--max-leaves", type=int, default=256)
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument("--background", default="#ffffff")
    parser.add_argument("--ignore-mask", type=Path)
    parser.add_argument("--mask-reason")
    parser.add_argument("--task-name", required=True, help="historical artifact task directory name")
    parser.add_argument("--output", type=Path, help="optional numeric-prefixed JSON path under the task artifact directory")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = analyze_grid(
        args.reference,
        args.render,
        grid=args.grid,
        tolerance=args.tolerance,
        refine_threshold=args.refine_threshold,
        min_cell=args.min_cell,
        max_depth=args.max_depth,
        max_leaves=args.max_leaves,
        top=args.top,
        background=args.background,
        ignore_mask=args.ignore_mask,
        mask_reason=args.mask_reason,
        output=artifact_report_path(args.task_name, "grid", args.output),
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


__all__ = ["analyze_grid", "main"]
