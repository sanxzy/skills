---
name: story-page
description: |
  Create one production-ready, model-agnostic image-generation prompt for a
  single narrative story page. Use for illustrated story pages, children's
  books, graphic narratives, cinematic keyframes, visual novels, game scenes,
  sequential art, and other image sequences that require strict visual
  continuity from one page to the next, including single- or multi-reference
  inputs.
argument-hint: "Describe the story page, sequence, characters, environment, or visual reference(s) to continue from."
---

# Story Page

Turn a narrative brief into one highly detailed prompt for one finished story
image. The prompt must make the page readable on its own while preserving the
series' established environment, character design, spatial geography, camera
language, lighting, palette, material treatment, and emotional tone.

This skill is different from `storyboard`: the default output is one coherent,
full-bleed narrative image, not a composite sheet of panels or a shot list. A
multi-panel comic or storyboard page is supported only when the user explicitly
requests it.

## Core continuity principle

Continuity is an explicit contract, not an assumption. Every page prompt must
contain a complete `CONTINUITY LOCK` that restates the visual facts inherited
from the previous prompt or established on the first page. It must also contain
a narrow `CURRENT PAGE DELTA` that names only what changes on this page.

Never write only `same as previous`, `as before`, or `continue the scene`.
Repeat the actual locked details in the new prompt so the prompt remains usable
when pasted into an image tool without hidden context. If a previous prompt is
available, preserve its resolved anchor wording as closely as possible. Change
only the fields that the current brief explicitly changes or that must evolve as
a direct consequence of the story.

## Interface

### Input

Accept:

- a free-form narrative or visual brief in any language;
- an optional previous `story-page` prompt, inline text, or prior artifact;
- zero or more attached visual references, including character, wardrobe, prop,
  pose, environment, camera, lighting, or previous-page images; each may have a
  user-defined identifier, role, attribute scope, or target subject;
- an optional series or project name, page number, chapter, scene, beat, or
  sequence position;
- optional character, prop, environment, wardrobe, architecture, or world
  details;
- optional aspect ratio, page orientation, crop, medium, realism, visual
  style, camera language, palette, lighting, mood, typography, and rendering
  constraints;
- an optional safe output path.

The current written brief is authoritative for the page-specific request. The
previous prompt's resolved continuity anchors are authoritative for inherited
facts. A current brief may intentionally update one inherited fact; record that
update explicitly instead of allowing accidental drift. Visual references supply
observable evidence scoped by an explicit reference map; they do not silently
override written continuity or the user's requested transformation. Do not infer
unshown identity, relationships, narrative events, off-frame details, or material
properties from any reference.

If the user asks for continuation but provides no previous prompt, prior
artifact, previous-page visual reference, or sufficient series bible, ask for the
missing continuity source before writing. Do not invent an established
character design, location, camera system, or palette merely to make the page
appear complete.

### Output

Return and write exactly one English, model-agnostic image-generation prompt in
raw Markdown. Do not wrap it in a fenced code block, add a rationale essay,
produce unrelated variants, or append conversational commentary to the
artifact.

The default output is one finished full-bleed story illustration for one page.
It must be self-contained and paste-ready. When visual references are supplied,
it must include a stable `REFERENCE MAP` with concise textual observations,
ownership, and preserve/change boundaries. The prompt may contain structural
labels for clarity, but those labels are generation instructions, not visible
page typography. Only text explicitly requested by the user may appear in the
image.

The default artifact path is:

`_xzy-ai/outputs/story-page/<series-slug>-page-<NNN>.md`

Use a user-supplied path only when it remains inside the active workspace and
contains no traversal. Derive a safe lowercase kebab-case series slug from the
project or series name; if no name is supplied, use the scene or story subject,
then `story-page`. Use the supplied page number when available. Never overwrite
an existing artifact; append `-2`, `-3`, and so on to the filename when needed.

The artifact must not require a previous file, transcript, scratch prompt,
or external example to be interpreted. Read supplied continuity material during
the workflow, then restate the necessary facts in the new prompt. If visual
references are used for rendering, the artifact may name the supplied images only
through a stable `REFERENCE MAP`; it must never contain image paths, URLs, or
unapproved external-file dependencies.

## Workflow

### 1. Parse the page brief

Extract resolved facts and open decisions separately. Identify, when supplied:

- story premise, page function, narrative beat, cause and effect, and intended
  emotional response;
