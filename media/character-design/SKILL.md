---
name: character-design
description: |
  Create one production-ready, model-agnostic character design sheet prompt from
  a free-form brief and optional visual reference. Use for characters, mascots,
  creatures, factions, branded subjects, anonymous figures, costume studies,
  turnaround sheets, and image-generation prompts.
argument-hint: "Describe the character, subject, purpose, or visual reference."
---

# Character Design

Create one English, production-ready prompt for a composite character design sheet. The prompt is the primary output. Rendering is optional and is never required for this skill to complete.

## Interface

### Input

Accept:

- a free-form brief in any language;
- an optional image or visual reference;
- optional style, realism, face treatment, aspect ratio, purpose, palette, text, branding, and fidelity decisions;
- an optional safe output path.

The user's brief is the source of truth. Input/source wording is unrestricted: read the user's terms as provided and do not reject, censor, or sanitize the brief solely because it contains detection-only vocabulary. The vocabulary restrictions below apply only at the generated-output boundary. Do not invent names, identity facts, cultural meanings, logos, materials, or visual details that materially change the request.

### Output

Return one structured prompt in raw English Markdown and write it automatically after validation. Do not produce multiple variants, a rationale essay, or a fenced code block around the prompt.

The default artifact path is:

`_xzy-ai/outputs/character-design/<slug>.md`

Use a user-supplied path only when it stays inside the active workspace and contains no traversal. Never overwrite an existing artifact; add `-2`, `-3`, and so on when the target already exists.

The default timing is automatic writing after the quality gate. If the user explicitly requests image-first review, defer writing for that run, keep the working prompt transient, and run the same quality gate again after the user approves the image. Renderer approval is never required by default.

The generated artifact is a paste-ready prompt, not a prose report about a prompt. It must visually follow the structure in `_xzy-ai/examples/character-design-sheet.md`:

- begin with a keyword-led opening stack of concise descriptors, one phrase per line;
- use plain uppercase field labels such as `ASPECT RATIO:` and `LAYOUT STRUCTURE:` with a blank line after each label;
- use comma-separated prompt phrases rather than explanatory paragraphs;
- use the example-compatible section order defined in step 8 below;
- do not add Markdown heading markers (`#`, `##`), frontmatter, commentary, rationale, or a second prompt variant to the generated artifact.

Bundled grounding examples live in `references/examples/`. They are optional internal pattern references, not additional briefs. Read `references/examples/README.md` and, when useful, one or two relevant examples to observe the fixed structure, specificity, and layout. The current user brief always has priority: if an example conflicts with the brief, discard the example detail; never copy an example's identity, project, palette, props, text, or story unless the user supplied it. All bundled examples intentionally share the same top-level structure so the agent learns a stable output contract rather than a menu of formats.

### Invariants

Every completed artifact must:

- describe one coherent composite character sheet;
- preserve resolved user decisions and distinguish them from open decisions;
- use English and model-agnostic wording unless a target model is explicitly named;
- include the required sections in the order defined below;
- use concrete construction language for dressed subjects;
- include a concise `AVOID` section;
- contain no unresolved placeholders, contradictions, invented identity facts, or unsafe paths;
- remain understandable without any external log, transcript, example, scratch prompt, generated image, or other file.

## Workflow

### 1. Parse the brief

Extract only facts that are present or clearly requested:

- subject, role, identity, group or faction scale;
- intended use and production context;
- visual style, realism, rendering, and medium;
- face treatment, body or form, pose, and silhouette;
- outfit or surface construction, props, equipment, and markings;
- setting, palette, lighting, camera, mood, typography, and branding;
- visual references and requested fidelity;
- output format, aspect ratio, and technical constraints.

Separate **resolved facts** from **open decisions**. An explicit instruction is resolved and must not be asked again.

Treat age information as an internal safety decision, never as output copy. Never emit age labels, numeric ages, or age disclaimers in a generated prompt or artifact, even when they appear in the brief. Use neutral nouns such as `woman`, `man`, `person`, `figure`, or `feminine-presenting figure` where appropriate. If a safety-critical distinction cannot be handled without an age label, stop before writing instead of emitting one.

### 2. Resolve material ambiguity

