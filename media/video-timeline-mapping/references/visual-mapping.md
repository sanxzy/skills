# Visual/editorial mapping

Read alongside [SKILL.md](../SKILL.md). This is guidance for deciding **what viewers should see**, not for finding or rendering a clip. Interpret the entire narration privately before making local choices. The output remains a visual/audio blueprint, not a second script or an explicit story-outline file.

## Resolve a visual language before assigning cuts

Priority: user instructions and prohibitions → supplied reference → source's subject and emotional/informational demands → audience/platform → neutral content-fitting treatment. Explicitly state when a style is inferred. A talking-head edit might retain known presenter footage, while a tutorial might need a screen recording; neither is assumed merely because someone narrates. An investigative treatment is not automatically ominous. Use only relevant direction, not a fixed shot-length formula.

Style may change visual density, duration, framing, graphic use, movement and transition language. It does not override factual integrity, legibility, or explicit constraints. A vintage-documentary direction can use restrained grain, framing and occasional handheld drift on *clearly illustrative* material; it must not manufacture apparent historical proof or shake readable evidence text. See the [Ames blueprint](../examples/pengkhianat-cia-yang-lolos-hampir-9-tahun.timeline.md) for selective treatment. A slower travel/place study can retain a location view through multiple cues and an actual non-narrated passage; see the [Giethoorn blueprint](../examples/bagaimana-hidup-ketika-kanal-menjadi-jalan-id.timeline.md).

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

## Structure without mechanical cutting

Visual progression can move wide → specific → mechanism → consequence, or follow another narrative logic. A map is useful for spatial orientation, a diagram for an invisible mechanism, a document view when source material itself matters. Contrast, parallel editing and before/after are optional structures when they clarify the relationship; do not choose them solely to create activity. Protect graphic reading time and subtitle coexistence. Allow long holds, quiet observation and primary-footage re-entry when useful. If one cue covers multiple concepts but word times are unavailable, use staged internal states or explicitly approximate timing per [input-and-timing.md](input-and-timing.md).

## Example decision checks

- Five place-description cues do not require five unrelated scenic clips. Can one establishing view and an internal detail progression work?
- A diagram explaining a mechanism can remain in place across several cues or narrative beats, changing highlights and even audio emphasis without a cut.
- When access, money and meetings must be compared, hold a readable comparison graphic; a shaken evidence diagram reduces comprehension. Reserve selective motion for less text-heavy illustrative elements.
- If the subject is named only after a pause, avoid an identifying portrait or name label earlier.