- page number, chapter, scene, sequence order, preceding state, and desired
  next state;
- every subject, character role, silhouette, face or face treatment, hair,
  body language, clothing or surface design, markings, and recurring prop;
- location identity, architecture, terrain, landmarks, foreground objects,
  midground structures, background horizon, scale cues, and spatial geography;
- time of day, season, weather, atmospheric density, and environmental changes;
- visual medium, rendering method, linework, realism, texture, finish, and
  established art direction;
- aspect ratio, orientation, page margins or bleed, crop, focal hierarchy, and
  any explicitly requested panel or border treatment;
- subject positions, facing direction, screen direction, depth plane, gaze,
  distance to landmarks, negative space, and occlusion relationships;
- camera height, viewpoint, shot scale, angle, lens or perspective, focus,
  depth of field, and movement implied by the frame;
- lighting sources, direction, softness, shadow behavior, color temperature,
  bounce light, rim light, and continuity with the prior page;
- dominant, secondary, and accent colors; saturation, contrast, color grade,
  and the emotional tone carried by the palette;
- materials, surface wear, wetness, dust, translucency, gloss, roughness,
  fabric or construction details, and contact shadows;
- atmosphere, particles, weather effects, motion cues, magical or graphic
  effects, and their physical relation to the scene;
- dialogue, captions, signage, labels, logos, and other text that must appear
  exactly, if any;
- each visual reference, its stable identifier, role, observable attributes,
  target subject or prop, requested fidelity, and preserve/change scope;
- exact final character count and identity, wardrobe, accessory, prop, pose,
  camera, environment, lighting, and spatial ownership when multiple references
  or characters are involved;
- the intended delivery purpose, such as picture book, visual novel, game
  concept, cinematic frame, editorial illustration, or sequential art.

Do not turn every adjective into a new visual fact. Preserve concrete details
that affect identity, continuity, composition, or rendering; omit unsupported
embellishment.

### 2. Resolve material ambiguity

Ask one focused question at a time when an unresolved decision could materially
change the image. Do not ask for information already present in the brief. Use
low-risk defaults when the choice is not consequential.

Ask before guessing about:

- a page illustration versus a comic page, storyboard sheet, or multi-image
  output when the wording is ambiguous;
- aspect ratio or orientation when the result would change the composition
  substantially;
- the required fidelity of a visual reference;
- multiple references whose roles, target subjects, attribute ownership, or
  attachment order are unclear;
- a reference containing incidental people when the intended final character
  count is unclear;
- a character redesign or environment change that conflicts with a previous
  continuity lock;
- a new location when it is unclear whether the story moved or the existing
  location should be preserved;
- a face, identity, costume, or prop change that could materially alter the
  established subject;
- visible text, branding, dialogue, or captions when the supplied wording is
  incomplete or contradictory.

When neither format nor orientation is supplied, default to a 4:5 portrait,
full-bleed narrative illustration. When the brief clearly implies a cinematic
wide frame, use 16:9. A user-supplied ratio always overrides the default.

If any visual reference is supplied and fidelity is unresolved, ask the user to
choose one for the relevant reference or attribute:

- `inspired` — borrow broad mood, palette, or compositional energy while
  creating a distinct design;
- `faithful` — preserve the main visual anchors while adapting the requested
  page or transformation;
- `close` — retain most visible design details while changing the scene or
  presentation;
- `clone` — reproduce the reference as closely as possible only after the user
  confirms authorization.

### 3. Map visual references

Treat visual references as a mapped set of evidence, not as an instruction to
blend whole images. If no visual reference is supplied, omit `REFERENCE MAP` and
do not imply that one exists.

When one or more references are supplied:

1. **Assign stable identifiers.** Preserve user-provided or tool-provided names.
   If no names exist and attachment order is reliable, label the attachments as
   `Reference A`, `Reference B`, `Reference C`, and so on, and state the order in
   the prompt. If order is not reliable and the distinction matters, ask the
   user to label the attachments. Never invent unavailable semantic `@` IDs,
   file paths, or URLs.
2. **Assign a narrow role and target to every reference.** Possible roles include
   identity, face, hair, body proportions, wardrobe, accessory, prop, pose,
   interaction, camera, environment, lighting, palette, material, or composition.
   Record only visible, relevant observations for the mapped page, character,
   prop, or global scene.
