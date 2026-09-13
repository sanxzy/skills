---
name: storyboard
description: |
  Create one production-ready, model-agnostic storyboard sheet prompt from a
  free-form narrative brief. Use for cinematic sequences, animation boards,
  action breakdowns, commercials, music videos, game cinematics, visual
  previsualization, and single- or multi-reference continuity work. The primary output is an English Markdown prompt; image
  rendering is optional and is never required.
argument-hint: "Describe the story, sequence, characters, setting, or visual reference(s)."
---

# Storyboard

Turn a narrative or visual brief into one coherent prompt for a composite storyboard sheet. The prompt must communicate story progression, shot grammar, timing, continuity, and visual direction—not merely a collection of attractive poses.

## Interface

### Input

Accept:

- a free-form brief in any language;
- zero or more attached images or visual references; when several are supplied, each may have a user-defined identifier, role, attribute scope, or target character;
- optional duration, panel count, scene count, timecodes, aspect ratio, medium, visual style, camera language, palette, lighting, mood, dialogue, captions, sound cues, and delivery purpose;
- optional character, prop, environment, brand, or continuity constraints;
- an optional safe output path.

The user's written brief is the source of truth. Extract only facts that are present or clearly requested. Treat supplied images as visual evidence scoped by an explicit reference map; do not infer unshown identity, relationships, narrative events, off-frame details, or material properties. Do not invent character names, dialogue, logos, cultural meanings, plot events, relationships, props, or visual details that materially change the brief.

### Output

Return and write exactly one structured prompt in raw English Markdown. Do not wrap it in a fenced code block, add a rationale essay, or produce multiple variants.

The default artifact path is:

`_xzy-ai/outputs/storyboard/<slug>.md`

Use a user-supplied path only when it remains inside the active workspace and contains no traversal. Never overwrite an existing artifact; append `-2`, `-3`, and so on when the target already exists.

The default artifact describes one composite storyboard sheet containing all requested panels. It does not render an image. If the caller separately requests image generation, use the validated prompt with the caller's chosen image tool; rendering is not part of this skill's required output.

Every completed artifact must:

- describe one understandable sequence with a beginning, development, and ending or deliberate final beat;
- preserve resolved story, character, prop, environment, style, camera, timing, and layout decisions;
- use model-agnostic, concrete English unless a target model is explicitly named;
- contain a numbered scene or panel breakdown with readable timecodes when timing is relevant;
- maintain continuity across characters, screen direction, props, geography, lighting, and action;
- include the required sections in the order defined below;
- include a stable `REFERENCE MAP` whenever visual references are supplied, with explicit roles, observations, ownership, preserve/change boundaries, and conflict resolution;
- contain no unresolved placeholders, contradictions, invented text, unsafe paths, or unapproved external-file dependencies; supplied attachments may be referenced only through stable labels and must also be described textually;
- include a concise `AVOID` section.

## Workflow

### 1. Parse the brief

Extract and separate resolved facts from open decisions:

- story premise, objective, conflict, transformation, and final beat;
- characters, their visual anchors, roles, relationships, expressions, and body language;
- setting, time, geography, environmental conditions, and recurring landmarks;
- actions, cause-and-effect transitions, emotional progression, and pacing;
- duration, panel count, scene count, timecodes, and transition requirements;
- storyboard medium: rough ink, clean animation board, 3D previsualization, live-action film board, comic layout, or another requested treatment;
- aspect ratio, sheet orientation, panel arrangement, gutters, annotations, and background treatment;
- camera size, angle, lens or perspective, movement, screen direction, and editing rhythm;
- visual effects, motion cues, lighting, palette, texture, rendering, mood, and quality level;
- supplied dialogue, captions, sound cues, brand text, and other text that must be preserved exactly;
- each visual reference, its stable identifier, intended role, observable attributes, target character or prop, requested fidelity, and preserve/change scope;
- exact output character count and identity, wardrobe, prop, pose, camera, environment, and lighting ownership when multiple references or characters are involved;
- intended use, such as animation planning, commercial pitch, game cinematic, music video, or film previsualization.

Do not turn every descriptive phrase into a separate panel. Identify the narrative beats that must be seen and connect them causally.

