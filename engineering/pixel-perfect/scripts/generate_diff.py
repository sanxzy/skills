"""Generate machine-readable diff and heatmap evidence for one image pair."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

try:
    from ._common import (
        Image,
        ImageChops,
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_stage,
        atomic_save_png,
        include_mask,
        load_ignore_mask,
        load_pair,
        metrics_for_images,
        output_dir,
        parse_hex_color,
        run_entrypoint,
        write_json,
    )
except ImportError:  # pragma: no cover - direct executable path
    from _common import (  # type: ignore
        Image,
        ImageChops,
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_stage,
        atomic_save_png,
        include_mask,
        load_ignore_mask,
        load_pair,
        metrics_for_images,
        output_dir,
        parse_hex_color,
        run_entrypoint,
        write_json,
    )


def _heatmap(gray):
    """Map zero-to-255 error intensity to a readable blue-yellow-red palette."""

    palette: list[int] = []
    for value in range(256):
        position = value / 255.0
        if position < 0.5:
            amount = position * 2.0
            red, green, blue = 0, int(round(210 * amount)), int(round(255 * (1.0 - amount)))
        else:
            amount = (position - 0.5) * 2.0
            red, green, blue = 255, int(round(210 * (1.0 - amount))), 0
        palette.extend((red, green, blue))
    image = gray.convert("P")
    image.putpalette(palette)
    return image


def _masked_rgb(image, mask):
    mask_rgb = Image.merge("RGB", (mask, mask, mask))
    return ImageChops.multiply(image, mask_rgb)


def generate_diff(
    reference: object,
    render: object,
    destination: object,
    *,
    tolerance: int = 0,
    amplify: int = 4,
    background: str = "#ffffff",
    ignore_mask: object | None = None,
    mask_reason: str | None = None,
) -> dict[str, object]:
    """Write a black/colored diff and a heatmap, then read back the manifest."""

    if ignore_mask is not None and not mask_reason:
        raise PixelPerfectError("an ignore mask requires an explicit --mask-reason")
    color = parse_hex_color(background)
    if type(amplify) is not int or amplify < 1 or amplify > 32:
        raise PixelPerfectError("diff amplify must be an integer between 1 and 32")
    pair = load_pair(reference, render, background=color)
    ignored = load_ignore_mask(ignore_mask, pair.size)
    mask = include_mask(ignored, pair.size)
    metrics = metrics_for_images(pair.reference.image, pair.render.image, mask, tolerance=tolerance)
    difference = ImageChops.difference(pair.reference.image, pair.render.image)
    amplified = difference.point(lambda value: min(255, int(value) * amplify), mode="RGB")
    diff_image = _masked_rgb(amplified, mask)
    max_difference = difference.split()[0]
    for channel in difference.split()[1:]:
        max_difference = ImageChops.lighter(max_difference, channel)
    heatmap = _heatmap(ImageChops.multiply(max_difference, mask))
    directory = output_dir(destination)
    diff_path = atomic_save_png(diff_image, directory / "001-diff.png")
    heatmap_path = atomic_save_png(heatmap, directory / "002-heatmap.png")
    manifest_path = directory / "003-manifest.json"
    result: dict[str, object] = {
        "status": "complete",
        "operation": "diff",
        "reference": pair.reference.info.as_dict(),
        "render": pair.render.info.as_dict(),
        "conditions": {
            "dimensions": list(pair.size),
            "background": "#%02x%02x%02x" % color,
            "tolerance": tolerance,
            "amplify": amplify,
            "ignore_mask": str(Path(ignore_mask).expanduser().resolve()) if ignore_mask is not None else None,
            "mask_reason": mask_reason,
            "mask_semantics": "non-black mask pixels are excluded from comparison",
        },
        "metrics": metrics,
        "artifacts": {
            "directory": str(directory.resolve()),
            "diff": str(diff_path.resolve()),
            "heatmap": str(heatmap_path.resolve()),
            "manifest": str(manifest_path.resolve()),
        },
    }
    write_json(manifest_path, result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = PixelPerfectArgumentParser(description="Generate diff and heatmap PNG evidence")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--render", required=True, type=Path)
    parser.add_argument("--task-name", required=True, help="historical artifact task directory name")
    parser.add_argument("--output-dir", type=Path, help="optional empty numeric-prefixed stage under .artifacts/pixel-perfect/<task-name>")
    parser.add_argument("--tolerance", type=int, default=0)
    parser.add_argument("--amplify", type=int, default=4)
    parser.add_argument("--background", default="#ffffff")
    parser.add_argument("--ignore-mask", type=Path)
    parser.add_argument("--mask-reason")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = generate_diff(
        args.reference,
        args.render,
        artifact_stage(args.task_name, "diff", args.output_dir),
        tolerance=args.tolerance,
        amplify=args.amplify,
        background=args.background,
        ignore_mask=args.ignore_mask,
        mask_reason=args.mask_reason,
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


__all__ = ["generate_diff", "main"]
