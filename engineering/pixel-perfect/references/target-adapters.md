# Target adapter reference

## Adapter boundary

The pixel-perfect scripts compare raster files. The target adapter is the
project-specific way to create those files. It may be a browser, mobile simulator, desktop app, canvas/game scene,
document renderer, or another renderer, but it must expose a repeatable command
or procedure with a clear output path. The schema below is target-neutral; the
values show one web example.

```yaml
name: web-dashboard
prepare:
  command: <project-local setup>
render:
  command: <project-local deterministic raster-capture command>
  output: <absolute or workspace-owned PNG>
conditions:
  viewport: [1536, 1024]
  dpr: 1
  zoom: 1
  fonts_ready: true
  data: fixture/dashboard.json
  theme: dark
  scroll: [0, 0]
side_effects: <what the adapter changes>
```

The skill does not guess a target command. Inspect project scripts,
documentation, existing test tooling, and runtime availability first. Run the
mechanical preflight before implementation. For a web target, this can be:

```bash
pixel-perfect preflight --task-name TASK --reference REF \
  --viewport 1536x1024 --dpr 1 \
  --require-executable node --font-path assets/Inter-SemiBold.woff2
```

`preflight` reports facts and hypotheses; the agent decides whether the
combination is sufficient.

## Deterministic render checklist

Before capture, stabilize:

- viewport/window/surface dimensions and scale/DPR;
- browser/engine, simulator, desktop, or document-renderer version;
- zoom, display scale, camera/scene/page position, and focused input;
- font loading and other local material/resource files;
- content/data/locale/timezone and deterministic seeds;
- network responses and feature flags;
- theme/color mode;
- animation/transition/caret/particle state;
- timestamps/random values; and
- screenshot encoding and output dimensions.

If a command uses a real browser, prefer the skill-owned `browser` adapter or
an existing project renderer rather than inventing a one-off Chrome command.
If a raw browser command is unavoidable, preserve its exact command, version,
log, and fresh output path in the run record, and report controls it could not
prove. A zero exit code is not a semantic or readiness check. If the target
cannot be launched or captured, stop at `BLOCKED`.

For a CSS viewport with device scale factor `dpr`, validate the raster against
`round(viewport width * dpr)` × `round(viewport height * dpr)` when the backend
renders device pixels; do not compare it to CSS dimensions by assumption.
Record both coordinate spaces so a clean integer relationship is not mistaken
for proof of the original reference setup.

When a user/project-specified stylesheet, font, remote asset, or data request
is loaded from a network source, treat network readiness as part of the
adapter contract. Prefer pinned/local resources for strict matching, or wait
for the target-specific readiness condition and record any limitation.

## Output validation

An adapter result is valid only when:

1. the command returned successfully;
2. the declared output is a new/readable regular image;
3. the image dimensions match the requested render condition;
4. the file is not empty or a stale prior capture; and
5. the current target state is the one intended for the reference.

A successful command with an absent, stale, or wrong-size image is not a
render proof. Keep adapter diagnostics outside the JSON metric report or bound
them before reporting.

## Behavior verification

Visual comparison does not verify behavior. Add target-specific checks for
in-scope requirements, such as:

- navigation/CTA or target-specific input interaction;
- keyboard focus, pointer input, controller input, or form entry;
- responsive layout or scene/camera changes at intermediate conditions;
- loading/error/empty/resource states; or
- accessibility tree/labels/roles when the target exposes them.

Keep these checks separate from image similarity and report their status. A
visual correction that breaks a required behavior must not be kept merely
because its score increased.

## Multi-reference adapters

A multi-reference adapter takes a contract record as input rather than
hard-coding one screenshot. The same implementation is rendered independently
for each render condition/state. Persist the conditions with each output so
later comparison cannot accidentally pair the wrong image and state.

## Dependency boundary

The standard `render_browser.py` adapter accepts a URL/local file, viewport,
DPR, wait milliseconds, optional selector/font readiness, animation disabling,
scroll, theme, and full-page capture. It prefers Playwright when the package
and browser are already available in `<cwd>/.venv`; otherwise it uses native
Chrome/Chromium and marks unsupported requested controls as `partial`.

The pixel-perfect runtime installs only its own `Pillow>=10` dependency into
`<cwd>/.venv`. Browser engines, mobile SDKs, desktop applications, project
packages, and fonts are target prerequisites. Install those only through the
project's authorized setup, never globally as a hidden side effect of this
skill.
