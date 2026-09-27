# Manually directed real narration: Tristan opening

These are **manually authored** voice directions on an excerpt copied from the bundled Indonesian Tristan timeline, not a tag-insertion script or a claim that the audio has been auditioned. The original transcript-derived narration may contain unverified claims: this is a voice-direction/format example, **not** verified research. The copied source's spoken words are retained in order.

1. [Manually timed SRT excerpt](tristan-opening.srt) — 22 short cues, including one `♪ ♪` video-track placement cue; the spoken word order matches the longer original transcript blocks.
2. [Complete hand-directed draft](tristan-opening.work.txt) — the 21 spoken cues each have their own anchor; local phrasing, tags, and capitalization were written by hand before grouping.
3. [Copy-ready `.voice.md`](tristan-opening.voice.md) — four short segments retaining the hand-written direction, not a long paragraph with one generic mood tag.
4. [Generated `.voice.map.md`](tristan-opening.voice.map.md) — maps each short source cue back to a voice segment. Cue times are editorial, not measured audio.

## Hand-scored prosody plan (not Eleven v3 syntax)

| Source movement | Pre-focus / focus / landing | Intended contour and delivery | Rendered cue |
| --- | --- | --- | --- |
| Ocean → island silhouette | Establish distance; hold briefly at `Dari kejauhan`; let the visual resolve into `daratan ini`. | Measured → suspended → plain explanation; no stress on every adjective. | `[calm] [deliberate]`, a restrained ellipsis, then `[calm]`. |
| Anonymous island → its name | The buildup ends at **TRISTAN**; the remainder identifies the settlement. | Reveal → falling statement, without shouting. | `[short pause]`, `[deliberate]`, one capitalized name. |
| Distance → cost of reaching it | The figure `2.800 km` is context; the destination is the **6 hingga 10 hari** journey. | Hold at `daratannya`, then land the travel consequence. | `[thoughtful]` near the pivot and a local ellipsis, with no new spoken claim. |
| Empty ocean → inhabited home | Natural landscape first; then people living beneath the volcano. | Calm observation → softer human-scale turn. | `[quietly]` only before the people, not over the whole scene. |
| Visitors → lived experience | Visits are setup; **KEHIDUPAN** carries the central question; challenges close the inquiry. | Explanatory → curious → deliberate landing. | `[short pause]`, `[curious]`, one focus word, then `[deliberate]`. |

Contours here are **intentions**; Eleven v3 does not accept or guarantee an exact rising/falling pitch curve. Read this table before studying the marked draft so the tags are consequences of information flow, not decoration.

## Why this direction is more than `[calm]` on a paragraph

- The setup stays measured; `Dari kejauhan...` holds the visual before its referent, without making every sentence dramatic.
- The reveal `Inilah TRISTAN` gets one deliberate focus. The geography that follows stays explanatory. A later `[thoughtful]` connects the travel distance to its consequence instead of emphasizing every number.
- The next block shifts from empty ocean to the people living there. `[quietly]` marks that human-scale turn, not an invented emotional reaction.
- After the visitor setup, `[curious]` belongs by the **actual questions**, with `KEHIDUPAN` as the informational focus. The final question receives a deliberate landing. No new question or assertion was added.
- A `[short pause]` is an expressive cue, never an exact silence target. `[thoughtful]` is a descriptive, voice-dependent cue that needs auditioning; it is not a guaranteed v3 setting.

The splitter can reproduce these **handwritten** voice and map files from the full hand-directed draft; it does not compose the prosody:

```bash
python3 <skill-dir>/scripts/build_voice.py <skill-dir>/examples/tristan-opening.srt <skill-dir>/examples/tristan-opening.work.txt --force
```

The structural test runs this transformation in a temporary directory and compares the voice/map pair byte-for-byte against the bundled output. For another complete example, use the [full crime walkthrough](crime-directed-walkthrough.md). For the complete 21-minute source, use the manually authored [long-form SRT fixture](../scripts/fixtures/pulau-tanpa-bandara-bagaimana-warganya-bertahan-id.srt) to test coverage and limits. Do **not** treat the old mechanically tagged full-length output as a voice-quality example.
