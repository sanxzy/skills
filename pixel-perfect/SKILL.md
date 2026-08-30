---
name: pixel-perfect
version: 1.0.0
description: |
  Reproduce a UI reference image in an existing project with framework-agnostic,
  screenshot-driven iteration. Uses bundled Python scripts for deterministic
  browser rendering, Pillow/NumPy image analysis, text-readable diagnostics,
  and bounded visual verification. Works for agents with or without vision.
---

# Pixel-perfect

Use this skill when a user asks to implement, reproduce, or closely match a UI from a screenshot or other raster reference. The skill is framework-agnostic: preserve the project's existing framework and architecture, whether the target is static HTML, React, Vue, Svelte, Angular, a desktop web shell, or another browser-rendered project.

The skill captures the useful behavior from a high-fidelity implementation session without copying its accidental weaknesses:

```text
inspect -> establish baseline -> render -> measure -> diagnose one cause
       -> make one focused edit -> render again -> compare -> verify
```

The host agent performs the implementation directly in the current checkout. The bundled CLI performs repeatable mechanics; it never edits source code or invents a replacement architecture. The agent is responsible for deciding the next smallest source edit from the evidence.

## Non-negotiable behavior

1. **Inspect before editing.** Read project instructions, identify the project root, inspect the reference dimensions, detect the framework and existing commands, and find the real render entrypoint. Do not guess a missing path.
2. **Use the reference viewport.** Derive the primary viewport from the reference image unless the user explicitly supplies another one. Render at device scale factor 1.
3. **Use measurable evidence.** Every visual iteration must produce a machine-readable comparison report. A model without vision must be able to continue from JSON/Markdown output alone.
4. **Edit one cause at a time.** Do not batch unrelated CSS, markup, or asset changes. A focused edit may update the declarations and markup required for one diagnosed cause, but it must have one stated hypothesis.
5. **Render after every focused edit.** Never infer that an edit worked from source inspection. Compare the new screenshot and check for regressions in already-correct regions.
6. **Preserve behavior and architecture.** Reuse the project's framework, dependencies, build command, routing, and assets when they exist. Do not replace a working application with a static mock merely to improve one screenshot.
7. **Keep the loop bounded.** Use a configured iteration cap and stop after a metric plateau. Report remaining mismatch honestly; never claim pixel identity from an unverified visual impression.
8. **Verify behavior separately.** Visual similarity does not prove that navigation, controls, keyboard access, or application behavior still works.

## Reference-image use rule

This is a hard anti-bypass rule: do not bypass the bundled analysis and comparison scripts by displaying the reference/design screenshot in the implementation. Never use the reference/design screenshot itself as runtime UI content. Do not install it as a CSS `background`/`background-image`, `<img>`/`<picture>`, `mask-image`, canvas or texture, CSS `content`, data URI, imported asset, overlay, or any equivalent screenshot-based shortcut. Do not crop or slice the screenshot into implementation assets, and do not make the rendered project depend on the reference file or artifact path. The reference image is an analysis and comparison input only; recreate the interface from measured evidence, using existing project assets or separately authored individual assets when required.

## Environment and bundled scripts

All operational scripts live inside this skill. Agents must not create one-off PIL, NumPy, OCR, or pixel-probing scripts during an invocation.

The public entrypoint is:

```bash
python <skill-root>/scripts/pixel-perfect.py <subcommand> ...
```

The CLI automatically creates or repairs the workspace-local runtime when a command needs it. `<cwd>` means the directory from which the CLI is invoked; `--project-root` may point to a checkout inside or outside that workspace:

```text
<cwd>/.xzy-env/pixel-perfect/
```

The runtime installs Pillow and NumPy. Pillow is required for image I/O; NumPy is used for fast array metrics and is installed automatically. The analysis code has a standard-Python fallback if NumPy installation is unavailable, and the report states which engine ran. No pandas dependency is used. If no system Chrome/Chromium is available, the render path installs and uses Playwright Chromium in the same environment.

Do not install packages globally. Do not add the runtime, generated screenshots, or reports to the implementation commit. Generated artifacts are stored in `<cwd>/.artifacts/pixel-perfect/<page_name>/`. Pass `--page-name PAGE_NAME` to select the page directory; when omitted, the CLI uses the reference filename stem, or `default` when no reference exists. Every generated file, including the candidate screenshot, is kept under that page directory; manually supplied output paths are normalized there as well.

### Public CLI

