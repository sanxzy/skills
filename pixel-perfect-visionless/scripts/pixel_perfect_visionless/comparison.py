"""Pixel and element-level comparison for two extracted screenshots."""

from __future__ import annotations

import math
import re
from typing import Any


_TEXT_SPACE = re.compile(r"\s+")


def _normalize_text(value: Any) -> str:
    return _TEXT_SPACE.sub(" ", str(value or "")).strip().lower()


def _area(bounds: dict[str, int]) -> int:
    return bounds["width"] * bounds["height"]


def _iou(first: dict[str, int], second: dict[str, int]) -> float:
    left = max(first["x"], second["x"])
    top = max(first["y"], second["y"])
    right = min(first["x"] + first["width"], second["x"] + second["width"])
    bottom = min(first["y"] + first["height"], second["y"] + second["height"])
    if right <= left or bottom <= top:
        return 0.0
    intersection = (right - left) * (bottom - top)
    union = _area(first) + _area(second) - intersection
    return intersection / union if union else 0.0


def _center_distance(first: dict[str, int], second: dict[str, int], viewport: dict[str, int]) -> float:
    first_center = (first["x"] + first["width"] / 2, first["y"] + first["height"] / 2)
    second_center = (second["x"] + second["width"] / 2, second["y"] + second["height"] / 2)
    distance = math.hypot(first_center[0] - second_center[0], first_center[1] - second_center[1])
    diagonal = max(1.0, math.hypot(viewport["width"], viewport["height"]))
    return min(1.0, distance / diagonal)


def _semantic_top(node: dict[str, Any]) -> str | None:
    candidates = node.get("inference", {}).get("semantic", {}).get("candidates", [])
    if not candidates:
        return None
    role = candidates[0].get("role")
    return role if role and role != "unknown" else None


def _match_score(reference: dict[str, Any], candidate: dict[str, Any], viewport: dict[str, int]) -> float:
    score = 0.0
    ref_text = _normalize_text(reference.get("observed", {}).get("text"))
    candidate_text = _normalize_text(candidate.get("observed", {}).get("text"))
    if ref_text and candidate_text:
        if ref_text == candidate_text:
            score += 0.58
        elif ref_text in candidate_text or candidate_text in ref_text:
            score += 0.28
    if reference["primitiveType"] == candidate["primitiveType"]:
        score += 0.18
    ref_role = _semantic_top(reference)
    candidate_role = _semantic_top(candidate)
    if ref_role and ref_role == candidate_role:
        score += 0.1
    score += 0.14 * _iou(reference["absoluteBounds"], candidate["absoluteBounds"])
    score += 0.08 * (1.0 - _center_distance(reference["absoluteBounds"], candidate["absoluteBounds"], viewport))
    ref_box = reference["absoluteBounds"]
    candidate_box = candidate["absoluteBounds"]
    size_similarity = 1.0 - min(
        1.0,
        (
            abs(ref_box["width"] - candidate_box["width"]) / max(1, ref_box["width"])
            + abs(ref_box["height"] - candidate_box["height"]) / max(1, ref_box["height"])
        )
        / 2,
    )
    score += 0.1 * size_similarity
    return min(1.0, score)


def _snapshot(node: dict[str, Any]) -> dict[str, Any]:
    semantic = node.get("inference", {}).get("semantic", {}).get("candidates", [])
    observed = node.get("observed", {})
    return {
        "id": node["id"],
        "primitiveType": node["primitiveType"],
        "status": node.get("status"),
        "absoluteBounds": node["absoluteBounds"],
        "relativeBounds": node.get("relativeBounds"),
        "parentId": node.get("parentId"),
        "text": observed.get("text"),
        "style": observed.get("style", {}),
        "semantic": semantic[:3],
    }


def _box_delta(expected: dict[str, int], actual: dict[str, int]) -> dict[str, int]:
    return {key: int(actual[key] - expected[key]) for key in ("x", "y", "width", "height")}


