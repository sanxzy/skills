# ElevenLabs Eleven v3 recipes and audio-tag catalog

This is a **self-contained catalog of the named v3 tag examples covered by this skill's voice-direction material**, not a closed list of every tag Eleven v3 will ever accept. Eleven v3 interprets square-bracketed natural-language cues in the TTS input. Results depend on the chosen voice, context, Stability, and the individual generation. A tag being documented as an example does **not** promise that every voice will follow it or that its effect has a fixed strength, duration, or scope. The skill does not generate or audition audio.

**Status key:** **D/V** = the cue or category appears in ElevenLabs v3 examples, but audible response varies; **E** = descriptive/experimental, officially labeled experimental, or not established as a standard enumerated example. The categories overlap: one cue may affect emotion, rhythm, and intensity at once. Brackets in the tables are *literal tag spelling* unless a row says it is a placeholder.

## Quick selection recipe

1. Start with the narration's meaning, language, and [style recipe](style-recipes.md); identify a single information focus where needed.
2. Let normal punctuation and phrasing carry routine delivery. Use **one** tag from the relevant category at a meaningful pivot; use a second only for a distinct audible dimension (e.g. `[nervous][quietly]`).
3. Place tags immediately before the words they should affect, or after a line for a reaction. No v3 tag has a guaranteed closing/reset syntax; explicitly re-establish a new state when direction changes.
4. Keep performance compatible with factual scope. Do not use crying, laughter, sinister sounds, or shouting just to make a neutral documentary claim more engaging. Do not invent speaker turns or dialogue.
5. Ask the audio producer to compare takes with the chosen voice. Remove tags that are ignored, spoken aloud, or too theatrical. The `.voice.md` output remains text-only.

## Documented v3 tag examples (D/V)

| Family | Literal examples | What they can request / when to consider them |
| --- | --- | --- |
| Emotion and attitude | `[happy]` `[happily]` `[sad]` `[angry]` `[curious]` `[excited]` `[crying]` `[sarcastic]` `[sarcastically]` `[mischievously]` `[calm]` `[nervous]` `[worried]` `[upset]` `[annoyed]` `[frustrated]` `[sorrowful]` `[playfully]` `[surprised]` `[awe]` | A local emotional turn warranted by the spoken content. `[crying]` is a performance direction, not permission to add a character event. |
| Neutrality, restraint, and manner | `[flatly]` `[deadpan]` `[understated]` `[deliberate]` `[casual]` `[questioning]` `[tired]` `[hesitant]` `[dramatically]` | Manner rather than a numerical acoustic setting. Prefer restrained cues for explanatory narration and use dramatic cues only if the brief and facts justify them. |
| Loudness / vocal mode | `[whisper]` `[whispers]` `[whispering]` `[shouts]` `[shouting]` `[booming]` `[quietly]` `[loudly]` `[softly]` | Qualitative delivery, not decibels or guaranteed whisper/shout. Match the base voice to the requested range. |
| Pause and flow | `[pause]` `[short pause]` `[long pause]` `[continues after a beat]` `[breathes]` | Beats and phrasing, **not** exact silence duration. A pause may color the surrounding sentence. |
| Pace and speech behavior | `[rushed]` `[slows down]` `[slowly]` `[deliberate]` `[rapid-fire]` `[stammers]` `[drawn out]` `[repeats]` `[timidly]` | Qualitative pace/rhythm or manner, not a words-per-minute target. Do not use `[repeats]` to fabricate words or facts. |
| Emphasis | `[emphasized]` `[stress on next word]` `[understated]` | Direct attention to a chosen focus; capitalization, quotation marks, and semantic contrast can also help. Exact stress strength is unavailable. |
| Vocal reactions | `[laughs]` `[laughs harder]` `[starts laughing]` `[wheezing]` `[sighs]` `[sigh of relief]` `[exhales]` `[clears throat]` `[snorts]` `[gulps]` `[gasps]` `[swallows]` `[light chuckle]` `[giggle]` `[big laugh]` `[coughing]` | May emit a reaction or color nearby speech. `[giggle]` and `[big laugh]` appear in a comedic example, not as tested documentary cues. For this skill, use only if genuinely part of the requested performance; never invent a person's reaction as fact. |
| Turn-taking (dialogue only) | `[interrupting]` `[overlapping]` `[cuts in]` `[interjecting]` `[beginning to speak]` | Directions for real multi-speaker material; irrelevant to the default single narrator. They do not guarantee sample-accurate overlap. |
| Named accents | `[British accent]` `[Australian accent]` `[Southern US accent]` `[American accent]` `[Irish accent]` `[French accent]` | Change requested delivery, **not** the language or words. Authenticity and response depend on the voice. Do not add an accent because a place is mentioned in narration. |
| Character / genre performances | `[pirate voice]` `[evil scientist voice]` `[childlike tone]` `[robotic tone]` `[fantasy narrator]` `[classic film noir]` | Character performance options illustrated in v3 material; generally unsuitable for a factual documentary unless explicitly requested and auditioned. These are not a shortcut to a particular person's voice. |

