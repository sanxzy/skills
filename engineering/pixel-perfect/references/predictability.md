# Pixel-perfect predictability rules, tips, and tricks

## Purpose

These rules are operational guidance for agents using the skill. They turn the
failure patterns from real reproduction runs into repeatable habits. They apply
to any runnable target that can emit a deterministic raster—not only browser
or UI implementations. They do not replace the acceptance policy, semantic
section contracts, or the agent's judgment about the target visual composition.

## Non-negotiable rules

### 1. Resolve one active skill and one target root

- Resolve `<skill-directory>` from the active invocation, installation
  metadata, or user-specified source before invoking a script. The skill may
  live in a repository responsibility path, an installed skill directory, a
  platform-specific mirror, or another configured location; never hardcode one
  installation folder. Run the dispatcher from the target project root:

  ```bash
  <skill-directory>/scripts/pixel-perfect ...
  ```

- If multiple copies exist, verify the selected copy's `SKILL.md` and
  dispatcher version before using it, and record the exact path used. Do not
  mix scripts, references, or source instructions from different copies.
- Keep the reference, target source, renderer, and artifact namespace tied to
  the same target root. A valid metric from a different checkout or stale
  source revision is not evidence for the current implementation.

### 2. Establish the run contract before changing source

Run `preflight` before implementation and record what is observed versus what
is only assumed:

- reference dimensions, mode, alpha, and backdrop;
- target coordinate space and raster dimensions (for example CSS viewport,
  device/surface size, camera bounds, or document page size);
- scale/DPR, zoom, scroll/camera position, and renderer version when applicable;
- fonts and other material resources plus their loading/readiness status;
- target entrypoint, data, theme, scene/state, and deterministic inputs; and
- material assets and their certainty.

Dividing reference dimensions by a plausible scale factor can produce a useful
hypothesis, but it does not prove the original coordinate space, render
conditions, or renderer. Keep that value marked as an assumption until the
target render contract or adapter supports it.

### 3. Keep every artifact inside the task namespace from the first render

Script outputs belong under:

```text
<cwd>/.artifacts/pixel-perfect/<task-name>/
```

Use the returned JSON artifact paths. Do not guess stage numbers, overwrite a
prior evidence file, or compare a path copied from an earlier iteration.

For agent-owned raw captures, renderer logs, crops, and A/B test files, create
a run-local progress directory before the first render, for example:

```text
<cwd>/.artifacts/pixel-perfect/<task-name>/progress/
```

Give those files unique numeric prefixes. Do not use `/tmp`, the project root,
or unprefixed names for evidence that must remain auditable. Temporary runtime
files may remain under the skill-managed `.venv` only.

### 4. Serialize stage allocation and consume paths, not guesses

Run artifact-writing operations sequentially, especially `normalize`, `grid`,
`diff`, `quick`, `iteration`, and `accept`. Concurrent operations can choose
the same numeric stage prefix for different operation names, making the history
ambiguous even when both commands succeed. A single `quick` call is safer than
launching its component operations independently.

After every command:

1. parse the JSON result;
2. copy the exact paths into the run record;
3. verify the expected files exist and are readable; and
4. use those paths for the next command.

### 5. Treat every raster capture as a fresh, validated input

Before comparison, confirm that the raster capture:

- was produced after the latest source edit;
- is a new regular file rather than a stale previous capture;
- has the expected raster dimensions for the target's coordinate/scale
  mapping (`round(viewport × DPR)` where a renderer uses device pixels); and
- represents the intended target, state/scene, data, theme, and camera or
  scroll position.

A successful renderer exit, a non-empty PNG, or a script result of
`status: complete` is not proof that the intended state or scene was captured.
`complete` means the mechanic ran and read its artifact back; it does not mean
that the visual or semantic gates passed.

### 6. Make one hypothesis-led correction at a time

For each iteration, write the suspected cause, the smallest responsible scope,
and the expected observable effect. Avoid bundling font, geometry, gradient,
spacing, and border changes in one edit: a score change then cannot identify
what helped or regressed.

Use `iteration` against the best verified comparison. Retain an improvement
only when the relevant local evidence improves without a full-composition or
critical-region regression. Restore the best verified revision when evidence
gets worse or oscillates; do not keep the last edited source merely because it
exists.

