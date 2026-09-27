# Standalone SRT handoff (invented narration; format demo only)

No other skill or guide is needed. Input is a standard one-line-per-cue `.srt` file; the agent **manually** directs the complete draft before the helper segments it. Timecodes are editorial estimates.

Input `sample.srt` (the `♪ ♪` cue remains visible if imported into a displayed subtitle track):

```text
1
00:00:00,000 --> 00:00:08,000
Pada tahun 1986, tiga kapal tiba di pelabuhan.

2
00:00:09,000 --> 00:00:17,000
Namun, hanya satu yang kembali keesokan harinya.

3
00:00:20,000 --> 00:00:25,000
♪ ♪

4
00:00:25,000 --> 00:00:34,000
Penyelidikan dimulai pada pagi berikutnya.
```

Hand-directed `sample.work.txt`, written **from beginning to end before splitting**. The helper derives the non-spoken anchors from SRT cues; it does not choose delivery:

```text
[00:00.000–00:08.000]
[calm] Pada tahun seribu sembilan ratus delapan puluh enam, tiga kapal tiba di pelabuhan.

[00:09.000–00:17.000]
Namun, hanya SATU yang kembali keesokan harinya.
<!-- beat -->

[00:20.000–00:25.000]
♪ ♪

[00:25.000–00:34.000]
[deliberate] Penyelidikan dimulai pada pagi berikutnya.
```

```bash
python3 <skill-dir>/scripts/build_voice.py sample.srt sample.work.txt
```

The helper writes `sample.voice.md` and `sample.voice.map.md` beside `sample.srt`. Paste only the text inside a voice segment's fence into Eleven v3. The map records source cue timecodes and the expanded date for review. The SRT **retains** its music marker for the editor track, while `.voice.md` **omits** that marker. Neither anchors nor beat hints enter TTS input.

This illustrates the format, not verified history or an auditioned voice. Actual delivery, pronunciation, and recorded timing need downstream checking.
