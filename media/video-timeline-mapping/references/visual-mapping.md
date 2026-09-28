# Visual/editorial mapping

Read alongside [SKILL.md](../SKILL.md). This is guidance for deciding **what viewers should see**, not for finding or rendering a clip. Interpret the entire narration privately before making local choices. The output remains a visual/audio blueprint, not a second script or an explicit story-outline file.

## Resolve a visual language before assigning cuts

Priority: user instructions and prohibitions → supplied reference → source's subject and emotional/informational demands → audience/platform → neutral content-fitting treatment. Explicitly state when a style is inferred. A talking-head edit might retain known presenter footage, while a tutorial might need a screen recording; neither is assumed merely because someone narrates. An investigative treatment is not automatically ominous. Use only relevant direction, not a fixed shot-length formula.

Style may change visual density, duration, framing, graphic use, movement and transition language. It does not override factual integrity, legibility, or explicit constraints. A vintage-documentary direction can use restrained grain, framing and occasional handheld drift on *clearly illustrative* material; it must not manufacture apparent historical proof or shake readable evidence text. See the [Ames blueprint](../examples/pengkhianat-cia-yang-lolos-hampir-9-tahun.timeline.md) for selective treatment. A slower travel/place study can retain a location view through multiple cues and an actual non-narrated passage; see the [Giethoorn blueprint](../examples/bagaimana-hidup-ketika-kanal-menjadi-jalan-id.timeline.md).

### Prefer moving footage over stills

Unless the user directs otherwise, treat **moving footage as the default picture and a still as something to justify**. Real motion carries depth, scale and life a frozen frame cannot, and a run of stills reads as a slideshow. When two pictures would serve the same line equally well, choose the one that moves. Prefer real footage over an illustration whenever both are available for that line.

Four cases still default to a still or a constructed image, because motion would not serve the reader:

- The material is genuinely static: a document, page, photograph, map, chart, or a screenshot whose whole content is the frame.
- The image must stay readable beyond a glance, and movement would compete with reading time or subtitle space.
- The subject is a past period with no surviving moving record, so an archival photograph is the honest evidence and a staged reconstruction would be a fabrication.
- A diagram, animation or composite is the only way to show an invisible mechanism, a change over time, or a relationship between places.

Treat this as a treatment decision, not an availability claim. Primary footage and media availability must never be assumed, and naming a footage requirement does not license implying that such footage was obtained or exists at the specified place. Keep each requirement marked with its specificity, and record the inference in Editorial Direction when the direction was not supplied.

## Understand beats, then time visual sequences independently

A narrative beat is a change in meaning; it is not the parent of picture or sound. Decide whether the same visual sequence can stay active across several semantic changes, cue boundaries or a switch from narration to original source audio. `VIS-SEQ-###` owns the picture interval; optional `BEAT-###` references describe meaning only. Use `Source Cues: n–m` for lightweight SRT alignment without copying narration. See [cross-layer-sequences.md](cross-layer-sequences.md) for a picture continuing through four beats and an original-sound handoff.

1. What has changed in subject, location, time, action, explanation or viewer knowledge—and does that change actually require a new picture?
2. Can the current image still serve that idea? Will it remain legible long enough?
3. Does a new view increase understanding, establish scale, provide evidence, create warranted contrast or preserve suspense? If not, **HOLD**.
4. What is the least elaborate type that communicates the need? Give the purpose, specificity, and any framing/readability constraints.
5. How will the next visual connect? Are the subject, direction, scale and geography clear?

The taxonomy is descriptive, not a menu that must be exhausted: PRIMARY_FOOTAGE (only when actually provided), BROLL (supporting real scene), ARCHIVAL, STILL, DOCUMENT, SCREEN_RECORDING, SCREENSHOT, GRAPHIC, MOTION_GRAPHIC, DIAGRAM, MAP, CHART, TEXT, UI, ANIMATION, COMPOSITE, HOLD or NONE. Use an appropriate custom label when needed. Do not interpret `BROLL` as a synonym for all narration coverage. Use an INSERT for a short detail within an established setting, a CUTAWAY for a temporary departure from a known primary/establishing view, or a sequence/montage when several short images accomplish one intent; identify returns when relevant.

`HOLD` means the previous visual sequence persists: identify it, its duration and any internal change (e.g. highlighting a mechanism) without falsely implying a new asset/cut. `NONE` means an intentional absence of image; say what the screen actually shows (black, blank background, etc.), for how long and why. An empty field is not `NONE`. When simultaneous elements exist, distinguish the base from overlay(s), including independent overlay start/end and visual hierarchy. If a diagram needs many labels, prefer stepwise reveals over unreadable simultaneity. Text should add identification, a number or comprehension rather than duplicate subtitles.

## Specificity, representation and factual restraint