### 2. Resolve material ambiguity

Ask one focused question at a time when a missing decision can materially change the result. Offer a recommended default when useful. Ask before guessing about:

- a conflicting or ambiguous aspect ratio or sheet layout;
- an individual frame sequence versus one composite storyboard sheet;
- a missing ending when multiple outcomes are plausible;
- a visual medium or realism level that changes the board substantially;
- a reference's required fidelity when the supplied image is not clearly inspirational or authoritative;
- multiple references whose roles, target characters, attribute ownership, or attachment order are unclear;
- a reference containing incidental people when the intended final character count is unclear;
- a duration or panel count when both are absent and pacing is central to the brief.

Do not ask the user to repeat a decision already present in the brief. When a missing detail is low-risk, use the defaults in this skill and make the resolved choice visible in the prompt.

If neither duration nor panel count is supplied, default to a concise 12-panel sequence across 15 seconds. If the brief clearly implies a different scale, preserve that implied scale instead. If only one is supplied, derive the other without changing the requested story beats. If explicit timecodes are supplied, preserve them and do not redistribute them.

### 3. Handle visual references

Treat visual references as a mapped set of evidence, not as an instruction to blend whole images. If no reference is supplied, omit `REFERENCE MAP` and do not imply that one exists.

When one or more references are supplied:

1. **Assign stable identifiers.** Preserve user-provided names or identifiers. If none exist, label the attachments in the supplied order as `Reference A`, `Reference B`, `Reference C`, and so on, and state that mapping explicitly. If attachment order is not reliable and the distinction matters, ask the user to label the references before writing. Never invent unavailable semantic `@` identifiers, file paths, or URLs.

2. **Assign one or more explicit roles to each reference.** Possible roles include character identity, face, hair, body proportions, wardrobe, prop, pose, interaction, camera, composition, environment, lighting, palette, material, or storyboard presentation. For every reference, record only relevant visible evidence:
   - `ROLE` — what the reference controls;
   - `OBSERVATION` — concrete features visibly supported by that reference;
   - `PRESERVE` — anchors that must remain consistent;
   - `CHANGE` — the requested `FROM → TO` transformation and its scope;
   - `DO NOT TRANSFER` — unrelated identity, pose, wardrobe, environment, or incidental people.

3. **Establish attribute ownership and source/target mapping.** Assign each important attribute to the written brief or to a specific reference. For multi-character sequences, map every output character separately: identity, face, hair, body proportions, wardrobe, accessories, props, pose, and interaction. State the exact final character count. A person visible only inside a wardrobe, pose, environment, or group reference is not an output character unless the brief explicitly requests it.

4. **Assemble rather than collage.** Use explicit source-to-target instructions such as `transfer the garment construction from Reference B to Character 1 while preserving Character 1's identity from Reference A`. Integrate the mapped attributes into one coherent subject and one coherent storyboard sheet. Do not use vague instructions such as `combine these images` or allow an incidental reference subject to become the target.

5. **Resolve conflicts before writing.** Apply this priority order: explicit written instructions, character- or attribute-specific mapping, role-specific reference evidence, then conservative visual inference. If two references materially conflict and no priority is supplied, ask one focused question; do not average the references or invent a compromise. Do not infer hidden, occluded, or off-frame details as facts.

If fidelity is not resolved, ask the user to choose one for the relevant reference or attribute:

- `inspired` — borrow broad mood, palette, or compositional energy while creating a distinct design;
- `faithful` — preserve the main visual anchors while changing the presentation into the requested storyboard;
- `close` — retain most visible design details while adapting them to the sequence;
- `clone` — reproduce the reference as closely as possible only after the user confirms authorization.

When the user asks for a from-scratch prompt, references are visual evidence only:

- author the description independently from visual inspection;
- do not put image paths or URLs in the generated prompt;
- do not pass the references to a renderer when the caller explicitly requested no reference transfer;
- describe enough of the relevant visual result that the artifact does not require an outside file to understand its intent;
- do not claim exact or pixel-level fidelity unless the user explicitly authorized it and the result supports that claim.

