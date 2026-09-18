"""Shared Pillow, validation, reporting, and metric primitives.

The public scripts intentionally stay small.  This module owns the mechanics
that must behave identically across normalization, comparison, diff creation,
and adaptive-grid analysis.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:  # Pillow is an explicit runtime dependency; never install it here.
    from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat
    _PILLOW_IMPORT_ERROR: Exception | None = None
except ImportError as exc:  # pragma: no cover - exercised without Pillow
    Image = None  # type: ignore[assignment]
    ImageChops = None  # type: ignore[assignment]
    ImageFilter = None  # type: ignore[assignment]
    ImageOps = None  # type: ignore[assignment]
    ImageStat = None  # type: ignore[assignment]
    _PILLOW_IMPORT_ERROR = exc


MAX_IMAGE_PIXELS = 100_000_000
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_PATH_TEXT = 4096
MAX_REGIONS = 256
MAX_GRID_LEAVES = 4096


class PixelPerfectError(RuntimeError):
    """A bounded, user-actionable skill failure."""

    def __init__(self, message: str, *, status: str = "failed") -> None:
        super().__init__(message)
        self.status = status


class PixelPerfectArgumentParser(argparse.ArgumentParser):
    """Keep CLI validation on the same structured JSON error boundary."""

    def error(self, message: str) -> None:
        raise PixelPerfectError(f"invalid arguments: {message}", status="invalid_input")


def require_pillow() -> None:
    """Fail as structured tool-unavailable output instead of a traceback."""

    if _PILLOW_IMPORT_ERROR is not None:
        raise PixelPerfectError(
            "Pillow is unavailable; run the skill with an interpreter that has "
            "Pillow installed (no global installation is performed)",
            status="tool_unavailable",
        )


def run_entrypoint(script: object, argv: Sequence[str]) -> int | None:
    """Ensure ``<cwd>/.venv`` and re-exec direct script calls inside it.

    The public shell dispatcher already enters the runtime; this hook also
    makes direct ``python3 scripts/<tool>.py`` calls obey the same boundary.
    ``os.execve`` does not return on success, so callers can continue to their
    parser only when the current interpreter is already the selected venv.
    """

    script_path = Path(script).resolve()
    try:
        from runtime import ensure_runtime
    except ImportError:  # pragma: no cover - package import path
        from .runtime import ensure_runtime  # type: ignore
    runtime = ensure_runtime(Path.cwd())
    try:
        active_prefix = Path(sys.prefix).resolve()
        selected_prefix = runtime.directory.resolve()
        # Preserve the venv launcher symlink when executing; resolving it to
        # the base interpreter would lose the venv prefix on Unix.
        selected = runtime.python
    except OSError as exc:
        raise PixelPerfectError(f"Could not verify the active runtime interpreter: {safe_text(exc)}", status="runtime_unusable") from exc
    # On Unix a venv's python is normally a symlink to the base executable;
    # comparing only sys.executable would therefore mistake the host Python
    # for the isolated interpreter.
    if (
        active_prefix == selected_prefix
        and sys.base_prefix != sys.prefix
        and _PILLOW_IMPORT_ERROR is None
    ):
        return None
    # If this process imported before a missing Pillow dependency was installed
    # in an already-active venv, reload the module graph in a fresh interpreter.
    environment = dict(os.environ)
    for name in (
        "PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "PYTHONUSERBASE",
        "PIP_CONFIG_FILE", "PIP_TARGET", "PIP_USER", "PIP_PREFIX",
        "PIP_REQUIRE_VIRTUALENV",
    ):
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    os.execve(str(selected), [str(selected), str(script_path), *tuple(argv)], environment)
    return None  # pragma: no cover


def safe_text(value: object, limit: int = 4000) -> str:
    try:
        text = str(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 18)] + "…[truncated]"


def safe_repr(value: object, limit: int = 240) -> str:
    try:
        text = repr(value)
    except Exception:
        text = f"<unrepresentable {type(value).__name__}>"
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 18)] + "…[truncated]"


def checked_text(value: object, label: str, *, max_length: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PixelPerfectError(f"{label} must be a non-blank string")
    text = value.strip()
    if len(text) > max_length:
        raise PixelPerfectError(f"{label} is too long; maximum is {max_length} characters")
    if "\x00" in text:
        raise PixelPerfectError(f"{label} must not contain NUL bytes")
    return text


def input_path(value: object, label: str) -> Path:
    if isinstance(value, Path):
        path = value.expanduser()
    else:
        path = Path(checked_text(value, label, max_length=MAX_PATH_TEXT)).expanduser()
    try:
        if not path.is_file() or path.is_symlink():
            raise PixelPerfectError(f"{label} is not a regular non-symlink file: {path}")
    except OSError as exc:
        raise PixelPerfectError(f"Could not inspect {label}: {safe_text(exc)}") from exc
    return path


def output_dir(value: object) -> Path:
    if isinstance(value, Path):
        path = value.expanduser()
    else:
        path = Path(checked_text(value, "output directory", max_length=MAX_PATH_TEXT)).expanduser()
    try:
        if path.exists() and (path.is_symlink() or not path.is_dir()):
            raise PixelPerfectError(f"Output directory is not a real directory: {path}")
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise PixelPerfectError(f"Output directory is not a real directory: {path}")
    except OSError as exc:
        raise PixelPerfectError(f"Could not prepare output directory {path}: {safe_text(exc)}") from exc
    return path


def output_path(value: object, label: str = "output path") -> Path:
    if isinstance(value, Path):
        path = value.expanduser()
    else:
        path = Path(checked_text(value, label, max_length=MAX_PATH_TEXT)).expanduser()
    try:
        if path.exists() and path.is_symlink():
            raise PixelPerfectError(f"{label} must not be a symlink: {path}")
    except OSError as exc:
        raise PixelPerfectError(f"Could not inspect {label}: {safe_text(exc)}") from exc
    return path


def checked_task_name(value: object) -> str:
    name = checked_text(value, "task name", max_length=100)
    if name in {".", ".."} or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is None:
        raise PixelPerfectError(
            "task name must be one safe path segment using letters, numbers, "
            "dot, underscore, or hyphen"
        )
    return name


def _workspace_path(cwd: object | None = None) -> Path:
    candidate = Path.cwd() if cwd is None else Path(cwd).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise PixelPerfectError(f"Working directory does not exist: {candidate}") from exc
    if not resolved.is_dir():
        raise PixelPerfectError(f"Working directory is not a directory: {resolved}")
    return resolved


def _ensure_namespace_directory(path: Path) -> Path:
    try:
        if path.exists() and path.is_symlink():
            raise PixelPerfectError(f"Artifact namespace must not contain symlinks: {path}")
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink() or not path.is_dir():
            raise PixelPerfectError(f"Artifact namespace is not a real directory: {path}")
    except PixelPerfectError:
        raise
    except OSError as exc:
        raise PixelPerfectError(f"Could not prepare artifact namespace {path}: {safe_text(exc)}") from exc
    return path


def artifact_root(task_name: object, *, cwd: object | None = None) -> Path:
    """Return the only public artifact namespace for one task."""

    workspace = _workspace_path(cwd)
    name = checked_task_name(task_name)
    base = _ensure_namespace_directory(workspace / ".artifacts")
    base = _ensure_namespace_directory(base / "pixel-perfect")
    return _ensure_namespace_directory(base / name)


def allocate_stage(task_name: object, operation: str, *, cwd: object | None = None) -> Path:
    """Atomically allocate the next numeric, append-only task stage."""

    root = artifact_root(task_name, cwd=cwd)
    label = checked_text(operation, "artifact operation", max_length=40).lower()
    if re.fullmatch(r"[a-z0-9-]+", label) is None:
        raise PixelPerfectError("artifact operation must use lowercase letters, numbers, or hyphens")
    used_numbers: set[int] = set()
    try:
        for child in root.iterdir():
            match = re.match(r"^(\d+)-", child.name)
            if match is not None:
                used_numbers.add(int(match.group(1)))
    except OSError as exc:
        raise PixelPerfectError(f"Could not inspect artifact history {root}: {safe_text(exc)}") from exc
    next_number = max(used_numbers, default=0) + 1
    for _ in range(10000):
        candidate = root / f"{next_number:03d}-{label}"
        try:
            candidate.mkdir()
        except FileExistsError:
            next_number += 1
            continue
        except OSError as exc:
            raise PixelPerfectError(f"Could not allocate artifact stage {candidate}: {safe_text(exc)}") from exc
        return candidate
    raise PixelPerfectError(f"Artifact task has reached its stage history limit: {root}")


def artifact_stage(task_name: object, operation: str, explicit: object | None = None, *, cwd: object | None = None) -> Path:
    """Resolve an optional output directory without leaving the task namespace."""

    if explicit is None:
        return allocate_stage(task_name, operation, cwd=cwd)
    root = artifact_root(task_name, cwd=cwd)
    path = output_path(explicit, "artifact output directory")
    try:
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(root.resolve()):
            raise PixelPerfectError(
                f"Artifact output must stay under {root}; refusing {path}"
            )
        if path.exists() and (path.is_symlink() or not path.is_dir()):
            raise PixelPerfectError(f"Artifact output is not a real directory: {path}")
        if re.fullmatch(r"[0-9]{3,}-[a-z0-9-]+", path.name) is None:
            raise PixelPerfectError("artifact output directory must have a numeric prefix, for example 001-normalize")
        path.mkdir(parents=True, exist_ok=True)
        if any(path.iterdir()):
            raise PixelPerfectError(f"Artifact stage is not empty; choose a new numeric stage: {path}")
    except PixelPerfectError:
        raise
    except OSError as exc:
        raise PixelPerfectError(f"Could not validate artifact output directory {path}: {safe_text(exc)}") from exc
    return path


def artifact_report_path(task_name: object, operation: str, explicit: object | None = None, *, cwd: object | None = None) -> Path:
    """Allocate or validate one numeric-prefixed JSON report path."""

    if explicit is None:
        stage = allocate_stage(task_name, operation, cwd=cwd)
        return stage / f"001-{operation}.json"
    root = artifact_root(task_name, cwd=cwd)
    path = output_path(explicit, "artifact report path")
    try:
        if not path.resolve(strict=False).is_relative_to(root.resolve()):
            raise PixelPerfectError(f"Artifact report must stay under {root}; refusing {path}")
        if re.fullmatch(r"[0-9]{3,}-[A-Za-z0-9._-]+\.json", path.name) is None:
            raise PixelPerfectError("artifact report filename must have a numeric prefix")
        if path.exists():
            raise PixelPerfectError(f"Artifact report already exists; choose a new numeric path: {path}")
    except PixelPerfectError:
        raise
    except OSError as exc:
        raise PixelPerfectError(f"Could not validate artifact report path {path}: {safe_text(exc)}") from exc
    return path


def checked_float(value: object, label: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PixelPerfectError(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise PixelPerfectError(f"{label} must be a finite number")
    if minimum is not None and number < minimum:
        raise PixelPerfectError(f"{label} must be at least {minimum:g}")
    if maximum is not None and number > maximum:
        raise PixelPerfectError(f"{label} must be at most {maximum:g}")
    return number


def checked_int(value: object, label: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
    if type(value) is not int:
        raise PixelPerfectError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise PixelPerfectError(f"{label} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise PixelPerfectError(f"{label} must be at most {maximum}")
    return value


def parse_dimensions(value: object, label: str = "dimensions") -> tuple[int, int]:
    text = checked_text(value, label, max_length=40).lower()
    match = re.fullmatch(r"(\d+)x(\d+)", text)
    if match is None:
        raise PixelPerfectError(f"{label} must use WIDTHxHEIGHT, for example 1536x1024")
    width, height = (int(part) for part in match.groups())
    if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
        raise PixelPerfectError(f"{label} must be positive and within the image safety limit")
    return width, height


def parse_point(value: object, label: str = "point") -> tuple[int, int]:
    text = checked_text(value, label, max_length=80)
    parts = text.split(",")
    if len(parts) != 2:
        raise PixelPerfectError(f"{label} must use X,Y")
    try:
        point = tuple(int(part.strip()) for part in parts)
    except ValueError as exc:
        raise PixelPerfectError(f"{label} must use integer X,Y") from exc
    if point[0] < 0 or point[1] < 0:
        raise PixelPerfectError(f"{label} must be non-negative")
    return point  # type: ignore[return-value]


def parse_hex_color(value: object) -> tuple[int, int, int]:
    text = checked_text(value, "background color", max_length=16)
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", text):
        raise PixelPerfectError("background color must use #RRGGBB")
    return tuple(int(text[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]


def _size(value: object, label: str) -> tuple[int, int]:
    try:
        values = tuple(value)  # type: ignore[arg-type]
    except Exception as exc:
        raise PixelPerfectError(f"{label} has unusable dimensions") from exc
    if len(values) != 2 or any(type(item) is not int or item <= 0 for item in values):
        raise PixelPerfectError(f"{label} must have two positive integer dimensions")
    width, height = values
    if width * height > MAX_IMAGE_PIXELS:
        raise PixelPerfectError(f"{label} exceeds the {MAX_IMAGE_PIXELS:,}-pixel safety limit")
    return width, height


@dataclass(frozen=True)
class ImageInfo:
    source_path: str
    source_size: tuple[int, int]
    normalized_size: tuple[int, int]
    source_mode: str
    normalized_mode: str
    alpha_composited: bool
    exif_orientation_applied: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "source_path": self.source_path,
            "source_size": list(self.source_size),
            "normalized_size": list(self.normalized_size),
            "source_mode": self.source_mode,
            "normalized_mode": self.normalized_mode,
            "alpha_composited": self.alpha_composited,
            "exif_orientation_applied": self.exif_orientation_applied,
        }


@dataclass(frozen=True)
class NormalizedImage:
    image: Any
    info: ImageInfo


@dataclass(frozen=True)
class ImagePair:
    reference: NormalizedImage
    render: NormalizedImage
    background: tuple[int, int, int]

    @property
    def size(self) -> tuple[int, int]:
        return self.reference.image.size


def normalize_image(path: object, *, background: tuple[int, int, int]) -> NormalizedImage:
    """Load one raster image, apply EXIF orientation, and produce clean RGB."""

    require_pillow()
    source_path = input_path(path, "image")
    try:
        with Image.open(source_path) as opened:  # type: ignore[union-attr]
            source_size = _size(opened.size, "image")
            source_mode = str(opened.mode)
            try:
                orientation = opened.getexif().get(274)
            except Exception:
                orientation = None
            has_alpha = "A" in opened.getbands() or "transparency" in opened.info
            opened.load()
            oriented = ImageOps.exif_transpose(opened)  # type: ignore[union-attr]
            working = oriented.copy()
        normalized_size = _size(working.size, "normalized image")
        if has_alpha:
            rgba = working.convert("RGBA")
            backdrop = Image.new("RGBA", rgba.size, (*background, 255))  # type: ignore[union-attr]
            normalized = Image.alpha_composite(backdrop, rgba).convert("RGB")  # type: ignore[union-attr]
        else:
            normalized = working.convert("RGB")
        normalized.load()
    except PixelPerfectError:
        raise
    except Exception as exc:
        raise PixelPerfectError(f"Could not decode image {source_path}: {safe_text(exc)}", status="invalid_input") from exc
    return NormalizedImage(
        image=normalized,
        info=ImageInfo(
            source_path=str(source_path.resolve()),
            source_size=source_size,
            normalized_size=normalized_size,
            source_mode=source_mode,
            normalized_mode="RGB",
            alpha_composited=has_alpha,
            exif_orientation_applied=orientation not in (None, 1),
        ),
    )


def load_pair(reference: object, render: object, *, background: tuple[int, int, int]) -> ImagePair:
    reference_image = normalize_image(reference, background=background)
    render_image = normalize_image(render, background=background)
    if reference_image.image.size != render_image.image.size:
        raise PixelPerfectError(
            "Reference and render dimensions differ; normalize the render "
            "conditions instead of silently resizing either image: "
            f"reference={reference_image.image.size}, render={render_image.image.size}",
            status="incompatible_input",
        )
    return ImagePair(reference_image, render_image, background)


def _regular_target(path: Path) -> None:
    try:
        if path.exists() and path.is_symlink():
            raise PixelPerfectError(f"Artifact target must not be a symlink: {path}")
    except OSError as exc:
        raise PixelPerfectError(f"Could not inspect artifact target {path}: {safe_text(exc)}") from exc


def atomic_write_text(path: object, text: str) -> Path:
    target = output_path(path)
    _regular_target(target)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.parent.is_symlink():
            raise PixelPerfectError(f"Artifact parent must not be a symlink: {target.parent}")
        fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        if not target.is_file() or target.is_symlink():
            raise PixelPerfectError(f"Atomic write did not produce a regular file: {target}")
    except PixelPerfectError:
        raise
    except OSError as exc:
        raise PixelPerfectError(f"Could not write artifact {target}: {safe_text(exc)}") from exc
    return target


def write_json(path: object, value: object) -> Path:
    try:
        encoded = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    except (TypeError, ValueError) as exc:
        raise PixelPerfectError(f"Could not serialize JSON artifact: {safe_text(exc)}") from exc
    target = atomic_write_text(path, encoded)
    read_json(target)
    return target


def read_json(path: object) -> Any:
    target = input_path(path, "JSON input")
    try:
        if target.stat().st_size > MAX_JSON_BYTES:
            raise PixelPerfectError(f"JSON input is larger than {MAX_JSON_BYTES:,} bytes: {target}")
        with target.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except PixelPerfectError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PixelPerfectError(f"Could not read JSON input {target}: {safe_text(exc)}", status="invalid_input") from exc


def atomic_save_png(image: Any, path: object) -> Path:
    require_pillow()
    target = output_path(path)
    _regular_target(target)
    if image is None or not hasattr(image, "save"):
        raise PixelPerfectError("PNG artifact needs a Pillow image")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.parent.is_symlink():
            raise PixelPerfectError(f"Artifact parent must not be a symlink: {target.parent}")
        fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".png", dir=str(target.parent))
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            image.save(temporary, format="PNG", compress_level=6, optimize=False)
            os.replace(temporary, target)
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        if not target.is_file() or target.is_symlink() or target.stat().st_size <= 0:
            raise PixelPerfectError(f"PNG artifact was not materialized: {target}")
        with Image.open(target) as checked:  # type: ignore[union-attr]
            checked.verify()
    except PixelPerfectError:
        raise
    except Exception as exc:
        raise PixelPerfectError(f"Could not write PNG artifact {target}: {safe_text(exc)}") from exc
    return target


def load_ignore_mask(path: object | None, size: tuple[int, int]) -> Any | None:
    """Load a binary ignore mask; non-black pixels are excluded."""

    require_pillow()
    if path is None:
        return None
    source_path = input_path(path, "ignore mask")
    try:
        with Image.open(source_path) as opened:  # type: ignore[union-attr]
            opened.load()
            oriented = ImageOps.exif_transpose(opened)  # type: ignore[union-attr]
            mask = oriented.convert("L")
        if tuple(mask.size) != tuple(size):
            raise PixelPerfectError(
                f"Ignore mask dimensions {mask.size} do not match image dimensions {size}",
                status="incompatible_input",
            )
        return mask.point(lambda value: 255 if value > 0 else 0, mode="L")
    except PixelPerfectError:
        raise
    except Exception as exc:
        raise PixelPerfectError(f"Could not decode ignore mask {source_path}: {safe_text(exc)}", status="invalid_input") from exc


def include_mask(ignore_mask: Any | None, size: tuple[int, int]) -> Any:
    require_pillow()
    if ignore_mask is None:
        return Image.new("L", size, 255)  # type: ignore[union-attr]
    if tuple(ignore_mask.size) != tuple(size):
        raise PixelPerfectError("Ignore mask does not match the comparison dimensions", status="incompatible_input")
    return ImageOps.invert(ignore_mask)  # type: ignore[union-attr]


def _channel_max(image: Any) -> Any:
    channels = image.split()
    result = channels[0]
    for channel in channels[1:]:
        result = ImageChops.lighter(result, channel)  # type: ignore[union-attr]
    return result


def _mask_count(mask: Any) -> int:
    histogram = mask.histogram()
    return int(sum(histogram[1:]))


def _mean_values(image: Any, mask: Any) -> tuple[float, ...]:
    if _mask_count(mask) == 0:
        return tuple(0.0 for _ in image.getbands())
    values = ImageStat.Stat(image, mask=mask).mean  # type: ignore[union-attr]
    return tuple(float(value) for value in values)


def _rounded(value: float) -> float:
    return round(float(value), 6)


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def metrics_for_images(
    reference: Any,
    render: Any,
    mask: Any,
    *,
    tolerance: int = 0,
    calculate_edges: bool = True,
) -> dict[str, object]:
    """Calculate stable full-image or crop metrics for two RGB images."""

    require_pillow()
    if reference.size != render.size or reference.size != mask.size:
        raise PixelPerfectError("Comparison images and mask must have identical dimensions", status="incompatible_input")
    tolerance = checked_int(tolerance, "pixel tolerance", minimum=0, maximum=255)
    total = reference.size[0] * reference.size[1]
    considered = _mask_count(mask)
    if considered == 0:
        raise PixelPerfectError("Comparison mask excludes every pixel", status="invalid_input")
    difference = ImageChops.difference(reference, render)  # type: ignore[union-attr]
    max_difference = _channel_max(difference)
    raw_changed = ImageChops.multiply(  # type: ignore[union-attr]
        max_difference.point(lambda value: 255 if value > 0 else 0, mode="L"), mask
    )
    changed = ImageChops.multiply(  # type: ignore[union-attr]
        max_difference.point(lambda value: 255 if value > tolerance else 0, mode="L"), mask
    )
    channel_means = _mean_values(difference, mask)
    mean_color = sum(channel_means) / len(channel_means)
    weighted_color = sum(mean * weight for mean, weight in zip(
        channel_means, (0.2126, 0.7152, 0.0722)
    ))
    tolerated_difference = difference.point(  # type: ignore[union-attr]
        lambda value: max(0, int(value) - tolerance), mode="RGB"
    )
    tolerated_channels = _mean_values(tolerated_difference, mask)
    tolerated_weighted = sum(mean * weight for mean, weight in zip(
        tolerated_channels, (0.2126, 0.7152, 0.0722)
    ))
    tolerant_color_similarity = _clamp_score(1.0 - tolerated_weighted / 255.0)
    raw_changed_count = _mask_count(raw_changed)
    changed_count = _mask_count(changed)
    color_similarity = _clamp_score(1.0 - (weighted_color / 255.0))
    edge_similarity: float | None = None
    mean_edge: float | None = None
    edge_changed_count: int | None = None
    if calculate_edges:
        reference_edges = reference.convert("L").filter(ImageFilter.FIND_EDGES)  # type: ignore[union-attr]
        render_edges = render.convert("L").filter(ImageFilter.FIND_EDGES)  # type: ignore[union-attr]
        edge_difference = ImageChops.difference(reference_edges, render_edges)  # type: ignore[union-attr]
        edge_mean = _mean_values(edge_difference, mask)[0]
        edge_similarity = _clamp_score(1.0 - edge_mean / 255.0)
        edge_changed = ImageChops.multiply(  # type: ignore[union-attr]
            edge_difference.point(lambda value: 255 if value > tolerance else 0, mode="L"), mask
        )
        mean_edge = edge_mean
        edge_changed_count = _mask_count(edge_changed)
    bounds = changed.getbbox()
    bbox = list(bounds) if bounds is not None else None
    return {
        "width": int(reference.size[0]),
        "height": int(reference.size[1]),
        "total_pixels": total,
        "considered_pixels": considered,
        "ignored_pixels": total - considered,
        "raw_changed_pixels": raw_changed_count,
        "changed_pixels": changed_count,
        "difference_percentage": _rounded(changed_count * 100.0 / considered),
        "raw_difference_percentage": _rounded(raw_changed_count * 100.0 / considered),
        "mean_color_difference": _rounded(mean_color),
        "weighted_color_difference": _rounded(weighted_color),
        "tolerated_weighted_color_difference": _rounded(tolerated_weighted),
        "color_similarity": _rounded(color_similarity),
        "tolerant_color_similarity": _rounded(tolerant_color_similarity),
        "max_channel_mean_difference": _rounded(_mean_values(max_difference, mask)[0]),
        "bbox": bbox,
        "mean_edge_difference": None if mean_edge is None else _rounded(mean_edge),
        "edge_changed_pixels": edge_changed_count,
        "edge_similarity": None if edge_similarity is None else _rounded(edge_similarity),
        "similarity_score": _rounded(color_similarity),
    }


def crop_box(image: Any, box: tuple[int, int, int, int]) -> Any:
    left, top, width, height = box
    return image.crop((left, top, left + width, top + height))


def content_bbox(
    image: Any,
    background: tuple[int, int, int],
    *,
    tolerance: int = 0,
) -> list[int] | None:
    """Return the non-background bounding box as a coarse geometry signal."""

    require_pillow()
    tolerance = checked_int(tolerance, "structure tolerance", minimum=0, maximum=255)
    backdrop = Image.new("RGB", image.size, background)  # type: ignore[union-attr]
    difference = ImageChops.difference(image, backdrop)  # type: ignore[union-attr]
    changed = _channel_max(difference).point(
        lambda value: 255 if value > tolerance else 0, mode="L"
    )
    bounds = changed.getbbox()
    return list(bounds) if bounds is not None else None


@dataclass(frozen=True)
class RegionSpec:
    name: str
    bbox: tuple[int, int, int, int]
    weight: float = 1.0
    critical: bool = False
    threshold: float | None = None

    def as_dict(self) -> dict[str, object]:
        value: dict[str, object] = {
            "name": self.name,
            "bbox": list(self.bbox),
            "weight": _rounded(self.weight),
            "critical": self.critical,
        }
        if self.threshold is not None:
            value["threshold"] = _rounded(self.threshold)
        return value


def load_regions(path: object | None, size: tuple[int, int]) -> tuple[RegionSpec, ...]:
    if path is None:
        return ()
    value = read_json(path)
    if isinstance(value, Mapping):
        value = value.get("regions")
    if not isinstance(value, list):
        raise PixelPerfectError("regions JSON must be a list or an object with a regions list", status="invalid_input")
    if len(value) > MAX_REGIONS:
        raise PixelPerfectError(f"regions JSON may contain at most {MAX_REGIONS} regions")
    result: list[RegionSpec] = []
    names: set[str] = set()
    image_width, image_height = size
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            raise PixelPerfectError(f"region {index} must be a JSON object")
        raw_name = item.get("name", f"region-{index}")
        name = checked_text(raw_name, f"region {index} name", max_length=120)
        if name in names:
            raise PixelPerfectError(f"region names must be unique: {name}")
        names.add(name)
        raw_box = item.get("bbox")
        if raw_box is None:
            raw_box = [item.get("x"), item.get("y"), item.get("width"), item.get("height")]
        try:
            parts = tuple(raw_box)
        except Exception as exc:
            raise PixelPerfectError(f"region {name} bbox must be [x, y, width, height]") from exc
        if len(parts) != 4 or any(type(part) is not int for part in parts):
            raise PixelPerfectError(f"region {name} bbox must contain four integers")
        x, y, width, height = parts
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > image_width or y + height > image_height:
            raise PixelPerfectError(f"region {name} bbox must lie inside image dimensions {size}")
        weight = checked_float(item.get("weight", 1.0), f"region {name} weight", minimum=0.000001, maximum=1_000_000.0)
        critical = item.get("critical", False)
        if type(critical) is not bool:
            raise PixelPerfectError(f"region {name} critical must be boolean")
        threshold_value = item.get("threshold")
        threshold = None if threshold_value is None else checked_float(
            threshold_value, f"region {name} threshold", minimum=0.0, maximum=1.0
        )
        result.append(RegionSpec(name, (x, y, width, height), weight, critical, threshold))
    return tuple(result)


def selected_similarity(metrics: Mapping[str, object], mode: str) -> float:
    if mode == "edge":
        value = metrics.get("edge_similarity")
    elif mode == "tolerant":
        value = metrics.get("tolerant_color_similarity")
    else:
        value = metrics.get("color_similarity")
    return float(value) if isinstance(value, (int, float)) else 0.0


def comparison_report(
    pair: ImagePair,
    *,
    mode: str,
    tolerance: int,
    ignore_mask: Any | None = None,
    ignore_mask_path: object | None = None,
    mask_reason: str | None = None,
    regions: Sequence[RegionSpec] = (),
    structure_background: tuple[int, int, int] | None = None,
    structure_tolerance: int = 0,
) -> dict[str, object]:
    allowed_modes = {"exact", "tolerant", "region-weighted", "edge", "color-aware"}
    if mode not in allowed_modes:
        raise PixelPerfectError(f"comparison mode must be one of: {', '.join(sorted(allowed_modes))}")
    tolerance = checked_int(tolerance, "pixel tolerance", minimum=0, maximum=255)
    if mode == "exact" and tolerance != 0:
        raise PixelPerfectError("exact comparison requires --tolerance 0")
    if mode == "region-weighted" and not regions:
        raise PixelPerfectError("region-weighted comparison requires a non-empty --regions JSON file")
    if ignore_mask_path is not None and not mask_reason:
        raise PixelPerfectError("an ignore mask requires an explicit --mask-reason")
    mask = include_mask(ignore_mask, pair.size)
    metrics = metrics_for_images(pair.reference.image, pair.render.image, mask, tolerance=tolerance)
    region_rows: list[dict[str, object]] = []
    weighted_sum = 0.0
    weight_total = 0.0
    for spec in regions:
        local_mask = crop_box(mask, spec.bbox)
        local_metrics = metrics_for_images(
            crop_box(pair.reference.image, spec.bbox),
            crop_box(pair.render.image, spec.bbox),
            local_mask,
            tolerance=tolerance,
        )
        score = selected_similarity(local_metrics, mode if mode != "region-weighted" else "color-aware")
        row: dict[str, object] = {
            **spec.as_dict(),
            "metrics": local_metrics,
            "similarity_score": _rounded(score),
        }
        if spec.threshold is not None:
            row["passed"] = score >= spec.threshold
        elif spec.critical:
            row["passed"] = None
        region_rows.append(row)
        weighted_sum += spec.weight * score
        weight_total += spec.weight
    weighted_similarity = weighted_sum / weight_total if weight_total else None
    selected = weighted_similarity if mode == "region-weighted" else selected_similarity(metrics, mode)
    metrics["similarity_score"] = _rounded(selected)
    report: dict[str, object] = {
        "status": "complete",
        "reference": pair.reference.info.as_dict(),
        "render": pair.render.info.as_dict(),
        "conditions": {
            "dimensions": list(pair.size),
            "background": "#%02x%02x%02x" % pair.background,
            "mode": mode,
            "tolerance": tolerance,
            "ignore_mask": str(Path(ignore_mask_path).expanduser().resolve()) if ignore_mask_path is not None else None,
            "mask_reason": mask_reason,
            "mask_semantics": "non-black mask pixels are excluded from comparison",
        },
        "metrics": metrics,
        "regions": region_rows,
    }
    if weighted_similarity is not None:
        report["weighted_similarity"] = _rounded(weighted_similarity)
    critical = [row for row in region_rows if row.get("critical") is True]
    report["critical_regions"] = critical
    if structure_background is not None:
        structure_tolerance = checked_int(
            structure_tolerance, "structure tolerance", minimum=0, maximum=255
        )
        reference_bbox = content_bbox(
            pair.reference.image,
            structure_background,
            tolerance=structure_tolerance,
        )
        render_bbox = content_bbox(
            pair.render.image,
            structure_background,
            tolerance=structure_tolerance,
        )
        displacement = None
        if reference_bbox is not None and render_bbox is not None:
            displacement = [
                render_bbox[index] - reference_bbox[index]
                for index in range(4)
            ]
        report["structure"] = {
            "background": "#%02x%02x%02x" % structure_background,
            "tolerance": structure_tolerance,
            "reference_content_bbox": reference_bbox,
            "render_content_bbox": render_bbox,
            "bbox_displacement": displacement,
            "note": "coarse non-background bounds; not a semantic element measurement",
        }
    return report


def parse_grid_spec(value: object) -> tuple[int, int]:
    text = checked_text(value, "grid", max_length=40).lower()
    match = re.fullmatch(r"(\d+)x(\d+)", text)
    if match is None:
        raise PixelPerfectError("grid must use ROWSxCOLUMNS, for example 4x4")
    rows, columns = (int(part) for part in match.groups())
    if rows < 1 or columns < 1 or rows > 64 or columns > 64:
        raise PixelPerfectError("grid rows and columns must be between 1 and 64")
    return rows, columns


def split_axis(length: int, parts: int) -> tuple[tuple[int, int], ...]:
    return tuple((index * length // parts, (index + 1) * length // parts) for index in range(parts))


def json_result(result: Mapping[str, object], *, output: object | None = None) -> dict[str, object]:
    payload = dict(result)
    if output is not None:
        target = write_json(output, payload)
        payload["artifacts"] = {**(payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}), "report": str(target.resolve())}
        # Persist the final version once more so the on-disk report includes its own pointer.
        write_json(target, payload)
    return payload


__all__ = [
    "Image",
    "ImageChops",
    "ImageFilter",
    "ImageOps",
    "ImageStat",
    "ImageInfo",
    "ImagePair",
    "NormalizedImage",
    "PixelPerfectArgumentParser",
    "PixelPerfectError",
    "RegionSpec",
    "MAX_GRID_LEAVES",
    "artifact_report_path",
    "artifact_root",
    "artifact_stage",
    "atomic_save_png",
    "atomic_write_text",
    "checked_float",
    "checked_int",
    "checked_task_name",
    "checked_text",
    "comparison_report",
    "content_bbox",
    "crop_box",
    "include_mask",
    "input_path",
    "json_result",
    "load_ignore_mask",
    "load_pair",
    "load_regions",
    "metrics_for_images",
    "normalize_image",
    "output_dir",
    "output_path",
    "parse_dimensions",
    "parse_hex_color",
    "parse_grid_spec",
    "parse_point",
    "read_json",
    "require_pillow",
    "run_entrypoint",
    "safe_repr",
    "safe_text",
    "split_axis",
    "write_json",
]
