---
name: pixel-perfect
version: 1.0.0
description: |
  Reproduce a reference image as a real, runnable visual target through deterministic
  raster capture, Pillow comparison, adaptive-grid localization, focused correction,
  and auditable full-composition verification.
argument-hint: "Provide reference image(s), target project/runtime, viewport/state, and acceptance threshold when known."
---

# Pixel-perfect

Use this skill when an agent must reproduce one or more reference images as a
real implementation: HTML/CSS, React/Vue/other web UI, Flutter, React Native,
SwiftUI, Android, desktop, canvas, game UI, document renderer, or another
target that can produce a deterministic raster capture.

The public abstraction is **reproduce the visual state in a runnable target**,
not **make a picture that looks similar**. The agent owns visual reasoning and
implementation decisions. The skill-owned scripts perform bounded, repeatable
image mechanics:

```text
INSPECT → DECOMPOSE → IMPLEMENT → RENDER → COMPARE → CORRECT → VERIFY
```

Do not claim pixel-perfect completion from subjective inspection, one global
score, a local crop, or a successful renderer exit. A final claim needs a fresh
full-composition render, measured evidence, critical-region checks, and
behavior verification for the requested scope.

### Target-neutral core

The workflow is target-neutral: it applies to web pages, native/mobile or
desktop applications, simulator/device surfaces, canvas/game scenes,
documents, and any other runnable target that can produce a deterministic
raster. Browser and CSS-viewport examples below are conditional web-target
guidance—not requirements. Any framework, library, or external resource named
by the user or project is a task input, never a skill default. For another
target, define its equivalent render contract (for example window/surface size, device scale,
camera/scene state, asset readiness, animation state, and input state) and use
a project-specific adapter that emits the reference-comparable image.

## Responsibility boundary: agent versus scripts

The **agent owns meaning and source changes**: inspect the reference and
codebase, choose target/state/render conditions, decompose semantic sections,
map critical regions, implement the native target, interpret evidence, diagnose
causes, edit/rollback code, verify in-scope behavior/accessibility, and decide
`MATCHED | PARTIAL | BLOCKED`.

The **scripts own deterministic mechanics**: provision the skill venv, inspect
raster/tool facts, render through an optional browser adapter, normalize image
representations, calculate metrics, localize error with a grid, materialize
diff/heatmap evidence, recommend retain/hold/rollback from supplied reports,
and aggregate explicit acceptance gates. They never edit target source, infer
hidden behavior, decide which component owns a hotspot, or turn a score into
semantic acceptance.

Read [`references/agent-vs-script.md`](references/agent-vs-script.md) before
orchestrating a task. It defines every stage's input/output boundary and the
claims each side is forbidden to make.

## Trigger boundary and inputs

Accept:

- one or more reference raster images;
- a safe historical `task_name` for the artifact namespace;
- the target codebase and target runtime/framework;
- viewport/device dimensions, scale/DPR, theme, data, and state when known;
- project constraints, existing components, fonts, icons, and allowed assets;
- an explicit acceptance threshold, or a justified `EXACT`, `HIGH`, or
  task-specific `CUSTOM` threshold; and
- behavior requirements visible in the reference or explicitly supplied by the
  user.

Inspect the target project before changing it. If a material visual condition
is unknown, state an assumption or ask for clarification. A static reference
does not establish hidden behavior, responsive rules at unshown sizes, or
interaction states that are not visible.

The reference is evidence, never an implementation asset. Never put it in the
final target as a background, overlay, texture, hidden image, or single bitmap
standing in for native content or controls.

## Runtime and automatic dependency setup

The normal public entrypoint is the skill-owned dispatcher. Resolve the skill
directory before invoking it; do not guess a path from the target project:

```bash
<skill-directory>/scripts/pixel-perfect normalize \
  --task-name dashboard \
  --reference <reference.png> \
  --render <render.png>
```

Every dispatcher operation first prepares the skill runtime under exactly:

```text
<cwd>/.venv/
```

Here `<cwd>` is the current working directory from which the skill is invoked,
normally the target project root. It is not the skill checkout. The runtime
installer is `scripts/runtime.py` and its only declared skill dependency is:

| Dependency | Purpose |
| --- | --- |
| `Pillow>=10` | image decoding, normalization, comparison, diff, heatmap, and grid metrics |