When references are intended for rendering, the caller may attach only the mapped images separately from the prompt. Preserve their mapping and order, and do not add an unmapped reference. The artifact must use stable labels rather than paths and must never claim that an unavailable identifier is understood by the renderer.

Translate named artists, studios, or brands into observable properties when they are used only as style shorthand. Preserve a brand name, fictional property, or supplied on-screen text when it is explicitly part of the requested identity. Create an original visual treatment rather than copying an artist's signature style.

When one or more references are supplied, read and apply the conditional companion [Multi-Reference Mapping](./references/MULTI-REFERENCE-MAPPING.md). It deepens the registry, attribute-ownership, multi-character, conflict-resolution, and renderer-handoff rules without changing this skill's canonical output order.

### 4. Build the narrative spine

Before writing the final prompt, reduce the brief to a causal sequence:

1. **Orientation** — establish who or what is present, where it is, and the initial state.
2. **Trigger** — show the event, discovery, decision, or pressure that starts the movement.
3. **Development** — escalate the action or emotion through distinct visual beats.
4. **Turn or payoff** — show the consequence, reveal, transformation, or decisive action.
5. **Resolution** — end on the requested outcome, aftermath, image, or deliberate cliffhanger.

Use only the stages the brief supports. An abstract montage may use rhythm or thematic progression instead of a literal plot, but each panel must still have a visual function and a meaningful relation to adjacent panels.

Every panel should answer at least one of these questions:

- What changed from the previous panel?
- What new information is revealed?
- What action or reaction advances the sequence?
- What camera or scale change makes the beat legible?
- What emotional or visual payoff is being prepared?

Do not repeat the same action with a new angle unless the repetition is explicitly requested for emphasis, rhythm, or slow motion.

### 5. Design the storyboard sheet

The default composition is one polished composite board rather than a single finished illustration:

- a clear grid or intentional cinematic panel arrangement;
- distinct panel gutters and readable separation;
- consistent character and prop design across all panels;
- numbered panels and time labels when requested or needed for production clarity;
- a visual hierarchy that gives the opening, climax, and final beat enough weight;
- sparse production annotations only when requested or useful;
- mapped character and reference attributes remain distinct across every panel;
- no source-reference collage, incidental reference people, invented captions, dialogue, logos, or labels;
- no panel cropped by the canvas boundary.

A requested layout overrides the default. If the brief specifies a panel count, row structure, page count, or left-to-right reading direction, follow it exactly. If the user requests individual frame prompts instead of a sheet, ask whether to keep this one-prompt contract or start a separate prompt-generation run; do not silently produce a bundle of unrelated prompts.

### 6. Write the scene breakdown

Use a stable, readable format for every panel:

```text
01 (00:00–00:01)
shot size and camera angle,
subject and action,
environment and continuity anchor,
story or emotional function,
optional movement, effect, sound, or transition cue
```

Use `MM:SS` timecodes for sequences longer than one minute and preserve the user's precision when finer timing is supplied. Time ranges must be chronological, non-overlapping, and cover the intended duration without unexplained gaps. If the brief supplies only point timestamps, use those points consistently rather than fabricating ranges.

Each panel description should identify, as relevant:

- shot size and viewpoint;
- camera movement or transition;
- subject position, action, gaze, expression, or body language;
- mapped character identity and any reference-owned continuity anchor when needed;
- important prop state, owner, and its change;
- environment, screen direction, and spatial relation;
- emotional or narrative purpose;
- motion lines, particles, impact, atmosphere, or other visible effects;
- optional sound or editing cue when it improves previsualization.

Keep the wording prompt-friendly: concrete visual nouns and concise action phrases are more useful than a screenplay paragraph. Use a consistent action tense and do not switch camera direction, costume, prop placement, or environment without a stated story reason.

For a multi-scene brief, create a `SCENE BREAKDOWN` subsection for each scene while retaining one global continuity description. For a single sequence, use one numbered list.

### 7. Assemble the final prompt

Use this order unless the user explicitly requests a different non-core layout:

