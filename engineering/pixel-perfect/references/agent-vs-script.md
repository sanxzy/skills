# Agent versus script responsibility

The skill is intentionally hybrid. The **agent** owns meaning, scope, and
source-code decisions. The **scripts** own deterministic mechanics that can be
validated without subjective judgment. Never swap these boundaries merely to
make a report look complete.

## Responsibility matrix

| Stage | Agent handles | Script handles | Handoff/evidence | Script must not claim |
| --- | --- | --- | --- | --- |
| `INSPECTING` | inspect reference/project; identify visible facts, assumptions, target runtime, assets, resources, state, and behavior scope | `preflight` reads raster facts and discovers local runtime/renderer/executable/resource capabilities | preflight JSON + agent fact/assumption notes | what a target means, hidden behavior, exact render conditions from pixels, or that an adapter can render the target |
| `DECOMPOSED` | semantic sections/objects; ownership, dependencies, global constraints, critical regions, thresholds, and statuses | `compare`/`grid` only later measure coordinates and error | section contract JSON + regions JSON | which object/target element owns a hotspot or whether a section is semantically correct |
| `IMPLEMENTING` | modify native target code, preserve behavior/accessibility, choose assets, and keep changes scoped | no public pixel script edits target source | target diff + implementation notes | that a visual score compensates for broken behavior or prohibited reference embedding |
| `RENDERING` | choose adapter, target/entrypoint, state, data, render conditions, theme, camera/scroll, and wait policy; verify target state | the selected adapter performs bounded screenshot mechanics when it supports the requested controls | adapter manifest + actual screenshot + target-state observation | that a successful renderer exit proves the intended target state, loaded resources, or behavior |
| `COMPARING` | choose comparison mode/tolerance and interpret whether the result is relevant to the contract | `normalize` decodes/orients/composites RGB; `compare` calculates pixel/color/edge/region metrics | normalized pair + compare JSON | that one similarity score means `MATCHED` |
| `LOCALIZING` | map hotspots to semantic owners; select the highest-impact hypothesis and effect-overlap region | `grid` subdivides error in full-image coordinates; `diff` emits diff/heatmap images | grid JSON + inspected diff/heatmap | what caused a red cell or that a local crop proves full composition |
| `CORRECTING` | make one smallest evidence-backed code change; decide whether behavior trade-off is allowed | `iteration` compares current/baseline evidence and recommends retain/hold/rollback | iteration JSON + agent-applied Git/source action | that it can edit, revert, commit, or silently retain target code |
| `VERIFYING` | inspect actual artifacts, run behavior/accessibility checks, map critical regions, assess substitutions, and decide final status | `accept` evaluates supplied reports/declarations into machine-readable gates | acceptance JSON + final agent report | that declarations or metrics prove semantics not supplied as evidence |

## Command ownership

The scripts are mechanical and can be composed:

- `runtime`: skill dependency setup only;
- `preflight`: capability/input discovery only;
- `browser`: optional target screenshot mechanics only;
- `normalize`: image representation normalization only;
- `compare`: metric calculation only;
- `grid`: coordinate-preserving error localization only;
- `diff`: visual evidence materialization only;
- `quick`: normalize → compare → diff convenience chain only;
- `iteration`: evidence-based retain/hold/rollback recommendation only; and
- `accept`: gate aggregation only.

The agent must use the returned JSON and inspect actual images before making a
semantic claim. The agent must not reimplement the scripts' pixel algorithms
or blindly trust a script path, exit code, score, or filename.

## Quick command boundary

`quick` is appropriate for a small stable iteration after the agent has
already inspected the target and produced a fresh render:

```text
agent: inspect target and render current state
script: quick normalize + compare + diff
agent: inspect metrics/diff, hypothesize, edit code
agent: rerender and run quick again
script: accept only after the agent supplies all required declarations
```

It does not inspect the codebase, render the target, fix code, verify behavior,
or decide acceptance. Add `--with-grid` only when localization is needed; do
not generate grid evidence for every tiny iteration by default.

## Browser boundary

`browser` is a standard mechanical adapter, not a universal target oracle. It
prefers an installed Playwright package and otherwise uses a discovered native
Chrome/Chromium headless executable. The Playwright path supports viewport,
DPR, wait selector, font readiness, animation disabling, theme, scroll, and
full-page capture. The CLI fallback supports only the controls reported in its
manifest and marks unsupported requested controls as `partial`.

The agent chooses the browser target and state, confirms the screenshot is the
intended target, and performs semantic/behavior/accessibility checks. If the
adapter is unavailable or reports a limitation, the agent returns `BLOCKED` or
`PARTIAL` instead of treating a fallback screenshot as equivalent evidence.

## Acceptance boundary

`accept` is deliberately fail-closed for final `MATCHED`:

- every comparison must prove dimensions and threshold;
- critical regions must be explicitly passed, not merely absent;
- section status must be supplied and matched;
- target and behavior status must be declared;
- font and asset certainty must be exact or explicitly in-scope/allowed;
- grid evidence must be supplied and reviewed by the agent; and
- an iteration report recommending rollback cannot be ignored.

The final decision still depends on agent-owned evidence that no script can
infer generically, especially semantic ownership, target behavior,
accessibility when applicable, and accidental reference-image embedding.
