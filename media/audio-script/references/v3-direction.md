# Eleven v3 voice-direction boundaries

This is the skill's self-contained Eleven v3 practice reference. It is guidance for **text-only** markup; it does not imply audio was generated or that a tag was validated with a specific voice. No external guide is required to apply it. If platform behavior later changes, verify new claims before making them.

## Direct in this order

1. Keep the meaning and uncertainty of the source. Map the information pivot: setup → contrast → consequence; do not turn a question or attributed claim into an established fact.
2. Keep natural spoken phrasing, sentence boundaries, and context. Match the source language.
3. Use punctuation for ordinary rhythm. An ellipsis can suggest hesitation/weight; it is not a neutral timed silence. Capitals can add focus, but they can also sound like shouting if overused. Quotation marks can emphasize or indicate quotation: preserve actual quoted meaning.
4. Add local audio tags **only** for a missing audible intention. The bundled [ElevenLabs recipes and tag catalog](elevenlabs-recipes.md) groups documented examples, experimental requests, and excluded sound cues. Common narration examples include `[calm]`, `[curious]`, `[deliberate]`, `[quietly]`, `[pause]`, `[short pause]`, `[long pause]`, `[emphasized]`, and `[stress on next word]`. Reactions like `[sighs]` should not be invented for neutral documentary narration. Natural-language tags outside documented examples are experimental until tested.
5. Review the prospective spoken text with tags removed. Does it still make a correct, intelligible statement? Does focus clarify rather than distort it? If an abbreviation or number needs a spoken form, write it in the narration language and keep its exact value and scope.

A prosody plan such as `focus: SATU`, `contour: rising`, `pause before consequence` is **working notation**, not v3 syntax. No documented v3 prompt guarantees exact pitch curves, word-level stress, volume, pace, or milliseconds of silence. The base voice is the strongest constraint; text structure, Stability, and generations affect results. Do not put planning notes, timestamps, SSML `<break>`, scene headers, or source citations inside a segment's fenced input. Audio tags should stay immediately before the passage they direct; there is no universal reset tag.

## Segments and editorial timing

- The reviewed Eleven v3 guidance lists a 5,000-character TTS input limit; that is a platform ceiling, **not** a voice-direction target. The helper groups toward 500 characters and caps segments at 900 by default so a segment stays a short coherent performance beat. It splits at manually authored intonation-paragraph boundaries **within** source blocks; it does not write the performance plan. A large unbroken paragraph must be phrased manually before splitting.
- Score the focus, contour intention, and local change by hand first; use paragraphs to indicate spoken thought units and `<!-- beat -->` only between source blocks at stronger topic turns. The helper removes the beat marker. A source timecode can map to multiple segments; it supplies no sub-block timing.
- Keep the same voice/model/setting in the eventual production unless explicitly changing the narrator. A repeated segment-opening cue can request a similar state; v3 Request Stitching is unavailable, so continuity is never guaranteed across calls.
- A `[long pause]` may vary; an original source interval is an editorial target. Flag likely dense passages in the map. The audio editor aligns accepted takes, inserts exact silence, and checks actual durations after generation.

## Reliability checklist

- Model: use Eleven v3 when generating; Audio Tags are v3 performance directions rather than words to be spoken, but an unsuitable voice may ignore or even speak tags. If this happens, try a compatible voice, move tags closer to the relevant words, or remove competing cues.
- Stability: Creative generally offers more expression but greater hallucination risk; Natural is balanced; Robust is more consistent but less responsive to tags. These are audition choices, not things to paste inside narration.
- Pauses: `[pause]`, `[short pause]`, and `[long pause]` are qualitative. Ellipses, dashes, line breaks, and sentence boundaries also affect phrasing. SSML `<break time="..."/>` is not supported in v3. Use audio editing when a gap must last an exact number of milliseconds.
- Emphasis: prefer a clear semantic contrast, then optionally one capitalized word or phrase; `[emphasized]` and `[stress on next word]` are additional qualitative cues. Neither a capital nor a tag fixes exact stress or pitch.
- Generation: repeated takes vary. Compare takes, check for mispronounced numbers and names, and archive accepted text/settings/audio downstream. This skill does not generate audio, so it cannot verify audible results.
- Long form: do not assume segments remember each other; `eleven_v3` does not support Request Stitching. The input length and sample behavior can change across platform surfaces; keep the bundled conservative length cap and review actual platform limits before an unusually large production.
