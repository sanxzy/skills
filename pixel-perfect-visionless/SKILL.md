---
name: pixel-perfect-visionless
version: 1.0.0
description: |
  Compile a screenshot into a deterministic, framework-agnostic visual UI
  intermediate representation for coding agents without native vision. Produces
  persistent structured facts, layout text, ASCII orientation, and actionable
  pixel/element comparison reports.
---

# Pixel-perfect visionless

Use this skill when the coding agent cannot inspect screenshots natively and must reproduce a UI from deterministic textual and structured evidence. The screenshot remains the source of truth; implementation labels and layout hypotheses never overwrite measured image-space facts.

The companion `pixel-perfect` skill is intended for screenshot-first workflows used by vision-capable agents. This skill is self-contained and does not import or depend on it.

## Core contract

```text
screenshot -> observed facts -> visual-ui-ir v1
          -> layout text + ASCII projections
          -> implementation
          -> rendered screenshot
          -> pixel + structured visual diff
```

The canonical artifact is `design.struct.json`:

```json
{
  "schema": "visual-ui-ir",
  "version": 1,
  "source": {},
  "nodes": [],
  "scene_graph": {},
  "relationships": [],
  "inference": {},
  "capabilities": {},
  "diagnostics": []
}
```

`source`, `nodes[].observed`, and measured pixel evidence are facts. `relationships`, `nodes[].inference`, semantic roles, and layout hypotheses are inferences. Both layers remain inspectable. Unknown or ambiguous evidence is represented with `status`, `method`, `evidence`, and `confidence`; it is not silently invented or discarded.

## Reference-image use rule

This is a hard anti-bypass rule: do not bypass the bundled analysis and comparison scripts by displaying the reference/design screenshot in the implementation. Never use the reference/design screenshot itself as runtime UI content. Do not install it as a CSS `background`/`background-image`, `<img>`/`<picture>`, `mask-image`, canvas or texture, CSS `content`, data URI, imported asset, overlay, or any equivalent screenshot-based shortcut. Do not crop or slice the screenshot into implementation assets, and do not make the rendered project depend on the reference file or artifact path. The reference image is an analysis and comparison input only; recreate the interface from measured evidence, using existing project assets or separately authored individual assets when required.

## Environment and persistence

The bundled CLI is:

```bash
python <skill-root>/scripts/pixel-perfect-visionless.py <command> ...
```

The invocation workspace is the current working directory:

```text
<cwd>/.xzy-env/pixel-perfect-visionless/
<cwd>/.artifacts/pixel-perfect-visionless/
```

The runtime automatically installs and validates these Python packages inside its workspace virtual environment:

- Pillow;
- NumPy;
- `opencv-python-headless`;
- `pytesseract`.

Tesseract is the required OCR binary and `eng` is the MVP language data. Setup detects supported package managers (`brew`, `apt-get`, `dnf`, `choco`, and `winget`) and attempts non-interactive installation. Missing permissions, package managers, binary, or language data are hard failures for this visionless skill. The error and attempted commands are persisted before the command exits.

Do not install these dependencies globally. Do not commit `.xzy-env`, generated runs, screenshots, or reports.

## Commands

| Command | Purpose |
| --- | --- |
| `setup` | Install and validate the complete Python, OCR, and optional browser toolchain. |
| `inspect` | Persist source image metadata, colors, probes, edges, and preprocessing evidence. |
| `compile` | Extract OCR, primitives, hierarchy, relationships, semantics, UI IR, layout text, and ASCII. |
| `render` | Capture an application at the reference viewport. |
| `compare` | Compare raw screenshots and persist pixel plus element-level structured differences. |
| `verify` | Render when needed, compare, apply thresholds, and persist the acceptance verdict. |

Every command writes a persistent run directory under `.artifacts/pixel-perfect-visionless/runs/`. Previous runs are immutable; `latest.json` points to the newest run. Complete results are in files; stdout emits one compact JSON pointer containing the status, operation, run directory, and `result.json`/`result.md` paths. Read those paths only when deeper evidence is needed.

Typical workflow:

```bash
python /path/to/pixel-perfect-visionless/scripts/pixel-perfect-visionless.py setup \
  --project-root /path/to/project

python /path/to/pixel-perfect-visionless/scripts/pixel-perfect-visionless.py compile \
  --project-root /path/to/project \
  --reference design.png \
  --debug-artifacts

python /path/to/pixel-perfect-visionless/scripts/pixel-perfect-visionless.py render \
  --project-root /path/to/project \
  --reference design.png \
  --url http://localhost:3000

python /path/to/pixel-perfect-visionless/scripts/pixel-perfect-visionless.py compare \
  --reference design.png \
  --candidate .artifacts/pixel-perfect-visionless/runs/.../candidate.png

python /path/to/pixel-perfect-visionless/scripts/pixel-perfect-visionless.py verify \
  --project-root /path/to/project \
  --reference design.png \
  --url http://localhost:3000 \
  --max-mae 10 \
  --max-region-mae 15 \
  --min-within-tolerance 0.85
```

A compile run contains:

```text
design.struct.json       canonical UI IR v1
design.layout.txt        compact text projection
design.ascii             spatial orientation projection
compile.json             result and artifact manifest
compile.md               human/LLM-readable summary
manifest.json            source/configuration/toolchain provenance
result.json/result.md    persistent operation result
```

`--debug-artifacts` additionally writes the untouched RGB source copy, grayscale image, edge map, and detected-geometry overlay.

## UI IR v1

### Observed nodes

The low-level primitive catalog is:

```text
viewport, rectangle, rounded_rectangle, line, circle, ellipse,
text, image, icon, divider, shadow, gradient, mask, container
```

Each node retains:

- deterministic `id`;
- `primitiveType`;
- `status`: `observed`, `candidate`, or `unknown`;
- `absoluteBounds` in source image coordinates;
- optional `relativeBounds`, `parentId`, and `children`;
- observed text/style data;
- detection method and evidence;
- confidence;
- separate inference data.

OCR uses Tesseract `eng` and emits line/paragraph text runs with token boxes and token confidence evidence. Font family, weight, and size are not asserted as facts in the MVP.

Basic per-node solid foreground/background colors are measured where possible. Border, radius, opacity, gradient, shadow, mask, and other effect observations may be candidates with confidence rather than guaranteed measurements.

Images and icons are represented as raster regions with bounds, colors, deterministic evidence, and confidence. The MVP does not recover the original asset file or component library.

### Relationships and semantics

The analyzer preserves absolute bounds while deriving:

- parent-child containment and parent-relative bounds;
- left/right/center alignment;
- equal width/height;
- vertical/horizontal gaps;
- repeated geometry.

Every relationship includes evidence and confidence. Semantic role candidates use this fixed MVP taxonomy:

```text
container, button, input, card, navbar, sidebar,
modal, dropdown, list, image, icon, divider, text
```

Semantic roles are hypotheses, not replacements for primitive types. Framework-specific CSS, React, Flutter, or component-library hints are deferred.

## Text and ASCII projections

`design.layout.txt` always separates:

1. **Observed scene** — node types, bounds, text, and observed styles;
2. **Relationships** — containment, alignment, spacing, and repetition evidence;
3. **Inference** — semantic candidates and confidence-scored hypotheses.

`design.ascii` is generated from the IR bounds. It is only a coarse spatial orientation aid. It is never a numerical source of truth.

Regions use `name=x,y,width,height` (repeat `--region`) and can receive a separate `--max-region-mae` verification threshold.

## Structured comparison

`compare` extracts both reference and candidate screenshots with the same deterministic pipeline. It writes:

- pixel metrics: MAE, exact fraction, tolerance fraction, mismatch bbox, rows/columns, tiles, regions, and visual overlays;
- `reference.struct.json` and `candidate.struct.json`;
- `diff.json` and `diff.md` with match confidence;
- expected/actual/delta bounds, primitive types, text, styles, and unmatched node lists;
- category statuses for geometry, position, dimensions, color, typography, borders, radius, shadows, alignment, spacing, assets, and pixel similarity.

Categories are explicitly `measured`, `candidate`, or `unavailable`. Aggregate similarity excludes unavailable categories and lists the exclusions. Ambiguous matches are not forced into one-to-one pairs.

Read `comparison.md` first because it is the concise comparison summary. Open the usually much larger `comparison.json` only when exact pixel metrics, probes, regions, structured matches, or other detailed evidence are needed. For structured node details, use `diff.md` before `diff.json` when the comparison artifact provides both.

## Visionless workflow

1. Run `inspect` and read `inspection.json`/`inspection.md`.
2. Run `compile` and read `design.struct.json` first, then `design.layout.txt` and `design.ascii`.
3. Map IR node IDs and layout owners to the target project's source modules.
4. Implement one dependency-ordered section or one diagnosed cause at a time.
5. Render at the exact reference viewport.
6. Run `compare` and read `comparison.md` first; open `comparison.json` only when the Markdown summary does not contain the required detail.
7. Make one focused edit based on the highest-impact measurable mismatch.
8. Rerender immediately and check the active region plus accepted regions.
9. Run `verify` with explicit thresholds and the project's normal tests/build/lint/typecheck.
10. Report remaining mismatch, unavailable categories, toolchain versions, and the next hypothesis honestly.

Do not claim to have visually inspected the screenshot. If evidence is insufficient, state the uncertainty and preserve it in the artifact.

## Failure and completion rules

Hard failures must be persisted and stop the operation:

- missing required Python package or import;
- missing Tesseract or `eng` data;
- unreadable source/candidate image;
- dimension mismatch;
- browser failure;
- unwritable artifact directory.

An image with no readable text or no confidently detectable shape is valid evidence. Emit an empty/candidate extraction with diagnostics rather than inventing nodes.

Before accepting a match, confirm:

- reference and candidate dimensions match;
- threshold checks pass;
- important regions and structured nodes have no unacceptable regression;
- browser/runtime checks pass;
- the application's normal behavior checks pass;
- all reports and diagnostics are persistent;
- no generated runtime/artifacts are included in the source change.

The MVP is intentionally single-viewport, English-only, classical/deterministic, and framework-agnostic. Multilingual OCR, multi-viewport inference, source asset matching, heavy ML, and framework-specific code generation are deferred.