Choose the strongest specificity the story requires: `EXACT` for an actual item/event; `ENTITY_SPECIFIC` for the correct named person/object; `LOCATION_SPECIFIC` for the real place; `REPRESENTATIVE` when honestly substitutable; `CONCEPTUAL` for mechanisms; `ABSTRACT` when literal imagery is unnecessary. These concern **requirements**, not confirmation that such media exists. State narrative period and location when confusion is plausible. Label representative/illustrative/reenacted images where they might be mistaken for actual events. Do not stage generic archival-looking footage as evidence, invent document content, imply a particular person appears in an anonymous image, or show the answer before the narration reveals it.

Avoid visual rhetoric that distorts neutral facts: an ominous red grade over a person, false violence, a staged government file, or a dramatic soundtrack can imply unsupported guilt. Preserve attribution and qualification for historical claims. If the source itself may contain an unsupported claim, avoid strengthening it visually; note the limitation in Editorial Direction or Unresolved Decisions rather than doing independent research or rewriting the SRT. A documentary-style plan is **not** asset or factual verification.

## Give the picture a reason: B-roll connection classes

Specificity answers *which* image is required. A separate question answers *why this image for this line*: how strongly is the picture connected to what is being said? Judge that connection first, then choose.

| Class | Connection to the spoken line |
| --- | --- |
| **Direct** | The line names something visible; the picture shows that thing. |
| **Suggestive** | The line is about an abstraction; the picture carries it as image, not as fact. |
| **Atmospheric** | The picture carries the mood, setting and period of a place or moment. |
| **Wallpaper** | The connection is only vaguely thematic; the picture is filling the screen. |

Direct is the most common and usually correct choice. Much narration plainly names what should be seen, and refusing to show it is false sophistication that costs comprehension. Suggestive and atmospheric pictures earn their place when the line cannot be shown. Wallpaper is the failure mode to watch for.

**Class is not density.** Naming a class for a picture a sequence already justifies does not license a new picture per line. `BROLL` still must not become a synonym for all narration coverage, and a direct picture earns its place only when the current sequence cannot hold the line.

This axis is **orthogonal to specificity**: a `LOCATION_SPECIFIC` picture can be direct, and a `CONCEPTUAL` one can be suggestive. Record the class inside the existing purpose field as plain wording — "direct illustration of the named object", "atmospheric, illustrative, not evidence of the event" — not as a new required field or a label set the blueprint contract does not define.

**Wallpaper is the diagnostic.** Ask of any B-roll: *if this picture were removed, what would the viewer lose?* If the only answer is "the screen would be empty", it is wallpaper. Then test in order: can the current sequence HOLD, can a diagram carry the idea, or is the image genuinely needed? Wallpaper spread thinly across a whole video is worse than a few honest holds, because it converts narration into continuous visual noise and buries the moments that truly deserve a picture. Reserve it for passages with no stronger option, mark it as such, and never use it to reach a target duration.

**Suggestive pictures need a factual guard.** A symbol carries meaning, not evidence. Use one only when the narration itself is figurative or abstract, and state that the image is illustrative. Never let a symbol imply that a real event, person or place occurred: do not cut to doves being released while the narration describes a documented accord, and do not use a symbolic image to stand for a specific site, casualty or decision. If a viewer could reasonably read the picture as proof of the spoken claim, the class is wrong — choose direct, a diagram, or NONE instead.

**Atmospheric pictures are strongest at boundaries.** A new scene, location, time or subject is where a mood picture helps the viewer settle in. Once established, let the direct picture that carries the explanation run, and use atmosphere to reopen a section rather than to fill it.

## Structure without mechanical cutting

Visual progression can move wide → specific → mechanism → consequence, or follow another narrative logic. A map is useful for spatial orientation, a diagram for an invisible mechanism, a document view when source material itself matters. Contrast, parallel editing and before/after are optional structures when they clarify the relationship; do not choose them solely to create activity. Protect graphic reading time and subtitle coexistence. Allow long holds, quiet observation and primary-footage re-entry when useful. If one cue covers multiple concepts but word times are unavailable, use staged internal states or explicitly approximate timing per [input-and-timing.md](input-and-timing.md).

## Example decision checks

- Five place-description cues do not require five unrelated scenic clips. Can one establishing view and an internal detail progression work?
- A diagram explaining a mechanism can remain in place across several cues or narrative beats, changing highlights and even audio emphasis without a cut.
- When access, money and meetings must be compared, hold a readable comparison graphic; a shaken evidence diagram reduces comprehension. Reserve selective motion for less text-heavy illustrative elements.
- If the subject is named only after a pause, avoid an identifying portrait or name label earlier.
- A narration that plainly names a visible object usually wants a direct picture. Check whether avoiding a literal image is costing comprehension before reaching for something more atmospheric.
- A long passage described only in the abstract is a wallpaper risk. Test it with the removal question before assigning a run of scenic inserts, and consider a diagram or a HOLD first.
