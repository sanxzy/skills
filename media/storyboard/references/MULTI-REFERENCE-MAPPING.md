# Multi-Reference Mapping

This is a conditional companion for `storyboard`. Read it only when the input contains one or more visual references. `SKILL.md` remains the source of truth for the storyboard prompt contract, canonical section order, narrative structure, timing, layout, and artifact path. This document deepens only the reference-mapping, ownership, anti-hallucination, and renderer-handoff rules.

Convert a set of images into explicit, limited visual evidence:

- identify which reference controls which attribute;
- identify which output character, prop, or scene receives that attribute;
- separate what must be preserved from what must change;
- prevent identity bleed, wardrobe crossover, incidental people, collage-like assembly, and unsupported invention;
- keep the final prompt useful when the mapped images are attached separately, without embedding file paths or outside dependencies.

Do not treat a multi-reference input as `image A + image B + image C`. Treat it as an attribute graph:

```text
reference evidence → owned attribute → target subject or scene → final storyboard sheet
```

## Reference registry

Create a stable registry before drafting the prompt.

1. Preserve identifiers supplied by the user or the calling interface.
2. If no identifiers exist and attachment order is reliable, assign `Reference A`, `Reference B`, `Reference C`, and so on in attachment order, and state that mapping in the prompt.
3. If order is not reliable and the distinction affects the result, ask the user to label the attachments before writing.
4. Never invent unavailable semantic identifiers, file paths, URLs, or renderer capabilities.
5. Attach only references listed in the registry. Do not add an unregistered image because it looks useful.

A registry entry should be concise:

```text
Reference A — character identity
Attachment mapping: first attached image
Target: Character 1
Extract: face, hair, silhouette, approximate proportions
Preserve: identity anchors and defining marks
Change: none unless stated in the brief
Do not transfer: clothing, pose, background, or incidental people
```

The `Attachment mapping` line is an execution aid, not a file citation. If an interface exposes a real attachment name, use that name instead of inventing a positional claim.

## Reference card

For every reference, create one card with only information relevant to its assigned role:

- **`ROLE`** — identity, face, hair, body proportions, wardrobe, accessory, prop, pose, interaction, camera, composition, environment, lighting, palette, material, board layout, or another concrete role;
- **`TARGET`** — the output character, prop, scene, or global sheet that receives the evidence;
- **`OBSERVATION`** — visible shape, color, construction, position, texture, lighting, or composition anchors;
- **`PRESERVE`** — features that remain stable across panels;
- **`CHANGE`** — an explicit local transformation written as `FROM → TO`;
- **`DO NOT TRANSFER`** — attributes that belong to another source or are irrelevant, including faces, bodies, clothing, pose, environment, text, and incidental people.

Do not promote an inference to an observation. If an attribute is hidden, cropped, occluded, ambiguous, or absent, mark it as unspecified and follow the written brief rather than filling the gap.

## Attribute ownership

Assign one primary owner to every important attribute. Use the written brief as an owner when it explicitly specifies the result; otherwise use the most specific mapped reference.

| Attribute | Required owner | Validation rule |
| --- | --- | --- |
| Identity, face, hair, body proportions | one character identity source | must remain attached to that character |
| Wardrobe, accessories, surface design | a named wardrobe source and target character | never transfer the source model's identity |
| Prop design and prop state | a prop source or written brief | preserve owner and state across panels |
| Pose, gesture, and weight distribution | a pose source or written brief | transfer posture only, not identity or clothing |
| Interaction geometry | a mapped multi-person pose source or written brief | map left/right person slots to output characters |
| Camera and composition | camera/composition source or written brief | apply globally unless a panel explicitly changes it |
| Environment, lighting, palette, and board layout | scene source or written brief | do not import unrelated subjects or text |

If two references control one attribute, split their responsibilities explicitly, for example: `Reference B controls garment silhouette; Reference C controls fabric texture and trim.` Never write only `combine the clothing from B and C`.

