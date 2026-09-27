# Built-in editing styles and custom style design

This is a **skill-owned editorial style library**, not a collection of asset packs or separate software skills. Read [SKILL.md](../SKILL.md) first. Style is a set of visual/audio *decisions*, not a fixed number of seconds per shot. Apply explicit user direction first. When no style is provided, infer a neutral content-fitting treatment and say so; do not silently pick any named preset. A custom style can combine or depart from every pattern here.

## Style dimensions

Record only dimensions that affect the plan: visual tempo and hold length, primary-footage presence (only when supplied), supporting-footage density, graphics/text load, camera/motion language, music role, ambience prominence, SFX density, silence, transitions and evidence/disclosure policy. Do not invent exact shot-length or SFX-count rules; choose picture/audio interval durations from source meaning, readability and platform needs.

| Starting pattern | Visual language and pacing | Audio and transitions | Avoid |
| --- | --- | --- | --- |
| **Neutral editorial** (fallback, not a mandatory aesthetic) | Clearly motivated visual changes, useful holds, specific support rather than filler; diagrams for mechanisms. | Music optional and unobtrusive, ambience only with environmental purpose, clean cuts. | Automatically covering every line with B-roll. |
| **Observational place/travel** | Location-specific place context (asset unverified), wide → detail, longer views and room for non-spoken observation. | Restrained music; when verified footage carries useful NAT_SOUND, a source-audio sensory window can let place sound lead. | Generic place footage passed off as the named destination; inventing original environmental sound or over-cutting a quiet gap. |
| **Human-centered field documentary** | Daily work and place-specific context, patient sequences about real constraints; authentic subjects only when sources are supplied. | Environmental texture or verified original location sound may persist across practical tasks, music sparse; quiet holds for consequences. | Exoticizing residents, identifying generic people as the cited subjects, staging source reports. |
| **Vintage documentary** | Archival-inspired color/texture, historical maps/documents where meaningful, restrained dates and illustrative framing. Sparse, localized handheld motion can intensify *selected* moments. | Low music/pulse and selective silence; cuts and visual callbacks over decorative wipes. | Treating fake aged footage as real archival evidence; shaking dates, documents or readable subtitles. |
| **Investigative factual** | Reveal control, comparison graphics, legible evidence and attribution. Investigative does not necessarily mean vintage. | Speech-led, restrained suspense, selective drop to no music. | Implying guilt from soundtrack, fabricated evidence or anonymous faces. |
| **Data-led newsroom/geopolitical** | Dated maps and comparison graphics with units, denominator, location and attribution visible. | Neutral bed or no music during dense data; clean changes between distinct comparisons. | Breaking-news urgency, mismatched baselines, invented incident footage or unverified live claims. |
| **Educational explainer** | Concepts progress through labeled stages; hold diagrams while understanding develops. | Low unobtrusive bed if helpful; limited accents at meaningful visual states. | Exceeding subtitle/graphic reading capacity or a cut at each sentence. |
| **Vox-style animation** (opt-in preset) | Explanatory motion chosen for a specific relationship: kinetic type, staged maps/data/diagrams, cutouts, documents, annotations, image treatment or B-roll/graphic composites. Hold when comprehension needs time. See [motion grammar](vox-style-animation.md). | Cue-grounded reveals, motivated visual match/shape/zoom transitions where useful, restrained music/SFX; clean cuts and stillness remain valid. | Copying branding, animating every subtitle/shot, false word-level sync, decorative wipes, unsupported data or unverified imagery. |
| **Talking-head / interview** | Retain *provided* primary footage; use brief cutaways for claims, then intentional re-entry. | Preserve voice continuity, avoid ambient resets on every return. | Assuming presenter footage exists or covering every line. |
| **Tutorial / screencast** | Real screen/process visibility, deliberate cursor/step focus and enough time to follow operations. | Minimal music/SFX around instructions; clear audio. | Decorative B-roll obscuring critical steps. |
| **Fast social / UGC** | Shorter motivated states, concise text and responsive cuts tied to performance; preserve key information. | Rhythmic but speech-safe audio, selective accents, occasional silence for contrast. | Uniform speed, unreadable text, every cut accompanied by a whoosh. |
| **Slow cinematic / reflective** | Longer observation, composition, restrained motion and scale progression. | Ambience and space matter; music/silence may carry a slow arc. | Long empty holds unsupported by the subject or melodrama. |
| **Corporate / product** | Clarity, accurate product/brand identification and process, consistent graphics. | Clean restrained mix, cuts/graphics that clarify rather than impress. | Inventing brand kit, product capabilities or demo footage. |