On first use, the skill creates the missing environment with the host's
explicit Python interpreter, prepares pip inside that environment, and
installs the dependency using the venv's interpreter. Package cache and
installer temporary files stay under `<cwd>/.venv/.cache/pip` and
`<cwd>/.venv/.tmp`; no global Python package or global cache is required.

If `<cwd>/.venv` already exists, reuse it in place. The bootstrap verifies
`pyvenv.cfg`, isolated site-packages, the venv interpreter, and pip; it runs
`ensurepip` in that venv only when pip is missing, then installs/upgrades only
the declared `Pillow>=10` requirement when necessary. It never clears,
deletes, recreates, or upgrades unrelated packages in an existing venv. A
path that exists but is not a valid isolated venv, or a venv that fails its
identity probe, is reported as `runtime_unusable` and left untouched rather
than repaired destructively. Run `pixel-perfect runtime --cwd <cwd>` to inspect
readiness.

Direct calls to `preflight.py`, `render_browser.py`, `quick.py`,
`normalize_images.py`, `compare_images.py`, `generate_diff.py`,
`analyze_grid.py`, `iteration.py`, or `verify_acceptance.py` also enter this
same venv boundary
before doing work. Prefer the dispatcher because it keeps the invocation
contract uniform. Target-project dependencies such as a browser, framework,
Flutter SDK, fonts, or device simulator remain project/runtime prerequisites;
this skill does not guess or globally install them.

## Artifact namespace and historical traceability

Every image-processing command requires a `--task-name` and writes to the
append-only namespace:

```text
<cwd>/.artifacts/pixel-perfect/<task_name>/
├── 001-normalize/
│   ├── 001-reference.png
│   ├── 002-render.png
│   └── 003-manifest.json
├── 002-compare/001-compare.json
├── 003-grid/001-grid.json
└── 004-diff/
    ├── 001-diff.png
    ├── 002-heatmap.png
    └── 003-manifest.json
```

Other operations use the same global stage sequence, for example
`001-preflight/001-preflight.json`, `001-browser/001-browser.png`,
`001-quick/...`, `001-iteration/001-iteration.json`, or
`001-acceptance/001-acceptance.json` when they are the first operation for a
new task.

Stage numbers are monotonically allocated across all operations for a task,
so repeated renders/comparisons become an auditable history rather than
replacing earlier evidence. Final image and report names also have numeric
prefixes. The default output location is always below this namespace; an
explicit `--output-dir`/`--output` is accepted only when it is a new,
numeric-prefixed path below the same task directory. The scripts never choose
`/tmp` or `/private` as an artifact destination. Atomic write scratch files
are created beside their final artifact, not in the OS temporary directory.

## Multi-script interface

The dispatcher forwards arguments without shell evaluation:

```text
pixel-perfect quick      --task-name NAME --reference REF --render PNG [--with-grid]
pixel-perfect preflight  --task-name NAME --reference REF [preflight options]
pixel-perfect browser    --task-name NAME --target URL_OR_FILE [browser options]
pixel-perfect normalize  --task-name NAME --reference REF --render PNG [--output-dir DIR]
pixel-perfect compare    --task-name NAME --reference REF --render PNG [comparison options]
pixel-perfect diff       --task-name NAME --reference REF --render PNG [--output-dir DIR] [diff options]
pixel-perfect grid       --task-name NAME --reference REF --render PNG [grid options]
pixel-perfect iteration  --task-name NAME --current COMPARE.json [--baseline COMPARE.json]
pixel-perfect accept     --task-name NAME --compare COMPARE.json [acceptance options]
pixel-perfect runtime    [--cwd CWD]
```

Script responsibilities are intentionally narrow:

| Script | Responsibility |
| --- | --- |
| `scripts/runtime.py` | create/reuse/verify `<cwd>/.venv`, install only declared skill dependencies, and run one skill script in that interpreter |
| `scripts/preflight.py` | report raster dimensions/alpha, capability/tool/font/asset certainty, and render-condition hypotheses without interpreting target semantics |
| `scripts/render_browser.py` | mechanically capture a URL/local file with Playwright or native Chrome/Chromium when available; report unsupported controls explicitly |
| `scripts/quick.py` | run the fast normalize → compare → diff chain, optionally adding grid; it never edits or renders target code |
| `scripts/normalize_images.py` | decode two references, apply EXIF orientation, composite alpha over an explicit backdrop, produce clean RGB PNGs, and persist a manifest |
| `scripts/compare_images.py` | calculate exact/tolerant/color-aware/edge/region-weighted metrics, masks, critical-region results, and optional JSON evidence |
| `scripts/generate_diff.py` | materialize amplified numeric-prefixed diff/heatmap images plus a metrics manifest |
| `scripts/analyze_grid.py` | calculate a coarse grid and best-first adaptive subdivisions in full-image coordinates |
| `scripts/iteration.py` | compare supplied baseline/current evidence and recommend retain, hold, or rollback; it never changes source/Git |
| `scripts/verify_acceptance.py` | evaluate explicit comparison, dimensions, critical-region, section, certainty, behavior, target, grid, and regression gates |
| `scripts/_common.py` | shared validation, artifact history allocation, atomic writes, Pillow primitives, and stable report mechanics; it is not a second public entrypoint |