Use the question tool for one material question at a time when a missing decision can materially change the result. Offer clear choices and a short recommendation when useful.

Ask before guessing about:

- style or realism;
- face treatment;
- aspect ratio when absent or ambiguous;
- individual versus group scale;
- gender presentation, body type, or other identity-defining details;
- palette, purpose, branding, typography, or logo treatment;
- reference fidelity.

Do not ask the user to repeat a clear source term merely because it needs structural translation.

If a visual reference is supplied and fidelity is not resolved, ask the user to choose exactly one:

- `inspired` — borrow broad mood, palette, or composition while creating a distinct design;
- `faithful` — preserve the main silhouette, proportions, palette, or construction in a new presentation;
- `close` — retain most visible details while adapting the presentation;
- `clone` — reproduce the reference as closely as possible, only after the user confirms authorization to use it.

Do not require a separate discussion skill, transcript, or decision file. If a material decision remains unresolved, stop before writing the artifact.

### 3. Handle visual references

Use a supplied reference to understand composition, silhouette, pose, materials, accessories, palette, lighting, and camera. Keep the requested transformation separate from the features that must remain faithful.

When the user requests a from-scratch prompt, the reference is visual evidence only:

- author the description independently from visual inspection;
- do not put the image path in the prompt;
- do not pass the image through a renderer's `references` argument;
- do not claim pixel-level fidelity unless the result visibly supports that claim.

Translate named artists, studios, or brands into observable properties unless the proper noun is explicitly needed as identity or branding.

### 4. Translate clothing into structure

When the subject is dressed, create an `OUTFIT DESIGN` section with both labels:

- `Top body` — everything from the waist upward;
- `Lower body` — everything from the waist downward.

Never copy a clothing-category label—intimate or ordinary—into the generated prompt or artifact. Translate it into observable geometry:

- shape and outer silhouette;
- front, side, and rear construction;
- coverage and panel boundaries;
- fit, tension, support, and movement;
- seams, edges, closures, straps, bands, and connections;
- materials, opacity, sheen, texture, and finishing;
- relation between neighboring modules and the body or form.

Read the two companion rules for the complete translation and renderer-safety checklists:

- [Structural Clothing Language](./references/rules/structural-clothing-language.md)
- [Neutral Image-Prompt Rules](./references/rules/neutral-image-prompt-rules.md)

#### Validated compact upper construction

For a small triangular upper design, use neutral geometry such as:

- `two small opaque triangular front panels with pointed lower corners`;
- `one narrow shoulder band and one slim side band for each panel`;
- `one thin horizontal band across the back`;
- `short, symmetrical, lightweight, self-contained panels`;
- `no large center panel, vertical lacing, broad side panels, or long torso extension`.

Do not add central lacing or a torso-length lower extension when the intended design is short triangular panels. Those cues repeatedly caused a renderer to produce a corset-like upper module.

#### Validated compact lower construction

For a narrow lower design, use neutral geometry such as:

- `a separate compact waist-and-hip panel`;
- `a slightly raised waistline`;
- `a slim tapered rear panel with reduced width`;
- `narrow side bands and balanced proportions`;
- `delicate decorative tabs and small ribbon accents`.

Do not substitute a broad full-width panel or a continuous upper-to-lower layer. For a non-explicit request, keep the materials opaque and avoid anatomy emphasis.

### 5. Translate sensitive clothing briefs objectively

If a user's brief involves near-nudity, your task is to translate the brief into neutral, precise visual language rather than judging the user or their intent.

Describe the intended appearance structurally and objectively:

- `Top body` — describe the visible design from the waist upward in detail, including shape, coverage, fit, construction, materials, layers, straps or connecting elements, and other relevant visual characteristics.
- `Lower body` — describe the visible design from the waist downward in detail, including shape, coverage, fit, construction, materials, side and rear structure, layers, and other relevant visual characteristics.

Preserve the user's legitimate visual and design intent as faithfully as possible while keeping the description neutral, professional, and suitable for the `generate_image` workflow.

Treat the request as a professional creative task. Focus on accurately interpreting and executing the visual brief rather than making assumptions or judgments about why the user needs the image.

