"""Canonical layered UI IR and deterministic relationship analysis."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .extraction import ExtractionResult, PRIMITIVE_TYPES, SEMANTIC_ROLES


def _area(bounds: dict[str, int]) -> int:
    return bounds["width"] * bounds["height"]


def _right(bounds: dict[str, int]) -> int:
    return bounds["x"] + bounds["width"]


def _bottom(bounds: dict[str, int]) -> int:
    return bounds["y"] + bounds["height"]


def _contains(parent: dict[str, int], child: dict[str, int], *, strict: bool = True) -> bool:
    if strict and parent == child:
        return False
    return (
        parent["x"] <= child["x"]
        and parent["y"] <= child["y"]
        and _right(parent) >= _right(child)
        and _bottom(parent) >= _bottom(child)
    )


def _overlap_length(first_start: int, first_end: int, second_start: int, second_end: int) -> int:
    return max(0, min(first_end, second_end) - max(first_start, second_start))


def _horizontal_overlap(first: dict[str, int], second: dict[str, int]) -> float:
    overlap = _overlap_length(first["x"], _right(first), second["x"], _right(second))
    return overlap / max(1, min(first["width"], second["width"]))


def _vertical_overlap(first: dict[str, int], second: dict[str, int]) -> float:
    overlap = _overlap_length(first["y"], _bottom(first), second["y"], _bottom(second))
    return overlap / max(1, min(first["height"], second["height"]))


def _center(bounds: dict[str, int]) -> tuple[float, float]:
    return (bounds["x"] + bounds["width"] / 2, bounds["y"] + bounds["height"] / 2)


def _candidate_status(confidence: float) -> str:
    return "observed" if confidence >= 0.75 else "candidate"


def _copy_box(bounds: dict[str, int]) -> dict[str, int]:
    return {key: int(bounds[key]) for key in ("x", "y", "width", "height")}


def _add_inferred_containers(nodes: list[dict[str, Any]], width: int, height: int) -> None:
    existing = {
        tuple(node["absoluteBounds"].values())
        for node in nodes
        if node["primitiveType"] == "container"
    }
    additions = []
    for node in nodes:
        if node["primitiveType"] not in {"rectangle", "rounded_rectangle"}:
            continue
        bounds = node["absoluteBounds"]
        if _area(bounds) < width * height * 0.015 or tuple(bounds.values()) in existing:
            continue
        confidence = 0.48 if _area(bounds) < width * height * 0.15 else 0.62
        additions.append(
            {
                "primitiveType": "container",
                "status": _candidate_status(confidence),
                "absoluteBounds": _copy_box(bounds),
                "relativeBounds": None,
                "parentId": None,
                "children": [],
                "observed": {"style": node.get("observed", {}).get("style", {})},
                "detection": {
                    "method": "inference.rectangle-container",
                    "evidence": {"source_node_type": node["primitiveType"], "source_bounds": _copy_box(bounds)},
                },
                "confidence": {"overall": confidence},
                "inference": {},
                "_sort_key": (bounds["y"], bounds["x"], "container", -_area(bounds)),
            }
        )
    nodes.extend(additions)


def _assign_ids(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    type_order = {primitive: index for index, primitive in enumerate(PRIMITIVE_TYPES)}
    sorted_nodes = sorted(
        nodes,
        key=lambda node: (
            0 if node["primitiveType"] == "viewport" else 1,
            type_order.get(node["primitiveType"], len(type_order)),
            node["absoluteBounds"]["y"],
            node["absoluteBounds"]["x"],
            node["absoluteBounds"]["width"],
            node["absoluteBounds"]["height"],
            node.get("detection", {}).get("method", ""),
        ),
    )
    counters: defaultdict[str, int] = defaultdict(int)
    for node in sorted_nodes:
        primitive = node["primitiveType"]
        if primitive == "viewport":
            node["id"] = "viewport"
        else:
            counters[primitive] += 1
            node["id"] = f"{primitive}-{counters[primitive]:03d}"
        node.pop("_sort_key", None)
    return sorted_nodes


def _set_hierarchy(nodes: list[dict[str, Any]]) -> None:
    viewport = next(node for node in nodes if node["id"] == "viewport")
    parents = [
        node
        for node in nodes
        if node["primitiveType"]
        in {"viewport", "container", "rectangle", "rounded_rectangle", "image", "mask"}
    ]
    for node in nodes:
        node["parentId"] = None if node is viewport else "viewport"
        node["relativeBounds"] = None
        if node is viewport:
            continue
        candidates = [
            parent
            for parent in parents
            if parent is not node and _contains(parent["absoluteBounds"], node["absoluteBounds"])
        ]
        if candidates:
            candidates.sort(key=lambda parent: (_area(parent["absoluteBounds"]), parent["id"]))
            parent = candidates[0]
            node["parentId"] = parent["id"]
            node["relativeBounds"] = {
                "x": node["absoluteBounds"]["x"] - parent["absoluteBounds"]["x"],
                "y": node["absoluteBounds"]["y"] - parent["absoluteBounds"]["y"],
                "width": node["absoluteBounds"]["width"],
                "height": node["absoluteBounds"]["height"],
            }
    by_id = {node["id"]: node for node in nodes}
    for node in nodes:
        node["children"] = []
    for node in nodes:
        if node["parentId"] and node["parentId"] in by_id:
            by_id[node["parentId"]]["children"].append(node["id"])
    for node in nodes:
        node["children"].sort(
            key=lambda child_id: (
                by_id[child_id]["absoluteBounds"]["y"],
                by_id[child_id]["absoluteBounds"]["x"],
                child_id,
            )
            if child_id in by_id
            else (0, 0, child_id)
        )


def _relationship(
    relation_type: str,
    source: dict[str, Any],
    target: dict[str, Any],
    *,
    value: Any = None,
    confidence: float,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": relation_type,
        "source": source["id"],
        "target": target["id"],
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "evidence": evidence,
    }
    if value is not None:
        result["value"] = value
    return result


def _relationships(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Infer bounded, useful relationships from direct siblings.

    A screenshot can yield many overlapping contour candidates. Comparing every
    pair would produce a large and mostly redundant graph, so this analyzer
    links adjacent/grouped evidence and deliberately caps each relationship
    family per parent.
    """

    layout_types = {
        "container",
        "rectangle",
        "rounded_rectangle",
        "text",
        "image",
        "divider",
    }
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        if node["primitiveType"] in layout_types and node["primitiveType"] != "viewport":
            grouped[node["parentId"] or "viewport"].append(node)

    relationships: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    counts: defaultdict[tuple[str, str], int] = defaultdict(int)
    family_limit = 48

    def add(
        relation_type: str,
        source: dict[str, Any],
        target: dict[str, Any],
        *,
        value: Any = None,
        confidence: float,
        evidence: dict[str, Any],
    ) -> None:
        key = (relation_type, source["id"], target["id"])
        family = (evidence.get("parent", "viewport"), relation_type)
        if key in seen or counts[family] >= family_limit:
            return
        seen.add(key)
        counts[family] += 1
        relationships.append(
            _relationship(
                relation_type,
                source,
                target,
                value=value,
                confidence=confidence,
                evidence=evidence,
            )
        )

    by_id = {node["id"]: node for node in nodes}
    for parent in nodes:
        for child_id in parent.get("children", []):
            child = by_id.get(child_id)
            if child is not None:
                add(
                    "contains",
                    parent,
                    child,
                    confidence=1.0,
                    evidence={"parent": parent["id"], "source": "parentId/children"},
                )

    for parent_id, children in grouped.items():
        siblings = sorted(
            children,
            key=lambda node: (
                node["absoluteBounds"]["y"],
                node["absoluteBounds"]["x"],
                node["id"],
            ),
        )
        if len(siblings) > 96:
            text_nodes = [node for node in siblings if node["primitiveType"] == "text"]
            other_nodes = sorted(
                [node for node in siblings if node["primitiveType"] != "text"],
                key=lambda node: (
                    -_area(node["absoluteBounds"]),
                    node["absoluteBounds"]["y"],
                    node["absoluteBounds"]["x"],
                    node["id"],
                ),
            )
            siblings = sorted(
                text_nodes + other_nodes[: max(0, 96 - len(text_nodes))],
                key=lambda node: (
                    node["absoluteBounds"]["y"],
                    node["absoluteBounds"]["x"],
                    node["id"],
                ),
            )

        for index, source in enumerate(siblings):
            source_box = source["absoluteBounds"]
            for target in siblings[index + 1 : index + 17]:
                target_box = target["absoluteBounds"]
                evidence = {"parent": parent_id}
                if abs(source_box["x"] - target_box["x"]) <= 1:
                    add("align_left", source, target, confidence=0.98, evidence={**evidence, "coordinate_delta": abs(source_box["x"] - target_box["x"])})
                if abs(_right(source_box) - _right(target_box)) <= 1:
                    add("align_right", source, target, confidence=0.98, evidence={**evidence, "coordinate_delta": abs(_right(source_box) - _right(target_box))})
                if abs(source_box["width"] - target_box["width"]) <= 1:
                    add("equal_width", source, target, value=source_box["width"], confidence=0.98, evidence={**evidence, "width_delta": abs(source_box["width"] - target_box["width"])})
                if abs(source_box["height"] - target_box["height"]) <= 1:
                    add("equal_height", source, target, confidence=0.98, evidence={**evidence, "height_delta": abs(source_box["height"] - target_box["height"])})
                source_center = _center(source_box)
                target_center = _center(target_box)
                if abs(source_center[0] - target_center[0]) <= 1:
                    add("center_x", source, target, confidence=0.96, evidence={**evidence, "center_delta": round(abs(source_center[0] - target_center[0]), 4)})
                horizontal_overlap = _horizontal_overlap(source_box, target_box)
                if horizontal_overlap >= 0.5:
                    if target_box["y"] >= _bottom(source_box):
                        gap = target_box["y"] - _bottom(source_box)
                        if gap <= max(512, source_box["height"] * 8):
                            add("vertical_gap", source, target, value=gap, confidence=0.92, evidence={**evidence, "horizontal_overlap": round(horizontal_overlap, 4)})
                    elif source_box["y"] >= _bottom(target_box):
                        gap = source_box["y"] - _bottom(target_box)
                        if gap <= max(512, target_box["height"] * 8):
                            add("vertical_gap", target, source, value=gap, confidence=0.92, evidence={**evidence, "horizontal_overlap": round(horizontal_overlap, 4)})
                vertical_overlap = _vertical_overlap(source_box, target_box)
                if vertical_overlap >= 0.5:
                    if target_box["x"] >= _right(source_box):
                        add("horizontal_gap", source, target, value=target_box["x"] - _right(source_box), confidence=0.9, evidence={**evidence, "vertical_overlap": round(vertical_overlap, 4)})
                    elif source_box["x"] >= _right(target_box):
                        add("horizontal_gap", target, source, value=source_box["x"] - _right(target_box), confidence=0.9, evidence={**evidence, "vertical_overlap": round(vertical_overlap, 4)})
                if source["primitiveType"] == target["primitiveType"] and abs(source_box["width"] - target_box["width"]) <= 2 and abs(source_box["height"] - target_box["height"]) <= 2:
                    add("repeated_geometry", source, target, value={"width": source_box["width"], "height": source_box["height"]}, confidence=0.86, evidence={**evidence, "primitive_type": source["primitiveType"]})

    relationships.sort(key=lambda relation: (relation["type"], relation["source"], relation["target"], str(relation.get("value", ""))))
    for index, relation in enumerate(relationships, start=1):
        relation["id"] = f"relationship-{index:04d}"
    return relationships