Use the scripts rather than rewriting comparison algorithms in the calling
agent. All commands return one JSON object on stdout for normal operation or a
structured JSON error with a non-zero exit code. A `complete` script result
means the mechanic ran and its artifacts were read back; it does not mean the
visual acceptance threshold passed.

### Comparison options

`compare` supports:

- `--mode exact` — any non-identical pixel is changed; requires tolerance `0`;
- `--mode tolerant` — changed pixels exceed `--tolerance` per channel;
- `--mode color-aware` — uses luminance-weighted color difference for the
  primary similarity score;
- `--mode edge` — uses Pillow edge maps for the primary structure score while
  retaining color metrics; and
- `--mode region-weighted --regions regions.json` — aggregates named region
  scores by explicit weights.

All modes also report raw/tolerated changed pixels, percentage, mean and
weighted color difference, bounding box, edge similarity, dimensions, and
considered/ignored pixel counts. Dimensions must match; normalization never
silently resizes. Use `--background #RRGGBB` consistently for transparent
inputs. Add `--structure-background #RRGGBB` when the canvas color is known to
receive coarse non-background content bounds and a bbox displacement signal;
this is a geometry hint, not a semantic element measurement.

For locked renderer/font conditions, prefer `exact`; use `tolerant` only for
small, stable anti-aliasing/encoding differences. Tolerance changes the
changed-pixel gate but raw color metrics remain visible. It must never conceal
text wrapping, alignment, size, overflow, or other structural differences.

A regions file is either a JSON list or `{ "regions": [...] }`:

```json
[
  {"name": "primary-cta", "bbox": [80, 120, 240, 56],
   "weight": 3, "critical": true, "threshold": 0.97}
]
```

`bbox` is `[x, y, width, height]` in normalized full-image pixels. Regions
must be inside the image, names must be unique, and weights/thresholds are
validated. A threshold produces `passed`; a critical region without a
threshold remains explicit rather than being guessed.

An ignore mask is opt-in and must include `--mask-reason`. Non-black mask
pixels are excluded; the reason is written into every report. Do not use a
mask to hide a known mismatch or dynamic area without documenting why it is
allowed by the task.

### Adaptive grid options

`grid` defaults to a `4x4` coarse partition and refines the highest-severity
eligible leaf first. Severity is the greater of tolerated changed-pixel ratio
and mean color difference normalized to `0..1`. Refinement is bounded by:

```text
--refine-threshold 0.05
--min-cell 32
--max-depth 3
--max-leaves 256
```

The report preserves coarse cells, final leaves, refinement paths, stop
reason, and sorted hotspots. Every `bbox` remains relative to the full image;
local crops never reset the coordinate origin.

## State model

Track the current state for each reference/target run:

| State | Meaning |
| --- | --- |
| `INSPECTING` | reference, assets, target project, and render environment are being established |
| `DECOMPOSED` | semantic sections, components, global constraints, and comparison regions are mapped |
| `IMPLEMENTING` | native target implementation is being created or adjusted |
| `RENDERING` | a deterministic screenshot is being produced |
| `COMPARING` | normalized reference and render are being measured |
| `CORRECTING` | one evidence-backed, focused correction is being applied |
| `VERIFYING` | full composition, critical regions, regression, and behavior are checked |
| `MATCHED` | all applicable acceptance gates pass |
| `PARTIAL` | valid implementation/evidence exists but one or more gates remain unmet |
| `BLOCKED` | a required target, renderer, font, asset, input, or evidence capability is unavailable |

Do not skip from `IMPLEMENTING` to `MATCHED`. Record the render conditions,
baseline, iteration, hypothesis, changed scope, local/global result, and
rollback decision for each correction.