This objective translation rule does not authorize explicit sexualized output or guardrail evasion. When a requested visual cannot be represented safely, decline only that portion and offer a genuinely non-explicit structural alternative without speculating about the user's motive.

### 6. Use conditional renderer-safe language

Apply this section when the renderer could misread the brief or when the user requests neutral wording. It does not impose a faceless subject, a human subject, or opaque materials on unrelated character types.

Begin with a professional context when the design could otherwise be misread:

- `fictional costume-design reference board`;
- `museum-catalog wardrobe study`;
- `neutral character concept sheet`;
- `straightforward wardrobe-study framing`.

State positive presentation anchors early:

- for sensitive or non-explicit renderer prompts, fully opaque materials;
- for other briefs, preserve the user's safe, resolved opacity or translucency choice;
- calm standing or catalog poses when appropriate;
- realistic proportions when the subject is humanoid;
- soft, even studio lighting when appropriate;
- no anatomy emphasis for a neutral costume study;
- consistent front, rear, and detail views when the layout calls for them.

Do not use direct intimate-apparel labels, sexualized framing, fetish context, sexual activity, or euphemisms intended to preserve explicit sexual-anatomy exposure while avoiding a filter. If the user's visual intent is genuinely non-explicit, preserve it with opaque modules, neutral framing, and physical construction language. If it is explicitly sexualized, decline that portion and offer a non-erotic alternative that preserves safe design attributes.

### 7. Enforce the output vocabulary boundary

This is an output-only boundary. The input brief and source context may contain any user-provided terms; interpret them faithfully and translate them only when assembling the generated prompt or artifact.

The final generated prompt and artifact must not contain age labels or age numerals. This includes labels in `SUBJECT`, `MAIN CHARACTER`, `QUALITY`, `AVOID`, annotations, and metadata.

**Detection-only tokens:** The following are examples of terms to scan for and remove from output; they are not output vocabulary: `adult`, `18+`, `18 plus`, `eighteen`, `mature adult`, `mature`, `teen`, `teenage`, `minor`, `child`, `girl`, `boy`, `youthful`, `young`, `age`, and explicit age-number phrases. This list is instruction-only: never quote it, summarize it, or copy it into the final artifact.

Use neutral output wording instead:

- `woman fashion figure`;
- `man fashion figure`;
- `feminine-presenting figure`;
- `masculine-presenting figure`;
- `person`, `figure`, or `character`.

Do not add an age qualifier merely to make a fashion prompt sound safe. If the source requires a safety-critical age distinction that cannot be represented without an age label, ask the user to revise the brief or stop; do not silently emit a forbidden label. Run the scan again after assembling every section, including `AVOID`, annotations, and metadata; if a match remains, revise before writing.

### 8. Assemble the sheet prompt

The generated prompt must follow the example-compatible format, not a prose report. Use plain uppercase labels, a blank line after each label, and short comma-separated prompt phrases. Do not use `#` or `##` heading markers inside the generated artifact.

Before drafting, consult the bundled examples only when the brief leaves the desired presentation format unclear. Select the closest example by medium or use case, then copy its structural pattern—not its content. The user brief remains the sole source of truth for subject, identity, narrative, styling, palette, props, text, and layout decisions.

Use this order unless the user explicitly requests a different non-core layout:

1. **Opening keyword stack** — 8–12 concise descriptors, one phrase per line, with comma separators and an optional comma after the final phrase. Convert the brief's style, purpose, medium, presentation, and finish into this stack. Do not write a paragraph before `ASPECT RATIO`.
2. `ASPECT RATIO:`;
3. `PROJECT:` when supplied, with the project name and tagline only when supplied;
4. `CHARACTER IP DESIGN` — a concise production-purpose line such as `production-ready character IP concept`;
5. `SUBJECT:`;
6. `MAIN CHARACTER:` or `MAIN SUBJECT:`;
7. `OUTFIT DESIGN:` with nested `Top body:` and `Lower body:` labels whenever the subject is dressed or has upper/lower surface construction;
8. `PROPS:` or `EQUIPMENT:` when relevant;
9. `LAYOUT STRUCTURE:`;
10. `VISUAL DETAILS:`;
11. `COLOR PALETTE:`;
12. `LIGHTING:`;
13. `CAMERA:`;
14. `MOOD:`;
15. `LAYOUT:`;
16. `QUALITY:`;
17. `AVOID:`.