3. **Define each reference card with `ROLE`, `TARGET`, `OBSERVATION`, `PRESERVE`,
   `CHANGE`, and `DO NOT TRANSFER`.** A hidden, cropped, occluded, or ambiguous
   attribute is unspecified; do not turn an inference into a continuity fact.
4. **Assign attribute ownership.** Map identity, face, hair, proportions,
   wardrobe, accessories, props, pose, interaction, camera, environment,
   lighting, and palette to the written brief or to a specific reference. Use
   explicit source-to-target wording, such as `transfer the wardrobe
   construction from Reference B to Character 1 while preserving Character 1's
   identity from Reference A`.
5. **Map multi-character references individually.** State the exact final
   character count, assign stable character IDs, map each identity and attribute
   owner, and map person slots in group or pose references. People visible only
   in a wardrobe, pose, environment, or group reference are not additional
   page subjects unless the brief requests them. Keep identity separate from
   screen position and interaction geometry.
6. **Keep preserve/change scope local.** If the brief changes only the pose,
   camera, or background, preserve all other resolved continuity locks. Require
   one unified story-page image, never a source-reference collage or a vague
   `combine these images` result.
7. **Resolve conflicts before writing.** Current written instructions and an
   explicit `CURRENT PAGE DELTA` override inherited written continuity only when
   they intentionally change it; inherited written locks override a new image;
   character- and attribute-specific mapping overrides general reference
   impression; conservative inference is last. If a material conflict remains,
   ask one focused question instead of averaging or inventing a compromise.

If the user requests from-scratch generation or says not to pass references to
the renderer, inspect references only as visual evidence when available, author
the description independently, omit them from the renderer handoff, and never
place an image path or URL in the prompt. When reference-driven rendering is
requested, attach only the mapped references separately and preserve their
mapping/order.

Read and apply the conditional companion [Multi-Reference Mapping](./references/MULTI-REFERENCE-MAPPING.md) for the complete registry, ownership,
multi-character, conflict-resolution, and renderer-handoff checklist. It
supplements this skill without changing the full-bleed story-page contract or
canonical prompt order.

### 4. Establish or recover the continuity ledger

Treat continuity as two layers: **identity/system locks** and **page state**.
Identity/system locks remain stable across pages unless the user explicitly
updates them. Page state evolves through visible story events. When a
`REFERENCE MAP` exists, merge only its mapped, visible observations into the
relevant locks; do not let a new image silently replace a previous written
anchor.

Recover these identity/system locks from the previous prompt when available:

- **Series visual language:** medium, rendering method, line or brush behavior,
  realism level, texture, finish, and visual hierarchy;
- **Reference anchors:** active reference identifiers, roles, and attribute
  ownership that must remain stable across pages;
- **Canvas system:** orientation, crop grammar, safe margins or bleed, and
  recurring framing conventions; preserve the ratio declared under `ASPECT
  RATIO:` without repeating it;
- **World and location:** the recurring place, architectural or natural
  geometry, permanent landmarks, surface materials, scale relationships, and
  recognizable background anchors;
- **Time and atmosphere:** season, time of day, weather pattern, air density,
  and baseline environmental condition;
- **Character identity:** names supplied by the user, roles, silhouette,
  proportions, face treatment, hair shape and color, skin or surface features,
  clothing or body-surface construction, colors, accessories, and recurring
  markings;
- **Prop identity:** dimensions, shape, materials, color, wear, markings,
  ownership, and any recurring relationship to a character or landmark;
- **Camera grammar:** viewpoint side, camera height, perspective or lens
  behavior, typical shot scale, horizon treatment, and screen-direction rules;
- **Lighting rig:** key direction, fill level, shadow softness, rim or bounce
  behavior, color temperature, and baseline contrast;
- **Color system:** dominant hues, secondary hues, accent colors, saturation,
  contrast, and grade;
- **Spatial map:** left/right landmark order, screen direction, recurring
  entrances or exits, subject geography, and orientation of important props.

Recover these page-state fields from the previous prompt and update them only
through explicit story movement:

- each subject's last position, depth plane, orientation, gaze, pose, and
  action state;
- each recurring prop's last position, orientation, holder, and physical state;
- the direction and cause of movement, including what remains off-screen;
- the current weather, light change, damage, transformation, or environmental
  event;
- the last camera position and the reason a new page changes or preserves it;
- unresolved visual consequences that the next page must show.

If a previous prompt conflicts with a previous image or a newly supplied
reference, preserve the written prompt's intended continuity unless the user
asks to correct the visual result. Do not rewrite the series bible merely to
rationalize accidental render drift.