| Command | Purpose |
| --- | --- |
| `setup` | Create the local environment and optionally install a browser adapter. |
| `inspect` | Emit reference-image facts and read-only project reconnaissance. |
| `decompose` | Create a structured, text-readable section plan before source edits. |
| `render` | Capture one viewport-sized screenshot using system Chrome/Chromium or Playwright. |
| `compare` | Produce metrics, mismatch diagnosis, overlay, diff, mask, JSON, and Markdown. |
| `verify` | Render when necessary, compare, smoke-check, run optional responsive checks, and return an acceptance exit code. |

Common options:

- `--project-root PATH` — target source checkout; defaults to the current directory. It does not control runtime or artifact placement.
- `--page-name PAGE_NAME` — logical page name used by the default artifact directory `.artifacts/pixel-perfect/<page_name>/`; defaults to the reference filename stem, or `default` without a reference.
- `--no-auto-setup` — use an already prepared workspace runtime and fail clearly if it is missing.
- `--reference PATH` — raster reference image, resolved relative to `<cwd>` unless absolute.
- `--candidate PATH`, `--sections-file PATH`, and `--previous-report PATH` — input/report paths resolved relative to `<cwd>` unless absolute; an external candidate is copied into the page artifact directory before comparison.
- `--output`, `--output-dir`, and `--report` — generated paths are normalized under `.artifacts/pixel-perfect/<page_name>/`; simple relative values are page-relative, and paths outside the page directory are re-rooted by filename/directory name.
- `--entry PATH` — local render entrypoint resolved relative to `--project-root` unless absolute.
- `--viewport WIDTHxHEIGHT` — explicit viewport; otherwise `render` and `verify` derive it from the reference.
- `--url URL` — running HTTP(S) URL, `file:` URL, data URL, or existing local file path.
- `--entry PATH` — local entrypoint relative to the project root.
- `--browser PATH|playwright` — select a browser explicitly.
- `--region name=x,y,width,height` — compare a named layout region (repeatable).
- `--point x,y` — include an exact pixel probe in the text report (repeatable).

Exit codes are stable: `0` means the command passed, `1` means comparison/verification did not meet its thresholds, and `2` means configuration, environment, browser, or input failure.

### File-first CLI output

The CLI writes detailed JSON/Markdown/image evidence to the page-scoped artifact paths and prints only one compact JSON pointer on stdout. The pointer contains the status, operation, lightweight context, and file descriptors; it does not inline comparison metrics, runtime records, decomposition data, `page_name`, or `output_dir`. Read the returned paths only when deeper evidence is needed. On command failure, stderr contains a short error summary and a descriptor for the persisted error JSON when the artifact directory is writable.

Defaults that make this contract consistent:

- `inspect` writes `.artifacts/pixel-perfect/<page_name>/inspection.json` when `--output` is omitted.
- `render` writes `.artifacts/pixel-perfect/<page_name>/candidate.png` and a JSON render report next to it when `--output` and `--report` are omitted.
- `decompose`, `compare`, and `verify` keep their detailed reports under `.artifacts/pixel-perfect/<page_name>/`; optional output directories are page-scoped as well.

Each returned file uses an object with `output_path` and `description`. The pointer omits `page_name` and `output_dir`; the page scope is visible in every returned file path:

```json
{
  "reports": {
    "markdown": {
      "output_path": "/workspace/.artifacts/pixel-perfect/dashboard/comparison.md",
      "description": "Concise comparison summary; read before comparison.json."
    }
  },
  "artifacts": {
    "diff": {
      "output_path": "/workspace/.artifacts/pixel-perfect/dashboard/diff.png",
      "description": "Enhanced visualization of pixel-level differences."
    }
  },
  "candidate": {
    "output_path": "/workspace/.artifacts/pixel-perfect/dashboard/candidate.png",
    "description": "Candidate screenshot used for the comparison."
  }
}
```

### Recommended command sequence

From the project root, after resolving a reference image:

```bash
python /path/to/pixel-perfect/scripts/pixel-perfect.py inspect \
  --project-root . \
  --page-name dashboard \
  --reference path/to/reference.png

python /path/to/pixel-perfect/scripts/pixel-perfect.py decompose \
  --project-root . \
  --page-name dashboard \
  --reference path/to/reference.png \
  --section shell=0,0,1536,1024 \
  --section sidebar=0,44,252,934 \
  --section main=252,44,873,934 \
  --section inspector=1125,44,411,934

python /path/to/pixel-perfect/scripts/pixel-perfect.py render \
  --project-root . \
  --page-name dashboard \
  --reference path/to/reference.png \
  --url http://localhost:3000 \
  --output .artifacts/pixel-perfect/dashboard/candidate-00.png

python /path/to/pixel-perfect/scripts/pixel-perfect.py compare \
  --project-root . \
  --page-name dashboard \
  --reference path/to/reference.png \
  --candidate .artifacts/pixel-perfect/dashboard/candidate-00.png \
  --region sidebar=0,44,252,934 \
  --region main=252,44,873,934 \
  --region inspector=1125,44,411,934
```

