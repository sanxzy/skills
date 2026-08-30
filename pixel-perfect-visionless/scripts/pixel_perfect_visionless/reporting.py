"""Persistent Markdown projections for visionless agents."""

from __future__ import annotations

from typing import Any


def _box(bounds: dict[str, int]) -> str:
    return "x={x} y={y} w={width} h={height}".format(**bounds)


def inspection_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Pixel-perfect visionless inspection",
        "",
        f"- Image: `{report.get('path')}`",
        f"- Viewport: `{report.get('viewport')}`",
        f"- Format/mode: `{report.get('format')}` / `{report.get('mode')}`",
        f"- SHA-256: `{report.get('sha256')}`",
        "",
        "## Dominant colors",
        "",
        "| Color | Fraction | Pixels |",
        "| --- | ---: | ---: |",
    ]
    for color in report.get("dominant_colors", []):
        lines.append(f"| `{color['color']}` | `{color['fraction']}` | `{color['pixels']}` |")
    lines.extend(["", "## Edge evidence", "", f"- Vertical peaks: `{report.get('edge_peaks', {}).get('x', [])}`", f"- Horizontal peaks: `{report.get('edge_peaks', {}).get('y', [])}`"])
    if report.get("samples"):
        lines.extend(["", "## Pixel probes", "", "| x | y | RGB | Hex |", "| ---: | ---: | --- | --- |"])
        for sample in report["samples"]:
            lines.append(f"| {sample['x']} | {sample['y']} | `{sample['rgb']}` | `{sample['hex']}` |")
    return "\n".join(lines) + "\n"


def compile_markdown(ir: dict[str, Any], artifacts: dict[str, str] | None = None) -> str:
    lines = [
        "# Pixel-perfect visionless compile",
        "",
        f"- Schema: `{ir['schema']} v{ir['version']}`",
        f"- Source: `{ir['source']['path']}`",
        f"- Viewport: `{ir['source']['viewport']}`",
        f"- Nodes: `{len(ir.get('nodes', []))}`",
        f"- Relationships: `{len(ir.get('relationships', []))}`",
        "",
        "## Layer contract",
        "",
        "- Observed raster facts are authoritative.",
        "- Relationships and semantic roles are inference and carry confidence.",
        "- Unknown or candidate detections are preserved rather than discarded.",
    ]
    if artifacts:
        lines.extend(["", "## Persistent artifacts", ""])
        lines.extend(f"- `{name}`: `{path}`" for name, path in sorted(artifacts.items()))
    lines.extend(["", "## Diagnostics", ""])
    lines.extend(f"- {item}" for item in ir.get("diagnostics", []))
    return "\n".join(lines) + "\n"


def structured_diff_markdown(diff: dict[str, Any]) -> str:
    lines = [
        "# Structured visual diff",
        "",
        f"- Overall similarity: **{diff.get('overall_similarity', 0):.4f}**",
        "",
        "## Category status",
        "",
        "| Category | Status | Score/reason |",
        "| --- | --- | --- |",
    ]
    for name, category in sorted(diff.get("categories", {}).items()):
        value = f"{category['score']:.4f}" if "score" in category else category.get("reason", "")
        lines.append(f"| `{name}` | **{category.get('status', 'unknown')}** | `{value}` |")
    structured = diff.get("structured", {})
    lines.extend(["", "## Node deltas", ""])
    matches = structured.get("matches", [])
    if matches:
        lines.extend(["| Reference | Candidate | Confidence | Delta |", "| --- | --- | ---: | --- |"])
        for match in matches:
            lines.append(
                f"| `{match['reference_id']}` | `{match['candidate_id']}` | "
                f"`{match['confidence']:.4f}` | `{match['delta']}` |"
            )
    else:
        lines.append("No nodes were matched.")
    for key in ("unmatched_reference", "unmatched_candidate"):
        lines.extend(["", f"### {key.replace('_', ' ').title()}", ""])
        values = structured.get(key, [])
        if values:
            lines.extend(f"- `{item['id']}` `{item['primitiveType']}` {_box(item['absoluteBounds'])}" for item in values)
        else:
            lines.append("None.")
    lines.extend(["", "## Diagnostics", ""])
    lines.extend(f"- {item}" for item in diff.get("diagnostics", []))
    return "\n".join(lines) + "\n"


def comparison_markdown(pixel: dict[str, Any], structured: dict[str, Any]) -> str:
    metrics = pixel.get("metrics", {})
    lines = [
        "# Pixel-perfect visionless comparison",
        "",
        f"- Reference: `{pixel.get('reference')}`",
        f"- Candidate: `{pixel.get('candidate')}`",
        f"- Viewport: `{pixel.get('viewport')}`",
        f"- Pixel mean absolute error: `{metrics.get('mean_abs_error')}`",
        f"- Pixel exact fraction: `{metrics.get('exact_fraction')}`",
        f"- Structured similarity: `{structured.get('overall_similarity')}`",
        "",
        "## Pixel evidence",
        "",
        f"- Mismatch bounding box: `{metrics.get('mismatch_bbox') or 'none'}`",
        f"- Mismatch pixels: `{metrics.get('mismatch_pixels')}`",
        f"- Hottest tiles: `{metrics.get('tile_hotspots', [])[:10]}`",
        "",
        "## Structured diff",
        "",
        f"- Matched nodes: `{len(structured.get('structured', {}).get('matches', []))}`",
        f"- Unmatched reference nodes: `{len(structured.get('structured', {}).get('unmatched_reference', []))}`",
        f"- Unmatched candidate nodes: `{len(structured.get('structured', {}).get('unmatched_candidate', []))}`",
    ]
    return "\n".join(lines) + "\n"


def verification_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Pixel-perfect visionless verification",
        "",
        f"- Status: **{str(result.get('status', 'unknown')).upper()}**",
        f"- Viewport: `{result.get('viewport', 'unknown')}`",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in result.get("checks", []):
        lines.append(f"| `{check.get('name')}` | **{check.get('status')}** | {str(check.get('detail', '')).replace('|', '\\|')} |")
    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in result["warnings"])
    return "\n".join(lines) + "\n"
