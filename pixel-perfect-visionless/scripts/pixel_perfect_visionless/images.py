"""Image loading, inspection, and pixel comparison primitives."""

from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageChops, ImageEnhance

import numpy as np


class ImageAnalysisError(RuntimeError):
    """Raised when an image cannot be read or compared."""


def load_image(path: Path) -> Image.Image:
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ImageAnalysisError(f"Image file not found: {path}")
    try:
        with Image.open(path) as image:
            return image.copy()
    except Exception as exc:
        raise ImageAnalysisError(f"Could not read image {path}: {exc}") from exc


def load_rgb(path: Path) -> Image.Image:
    return load_image(path).convert("RGB")


def source_sha256(path: Path) -> str:
    digest = sha256()
    try:
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ImageAnalysisError(f"Could not hash image {path}: {exc}") from exc
    return digest.hexdigest()


def parse_viewport(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.lower().replace(" ", "").split("x", 1)
        width, height = int(width_text), int(height_text)
    except (AttributeError, ValueError) as exc:
        raise ImageAnalysisError(f"Invalid viewport {value!r}; expected WIDTHxHEIGHT") from exc
    if width <= 0 or height <= 0:
        raise ImageAnalysisError(f"Viewport dimensions must be positive: {value!r}")
    return width, height


def parse_point(value: str) -> tuple[int, int]:
    try:
        x_text, y_text = (part.strip() for part in value.split(","))
        x, y = int(x_text), int(y_text)
    except ValueError as exc:
        raise ImageAnalysisError(f"Invalid point {value!r}; expected x,y") from exc
    if x < 0 or y < 0:
        raise ImageAnalysisError(f"Point coordinates must be non-negative: {value!r}")
    return x, y


def validate_points(points: Iterable[tuple[int, int]], size: tuple[int, int]) -> list[tuple[int, int]]:
    width, height = size
    result = []
    for x, y in points:
        if x >= width or y >= height:
            raise ImageAnalysisError(f"Point ({x},{y}) falls outside image {width}x{height}")
        result.append((x, y))
    return result


def parse_region(value: str) -> tuple[str, tuple[int, int, int, int]]:
    if "=" in value:
        name, coordinates = value.split("=", 1)
    elif ":" in value:
        name, coordinates = value.split(":", 1)
    else:
        raise ImageAnalysisError(f"Invalid region {value!r}; expected name=x,y,width,height")
    try:
        x, y, width, height = (int(part.strip()) for part in coordinates.split(","))
    except ValueError as exc:
        raise ImageAnalysisError(f"Invalid region {value!r}; expected name=x,y,width,height") from exc
    if not name.strip() or x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ImageAnalysisError(f"Region must use non-negative coordinates and positive size: {value!r}")
    return name.strip(), (x, y, width, height)


def validate_regions(
    regions: Iterable[tuple[str, tuple[int, int, int, int]]], size: tuple[int, int]
) -> list[tuple[str, tuple[int, int, int, int]]]:
    width, height = size
    result = []
    names: set[str] = set()
    for name, (x, y, region_width, region_height) in regions:
        if name in names:
            raise ImageAnalysisError(f"Duplicate region name: {name}")
        if x < 0 or y < 0 or region_width <= 0 or region_height <= 0:
            raise ImageAnalysisError(f"Region {name!r} must have positive size and non-negative coordinates")
        if x + region_width > width or y + region_height > height:
            raise ImageAnalysisError(
                f"Region {name!r} ({x},{y},{region_width},{region_height}) falls outside image {width}x{height}"
            )
        names.add(name)
        result.append((name, (x, y, region_width, region_height)))
    return result


def _serial_color(color: Iterable[int]) -> str:
    return "#%02x%02x%02x" % tuple(int(channel) for channel in color)


def _dominant_colors(image: Image.Image, limit: int = 12) -> list[dict[str, Any]]:
    rgb = image.convert("RGB")
    sample_width = min(160, rgb.width)
    sample_height = max(1, round(rgb.height * sample_width / rgb.width))
    sample = rgb.resize((sample_width, sample_height))
    array = np.asarray(sample, dtype=np.uint8)
    quantized = (array // 8) * 8
    counts = Counter(map(tuple, quantized.reshape(-1, 3)))
    total = sample_width * sample_height
    return [
        {
            "color": _serial_color(color),
            "rgb": [int(channel) for channel in color],
            "pixels": count,
            "fraction": round(count / total, 6),
        }
        for color, count in counts.most_common(limit)
    ]


def _probe_positions(length: int) -> list[int]:
    values = {
        0,
        max(0, length - 1),
        max(0, length - 2),
        round(length * 0.05),
        round(length * 0.10),
        round(length * 0.25),
        round(length * 0.50),
        round(length * 0.75),
        round(length * 0.90),
        round(length * 0.95),
    }
    return sorted(value for value in values if 0 <= value < length)


def _scanline_runs(image: Image.Image, *, axis: str) -> list[dict[str, Any]]:
    if axis not in {"x", "y"}:
        raise ImageAnalysisError(f"Unknown scanline axis: {axis}")
    rgb = image.convert("RGB")
    length = rgb.width if axis == "x" else rgb.height
    positions = _probe_positions(rgb.height if axis == "x" else rgb.width)
    minimum_length = max(8, length // 80)
    result = []
    for position in positions:
        colors = [
            tuple((channel // 8) * 8 for channel in rgb.getpixel((index, position)))
            for index in range(length)
        ] if axis == "x" else [
            tuple((channel // 8) * 8 for channel in rgb.getpixel((position, index)))
            for index in range(length)
        ]
        runs = []
        start = 0
        previous = colors[0]
        for index, color in enumerate(colors[1:], start=1):
            if color == previous:
                continue
            if index - start >= minimum_length:
                runs.append({"start": start, "end": index - 1, "length": index - start, "color": _serial_color(previous)})
            start = index
            previous = color
        if length - start >= minimum_length:
            runs.append({"start": start, "end": length - 1, "length": length - start, "color": _serial_color(previous)})
        runs.sort(key=lambda item: item["length"], reverse=True)
        result.append({"position": position, "runs": runs[:24]})
    return result


def _top_peaks(values: np.ndarray, limit: int = 12, minimum: float = 0.0) -> list[dict[str, Any]]:
    indices = np.where(values > minimum)[0].tolist()
    indices.sort(key=lambda index: float(values[index]), reverse=True)
    return [{"position": int(index), "score": round(float(values[index]), 4)} for index in indices[:limit]]


def edge_map(image: Image.Image) -> Image.Image:
    import cv2

    array = np.asarray(image.convert("RGB"), dtype=np.uint8)
    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    return Image.fromarray(edges)


def _edge_peaks(image: Image.Image) -> dict[str, Any]:
    array = np.asarray(image.convert("RGB"), dtype=np.float32)
    gray = array @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    x_gradient = np.abs(np.diff(gray, axis=1)).mean(axis=0)
    y_gradient = np.abs(np.diff(gray, axis=0)).mean(axis=1)
    return {
        "engine": "numpy",
        "x": _top_peaks(x_gradient, minimum=0.35),
        "y": _top_peaks(y_gradient, minimum=0.35),
    }


def inspect_image(path: Path, *, points: Iterable[tuple[int, int]] = ()) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    image = load_image(path)
    rgb = image.convert("RGB")
    checked = validate_points(points, rgb.size)
    with Image.open(path) as source:
        image_format = source.format
        source_mode = source.mode
    return {
        "path": str(path),
        "sha256": source_sha256(path),
        "format": image_format,
        "mode": source_mode,
        "analysis_mode": "RGB",
        "width": rgb.width,
        "height": rgb.height,
        "viewport": f"{rgb.width}x{rgb.height}",
        "corners": {
            "top_left": list(rgb.getpixel((0, 0))),
            "top_right": list(rgb.getpixel((rgb.width - 1, 0))),
            "bottom_left": list(rgb.getpixel((0, rgb.height - 1))),
            "bottom_right": list(rgb.getpixel((rgb.width - 1, rgb.height - 1))),
        },
        "samples": [
            {"x": x, "y": y, "rgb": list(rgb.getpixel((x, y))), "hex": _serial_color(rgb.getpixel((x, y)))}
            for x, y in checked
        ],
        "dominant_colors": _dominant_colors(rgb),
        "edge_peaks": _edge_peaks(rgb),
        "scanlines": {
            "horizontal": _scanline_runs(rgb, axis="x"),
            "vertical": _scanline_runs(rgb, axis="y"),
        },
        "analysis_engine": "numpy",
    }


def _bbox(mask: np.ndarray) -> dict[str, int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return {
        "x": int(xs.min()),
        "y": int(ys.min()),
        "width": int(xs.max() - xs.min() + 1),
        "height": int(ys.max() - ys.min() + 1),
        "pixels": int(mask.sum()),
    }


def _ranked_density(values: np.ndarray, limit: int = 12) -> list[dict[str, Any]]:
    indices = np.where(values > 0)[0].tolist()
    indices.sort(key=lambda index: float(values[index]), reverse=True)
    return [{"position": int(index), "fraction": round(float(values[index]), 6)} for index in indices[:limit]]


def _tile_hotspots(pixel_error: np.ndarray, tile_size: int, tolerance: int) -> list[dict[str, Any]]:
    height, width = pixel_error.shape
    tiles = []
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            tile = pixel_error[y : y + tile_size, x : x + tile_size]
            tiles.append(
                {
                    "x": x,
                    "y": y,
                    "width": int(tile.shape[1]),
                    "height": int(tile.shape[0]),
                    "mean_error": round(float(tile.mean()), 4),
                    "max_error": int(tile.max()),
                    "mismatch_fraction": round(float((tile > tolerance).mean()), 6),
                }
            )
    tiles.sort(key=lambda tile: (tile["mean_error"], tile["mismatch_fraction"]), reverse=True)
    return tiles[:20]


def _metrics(reference: Image.Image, candidate: Image.Image, tolerance: int) -> dict[str, Any]:
    reference_array = np.asarray(reference.convert("RGB"), dtype=np.int16)
    candidate_array = np.asarray(candidate.convert("RGB"), dtype=np.int16)
    difference = np.abs(reference_array - candidate_array)
    pixel_error = difference.max(axis=2)
    mismatch = pixel_error > tolerance
    return {
        "mean_abs_error": round(float(difference.mean()), 6),
        "mean_abs_error_by_channel": [round(float(value), 6) for value in difference.mean(axis=(0, 1))],
        "max_error": int(pixel_error.max()),
        "exact_fraction": round(float((pixel_error == 0).mean()), 6),
        "within_tolerance_fraction": round(float((~mismatch).mean()), 6),
        "mismatch_fraction": round(float(mismatch.mean()), 6),
        "mismatch_pixels": int(mismatch.sum()),
        "tolerance": tolerance,
        "analysis_engine": "numpy",
        "mismatch_bbox": _bbox(mismatch),
        "top_mismatch_rows": _ranked_density(mismatch.mean(axis=1)),
        "top_mismatch_columns": _ranked_density(mismatch.mean(axis=0)),
        "tile_hotspots": _tile_hotspots(pixel_error, 64, tolerance),
    }


def _region_metrics(reference: Image.Image, candidate: Image.Image, tolerance: int) -> dict[str, Any]:
    metrics = _metrics(reference, candidate, tolerance)
    metrics.pop("tile_hotspots", None)
    return metrics


def compare_images(
    reference_path: Path,
    candidate_path: Path,
    *,
    regions: Iterable[tuple[str, tuple[int, int, int, int]]] = (),
    tolerance: int = 10,
    points: Iterable[tuple[int, int]] = (),
) -> tuple[dict[str, Any], Image.Image, Image.Image]:
    if tolerance < 0 or tolerance > 255:
        raise ImageAnalysisError("Pixel tolerance must be between 0 and 255")
    reference = load_rgb(reference_path)
    candidate = load_rgb(candidate_path)
    if reference.size != candidate.size:
        raise ImageAnalysisError(
            f"Image dimensions differ: reference={reference.width}x{reference.height}, candidate={candidate.width}x{candidate.height}"
        )
    parsed_regions = validate_regions(regions, reference.size)
    checked_points = validate_points(points, reference.size)
    report = {
        "reference": str(Path(reference_path).expanduser().resolve()),
        "candidate": str(Path(candidate_path).expanduser().resolve()),
        "width": reference.width,
        "height": reference.height,
        "viewport": f"{reference.width}x{reference.height}",
        "metrics": _metrics(reference, candidate, tolerance),
        "regions": [],
        "reference_edge_peaks": _edge_peaks(reference),
        "candidate_edge_peaks": _edge_peaks(candidate),
        "samples": {
            "reference": [
                {"x": x, "y": y, "rgb": list(reference.getpixel((x, y))), "hex": _serial_color(reference.getpixel((x, y)))}
                for x, y in checked_points
            ],
            "candidate": [
                {"x": x, "y": y, "rgb": list(candidate.getpixel((x, y))), "hex": _serial_color(candidate.getpixel((x, y)))}
                for x, y in checked_points
            ],
            "delta": [
                {
                    "x": x,
                    "y": y,
                    "delta": [candidate.getpixel((x, y))[channel] - reference.getpixel((x, y))[channel] for channel in range(3)],
                }
                for x, y in checked_points
            ],
        },
        "reference_dominant_colors": _dominant_colors(reference),
        "candidate_dominant_colors": _dominant_colors(candidate),
    }
    for name, (x, y, width, height) in parsed_regions:
        reference_region = reference.crop((x, y, x + width, y + height))
        candidate_region = candidate.crop((x, y, x + width, y + height))
        report["regions"].append({"name": name, "box": [x, y, width, height], **_region_metrics(reference_region, candidate_region, tolerance)})
    return report, reference, candidate


def save_visual_artifacts(
    reference: Image.Image,
    candidate: Image.Image,
    output_dir: Path,
    *,
    tolerance: int = 10,
) -> dict[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = output_dir / "overlay.png"
    diff_overlay_path = output_dir / "diff-overlay.png"
    diff_path = output_dir / "diff.png"
    mask_path = output_dir / "threshold-mask.png"
    blended = Image.blend(reference, candidate, 0.5)
    blended.save(overlay_path)
    reference_array = np.asarray(reference, dtype=np.int16)
    candidate_array = np.asarray(candidate, dtype=np.int16)
    mask = (np.abs(reference_array - candidate_array).max(axis=2) > tolerance).astype("uint8") * 255
    diff_mask = Image.fromarray(mask)
    Image.composite(Image.new("RGB", reference.size, (255, 0, 0)), blended, diff_mask).save(diff_overlay_path)
    ImageEnhance.Brightness(ImageChops.difference(reference, candidate)).enhance(4).save(diff_path)
    diff_mask.save(mask_path)
    return {"overlay": str(overlay_path), "diff_overlay": str(diff_overlay_path), "diff": str(diff_path), "threshold_mask": str(mask_path)}
