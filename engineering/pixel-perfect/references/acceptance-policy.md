# Acceptance policy reference

## Default levels

Use a task-specific threshold when supplied. Otherwise select the least
ambiguous default supported by the render environment:

| Level | Global similarity | Preconditions |
| --- | ---: | --- |
| `EXACT` | `>= 0.99` | target dimensions/scale, renderer, resources, data, and state are locked |
| `HIGH` | `>= 0.97` | target environment is comparable but not fully identical |
| `CUSTOM` | explicit | reference or platform has special constraints |

The scripts report scores; the agent decides whether the environment satisfies
the selected level.

## Required gates for MATCHED

All of these must be true for every required reference:

1. target implementation launches/renders in the requested environment;
2. reference/render dimensions and render conditions are recorded;
3. global threshold passes in the selected comparison mode;
4. every named critical region passes its threshold or is independently
   verified with an accepted exception;
5. all required semantic sections have current evidence;
6. adaptive-grid high-severity critical hotspots are resolved or explained;
7. full composition has no regression from focused corrections;
8. in-scope interaction, behavior, and accessibility checks pass when
   applicable;
9. the implementation does not use the reference image as target content; and
10. remaining differences are explicit and material substitutions are listed.

A global score cannot excuse a failed critical control. A small non-critical
anti-aliasing difference may be accepted only when the renderer difference is
known, stable, measured, and documented.

## Multiple references

Treat each reference as a separate render contract with:

```yaml
id: desktop-dashboard
reference: dashboard.png
viewport: [1536, 1024]
dpr: 1
state: dark-loaded
```

Run comparison separately for each contract. A shared implementation must
remain consistent across them. Test intervals or transitions between provided
render conditions when the target supports them; do not optimize only the two
screenshots.

## Single reference

When there is no second render-condition/state contract, use the simplest
behavior already supported by the project. Do not fabricate complex responsive,
scene, or interaction rules. State clearly which unreferenced conditions or
behaviors were not established.

## Terminal statuses

| Status | Meaning |
| --- | --- |
| `MATCHED` | all applicable gates pass with evidence |
| `PARTIAL` | runnable result and valid evidence exist, but one or more gates remain |
| `BLOCKED` | a required renderer, asset, font, target, or input prevents proof |

`PARTIAL` and `BLOCKED` are honest outcomes, never implicit success.

## Critical regions

Typical critical regions include logo/brand, main heading, navigation,
primary CTA, form controls, focal illustration, scene focal points, document
figures, and any user-specified area. Choose examples appropriate to the target.
Every required semantic region contract should carry `bbox`, `threshold`, `weight`,
`critical`, and `status`; define critical bounds explicitly. Check them
independently from global metrics and preserve their status in the final
report. `verify_acceptance.py` rejects a required section contract that omits
these fields.

## Deliberate differences

For each remaining difference record:

```yaml
region: hero-illustration
kind: unavailable-asset | renderer-antialiasing | behavior-preservation | unknown
impact: low | material
observed: <what the evidence shows>
reason: <why it remains>
next_action: <none, asset request, renderer change, or follow-up>
```

Do not call a difference deliberate merely because correcting it is tedious.
