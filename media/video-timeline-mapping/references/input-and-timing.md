# Input, SRT interpretation, and timing

Read alongside [SKILL.md](../SKILL.md). This reference describes how to derive defensible timing; it does **not** make cue boundaries into visual cuts. The original SRT is the spoken-word record. Do not copy its transcript into the timeline.

## Intake

Required: one readable local timestamped narration file, ordinarily UTF-8 SRT. Optional: an explicit title and total video duration, platform/aspect ratio, style/reference, footage inventory, music policy, visual/audio restrictions, audience, and an existing timeline to revise. Use provided constraints before inference. A plain prose script without timing is insufficient for an exact timeline: request timecoded narration rather than fabricate timings. If a format other than SRT supplies reliable cue times, normalize conceptually without modifying it.

Inspect the **whole** source before planning anything. Read every cue; inspect the start/end, text, pauses, non-spoken markers, opening and ending spans, chronological order, and overlaps. Then reconstruct sentences and arguments across cues privately. A cue can end mid-sentence, so neither its index nor its start/end means a semantic or visual change.

## Parsing and source-span checks

Conventional SRT: cue index; `HH:MM:SS,mmm --> HH:MM:SS,mmm`; one or more subtitle text lines; blank line between cues. Parse with the last end timestamp as the known source endpoint, not a guaranteed MP4 duration. Cue times must be valid and have positive duration; indices/time order must make sense. An overlap may be legitimate in a multi-speaker source, but if its interpretation is unclear, flag it before mapping. Do not silently reorder or repair corrupt cues. If the source is empty, malformed, lacks usable timings or is incomplete in a way that prevents full mapping, stop and ask for a corrected input or a bounded scope.

Treat `♪ ♪`, `[music]`, similar markers and descriptive sounds as *non-spoken cues*. They may document a sound state but never become narrated words or prove that a specific music asset is available. When a music marker appears after a gap, do not claim music exists in that gap without a separate editorial choice. Silence in the narration does not prove full-mix silence.

## Source timing versus editorial timing

| Observed source | Defensible treatment |
| --- | --- |
| First cue begins after 00:00:00.000 | Cover the lead-in visually; normally keep it inside the first establishing visual sequence when no picture state changes. |
| Inter-cue gap | Preserve its duration. Hold existing picture/audio if appropriate, or give it a separate visual sequence only for an actual picture change (e.g. a long observational passage). |
| Several cues express one idea | A single visual sequence can span all of them. |
| One cue explains several stages | Use staged highlights in one visual, or a justified in-cue change if its timing is defensible. |
| Narration ends before source endpoint | Plan the remaining visual state; mark a sound cue only if the source actually supports it or the direction calls for it. |
| Known requested render duration exceeds SRT | Use the explicit duration and explain the extension; without it, never invent a post-roll. |

A `VIS-SEQ` interval belongs to the **picture state**, not automatically to its cited cues or narrative beats. Include cue numbers/ranges in the blueprint for alignment, but do not copy cue text. Source-audio handoffs must use a real gap in those cue times. If a user authorizes narration retiming, request an updated timecoded narration source before treating the new handoff as final; otherwise mark it conditional/unresolved and leave existing cue timing intact. Use cue boundaries when they naturally coincide with a motivated change. Use `HH:MM:SS.mmm` for defensible times, but timecode syntax alone is not evidence of sub-cue precision. If a meaningful action occurs inside a cue with no word timing, prefer an exact surrounding cue boundary, an internal progression without a timestamp, or an explicitly approximate `~HH:MM:SS.mmm` with `Timing: APPROXIMATE` and why. Do not multiply false-precision sub-cue cuts. A cue index/range is a locator for an agent with the SRT, not a demand for a cut or a second narration summary.

For long sources, a private working outline can record section functions, entities, chronological transitions, reveals, and major gaps. This outline is for global understanding, not a required output section. An optional concise narrative-beat index is useful only when cross-beat relationships need explicit IDs; it never owns media intervals. Map successive spans, then review the entire plan to ensure the last cue, gaps, and ending are all accounted for.

## Example timing decisions

- Giethoorn: 00:00:00.000–00:00:00.920 is only a sub-second opening lead-in; let the establishing visual continue into the first cue rather than creating a separate sequence. 00:00:33.100–00:00:58.020 is a longer narration gap and may support an intentionally observational picture sequence. Music-only cues 54–55 are not spoken narration. See the [bundled input](../examples/bagaimana-hidup-ketika-kanal-menjadi-jalan-id.srt) and [blueprint](../examples/bagaimana-hidup-ketika-kanal-menjadi-jalan-id.timeline.md).
- Ames: keep the name unshown until cue 5 at 00:00:28.571; the gap after cue 4 can hold an anonymous image without inventing extra speech. See the [bundled input](../examples/pengkhianat-cia-yang-lolos-hampir-9-tahun.srt) and [blueprint](../examples/pengkhianat-cia-yang-lolos-hampir-9-tahun.timeline.md).
