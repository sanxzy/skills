"""Deterministic agent-facing projections of the canonical UI IR."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageDraw


def _box_text(bounds: dict[str, int]) -> str:
    return "x={x} y={y} w={width} h={height}".format(**bounds)


def _node_label(node: dict[str, Any]) -> str:
    primitive = node["primitiveType"]
    observed = node.get("observed", {})
    text = observed.get("text")
    suffix = f' text="{str(text).replace(chr(34), chr(39))}"' if text else ""
    return f'{node["id"]} [{primitive}] {_box_text(node["absoluteBounds"])}{suffix}'


def _compact_style(style: dict[str, Any]) -> str:
    values = []
    for key in ("background", "foreground"):
        value = style.get(key)
        if isinstance(value, dict) and value.get("color"):
            values.append(f"{key[:3]}={value['color']}")
    return " ".join(values)


def _tree_lines(
    node_id: str,
    by_id: dict[str, dict[str, Any]],
    visible: set[str],
    depth: int = 0,
) -> list[str]:
    node = by_id[node_id]
    lines = [f'{"  " * depth}- {_node_label(node)}'] if node_id in visible else []
    if node_id in visible:
        style = _compact_style(node.get("observed", {}).get("style", {}))
        if style:
            lines.append(f'{"  " * (depth + 1)}colors={style}')
    for child_id in node.get("children", []):
        if child_id in by_id:
            lines.extend(_tree_lines(child_id, by_id, visible, depth + (1 if node_id in visible else 0)))
    return lines


def layout_text(ir: dict[str, Any]) -> str:
    source = ir["source"]
    lines = [
        "# Visual UI layout",
        "",
        f"Schema: {ir['schema']} v{ir['version']}",
        f"Viewport: {source['width']}x{source['height']}",
        "",
        "## Observed scene",
        "",
    ]
    by_id = {node["id"]: node for node in ir["nodes"]}
    observed_nodes = [node for node in ir["nodes"] if node["status"] == "observed" or node["id"] == "viewport"]
    if len(observed_nodes) > 240:
        keep = {node["id"] for node in observed_nodes if node["primitiveType"] in {"viewport", "text", "container", "rectangle", "rounded_rectangle", "divider"}}
        extras = sorted(
            [node for node in observed_nodes if node["id"] not in keep],
            key=lambda node: (-node["absoluteBounds"]["width"] * node["absoluteBounds"]["height"], node["id"]),
        )
        keep.update(node["id"] for node in extras[: max(0, 240 - len(keep))])
        lines.append(f"- Showing {len(keep)} high-value observed nodes; {len(observed_nodes) - len(keep)} minor nodes remain in design.struct.json.")
    else:
        keep = {node["id"] for node in observed_nodes}
    lines.extend(_tree_lines(ir["scene_graph"]["root"], by_id, keep))

    candidates = [node for node in ir["nodes"] if node["status"] == "candidate"]
    if candidates:
        lines.extend(["", f"Candidate evidence: {len(candidates)} nodes (full details in design.struct.json)."])
        for node in sorted(candidates, key=lambda item: (-item["confidence"]["overall"], item["id"]))[:64]:
            lines.append(f"- {node['id']} [{node['primitiveType']}] {_box_text(node['absoluteBounds'])} confidence={node['confidence']['overall']:.4f}")
        if len(candidates) > 64:
            lines.append(f"- ... {len(candidates) - 64} additional candidate nodes omitted from this compact projection.")

    lines.extend(["", "## Relationships", ""])
    relationships = ir.get("relationships", [])
    if relationships:
        lines.append(f"Total relationships: {len(relationships)}; showing at most 200 highest-confidence deterministic entries.")
        selected = sorted(relationships, key=lambda relation: (-relation["confidence"], relation["type"], relation["source"], relation["target"]))[:200]
        for relation in selected:
            value = f" value={relation['value']}" if "value" in relation else ""
            lines.append(f"- {relation['source']} -> {relation['target']} {relation['type']}{value} confidence={relation['confidence']:.4f}")
        if len(relationships) > len(selected):
            lines.append(f"- ... {len(relationships) - len(selected)} additional relationships omitted from this compact projection.")
    else:
        lines.append("No relationships were measured or inferred.")

    lines.extend(["", "## Inference", ""])
    semantic = ir.get("inference", {}).get("semantic_roles", [])
    if semantic:
        lines.append(f"Total semantic candidates: {len(semantic)}; showing at most 200.")
        for item in semantic[:200]:
            lines.append(f"- {item['node']}: semantic_role={item['role']} confidence={item['confidence']:.4f} reason={item['reason']}")
        if len(semantic) > 200:
            lines.append(f"- ... {len(semantic) - 200} additional semantic candidates omitted from this compact projection.")
    else:
        lines.append("No semantic role candidates were produced.")
    lines.append("- Implementation hints: none; framework-specific code generation is deferred.")
    lines.extend(["", "## Capabilities", ""])
    capabilities = ir.get("capabilities", {})
    lines.append(f"- OCR: {capabilities.get('ocr', {})}")
    lines.append(f"- Geometry: {capabilities.get('geometry', {})}")
    lines.append(f"- Primitive counts: {ir.get('primitive_counts', {})}")
    lines.extend(["", "## Diagnostics", ""])
    lines.extend(f"- {item}" for item in ir.get("diagnostics", []))
    return "\n".join(lines) + "\n"


def _ascii_char(node: dict[str, Any]) -> str:
    return {
        "viewport": " ",
        "container": "#",
        "rectangle": "+",
        "rounded_rectangle": "O",
        "line": "-",
        "divider": "=",
        "text": "T",
        "image": "I",
        "icon": "*",
        "circle": "C",
        "ellipse": "E",
        "shadow": "s",
        "gradient": "g",
        "mask": "m",
    }.get(node["primitiveType"], "?")


def ascii_projection(ir: dict[str, Any], *, max_width: int = 80, max_height: int = 44) -> str:
    source = ir["source"]
    width = int(source["width"])
    height = int(source["height"])
    scale = max(width / max(4, max_width - 2), height / max(4, max_height - 2), 1.0)
    columns = max(4, min(max_width, int(round(width / scale)) + 2))
    rows = max(4, min(max_height, int(round(height / scale)) + 2))
    grid = [[" " for _ in range(columns)] for _ in range(rows)]

    def point(x: int, y: int) -> tuple[int, int]:
        return (
            max(0, min(columns - 1, int(round(x / scale)) + 1)),
            max(0, min(rows - 1, int(round(y / scale)) + 1)),
        )

    def draw_node(node: dict[str, Any]) -> None:
        if node["primitiveType"] == "viewport":
            return
        box = node["absoluteBounds"]
        left, top = point(box["x"], box["y"])
        right, bottom = point(box["x"] + box["width"] - 1, box["y"] + box["height"] - 1)
        char = _ascii_char(node)
        for x in range(left, right + 1):
            if 0 <= x < columns:
                if 0 <= top < rows:
                    grid[top][x] = char
                if 0 <= bottom < rows:
                    grid[bottom][x] = char
        for y in range(top, bottom + 1):
            if 0 <= y < rows:
                if 0 <= left < columns:
                    grid[y][left] = char
                if 0 <= right < columns:
                    grid[y][right] = char
        text = str(node.get("observed", {}).get("text", ""))
        if text and right - left >= 6 and 0 <= top < rows:
            label = text[: max(1, right - left - 1)]
            for index, letter in enumerate(label, start=left + 1):
                if index < right and 0 <= index < columns:
                    grid[top][index] = letter

    # Draw larger surfaces first so text, icons, and smaller shapes remain legible.
    nodes = sorted(
        ir["nodes"],
        key=lambda node: (
            -node["absoluteBounds"]["width"] * node["absoluteBounds"]["height"],
            node["primitiveType"],
            node["id"],
        ),
    )
    for node in nodes:
        draw_node(node)
    border = "+" + "-" * max(0, columns - 2) + "+"
    body = ["|" + "".join(row[1:-1])[: max(0, columns - 2)].ljust(max(0, columns - 2)) + "|" for row in grid]
    return "\n".join([border, *body, border]) + "\n"


def debug_overlay(image: Image.Image, ir: dict[str, Any]) -> Image.Image:
    overlay = image.convert("RGB").copy()
    draw = ImageDraw.Draw(overlay)
    colors = {
        "viewport": (0, 180, 255),
        "container": (255, 128, 0),
        "rectangle": (255, 80, 80),
        "rounded_rectangle": (255, 0, 180),
        "text": (0, 180, 0),
        "line": (150, 0, 220),
        "divider": (80, 0, 180),
        "image": (0, 150, 180),
        "icon": (180, 120, 0),
    }
    for node in ir["nodes"]:
        box = node["absoluteBounds"]
        xy = (box["x"], box["y"], box["x"] + box["width"] - 1, box["y"] + box["height"] - 1)
        draw.rectangle(xy, outline=colors.get(node["primitiveType"], (128, 128, 128)), width=1)
    return overlay