## Quick-start loop

For a small, already-understood target, use this short loop. The agent still
owns the first/last semantic decisions; `quick` only compresses repeatable
image mechanics:

```text
agent: inspect reference + target and choose conditions
agent: render the current target state
script: pixel-perfect quick --task-name TASK --reference REF --render RENDER
agent: inspect compare JSON, diff, and (when needed) --with-grid hotspots
agent: form one hypothesis, edit native target code, and rerender
agent: repeat until stable, then run `accept` with all declarations
```

`quick` performs `normalize → compare → diff` and does not inspect code, choose
component ownership, fix source, or verify behavior. Use `--with-grid` only
when the diff needs localization. For a new target, run `preflight` first; for
a web target, use `browser` or the project's more capable renderer adapter.

## Predictability rules, tips, and tricks

Use [`references/predictability.md`](references/predictability.md) for the
full operational checklist. The high-impact rules are:

1. **Resolve one active skill path.** Run the dispatcher from the target
   project root and record the exact `<skill-directory>` used. Do not assume a
   particular installation folder or platform mirror, and do not silently mix
   copies from different skill locations or versions.
2. **Preflight before implementation.** Record observed facts separately from
   render-condition assumptions: coordinate space, viewport/surface/camera,
   scale/DPR, fonts/resources, and renderer. A reference dimension that divides
   cleanly by a scale factor is a hypothesis, not proof of the original setup.
3. **Create the evidence namespace before the first render.** Keep script
   outputs under `.artifacts/pixel-perfect/<task-name>/`, keep agent-owned
   crops/logs/A-B files in a numeric-prefixed `progress/` directory there, and
   never use `/tmp` or unprefixed root files for auditable evidence.
4. **Use returned artifact paths exactly.** Do not guess the next stage or
   compare a path from an earlier iteration. Run artifact-writing commands
   serially; concurrent operations can reuse a numeric prefix for different
   operation names.
5. **Validate every fresh screenshot.** It must follow the latest source edit,
   be a new readable file, have the expected raster dimensions for the target
   coordinate space (`viewport × DPR` where applicable), and represent the
   intended state or scene. A script `status: complete` is mechanical success,
   not visual acceptance.
6. **Make one hypothesis-led edit per iteration.** Keep font, geometry,
   spacing, gradient, and border corrections separable. Use `iteration` against
   the best verified baseline and roll back worse or oscillating revisions.
7. **Prove font/resource readiness.** Resolve candidate resources relative to
   the actual target fixture, wait for renderer readiness (fonts, assets,
   shaders, models, data, or equivalent), and give each A/B render a distinct
   output path. A filesystem match or declaration does not prove the renderer
   used that resource.
8. **Map semantics before grid localization.** Use regions and grid/diff in
   full-image coordinates to localize a cause; never treat a local crop or
   global score as full-composition proof.
9. **Run final evidence after the final edit.** Freshly render, compare, inspect
   required regions, and run `accept` before claiming `MATCHED`; otherwise
   report `PARTIAL` or `BLOCKED` with the unknowns.

For strict matching, treat user/project-specified frameworks, external
styles/resources, remote assets, network data, and target-specific runtime
state as render inputs. Prefer pinned/local resources when permitted, and
document any readiness limitation. Do not introduce a framework or library
because another task used it. Keep Pillow as the default runtime; add heavier
dependencies only after profiling shows a real bottleneck.

## End-to-end orchestration

### 1. Inspect before implementation

Read the reference dimensions/aspect ratio and inspect its actual pixels.
Identify visible facts separately from measurements and assumptions:

- semantic sections and their full-image bounds;
- container width, gutters, alignment axes, vertical rhythm, and layering;
- typography family/weight/size/line-height, wrapping, and baseline;
- colors and semantic surface roles;
- borders, radii, shadows, blur, glow, overflow, and clipping;
- native vs supplied image/icon/logo assets;
- visible interaction/loading/theme state; and
- target project entrypoint, renderer, fonts, data, and dependencies.

If a font or material asset is unavailable, find a project-local equivalent or
report the substitution. Do not hide a material substitution behind a score.

Then run the mechanical preflight before implementation:

```bash
pixel-perfect preflight --task-name TASK --reference REF \
  --viewport 1536x1024 --dpr 1 \
  --font-path path/to/font.woff2 --asset path/to/logo.svg
```