For a static local entrypoint, omit `--url` and pass `--entry index.html` (or let the CLI discover `index.html` under `--project-root`). For a framework application, use the project's normal dev server and pass its URL; do not make the CLI guess a port. A local file supplied through `--url` is resolved relative to `<cwd>` unless absolute.

For final acceptance:

```bash
python /path/to/pixel-perfect/scripts/pixel-perfect.py verify \
  --project-root . \
  --page-name dashboard \
  --reference path/to/reference.png \
  --url http://localhost:3000 \
  --responsive-viewport 390x844 \
  --max-mae 10 \
  --min-within-tolerance 0.85
```

The command writes `comparison.json`, `comparison.md`, `verification.json`, `verification.md`, `candidate.png` when it rendered the candidate, `overlay.png`, `diff.png`, `threshold-mask.png`, and any responsive smoke screenshots. For comparison output, read `comparison.md` first because it is the concise diagnostic summary; open the usually much larger `comparison.json` only when exact metrics, probes, regions, scanlines, or tile details are needed. For verification output, read `verification.md` first and open `verification.json` only for deeper evidence. Do not rely on the generated image being visible to the model.

### Rich section definitions

Use `decompose --sections-file sections.json` when a section needs more than a bounding box. The file may be a JSON array or an object with a `sections` array:

```json
{
  "sections": [
    {
      "id": "sidebar",
      "bounds": [0, 44, 252, 934],
      "visual_contract": ["Dark navigation panel with compact project and session groups"],
      "content_state": "default",
      "layout_owner": "src/layout/Sidebar.tsx",
      "dependencies": ["global-frame"],
      "implementation_order": 2,
      "verification_region": [0, 44, 252, 934],
      "responsive_behavior": "Collapse below 768px.",
      "acceptance_criteria": ["Navigation remains keyboard reachable."]
    }
  ]
}
```

A section supplied only through `--section id=x,y,width,height` is deliberately marked `draft` because its semantic contract is still missing. Complete the JSON plan before treating that section as implementation-ready.

## Workflow

### 1. Resolve scope and project state

- Treat the user-provided reference as the visual contract and preserve its established terminology.
- Read the repository's instruction files and any project-local README or architecture guidance.
- Resolve the target checkout from the project's documented root mechanism when one exists. If the root, target file, route, or reference is ambiguous in a way that changes implementation, ask one focused question before editing.
- If the target directory is absent, do not create it silently. Ask for permission; after permission, create the smallest valid project foundation and record that decision.
- Check existing working-tree changes. Never overwrite unrelated user work; distinguish baseline changes from this task's changes.

### 2. Inspect the environment and reference

Run `inspect` before implementation. It reports:

- exact image width, height, mode, and derived primary viewport;
- corner colors and dominant quantized colors;
- strongest horizontal and vertical edge positions;
- the available analysis engine;
- project manifests, likely framework, package manager, scripts, candidate entrypoints, and a bounded file list.

Also inspect available renderers. The CLI prefers an installed Chrome/Chromium executable because it is close to the browser screenshot workflow used by the source session. It uses Playwright Chromium only when required or explicitly selected. If an optional tool is missing, use the CLI's setup path rather than writing an ad-hoc replacement.

### 3. Decompose the visual contract

Before writing the first implementation, run `decompose` and create a section plan. If no section definitions are available yet, accept its `draft` output as a scaffold and complete it before editing source. Do not treat automatically suggested edge positions as semantic labels.

Every named section must have this contract:

```text
id
bounds: x, y, width, height
visual_contract
content_state
layout_owner
dependencies
implementation_order
verification_region
responsive_behavior
acceptance_criteria
```

Use sections that match implementation seams and meaningful visual regions. A practical dependency order is:

1. global frame and persistent chrome;
2. primary columns and panel boundaries;
3. internal cards, toolbars, lists, and forms;
4. repeated rows, icons, badges, and controls;
5. typography, assets, colors, borders, and effects;
6. active/loading/empty/error/focus states and interactions;
7. responsive mapping and smoke checks.

