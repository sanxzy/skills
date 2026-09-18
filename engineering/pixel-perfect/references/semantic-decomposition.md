# Semantic decomposition reference

## Why semantics precede the grid

A pixel grid identifies where pixels differ; it does not explain which
component, object, or target element owns the error. Map the composition into
meaningful sections first, then use grid coordinates to prioritize and localize
corrections. The screen/dashboard example below is illustrative; the same
schema applies to scenes, documents, canvases, and native surfaces.

## Section schema

Use a section/component map such as:

```yaml
screen:
  id: dashboard
  region: [0, 0, 1536, 1024]
  children:
    - id: header
      region: [0, 0, 1536, 72]
      components: [brand, navigation, account-menu]
      depends_on: [global-container, font-loading]
      comparison_region: [0, 0, 1536, 84]
      threshold: 0.97
      weight: 1
      critical: true
      criteria:
        - brand and navigation share the header baseline
        - right actions keep the reference gutter
      status: pending
    - id: hero
      region: [80, 120, 1376, 360]
      components: [eyebrow, heading, body, primary-cta, illustration]
      depends_on: [header, typography-tokens]
      comparison_region: [64, 96, 1408, 408]
      criteria:
        - heading wraps into the observed line count
        - illustration does not clip its glow
      status: pending
```

Each record should have:

- stable `id`;
- full-image `region`;
- named components and ownership;
- dependencies;
- `comparison_region` with effect overlap;
- local acceptance criteria; and
- `pending`, `implementing`, `comparing`, `matched`, or `blocked` status.

## Global constraints

Record constraints that cross sections:

- one shared max-width/container and gutter token;
- common left/right alignment axes;
- page background continuation;
- stacking/z-index order;
- typography scale and baselines;
- shared card/control radius, border, and shadow tokens;
- vertical rhythm between sections; and
- breakpoint, camera, scene, or other render-condition/state transitions.

A section correction must not silently change a shared constraint. If it does,
rerender every affected reference and record the regression decision.

## Ownership map

When a grid hotspot is reported, map it to the smallest likely owner or
rendering constraint:

```text
R1:C3–C4 → header/actions → global right gutter + action group
R2:C1–C3 → hero/copy → font metrics + copy width
R3:C2   → feature-card → card height + internal spacing
```

The mapping is a hypothesis until a focused correction and comparison support
it. Do not make unrelated property changes merely because a cell is red.

## Local acceptance

A local region can be marked matched only after:

1. its semantic criteria are satisfied;
2. the comparison region was measured;
3. effect overlap was included; and
4. a full composition render shows no regression.

Local success never overrides a failed critical region or global threshold.
