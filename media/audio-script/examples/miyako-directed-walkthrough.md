# Full manually directed crime example: Miyako Hiraoka investigation

**Content warning:** the source contains explicit descriptions of violence against a real victim. This is a **full-format voice-direction demonstration** from a transcript-derived narration, not independently verified research or a publishable final script. Some claims about police systems, timelines, motives, and forensic conclusions require upstream fact-checking. The `audio-script` pass preserves source wording, including graphic passages; it adds **no** new violent description, reaction, or sound effect. A real production should first decide whether to remove unnecessary graphic detail in the upstream video script rather than using TTS direction to make it more dramatic.

Study the bundled files in order:

1. [Full source timeline](miyako-full.srt) — the same **manually authored 574-cue SRT** as the transcript-derived Indonesian video example, with 3,266 spoken words in original order and no `♪ ♪` markers. Its source claims require separate provenance and fact-checking before publication; the upstream video-script companion is not bundled with this example.
2. [Full manually directed working draft](miyako-full.work.txt) — all 574 source anchors retained, with hand-selected qualitative delivery tags and 63 thought-boundary beats from opening through final consequence.
3. [Complete Eleven v3 `.voice.md`](miyako-full.voice.md) — 73 manually directed segments, none over 500 characters and none ending mid-sentence. The helper split the authored draft; it did not write the performance.
4. [Complete `.voice.map.md`](miyako-full.voice.map.md) — every SRT cue covered, with editorial cue timecodes; neither map nor narration measures recorded TTS timing.

## Manual direction through the investigation

| Movement | Information focus and voice choice | Safeguard |
| --- | --- | --- |
| Ordinary departure → missed return | Measured setup; softer landing on the expected return to the dormitory. The contrast comes from the two facts, not theatrical suspense. | No fabricated witness feeling or character voice. |
| Search → forensic identification | Calm investigative cadence, with restraint around discovery and forensic details. Give official attribution room. | **No** whispers, gasps, shocking sound cues, or stressed graphic words. |
| Missing evidence → stalled inquiry | Separate camera coverage, geography, and inter-prefecture data problems into intelligible thought units. | Avoid making a broad institutional claim sound more certain than the source. |
| Old files → review in 2016 | Deliberate pivot from nearly seven years of stalled leads to reviewing original data. `SATU nama` is the informational hinge, not every statistic. | Do not frame the suspect as convicted by a court. |
| Camera → recovered files → deceased suspect | The initially `KOSONG` card gives way to recovered data; pause before the source's revelation that Yano had already `MENINGGAL`. | Keep the victim's treatment understated; tags are not a substitute for verification. |
| Case closed → no trial → safety changes | Land the distinction between an investigative conclusion and **no formal prosecution/verdict**; close with what changed in the campus environment. | Do not claim the case created every later reform in Japan. |

The full source has explicit language; this example intentionally **does not amplify it** through delivery. A content editor, not this TTS skill, should decide whether the source should be revised for a given audience. The helper reports zero detected spoken-word changes and zero approximate-rate warnings; neither result establishes factual truth, safe content, or actual audio timing. Tags are qualitative and voice-dependent.

For a structural check, the test suite rebuilds both outputs in a temporary directory and compares them byte-for-byte with these bundled files. Do not assume that a passing test evaluates voice quality. Rebuild locally only after inspecting existing artifacts:

```bash
python3 <skill-dir>/scripts/build_voice.py <skill-dir>/examples/miyako-full.srt <skill-dir>/examples/miyako-full.work.txt --force
```