If the current brief intentionally changes a locked field, record it in
`CURRENT PAGE DELTA`, state the new value in the relevant section, and preserve
all unaffected locks. A new scene may change location, time, or lighting, but it
must state the transition and retain character, style, camera, and palette
anchors unless the user also changes them.

### 5. Define the page delta before drafting

Write a short internal change list before assembling the prompt:

1. what the story advances from the previous page;
2. which subject action, expression, pose, or relationship changes;
3. which prop or environmental state changes;
4. which positions, screen directions, or depth relations change;
5. which camera or composition change makes the beat legible;
6. which lighting, palette, or atmosphere change is caused by the story;
7. which facts remain locked and must not drift.

The page delta is not permission to redesign everything. If the brief asks for a
new action in the same room, keep the room geometry, landmarks, style, camera
system, palette, and lighting behavior stable. If the brief asks for a new
location, carry forward every unaffected identity and rendering anchor.

### 6. Design the spatial composition

Plan the image as a readable spatial system before writing adjectives. State
where things are and how they relate:

- divide the frame into foreground, midground, and background;
- identify the visual anchor and its approximate frame position;
- place each subject using a normalized position such as left third, center,
  right third, upper/lower zone, or an approximate percentage when useful;
- state the subject's depth plane, facing direction, gaze direction, distance
  from recurring landmarks, and overlap or occlusion order;
- preserve left/right screen geography and screen direction from the previous
  page unless a motivated camera reversal is requested;
- name the nearby components that frame the subject: walls, doors, furniture,
  vegetation, vehicles, terrain, signage, props, shadows, or atmospheric layers;
- describe the negative space needed for the action, gaze, silhouette, or
  readable emotional beat;
- explain the path of the eye through scale, leading lines, contrast, color,
  gesture, and depth;
- keep all important faces, hands, props, and story clues inside the requested
  crop unless the brief deliberately places one off-screen.

Use relational placement when exact measurements are not established. Do not
invent false numeric precision merely to sound detailed.

### 7. Write the prompt in the canonical order

Use plain uppercase labels, a blank line after each label, and concise but
specific comma-separated phrases. Use complete physical descriptions rather
than generic style-word lists. Keep the following order unless the user
explicitly requests a different non-core format:

1. opening descriptor stack;
2. `ASPECT RATIO:`;
3. `SERIES / PAGE:`;
4. `REFERENCE MAP:` when visual references are supplied;
5. `PAGE PURPOSE:`;
6. `CONTINUITY LOCK:` with the nested locks below;
7. `CURRENT PAGE DELTA:`;
8. `SCENE ENVIRONMENT:`;
9. `FOREGROUND:`;
10. `MIDGROUND:`;
11. `BACKGROUND:`;
12. `SUBJECTS:`;
13. `BLOCKING AND POSITION:`;
14. `ACTION / EXPRESSION:`;
15. `COMPOSITION:`;
16. `CAMERA:`;
17. `LIGHTING:`;
18. `COLOR TONE:`;
19. `MATERIALS / TEXTURES:`;
20. `ATMOSPHERE / EFFECTS:`;
21. `TEXT / GRAPHICS:` when visible text or graphic identity is relevant;
22. `RENDERING / QUALITY:`;
23. `AVOID:`;
24. `PAGE STATE FOR NEXT PAGE:`.

The opening descriptor stack should identify the requested medium, narrative
purpose, finish, and continuity priority in 6–12 short phrases. Do not place a
rationale or unresolved alternative before `ASPECT RATIO:`.

#### `REFERENCE MAP:`

Include this section only when one or more visual references are supplied. Make
it a compact operating map for the attached evidence, not a vague similarity
request or a transcription of every visible detail. Use the same stable labels
throughout the prompt. Preserve user- or tool-provided attachment names; if no
names exist and order is reliable, state `Reference A = first attached image`,
`Reference B = second attached image`, and so on. Never include image paths,
URLs, or unavailable semantic identifiers.

For each reference, state only relevant visible evidence:

- `ROLE:` what it controls, such as identity, wardrobe, prop, pose, camera,
  environment, lighting, palette, material, or composition;
- `TARGET:` the page subject, character, prop, or global scene receiving it;
- `OBSERVATION:` concrete visible anchors;
- `PRESERVE:` attributes that must remain stable;
- `CHANGE:` the narrow `FROM → TO` transformation;
- `DO NOT TRANSFER:` unrelated identity, face, hair, body, wardrobe, pose,
  environment, text, or incidental people.