The script reports facts and capability availability. The agent decides
whether the target/browser/font/asset combination is sufficient, asks for
missing material inputs, and records certainty as `exact`, `substitute`,
`recreated`, `missing`, or `unknown`.

### 2. Decompose semantically, then spatially

Create a section map before coding. A section record includes:

```yaml
id: hero
region: [x, y, width, height]
components: [heading, body, primary-cta, illustration]
depends_on: [page-container, font-loading]
comparison_region: [x, y, width, height] # includes effect overlap
threshold: 0.97
weight: 1
critical: false
criteria: [heading wraps into two lines, CTA baseline aligns]
status: pending
```

Use the adaptive grid only to localize error after semantic mapping. Preserve
shared constraints such as container width, background continuation, stacking,
baselines, and flow; a locally perfect crop is not proof of a coherent page.

### 3. Establish deterministic rendering

For web targets, the optional standard adapter is:

```bash
pixel-perfect browser --task-name TASK --target http://localhost:3000 \
  --viewport 1536x1024 --dpr 1 --wait-ms 500 \
  --wait-for-fonts --disable-animations --scroll 0,0
```

It prefers Playwright when installed in `<cwd>/.venv` and otherwise uses a
native Chrome/Chromium headless executable. Read its manifest: a Chrome CLI
fallback marks unsupported wait/font/animation/scroll/theme controls as
`partial`. The agent must still confirm the target state and behavior; a
browser screenshot is not a semantic oracle.

Before each comparison, control as many of these as the target permits:

- viewport/device width and height;
- device-pixel ratio, zoom, and display scale;
- font files and font-loading completion;
- fixed test data, content, locale, and timezone;
- scroll position, theme, color mode, and loading state;
- animation/caret/transition state;
- random values, timestamps, network responses, and feature flags; and
- renderer/runtime version.

If a dynamic area cannot be stabilized, obtain explicit approval for a mask,
record the reason, and keep its exclusion visible in the report. Do not
silently mask it.

### 4. Implement in dependency order

Use native target primitives and the smallest project-compatible change:

1. canvas/background;
2. global container and layout geometry;
3. section geometry and flow;
4. typography and wrapping;
5. component sizing and spacing;
6. color/surface/border/radius/shadow;
7. icons, images, and decorative detail; then
8. in-scope interaction states and behavior.

After a change that can alter global flow, render the full composition—not
only the focused section. Preserve existing behavior and accessibility unless
the task explicitly changes them.

### 5. Run the evidence loop

For each stable iteration:

```bash
pixel-perfect normalize --task-name TASK --reference REF --render RENDER
pixel-perfect compare --task-name TASK --reference NORM/001-reference.png \
  --render NORM/002-render.png --mode color-aware
pixel-perfect grid --task-name TASK --reference NORM/001-reference.png \
  --render NORM/002-render.png
pixel-perfect diff --task-name TASK --reference NORM/001-reference.png \
  --render NORM/002-render.png
```

Read the JSON and actual diff/heatmap artifacts. Select the highest-impact
mismatch, write a concrete hypothesis, change the smallest responsible scope,
and re-render. Keep a baseline; retain a change only if the relevant local
metric improves without a full-composition regression or if it resolves a
previously identified contract issue. If scores oscillate, restore the best
verified revision, record the conflict, and revisit geometry, font metrics,
assets, environment, or shared constraints instead of thrashing properties.

### 6. Verify globally and behaviorally

A section may be `matched` locally only after its comparison region passes. The
run is not complete until every required section and every reference viewport/
state has been checked again in one full composition. Inspect critical regions
independently; a high global score cannot erase a failed logo, heading, CTA,
navigation, form control, focal illustration, or other target-specific focal element.

Use `iteration` after a correction when a baseline exists:

```bash
pixel-perfect iteration --task-name TASK \
  --baseline BASELINE_COMPARE.json --current CURRENT_COMPARE.json
```

The report recommends `retain`, `hold`, or `rollback`; the agent applies the
source/Git action and never delegates that mutation to the script. Finish with
machine-readable gates only after the agent supplies all declarations:

```bash
pixel-perfect accept --task-name TASK \
  --compare CURRENT_COMPARE.json --grid CURRENT_GRID.json \
  --grid-reviewed --sections sections.json \
  --target-status runnable --behavior-status passed \
  --font-status body=exact --asset-status logo=exact
```