A few examples appear in different official v3 articles rather than one common registry; **D/V** describes their appearance as examples, not an API enum or a promise of cross-voice consistency. `[happily]`, `[worried]`, `[upset]`, `[annoyed]`, `[booming]`, `[coughing]`, and `[beginning to speak]` are illustrated in the Audio Tags overview; their inclusion does not make them all appropriate for documentary voiceover. In the precision-delivery article, descriptive compound cues such as `[quietly, after a pause]`, `[angrily, fed up]`, and `[suspicious tone]` appear **inside illustrative examples**; treat them as voice-dependent experiments, not independent guaranteed pause or emotion controls. Prefer the simpler documented cue if it achieves the same effect. Pronunciation IPA `/.../` is **not** an audio tag; it is a separate pronunciation technique that requires testing with the selected voice.

## Practical usage from the Audio Tags overview

- **Inline scope:** a tag is a bracketed performance cue beside the relevant words, not a stage direction to be spoken. Put a new cue at the actual turn, including mid-sentence if the delivery genuinely changes; two compatible cues can be adjacent. The article demonstrates `[tired]` before a setup and `[upset]` before its emotional turn. Do not assume a tag persists or resets with mathematical precision.
- **Text before tags:** punctuation and capitalization matter even without tags. Commas guide ordinary phrasing; an ellipsis may trail off or imply hesitation; a line break can give a larger beat; ALL CAPS may emphasize one focus word. Preserve the input's claim and avoid making every sentence sound like a reveal.
- **SSML analogies, not equivalents:** `<break>` maps loosely to `[pause]`, an ellipsis, or a line break; rate to `[drawn out]` / `[slowly]` / `[rushed]`; emphasis to a focus word or `[emphasized]`; high/low pitch to emotional impressions such as `[excited]` or `[softly]` / `[sorrowful]`. Eleven v3 does **not** support SSML break tags or numerical SSML pitch/rate controls via these analogies. `[shouts]` can create strong emphasis, but use it only if shouting is actually wanted; capitalizing a focus word is usually less disruptive for factual narration.
- **If a tag is spoken aloud or ignored:** first confirm the production uses Eleven v3. Then check whether the base voice conflicts with the cue (for example, a naturally quiet voice repeatedly asked to shout), simplify conflicting tags, and audition another take or suitable voice. This is an audio-production check, not something this text-only skill can certify.
- **UI and API:** inline v3 tags are illustrated for both interfaces; the skill outputs plain text usable in either, but does not send requests. Do not treat the article's broad cloning or availability statements as a current guarantee for a particular voice or account.

## Experimental / descriptive requests (E)

ElevenLabs describes tag discovery as open-ended, but it does not publish a complete, universally reliable enumeration. The following either appear in an explicitly experimental context or are natural-language directions used as *tests*, not established universal controls:

| Type | Examples | Important limit |
| --- | --- | --- |
| Officially labeled experimental | `[sings]` `[woo]` `[fart]` | Test thoroughly; none belongs in ordinary documentary narration. |
| Accent placeholder, **not literal syntax** | `[strong X accent]` | Replace `X` with a real accent description and audition; the strong variant is experimental and may be unreliable. Never paste the literal `X` as a production direction. |
| Descriptive emotion / progression | `[thoughtful]` `[serious]` `[mysterious]` `[determined]` `[restrained]` `[steadier]` `[controlled]` `[disbelief]` `[voice breaking]` `[dramatic]` | May work in context, but are not guaranteed standardized controls. Use only when the script warrants that reading; audition or fall back to plain phrasing. |
| Descriptive pitch impression | `[deep voice]` | Treat as a voice-dependent qualitative experiment; it does not set an exact pitch. Selecting a suitable voice usually matters more. |
| Prosody labels that are **planning notation, not validated controls** | `[rising]` `[falling]` `[pitch +20%]` `[pause 1.75s]` | Do not put these in production text as though they were documented v3 pitch or timing operators. Use natural sentence type, punctuation, or editing after generation. |

