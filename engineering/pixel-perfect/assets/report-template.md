# Pixel-perfect final report

```text
Status: MATCHED | PARTIAL | BLOCKED
Target: <runtime / framework / device / renderer>
Reference: <path(s), render condition/state, dimensions>
Render conditions: <coordinate space, viewport/window/surface/camera, scale/DPR, zoom, renderer, resources, theme, data, state>
Global similarity: <score, mode, tolerance>
Critical-region status: <passed / failed / unknown; list failures>
Sections verified: <count>/<total; bbox/threshold/weight/critical/status contract>
Font certainty: <exact / substitute / recreated / missing / unknown / not in scope>
Asset certainty: <exact / substitute / recreated / missing / unknown / not in scope>
Behavior verification: <passed / partial / not applicable / not in scope / blocked>
Machine gates: <path to acceptance JSON; MATCHED/PARTIAL/BLOCKED>
Remaining differences:
- <region>: <observed difference>; <reason/impact>
Assumptions or substitutions:
- <explicit item or none>
Evidence:
- normalized reference/render: <path>
- comparison metrics: <path>
- adaptive grid: <path>
- diff: <path>
- heatmap: <path>
- preflight/browser/iteration evidence: <path(s) or none>
```

## Evidence minimum

Attach or retain the actual final render, normalized pair (or the input
conditions proving they are equivalent), comparison JSON, and diff/heatmap when
any material difference remains. For multiple references, list evidence per
contract. Include the run/iteration record when the work used a correction
loop.

## Language rules

Use:

- **observed** for pixels, files, and measured outputs;
- **inferred** for likely causes or semantics not independently proven; and
- **unknown** for unavailable or inconclusive evidence.

Do not replace a failed or unavailable check with a polished summary.
