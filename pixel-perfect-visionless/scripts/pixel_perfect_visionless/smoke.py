"""Conservative screenshot smoke checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .images import load_rgb


def smoke_check(path: Path) -> dict[str, Any]:
    image = load_rgb(path)
    sample_width = min(96, image.width)
    sample_height = max(1, round(image.height * sample_width / image.width))
    sample = image.resize((sample_width, sample_height))
    flattened = getattr(sample, "get_flattened_data", None)
    colors = len(set(flattened() if flattened is not None else sample.getdata()))
    spans = [high - low for low, high in image.getextrema()]
    non_flat = colors > 1 and max(spans, default=0) > 0
    return {
        "status": "pass" if non_flat else "fail",
        "width": image.width,
        "height": image.height,
        "sample_unique_colors": colors,
        "channel_spans": spans,
        "non_flat": non_flat,
    }
