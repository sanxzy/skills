# Timing and format

Use before writing, after editing, and when resolving validator warnings.

## Runtime is two budgets

Let `T` be the target seconds, `G` be useful non-narrated seconds, and `R` be the planned spoken words per minute:

`spoken word budget ≈ (T − G) × R / 60`

At 135 words per minute with modest visual breathing room:

| Requested runtime | Illustrative useful gaps | Approximate spoken words |
| --- | --- | --- |
| 5 minutes | 15 seconds | 641 |
| 8 minutes | 25 seconds | 1,024 |
| 12 minutes | 40 seconds | 1,530 |
| 20 minutes | 60 seconds | 2,565 |

These are planning examples, not mandatory word counts. A supported wildlife sequence can justify more silence; a dense explanation may need slower speech. The default script still needs at least eight minutes of realistic content and purposeful visual time. A 500-word explanation does not become eight minutes by assigning generous endpoints.

## Choose a rate honestly

As an editorial starting point, many clear English or Indonesian documentary drafts can be planned around 120–150 spoken words per minute. This is a working assumption, not a universal physiological fact or a standard for every language. Use slower delivery for unfamiliar names, multiple figures, emotionally weighty facts, or younger audiences. Languages with different segmentation need a language-aware estimate or timed reading.

Count words as they are spoken. “2026,” “3.5 km,” and an acronym may take more than one word to read. Record the chosen rate, pronunciation assumptions, and any number expansion in the sources file. Do not use exceptionally fast narration to fit overlong content or exceptionally slow narration to fill a thin draft.

## Time each short cue

`cue seconds ≈ spoken words × 60 / local rate`, adjusted for natural phrasing and pauses. Write the explanation as a **connected sequence of short, complete spoken thoughts** before assigning cue times. For example, a 45-word explanation might require three linked 15-word cues, roughly 6–8 seconds each at 135 words per minute, not one 20-second subtitle block or three disconnected dramatic fragments. A short cue's timing includes its natural delivery, but it does not promise exact TTS duration.

Draft and revise the spoken progression first, then calculate the timeline from the beginning. Add meaningful visual gaps where needed. Recalculate downstream cue times after changing words. SRT's millisecond format is a file convention, not recorded precision. Do not force a fixed duration per cue or imitate caption-extraction overlaps. If a cue carries two independent facts or is hard to speak in one breath, rewrite the narration into adjacent complete thoughts *manually*, preserving qualifications and causal links.

## Exact SRT contract

```text
1
00:00:00,000 --> 00:00:06,500
The verified consequence comes first.

2
00:00:06,500 --> 00:00:12,800
The next thought tells us why it matters.
```

