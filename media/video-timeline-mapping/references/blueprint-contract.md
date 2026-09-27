# Markdown blueprint and revision contract

[SKILL.md](../SKILL.md) owns scope and output. A narrative beat describes meaning; a visual sequence and every audio region own their **own** start/end. Neither SRT cue nor narrative beat is a container for all media. SRT owns all spoken words and original cue timestamps: blueprint references cue **numbers/ranges only**, never copies their text.

## Location and sections

Write one UTF-8 Markdown file in the active target workspace: `.artifacts/video-timeline-mapping/<title_name>.timeline.md`. Derive a safe lowercase hyphenated stem from title or input filename, stripping path separators and using `video-timeline` if empty. Never silently overwrite an unrelated title. The installed examples are examples, not runtime destinations.

1. **Metadata:** title, source path, known source span, style (explicit/inferred), version; separate authorized duration if different. SRT endpoint does not prove rendered runtime.
2. **Editorial Direction:** concise visual/audio grammar, representation policy, priorities and constraints.
3. **Visual Sequences:** the authoritative picture timeline. Each `VIS-SEQ-### | start–end` states visual requirement(s), purpose, specificity, `Source Cues: n–m` or gap, internal visible states when needed, overlays and continuity. A sequence may span several narrative beats and many cues. A VIS-SEQ boundary is a *planning-region boundary*, not automatically a clip cut: if a later region says HOLD an earlier VIS, the underlying media continues through both regions. Prefer one longer VIS-SEQ with timed internal states when no new picture decision justifies a split. If a montage needs several shots, describe bounded internal stages rather than an undefined list.
4. **Audio Timeline:** compact `NARRATION` cue-number/range coverage and **only significant** pause/resume handoffs (SRT remains sole timing/word source); independently timed `SOURCE_AUDIO` (`SRC-AUD-###`, including `NAT_SOUND` originally captured with footage), music, separately mapped ambience and added SFX regions as useful. A `SENSORY_BEAT` is a named editorial window within these regions, not another layer or forced visual cut. Mark `SOURCE_AUDIO: none specified` if no original-media sound is known/requested; never fabricate a recording.
5. **Transition Map:** only deliberate visual/audio connections; IDs and timing reference sequence/audio events, not a second master timeline.
6. **Editorial Validation:** coverage, continuity, cue integrity, source-audio uncertainty and unresolved decisions; no unchecked PASS.

An optional concise `Narrative Beat Index` may give `BEAT-### | start–end | function` **only if** cross-beat relationships need explicit IDs. It does not own visual/audio and must not transcribe cues. `Spans Beats` on a visual sequence references that index when present; otherwise `Source Cues` already gives lightweight traceability. Do not enumerate every cue twice or add a narrative outline simply to satisfy a template.

## Minimal visual sequence with independent narration

```markdown
### VIS-SEQ-002 | 00:00:23.000–00:01:08.000
Source Cues: 5–13
Spans Beats: BEAT-002–BEAT-003 (if the optional narrative index is present)
Visual: VIS-002 — One illustrated surface-to-air model stays on screen. At cue 7, add an evaporation label; later continue the same model to show gradual water loss without boiling. Conceptual, not measured vapor footage.
Audio: MUS-001 continues beneath the explanation, if used.
Connection: No cut at the BEAT-002/BEAT-003 boundary.

## Audio Timeline
- NARRATION | cues 1–103 — Use exact cue timing in the paired SRT; gaps contain no narration.
- SOURCE_AUDIO — None specified; no original-footage sound claimed.
```

For a sequence crossing several meaning changes, one `VIS-SEQ` covers the entire picture interval while optional BEAT IDs (or cue ranges) locate narrative shifts and `SRC-AUD` regions describe sound handoffs **inside** it. The [cross-layer example](cross-layer-sequences.md) demonstrates this without claiming original footage exists.

## Identity, timing and authority

`VIS-SEQ-` names a picture region; `VIS-` optionally names its visual requirement/internal state; `BEAT-` names a narrative change **only in an explicit index**. `SRC-AUD-`, `MUS-`, `AMB-`, `SFX-`, `TRN-` name independent events as useful. `Visual Sequences` is authoritative for picture timing; `Audio Timeline` is authoritative for supporting audio timing; `NARRATION` refers back to the SRT, which is authoritative for speech. Short `Audio:`/`Connection:` notes within sequences may point to those regions but do not create second contradictory timing. A HOLD in a later VIS-SEQ refers to earlier VIS media, not an additional full-screen image; carry that base across the boundary without a restart. A source-audio link names its associated `VIS-SEQ`, known/unknown original content, provenance/availability status and role; never convert an unsupported `NAT_SOUND` requirement into an asserted existing recording. A sensory pause names the actual SRT gap and linked source-audio region; an authorized narration revision remains conditional until a revised timecoded source is supplied.

Use `HH:MM:SS.mmm` where defensible; for an in-cue estimate use `~HH:MM:SS.mmm`, `Timing: APPROXIMATE`, and a reason. A millisecond format is not word-level evidence. Do not put proposed speech in an SRT gap as an established fact. All base picture intervals must cover the known/planned span with no unexplained holes or conflicting full-frame overlaps. Composite/overlay lifetime can differ from base picture. Music, ambience, SFX and source audio may cross any sequence and beat boundary. No event extends beyond known duration without a separately authorized duration and reason.

## Revisions

Read the existing file and SRT; change only affected visual sequences, audio regions and linked transitions. Preserve unaffected IDs/timings; retire removed IDs (gaps are fine); add IDs only for new events. Bump `Timeline Version`, add a one-line revision summary and recheck both sides of every changed boundary. A prior file with `Master Timeline`/`BEAT` denoting picture regions can be migrated to `Visual Sequences`/`VIS-SEQ` while retaining numeric suffixes and VIS IDs; do not treat those old picture BEAT IDs as a newly invented semantic-beat index. Do not renumber other events for cosmetic continuity. Read back the saved file and return its path and material limitations.
