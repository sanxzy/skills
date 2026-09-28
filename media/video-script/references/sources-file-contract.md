# Sources file contract

The script remains clean. This paired file carries everything needed to audit its evidence and understand its production assumptions. It is not merely a bibliography.

Use the same filename stem as the new `.srt` script and the `.source.md` suffix. All bundled full examples now use `.source.md` companions; `.sources.md` is not a supported output convention. The following sections are a practical schema; add or compress sections to fit the topic without losing traceability.

## Brief and timing

Record the title, content direction, language, audience assumptions, requested duration or default, intended runtime, approximate spoken word count, planned delivery rate, visual gaps, research date, and whether timing is estimated or measured. Include meaningful scope choices, such as examining one country rather than all countries or using a particular definition of a ranking.

## Source register

For each source record:

- Stable ID such as `S01`.
- Page/document title and publisher or author.
- Direct supporting URL, not a search results page.
- Publication/update date when actually available; otherwise `not stated`.
- Date accessed and what was inspected: relevant section, table, figure, page, or passage.
- Source role: primary research, official data, institutional explanation, archive, interview, or secondary reporting.
- Scope or access limitations that affect its use.

A full paper was not read merely because its abstract was. A failed direct opening is not a successful page read: if accessible indexed text or a mirror supplied the supporting passage, identify that access method and the context actually inspected. A short search snippet, unread passage, unrelated recommendation, or page footer is not supporting evidence. See [research-and-verification.md](research-and-verification.md) for the passage-reading requirement.

Summarize evidence briefly in original language; quote only when necessary and within applicable limits. Preserve source qualifications. Avoid copying whole articles or transcripts into this file.

## Claim-to-evidence map

| Claim ID | Final SRT cue number(s) and editorial time(s) | Claim or tightly related claims | Supporting source and locator | Verification/qualification |
| --- | --- | --- | --- | --- |
| C01 | Cues 1–2, 00:00:00,000–00:00:12,000 | Factual content of opening | S01, named section | Exact supported scope |
| C02 | Cues 3–4, 00:00:12,000–00:00:25,000 | Explanation of the mechanism | S02, section/page | Established mechanism or attributed interpretation |

Map all material factual claims, including hook facts, scene details, statistics, transitions implying causality, and conclusions. Group related statements only when the sources support the whole group. Multiple sources may support different parts of a block; say which. Pure orientation, a clearly hypothetical demonstration, or an editorial question can be identified as such rather than assigned a false citation.

Keep identifiers stable during revisions, but update cue numbers, editorial timecodes, and wording to match the final SRT. The reader should be able to start from either an important narration claim or a source and find the connection.

## Calculations and uncertainty

For a derived number, record sourced inputs, dates, units, formula, result, rounding, and what assumptions mean. Label a calculation as derived; do not attribute the result to a source that only supplied an input.

Document rejected or uncertain claims when their exclusion matters to the framing. Explain contradictions that remain relevant. Do not bury a qualifier in this file if the narration would become misleading without it.

## Optional production notes

For title-development tasks, include the selected title, audience, reason a stranger would click, curiosity loop, and the answer or experience delivered by the script. Record any proposed complementary thumbnail concept and its asset assumptions. Distinguish an editorial candidate from a measured outlier or tested winner; record only performance evidence actually inspected. See [titles-and-thumbnails.md](titles-and-thumbnails.md).

Record useful visual ideas, intended purposes of larger gaps, pronunciation guidance, or displayed text. Distinguish proposed assets from supplied assets and documented scenes from illustrations. These notes do not replace the required evidence map. Omit them when they add no value.

## Final verification

Record actual checks performed, not aspirational checklist ticks: final wording compared with source passages, current values checked on a date, calculations recalculated, timing validator result, and spoken-read estimate. State limitations clearly: a validator cannot certify factual truth; intended timing is not a recorded voice performance.
