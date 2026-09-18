# Pixel-perfect workflow reference

## Purpose

This document expands the orchestration contract in `SKILL.md`. It describes
what the agent decides, what the scripts measure, and which evidence is needed
before moving between states. The fields are target-neutral; `viewport`, DPR,
and browser values below are illustrative render-condition examples. For
operational rules distilled from prior reproduction runs, also read
[`predictability.md`](predictability.md).

## Run record

Keep one run record for each target/reference set. Store image, diff, grid,
and report artifacts only under `<cwd>/.artifacts/pixel-perfect/<task_name>/`.
Create a run-local `progress/` directory there before the first capture for
agent-owned raw renders, crops, logs, and A/B files; keep those filenames
numeric-prefixed as well. The runtime's dependency files belong under
`<cwd>/.venv`; they are not visual evidence. At minimum record:

```yaml
run_id: <safe id>
task_name: <safe artifact namespace segment>
started_at: <timestamp>
status: INSPECTING
references:
  - path: <absolute path>
    viewport: [1536, 1024]
    state: dashboard-dark
    source_digest: <optional sha256>
target:
  project_root: <absolute path>
  framework: <observed value>
  renderer: <command or tool>
conditions:
  viewport: [1536, 1024]
  dpr: 1
  zoom: 1
  theme: dark
  data: fixed-fixture
sections: []
iterations: []
evidence: []
assumptions: []
blockers: []
```

Persist the record before a long-running render/correction loop when the host
project has a durable artifact convention. Append observations rather than
overwriting the explanation for earlier iterations.

## State transitions

```text
INSPECTING
  -> DECOMPOSED       after reference/project facts and section map exist
DECOMPOSED
  -> IMPLEMENTING     after the first bounded implementation scope is chosen
IMPLEMENTING
  -> RENDERING        after a runnable target state is prepared
RENDERING
  -> COMPARING        after a fresh screenshot is materialized
COMPARING
  -> CORRECTING       when a material mismatch has a supported hypothesis
COMPARING
  -> VERIFYING        when required local checks are stable
CORRECTING
  -> RENDERING        after the focused change is applied
VERIFYING
  -> MATCHED          only when every applicable gate passes
VERIFYING
  -> PARTIAL/BLOCKED   when a valid but incomplete result or hard prerequisite remains
```

A script's JSON `status: complete` only says that its mechanical operation and
artifact read-back succeeded. It is not the run state `MATCHED`.

## Efficient command sequence

Use the cheapest evidence that answers the current question. Each operation
allocates the next numeric stage under the task directory; never overwrite a
prior stage. Run artifact-writing operations serially and consume the exact
paths returned in JSON. Concurrent operations can select the same numeric
prefix for different operation names, so a successful command is not
permission to infer a stage path.

1. agent inspects the reference and target project;
2. `preflight` records dimensions, capabilities, resources, and assets;
3. agent renders only the requested target render condition/state (or uses the
   target-specific adapter; `browser` is the web option);
4. `quick` performs normalize → compare → diff for a small stable iteration;
5. agent inspects evidence, maps the hotspot, and makes one focused change;
6. `grid` is added when a mismatch needs localization;
7. `iteration` records retain/hold/rollback evidence against the baseline; and
8. `accept` evaluates the final full-composition evidence and declarations.

Do not regenerate diff/heatmap for every exploratory thought if the global
comparison already shows that the change is unrelated. After geometry or flow
changes, however, always rerun a full composition comparison because local
metrics cannot prove that downstream sections remained stable.

## Iteration record

Each correction should be explainable without the agent's hidden reasoning.
The example below uses a web heading, but the record applies equally to a
native view, simulator surface, canvas/game scene, desktop window, or document:

```yaml
iteration: 4
state: CORRECTING
scope: hero-heading
hypothesis: font fallback increases line width and pushes the CTA down
change: load project-local Inter weight 600 before capture
before:
  global_similarity: 0.9412
  local_difference_percentage: 18.4
reference_condition: viewport 1536x1024, DPR 1, dark, fixed data
observed_after:
  global_similarity: 0.9731
  local_difference_percentage: 3.1
  regression: none
decision: keep
next: verify hero and full composition
```

If the after score is lower or another region regresses, restore the best
verified revision rather than alternating properties blindly. If a behavior
fix is required despite a small visual cost, keep it when it is in scope and
record the deliberate trade-off.

## Section boundary rule

Section comparison regions include a small overlap margin for shadows, glows,
blur, borders, and overflow. The margin is evidence-only: it does not change
the implementation geometry. The full-image grid always retains original
coordinates so a local issue can be traced back to the page map.

## Recovery checklist

When a stage fails:

1. preserve the last valid run/evidence record;
2. classify the failure as input, environment, renderer, asset, comparison, or
   implementation;
3. fix the smallest root cause;
4. verify the next screenshot is new, readable, correctly sized, and from the
   intended source/state;
5. rerun from that fresh render, not a stale screenshot;
6. compare against the best baseline using the returned artifact paths; and
7. record whether the failure was recovered or remains a blocker.

A missing screenshot is unknown. An unchanged screenshot after an intended
change is evidence of no observable change, not proof that the action worked.
An invalid A/B experiment—such as a font URL resolved relative to the wrong
HTML directory—must be marked invalid and rerun before its metrics are used.
