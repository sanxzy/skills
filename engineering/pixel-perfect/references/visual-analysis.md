# Visual analysis reference

## Evidence classes

Before implementation, label every statement as one of:

- **Observed:** directly visible in the current reference pixels or target
  project files, such as a dark surface, a two-line heading, or a 1536x1024
  image dimension.
- **Measured:** produced by a repeatable tool or calculation, such as a
  bounding box, color sample, pixel difference, or grid-cell error.
- **Assumed:** a reversible interpretation not proven by the static image,
  such as a likely breakpoint or hover behavior.

Do not turn an assumption into a requirement without user/project evidence.

## Inspection order

1. **Canvas:** dimensions, aspect ratio, transparent/opaque background, and
   whether the image appears cropped or scaled.
2. **Large geometry:** page bands, global gutters, container width, major
   columns, section heights, alignment axes, and background continuation.
3. **Component geometry:** cards, controls, illustration bounds, icon boxes,
   border widths, radii, shadows, and stacking.
4. **Typography:** family, available weights, size, line-height, letter
   spacing, wrapping width, baseline, truncation, and text contrast.
5. **Color roles:** canvas, surface, elevated surface, border, primary text,
   secondary text, accent, success/warning/error, and disabled states.
6. **Assets:** logos, icons, photographs, illustrations, and whether each can
   be implemented with a native primitive or must use a project asset.
7. **State:** visible theme, selected/active/disabled/loading state, scroll
   position, and any content that changes with time or data.

## Measurement discipline

Use a small set of stable anchors instead of measuring every decorative pixel:

- outer canvas edges;
- shared container left/right edges;
- top/bottom of major bands;
- heading baselines and line boxes;
- repeated card widths/gaps;
- control centers and hit areas;
- focal illustration bounds; and
- shadow/glow extents with their overlap margin.

Record the coordinate space. Reference coordinates are full-image pixels, not
renderer-specific units (such as CSS pixels) unless the render condition
explicitly maps them one-to-one. If scale/DPR, zoom, camera, or device mapping
changes the relationship, resolve that condition before comparing.

## Color sampling

Sample broad flat areas for token candidates and compare them against actual
render output. Do not infer a design token from one anti-aliased edge pixel.
When a gradient, texture, shadow, or photograph is present, record the role as
an effect/asset rather than collapsing it into one color.

Alpha images are normalized against the explicitly selected `#RRGGBB` backdrop
by `normalize_images.py`. Use the same backdrop for every iteration and report
it in evidence.

## Typography diagnosis

When text differs, inspect in this order:

1. font/resource file and actual loaded family;
2. weight availability and renderer fallback;
3. font size and line-height;
4. content width and wrapping;
5. letter spacing and text transform; then
6. color and anti-aliasing.

For non-text targets, apply the same order to the relevant material/resource,
object bounds, transform/camera, and renderer-specific sampling settings.

A text mismatch often changes downstream geometry. Do not compensate for a
wrong font by adding arbitrary margins to later components.

## Assets and substitutions

For each material asset, record:

```yaml
id: logo
source: project-local | supplied | unavailable
observed_bounds: [x, y, width, height]
implementation: native-img | svg | icon-primitive | css-shape
substitution: <none or explicit reason>
```

A placeholder is acceptable only when the task allows it and the final report
states the effect. Never use the reference screenshot as the asset.

## Static-image boundary

A reference proves the visible state at one point. It does not prove:

- interaction behavior;
- responsive behavior at another width;
- data loading/error transitions;
- keyboard/focus behavior or other target input behavior; or
- semantics/accessibility not visible in pixels.

Implement only what the target/project contract supports and mark the rest as
unknown or separately verified.
