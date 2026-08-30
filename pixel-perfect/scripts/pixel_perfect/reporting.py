"""Stable JSON and Markdown reports for model-readable visual verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _format_metric(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def comparison_markdown(report: dict[str, Any]) -> str:
    metrics = report.get("metrics", {})
    lines = [
        "# Pixel-perfect comparison",
        "",
        f"- Reference: `{report.get('reference')}`",
        f"- Candidate: `{report.get('candidate')}`",
        f"- Viewport: `{report.get('viewport')}`",
        f"- Analysis engine: `{metrics.get('analysis_engine', 'unknown')}`",
        "",
        "## Overall metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key in (
        "mean_abs_error",
        "exact_fraction",
        "within_tolerance_fraction",
        "mismatch_fraction",
        "mismatch_pixels",
        "max_error",
        "tolerance",
    ):
        if key in metrics:
            lines.append(f"| `{key}` | `{_format_metric(metrics[key])}` |")

    regions = report.get("regions", [])
    if regions:
        lines.extend(
            [
                "",
                "## Regions",
                "",
                "| Region | Box | Mean error | Within tolerance | Mismatch fraction |",
                "| --- | --- | ---: | ---: | ---: |",
            ]
        )
        for region in regions:
            lines.append(
                "| `{name}` | `{box}` | `{error}` | `{within}` | `{mismatch}` |".format(
                    name=region.get("name"),
                    box=",".join(str(value) for value in region.get("box", [])),
                    error=_format_metric(region.get("mean_abs_error", "n/a")),
                    within=_format_metric(region.get("within_tolerance_fraction", "n/a")),
                    mismatch=_format_metric(region.get("mismatch_fraction", "n/a")),
                )
            )

    bbox = metrics.get("mismatch_bbox")
    lines.extend(["", "## Diagnosis", ""])
    lines.append(f"- Mismatch bounding box: `{bbox or 'none'}`")
    reference_edges = report.get("reference_edge_peaks", {})
    candidate_edges = report.get("candidate_edge_peaks", {})
    lines.append(
        "- Strong reference edges: "
        + ", ".join(
            f"x={item['position']} ({item['score']:.2f})"
            for item in reference_edges.get("x", [])[:6]
        )
        + "; "
        + ", ".join(
            f"y={item['position']} ({item['score']:.2f})"
            for item in reference_edges.get("y", [])[:6]
        )
        if reference_edges.get("x") or reference_edges.get("y")
        else "- Strong reference edges: unavailable"
    )
    lines.append(
        "- Strong candidate edges: "
        + ", ".join(
            f"x={item['position']} ({item['score']:.2f})"
            for item in candidate_edges.get("x", [])[:6]
        )
        + "; "
        + ", ".join(
            f"y={item['position']} ({item['score']:.2f})"
            for item in candidate_edges.get("y", [])[:6]
        )
        if candidate_edges.get("x") or candidate_edges.get("y")
        else "- Strong candidate edges: unavailable"
    )
    lines.append(
        "- Top mismatch rows: "
        + ", ".join(
            f"{item['position']} ({item['fraction']:.3f})"
            for item in metrics.get("top_mismatch_rows", [])[:8]
        )
        if metrics.get("top_mismatch_rows")
        else "- Top mismatch rows: none"
    )
    lines.append(
        "- Top mismatch columns: "
        + ", ".join(
            f"{item['position']} ({item['fraction']:.3f})"
            for item in metrics.get("top_mismatch_columns", [])[:8]
        )
        if metrics.get("top_mismatch_columns")
        else "- Top mismatch columns: none"
    )
    hotspots = metrics.get("tile_hotspots", [])[:10]
    if hotspots:
        lines.append("- Hottest tiles:")
        for tile in hotspots:
            lines.append(
                "  - `{x},{y} {width}x{height}`: mean `{mean_error}`, mismatch `{mismatch_fraction}`".format(
                    **tile
                )
            )
    return "\n".join(lines) + "\n"


def write_comparison_reports(
    report: dict[str, Any], output_dir: Path
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "comparison.json"
    markdown_path = output_dir / "comparison.md"
    write_json(json_path, report)
    markdown_path.write_text(comparison_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}


def verification_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Pixel-perfect verification",
        "",
        f"- Status: **{result.get('status', 'unknown').upper()}**",
        f"- Viewport: `{result.get('viewport', 'unknown')}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in result.get("checks", []):
        lines.append(
            "| `{name}` | **{status}** | {detail} |".format(
                name=check.get("name"),
                status=check.get("status"),
                detail=str(check.get("detail", "")).replace("|", "\\|"),
            )
        )
    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result["warnings"])
    return "\n".join(lines) + "\n"
