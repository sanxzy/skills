# Neutral Image-Prompt Rules

This rule set records wording that successfully produced a faceless three-panel costume sheet after the renderer reported a possible nudity, sexuality, or erotic-content violation. Apply it conditionally when neutral renderer framing is needed; it does not require a human subject, a faceless treatment, or an opaque material for every character. It complements `structural-clothing-language.md`; it is a reusable rule, not an iteration log. The full character-sheet artifact format is defined by `SKILL.md`; this document supplies only a conditional renderer-specific subset.

Keep the intended visual construction while presenting it as a neutral design artifact:

- use a professional costume-design, wardrobe-study, catalog, or character-reference context;
- describe visible geometry, materials, seams, panels, connections, and proportions rather than category labels;
- keep the pose calm and the framing non-suggestive;
- for sensitive or non-explicit renderer prompts, state that materials are opaque and the presentation is a design study; otherwise preserve the user's safe, resolved material choice;
- preserve the user's colors, accessories, silhouette, and requested faceless treatment;
- avoid words or framing that can make a renderer interpret the request as sexual content.

Neutral wording must not become vague wording. Preserve the physical design with precise construction language.

## Validated prompt sequence

Use this order when writing a renderer-only prompt or a neutral construction subsection. `ASPECT RATIO` is the first section when it is required; the opening context follows it. This is the canonical order for this conditional companion rule, while the full example-compatible character-sheet order is defined in `SKILL.md`.

1. **`ASPECT RATIO`:** State the resolved ratio first when the artifact contract requires it.
2. **Context and presentation:** Use a `fictional costume-design reference board`, `museum-catalog wardrobe study`, or comparable professional context, then state the layout, pose, lighting, and framing appropriate to the brief.
3. **Subject:** Use a neutral figure, creature, object, robot, or abstract-form description appropriate to the brief. Do not emit age labels, age numbers, age disclaimers, or the detection-only vocabulary used by this rule.
4. **Face treatment:** If the brief requests a faceless or masked subject, describe a `smooth matte blank surface` or the resolved mask and keep it separate from the outfit description. If a face is requested, preserve the visible face and relevant expression behavior.
5. **Composition:** Describe the panel count, panel order, dividers, background, crop, scale, and the requested views.
6. **`OUTFIT DESIGN`:** If the subject is dressed, use `Top body` and `Lower body` and describe the visible construction in concrete physical terms.
7. **Materials and finish:** Preserve the user's safe, resolved materials. Use `fully opaque` as the neutral default for sensitive renderer prompts, not as a universal requirement.
8. **`AVOID`:** Keep the list short and factual. Prefer geometry and production constraints over repeated sensitive terms.

Do not pass a visual source through the generator's `references` parameter when the user asks for a from-scratch prompt. Analyze the source separately and author the prompt from the written visual description.

## Structural wording that preserves a separated design

### Top body

Use concrete anchors such as:

- `a separate compact torso module ending at the natural waist`;
- `two rounded symmetrical front sections`;
- `pale-blue edging and scalloped decorative trim`;
- `precise central lacing, narrow shoulder bands, small ribbon ties, and fine side seams`;
- `a pearl collar with a pale-blue bow and small gold heart`;
- `white decorative wrist bands`.

For a smaller upper module, add `two small contoured front panels`, `reduced panel height and width`, `narrow shoulder bands`, `slim side connections`, and `a high lower edge at the natural waist`, then state that the module is fully opaque and presented without anatomy emphasis. For a triangular upper design, replace the generic panels with `two separate small opaque triangular front panels with pointed lower corners`; specify one narrow shoulder strap and one slim side band per panel, optionally one thin horizontal back band, and state that no fabric continues below or between the panel points. Explicitly exclude a center panel, vertical lacing, broad side panels, and a long torso extension. This prevents the renderer from turning a small two-panel design into a corset-like upper module.

These phrases communicate shape, boundaries, connections, and accessories without naming a category.

### Lower body

Use concrete anchors such as:

- `a separate compact waist-and-hip module`;
- `a slightly raised waistline`;
- `an extremely narrow centered rear panel with slim side bands`;
- `a small central footprint and reduced overall width`;
- `delicate decorative side tabs and small pale-blue bows`;
- `matching white leg panels that finish above the knees with scalloped decorative edges`;
- `an intentional small interval between the upper and lower modules`.

When the user wants substantially more of the rear silhouette visible, say that `most of the rear silhouette remains visually unobstructed` and explicitly reject `broad full-width or broad rear panels`. This was the neutral wording that produced the closest successful result in testing.

Do not replace a separated construction with a generic `full-coverage outfit` or another broad category. That workaround passed the renderer but visibly changed the intended design.

## Neutral framing rules

