# Visual/audio blueprint quality review

Use after drafting **and after revisions**. Read [SKILL.md](../SKILL.md) for the deliverable contract. A syntactically neat timeline is not necessarily an intentional edit. Review the actual input SRT and every major visual/audio decision; do not trust a PASS label written during drafting.

## Source and coverage

- Read the entire SRT; count opening/inter-cue/ending gaps and non-spoken markers. Source cues are locators, never default cut points. Did a sub-second gap become a meaningless separate visual sequence? Did a long gap disappear?
- The first visual sequence starts at the known planned beginning; successive base picture intervals have no accidental gap or impossible full-frame overlap; the last ends at the known endpoint or an explicitly provided duration. A HOLD names the preceding VIS/sequence whose base media continues; NONE identifies the visible screen. Does a valid visual stay active across changes of meaning or sound rather than restart at each beat?
- The SRT remains untouched. Are Narration references **cue numbers/ranges only**, with no duplicated words? Does any field invent speech or treat `♪ ♪` as narration? Are durations and approximate in-cue decisions honest?

## Visual accuracy and comprehension

- Can the editor identify what kind of image is required, what must be visible, why it belongs there, and whether actual location/entity/period is required? Are generic or aged-looking images ever misleadingly presented as actual evidence?
- Does visual order follow viewer knowledge and source chronology? Check reveal points and compare setup/payoff. A late name reveal cannot be spoiled by a premature portrait or text label.
- Are maps, documents, diagrams, captions and subtitles legible together? Is there enough time to inspect complex information? Does the chosen style preserve important text from distracting shake, zoom, grain or overlays?
- Are there repetitive filler shots, mechanical B-roll-to-graphic alternation, excessive cuts, or a succession of unsupported archival demands? Conversely, does a hold last without purpose?

## Audio and connections

- Narration intelligibility wins over music, ambience and SFX. Are musical emotion and accents proportionate to the actual story? Is silence or no music a valid choice in the plan?
- Are source-audio/ambient/music intervals independent from picture and beat boundaries, with no unexplained stops/restarts or assumed on-location recording? If original footage sound becomes PRIMARY, is its actual content/provenance known (or explicitly conditional), and is there an SRT narration gap (or a revised timecoded source for an authorized retime)? Is a `SENSORY_BEAT` a meaningful window inside a continuing picture rather than a forced new shot? Are captured NAT_SOUND and separately added ambience/SFX distinguished, with no duplicated wind/water/bird/impact sound by default? Are SFX rare and motivated rather than added per cut? Is a music-only source cue distinguished from an editorial proposal?
- For each J/L cut (including SOURCE_AUDIO prelap/postlap), what actual scene audio leads/trails, by how much, and across which visual boundary? A voiceover continuing under B-roll is not automatically an L-cut. Does a named bridge actually span the visual cut? Does a match cut have a visible match basis?
- Are any simultaneous images or sound policies contradictory? Did a dissolve specify overlapping visual states, and did intentional full silence accidentally overlap speech?

## Style and pacing

Check the micro (within a visual/audio interval), meso (across several regions) and macro (whole video) rhythm: is density driven by content and user instruction rather than a fixed subtitle cadence? Has explicit direction propagated throughout, including no-music/no-SFX/no-B-roll constraints? If no style was supplied, is the chosen treatment recorded as an inference rather than claimed as the user's preference? For a custom style, does the timeline show where its distinctive choices actually happen, and where it intentionally calms down? If Vox-style animation is requested, does each animated map, chart, cutout, annotation or transition clarify an editorial relationship, preserve attribution/reading time and use defensible cue-level timing rather than invented word sync or constant branded motion?

## Final read-back

Read the saved output file, not only the draft response. Confirm that referenced source paths and local skill reference/example links resolve, IDs and transition references exist, start/end ordering is valid, and visual coverage is continuous. `Visual Sequences` governs picture timing; `Audio Timeline` governs SOURCE_AUDIO and other supporting audio; SRT governs narration words/timing. Cue references and optional narrative-beat IDs must not imply media restarts; summaries must not conflict. Record unresolved source/asset uncertainty rather than fabricate a solution. Do not claim material factual verification from an SRT alone. Return only the actual artifact location and any material limitation.

A useful inspection aid is to compare three locations in the blueprint with the SRT: the first minute (opening and reveal), one middle transition (layer independence), and the ending (non-spoken region). That sample is **not** a substitute for checking the entire sequence.