def _color_delta(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("background", "foreground"):
        expected_value = expected.get(key, {}).get("color") if isinstance(expected.get(key), dict) else None
        actual_value = actual.get(key, {}).get("color") if isinstance(actual.get(key), dict) else None
        if expected_value is not None or actual_value is not None:
            result[key] = {"expected": expected_value, "actual": actual_value, "changed": expected_value != actual_value}
    return result


def _delta(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    expected_observed = reference.get("observed", {})
    actual_observed = candidate.get("observed", {})
    result: dict[str, Any] = {
        "bounds": _box_delta(reference["absoluteBounds"], candidate["absoluteBounds"]),
        "primitive_changed": reference["primitiveType"] != candidate["primitiveType"],
    }
    expected_text = expected_observed.get("text")
    actual_text = actual_observed.get("text")
    if expected_text is not None or actual_text is not None:
        result["text"] = {"expected": expected_text, "actual": actual_text, "changed": expected_text != actual_text}
    colors = _color_delta(expected_observed.get("style", {}), actual_observed.get("style", {}))
    if colors:
        result["colors"] = colors
    return result


def _match_nodes(reference_ir: dict[str, Any], candidate_ir: dict[str, Any]) -> dict[str, Any]:
    viewport = reference_ir["source"]
    reference_nodes = [node for node in reference_ir["nodes"] if node["id"] != "viewport"]
    candidate_nodes = [node for node in candidate_ir["nodes"] if node["id"] != "viewport"]
    by_reference = {node["id"]: node for node in reference_nodes}
    by_candidate = {node["id"]: node for node in candidate_nodes}
    available = set(by_candidate)
    matches = []
    unmatched_reference = []
    for reference in sorted(reference_nodes, key=lambda node: (node["absoluteBounds"]["y"], node["absoluteBounds"]["x"], node["id"])):
        scored = sorted(
            (
                (_match_score(reference, candidate, viewport), candidate)
                for candidate_id, candidate in by_candidate.items()
                if candidate_id in available
            ),
            key=lambda item: (-item[0], item[1]["id"]),
        )
        if not scored or scored[0][0] < 0.32:
            unmatched_reference.append(_snapshot(reference))
            continue
        score, candidate = scored[0]
        available.remove(candidate["id"])
        matches.append(
            {
                "reference_id": reference["id"],
                "candidate_id": candidate["id"],
                "confidence": round(score, 4),
                "expected": _snapshot(reference),
                "actual": _snapshot(candidate),
                "delta": _delta(reference, candidate),
            }
        )
    return {
        "matches": matches,
        "unmatched_reference": unmatched_reference,
        "unmatched_candidate": [_snapshot(by_candidate[node_id]) for node_id in sorted(available)],
    }


def _score_from_error(error: float) -> float:
    return round(max(0.0, min(1.0, 1.0 - error)), 6)


def _category_reports(
    reference_ir: dict[str, Any], candidate_ir: dict[str, Any], structured: dict[str, Any], pixel_report: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    matches = structured["matches"]
    if not matches:
        geometry = {"status": "measured", "score": 0.0, "matched_nodes": 0}
        position = {"status": "measured", "score": 0.0, "matched_nodes": 0}
        dimensions = {"status": "measured", "score": 0.0, "matched_nodes": 0}
    else:
        position_errors = []
        dimension_errors = []
        geometry_errors = []
        for match in matches:
            expected = match["expected"]["absoluteBounds"]
            actual = match["actual"]["absoluteBounds"]
            position_errors.append(
                min(1.0, (abs(actual["x"] - expected["x"]) + abs(actual["y"] - expected["y"])) / max(1, reference_ir["source"]["width"] + reference_ir["source"]["height"]))
            )
            dimension_errors.append(
                min(1.0, (abs(actual["width"] - expected["width"]) + abs(actual["height"] - expected["height"])) / max(1, expected["width"] + expected["height"]))
            )
            geometry_errors.append((position_errors[-1] + dimension_errors[-1]) / 2)
        position = {"status": "measured", "score": _score_from_error(sum(position_errors) / len(position_errors)), "matched_nodes": len(matches)}
        dimensions = {"status": "measured", "score": _score_from_error(sum(dimension_errors) / len(dimension_errors)), "matched_nodes": len(matches)}
        geometry = {"status": "measured", "score": _score_from_error(sum(geometry_errors) / len(geometry_errors)), "matched_nodes": len(matches)}

    color_deltas = []
    text_matches = 0
    for match in matches:
        expected_style = match["expected"].get("style", {})
        actual_style = match["actual"].get("style", {})
        for key in ("background", "foreground"):
            expected = expected_style.get(key, {}).get("color") if isinstance(expected_style.get(key), dict) else None
            actual = actual_style.get(key, {}).get("color") if isinstance(actual_style.get(key), dict) else None
            if expected is not None and actual is not None:
                color_deltas.append(0.0 if expected == actual else 1.0)
        if match["expected"].get("primitiveType") == "text":
            text_matches += 1
    color = (
        {"status": "measured", "score": _score_from_error(sum(color_deltas) / len(color_deltas)), "samples": len(color_deltas)}
        if color_deltas
        else {"status": "unavailable", "reason": "No comparable per-node solid colors were extracted."}
    )
    relationship_types = {relation["type"] for relation in reference_ir.get("relationships", [])} & {relation["type"] for relation in candidate_ir.get("relationships", [])}
    alignment = {"status": "measured", "score": 1.0 if "align_left" in relationship_types or "equal_width" in relationship_types else 0.0, "relationship_types": sorted(relationship_types)}
    spacing = {"status": "measured", "score": 1.0 if "vertical_gap" in relationship_types or "horizontal_gap" in relationship_types else 0.0, "relationship_types": sorted(relationship_types)}
    has_effect_candidates = any(
        node["primitiveType"] in {"shadow", "gradient", "mask"}
        for node in reference_ir["nodes"] + candidate_ir["nodes"]
    )
    effect_status = {"status": "candidate", "reason": "Effect primitive candidates require focused verification."} if has_effect_candidates else {"status": "unavailable", "reason": "No reliable effect measurements were extracted."}
    assets = {"status": "candidate", "reason": "Image/icon regions are compared as raster candidates; source asset matching is deferred."}
    typography = {"status": "candidate", "text_nodes": text_matches, "reason": "OCR text geometry is available; font metrics are not inferred in MVP."}
    return {
        "geometry": geometry,
        "position": position,
        "dimensions": dimensions,
        "color": color,
        "typography": typography,
        "borders": effect_status,
        "radius": effect_status,
        "shadows": effect_status,
        "alignment": alignment,
        "spacing": spacing,
        "assets": assets,
        "pixel": {
            "status": "measured",
            "score": round(max(0.0, 1.0 - pixel_report["metrics"]["mean_abs_error"] / 255.0), 6),
            "mean_abs_error": pixel_report["metrics"]["mean_abs_error"],
        },
    }


def compare_irs(reference_ir: dict[str, Any], candidate_ir: dict[str, Any], pixel_report: dict[str, Any]) -> dict[str, Any]:
    structured = _match_nodes(reference_ir, candidate_ir)
    categories = _category_reports(reference_ir, candidate_ir, structured, pixel_report)
    weighted = {
        "geometry": 0.25,
        "position": 0.15,
        "dimensions": 0.15,
        "color": 0.2,
        "alignment": 0.1,
        "spacing": 0.05,
        "pixel": 0.1,
    }
    weighted_scores = [
        weight * float(categories[name]["score"])
        for name, weight in weighted.items()
        if categories[name].get("status") == "measured" and "score" in categories[name]
    ]
    weight_total = sum(
        weight for name, weight in weighted.items() if categories[name].get("status") == "measured" and "score" in categories[name]
    )
    return {
        "schema": "visual-ui-diff",
        "version": 1,
        "reference_source": reference_ir["source"],
        "candidate_source": candidate_ir["source"],
        "overall_similarity": round(sum(weighted_scores) / weight_total if weight_total else 0.0, 6),
        "categories": categories,
        "structured": structured,
        "excluded_categories": [name for name, value in categories.items() if value.get("status") == "unavailable"],
        "diagnostics": [
            "Node matching is heuristic and confidence-scored.",
            "Unmatched nodes are preserved rather than forced into pairs.",
        ],
    }