- Use consecutive cue numbers starting at 1. Each cue has a number, timestamp range, and **one or two subtitle text lines** (one spoken sentence total), followed by a blank separator; a final newline is allowed.
- Use two-digit hours, minutes and seconds `00`–`59`, and three milliseconds with a comma. Use the literal ` --> ` arrow; no `[MM:SS.mmm–MM:SS.mmm]` Markdown timeline in new scripts.
- The next start must be at or after the previous end; touching intervals are valid. Each cue must have positive duration.
- Every cue contains spoken narration or an intentional `♪ ♪` video-track marker, not an empty placeholder. No Markdown headings, wrappers, source metadata, inline citations, or directing tags.
- **Never put two sentences in one cue.** One complete sentence per cue is the norm; a brief, purposeful phrase or clause may be a separate cue. Periods inside numbers or square-bracketed spoken abbreviations are not sentence endings. Write any abbreviation containing letters and ending in a period inside brackets, e.g. `[Mr.]`, `[Jend.]`, `[U.S.]`; there is **no title whitelist**. These brackets appear on the video track. Bracketed citations, numbers, and stage directions are prohibited; unbracketed periods followed by more words count as sentence boundaries. In the audio-script draft, write the same spoken abbreviation without brackets (`Mr.`), because Eleven v3 interprets square brackets as Audio Tags. Split and retime by hand, keeping exact wording and the sequence of claims.
- Aim for a short complete thought per cue (usually 5–12 seconds; ≤35 Unicode word tokens and ≤15 seconds for spoken cues). This is an editorial granularity limit, not a mandate to pad terse lines or make every cue identical. Keep ideas linked across cues, and let real visual gaps remain gaps.
- For relaxed English/Indonesian subtitle reading, target 40–70 displayed characters per cue, 32–40 per line and **at most two lines**; manually review and usually split above about 80 characters. Allow roughly 12–15 displayed characters per second, counting spaces and punctuation (`reading seconds ≈ displayed characters / CPS`). A 60-character cue therefore needs approximately 4–5 seconds. If the available time is too short, rework the spoken phrasing/timing by hand without losing the original claims or spoken words. Put visual line breaks after punctuation or at natural phrase boundaries. These are comfort targets, not hard validity thresholds or a programmatic splitting recipe. [Netflix's U.S. English style guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-USA-Timed-Text-Style-Guide) uses up to 42 characters per line and 20 CPS for adults; it is a comparison, not our required pace.

Without a recording, final runtime remains an estimate. If the user later supplies a voice recording, retime to that recording rather than defending the earlier estimates.

## Validator

```bash
python3 <skill-dir>/scripts/validate_script.py <script.srt>
python3 <skill-dir>/scripts/validate_script.py <script.srt> --target-minutes 12
python3 <skill-dir>/scripts/validate_script.py <script.srt> --target-minutes 5 --sources <paired.source.md>
```

By default, the tool checks for at least eight minutes; with `--target-minutes`, it checks approximate agreement within five percent (or `--tolerance-seconds`). Use the chosen duration for a short-form request without a number. An explicit maximum or duration range remains binding: review those boundaries manually, even if an approximate-target check passes. It checks the `.source.md` sibling unless a path is specified. It never modifies files.

These default timing checks apply to new researched `.srt` scripts. All bundled full video examples now use SRT with paired `.source.md` records. Archival transcript-derived examples retain historical wording, footage-dependent gaps and tentative timestamps: they are craft context, **not** templates for a new script's timing or factual claims. The validator accepts SRT only; do not loosen new-script thresholds to imitate an archival example.

It rejects malformed, backward, overlapping, empty, citation-contaminated, metadata-contaminated, too-long, multi-sentence, or **more-than-two-line** SRT cues. It warns when a cue exceeds roughly 40 characters per line, 80 total displayed characters, or 15 displayed CPS so an editor can reassess timing and natural line breaks. It estimates spoken rates and reports timeline length, active narration time, words, and non-narrated share. A grossly slow overall rate, excessively fast substantive block, or more than twenty percent unspoken time fails by default; individually slow blocks receive warnings. These thresholds are review heuristics, not rules about documentary art. Adjust `--min-wpm`, `--max-wpm`, or `--max-unspoken-fraction` only for an actual language, delivery, or visual need, and document why. Review short fragments manually because word counting is especially crude there. An archival transcript preserving every original word *and* the source-video duration can mathematically exceed 15 displayed CPS even when every gap is used. When the user permits a longer editorial handoff, retime **manually**, preserve every spoken word, and distinguish the new SRT cue windows from the historical source-video windows in the paired record; a longer subtitle track does not imply that the original footage grew. Never silently omit words or carry archival exceptions into new scripts. A validator pass cannot replace visual review of the rendered captions.

Label-like narration such as `Chapter 1:` is flagged as possible internal metadata. Only when that wording is deliberately meant to be spoken may `--allow-spoken-labels` be used. This exception does not allow Markdown headings, research metadata, or unspoken directing notes in the main file.

The checker uses Unicode word tokens, excluding music markers; it cannot expand every number or acronym, judge multilingual timing, know what shots exist, verify source contents, validate claim mappings semantically, or prove the real recording length. It checks that the sources file is present and contains a URL, not that those URLs support the script. A passing result is the beginning of the editorial review, not a certificate of production quality.