- Lead with design purpose: `costume-design reference board`, `wardrobe study`, `catalog presentation`, or `character concept sheet`.
- Use `calm standing pose`, `straightforward wardrobe-study framing`, `soft even studio lighting`, and `realistic proportions`.
- For sensitive or non-explicit renderer prompts, say `fully opaque materials` in the positive description; otherwise preserve the user's safe, resolved opacity or translucency choice.
- For a faceless or masked subject, describe the face as featureless without describing expressions, seduction, attraction, or sexuality; for a visible face, preserve the requested expressions and identity cues.
- Describe body-region construction, not body-part emphasis.
- Keep the camera focused on consistent front, rear, and detail views rather than glamour framing.
- Do not add suggestive movement, fetish context, erotic narrative, or sexual activity.
- Do not include unrelated negative vocabulary merely to prove that it is excluded; a concise production-oriented `AVOID` list is safer.

## Boundary for explicit-minimal requests

Do not convert a request for near-total exposure of sexual anatomy or a direct intimate-apparel category into an image-generation prompt, even through euphemisms. Keep the source wording in source context only and offer a non-erotic alternative instead.

A safe alternative may preserve the palette, pose, accessories, hair, faceless treatment, and panel layout while changing the construction to:

- opaque, non-transparent upper and lower panels;
- compact but non-explicit coverage described through seams, edges, connections, and proportions;
- neutral catalog or costume-study framing;
- no anatomy emphasis, erotic mood, or suggestive posing;
- a clear request for user confirmation before generating the altered coverage.

Do not claim that euphemistic wording makes near-total sexual exposure safe. The visual intent and framing matter, not only the vocabulary.

## Lexical boundary

This boundary applies only to generated prompts and artifacts. The input brief and source context may contain the user's original terms; interpret them faithfully and translate them at the output boundary.

The following are detection-only concepts. Translate them before they enter an image-generation prompt:

- explicit clothing-category labels;
- sexualized or erotic framing;
- age-ambiguous wording paired with minimal construction;
- pose labels that imply sexuality rather than describing observable posture;
- wording that focuses attention on exposed anatomy instead of the design's geometry.

A structural translation should name the panel, edge, seam, connection, material, position, width, height, and relation to neighboring parts. It should not merely replace a category label with a vague phrase such as `fashion outfit`.

If a user requests a narrower rear construction, use geometry: `raised waistline`, `narrow centered rear panel`, `slim side bands`, `reduced width`, and `unobstructed rear silhouette`. Do not copy the source category label into the output prompt.

## Minimal negative constraints

Use only constraints that protect the requested result. A useful neutral list can include:

- `continuous fabric from shoulders to ankles`;
- `merged upper and lower modules`;
- `any long outer layer`;
- `arm-covering sleeves`;
- `broad full-width or broad rear panels`;
- `see-through surfaces`;
- `overly theatrical posing`;
- `visible facial features`;
- `altered panel order`;
- `missing headpiece, ribbons, or decorative trim`;
- `inconsistent hair or distorted anatomy`;
- `extra limbs, cluttered background, random text, logos, or watermark`.

Positive opaque-material wording should carry most of the safety and visual intent. Do not build a long negative prompt containing every prohibited sexual term.

## Failure and iteration rules

- Treat a renderer guardrail response as evidence about prompt interpretation, not as proof that the visual design itself is invalid.
- If a detailed prompt fails while a harmless control succeeds, isolate wording and complexity rather than changing the design into a different full-coverage form.
- Reframe the positive prompt first: professional design context, opaque materials, neutral pose, and physical construction.
- Keep one hypothesis per revision where possible: context, age wording, material wording, or geometry—not all at once.
- If the renderer returns only a generic HTTP status, record the exact visible response and mark the underlying cause unknown.
- A saved image is not automatically successful. Inspect panel order, face treatment, silhouette, construction, material, accessories, and the requested width or coverage change.
- Preserve meaningful attempts in the caller's own workflow when iteration tracking is requested; this companion file does not require a workspace log or any external record.

## Final validation checklist

Before sending the prompt to a renderer, confirm:

- professional design context appears before construction details;
- no direct category label or sexualized framing is present;
- subject wording contains no age label, age number, age disclaimer, or detection-only age token;
- face treatment is explicit and matches the brief; it is featureless only when faceless or masked treatment is requested;
- `OUTFIT DESIGN`, `Top body`, and `Lower body` are present;
- upper and lower modules are clearly separated;
- the requested width, height, rear geometry, and visible silhouette are described numerically or relationally where possible;
- materials preserve the user's resolved safe choice; use opaque and non-transparent wording as the neutral default for sensitive renderer prompts;
- pose and camera are neutral and production-oriented;
- `AVOID` is concise and relevant;
- no image path is included in the generator's `references` parameter when from-scratch generation is requested;
- the result will be visually inspected after generation;
- the finished prompt is rescanned after all sections are assembled, and no detection-only age token remains in any section.
