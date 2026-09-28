---
name: video-script
description: Research, verify, and write original documentary or educational video narration as an editor-ready timestamped timeline, with a separate claim-to-source record. Use for new video scripts and substantive script revisions.
---

# Video Script

Turn a title and content direction into a complete audiovisual narrative grounded in reliable research. Optimize in this order:

**Research quality → factual accuracy → narrative structure → clarity → engagement → audiovisual usability.**

## Bundle scope and precedence

All instructions, craft references, examples, and helpers needed to use this skill live inside this directory. Resolve companion links relative to the file containing them; `<skill-dir>` in commands means this directory's installed location. No other skill, repository artifact, prior conversation, or original transcript file is required. Source video URLs and input hashes record provenance; study the bundled examples and companions without loading original extraction files. New research uses available web tools, and the optional validator uses Python's standard library.

The user's brief controls language, voice, duration, and material requirements. This file defines the output contract; companion guidance and examples explain its application. The contract applies to new researched scripts and substantive revisions. The bundled `.md` / `.sources.md` research pairs and `.md` / `.source.md` transcript-derived pairs are archival craft examples being migrated by hand to the new SRT contract. They preserve evidence and source narration for study, including disclosed factual weaknesses and footage-dependent timing; their old file layout does not demonstrate the new output format. They are not finished researched deliverables or exceptions to the requirements for a new script. Study their narrative relationships without inheriting their errors, graphic detail, padding, or unsupported claims.

## Deliverable contract

Save two UTF-8 files relative to the user's active project:

- `.artifacts/video-scripts/<title_name>.srt`: only the production-ready subtitle timeline, **one short spoken thought per numbered cue**.
- `.artifacts/video-scripts/<title_name>.source.md`: research, verification, claim mappings, timing assumptions, and any production notes.

Derive a readable lowercase filename stem from the title: replace whitespace/punctuation with hyphens, retain meaningful Unicode letters and numbers, collapse repeated hyphens, and remove path separators. Use `video-script` if the stem is empty. Never interpret a title as a filesystem path. For a revision, update the established pair; for a different title that collides, use a distinguishing suffix and apply it to both files.

The main script is a conventional UTF-8 SRT file: sequential cue number, `HH:MM:SS,mmm --> HH:MM:SS,mmm`, **one or two text lines containing at most one spoken sentence**, then a blank line. For example:

```text
1
00:00:00,000 --> 00:00:03,500
Desa indah yang tak punya jalan raya.

2
00:00:03,500 --> 00:00:08,000
Giethoorn adalah sebuah desa kuno di Belanda.
```

Compose meaningful short spoken units *while writing*, not by automatically slicing finished paragraphs or assigning arbitrary timecodes. **One cue is at most one spoken sentence.** Put a hook, subject introduction, explanation, contrast, consequence, or question in separate cues when they are separate sentences. Never place two full sentences in the same subtitle cue, even when the combined cue is short. A deliberate short phrase without terminal punctuation may stand alone when it is an intelligible hook or continuation; a long sentence may be split at natural clause boundaries without changing its words. Typically aim for one sentence or natural intonation unit per cue, about 5–12 seconds and comfortably under 30 words; the validator enforces a generous 15-second / 35-token maximum on spoken cues. A very brief sentence is fine when it earns its place.

**Subtitle readability (English and Indonesian starting preset):**

| Setting | Comfortable target |
| --- | --- |
| Displayed characters per cue | 40–70 |
| Characters per line | 32–40 |
| Visual lines per cue | 1–2 |
| Reading speed | 12–15 characters per second (CPS) |
| Long cue | Manually review and usually split above roughly 80 characters |
| Visual line breaks | At punctuation or natural phrase boundaries |

Count spaces and punctuation: `minimum reading duration = total displayed characters ÷ chosen CPS`. A 60-character cue needs about 4–5 seconds at that pace. If only two seconds are available, manually split at a natural spoken boundary or revise *without dropping a fact, qualifier, or spoken word*; do not simply speed up the estimate. Review and usually split cues above roughly 80 characters. Break the **visual line**, without creating another cue or sentence, after punctuation or at a natural phrase boundary; never strand a small connective or separate words that belong together. For example, one cue can display:

```text
We need to finish this today,
so we can leave early tomorrow.
```

These are **comfort targets**, not a license to weaken factual coverage or to retime by formula. A two-line cue still contains only one spoken sentence, and the time on screen matters as much as its character count. For comparison, [Netflix's U.S. English timed-text guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-USA-Timed-Text-Style-Guide) allows 42 characters per line and up to 20 CPS for adults; our 40/15 preset is deliberately more relaxed. Keep related cues together narratively: do not turn a complete explanation into a string of disconnected dramatic fragments. Start times increase, intervals are positive and non-overlapping. SRT timecodes are **editorial estimates**, not measured recording timestamps. Each cue must allow enough time for its spoken words and natural delivery.

No Markdown title, frontmatter, section labels such as `Hook:` or `Chapter 1:`, citations, URLs, source IDs, research notes, word counts, explanations, or fenced code in the SRT narration. Write an inline spoken abbreviation that ends in a period inside literal brackets, e.g. `[Mr.]`, `[Jend.]`, or `[U.S.]`. This **syntax is generic**, not an enumerated list of known titles: letters and optional internal periods ending in a period are accepted; numbers, spaces, citations, and voice-direction tags in brackets are not. A period inside brackets or a number is not a sentence boundary; an unbracketed period followed by more words is treated as a boundary. A title or label may appear as narration only when it is actually part of the video. By default use narration only; let gaps carry visuals. If useful to the requested format, a deliberate video-track music interval may use `♪ ♪` as the cue's only text; it is **not** spoken by TTS. Do not dump shot lists or directing instructions into narration. Put optional visual plans and displayed-text specifications in the source file.

## Intake and duration

Use the supplied title, topic/content direction, and optional duration/requirements. Ask only for missing information that prevents choosing a subject or satisfying a material constraint. Infer reasonable tone and audience from the brief; use the requested language, otherwise the language of the user's request. Do not translate a supplied title without reason.

When creating or improving a title, read [titles-and-thumbnails.md](references/titles-and-thumbnails.md). Start with who would watch, what interests them, why they would click, and why a stranger would click. Develop one clear curiosity loop that the script can resolve; finalize the title after the story's payoff is known. A title and proposed thumbnail should communicate the same idea through complementary information. Keep required supplied titles, and do not imply that an untested candidate is a proven winner.

**Without an explicit duration, target at least eight minutes**, ordinarily a focused eight-to-ten-minute script. An explicit duration overrides this default: five minutes means approximately five, twelve means approximately twelve, twenty means approximately twenty. Treat an explicit short-form request as a duration override; if it has no numerical duration, choose a suitable short duration and record the assumption. Respect an explicit maximum or duration range.

Plan the actual spoken content before assigning timecodes. Use a plausible narration rate in the output language, allow meaningful visual gaps, then check both each block and the complete timeline. Do not meet duration by stretching sparse narration, repeating facts, adding long empty intervals, or slowing delivery unnaturally. See [timing-and-format.md](references/timing-and-format.md) for word budgets and timing calculations.

## Workflow

### 1. Research the story

Read [research-and-verification.md](references/research-and-verification.md). Use the available web search and page-reading tools to discover and read reliable sources. Research the question behind the title, mechanisms, useful examples, consequences, competing explanations, and uncertainty. Build a claim ledger before drafting.

Prefer authoritative primary material for the relevant subject: original studies, official data, institutional explanations, archives, court records, and first-hand documents. Use credible secondary reporting for synthesis and context. Search results are leads, not a substitute for reading the supporting passage. Trace copied claims back to their origin; multiple sites repeating one source do not provide independent confirmation.

### 2. Verify before selecting facts

Check every material factual claim against evidence that actually supports its wording, scope, date, denominator, and causal strength. Recheck current figures near delivery. Record calculations with inputs and units. Separate established facts, reported observations, contested interpretations, and editorial inference. Never invent statistics, dates, events, quotations, science, geography, personal claims, or causal links.

Omit unsupported claims. If uncertainty matters to the story, express it naturally and accurately in narration and document it in the sources file. Confident wording in a transcript, article, or model's output is not verification; inspect the supporting evidence. Do not use a short search snippet as proof. If web access is unavailable or the central premise remains unsupported, preserve useful work, explain the specific limitation, and request needed evidence; do not present an unverified draft as a finished researched script.

### 3. Design the narrative

Read [narrative-architecture.md](references/narrative-architecture.md). Choose a structure that fits the evidence: explanation, chronological investigation, geographic journey, comparison, or a documented subject facing a concrete task. Identify the opening promise, the changes that move the story, and the final answer. Make a private beat outline with each beat's purpose, supporting claims, visual opportunity, and approximate time budget. Keep this planning outside the script.

Unless the user specifies a different voice, select a relevant complete example from the [user-supplied transcript collection](examples/transcript-derived/stories-worth-studying.md) and read its paired `.source.md` before drafting. Study the continuity of the full narrative, sentence rhythm, concrete detail, and how developments lead into explanations. These transcript-derived examples are the primary voice references; the original researched demonstrations below illustrate evidence-to-story craft, but their old `.md` layout is not the current output contract. Keep the new script original and verify its facts independently: the collection records source narration, including claims that have not been independently verified.

Write as a documentary storyteller. Let concrete events, decisions, obstacles, and consequences develop the viewer's understanding. For Indonesian documentary narration, user-provided transcript references, or a draft that sounds like a research briefing, read [documentary-storytelling.md](references/documentary-storytelling.md). Repair punctuation when studying automatic transcripts; preserve their narrative relationships, not caption errors.

Make the first few narration cues a concrete hook: lead with the strongest verified consequence, consequential event, discovery, or contrast available for the subject. For a problem-focused story, show its impact before routine background. Introduce the subject promptly and connect the hook to the explanation that follows. Answer small questions as they arise; develop deeper implications afterward. Use **fact → explanation → context → consequence** as the default progression. Every cue must introduce, explain, contextualize, advance, connect, prepare, or resolve something useful. Remove cues that only repeat or announce forthcoming content.

### 4. Write for narration and pictures

Read [narration-and-clarity.md](references/narration-and-clarity.md) and [audiovisual-writing.md](references/audiovisual-writing.md) when shaping the draft. Write original language understandable across ages: concrete explanations, short-to-medium sentences, clear referents, smooth transitions, and a natural spoken rhythm. Explain necessary terminology where it first matters.

Keep factual progression central. Metaphors, analogies, questions, humor, and dramatic emphasis are occasional tools, not the default voice. Avoid hyperbole, repetitive sentence patterns, artificial suspense, and flowery descriptions. Do not manufacture a person's thoughts, an animal's motives, a scene, dialogue, or a filmed event to enliven the script. General audiences do not require babyish language or graphic depictions.

Keep the narration focused on the subject. Integrate necessary dates, attribution, and uncertainty naturally; put methodological explanations in the sources file. Avoid repeated instructions such as “this figure must be interpreted carefully” or “this document helps us evaluate the issue.” Explain the actual event, mechanism, or consequence instead, retaining any qualification needed for accuracy.

### 5. Time and audit the finished script

Read [quality-review.md](references/quality-review.md). Read the narration aloud or simulate a deliberate spoken reading. Recalculate after edits, including numbers and difficult names. Check factual support against the final wording, trace claims to the final timecodes, and ensure the ending pays off the title. Judge information density by understandability and progression, not the number of statistics.

Run the bundled validator when Python is available:

```bash
python3 <skill-dir>/scripts/validate_script.py .artifacts/video-scripts/<title_name>.srt
```

For a requested duration, or a chosen duration for an unnumbered short-form request, add `--target-minutes 5` (or the chosen value). Check any explicit maximum or duration range separately; the tool's approximate-target tolerance cannot override those boundaries. Supply a justified speech-rate range with `--min-wpm` / `--max-wpm` if the language or delivery needs it. See [timing-and-format.md](references/timing-and-format.md) for options and limitations. Fix errors and inspect warnings; a passing validator does not establish truth, narrative quality, or recorded runtime. Without Python, perform the equivalent checks manually.

### 6. Save and deliver

Finish the `.source.md` file using [sources-file-contract.md](references/sources-file-contract.md), including source titles, publishers, direct URLs, dates where available, relevant evidence locators, claim-to-SRT-cue mappings, limitations, and timing assumptions. Update mappings after changing narration or timestamps. Keep the paired outputs consistent.

For title-development tasks, record the selected title, audience, curiosity loop, payoff, proposed thumbnail concept if useful, and actual performance-evidence status in the sources file. Use the selected title for a new filename pair; rename an established pair only when requested and update its links. Do not insert packaging notes into narration or generate thumbnail assets unless requested.

Return concise links to both files and the intended duration. Keep process explanations outside the script. Completion requires both files, verified material claims, a coherent finished narrative, compliant formatting, and realistic timing. All bundled full timelines use `.srt` / `.source.md`; historical source wording and footage-dependent timing remain craft references, **not** templates for new-script pacing or unchecked factual claims.

## Bundled craft references and examples

Read selectively; do not load every resource for every request.

- [User-supplied transcript examples](examples/transcript-derived/stories-worth-studying.md): 16 bundled SRT transcript examples from 15 videos, with separate Indonesian/English Rockefeller versions. Each edited timeline has its own `.source.md` recording creator credit, video URL, input hash, editorial changes, factual limitations, and every block's provenance. Covers investigations, geography, daily life, traditions, and English wildlife narration. Use this collection first when selecting the default writing voice.
- [Transcript craft study](references/transcript-craft-study.md): comparison of the 16 bundled transcript examples from 15 videos, with local links and summarized techniques; useful for choosing techniques and recognizing weaknesses.
- [Clouds Have Water. Why Doesn’t It Always Rain?](examples/clouds-have-water-why-doesnt-it-always-rain.srt) and [its source record](examples/clouds-have-water-why-doesnt-it-always-rain.source.md): a full default-duration narration/source pair.
- [Seberapa Berbahaya Vladimir Putin?](examples/seberapa-berbahaya-vladimir-putin.srt) and [its source record](examples/seberapa-berbahaya-vladimir-putin.source.md): a complete Indonesian geopolitical example covering political power, Russia's government, military and nuclear capabilities, and European security; demonstrates dated data, attribution, and uncertainty.
- [Hujan Melimpah, Kenapa Desa Ini Bisa Kekurangan Air?](examples/hujan-melimpah-kenapa-desa-ini-bisa-kekurangan-air.srt) and [its source record](examples/hujan-melimpah-kenapa-desa-ini-bisa-kekurangan-air.source.md): an Indonesian documentary about Mawsynram, Meghalaya, India; connects homes, school, farming, crafts, markets, roads, and community responses to extreme rain. Demonstrates a narrative built from everyday tasks, geographic scope, dated field reporting, and a supported change in perspective.
- [Kenapa Satu Selat Bisa Mengguncang Ekonomi Dunia?](examples/kenapa-satu-selat-bisa-mengguncang-ekonomi-dunia.srt) and [its source record](examples/kenapa-satu-selat-bisa-mengguncang-ekonomi-dunia.source.md): an Indonesian documentary connecting Iran–Oman geography, navigation, oil and LNG shipping, and international consequences. Demonstrates clear proportions, dated baseline versus disruption data, cause-and-effect storytelling, alternative routes, and the limits of emergency responses.
- [Pengkhianat CIA yang Lolos Hampir 9 Tahun](examples/pengkhianat-cia-yang-lolos-hampir-9-tahun.srt) and [its sources](examples/pengkhianat-cia-yang-lolos-hampir-9-tahun.source.md): an Indonesian historical investigation of Aldrich Ames, the first KGB payment, compromised human sources, wealth, and documented alcohol problems. Demonstrates an evidence-based reveal, clear flashbacks, attributed motives, financial clues, and an ending that keeps the dramatic title within its supported scope.
- [Example walkthrough](examples/how-a-rainy-day-becomes-a-documentary.md): evidence-to-beat decisions, timing, and editorial tradeoffs for the rain pair.
- [Pattern workshop](examples/from-flat-facts-to-stories-worth-watching.md): original English and Indonesian excerpts, alternative narrative structures, transitions, and before/after revisions. Excerpts are not full-duration deliverables or reusable factual research.

Examples demonstrate craft and contracts. Re-research facts for new scripts; do not copy their wording, source claims, or timecodes mechanically.