The order above is the fixed bundled-example structure: opening descriptor stack, aspect ratio, project, character IP design, subject, main character, outfit, props, layout structure, visual details, color, lighting, camera, mood, layout, quality, and avoid. Do not insert a standalone `GRAPHIC DESIGN LAYER:` block. Put branding, typography, motifs, and graphic identity in `VISUAL DETAILS:` or `LAYOUT:`. Omit only genuinely inapplicable conditional blocks such as `PROJECT:`, `OUTFIT DESIGN:`, or `PROPS:`; never invent content just to fill a label. `LIGHTING:` remains a required block and should use a safe, context-appropriate default when the brief does not specify it.

Use the following formatting rules inside every block:

- keep one descriptor or short phrase per line, with commas where the phrase stack calls for them;
- keep the same top-level labels and order across bundled examples; vary only the user-relevant content;
- use `left panel –`, `right panel –`, and `bottom section:` within `LAYOUT STRUCTURE` when the reference-style split layout is appropriate;
- place hero art, turnaround views, expression or pose studies, action mini-sequences, detail callouts, equipment breakdowns, color swatches, branding, and annotations inside the appropriate layout descriptions instead of scattering unrelated sections;
- use `LAYOUT` for the overall board identity and presentation purpose, while `LAYOUT STRUCTURE` describes the actual panel assignment and reading order;
- do not repeat the same layout sentence in both blocks;
- keep the output as one integrated composite sheet, not a collection of separate prompts.

Keep one integrated composite sheet. The generic default is a contextual hero panel on the left, a clean turnaround or subject sheet on the right, and supporting details in a bottom section. An explicit reference layout or user-requested panel arrangement overrides that default while preserving subject continuity.

For a generic character sheet, include front, side, back, and 3/4 views plus a concise pose or body-language study. If the user explicitly specifies another view count or a reference-based three-panel board, follow that layout.

Add an expression study only when the face is visible. For faceless or fully masked subjects, use gesture, posture, and body-language variations.

Include relevant detail callouts for fabric, form, equipment, props, insignia, or other identity-defining construction. Include only user-supplied or user-approved text and logos; never invent brand text.

### 9. Write the artifact

Before writing:

- resolve all material decisions;
- derive a safe slug from project name, then character name, then `character-design-sheet`;
- verify the path stays inside the workspace and will not overwrite an existing artifact;
- ensure the prompt is raw structured Markdown with no fenced wrapper;
- run the quality gate below.

After the gate passes, write automatically and report the exact path. Aesthetic judgment remains with the user.

## Quality gate

Reject and revise the prompt before writing if any check fails.

### Content and intent

- The brief's resolved subject, purpose, identity, style, palette, pose, and reference constraints are present.
- Any bundled example used served only as a pattern reference; no unsupported example identity, project, palette, prop, text, or story detail was copied.
- Bundled examples and generated prompts use the same stable top-level skeleton; only brief-supported sections and content vary.
- No identity-defining fact was invented.
- No written/reference conflict was silently resolved.
- The requested transformation is distinct from preserved reference features.
- No age label, age number, or age disclaimer appears in the output.

### Structure

- The artifact begins with an 8–12-line keyword-led descriptor stack; no prose introduction, frontmatter, or `#`/`##` headings appear before or inside the prompt.
- `ASPECT RATIO:`, `CHARACTER IP DESIGN`, `SUBJECT:`, `LAYOUT STRUCTURE:`, `VISUAL DETAILS:`, `COLOR PALETTE:`, `LIGHTING:`, `CAMERA:`, `MOOD:`, `LAYOUT:`, `QUALITY:`, and `AVOID:` are present in that order.
- `PROJECT:` is present when supplied and omitted when absent; `PROPS:`/`EQUIPMENT:` appears when relevant; a standalone `GRAPHIC DESIGN LAYER:` block is not used.
- `MAIN CHARACTER:` or `MAIN SUBJECT:` is present and follows `SUBJECT:`.
- `OUTFIT DESIGN:`, `Top body:`, and `Lower body:` are present whenever the subject is dressed or has upper/lower surface construction.
- `LIGHTING:` is always present and contains a resolved, context-appropriate lighting treatment rather than an empty placeholder.
- The block contents use concise comma-separated prompt phrases and blank-line-separated labels rather than explanatory paragraphs.
- `LAYOUT STRUCTURE:` assigns the hero, turnaround, pose/expression, detail, action, equipment, palette, and annotation areas as relevant; `LAYOUT:` states the overall board presentation without duplicating that assignment.
- The layout describes one coherent composite sheet.
- The requested turnaround, detail, pose, or body-language views are achievable and consistent.

