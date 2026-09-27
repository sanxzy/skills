# Vox-style animation: editorial motion grammar

Read [SKILL.md](../SKILL.md) and [style-library.md](style-library.md) first. Use this built-in treatment **only when requested** (or when a user-provided reference clearly asks for it). “Vox-style” here means explanatory editorial motion in service of a story—not copying Vox branding, typography, palette, templates, signature compositions, or specific sequences. The skill plans motion intent and timing; it does not make graphics, source images, audio or a render.

## Editorial decision first

For each passage ask: what relationship cannot be understood as clearly from an unaltered shot or static hold? Animate **that relationship**—location, movement, scale, chronology, evidence, contrast or a hidden mechanism—then stop moving so viewers can inspect the result. Mix real footage, stills, documents and explanatory graphics when they have distinct jobs. A scene may be fully static or observational when movement adds nothing. Do not use kinetic type, animated arrows or B-roll overlays merely because narration continues.

| Treatment | When it earns screen time | Planning detail to record |
| --- | --- | --- |
| Kinetic typography | A short key number, location, term, phrase or contrast needs emphasis. | A short intentional on-screen label/number (not copied cue text as a narration field), what animates versus holds, and coexistence with subtitles. Do not animate a full transcript. |
| Animated map | Geography, scale, route, boundary or changing area is essential. | Start/end geographic scale, required labels, movement path, marker/boundary accuracy, whether map geometry is conceptual or needs verified source data. |
| Progressive data/diagram/timeline | Comparison, measured change, cause/effect or chronology needs staged comprehension. | Units, denominator, period, attribution, reveal order, reading hold; no invented data or misleading interpolation. |
| Cutout / collage | A **correctly identified** person/object/document must be related to context or compared with another item. | Entity specificity, provenance requirement, layer order and whether movement is illustrative—not evidence that the scene happened. |
| 2D shapes/illustrations | An invisible process or abstract relationship needs a legible visual model. | Required elements, arrows/direction, conceptual scale and which stages remain in frame. |
| Document/image treatment | The actual text/photo/headline or a particular detail matters. | Provenance/representation, highlighted passage, intended crop/push/mask/parallax, readable hold; never forge a document. |
| Callout / annotation | Viewers need to inspect a particular part of real footage, map or evidence. | Base visual, overlay lifetime and emphasis target (circle, underline, box, arrow, dim/blur); avoid hiding context or implying false proof. |
| B-roll + graphics composite | Real-world observation remains valuable while a short label, route, number or mechanism is overlaid. | Independent timing for base and overlay, hierarchy, subtitle safe area and removal point; don't replace every B-roll moment with a new shot. |
| Visually related transition | A meaningful shape, movement, direction, object or scale carries viewers into another idea. | From/to VIS-SEQ IDs, match basis, timing and narrative reason. If a clean cut is clearer, use it. |

## Sync without fabricated precision

Plan entry at a defensible SRT cue boundary when that cue introduces a concept, or mark an in-cue event `~HH:MM:SS.mmm` / `Timing: APPROXIMATE` if the exact word is unknown. SRTs generally lack word alignment; do **not** claim an exact frame where the narrator pronounces a word just because a subtitle cue contains it. Align semantic reveals to source cue numbers, and keep an established graphic visible across later cues or narrative beats. A visual may anticipate or follow a phrase if doing so improves understanding without spoiling it.

A `VIS-SEQ` can hold one base shot or diagram across several conceptual steps; overlays, text, arrows and highlights can start/end independently **inside** it. Describe internal progression rather than creating a fresh sequence for each label. Source audio and music also remain independently timed; motion does not require a whoosh for every graphic state.

## Worked timing sketch (not a sixth full blueprint)

From the bundled [water-cycle SRT](../examples/clouds-have-water-why-doesnt-it-always-rain.srt), cues 27–38 run `00:02:13.000–00:03:15.000`, followed by a 2-second narration gap. For a *hypothetical Vox-style revision* of the [existing educational blueprint](../examples/clouds-have-water-why-doesnt-it-always-rain.timeline.md), one continuous atmospheric diagram could run `00:02:13.000–00:03:17.000`:

- `00:02:13.000` (cue 27): rise into a simple vertical air-column map/diagram; hold geography and axis stable.
- `00:02:34.000` (cue 31): gradually reveal condensation/droplets as the narration moves to the phase change. Keep the vapor-to-droplet distinction clear.
- `00:02:42.000–00:02:55.000` (cues 33–34): a short cold-glass inset may overlay the existing diagram; base remains visible. Do not present the glass as atmospheric footage.
- `00:02:55.000–00:03:17.000` (cues 35–38, then gap): return attention to particle/droplet detail and **hold** the explanatory state long enough to inspect. No sound accent is required on every reveal.

Those boundaries are cue-level anchors, **not** proven word-level synchronizations. The sequence would need no separate cut at every cue. If revising the existing educational blueprint, extend affected VIS-SEQ-006 through 00:03:17.000 and retire VIS-SEQ-007 after carrying its required detail into the extended region; leave unaffected IDs alone. The five bundled blueprints remain distinct style treatments rather than being retroactively forced into Vox mode.

## Restraint and validation

Before choosing an animated treatment, compare it against HOLD, plain footage, a readable static graphic or a simple cut. If motion is selected, verify one main visual question at a time; accurate source attribution; legible text/subtitles/units; enough hold after the animation; restrained transition and SFX density; and quiet real-world passages where viewers can observe. Do not invent primary footage, geographic boundaries/routes, source documents, data, branded design assets or word-level timestamps. Conceptual maps/diagrams are acceptable only when clearly labeled as illustrations rather than asserted geographic evidence. The goal is understanding and rhythm, not constant motion or an imitation of a particular publisher's visual identity.