1. `ASPECT RATIO`;
2. opening quality and storyboard-medium statement;
3. `PROJECT` when supplied;
4. `REFERENCE MAP` when visual references are supplied;
5. `STORY PREMISE`;
6. `CHARACTERS`;
7. `MAIN ENVIRONMENT`;
8. `STORYBOARD LAYOUT`;
9. `STORY STRUCTURE`;
10. `SCENE BREAKDOWN`;
11. `CAMERA LANGUAGE`;
12. `VISUAL DETAILS`;
13. `LIGHTING`;
14. `COLOR PALETTE`;
15. `MOOD`;
16. `RENDERING`;
17. `QUALITY`;
18. `AVOID`.

Add `SOUND / EDITING CUES` after `SCENE BREAKDOWN` only when the brief includes sound, dialogue, transitions, rhythm, or edit-specific requirements. Add `PRODUCTION NOTES` only when the user supplies or requests production annotations.

Use the following section behavior:

#### `ASPECT RATIO`

State the resolved canvas or sheet ratio first, such as `16:9`, `4:3`, `2.39:1`, or a user-specified custom ratio. Do not add a conflicting ratio elsewhere.

#### Opening statement

Lead with the requested medium and visual purpose, for example `professional cinematic storyboard sheet`, `rough animation previsualization board`, `hand-drawn manga storyboard`, or `3D film blocking storyboard`. Combine only compatible style descriptors. Translate shorthand into observable properties where needed: line quality, rendering method, camera realism, panel treatment, texture, and finish.

#### `REFERENCE MAP`

Include this section only when one or more visual references are supplied. Make it an operational map for the renderer, not a vague similarity request or a transcription of every visible detail. Use the same stable identifiers everywhere in the prompt. If the interface exposes named attachments, preserve those names; otherwise state the attachment-order mapping, such as `Reference A = first attached image`, without inventing file paths or semantic identifiers.

For each reference, state only relevant, visibly supported information:

- `ROLE` — identity, wardrobe, pose, prop, camera, environment, lighting, palette, layout, or another concrete role;
- `OBSERVATION` — observable design, construction, composition, or surface anchors;
- `PRESERVE` — attributes that must remain consistent;
- `CHANGE` — the requested `FROM → TO` transformation and its scope;
- `DO NOT TRANSFER` — unrelated identity, face, hair, body, wardrobe, pose, environment, text, or incidental people.

When multiple characters are involved, add explicit `CHARACTER MAP` and `ATTRIBUTE OWNERSHIP` lines. Map each output character to its identity reference and assign wardrobe, accessories, props, pose, interaction, camera, and scene attributes separately. State the exact final character count. A person visible only in a wardrobe, pose, environment, or group reference is reference evidence, not an additional output character.

Add an `ASSEMBLY` rule with explicit source and target, for example: transfer the garment construction from the wardrobe reference to the mapped character while preserving that character's identity reference. Require one unified subject and one coherent storyboard sheet rather than a collage. Add `CONFLICT RESOLUTION`: explicit written instructions override character- or attribute-specific mappings, which override role-specific reference evidence; unresolved material conflicts must be resolved before writing, never blended through guesswork.

#### `STORY PREMISE`

State the central subject, objective, conflict or discovery, progression, and intended ending in compact prompt language. Preserve the user's narrative and do not write a new synopsis that changes it.

#### `CHARACTERS`

Define continuity anchors once: names supplied by the user, role, silhouette, clothing or surface design, hair or head treatment, props, expression range, body language, and relationships. Repeat only the anchors needed to keep later panels consistent. For anonymous, masked, faceless, non-human, or collective subjects, describe the requested treatment directly rather than inventing an identity.

When a `REFERENCE MAP` exists, use the same character identifiers and attribute ownership throughout `CHARACTERS` and `SCENE BREAKDOWN`. Keep each character's face, hair, body proportions, wardrobe, accessories, props, and defining marks with its assigned owner; do not let a pose or wardrobe reference replace the target character's identity. State the exact number of characters visible in the final sheet and exclude incidental people from source references unless explicitly requested.

If the sequence includes sensitive content, keep the framing professional and non-exploitative. Do not sexualize minors or turn a neutral brief into sexualized imagery. Preserve safe visual intent without adding moral commentary to the prompt.

#### `MAIN ENVIRONMENT`

