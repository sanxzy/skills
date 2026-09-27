# Cross-beat picture and original-source audio

Read [SKILL.md](../SKILL.md) and [blueprint-contract.md](blueprint-contract.md). This is a **schematic**, not one of the five complete example pairs and not a claim that archival footage, speech, rights or timed media exists. It illustrates what to specify *if* a verified clip and an SRT with the described narration gap are supplied. Replace cue numbers/times with real ones in a production plan.

## Example input conditions

- SRT cues 41–42 occupy `00:03:20.000–00:03:31.000`; cues 43–44 occupy `00:03:39.500–00:03:47.500`. The SRT contains **no narration** between `00:03:31.000–00:03:39.500`. No spoken cue text needs copying into the timeline.
- A separately provided, accurately identified archival clip has useful original speech. Its contents, date, authenticity, usable duration, rights and any captions/translation must be checked from the actual source. If not supplied, this is an *unresolved requirement*, not ready-to-play footage.

## Independent layers (optional semantic index)

```markdown
## Narrative Beat Index
- BEAT-041 | 00:03:20.000–00:03:26.000 | Establish the subject (no transcript text).
- BEAT-042 | 00:03:26.000–00:03:31.000 | Shift to historical context.
- BEAT-043 | 00:03:31.000–00:03:39.500 | Let original speech take focus.
- BEAT-044 | 00:03:39.500–00:03:47.500 | Resume interpretation.

## Visual Sequences
### VIS-SEQ-012 | 00:03:20.000–00:03:47.500
Source Cues: 41–44 (narration gap between cues 42 and 43)
Spans Beats: BEAT-041–BEAT-044
Visual: VIS-012 — Same accurately attributed archival picture throughout; no cut at the audio handoffs. ACTUAL only after footage/provenance verification.
Audio: SRC-AUD-004 becomes primary only in the SRT narration gap; MUS-003 pauses. This does not restart VIS-SEQ-012.
Connection: Cross-beat picture continuity is intentional.

## Audio Timeline
- NARRATION | cues 41–42 (ACTIVE), gap 00:03:31.000–00:03:39.500 (PAUSE), cues 43–44 (RESUME). Exact words and timing remain in SRT.
- SRC-AUD-004 | linked to VIS-SEQ-012 | 00:03:20.000–00:03:31.000 MUTED → 00:03:31.000–00:03:39.500 FADE_IN/PRIMARY → 00:03:39.500–00:03:47.500 DUCK/FADE_OUT. Content, sync, attribution and rights: verify against provided media; unresolved otherwise.
- MUS-003 | may continue below cues 41–42, PAUSE during SRC-AUD-004 primary, optional gradual RESUME after cue 43 begins; narration remains intelligible.
- SFX-001 | one optional subtle transition accent at 00:03:20.000 only if requested style warrants it.

## Transition Map
- TRN-004 | 00:03:31.000–00:03:39.500 | AUDIO_HANDOFF: NARRATION (gap) → SRC-AUD-004 PRIMARY → NARRATION (cues 43–44); picture stays VIS-SEQ-012. This is **not** a visual cut or a J/L cut.
```

No cue has been rewritten or retimed. A visual sequence crosses four narrative beats and changes original-sound state twice without picture restart. The original source's sound might not be usable: until verified, record `SRC-AUD-004` as conditional and leave the handoff unresolved. If the actual SRT has narration throughout `00:03:31.000–00:03:39.500`, do **not** insert this pause; either design a subordinate source-audio mix under narration, obtain explicit authorization **and a revised timecoded narration source** before finalizing the interlude, or omit it.

For interview footage, sports commentary or location documentary audio, the same logic applies: identify the particular original recording, the audible content/role and the SRT gap or voiceover relationship. An incoming original sound before its picture is a J-cut only when the audio actually leads that picture; a voice handoff while the picture stays put is not.

## Natural-sound variant

Imagine a **verified waterfall shot with its own usable recorded sound** and an SRT gap from 00:02:15.000–00:02:19.000. `VIS-SEQ-021` can run 00:02:10.000–00:02:25.000 throughout. Link `SRC-AUD-021` as `NAT_SOUND`: DUCKED behind cue-number-referenced narration through 00:02:15.000; PRIMARY during the real 4s gap (`SENSORY_BEAT`); BACKGROUND/DUCKED when narration resumes at 00:02:19.000. Pause/reduce music and omit duplicate waterfall SFX. The source recording, link and gap are hypothetical conditions, **not** facts to assert from a visual requirement alone. If waterfall sound begins before `VIS-SEQ-021`, a J-cut requires its actual lead and the cut time; if it trails the picture, an L-cut needs an actual overhang. Neither occurs just because source sound becomes PRIMARY while the image continues.

For an actual **source-audio bridge** in a different illustrative edit: if linked waterfall `SRC-AUD-021` begins at `00:02:08.800`, `VIS-SEQ-021` begins at `00:02:10.000`, and previous picture is still on screen until `00:02:10.000`, `TRN-021` is a SOURCE_AUDIO J_CUT with **1.200s lead**. If the waterfall picture instead ends at `00:02:25.000` while that same sound ends at `00:02:26.000`, the departure is a SOURCE_AUDIO L_CUT with **1.000s overhang** into the next picture. These are alternative conditional bridge designs, not mandatory additions to the sensory window above, and require a usable synced recording.