When multiple characters are involved, add `CHARACTER MAP`, `ATTRIBUTE
OWNERSHIP`, and the exact final character count. Map identity, wardrobe,
accessories, props, pose, interaction, and position to each character
separately. A person visible only in a wardrobe, pose, environment, or group
reference is not an additional page subject unless explicitly requested.

Add explicit source-to-target assembly, for example: transfer the wardrobe
construction from `Reference B` to `Character 1` while preserving `Character
1`'s identity from `Reference A`. Integrate the result into one coherent
full-bleed story-page image, not a collage or a hidden multi-image montage.
Resolve conflicts before writing: current written instructions and an explicit
page delta override inherited written locks only when they intentionally change
them; inherited written locks override a new image; character- and
attribute-specific mapping overrides general reference impression; conservative
inference is last. If a material conflict remains, ask one focused question
rather than blending or inventing a compromise.

#### `CONTINUITY LOCK:`

Include these nested labels whenever they apply, even when the value is
unchanged:

- `Series visual language:`
- `Reference anchors:` — active reference identifiers, roles, and owned
  attributes that must remain stable across pages;
- `Canvas system:` — orientation, crop grammar, safe margins or bleed, and
  recurring framing conventions; do not repeat the ratio already stated under
  `ASPECT RATIO:`;
- `World and location:`
- `Time and atmosphere:`
- `Character anchors:`
- `Wardrobe / surface anchors:`
- `Recurring prop anchors:`
- `Camera grammar:`
- `Lighting rig:`
- `Color system:`
- `Spatial map:`

State the inherited values concretely. For a first page, these fields establish
the baseline that subsequent prompts must repeat.

#### `CURRENT PAGE DELTA:`

Name only the intentional changes on this page. State the preceding state and
new state when the transition matters. End with an explicit instruction such as
`preserve every other continuity lock without redesign or drift`.

#### `SCENE ENVIRONMENT:`, `FOREGROUND:`, `MIDGROUND:`, `BACKGROUND:`

Describe the setting from large structure to small visible components. Include
location, surface, geometry, landmark identity, placement, depth, scale,
occlusion, focus, and continuity with the previous page. The background must be
specific enough that another prompt writer can recreate the same place rather
than merely choosing a similar mood.

#### `SUBJECTS:`

Describe each subject's locked identity before its current page state. Include
silhouette, proportions, face treatment, hair or head shape, clothing or
surface construction, recurring accessories, and distinguishing marks. Do not
invent names or identity facts. Keep the same subject design across pages even
when pose, emotion, damage, dirt, wetness, or lighting changes.

When a `REFERENCE MAP` exists, use its same character IDs and attribute owners
in `SUBJECTS`, `BLOCKING AND POSITION`, and `PAGE STATE FOR NEXT PAGE`. Keep each
character's identity, face, hair, proportions, wardrobe, accessories, and props
with its assigned owner; do not let a pose or wardrobe reference replace the
target subject. Exclude incidental people from source images and state the exact
final character count when multiple characters are involved.

#### `BLOCKING AND POSITION:`

Give every important subject and prop a clear frame position, depth plane,
orientation, facing direction, gaze, relationship to landmarks, and overlap
order. Use screen-left/screen-right consistently. State who is nearer or farther,
which limbs or objects lead the gesture, and how the composition leaves room for
movement or text. Keep character identity separate from position: name the
mapped character first, then state where it stands. For interactions, identify
the participant, body part, prop, contact point, and spatial relationship
explicitly.

#### `ACTION / EXPRESSION:`

Describe visible cause and effect, not an abstract plot summary. Explain weight
shift, limb direction, hand contact, gaze, facial expression or face treatment,
prop interaction, and emotional progression. The action must be physically
legible and must begin from the previous page's state when this is a continuation.

#### `COMPOSITION:`

Define the visual hierarchy, focal point, balance, leading lines, scale
contrast, negative space, crop, horizon, occlusion, and any requested page
border or panel treatment. Do not silently turn one full-bleed image into a
collage, triptych, or storyboard sheet.

#### `CAMERA:`

State camera height, viewpoint, horizontal side, shot scale, angle, lens or
perspective, distance, horizon, focus plane, depth of field, and any implied
movement. Explain why a changed camera view serves the page beat. Preserve the
series camera grammar when no change is requested.

