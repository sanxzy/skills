"""Normalize a reference/render pair into deterministic RGB PNG evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

try:
    from ._common import (
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_stage,
        atomic_save_png,
        load_pair,
        output_dir,
        parse_hex_color,
        run_entrypoint,
        write_json,
    )
except ImportError:  # pragma: no cover - direct executable path
    from _common import (  # type: ignore
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_stage,
        atomic_save_png,
        load_pair,
        output_dir,
        parse_hex_color,
        run_entrypoint,
        write_json,
    )


def normalize_pair(reference: object, render: object, destination: object, *, background: str = "#ffffff") -> dict[str, object]:
    """Write clean RGB copies and a read-back manifest."""

    color = parse_hex_color(background)
    pair = load_pair(reference, render, background=color)
    directory = output_dir(destination)
    reference_path = atomic_save_png(pair.reference.image, directory / "001-reference.png")
    render_path = atomic_save_png(pair.render.image, directory / "002-render.png")
    manifest_path = directory / "003-manifest.json"
    result: dict[str, object] = {
        "status": "complete",
        "operation": "normalize",
        "conditions": {
            "dimensions": list(pair.size),
            "background": "#%02x%02x%02x" % color,
            "color_mode": "RGB",
            "dimension_policy": "strict; no implicit resize",
        },
        "reference": pair.reference.info.as_dict(),
        "render": pair.render.info.as_dict(),
        "artifacts": {
            "directory": str(directory.resolve()),
            "reference": str(reference_path.resolve()),
            "render": str(render_path.resolve()),
            "manifest": str(manifest_path.resolve()),
        },
    }
    write_json(manifest_path, result)
    # Read-back is performed by write_json; return the same canonical payload.
    return result


def _parser() -> argparse.ArgumentParser:
    parser = PixelPerfectArgumentParser(
        description="Normalize reference and render images without resizing"
    )
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--render", required=True, type=Path)
    parser.add_argument("--task-name", required=True, help="historical artifact task directory name")
    parser.add_argument("--output-dir", type=Path, help="optional empty numeric-prefixed stage under .artifacts/pixel-perfect/<task-name>")
    parser.add_argument("--background", default="#ffffff", help="opaque RGB backdrop for alpha images")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = normalize_pair(
        args.reference,
        args.render,
        artifact_stage(args.task_name, "normalize", args.output_dir),
        background=args.background,
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


__all__ = ["main", "normalize_pair"]