Before the baseline, make the plan `ready`: each section has an owner, visible state, verification region, responsive behavior, and acceptance criteria. Dependencies may be empty for a root section but must be explicit. Keep sections small enough that one focused edit can target one section or one dependency edge; do not split the page into arbitrary score-optimizing slices.

### Sectioning cases

Use these rules when deciding whether something is a new section, a state, or a child element:

- **Persistent frame:** header, footer, sidebar shell, global background, and overflow belong to `global-frame` or `primary-regions`.
- **Spatial region:** a visually bounded column, panel, card group, or large empty area gets its own section when it has an independent layout owner or verification region.
- **Repeated structure:** rows, cards, nav items, icons, and badges are children of their owning section; describe the repeated pattern once and list important variants in `content_state`.
- **Visible state:** active, selected, loading, empty, error, focused, expanded, and disabled states are state contracts, not arbitrary extra rectangles. Add a separate section only when the state changes a separate implementation seam or overlay.
- **Overlay/portal:** dialogs, menus, tooltips, drawers, and floating controls get an explicit section because they can affect z-index, viewport bounds, and interaction verification.
- **Dynamic content:** freeze the data/state needed for the reference and record the fixture or route in `content_state`; do not tune layout against a moving response.
- **Scrollable content:** record the scroll position and viewport clipping in the section contract. Do not compare an unscrolled page with a scrolled reference.
- **Responsive behavior:** keep the semantic section identity across breakpoints and describe reflow, collapse, hide/show, or overflow in `responsive_behavior`.
- **Typography/assets:** keep them under the owning visual section unless a shared font/icon asset affects the entire frame; then make the dependency explicit.

The section plan becomes the text-only implementation map. For each section, record:

- its bounds, alignment anchors, and relationship to the global viewport;
- its hierarchy: panels, cards, rows, controls, and repeated structures;
- typography hierarchy, line-height, text density, and likely font sources;
- colors, gradients, borders, radii, shadows, icons, and assets;
- visible content and state: default, active, loading, empty, error, or focused;
- interaction rules, source owner, dependencies, and responsive exceptions;
- the exact verification region and acceptance evidence that will mark it accepted.

Prefer the section plan's `verification_region` values for comparison. Regions should correspond to meaningful layout sections, not arbitrary slices chosen only to make the score look better. Keep a short hypothesis log in the task progress tracker, for example: `main panel begins 4px too low because the toolbar line box is taller than the reference`.

### 4. Establish a coarse but complete baseline

Implement sections in the plan's dependency order. Finish a coarse vertical slice of the global frame and primary regions before polishing internal components. Mark a section accepted only after its focused comparison passes and the previously accepted sections show no unacceptable regression.

Implement the smallest complete vertical slice that can render the whole target state. Use existing project conventions and assets. Do not spend the first pass on one icon while the page frame is absent.

- Preserve semantic structure and existing behavior where possible.
- Use real project fonts/assets when available; do not silently substitute a dependency that changes the project architecture.
- Use CSS layout primitives appropriate to the project. Absolute positioning is acceptable for a fixed mockup only when the contract is explicitly fixed; it is not a default for framework applications.
- Keep the first pass observable: it must load at the target route and produce a screenshot.

Render the baseline immediately. Record its metrics before making refinements; this provides evidence that later edits improve the result rather than merely changing it.

### 5. Iterate with a diagnosis-first loop

For each iteration, follow this exact order:

1. Record the iteration number and current hypothesis.
2. Render the current target at the primary viewport.
3. Run `compare` with the active section's `verification_region`, all previously accepted section regions, and the configured pixel tolerance.
4. Read the text report and identify the highest-impact *single* mismatch class:
   - dimension/viewport mismatch;
   - global frame or panel boundary;
   - component position or size;
   - spacing or line-box alignment;
   - typography/font weight/line height;
   - color, border, gradient, or shadow;
   - content or state;
   - interaction/runtime error.
5. Use the mismatch bounding box, row/column density, tile hotspots, edge peaks, per-channel error, and region metrics to localize the cause. Do not make a CSS change without a stated cause.
6. Make one focused source edit.
7. Rerender and compare immediately.
8. Keep the edit only if the active section improves without an unacceptable regression in previously accepted sections; otherwise revert or correct the same hypothesis before moving on.
9. Update the section status and append the result to the progress log: change, evidence before/after, and next hypothesis.

The comparison tools intentionally expose both a global score and local evidence. A lower global error can hide a broken header or text block, so inspect regional and hotspot results before accepting an iteration.

Useful diagnosis patterns:

- A continuous vertical edge mismatch usually indicates a column boundary, width, or scrollbar issue.
- A continuous horizontal edge mismatch usually indicates a row height, margin, or line-box issue.
- A narrow mismatch around glyphs with otherwise correct boxes usually indicates font, weight, anti-aliasing, or text color.
- A broad low-amplitude mismatch across a panel usually indicates background, gradient, opacity, or color-scheme error.
- A compact high-error tile usually indicates one component, icon, or content-state mismatch.

If a comparison script fails, fix the cause instead of hiding the error. The CLI already handles missing NumPy, missing browser adapters, unreadable images, and dimension mismatches with explicit diagnostics.

### 6. Use bounded stopping rules

Set a task-appropriate `MAX_ITERATIONS`; use 20 when the user has not supplied a limit. Stop refinement when all of the following are true:

- reference and candidate dimensions match exactly;
- the primary comparison meets configured `max-mae`, `min-within-tolerance`, and hottest-tile thresholds;
- named important regions meet their own visual expectations;
- no large unresolved mismatch cluster remains in a high-priority region;
- the last three accepted iterations do not show a meaningful improvement, or the acceptance thresholds have passed;
- any responsive smoke viewport renders a non-flat page without captured browser/page errors;
- required project verification and interaction checks pass.

If the iteration cap or plateau is reached first, stop and report the remaining mismatch bbox, hottest regions, metrics, and likely next hypothesis. Never loop indefinitely and never describe a threshold pass as exact pixel identity unless `exact_fraction` is actually 1.0 under the chosen renderer.

### 7. Verify behavior and finalize

After visual acceptance:

1. Run `verify` and preserve its JSON/Markdown reports.
2. Run the project's normal build, lint, typecheck, and test commands when available.
3. Exercise visible interactions that the reference implies: tabs, navigation, search/filtering, toggles, buttons, and keyboard focus as applicable. Use the highest practical seam; do not replace behavior tests with screenshot equality.
4. Check responsive smoke sizes when the project is expected to be responsive.
5. Inspect the final diff. Remove debugging probes, temporary source markup, accidental dependencies, and generated files from the implementation change.
6. Keep `<cwd>/.xzy-env/pixel-perfect/` and `<cwd>/.artifacts/pixel-perfect/` out of the source commit unless the user explicitly requests them.
7. Report exactly what passed, what remains, the renderer and analysis engine used, the final thresholds, and any environment limitations.

## Framework guidance

The CLI does not assume a framework. The agent should:

- identify the framework and existing package scripts from `inspect`;
- use the project's normal start/build command and an explicit URL for browser rendering;
- preserve routing and state rather than replacing the app with a screenshot-shaped shell;
- keep visual changes localized to the owning module/style layer;
- use project tests and browser interaction checks in addition to image metrics.

For a static HTML target, a self-contained file may be the simplest correct implementation. For a framework target, reuse installed dependencies and existing component/style conventions before adding anything. The reference image is evidence about appearance, not permission to remove application behavior.

## No-vision contract

A model without image vision must still be able to complete the workflow. It must read:

1. `inspection.json` for reference dimensions, colors, and edge peaks;
2. `decomposition.json` or `decomposition.md` for the section map, order, owners, states, dependencies, and acceptance criteria;
3. `comparison.md` first for the concise overall and regional summary; open `comparison.json` only when detailed metrics or evidence are needed;
4. mismatch bbox, top rows/columns, scanlines, point probes, and tile hotspots from the comparison report for localization;
5. the current source and browser/project inspection output for mapping coordinates to selectors or modules;
6. the progress log for the previous hypothesis and regression result.

The model must not claim to have visually inspected an image it cannot see. If text-only evidence cannot distinguish two plausible causes, state the uncertainty and use an additional targeted probe or ask the user for the missing visual decision.

## Failure handling

- Missing or malformed project root: stop and ask; do not guess.
- Missing reference or candidate image: stop with the CLI error and correct the path.
- Dimension mismatch: treat it as a structural failure, not as a reason to resize silently.
- Browser failure: inspect the command and environment; use the supported adapter or fix the project server. Do not add arbitrary sleeps or retries.
- NumPy installation failure: retain the explicit Python fallback only when the report records it; do not pretend the fast analysis ran.
- Verification failure: identify the smallest root cause, make up to three focused self-fixes, rerun the relevant check, and ask the user how to proceed if it still fails.
- User feedback such as “refine incrementally” changes the iteration contract immediately: stop batching and continue with one hypothesis/edit/render cycle.