## Multi-character mapping

Use two levels of identity:

```text
Reference A → Character 1 identity
Reference B → Character 1 wardrobe
Reference C → Character 2 identity
Reference D → Character 2 wardrobe
Reference E / left person → Character 1 pose
Reference E / right person → Character 2 pose
```

For each output character:

1. assign a stable character ID, using a user-supplied name or a neutral label such as `Character 1`;
2. map identity, face, hair, proportions, wardrobe, accessories, props, pose, gaze, and interaction separately;
3. state where the character appears in the sheet and who they interact with;
4. preserve boundaries so one character cannot inherit another character's defining features;
5. state the exact number of final characters.

A reference may contain several people but still supply only one attribute. Map slots explicitly, such as `Reference E / person on the left → Character 1 pose` and `Reference E / person on the right → Character 2 pose`. People appearing only in a wardrobe, pose, environment, or group reference are not additional output characters unless the brief requests them.

Keep identity separate from position. Write `Character 1 occupies the left side` rather than using `the woman on the left` as the character's only identifier.

For interactions, map the relationship as well as the participants:

```text
Character 1 right hand → holds the left side of the prop
Character 2 left hand → holds the right side of the prop
Prop → centered between both characters
```

## Preserve and change boundaries

Use a narrow transformation scope.

- If the brief says `change only the background`, preserve identity, proportions, wardrobe, pose, props, camera, and lighting unless another change is explicitly requested.
- If the brief changes the pose, keep the mapped character design unchanged.
- If the brief changes the camera, keep character and wardrobe ownership unchanged.
- If a reference is used for inspiration only, transfer broad visual direction rather than exact visible construction.
- If fidelity is `faithful` or `close`, list the anchors that justify that level; do not silently escalate to cloning.
- Use `clone` only after the user confirms authorization and only for the specified reference scope.

A reference can be authoritative for one attribute and irrelevant for all others. State this boundary positively: `extract only the pose geometry from Reference E; do not transfer its identity, clothing, hairstyle, lighting, or environment.`

## Assembly and conflict resolution

Write source-to-target instructions:

```text
Transfer [attribute] from [Reference] to [target character or scene].
Preserve [owned attributes] from [other reference or written brief].
Integrate all mapped elements into one coherent subject and one storyboard sheet, not a collage.
```

Resolve conflicts in this order:

1. explicit written instructions;
2. character-specific and attribute-specific ownership;
3. role-specific evidence from the mapped reference;
4. conservative inference for unspecified details.

If two sources conflict materially and the brief does not establish priority, ask one focused question before writing. Do not average faces, merge costumes, blend body proportions, copy every visible person, or invent a compromise. Do not convert a hidden or cropped area into a precise fact.

## From-scratch mode

When the user explicitly requests a from-scratch prompt or says not to pass references to the renderer:

- inspect the images only as visual evidence when visual inspection is available;
- write the visual description independently;
- omit the references from the renderer handoff;
- never put an image path or URL in the prompt;
- do not claim exact reference fidelity.

When reference-driven rendering is requested, attach only the registered images separately from the prompt and preserve the registry order or real attachment names. The prompt must still state enough textual observations to make the intended output legible without guessing.

## Validation checklist

Before writing the storyboard artifact, verify:

- every supplied reference has a stable identifier and one or more explicit roles;
- every reference card contains a target, visible observations, preserve scope, change scope, and do-not-transfer scope;
- every important character and attribute has one clear owner;
- exact final character count is stated when more than one reference or character is involved;
- source-to-target transfer is explicit and never described as vague combination;
- incidental people, text, props, backgrounds, and clothing cannot leak from one reference into another target;
- conflicts are resolved or surfaced as a question rather than guessed;
- the `REFERENCE MAP` appears in the canonical prompt order;
- no image path, URL, unavailable identifier, external log, or unapproved file is required;
- the final sheet remains one coherent storyboard with readable panels, continuity, and a deliberate ending.