def _text_descendants(node: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> list[str]:
    result = []
    for child_id in node.get("children", []):
        child = by_id[child_id]
        if child["primitiveType"] == "text":
            result.append(str(child.get("observed", {}).get("text", "")))
        result.extend(_text_descendants(child, by_id))
    return result


def _semantic_candidates(node: dict[str, Any], by_id: dict[str, dict[str, Any]], viewport: dict[str, int]) -> list[dict[str, Any]]:
    primitive = node["primitiveType"]
    bounds = node["absoluteBounds"]
    text = " ".join(_text_descendants(node, by_id)).lower()
    candidates: list[dict[str, Any]] = []

    def add(role: str, confidence: float, reason: str) -> None:
        candidates.append({"role": role, "confidence": round(confidence, 4), "reason": reason})

    if primitive == "text":
        add("text", 0.99, "primitive is text")
    elif primitive == "divider":
        add("divider", 0.98, "primitive is divider")
    elif primitive == "line":
        add("divider", 0.62, "line may function as a divider")
    elif primitive == "image":
        add("image", 0.9, "primitive is image region")
    elif primitive == "icon":
        add("icon", 0.86, "primitive is icon candidate")
    elif primitive in {"container", "rectangle", "rounded_rectangle"}:
        if any(word in text for word in ("email", "password", "username", "search", "name", "phone")):
            add("input", 0.73, "contained text resembles an input label or placeholder")
        if any(word in text for word in ("sign in", "sign up", "submit", "save", "continue", "next", "login", "send")):
            add("button", 0.76, "contained text resembles an action label")
        if _area(bounds) >= _area(viewport) * 0.08:
            add("card", 0.48, "bounded surface occupies a substantial region")
        add("container", 0.64 if primitive == "container" else 0.38, "surface primitive can own child content")
        if bounds["y"] <= viewport["height"] * 0.12 and bounds["width"] >= viewport["width"] * 0.5:
            add("navbar", 0.42, "wide region near the top edge")
        if bounds["x"] <= viewport["width"] * 0.12 and bounds["height"] >= viewport["height"] * 0.35:
            add("sidebar", 0.42, "tall region near the left edge")
    elif primitive == "mask":
        add("container", 0.2, "mask may constrain a containing surface")

    if len(node.get("children", [])) >= 3:
        children = [by_id[child_id] for child_id in node["children"]]
        types = {child["primitiveType"] for child in children}
        if len(types) == 1 or all(child["primitiveType"] in {"text", "icon", "image"} for child in children):
            add("list", 0.45, "repeated or homogeneous child structure")
    if not candidates:
        add("unknown", 0.0, "no semantic evidence")
    candidates.sort(key=lambda item: (-item["confidence"], item["role"]))
    return candidates


def build_ir(extraction: ExtractionResult) -> dict[str, Any]:
    """Build the canonical, JSON-serializable UI IR from an extraction result."""

    nodes = [dict(node) for node in extraction.nodes]
    width = int(extraction.source["width"])
    height = int(extraction.source["height"])
    _add_inferred_containers(nodes, width, height)
    nodes = _assign_ids(nodes)
    _set_hierarchy(nodes)
    by_id = {node["id"]: node for node in nodes}
    viewport = by_id["viewport"]["absoluteBounds"]
    semantic_summary = []
    for node in nodes:
        candidates = _semantic_candidates(node, by_id, viewport)
        node["inference"] = {
            "semantic": {
                "taxonomy": list(SEMANTIC_ROLES),
                "candidates": candidates,
            }
        }
        if candidates and candidates[0]["role"] != "unknown":
            semantic_summary.append({"node": node["id"], **candidates[0]})
    relationships = _relationships(nodes)
    primitive_counts: defaultdict[str, int] = defaultdict(int)
    for node in nodes:
        primitive_counts[node["primitiveType"]] += 1
    diagnostics = list(extraction.diagnostics)
    diagnostics.append(
        f"Built {len(nodes)} deterministic nodes and {len(relationships)} measurable/inferred relationships."
    )
    result = {
        "schema": "visual-ui-ir",
        "version": 1,
        "uncertainty_statuses": ["observed", "candidate", "unknown"],
        "source": extraction.source,
        "nodes": nodes,
        "scene_graph": {
            "root": "viewport",
            "children": by_id["viewport"]["children"],
        },
        "relationships": relationships,
        "inference": {
            "semantic_roles": semantic_summary,
            "implementation_hints": [],
            "note": "Inference is hypothesis, not replacement for observed raster facts.",
        },
        "capabilities": {
            **extraction.capabilities,
            "relationships": [
                "contains",
                "parent_child",
                "relative_bounds",
                "align_left",
                "align_right",
                "equal_width",
                "equal_height",
                "center_x",
                "vertical_gap",
                "horizontal_gap",
                "repeated_geometry",
            ],
            "semantic_inference": True,
        },
        "diagnostics": diagnostics,
        "primitive_counts": dict(sorted(primitive_counts.items())),
    }
    validate_ir(result)
    return result


def validate_ir(ir: dict[str, Any]) -> None:
    """Validate the stable invariants exposed to downstream agents."""

    if ir.get("schema") != "visual-ui-ir" or ir.get("version") != 1:
        raise ValueError("UI IR must declare schema=visual-ui-ir and version=1")
    source = ir.get("source")
    if not isinstance(source, dict) or int(source.get("width", 0)) <= 0 or int(source.get("height", 0)) <= 0:
        raise ValueError("UI IR source must declare positive width and height")
    nodes = ir.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("UI IR must contain at least the viewport node")
    if any(not isinstance(node, dict) or not node.get("id") for node in nodes):
        raise ValueError("Every UI IR node must have an ID")
    ids = [node["id"] for node in nodes]
    if len(ids) != len(set(ids)):
        raise ValueError("UI IR node IDs must be unique")
    by_id = {node["id"]: node for node in nodes}
    if "viewport" not in by_id:
        raise ValueError("UI IR must contain a viewport node")
    allowed_statuses = {"observed", "candidate", "unknown"}
    for node in nodes:
        if not isinstance(node, dict) or node.get("status") not in allowed_statuses:
            raise ValueError("Every UI IR node must have an allowed uncertainty status")
        bounds = node.get("absoluteBounds")
        if not isinstance(bounds, dict) or any(int(bounds.get(key, 0)) <= 0 for key in ("width", "height")):
            raise ValueError("Every UI IR node must have positive absolute bounds")
        if int(bounds.get("x", -1)) < 0 or int(bounds.get("y", -1)) < 0:
            raise ValueError("UI IR node bounds must use non-negative coordinates")
        if int(bounds["x"]) + int(bounds["width"]) > int(source["width"]) or int(bounds["y"]) + int(bounds["height"]) > int(source["height"]):
            raise ValueError(f"UI IR node {node.get('id')} lies outside the source viewport")
        parent = node.get("parentId")
        if parent is not None and parent not in by_id:
            raise ValueError(f"UI IR node {node.get('id')} refers to missing parent {parent}")
        children = node.get("children", [])
        if not isinstance(children, list) or any(child not in by_id for child in children):
            raise ValueError(f"UI IR node {node.get('id')} refers to missing child")
    if ir.get("scene_graph", {}).get("root") != "viewport":
        raise ValueError("UI IR scene graph root must be viewport")