This distinction is intentionally conservative: a cue can be *plausible* without becoming a dependable parameter. If a user requests a custom style, describe its audible goal first and choose the smallest plausible cues; mark untested tags as experiments.

## Sound-related tags: known examples, **not for this skill's `.voice.md`**

Eleven v3 material also illustrates `[gunshot]`, `[applause]`, `[clapping]`, and `[explosion]` as sound-related cues. They are not guaranteed sound-effect production tools and should **not** be added to documentary narration by `audio-script`. Create sound effects separately in the video/audio editing workflow. Likewise, a source `♪ ♪` means **video-track music/SFX placement only**: keep it in the anchored working draft for mapping, exclude it from all TTS segments, and record its timecode only in `.voice.map.md`.

## Precision-delivery decision guide

ElevenLabs' precision-delivery article groups useful controls by **what must change in the sound**, not just by emotion. Apply this as a listening plan, not as an exact timing engine:

| If the line needs… | Try first | If still missing | Documentary safeguard |
| --- | --- | --- | --- |
| A processing beat | A sentence boundary or paragraph break | `[pause]`, `[short pause]`, or `[continues after a beat]` | No tag promises an exact gap; use the editor for exact placement. |
| Calm, intentional weight | Keep natural speech and isolate the key clause | `[deliberate]` or `[slows down]` by the clause | Slower must not imply unsupported gravity or certainty. |
| Forward momentum | Short, clear clauses | `[rushed]` or `[rapid-fire]` only where urgency is real | Maintain intelligibility and do not force a dense factual list through a short interval. |
| Human hesitation | Meaningful punctuation, if hesitation is actually intended | `[hesitant]`, `[stammers]`, or `[drawn out]` | These can imply uncertainty, fear, or a character's behavior; do not fabricate it for an attributed claim. |
| One meaningful focus | Rewrite the contrast in the narration's own words | Capitalize one word/phrase or use `[stress on next word]` / `[emphasized]` | Check that the new emphasis does not invert a qualification. |
| A reaction after speech | None unless the speaker/brief calls for it | A local `[sighs]`, `[exhales]`, `[laughs]`, etc. after the line | A reaction is a *new audible event*; do not add it as decorative filler. |

The official article illustrates that `I'm fine.`, `[flatly] I'm fine.`, and `I'm fine. [pause] really!` can invite different readings despite nearly the same words. A useful habit for this skill is to mark **where a phrase should land** (focus and beat), then choose a minimal tag. Place timing cues next to their passage; layer distinct cues only when a single cue fails. If an example contains `[repeats]`, actual repeated words, or stretched spellings (`Soooo`), do not imitate that in an informational script unless those words are truly meant to be spoken. **Exact pause duration, frames, pitch, and word-level timing are not guaranteed by tags**, even when promotional prose calls the result “precision” or “frame-by-frame.”

## Short, reusable patterns

These demonstrate markup, not historical facts or exact audible results. Copy **only** the directed speech when adapting a pattern; use the source script's actual words and constraints.

- **Calm → informational pivot:** `[calm] Perahu itu tiba pada pagi hari. [pause] [deliberate] Tetapi belum ada jadwal untuk perjalanan berikutnya.`
- **Quiet emphasis, not volume:** `[quietly] Hanya SATU jalur yang masih dapat dilalui.` Capitalization is a focus cue; avoid stacking `[shouts]` and exclamation marks on it.
- **Question → answer:** `[curious] Mengapa perjalanan ini perlu waktu lebih lama? [pause] Rutenya bergantung pada cuaca.` Never supply an unsupported answer just to complete the pattern.
- **Optional reaction (only if actually requested):** `[sighs] Baik. Kita coba lagi.` Do not attach a performed sigh to a factual quotation without permission.

For baseline performance and custom-style construction, use [style-recipes.md](style-recipes.md). For limits on segmentation, Stability, timing, and text-only output, use [v3-direction.md](v3-direction.md). Both are bundled in this skill; no outside documentation is required at runtime.

Source notes (optional provenance, **not** required to use the skill): ElevenLabs, [“What are Audio Tags? The complete guide to emotional TTS”](https://elevenlabs.io/blog/v3-audiotags) and [“Eleven v3 Audio Tags: Precision delivery control for AI speech”](https://elevenlabs.io/blog/eleven-v3-audio-tags-precision-delivery-control-for-ai-speech). The articles contain inconsistent lifecycle/clone phrasing (including research-preview wording in one); do not treat it as a current account-level guarantee. Claims about “full control,” “exactly as planned,” or “frame-by-frame precision” are promotional language, **not** a documented sample-accurate control interface.