#### `LIGHTING:`, `COLOR TONE:`, `MATERIALS / TEXTURES:`

Describe the light source positions and quality, shadow direction and softness,
bounce and rim behavior, palette hierarchy, contrast, saturation, color grade,
and the physical response of important surfaces. Keep these systems coherent
with the continuity lock. A dramatic change must have a visible story cause.

#### `ATMOSPHERE / EFFECTS:`

Include only effects supported by the brief or the established world: fog,
rain, dust, snow, mist, smoke, sparks, glow, magical energy, motion blur,
reflections, or particles. State their location, direction, density, scale,
and interaction with light and subjects. Effects must not obscure story-critical
faces, hands, props, or landmarks without a deliberate reason.

#### `TEXT / GRAPHICS:`

Include exact user-supplied dialogue, captions, signage, logos, or graphic
marks only when they must appear. Specify wording, language, placement, scale,
typography treatment, and legibility. If no text is requested, state `no visible
text, no invented lettering, no random logos or watermarks`.

#### `RENDERING / QUALITY:`

State the medium, finish, detail level, texture fidelity, anatomy or object
integrity, edge control, depth separation, and presentation quality. Use
concrete observable properties rather than unsupported technical guarantees.

#### `PAGE STATE FOR NEXT PAGE:`

Provide a concise but complete handoff marked as control information, not
visible typography. Record the current positions, facing directions, action
state, expression, prop state, spatial map, camera side, light direction,
weather, active reference ownership, and the exact continuity locks that must
carry forward. Preserve the final character count and character IDs when a
reference map is active. Do not include unresolved questions or speculative
future events.

### 8. Write the artifact

Before writing:

- resolve every material decision or ask the focused question required to
  resolve it;
- confirm the page is one image unless a multi-panel page was explicitly
  requested;
- derive the safe output slug and page number;
- verify that the destination is inside the active workspace and will not
  overwrite an existing artifact;
- assemble one raw English Markdown prompt in the canonical order, including
  `REFERENCE MAP` only when references are supplied;
- ensure mapped references are represented by stable labels and concise textual
  observations, never by image paths, URLs, or unapproved external dependencies;
- run the quality gate below.

After the quality gate passes, write automatically and report the exact path.
The user's aesthetic judgment remains authoritative after reviewing the prompt or
any later render.

## Quality gate

Reject and revise the prompt before writing if any check fails.

### Continuity

- A previous prompt or sufficient initial series brief was used whenever the
  user requested continuation.
- `CONTINUITY LOCK` restates the actual inherited style, canvas, world,
  characters, props, camera, lighting, palette, and spatial anchors; it does not
  rely on `same as previous`.
- When references are supplied, `REFERENCE MAP` gives every reference a stable
  role, target, visible observation, ownership, preserve/change boundary, and
  conflict rule.
- Every reference-derived detail is visibly supported by its mapped reference
  or explicitly supplied in the brief; hidden, cropped, and off-frame details
  are not presented as facts.
- `CURRENT PAGE DELTA` contains only requested or causally necessary changes.
- Character silhouette, face treatment, hair, surface or wardrobe construction,
  recurring accessories, and distinguishing marks remain consistent.
- Reference-owned identity, wardrobe, accessory, prop, pose, and scene attributes
  remain with their assigned owners; no identity or wardrobe crossover occurs.
- Recurring landmarks, architecture, terrain, screen-left/screen-right order,
  screen direction, and depth geography remain consistent unless a transition
  is explicitly shown.
- Camera grammar, light direction, color grade, material treatment, and visual
  medium remain consistent unless a motivated change is stated.
- Page state advances from the prior state without impossible teleportation,
  prop duplication, unexplained disappearance, or contradictory action.
- Multi-character pages state the exact final character count and preserve stable
  character IDs, positions, interactions, and reference ownership.
- `PAGE STATE FOR NEXT PAGE` records the new state clearly and contains no
  unresolved alternatives.

### Spatial and visual specificity

- The page function, current action, emotional beat, and intended focal point
  are visible and concrete.
- Foreground, midground, and background identify actual components and their
  positions, depth, scale, and relation to the subjects.
- Every important subject and prop has a clear location, orientation, gaze or
  facing direction, depth plane, and overlap relationship.
- Composition, crop, negative space, camera, focus, and perspective support the
  narrative beat rather than forming a random list of terms.