### 7. Validate fonts and test assets at the renderer boundary

Font and material-resource experiments are valid only when the candidate was
actually loaded and used by the target renderer:

- resolve resource paths relative to the actual target/fixture, not relative to
  a temporary directory that happens to contain a test file;
- use project-local, pinned resources when strict matching matters;
- wait for the renderer's resource-ready signal (for example
  `document.fonts.ready` for a web target, or an explicit asset/shader/model
  readiness check for another target);
- keep one candidate variable per A/B render; and
- give each candidate a distinct output path and compare it under identical
  conditions.

A filesystem search, a declaration, or a successful screenshot alone does not
prove that the renderer used the intended resource. Do not compensate for an
unverified font, texture, model, shader, or asset with arbitrary downstream
geometry.

### 8. Localize only after semantic decomposition

Map sections and critical regions in full-image coordinates before using the
adaptive grid. Use grid/diff output to locate error, not to decide what a
component means. Include effect-overlap margins for shadows, glows, blur, and
overflow. A locally improved crop never replaces a fresh full-composition
comparison.

### 9. Treat external styling and network state as render inputs

An external stylesheet, web font, remote asset, model/shader, data request, or
other external resource can change the pixels without changing source code.
For strict matching, prefer pinned/local resources when the project permits
it. Otherwise wait for the required resource and content/scene state, record
the dependency, and mark the render `PARTIAL` when the adapter cannot prove
readiness. A framework or library named by the user/project is a task
constraint, not a skill default; never introduce one because another task used
it.

Do not add NumPy or another runtime dependency just because a manual probe is
slow; Pillow is the declared baseline. Add an optional dependency only after a
measured bottleneck and an explicit runtime decision.

### 10. Final evidence must come after the final edit

The final sequence is always:

```text
last source edit
→ fresh render
→ normalize/compare (or quick)
→ inspect diff and required regions
→ accept with explicit declarations
→ final report
```

Never use the best score from before an unverified edit as the final result.
Run the final full-composition render even when the last change appears local,
and report `PARTIAL` or `BLOCKED` when a renderer, font, asset, behavior, or
critical-region gate remains unknown.

## Efficient diagnosis order

When a mismatch is visible, use this order to avoid compensating for the
wrong cause:

1. capture dimensions, coordinate space, scale/DPR, camera/scroll, and
   stale-output checks;
2. global canvas/surface, container or scene bounds, major axes, and flow;
3. actual font/resource loading and text wrapping when text is present;
4. component/object size, padding, baseline, repeated rhythm, and alignment;
5. color, surface, border, radius, shadow, gradient, material, and
   anti-aliasing; then
6. icons, sprites, models, and other decorative details.

For text, inspect the actual loaded font and weight before changing margins. For
another target, inspect its actual loaded assets/materials before compensating
with geometry. For a large score stall, revisit the render contract and shared
geometry before trying more isolated target properties.

## Practical iteration template

Append one record per correction rather than rewriting a summary:

```yaml
iteration: 4
source_revision: <working-tree revision or digest>
baseline_compare: <exact JSON path>
hypothesis: <one suspected cause>
change_scope: <one component/property family>
render: <exact fresh screenshot path and conditions>
observed_global: <score, mode, tolerance>
observed_regions: <named local results>
regression: <none or explicit region>
decision: retain | hold | rollback
next: <one evidence-backed action>
```

If an experiment is invalid—for example a candidate font URL resolved to a
missing file—mark it invalid and rerun it. Do not use identical metrics from
invalid experiments to choose between candidates.

## Final pre-claim checklist

- [ ] Canonical skill path and target root are recorded.
- [ ] Reference/render conditions and observed-versus-assumed values are
      recorded.
- [ ] All artifacts and agent-owned evidence are inside the task namespace.
- [ ] Every comparison uses the exact paths returned by the latest command.
- [ ] The last source edit has a fresh full-composition render and comparison.
- [ ] Required regions and semantic sections have explicit evidence.
- [ ] Font, asset, renderer, target, behavior, grid-review, and regression
      statuses are explicit.
- [ ] `accept` was run, or the report explains why the result is `PARTIAL` or
      `BLOCKED`.
- [ ] Remaining differences and unknowns are listed honestly.
