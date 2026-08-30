"""Classical, deterministic extraction from a raster screenshot."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np

from .images import ImageAnalysisError, load_image, inspect_image, source_sha256

PRIMITIVE_TYPES = (
    "viewport",
    "rectangle",
    "rounded_rectangle",
    "line",
    "circle",
    "ellipse",
    "text",
    "image",
    "icon",
    "divider",
    "shadow",
    "gradient",
    "mask",
    "container",
)
MAX_NODES_PER_PRIMITIVE = {
    "rectangle": 160,
    "rounded_rectangle": 160,
    "line": 160,
    "circle": 96,
    "ellipse": 96,
    "image": 64,
    "icon": 128,
    "divider": 96,
    "shadow": 64,
    "gradient": 32,
    "mask": 32,
    "container": 64,
}

SEMANTIC_ROLES = (
    "container",
    "button",
    "input",
    "card",
    "navbar",
    "sidebar",
    "modal",
    "dropdown",
    "list",
    "image",
    "icon",
    "divider",
    "text",
)


@dataclass
class ExtractionResult:
    path: Path
    source: dict[str, Any]
    nodes: list[dict[str, Any]]
    diagnostics: list[str]
    capabilities: dict[str, Any]
    debug: dict[str, Any]


def _box(x: int, y: int, width: int, height: int) -> dict[str, int]:
    return {"x": int(x), "y": int(y), "width": int(width), "height": int(height)}


def _box_area(box: dict[str, int]) -> int:
    return box["width"] * box["height"]


def _box_iou(first: dict[str, int], second: dict[str, int]) -> float:
    left = max(first["x"], second["x"])
    top = max(first["y"], second["y"])
    right = min(first["x"] + first["width"], second["x"] + second["width"])
    bottom = min(first["y"] + first["height"], second["y"] + second["height"])
    if right <= left or bottom <= top:
        return 0.0
    intersection = (right - left) * (bottom - top)
    union = _box_area(first) + _box_area(second) - intersection
    return intersection / union if union else 0.0


def _status(confidence: float) -> str:
    return "observed" if confidence >= 0.75 else "candidate"


def _node(
    primitive_type: str,
    bounds: dict[str, int],
    *,
    method: str,
    evidence: dict[str, Any],
    confidence: float,
    observed: dict[str, Any] | None = None,
    sort_key: tuple[Any, ...] = (),
) -> dict[str, Any]:
    return {
        "primitiveType": primitive_type,
        "status": _status(confidence),
        "absoluteBounds": bounds,
        "relativeBounds": None,
        "parentId": None,
        "children": [],
        "observed": observed or {},
        "detection": {"method": method, "evidence": evidence},
        "confidence": {"overall": round(float(max(0.0, min(1.0, confidence))), 4)},
        "inference": {},
        "_sort_key": sort_key or (bounds["y"], bounds["x"], primitive_type),
    }


def _quantized_colors(array: np.ndarray, limit: int = 8) -> list[tuple[tuple[int, int, int], int]]:
    if array.size == 0:
        return []
    quantized = (array.astype(np.uint16) // 8 * 8).astype(np.uint8)
    counts = Counter(map(tuple, quantized.reshape(-1, 3)))
    return counts.most_common(limit)


def _color_value(color: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % tuple(int(channel) for channel in color)


def _region_fingerprint(rgb: np.ndarray, bounds: dict[str, int]) -> str:
    height, width = rgb.shape[:2]
    x = max(0, min(width, bounds["x"]))
    y = max(0, min(height, bounds["y"]))
    right = max(x, min(width, bounds["x"] + bounds["width"]))
    bottom = max(y, min(height, bounds["y"] + bounds["height"]))
    return sha256(rgb[y:bottom, x:right].tobytes()).hexdigest()


def _style_for_box(rgb: np.ndarray, bounds: dict[str, int], *, text: bool = False) -> dict[str, Any]:
    height, width = rgb.shape[:2]
    x = max(0, min(width - 1, bounds["x"]))
    y = max(0, min(height - 1, bounds["y"]))
    right = max(x + 1, min(width, bounds["x"] + bounds["width"]))
    bottom = max(y + 1, min(height, bounds["y"] + bounds["height"]))
    crop = rgb[y:bottom, x:right]
    colors = _quantized_colors(crop)
    if not colors:
        return {}
    background_color, background_count = colors[0]
    result: dict[str, Any] = {
        "background": {
            "type": "solid",
            "color": _color_value(background_color),
            "confidence": round(min(1.0, background_count / max(1, crop.shape[0] * crop.shape[1]) * 2), 4),
        }
    }
    if text:
        foreground = next((item for item in colors[1:] if item[0] != background_color), None)
        if foreground:
            color, count = foreground
            result["foreground"] = {
                "type": "solid",
                "color": _color_value(color),
                "confidence": round(min(1.0, count / max(1, crop.shape[0] * crop.shape[1]) * 4), 4),
            }
    return result


def _ocr_nodes(rgb_image: Any, tesseract: Path) -> tuple[list[dict[str, Any]], list[str]]:
    import pytesseract
    from pytesseract import Output

    pytesseract.pytesseract.tesseract_cmd = str(tesseract)
    try:
        data = pytesseract.image_to_data(
            rgb_image,
            lang="eng",
            config="--psm 6",
            output_type=Output.DICT,
        )
    except Exception as exc:
        raise ImageAnalysisError(f"Tesseract OCR failed: {exc}") from exc

    groups: dict[tuple[int, int, int], list[dict[str, Any]]] = {}
    total_tokens = 0
    for index, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text).strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][index])
        except (KeyError, TypeError, ValueError):
            confidence = -1.0
        if confidence < 0:
            continue
        token = {
            "text": text,
            "bounds": _box(
                int(data["left"][index]),
                int(data["top"][index]),
                int(data["width"][index]),
                int(data["height"][index]),
            ),
            "confidence": round(max(0.0, min(1.0, confidence / 100.0)), 4),
        }
        key = (
            int(data.get("block_num", [0])[index]),
            int(data.get("par_num", [0])[index]),
            int(data.get("line_num", [0])[index]),
        )
        groups.setdefault(key, []).append(token)
        total_tokens += 1

    nodes = []
    for key, tokens in sorted(groups.items()):
        left = min(token["bounds"]["x"] for token in tokens)
        top = min(token["bounds"]["y"] for token in tokens)
        right = max(token["bounds"]["x"] + token["bounds"]["width"] for token in tokens)
        bottom = max(token["bounds"]["y"] + token["bounds"]["height"] for token in tokens)
        confidence = sum(token["confidence"] for token in tokens) / len(tokens)
        content = " ".join(token["text"] for token in tokens)
        nodes.append(
            _node(
                "text",
                _box(left, top, right - left, bottom - top),
                method="tesseract.image_to_data",
                evidence={"tokens": tokens, "block": key[0], "paragraph": key[1], "line": key[2]},
                confidence=confidence,
                observed={
                    "text": content,
                    "language": "eng",
                    "style": {},
                },
                sort_key=(top, left, "text", key),
            )
        )
    diagnostics = [f"Tesseract recognized {total_tokens} tokens across {len(nodes)} text runs."]
    if not nodes:
        diagnostics.append("Tesseract found no readable English text; this is valid image evidence, not a capability failure.")
    return nodes, diagnostics


def _contour_nodes(rgb: np.ndarray, edges: np.ndarray, cv2: Any) -> list[dict[str, Any]]:
    height, width = edges.shape
    image_area = width * height
    minimum_area = max(16.0, image_area * 0.000015)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    nodes: list[dict[str, Any]] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < minimum_area:
            continue
        x, y, box_width, box_height = (int(value) for value in cv2.boundingRect(contour))
        bounds = _box(x, y, box_width, box_height)
        if box_width >= width * 0.98 and box_height >= height * 0.98:
            continue
        perimeter = float(cv2.arcLength(contour, True))
        if perimeter <= 0:
            continue
        approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        rectangularity = min(1.0, area / max(1.0, box_width * box_height))
        aspect = max(box_width, box_height) / max(1, min(box_width, box_height))
        if len(approximation) >= 4 and aspect < 12 and rectangularity >= 0.35:
            rounded = len(approximation) > 4 and rectangularity >= 0.45
            primitive_type = "rounded_rectangle" if rounded else "rectangle"
            confidence = min(0.98, 0.58 + rectangularity * 0.4)
            nodes.append(
                _node(
                    primitive_type,
                    bounds,
                    method="opencv.findContours.approxPolyDP",
                    evidence={
                        "contour_area": round(area, 3),
                        "perimeter": round(perimeter, 3),
                        "vertices": len(approximation),
                        "rectangularity": round(rectangularity, 4),
                    },
                    confidence=confidence,
                    observed={"style": {}},
                    sort_key=(y, x, primitive_type, -round(area, 3)),
                )
            )
        circularity = 4 * np.pi * area / max(perimeter * perimeter, 1.0)
        if len(approximation) >= 6 and aspect < 5 and circularity >= 0.58 and area >= minimum_area * 1.5:
            ellipse = cv2.fitEllipse(contour)
            major, minor = sorted((float(ellipse[1][0]), float(ellipse[1][1])))
            ratio = minor / max(major, 1.0)
            primitive_type = "circle" if ratio >= 0.8 else "ellipse"
            confidence = min(0.9, 0.52 + circularity * 0.3 + ratio * 0.12)
            nodes.append(
                _node(
                    primitive_type,
                    bounds,
                    method="opencv.fitEllipse",
                    evidence={"axis_ratio": round(ratio, 4), "circularity": round(circularity, 4), "contour_area": round(area, 3)},
                    confidence=confidence,
                    observed={"style": {}},
                    sort_key=(y, x, primitive_type, -round(area, 3)),
                )
            )
        if 16 <= area <= min(image_area * 0.006, 5000) and aspect <= 6 and len(approximation) not in {4, 5} and circularity < 0.58:
            nodes.append(
                _node(
                    "icon",
                    bounds,
                    method="opencv.connected-contour-residual",
                    evidence={"contour_area": round(area, 3), "vertices": len(approximation), "region_sha256": _region_fingerprint(rgb, bounds)},
                    confidence=0.52,
                    observed={"style": {}},
                    sort_key=(y, x, "icon", -round(area, 3)),
                )
            )
        if box_width >= 24 and box_height >= 24 and area >= image_area * 0.002:
            crop = rgb[y : y + box_height, x : x + box_width]
            color_spread = float(np.std(crop.astype(np.float32), axis=(0, 1)).mean())
            if color_spread >= 12:
                nodes.append(
                    _node(
                        "image",
                        bounds,
                        method="opencv.color-variance-region",
                        evidence={"color_spread": round(color_spread, 4), "contour_area": round(area, 3), "region_sha256": _region_fingerprint(rgb, bounds)},
                        confidence=min(0.75, 0.38 + color_spread / 100),
                        observed={"style": {}},
                        sort_key=(y, x, "image", -round(area, 3)),
                    )
                )
    return nodes


def _line_nodes(edges: np.ndarray, cv2: Any) -> list[dict[str, Any]]:
    height, width = edges.shape
    minimum_length = max(8, min(width, height) // 35)
    threshold = max(12, min(width, height) // 12)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=threshold,
        minLineLength=minimum_length,
        maxLineGap=2,
    )
    if lines is None:
        return []
    result = []
    seen: list[tuple[int, int, int, int]] = []
    for raw in np.asarray(lines).reshape(-1, 4).tolist():
        x1, y1, x2, y2 = (int(value) for value in raw)
        length = float(np.hypot(x2 - x1, y2 - y1))
        if length < minimum_length:
            continue
        horizontal = abs(y2 - y1) <= 2
        vertical = abs(x2 - x1) <= 2
        if not (horizontal or vertical):
            continue
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        key = (left, top, right, bottom)
        if any(all(abs(key[index] - old[index]) <= 3 for index in range(4)) for old in seen):
            continue
        seen.append(key)
        if horizontal:
            bounds = _box(left, top, max(1, right - left + 1), 1)
        else:
            bounds = _box(left, top, 1, max(1, bottom - top + 1))
        primitive_type = "divider" if length >= max(width, height) * 0.12 else "line"
        result.append(
            _node(
                primitive_type,
                bounds,
                method="opencv.HoughLinesP",
                evidence={"length": round(length, 3), "orientation": "horizontal" if horizontal else "vertical"},
                confidence=min(0.94, 0.62 + length / max(width, height) * 0.25),
                observed={"style": {}},
                sort_key=(top, left, primitive_type, -round(length, 3)),
            )
        )
    return result


def _limit_nodes(nodes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    limited: list[dict[str, Any]] = []
    diagnostics: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        grouped.setdefault(node["primitiveType"], []).append(node)
    for primitive_type, values in grouped.items():
        limit = MAX_NODES_PER_PRIMITIVE.get(primitive_type)
        if limit is not None and len(values) > limit:
            values = sorted(
                values,
                key=lambda node: (
                    -node["confidence"]["overall"],
                    -_box_area(node["absoluteBounds"]),
                    node["absoluteBounds"]["y"],
                    node["absoluteBounds"]["x"],
                ),
            )[:limit]
            diagnostics.append(f"Capped {primitive_type} candidates at {limit}; lower-confidence candidates were omitted from this IR run and remain an extractor limitation.")
        limited.extend(values)
    return limited, diagnostics


def _dedupe_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in sorted(nodes, key=lambda item: item["_sort_key"]):
        bounds = node["absoluteBounds"]
        duplicate = False
        for existing in result:
            if existing["primitiveType"] != node["primitiveType"]:
                continue
            if _box_iou(existing["absoluteBounds"], bounds) >= 0.92:
                if node["confidence"]["overall"] > existing["confidence"]["overall"]:
                    result.remove(existing)
                else:
                    duplicate = True
                break
        if not duplicate:
            result.append(node)
    return result


def _special_nodes(rgb: np.ndarray, original: Any) -> list[dict[str, Any]]:
    height, width = rgb.shape[:2]
    nodes: list[dict[str, Any]] = []
    alpha = None
    if "A" in original.getbands():
        alpha = np.asarray(original.getchannel("A"), dtype=np.uint8)
    if alpha is not None and np.any(alpha < 255):
        mask = alpha < 255
        ys, xs = np.where(mask)
        if len(xs):
            bounds = _box(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))
            nodes.append(
                _node(
                    "mask",
                    bounds,
                    method="pillow.alpha-mask",
                    evidence={"transparent_pixels": int(mask.sum())},
                    confidence=0.98,
                    observed={"alpha": "partial"},
                    sort_key=(bounds["y"], bounds["x"], "mask"),
                )
            )
    # A broad variation across a region is a useful gradient candidate, never a certain style claim.
    corners = np.array(
        [rgb[0, 0], rgb[0, width - 1], rgb[height - 1, 0], rgb[height - 1, width - 1]],
        dtype=np.int16,
    )
    corner_spread = float(np.max(corners, axis=0).astype(np.float32).mean() - np.min(corners, axis=0).astype(np.float32).mean())
    if corner_spread >= 18:
        bounds = _box(0, 0, width, height)
        nodes.append(
            _node(
                "gradient",
                bounds,
                method="pillow.corner-color-trend",
                evidence={"corner_spread": round(corner_spread, 4)},
                confidence=0.48,
                observed={"style": {"background": {"type": "candidate-gradient"}}},
                sort_key=(0, 0, "gradient"),
            )
        )
    return nodes


def _effect_nodes(rgb: np.ndarray, surface_nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Emit conservative effect candidates from surface-local raster evidence."""

    height, width = rgb.shape[:2]
    result: list[dict[str, Any]] = []
    for node in surface_nodes:
        if node["primitiveType"] not in {"rectangle", "rounded_rectangle"}:
            continue
        bounds = node["absoluteBounds"]
        if bounds["width"] < 24 or bounds["height"] < 24 or _box_area(bounds) < width * height * 0.01:
            continue
        x, y = bounds["x"], bounds["y"]
        right = min(width, x + bounds["width"])
        bottom = min(height, y + bounds["height"])
        crop = rgb[max(0, y):bottom, max(0, x):right]
        if crop.shape[0] < 12 or crop.shape[1] < 12:
            continue
        left_half = crop[:, : crop.shape[1] // 2].astype(np.float32)
        right_half = crop[:, crop.shape[1] // 2 :].astype(np.float32)
        gradient_delta = float(abs(left_half.mean() - right_half.mean()))
        if gradient_delta >= 12:
            result.append(
                _node(
                    "gradient",
                    bounds.copy(),
                    method="numpy.surface-half-color-trend",
                    evidence={"mean_half_delta": round(gradient_delta, 4), "source_surface": node["primitiveType"]},
                    confidence=min(0.68, 0.35 + gradient_delta / 100),
                    observed={"style": {"background": {"type": "candidate-gradient"}}},
                    sort_key=(y, x, "gradient", -gradient_delta),
                )
            )
        # A darker, non-uniform ring just outside a surface is only a shadow candidate.
        outer_x = max(0, x - 4)
        outer_y = max(0, y - 4)
        outer_right = min(width, right + 4)
        outer_bottom = min(height, bottom + 4)
        outer = rgb[outer_y:outer_bottom, outer_x:outer_right].astype(np.float32)
        outer_luminance = outer @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        if outer_luminance.size and float(outer_luminance.std()) >= 5:
            result.append(
                _node(
                    "shadow",
                    _box(outer_x, outer_y, outer_right - outer_x, outer_bottom - outer_y),
                    method="numpy.surface-ring-variance",
                    evidence={"ring_luminance_std": round(float(outer_luminance.std()), 4), "source_surface": node["primitiveType"]},
                    confidence=0.34,
                    observed={"style": {"shadow": {"status": "candidate"}}},
                    sort_key=(outer_y, outer_x, "shadow", -float(outer_luminance.std())),
                )
            )
    return result


def _add_style(rgb: np.ndarray, nodes: list[dict[str, Any]]) -> None:
    for node in nodes:
        primitive = node["primitiveType"]
        observed = node.setdefault("observed", {})
        sampled_style = _style_for_box(rgb, node["absoluteBounds"], text=primitive == "text")
        existing_style = observed.get("style", {})
        observed["style"] = {**sampled_style, **existing_style} if existing_style else sampled_style


def extract_image(path: Path, *, tesseract: Path) -> ExtractionResult:
    """Extract observed nodes and return non-JSON debug arrays for optional writers."""

    import cv2

    path = Path(path).expanduser().resolve()
    original = load_image(path)
    rgb_image = original.convert("RGB")
    rgb = np.asarray(rgb_image, dtype=np.uint8)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    height, width = gray.shape
    source_report = inspect_image(path)

    text_nodes, diagnostics = _ocr_nodes(rgb_image, tesseract)
    contour_nodes = _contour_nodes(rgb, edges, cv2)
    line_nodes = _line_nodes(edges, cv2)
    special_nodes = _special_nodes(rgb, original)
    effect_nodes = _effect_nodes(rgb, contour_nodes)
    nodes = _dedupe_nodes(text_nodes + contour_nodes + line_nodes + special_nodes + effect_nodes)
    nodes, truncation_diagnostics = _limit_nodes(nodes)
    diagnostics.extend(truncation_diagnostics)

    # Add a viewport fact before assigning IDs. A viewport is always observed.
    viewport = _node(
        "viewport",
        _box(0, 0, width, height),
        method="image dimensions",
        evidence={"source": str(path)},
        confidence=1.0,
        observed={"style": _style_for_box(rgb, _box(0, 0, width, height))},
        sort_key=(-1, -1, "viewport"),
    )
    nodes.insert(0, viewport)
    _add_style(rgb, nodes)

    for node in nodes:
        node.pop("_sort_key", None)

    primitive_counts = Counter(node["primitiveType"] for node in nodes)
    catalog = {}
    for primitive in PRIMITIVE_TYPES:
        primitive_nodes = [node for node in nodes if node["primitiveType"] == primitive]
        statuses = {node["status"] for node in primitive_nodes}
        catalog[primitive] = {
            "status": "observed" if "observed" in statuses else "candidate" if "candidate" in statuses else "unknown",
            "count": len(primitive_nodes),
            "supported": True,
        }
    capabilities = {
        "preprocessing": ["RGB", "grayscale", "canny_edges"],
        "ocr": {"engine": "tesseract", "language": "eng", "binary": str(tesseract)},
        "geometry": {"engine": "opencv", "detectors": ["contours", "hough_lines", "ellipse_fit"]},
        "primitive_catalog": catalog,
        "semantic_taxonomy": list(SEMANTIC_ROLES),
    }
    diagnostics.append(f"Detected primitive counts: {dict(sorted(primitive_counts.items()))}.")
    return ExtractionResult(
        path=path,
        source={
            "path": str(path),
            "sha256": source_sha256(path),
            "format": source_report["format"],
            "mode": source_report["mode"],
            "width": width,
            "height": height,
            "viewport": f"{width}x{height}",
            "preserved": True,
        },
        nodes=nodes,
        diagnostics=diagnostics,
        capabilities=capabilities,
        debug={
            "original": original,
            "grayscale": gray,
            "edges": edges,
            "rgb": rgb,
        },
    )