Describe the recurring location, spatial landmarks, time, weather, surface, atmosphere, lighting conditions, and environmental continuity. If the setting changes, state the transition in the relevant panel rather than pretending it is unchanged.

#### `STORYBOARD LAYOUT`

Describe the sheet orientation, panel count, reading order, grid or arrangement, panel gutters, hero/climax emphasis, annotations, background, and how all panels remain inside the canvas. Keep the board visibly a storyboard sheet, not one merged illustration.

#### `STORY STRUCTURE`

State the total duration, panel count, scene count, pacing arc, and any required progression. Use the user's exact structure when supplied. A sequence may be described as `20-panel sequence`, `15-second cinematic progression`, `three-scene commercial board`, or an equivalent concrete structure.

#### `SCENE BREAKDOWN`

Number every panel. Use timecodes and the stable format above. Make the action progress and preserve continuity. Include the final beat explicitly; do not end with a generic `dramatic shot` when the brief supplies a concrete outcome.

#### `CAMERA LANGUAGE`

Describe the shared camera grammar and the purpose of changes: establishing wide shots, tracking views, over-the-shoulder transitions, macro inserts, overhead geography, low-angle impact shots, lens distortion, rack focus, push-ins, pans, tilts, or cuts. Avoid a random list of camera terms that is not reflected in the panel breakdown.

#### `VISUAL DETAILS`

Describe linework or rendering marks, motion arrows, speed lines, panel borders, perspective guides, particles, impact marks, depth of field, blur, transitions, annotations, and other visual evidence of motion or production planning. Keep effects subordinate to the story and style.

#### `LIGHTING`, `COLOR PALETTE`, and `MOOD`

Define a coherent visual system. Mention changes in light or palette only when they support the sequence. Preserve user-supplied colors and emotional intent; do not add arbitrary color symbolism.

#### `RENDERING` and `QUALITY`

State the final finish and production context: rough or clean board, monochrome or color, 2D or 3D, animation or live-action previsualization, detail level, and presentation quality. Avoid unsupported technical guarantees. `8k` may be included only when the user requests it or it is part of their established prompt convention; it does not replace clear composition or continuity.

#### `AVOID`

Keep this list concise and relevant. It may include inconsistent character appearance, broken continuity, missing panels, duplicated beats, unreadable or invented text, merged panel borders, cropped content, random logos, watermarks, extra limbs, distorted anatomy, contradictory lighting, or a single polished key art image replacing the requested storyboard sheet. Do not repeat every positive requirement as a negative prompt.

### 8. Write the artifact

Before writing:

- resolve every material decision or ask the focused question required to resolve it;
- derive a safe lowercase kebab-case slug from the project name, then the sequence name, then `storyboard`;
- verify that the destination is inside the active workspace and will not overwrite an existing artifact;
- assemble one raw English Markdown prompt in the canonical order, including `REFERENCE MAP` only when references are supplied;
- ensure mapped references are represented by stable labels and concise textual observations, never by file paths or unapproved external dependencies;
- run the quality gate below.

After the quality gate passes, write automatically and report the exact path. The user's aesthetic judgment remains authoritative after they review the artifact or a later render.

## Quality gate

Reject and revise the prompt before writing if any check fails.

### Story and intent

- The requested subject, premise, objective, conflict or discovery, progression, ending, setting, style, mood, and intended use are present when supplied.
- The sequence has a readable narrative or thematic progression rather than disconnected images.
- No character, prop, relationship, event, logo, dialogue, or cultural meaning was invented.
- Every reference-derived detail is visibly supported by its mapped reference or explicitly supplied in the brief; hidden, occluded, and off-frame details are not presented as facts.
- When references are supplied, every reference has an unambiguous role, target, and preserve/change boundary; no whole-image blending is implied.
- The final beat matches the brief and is explicitly represented.
- Resolved decisions are not contradicted by later sections.

### Timing and continuity

- The panel count, scene count, duration, and timecodes agree with each other.
- Time ranges are chronological, non-overlapping, and complete when ranges are used.
- Character appearance, action state, prop state, screen direction, geography, lighting, and environment remain consistent unless a change is shown or requested.
- Mapped character identities and reference-owned attributes remain with their assigned owners across every panel; wardrobe, face, pose, and prop details do not cross over.
- Camera changes have a narrative or visual purpose and appear in the panel breakdown.
- Every panel changes, reveals, advances, emphasizes, or resolves something meaningful.