- Lighting specifies source direction, quality, shadows, bounce or rim behavior,
  and continuity with the established light system.
- Color tone specifies dominant, secondary, and accent relationships plus grade,
  contrast, or saturation when relevant.
- Materials, textures, and atmospheric effects are physically and stylistically
  coherent with the locked world.

### Prompt integrity

- The prompt is in English, model-agnostic, concrete, and paste-ready.
- The aspect ratio is stated once without contradiction.
- The default is clearly one full-bleed narrative image, or the explicitly
  requested page layout is described without accidental montage behavior.
- When references are supplied, the page uses a `REFERENCE MAP` and explicit
  source-to-target assembly rather than vague image combination.
- No names, dialogue, logos, props, landmarks, plot events, or cultural meanings
  were invented.
- Only user-supplied visible text is requested; no random lettering, watermark,
  fake credit, or brand mark is added.
- No image path, transcript, scratch file, external log, or outside example is
  required to interpret the artifact; supplied attachments are identified only
  through the validated reference map.
- No unavailable semantic reference identifiers, placeholders, unresolved
  alternatives, internal reasoning, or questions remain in the artifact.
- `AVOID` is concise, relevant, and does not contradict the positive prompt.

### Artifact safety

- The destination stays inside the active workspace and contains no traversal.
- An existing artifact is never overwritten.
- The generated file contains only the one validated prompt, with no fenced
  wrapper or appended rationale.
- All authored project-file content is English and whitespace-clean.

## Companion files

The main `SKILL.md` owns the complete story-page interface, continuity contract,
and canonical prompt order. Read this companion only when the current input
contains one or more visual references:

- [Multi-Reference Mapping](./references/MULTI-REFERENCE-MAPPING.md) — stable
  reference labels, role and attribute ownership, preserve/change boundaries,
  multi-character mapping, conflict resolution, anti-hallucination checks, and
  renderer handoff.

The companion is conditional and never overrides the current written brief,
inherited continuity locks, or the full-bleed story-page contract. Do not require
any workspace log, transcript, scratch prompt, generated image, external example,
or file outside this skill's companion files to understand or validate the
workflow.

## Optional renderer iteration

This skill does not require image generation. When a caller separately renders
the prompt:

1. Send the validated prompt and the caller's chosen image-tool settings.
2. When references are used, attach only the images listed in `REFERENCE MAP`,
   preserve their mapping/order or real attachment names, and do not add an
   unmapped reference. Do not place an image path in the prompt.
3. When the caller requests from-scratch generation or no reference transfer,
   omit all image references from the renderer handoff.
4. Inspect the result for continuity, not just attractiveness: character
   identity, reference-owned attributes, exact character count, landmark
   geometry, subject positions, screen direction, camera, lighting, palette,
   prop state, action, and page function.
5. Treat an accepted image that changes a locked character, location, camera
   side, lighting system, palette, or reference ownership as a continuity
   failure.
6. Change one evidence-based variable at a time. Do not respond to drift with
   arbitrary retries, unrelated detail, or a giant negative prompt.
7. If the renderer exposes only a generic HTTP error, report the exact visible
   status and do not claim an unverified cause.
8. If a render reveals a mismatch, update only the affected positive anchor,
   preserve the rest of the continuity lock, and rerun the complete quality
   gate before writing a replacement prompt.

## Do not

- Do not confuse one story-page illustration with a storyboard sheet, shot list,
  or unrelated prompt bundle.
- Do not write `same as previous` as a substitute for repeating continuity
  details.
- Do not silently redesign an established character, prop, environment, camera
  system, lighting rig, or palette.
- Do not treat an accidental previous render drift as the new canonical design
  without the user's approval.
- Do not invent narrative events, character names, relationships, landmarks,
  props, dialogue, logos, or visible text.
- Do not change screen direction or spatial geography without stating the camera
  reversal or story movement that causes it.
- Do not list camera, lighting, or style adjectives that are absent from the
  actual composition.
- Do not use a supplied image path as prompt text or claim clone-level fidelity
  without authorization.
- Do not refer to multiple images without a stable mapping, assign an attribute
  without an owner, use vague `combine these images` wording, or transfer
  incidental people into the page.
- Do not overwrite an existing artifact.
- Do not leave external-file dependencies, scratch notes, unresolved questions,
  or internal reasoning in the final prompt; supplied visual attachments are
  allowed only when explicitly mapped in the current input.