`accept` returns `MATCHED`, `PARTIAL`, or `BLOCKED` and a gate object for
comparison, dimensions, critical regions, sections, fonts, assets, target,
behavior, adaptive-grid review, and regression. It evaluates declarations; it
does not prove semantics or replace the agent's final report.

For multiple references, map each image to a render-condition/state contract,
compare each separately, check the intervals or transitions between references
when the target supports them, and re-run regression comparisons after shared
changes. With one reference, implement only the simplest behavior supported by
the project and record which other conditions have no reference contract.

## Acceptance policy

Use [`references/acceptance-policy.md`](references/acceptance-policy.md) and
`verify_acceptance.py` together. The reference explains the human decision;
the script makes the supplied gate state explicit and fail-closed.

Use the following defaults only when the task does not set a custom threshold:

| Level | Global score | Environment |
| --- | ---: | --- |
| `EXACT` | `>= 0.99` | viewport, DPR, fonts, data, and rendering engine are locked |
| `HIGH` | `>= 0.97` | normal comparable target environment |
| `CUSTOM` | task-defined | special target/reference conditions |

The score is necessary, never sufficient. `MATCHED` requires:

- the implementation runs in the requested target;
- render conditions and input references are recorded;
- global threshold passes for every required reference;
- no critical region fails its threshold or remains unknown;
- all required semantic sections have bbox/threshold/weight/critical/status contracts and are verified;
- font and asset certainty is explicit (`exact`, approved non-exact, or an honest limitation);
- adaptive-grid hotspots contain no unexplained critical high-error region;
- no full-composition regression is detected;
- in-scope behavior and accessibility remain functional;
- no prohibited reference-as-target technique is present; and
- material remaining differences are listed honestly.

If the renderer, font, asset, viewport, or behavior cannot be established,
return `BLOCKED` or `PARTIAL`, not `MATCHED`. A low-priority platform
anti-aliasing difference may remain when measured, non-critical, and explained.

## Failure and recovery

- **Target cannot render:** stop and report the missing command/dependency and
  the exact attempted target. Never claim a match without an actual render.
- **Existing `.venv` is malformed:** leave it untouched and return
  `runtime_unusable`; do not delete/recreate a project environment implicitly.
- **Font/asset unavailable:** use a justified project-local substitute or ask
  for the material asset; record the visual consequence.
- **Reference/render dimensions differ:** correct the target's coordinate-space,
  scale/DPR, camera/viewport, or capture setup; do not resize a screenshot to
  conceal a geometry mismatch.
- **Score stalls:** revisit geometry, resource metrics, assets, renderer, and
  assumptions. More random target-property iterations are not recovery.
- **Local change regresses another section:** restore the best revision,
  inspect the full diff/grid, and correct the shared constraint.
- **Comparison script fails:** preserve the structured error and fix the
  named input/runtime condition. Do not convert a missing metric into a pass.
- **Behavior is not visible:** finish only the evidence-backed visual state
  and mark hidden behavior as unverified.

## Guardrails and truth contract

The skill must never:

- use the reference as final target content or a bitmap replacement for native target content;
- silently resize, crop, or mask away a mismatch;
- perform random property tweaking without a hypothesis and comparison;
- accept a local crop as full-composition proof;
- let a global score hide a failed critical region;
- sacrifice function, accessibility, or maintainable structure for pixels;
- infer responsive, interaction, scene, or state behavior that the evidence does not establish;
- report `MATCHED` before the final comparison and behavior gates; or
- hide missing renderer, font, asset, dependency, or evidence limitations.

Report facts in three categories:

- **Observed:** visible pixels, dimensions, files, or metric values produced by
  the current render/comparison.
- **Inferred:** a likely cause or semantic meaning that still needs caution.
- **Unknown:** unavailable render, unreadable asset, unverified behavior, or
  unsupported viewport/state.

## Final report

Use `assets/report-template.md`. The compact result must include:

```text
Status: MATCHED | PARTIAL | BLOCKED
Target: <runtime/framework/device/renderer>
Reference: <image(s), render condition/state, dimensions>
Render conditions: <coordinate space, viewport/window/surface/camera, scale/DPR, resources, theme, state, data>
Global similarity: <score and mode>
Critical-region status: <passed/failed/unknown>
Sections verified: <count/total>
Behavior verification: <summary>
Remaining differences: <explicit list>
Evidence: <normalized render, compare JSON, grid JSON, diff, heatmap>
```

Never omit a material limitation merely because the result is visually close.
