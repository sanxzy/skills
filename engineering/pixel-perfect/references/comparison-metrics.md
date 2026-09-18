# Comparison metrics reference

## Input contract

`normalize_images.py` converts both inputs to clean RGB PNGs after applying
EXIF orientation and compositing alpha over an explicit backdrop. It enforces
identical dimensions and never resizes implicitly. Every comparison should use
images produced by the same normalization conditions when possible.

## Metrics emitted by `compare`

The report includes:

- `raw_changed_pixels`: pixels with any non-zero channel difference;
- `changed_pixels`: pixels whose maximum channel difference is greater than
  the selected tolerance;
- `difference_percentage`: changed pixels divided by considered pixels;
- `mean_color_difference`: unweighted mean absolute channel difference,
  `0..255`;
- `weighted_color_difference`: luminance-weighted channel difference using
  `(0.2126, 0.7152, 0.0722)`;
- `color_similarity`: `1 - weighted_color_difference / 255`;
- `tolerant_color_similarity`: the same score after subtracting the selected
  per-channel tolerance from each absolute difference (clamped at zero);
- `bbox`: `[left, top, right, bottom]` for tolerated differences, or `null`;
- `edge_similarity`: the same normalized measure on Pillow `FIND_EDGES`
  grayscale maps; and
- considered/ignored pixel counts and dimensions.

The report's `similarity_score` is selected by mode. It is rounded for stable
JSON but the underlying comparison remains pixel based.

## Modes

| Mode | Primary score | Changed-pixel interpretation |
| --- | --- | --- |
| `exact` | color similarity | tolerance must be `0` |
| `tolerant` | tolerant color similarity | max per-channel delta greater than `--tolerance` |
| `color-aware` | luminance-weighted color similarity | same raw/tolerant mask |
| `edge` | edge-map similarity | tolerance applied to edge differences |
| `region-weighted` | weighted average of named region scores | per-region explicit weight |

No mode turns a low score into acceptance automatically. The agent combines
metrics with critical-region, section, behavior, and implementation checks.

When `--structure-background` is supplied, the report additionally compares
coarse non-background bounding boxes and emits `[dx, dy, dw, dh]` displacement
from reference to render. This is useful for canvas/layout drift but does not
measure a semantic element. Text baseline, overflow, scrollbar, and hit-area
checks remain target-adapter/agent responsibilities.

## Region weights

A region JSON entry uses normalized full-image coordinates:

```json
{
  "name": "primary-cta",
  "bbox": [80, 440, 240, 56],
  "weight": 3,
  "critical": true,
  "threshold": 0.97
}
```

Overlapping regions are permitted and intentional: their explicit weights
control their influence. A threshold is evaluated against that region's
selected similarity. A critical region without a threshold reports `passed:
null`; the agent must not invent one.

## Ignore masks

An ignore mask is an explicit exception, not a cleanup shortcut:

- it must have the same dimensions as the comparison images;
- non-black pixels are excluded;
- every command using it requires `--mask-reason`; and
- the reason and mask path are persisted in the output.

If every pixel is excluded, the operation fails because no visual claim can be
established. Dynamic masking should be rare and approved by the task contract.

## Adaptive grid

`analyze_grid.py` starts with a `4x4` partition by default. For each cell:

```text
severity = max(
  tolerated_changed_pixels / considered_pixels,
  mean_color_difference / 255
)
```

It repeatedly subdivides the highest-severity eligible leaf into four
quadrants, bounded by threshold, minimum cell size, maximum depth, and maximum
leaf count. The output contains:

- coarse cells;
- final leaves;
- full-image `[x, y, width, height]` coordinates;
- refinement paths and termination reason; and
- sorted hotspots.

This is a localization aid. It does not identify a component or prove that a
semantic section is correct.

## Anti-aliasing policy

Use tolerance only when the renderer, target coordinate/scale conditions,
resources, and state are otherwise identical and the residual difference is a
small, stable anti-aliasing or encoding effect. Compare raw metrics as well as
tolerated metrics. A tolerance must not hide geometry, text wrapping, contrast,
missing assets, overflow, or a critical target element. Record the exact
tolerance and reason in the final report.

## Diff artifacts

`generate_diff.py` writes into the next numeric stage under
`.artifacts/pixel-perfect/<task_name>/`:

- `001-diff.png`: amplified RGB channel difference, black where unchanged or
  excluded; and
- `002-heatmap.png`: blue-to-yellow-to-red intensity map of maximum channel
  error, followed by a numeric manifest JSON.

Inspect the actual images. A file existing or an FFmpeg/browser/renderer
command returning successfully is not a semantic visual observation.