### Neutral construction

- No clothing-category label, whether intimate or ordinary, appears in the generated prompt.
- Dressed forms are described through geometry, coverage, fit, construction, materials, seams, and connections.
- Compact triangular panels are not contradicted by central lacing, broad side panels, or a long torso extension.
- Narrow lower construction is not contradicted by a broad full-width panel or a continuous one-piece layer.
- Materials and framing are neutral for a non-explicit request; use opaque materials as the safe default for sensitive renderer prompts unless another safe, user-resolved material is required.
- No euphemistic wording is being used to bypass a guardrail.

### Vocabulary and integrity

- The output contains none of the detection-only age tokens or age-number patterns.
- The output contains no direct intimate-apparel labels or sexualized framing.
- The prompt is English, model-agnostic, concrete, and free of placeholders.
- No external log, transcript, scratch prompt, image path, or outside reference file is required to interpret the artifact.
- No unsupported technical claims, random logos, watermarks, or invented text are requested.
- The `AVOID` section is concise, relevant, and free of sensitive vocabulary.

## Optional renderer iteration

The skill does not require rendering, but when a caller uses the prompt with an image tool:

1. Send only the validated prompt and the caller's chosen tool settings.
2. Omit image references when from-scratch generation was requested.
3. Treat an HTTP 400 response as an observed failure, not a known diagnosis; report only what the tool exposes.
4. Make one evidence-based correction at a time: reduce complexity, remove a conflicting construction cue, or strengthen a missing geometric anchor.
5. Do not use arbitrary retries, a longer negative prompt, age labels, direct category labels, or euphemisms to evade a guardrail.
6. Treat a saved image as provisional until its layout, face treatment, silhouette, construction, materials, accessories, vocabulary, and requested changes are visually inspected.
7. If a result is polished but changes the form into a different construction, classify it as a visual failure and correct the prompt.
8. If the caller explicitly requests image-first approval, keep the working prompt transient, do not write the artifact during review, and write only after approval and a fresh quality-gate pass.

## Companion files

This skill is self-contained. Its instructional dependencies and optional pattern references are shipped inside this skill:

- `references/rules/structural-clothing-language.md` — structural translation and intent-preservation rules;
- `references/rules/neutral-image-prompt-rules.md` — neutral renderer framing and validated construction patterns;
- `references/examples/README.md` — grounding-example usage contract;
- `references/examples/*.md` — complete fictional prompt examples with one identical top-level skeleton, for structure and specificity only.

Do not require workspace logs, discussion transcripts, scratch prompts, generated images, external examples, or any file outside this skill's companion files. Bundled examples may guide form, but they never override the current user brief.

## Do not

- Do not invent names, logos, identity facts, cultural meanings, or reference details.
- Do not ask questions that the brief already answers.
- Do not name clothing categories in generated prompts or artifacts; use structural descriptions instead.
- Do not add `18+`, age numbers, age labels, or age disclaimers to generated output.
- Do not make a full-coverage workaround that changes the user's intended construction.
- Do not encode explicit sexual-anatomy exposure through euphemisms.
- Do not silently copy a visual reference at clone fidelity without authorization.
- Do not use a supplied image as a renderer reference when from-scratch generation was requested.
- Do not produce multiple prompt variants unless the user explicitly changes the output contract.
- Do not overwrite an existing artifact.
- Do not depend on logs, transcripts, scratch prompt files, generated images, external examples, or external skills to understand or validate this skill; bundled examples are optional pattern references only.
- Do not treat a bundled example as a hidden brief or copy its unsupported identity, project, palette, props, text, or story into a user's prompt.
