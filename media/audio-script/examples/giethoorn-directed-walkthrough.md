# Full manually directed everyday-life example: Giethoorn canals

This complete eight-minute example is a **voice-direction exercise**, not independently verified research. The copied Indonesian transcript-derived narration contains claims about the village's origin, population, bridges, tourism history, and visitor totals that require upstream verification before publication. Do not use direction to make a qualified claim sound certain.

Read the bundled files in order:

1. [Full SRT timeline](giethoorn-full.srt) — a copy of the manually authored 102-cue subtitle timeline (100 short spoken cues and two visible `♪ ♪` video-track cues). The hook and subject introduction are separate cues.
2. [Full hand-directed working draft](giethoorn-full.work.txt) — every spoken cue has its own anchor; local focus and delivery are written manually. `<!-- beat -->` marks a few meaningful topic changes, not one per cue.
3. [Complete `.voice.md`](giethoorn-full.voice.md) — 15 short Eleven v3 segments, with the author's manually directed utterances intact. No source timecodes or `♪ ♪` enter TTS.
4. [Complete `.voice.map.md`](giethoorn-full.voice.map.md) — source passage mapping, editorial checks, and the two unvoiced video-track intervals.

## Hand-scored direction plan

| Narrative movement | What should land | Why the direction changes |
| --- | --- | --- |
| Introduce Giethoorn | The opening's lack of a **JALAN RAYA** is a curiosity hook, then the name and location return to matter-of-fact delivery. | Avoid turning a hook into a blanket claim that no part of the wider village can have roads. |
| Origin story → landscape mechanism | The source says **menurut sejarah**: keep that qualification audible. Let **GAMBUT** become the focus before explaining how excavations and canals relate. | Emphasis should help the listener understand the physical mechanism, not certify a possibly disputed legend. |
| Scenery → movement | Pretty gardens and bridges are context; the practical distinction is that **KANAL** and paths are the main routes **in the historic part**. | Hold before the contrast, but preserve the source's narrower geographic scope. |
| Tourism → local residents | Explain the growth of visitor services, then shift to concerns about privacy and noise before the business response. | No invented residents' dialogue, cheering, or tourist sounds. |
| Warm season → frozen canals → crowded holidays | Use clear seasonal turns; a cold-enough winter can make boats unusable. Keep the last visitor figure qualified as **menurut data yang ada**. | Do not promise freezing every winter or turn the visitor estimate into an exact current census. |

The text-only helper reports no detected spoken-word changes and no approximate-rate warnings. It does **not** verify the transcript's facts, guarantee a recorded duration, or create performance choices. Paragraphing and local tags were written manually first; only then were authored passages separated into segments. Study the complete draft to see why some clauses are untagged while informational turns receive local direction.

Rebuild the pair only after inspecting existing files:

```bash
python3 <skill-dir>/scripts/build_voice.py <skill-dir>/examples/giethoorn-full.srt <skill-dir>/examples/giethoorn-full.work.txt --force
```