These are **illustrative patterns**, not exhaustive categories. `Vox-style animation` applies when explicitly requested or clearly indicated by a user-provided reference; it is not the default for all explainers or an obligation to animate the full video. News, comedy, mystery, horror, science, podcast, and bespoke combinations are valid if supported by the brief and source. Genre does not license inaccurate images/audio. A user may say “vintage documentary, but no music,” “investigative, not ominous,” or “fast tutorial with no cutaway”; honor those constraints across the entire timeline.

## Derive a custom style (not a new external skill)

1. Extract stated preferences and prohibitions verbatim into a private checklist: intended viewer experience, pace, visual identity, primary footage, graphics, sound, transitions, platform/aspect ratio, and factual boundaries. Ask when a choice changes the editorial result materially, not for every missing parameter.
2. Infer only missing dimensions from the content. State what is inferred in **Editorial Direction**; avoid invoking a named preset when a simple description is more accurate.
3. Translate vague adjectives into *bounded observable behaviors*: “energetic” might mean momentum from motivated cuts and a music pulse, not shaking every frame; “cinematic” might mean more time on spatial establishing views, not automatic slow motion or music; “vintage” might mean muted palette and archival-inspired graphic framing, not counterfeit archive footage.
4. Map the full SRT with those rules. Put selective deviations at specific VIS-SEQ/VIS/audio IDs and defensible times; use BEAT IDs only if an optional narrative index exists. Decide what remains stable (e.g. titles and evidence text) when motion is added.
5. Run a whole-video style pass: are visual tempo, audio density, transition grammar and quiet sections coherent? Do other dimensions undermine the user’s goal or narration intelligibility? Revise decisions, not the source words.

### Worked custom-style translation

Brief: “A vintage documentary about Ames, with a little shaky effect in a few beats so viewers feel adrenaline.”

- Global: archival-inspired color/grain/framing on designed imagery, **not** an assertion of real archival footage.
- Motion: a few bounded, subtle handheld drifts on illustrative layers tied to meaningful source events; date cards, source labels, maps and evidence text remain steady.
- Sound: restrained pulse under selected moments, speech always clear; no fake surveillance Foley or explosive impact cues.
- Pacing: allow evidence diagrams to hold and qualifications to breathe; adrenaline is variation against stability, not constant frantic cutting.
- Apply to the [complete Ames blueprint](../examples/pengkhianat-cia-yang-lolos-hampir-9-tahun.timeline.md). Giethoorn's [place-oriented plan](../examples/bagaimana-hidup-ketika-kanal-menjadi-jalan-id.timeline.md) demonstrates that another input calls for different visual/audio choices.

Additional complete demonstrations: [water-cycle science explainer](../examples/clouds-have-water-why-doesnt-it-always-rain.timeline.md), [Hormuz data-led newsroom treatment](../examples/kenapa-satu-selat-bisa-mengguncang-ekonomi-dunia.timeline.md), and [Mawsynram human-centered field documentary](../examples/hujan-melimpah-kenapa-desa-ini-bisa-kekurangan-air.timeline.md). Each is paired with an SRT of the same stem in `../examples/`; inspect the full input before copying an editorial technique.

To develop a new reusable style **within this skill**, add a short pattern with its visual/audio behavior, failure mode and an example that shows when it applies; do not make another dependency or alter the output contract. For a one-off custom brief, simply record the resolved direction in that project's blueprint—no new style file is necessary.