### Sheet composition

- `ASPECT RATIO`, `STORYBOARD LAYOUT`, `STORY STRUCTURE`, `SCENE BREAKDOWN`, `CAMERA LANGUAGE`, `VISUAL DETAILS`, `LIGHTING`, `COLOR PALETTE`, `MOOD`, `RENDERING`, `QUALITY`, and `AVOID` are present; `REFERENCE MAP` is also present when references are supplied.
- One composite storyboard sheet is clearly requested, with panel borders, gutters, reading order, and all content contained within the canvas.
- The requested medium and rendering treatment are clear and internally compatible.
- Any requested annotations, dialogue, captions, or brand text are preserved exactly; no unsupported text was added.

### Vocabulary and integrity

- The prompt is English, model-agnostic, concrete, and free of placeholders.
- No image path, transcript, external log, outside example, or unapproved reference file is needed to interpret it; supplied attachments are named only through the validated reference map.
- No unavailable semantic reference identifier, random logo, watermark, fake production credit, or invented on-screen text is requested.
- Named style shorthand has been translated into observable properties unless the proper name is explicitly part of the requested identity.
- `AVOID` is short, relevant, and does not introduce contradictions.
- No temporary notes, internal reasoning, unresolved alternatives, or question text remains in the artifact.

## Optional renderer iteration

This skill does not require image generation. When a caller uses the prompt with an image tool:

1. Send only the validated prompt and the caller's chosen settings.
2. When references are used, attach only the images listed in `REFERENCE MAP`, preserve their mapping/order, and do not add an unmapped reference.
3. Omit image references when the caller requested a from-scratch prompt.
4. Treat an HTTP 400 or other generic failure as an observed failure, not a known diagnosis; report only the visible response.
5. Change one evidence-based variable at a time: panel density, layout clarity, camera complexity, text amount, reference mapping clarity, or a contradictory style cue.
6. Do not solve a failed render by adding arbitrary retries, a giant negative prompt, or unrelated detail.
7. Inspect the result for panel count, reading order, legibility, story progression, character continuity, camera intent, time labels, requested medium, exact character count, and source-to-target reference ownership.
8. Treat a polished single illustration, merged grid, missing final beat, identity or wardrobe crossover, or continuity break as a visual failure even when the image is attractive.
9. Keep the written prompt unchanged unless the caller asks to revise it; when it is revised, rerun the full quality gate before writing the replacement artifact.

## Companion files

The main `SKILL.md` owns the complete storyboard interface and canonical prompt order. Read this companion only when the current input contains one or more visual references:

- [Multi-Reference Mapping](./references/MULTI-REFERENCE-MAPPING.md) — stable reference labels, role and attribute ownership, preserve/change boundaries, multi-character mapping, conflict resolution, anti-hallucination checks, and renderer handoff.

Do not require any workspace log, transcript, scratch prompt, generated image, external example, or file outside this skill's companion files to understand or validate the workflow. The companion is conditional and never overrides the current user's written brief.

## Do not

- Do not generate a shot list with no visual storyboard composition when the user asks for a storyboard sheet.
- Do not output multiple unrelated prompt variants by default.
- Do not turn the story into a generic montage or replace the requested ending with a new one.
- Do not invent characters, names, dialogue, props, logos, cultural meanings, or plot events.
- Do not hide timecode or panel-count conflicts; resolve them or ask.
- Do not use a supplied image path as prompt text or silently treat an unclear reference as a clone target.
- Do not refer to multiple images without a stable mapping, assign an attribute to a character without ownership, use vague `combine these images` wording, or transfer incidental people into the final sheet.
- Do not copy a named artist's signature style; describe observable visual properties and make the treatment original.
- Do not overwrite an existing artifact.
- Do not depend on the external example at `_xzy-ai/examples/storyboard.md`, a transcript, a scratch prompt, a generated image, or any other file outside this skill to understand or validate the workflow; supplied image attachments are allowed only when explicitly mapped in the current input.
