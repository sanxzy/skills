# Structural Clothing Language

This document defines the future-only wording boundary for `character-design` prompts and examples.

It is a companion rule, not a second creative brief. The current user brief remains the primary source of visual intent, and `SKILL.md` remains the authoritative workflow and output contract.

## Core rule

This is an output-only vocabulary boundary. The user's input brief and source context may contain any terms; read them faithfully and do not reject or sanitize the input solely because of its wording.

Do not name any clothing category—intimate or ordinary—in a generated image prompt or generated Markdown artifact. Translate the user's intended design into neutral, concrete visual language instead.

Preserve the design, not the category label. A compliant translation must still communicate:

- visible appearance and silhouette;
- shape and coverage;
- fit, support, tension, and movement;
- construction, panels, seams, edges, and closures;
- materials, opacity, texture, and finish;
- connections between parts;
- front, side, and rear geometry;
- layering and the relationship to the body;
- color, pattern, branding, and other user-approved identity details.

This rule applies to every clothing genre and style, not only adult fashion. It is a future-only output rule: do not preserve old category wording for compatibility with prior artifacts.

## Detection-only vocabulary

The following list is for recognizing wording that must be translated. It is not output vocabulary. Never copy these terms into a generated prompt, generated artifact, or grounding example merely because they appeared in a source brief.

### Category labels that require structural translation

- intimate or revealing garment labels, including terms such as `lingerie`, `bra`, `bralette`, `bikini`, `brief`, `thong`, and `G-string`;
- ordinary garment labels when the output contract requires structural wording, including terms such as `shirt`, `jacket`, `coat`, `dress`, `skirt`, `trousers`, `pants`, `shorts`, `uniform`, `jumpsuit`, `suit`, and `swimwear`;
- named accessory or footwear categories when a concrete body-region description would communicate the design more precisely.

### Framing and content language that requires neutralization

- sexualized or erotic framing;
- wording that presents the subject as an object rather than describing the design;
- explicit sexual acts or fetish framing;
- age-ambiguous descriptions paired with revealing or minimal-coverage apparel;
- suggestive pose labels that do not explain the visible movement or garment behavior.

Detection is not limited to these examples. Recognize synonyms, inflections, euphemisms, translations, and equivalent wording.

## When to replace wording

Replace a source term when any of the following is true:

1. It names a clothing category instead of describing what is visibly constructed.
2. It could cause an image model to interpret the request as explicit adult content rather than apparel design.
3. It describes a sexualized pose, framing, or activity instead of a production or fashion direction.
4. It hides important construction information such as coverage, fit, seams, support, or connections.
5. The user asks for a future generated prompt or example, even if the source wording is technically accepted by one particular image model.

Keep the original term only in the user's source context when necessary to preserve intent. Transform it in the generated prompt, output file, and image-generation request; never require a transcript or other external record.

Do not ask the user to restate a clear source term just because it needs translation. Ask a question only when the visual design remains ambiguous after the term is decomposed into its physical attributes.

## Required body-region structure

Every generated clothing or dressed-form description uses the generic `OUTFIT DESIGN` heading followed by both of these labels:

### Top body

Describe everything from the waist upward. Include the details that are visible and relevant:

- the outer silhouette and upper-edge shape;
- front coverage and rear coverage when visible;
- neckline, shoulder, side, or back geometry without relying on a category label;
- straps, bands, sleeves, panels, supports, closures, and connecting elements;
- fit at the chest, ribcage, shoulders, and waist;
- seam placement, reinforcement, layering, and tension;
- fabric, mesh, leather, knit, metal, or other materials;
- opacity, translucency, sheen, texture, and edge finishing; preserve a safe user-approved value unless the conditional neutral-renderer rules require an opaque alternative;
- how the upper construction moves with the body.

Use precise physical terms such as `contoured front panels`, `broad upper coverage`, `narrow shoulder connections`, `reinforced side seams`, `layered outer panel`, or `structured support` only when those details match the user's intent.

### Lower body

Describe everything from the waist downward. Include the details that are visible and relevant:

- waistline shape and height;
- front coverage panel and its boundaries;
- hip contour, side connections, and leg openings or hems;
- rear construction and attachment geometry;
- fit at the waist, hips, seat, thighs, knees, and ankles;
- seams, gussets, closures, reinforcement, and movement allowance;
- material, opacity, sheen, stretch, texture, and edge finishing;
- how the lower construction behaves during walking, posing, or action.

Use precise physical terms such as `smooth front panel`, `curved hip edges`, `narrow side connections`, `slim rear panel`, `high waist`, `tailored lower-body layer`, or `controlled lower-body coverage` only when those details match the user's intent.

For a non-human character, robot, creature, or abstract form, use the same labels to describe the upper and lower form construction. Do not force human garment language onto a subject that does not wear clothing.

## Translation method

Use this sequence for every future prompt:

1. **Capture the source intent.** Record the subject's age boundary, purpose, pose, silhouette, color, material, coverage, fit, and any cultural or brand constraints before rewriting.
2. **Identify the visible parts.** Separate the design into upper-body and lower-body regions, then identify panels, layers, edges, openings, seams, supports, closures, and connections.
3. **Describe geometry and behavior.** State how each part is shaped, where it begins and ends, how it fits, how it connects, and how it moves.
4. **Preserve material and finish.** Retain the user's fabric, surface, opacity, stretch, sheen, texture, color, pattern, and hardware choices.
5. **Neutralize only the risky wording.** Replace the category or framing label, not the underlying visual information. Keep the tone professional, editorial, commercial, technical, or narrative according to the brief.
6. **Reassemble the prompt.** Place the result under `OUTFIT DESIGN`, `Top body`, and `Lower body`, then carry the same construction into the hero, turnaround, pose, and detail panels.
7. **Check fidelity.** Compare the rewritten description against the source intent. If coverage, shape, material, fit, or connections were lost, restore them with concrete language rather than reverting to the category label.

## Translation patterns

These are patterns, not fixed templates. The source terms in the left column are detection-only and must not appear in output.

| Source wording to detect | Structural output strategy |
|---|---|
| An upper-body category label | Describe the visible upper silhouette, front and rear coverage, upper edge, shoulder or side connections, support, seams, closures, material, and fit under `Top body`. |
| A lower-body category label | Describe the waistline, front panel, hip shape, side connections, rear construction, leg openings or hem, material, coverage, and movement under `Lower body`. |
| A one-piece or continuous category label | Describe the continuous upper-to-lower silhouette, waist transition, panel boundaries, closure path, material, and fit across both body-region sections. |
| A layered outerwear category label | Describe the length, opening, overlap, collar or upper edge, sleeve or arm construction, hem, closures, lining, drape, and movement as upper or lower layers. |
| A revealing or minimal-coverage category label | State the intended coverage geometrically: the front panel shape, side width or connection, rear panel shape, edge placement, support, opacity, and material behavior. Keep age handling internal and use a neutral subject noun in output rather than an age label. |
| A sexualized pose or mood label | Describe the observable stance, weight shift, hand placement, gaze direction if applicable, camera relationship, garment movement, and professional editorial or performance intent. |

Do not use a generic replacement such as `fashion outfit` when the source provides more information. The output must remain drawable and production-useful.

## Age-token output policy

Age is an internal safety constraint, not default prompt copy. Generated prompts and artifacts must not add age labels, age numbers, or age disclaimers. This includes detection-only examples such as `18+`, `adult`, `mature adult`, `mature`, `teen`, `minor`, `child`, and explicit age-number phrases. The examples are instruction-only and must never be copied into an output prompt or artifact.

Use a neutral subject noun such as `woman fashion figure`, `man fashion figure`, `person`, `figure`, or `feminine-presenting figure` when appropriate. Never replace a forbidden age token with childlike, teen, school-age, youthful, or otherwise age-ambiguous wording.

If the source requires a safety-critical age distinction that cannot be represented without an age label, ask one clarifying question through the skill's question flow or stop before writing. Do not silently emit the forbidden label. Keep poses, camera, mood, and construction focused on professional design intent, and do not add sexual activity, fetish framing, or unrelated erotic detail.

## Intent preservation

Structural translation must be faithful, not evasive. Preserve all visual decisions that the user actually made:

- garment or form silhouette;
- amount and location of coverage;
- fit and support;
- fabric weight, stretch, sheen, transparency, and texture;
- seams, panels, straps, fasteners, and connections;
- color, pattern, hardware, and logo placement;
- the relationship between clothing, body, pose, environment, and lighting;
- cultural, religious, commercial, or narrative constraints.

Do not invent a different garment, add extra layers, change coverage, or make the subject more or less exposed merely because a category term was replaced. If the source does not specify a physical detail, do not fabricate one; ask when it materially affects the result.

If a requested term cannot be represented within the applicable image-generation constraints, retain the maximum amount of neutral, observable design information and state the unresolved limitation when necessary. Do not promise exact wording preservation when the output boundary requires a translation.

## Two-module fidelity check

When the brief calls for a separated upper and lower construction, validate the geometry before writing the prompt:

- the upper and lower modules have independent boundaries and are not merged into a continuous one-piece silhouette;
- the `Top body` description names its upper edge, lower edge, shoulder or side connections, and any visible front/rear geometry;
- the `Lower body` description names its waistline, front and rear panel shape, side connections, and leg openings or hems;
- any request for a smaller module is expressed through width, height, taper, panel footprint, and connection geometry;
- a compact triangular upper design uses short self-contained triangular panels and does not also contain central lacing, a broad center panel, or a long torso extension;
- a narrow lower design uses a raised waistline, slim tapered panel, and narrow side bands when those traits are requested;
- a generic full-coverage workaround is not substituted for the user's separated construction merely because it is easier for a renderer to accept.

Classify a prompt as a fidelity failure when a renderer produces a different silhouette, panel relationship, coverage pattern, or construction category, even if the image is technically polished.

## Output validation

Before writing or sending a generated prompt, verify:

- `OUTFIT DESIGN`, `Top body`, and `Lower body` are present;
- no detection-only category label appears in the generated prompt or example;
- clothing is described through shape, construction, coverage, fit, materials, visible structure, and connections;
- no age label, age number, age disclaimer, or detection-only age token appears in the generated output; use a neutral subject noun and keep any necessary safety decision internal;
- source colors, materials, silhouette, pose, and identity constraints remain intact;
- no sexualized or unrelated framing was introduced;
- the description is concrete enough for an image model to draw;
- unresolved ambiguity is routed to the skill's question flow instead of being filled with assumptions.

The goal is not to make the description vague. The goal is to replace a risky or opaque label with a precise physical description that preserves the intended result.
