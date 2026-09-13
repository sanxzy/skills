# Multi-Reference Mapping

This is a conditional companion for `story-page`. Read it only when the input contains one or more visual references. `SKILL.md` remains the source of truth for the full-bleed story-page interface, continuity ledger, page delta, canonical prompt order, artifact path, and quality gate. This document deepens only reference mapping, ownership, anti-hallucination, and renderer-handoff behavior.

## Goal

Turn a set of images into limited, traceable visual evidence for one narrative page:

- identify what each reference controls;
- identify which output subject, character, prop, or scene receives it;
- separate inherited anchors from the current-page change;
- prevent identity bleed, wardrobe crossover, incidental people, collage behavior, and unsupported invention;
- keep reference-driven pages consistent with the written series continuity.

Do not treat references as a stack of images to blend. Treat them as an attribute graph:

```text
reference evidence → owned attribute → target subject or scene → current page → next-page state
```

## Reference registry

Create a stable registry before drafting.

1. Preserve identifiers supplied by the user or calling interface.
2. If no identifiers exist and attachment order is reliable, assign `Reference A`, `Reference B`, `Reference C`, and so on in attachment order, and state the mapping in the prompt.
3. If order is not reliable and the distinction affects the page, ask the user to label the attachments before writing.
4. Never invent unavailable semantic identifiers, file paths, URLs, or renderer capabilities.
5. Attach only references present in the registry; do not add an unregistered image.

A registry entry should be concise:

```text
Reference A — character identity
Attachment mapping: first attached image
Target: Character 1
Extract: face, hair, silhouette, approximate proportions
Preserve: identity anchors across the series
Change: none unless explicitly requested
Do not transfer: clothing, pose, background, or incidental people
```

The attachment mapping is an execution aid, not a file citation. If a tool exposes a real attachment name, use that name instead of inventing a positional claim.

## Reference cards

For every reference, record only visible information relevant to its assigned role:

- **`ROLE`** — identity, face, hair, body proportions, wardrobe, accessory, prop, pose, interaction, camera, environment, lighting, palette, material, composition, or another concrete role;
- **`TARGET`** — the output character, subject, prop, page scene, or global image that receives the evidence;
- **`OBSERVATION`** — visible shape, color, construction, position, texture, lighting, or composition anchors;
- **`PRESERVE`** — features that must remain stable across this and later pages;
- **`CHANGE`** — the narrow `FROM → TO` transformation requested for this page;
- **`DO NOT TRANSFER`** — unrelated identity, face, hair, body, wardrobe, pose, environment, text, or incidental people.

Do not promote an inference to an observation. If a detail is hidden, cropped, occluded, ambiguous, or absent, mark it unspecified and follow the written brief or inherited continuity instead of filling the gap.

## Attribute ownership

Assign one primary owner to every important attribute. Use the current written brief when it explicitly specifies the result; otherwise use the most specific mapped reference, subject to inherited written continuity.

| Attribute | Required owner | Validation rule |
| --- | --- | --- |
| Identity, face, hair, body proportions | one character identity source or written lock | remains attached to that character across pages |
| Wardrobe, accessories, surface design | named wardrobe source and target character | source model identity never transfers |
| Prop design and state | prop source or written brief | owner, position, and state remain traceable |
| Pose, gesture, and weight distribution | pose source or written brief | posture transfers without identity or clothing |
| Interaction geometry | mapped multi-person pose source or written brief | person slots map to named output characters |
| Camera and composition | camera source or written brief | preserve series camera grammar unless changed |
| Environment, lighting, palette, and materials | scene source or written brief | do not import unrelated subjects or text |

If two references control one attribute, divide the responsibility explicitly, for example: `Reference B controls wardrobe silhouette; Reference C controls fabric texture and trim.` Never use only `combine the clothing from B and C`.

## Multi-character mapping

Use separate identity and attribute maps:

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
3. state frame position, depth plane, screen direction, and relationship to other characters;
4. keep every defining feature with its assigned owner;
5. state the exact final character count.

A reference can contain several people but supply only one attribute. Map slots explicitly, such as `Reference E / person on the left → Character 1 pose` and `Reference E / person on the right → Character 2 pose`. People appearing only in wardrobe, pose, environment, or group references are not additional page subjects unless requested.

Keep identity separate from position. Write `Character 1 occupies screen-left` rather than using `the person on the left` as the character's only identifier.

For interactions, map the relation as well as the participants:

```text
Character 1 right hand → holds the left side of the prop
Character 2 left hand → holds the right side of the prop
Prop → centered between both characters
```

Carry these assignments into `CONTINUITY LOCK`, `SUBJECTS`, `BLOCKING AND POSITION`, and `PAGE STATE FOR NEXT PAGE`.

## Preserve and change boundaries

Use a narrow page-local transformation.

- If the brief changes only the background, preserve identity, proportions, wardrobe, pose, props, camera grammar, lighting system, and palette.
- If the brief changes only the pose, keep the mapped character and wardrobe design unchanged.
- If the brief changes only the camera, keep character, prop, and environment ownership unchanged.
- If the reference is inspirational, transfer broad visual direction rather than exact construction.
- If fidelity is `faithful` or `close`, list the anchors supporting that scope; do not silently escalate to cloning.
- Use `clone` only after user authorization and only for the specified reference scope.

A reference can control one attribute while being irrelevant to everything else. State the boundary positively: `extract only the pose geometry from Reference E; do not transfer its identity, clothing, hairstyle, lighting, environment, or text.`

For continuation pages, a new reference does not replace an inherited written lock unless the current brief explicitly changes that lock and records the change in `CURRENT PAGE DELTA`.

## Assembly and conflict resolution

Use source-to-target instructions:

```text
Transfer [attribute] from [Reference] to [target character or scene].
Preserve [owned inherited attributes] from [previous written lock or other reference].
Integrate the result into one coherent full-bleed story-page image, not a collage.
```

Resolve conflicts in this order:

1. current written brief and explicit page delta;
2. inherited written continuity locks;
3. character-specific and attribute-specific ownership;
4. role-specific evidence from the mapped reference;
5. conservative inference for unspecified details.

If two sources materially conflict and the brief does not establish priority, ask one focused question before writing. Do not average faces, merge costumes, blend proportions, copy every visible person, or invent a compromise. Do not turn a hidden or cropped area into a precise continuity fact.

## From-scratch mode

When the user explicitly requests from-scratch generation or says not to pass references to the renderer:

- inspect the images only as visual evidence when available;
- write the visual description independently;
- omit the references from the renderer handoff;
- never put an image path or URL in the prompt;
- do not claim exact reference fidelity.

When reference-driven rendering is requested, attach only registered images separately from the prompt and preserve their order or real attachment names. The prompt must still contain enough textual observation to make the intended page legible without guessing.

## Validation checklist

Before writing the page artifact, verify:

- every supplied reference has a stable identifier, role, and target;
- every reference card contains visible observations, preserve scope, change scope, and do-not-transfer scope;
- every important character and attribute has one clear owner;
- the exact final character count is stated when multiple characters or reference subjects are involved;
- source-to-target transfer is explicit and never described as vague combination;
- incidental people, text, props, backgrounds, and wardrobe cannot leak between targets;
- inherited locks are not replaced by a new image without an explicit page delta;
- conflicts are resolved or surfaced as a question rather than guessed;
- `REFERENCE MAP` appears in the canonical prompt order;
- no image path, URL, unavailable identifier, external log, or unapproved file is required;
- the result remains one coherent full-bleed story-page image with a clear current beat and complete next-page state.
