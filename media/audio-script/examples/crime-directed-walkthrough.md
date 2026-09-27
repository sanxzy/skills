# Complete hand-directed crime narration: Rockefeller impostor

**Full version:** this example covers the entire 21-minute Indonesian transcript-derived narration, from the opening to the final `♪ ♪` placement marker. The source is a **craft-study transcript, not independently verified research**. It contains real-person allegations, attributed motives, and time-sensitive claims such as “Hari ini”; do not treat this example as fact-checked or ready to publish without upstream verification. The voice-direction pass preserves the source's spoken words rather than silently repairing those claims.

Read the files in order:

1. [Full subtitle source](rockefeller-full.srt) — the manually retimed Indonesian video-script narration in 449 numbered cues (441 spoken, 8 visible video-track `♪ ♪` markers). This matches the archived 2,817 spoken word tokens in order; it is not a new fact-check.
2. [Full manually directed draft](rockefeller-full.work.txt) — **every** spoken cue directed by hand, with selective focus, meaningful beat boundaries, and local changes of delivery. The anchors are metadata, never spoken.
3. [Complete `.voice.md`](rockefeller-full.voice.md) — 59 short, copy-ready Eleven v3 segments, all under 500 characters. The helper *only* split already directed passages; it did not select tags, pauses, or stressed words.
4. [Complete `.voice.map.md`](rockefeller-full.voice.map.md) — all 449 cue anchors accounted for; segment spans are editorial source ranges, not measured TTS timings. The eight `♪ ♪` intervals belong to the video/music track, not TTS.

## Hand-scored arc (not Eleven v3 syntax)

| Story movement | Performance decision | What not to do |
| --- | --- | --- |
| Claimed Rockefeller identity → original name | Focus on **MENGAKU** in the opening; shift to deliberate delivery at the named identity, then return to ordinary explanatory rhythm. | Do not treat a claimed family tie as established, or capitalize every proper name. |
| Early assumed identities → acceptance by social circles | Group each new alias with the specific conduct supporting it. Let contrast carry the story; put short processing breaks at changes of place or identity. | Do not assign `[mysterious]` or `[shouts]` to every sentence. |
| Sohus family → disappearance | Keep the setup and the couple's disappearance in separate intonation units. Use restraint at the harm, not a performed gasp or sinister sound. | Do not invent what John, Linda, or Christian thought. |
| Stolen credentials → Wall Street → new identity | Maintain clearer, more measured pacing around aliases, organizations, and causal turns. The source's attribution and qualifiers stay intact. | Do not accelerate dense lists until they become unintelligible. |
| Custody case → child recovered | Place quiet weight on consequences and relief, without making the child's harm an entertainment beat. | Do not introduce laughter, crying, or a new witness reaction. |
| Forensic discovery → competing courtroom accounts → verdict | Differentiate forensics, defense claims, prosecution claims, and jury decisions through phrasing. Close on the ruling in a controlled tone. | Do not make an allegation sound like a verdict or assume the narrator can verify the source's factual accuracy. |

## What the helper may—and may not—do

The agent must manually direct each passage **before** splitting: pre-focus → stress-bearing word → landing, punctuation, silence/processing space, and appropriate delivery. The helper only verifies anchors/coverage, flags changed spoken words or estimated timing risks, and groups the authored paragraphs into segments. For this version it flags **zero spoken-word differences** and **zero approximate-rate overruns**; the manually authored source cue boundaries and their timings are editorial estimates, not recorded audio. The `[Co.]` abbreviation appears literally in SRT but is manually written `Co.` in the TTS draft so Eleven v3 does not treat it as an Audio Tag. All eight music cues are excluded from voice text and retained in the map; the grouping was reviewed so no generated segment ends halfway through a spoken sentence.

Reproduce the outputs, after inspecting them, with:

```bash
python3 <skill-dir>/scripts/build_voice.py <skill-dir>/examples/rockefeller-full.srt <skill-dir>/examples/rockefeller-full.work.txt --force
```

The regression test rebuilds both files in a temporary directory and checks byte-for-byte equality. Keep the example's tone as an editorial demonstration—not a promise that tags will sound the same with every voice or that every transcript claim is true.
