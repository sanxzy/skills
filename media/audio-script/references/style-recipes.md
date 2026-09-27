# Style recipes for Eleven v3 narration

Styles here are editorial performance plans, **not ElevenLabs presets or literal `[style name]` tags**. Apply them by manually directing each passage's phrasing, focus, pauses, and delivery—never by assigning one preset tag to every block or generating the marked draft with a script. A requested style or the source script's established voice overrides the default. Keep the underlying factual scope and language. One script may move between recipes as the story changes, but avoid a different baseline voice in every segment. Select a compatible ElevenLabs voice in production; no tag can reliably override a mismatched voice.

| Recipe | Audible goal | Phrasing, focus, and pauses | Candidate local cues (use sparingly) | Avoid |
| --- | --- | --- | --- | --- |
| Restrained documentary (default) | Measured, clear, observant | Plain declarative setup; emphasize the one meaningful contrast; pause only at real turns. | `[calm]`, `[deliberate]`, `[understated]`, `[pause]` | Trailer-like reveals, uniform gravity, capitalizing every statistic. |
| Conversational explainer | Approachable and curious, without sacrificing precision | Short-to-medium thought units; clear setup → contrast → answer; let questions sound like genuine questions. | `[curious]`, `[casual]`, `[pause]` | Implying an unverified answer, overplaying surprise, a chatty aside that adds a new claim. |
| Cinematic documentary | Space and consequence with controlled intensity | Fewer, larger turns; let silence/visual gaps remain for the editor; land verified consequences rather than manufacturing suspense. | `[quietly]`, `[deliberate]`, `[long pause]` | Repeated ellipses, exaggerated threat, shouting, long model-generated pauses as exact time targets. |
| Clear educational | Intelligibility and steady confidence | Give definitions room; group technical lists; emphasize a term when it is introduced; normalize difficult numbers or abbreviations if meaning survives. | `[calm]`, `[stress on next word]`, `[pause]` | Over-tagging every definition, altering units, premature certainty. |

The candidate cues are examples found in the Eleven v3 direction material; results vary by voice and Stability. See [elevenlabs-recipes.md](elevenlabs-recipes.md) for the broader tag catalog and experimental boundaries. `[understated]` and `[casual]` may behave differently across voices. Omit a tag if ordinary phrasing already communicates the intent. Avoid mixing multiple independent emotions on one fact.

## Designing a custom recipe

Write a small performance card **outside** the Eleven v3 text, using the same fields as above:

1. **Audible goal**: what should a listener hear? Describe performance, not a brand/person imitation.
2. **Baseline**: energy, pace, degree of emotional display, language/accent requirements, and the kind of voice likely to suit it.
3. **Information flow**: setup, contrast, pivot, payoff; identify the focus word or phrase only when it matters.
4. **Phrasing**: natural sentence units, intentional processing points, and where a question or conclusion lands.
5. **Local cues**: a short validated tag vocabulary, punctuation strategy, and emphasis strategy. Use experimental natural-language tags only when explicitly requested and label them as untested until auditioned.
6. **Failure signs**: e.g. sensationalized uncertainty, inconsistent narrator identity, spoken tags, unnatural pauses, or a new assertion introduced solely for dramatic effect.
7. **Test line**: a representative excerpt from the actual source, tested with/without direction later by the audio producer; never claim a performance was tested by a text-only skill.

Map the card to the working draft through phrasing first, tags second. Do not put the card or style labels into the final copy-ready text or change a factual statement to force a desired contour. Keep segment-opening cues self-contained where needed: separate v3 requests do not share a guaranteed prosody state.
