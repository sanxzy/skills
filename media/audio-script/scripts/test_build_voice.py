#!/usr/bin/env python3
"""Standard-library tests for the standalone audio-script splitter."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from build_voice import build, read_source, read_draft, group, spoken, WORD  # noqa: E402


class BuildVoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.source = root / "example.srt"
        self.draft = root / "working.txt"
        self.source.write_text(
            "1\n00:00:00,000 --> 00:00:08,000\nPada tahun 1986,\ntiga kapal tiba.\n\n"
            "2\n00:00:08,000 --> 00:00:16,000\nNamun, hanya satu\nyang kembali.\n\n"
            "3\n00:00:18,000 --> 00:00:24,000\n♪ ♪\n\n"
            "4\n00:00:24,000 --> 00:00:34,000\nPenyelidikan dimulai\npada pagi berikutnya.\n", encoding="utf-8"
        )
        self.draft.write_text(
            "[00:00.000–00:08.000]\n[calm] Pada tahun seribu sembilan ratus delapan puluh enam, tiga kapal tiba.\n\n"
            "[00:08.000–00:16.000]\nNamun, hanya SATU yang kembali.\n"
            "<!-- beat -->\n\n"
            "[00:18.000–00:24.000]\n♪ ♪\n\n"
            "[00:24.000–00:34.000]\n[deliberate] Penyelidikan dimulai pada pagi berikutnya.\n", encoding="utf-8"
        )

    def test_build_map_and_copy_ready_text(self):
        voice, mapping, count, warnings, changes = build(self.source, self.draft)
        self.assertEqual(count, 2)
        self.assertEqual(len(changes), 1)
        text = voice.read_text(encoding="utf-8")
        self.assertIn("## Segment 001\n\n```text\n[calm]", text)
        self.assertNotIn("00:00", text)
        self.assertNotIn("<!-- beat -->", text)
        self.assertNotIn("♪", text)
        self.assertEqual(text.count("```text"), 2)
        review = mapping.read_text(encoding="utf-8")
        self.assertIn("[00:18.000–00:24.000]: `♪ ♪` is for video-track placement only; omitted", review)
        self.assertIn("Spoken-word differences", review)
        self.assertIn("tahun seribu sembilan", review)
        self.assertIn("Possible timing overruns", review)
        self.assertEqual(warnings, [])

    def test_dense_block_flags_estimated_overrun(self):
        original = self.draft.read_text(encoding="utf-8")
        self.draft.write_text(original.replace("[calm] Pada", "[calm] " + "kata " * 30 + "Pada"), encoding="utf-8")
        _, mapping, _, warnings, _ = build(self.source, self.draft)
        self.assertTrue(warnings)
        self.assertIn("may overrun", mapping.read_text(encoding="utf-8"))

    def test_all_blocks_must_match_in_order(self):
        bad = self.draft.read_text(encoding="utf-8").replace("[00:08.000–00:16.000]", "[00:08.000–00:15.000]")
        self.draft.write_text(bad, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not match source"):
            build(self.source, self.draft)
        self.assertFalse(self.source.with_name("example.voice.md").exists())

    def test_missing_and_extra_blocks_rejected(self):
        blocks = read_source(self.source)
        self.draft.write_text("[00:00.000–00:08.000]\nHi.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "draft has 1 blocks"):
            read_draft(self.draft, blocks)
        self.draft.write_text(self.draft.read_text(encoding="utf-8") + "[00:40.000–00:41.000]\nMore.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "draft has 2 blocks"):
            read_draft(self.draft, blocks)

    def test_no_ssml_and_no_music_replacement(self):
        original = self.draft.read_text(encoding="utf-8")
        self.draft.write_text(original.replace("♪ ♪", "[pause]"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "video-track music/SFX marker"):
            build(self.source, self.draft)
        self.draft.write_text(original.replace("[calm]", "<break time=\"2s\"/>"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SSML breaks"):
            build(self.source, self.draft)
        self.draft.write_text(original.replace("[calm]", "[calm] ♪ ♪"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "cannot appear in spoken text"):
            build(self.source, self.draft)

    def test_length_cap_no_silent_truncation(self):
        original = self.draft.read_text(encoding="utf-8")
        self.draft.write_text(original.replace("[calm]", "[calm] " + "kabar " * 40), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "over the 150-character cap"):
            build(self.source, self.draft, target=100, maximum=150)
        self.assertFalse(self.source.with_name("example.voice.md").exists())

    def test_no_overwrite_without_force(self):
        voice, mapping, *_ = build(self.source, self.draft)
        with self.assertRaisesRegex(ValueError, "output already exists"):
            build(self.source, self.draft)
        self.draft.write_text(self.draft.read_text(encoding="utf-8").replace("SATU", "satu"), encoding="utf-8")
        new_voice, new_mapping, *_ = build(self.source, self.draft, force=True)
        self.assertEqual((voice, mapping), (new_voice, new_mapping))

    def test_full_indonesian_timeline_fixture(self):
        fixture = Path(__file__).parent / "fixtures" / "pulau-tanpa-bandara-bagaimana-warganya-bertahan-id.srt"
        self.source = Path(self.tmp.name) / "example.srt"
        self.source.write_bytes(fixture.read_bytes())
        source_blocks = read_source(self.source)
        self.assertGreater(len(source_blocks), 25)  # real long-form timeline, not a tiny sample
        self.assertTrue(source_blocks[0].music)
        draft_parts = []
        for block in source_blocks:
            text = block.original
            if not block.music and block == source_blocks[1]:
                text = "[calm] " + text
            draft_parts.append(f"{block.anchor}\n{text}")
        self.draft.write_text("\n\n".join(draft_parts) + "\n", encoding="utf-8")
        voice, mapping, count, _, changes = build(self.source, self.draft)
        self.assertGreater(count, 1)
        self.assertEqual(changes, [])
        output = voice.read_text(encoding="utf-8")
        self.assertNotIn("♪", output)
        self.assertNotIn(source_blocks[1].anchor, output)
        segments = [part.split("\n```", 1)[0] for part in output.split("```text\n")[1:]]
        self.assertEqual(len(segments), count)
        self.assertTrue(all(len(segment) <= 900 for segment in segments))
        original_words = [word.casefold() for block in source_blocks if not block.music
                          for word in WORD.findall(block.original)]
        spoken_words = [word.casefold() for segment in segments
                        for word in WORD.findall(spoken(segment))]
        self.assertEqual(spoken_words, original_words)
        review = mapping.read_text(encoding="utf-8")
        for block in source_blocks:
            self.assertIn(block.anchor, review)
        self.assertIn("video-track placement only", review)

    def test_manually_directed_real_example(self):
        examples = Path(__file__).parent.parent / "examples"
        stem = "tristan-opening"
        self.source = Path(self.tmp.name) / f"{stem}.srt"
        self.source.write_bytes((examples / f"{stem}.srt").read_bytes())
        full_fixture = Path(__file__).parent / "fixtures" / "pulau-tanpa-bandara-bagaimana-warganya-bertahan-id.srt"
        source_words = [w.casefold() for b in read_source(self.source) if not b.music for w in WORD.findall(b.original)]
        fixture_words = [w.casefold() for b in read_source(full_fixture)[:22] if not b.music for w in WORD.findall(b.original)]
        self.assertEqual(source_words, fixture_words)
        self.draft.write_bytes((examples / f"{stem}.work.txt").read_bytes())
        voice, mapping, count, _, changes = build(self.source, self.draft)
        self.assertEqual(count, 4)
        self.assertEqual(changes, [])
        self.assertEqual(voice.read_bytes(), (examples / f"{stem}.voice.md").read_bytes())
        self.assertEqual(mapping.read_bytes(), (examples / f"{stem}.voice.map.md").read_bytes())
        self.assertNotIn("♪", voice.read_text(encoding="utf-8"))
        self.assertIn("Video-track music/SFX placement", mapping.read_text(encoding="utf-8"))

    def test_complete_manually_directed_crime_example(self):
        examples = Path(__file__).parent.parent / "examples"
        stem = "rockefeller-full"
        self.source = Path(self.tmp.name) / f"{stem}.srt"
        self.source.write_bytes((examples / f"{stem}.srt").read_bytes())
        self.draft.write_bytes((examples / f"{stem}.work.txt").read_bytes())
        blocks = read_source(self.source)
        self.assertEqual(len(blocks), 452)
        self.assertEqual(sum(b.music for b in blocks), 8)
        self.assertIn("[Co.]", blocks[184].original)
        voice, mapping, count, warnings, changes = build(self.source, self.draft)
        self.assertEqual(count, 144)
        self.assertEqual((warnings, changes), ([], []))
        self.assertEqual(voice.read_bytes(), (examples / f"{stem}.voice.md").read_bytes())
        self.assertEqual(mapping.read_bytes(), (examples / f"{stem}.voice.map.md").read_bytes())
        text = voice.read_text(encoding="utf-8")
        self.assertNotIn("♪", text)
        self.assertNotIn("<!-- beat -->", text)
        self.assertEqual(text.count("```text"), 144)
        self.assertIn("Peabody and Co. serta Nikko", text)
        self.assertNotIn("[Co.]", text)
        review = mapping.read_text(encoding="utf-8")
        self.assertIn("`rockefeller-full.srt`", review)
        self.assertEqual(review.count("`♪ ♪` is for video-track placement only"), 8)
        for block in blocks:
            self.assertIn(block.anchor, review)

    def test_complete_manually_directed_miyako_example(self):
        examples = Path(__file__).parent.parent / "examples"
        stem = "miyako-full"
        self.source = Path(self.tmp.name) / f"{stem}.srt"
        self.source.write_bytes((examples / f"{stem}.srt").read_bytes())
        self.draft.write_bytes((examples / f"{stem}.work.txt").read_bytes())
        blocks = read_source(self.source)
        self.assertEqual(len(blocks), 574)
        self.assertEqual(sum(len(WORD.findall(b.original)) for b in blocks), 3266)
        self.assertEqual(sum(b.music for b in blocks), 0)
        voice, mapping, count, warnings, changes = build(self.source, self.draft)
        self.assertEqual(count, 73)
        self.assertEqual((warnings, changes), ([], []))
        self.assertEqual(voice.read_bytes(), (examples / f"{stem}.voice.md").read_bytes())
        self.assertEqual(mapping.read_bytes(), (examples / f"{stem}.voice.map.md").read_bytes())
        text = voice.read_text(encoding="utf-8")
        self.assertNotIn("♪", text)
        self.assertEqual(text.count("```text"), 73)
        self.assertIn("`miyako-full.srt`", mapping.read_text(encoding="utf-8"))
        for block in blocks:
            self.assertIn(block.anchor, mapping.read_text(encoding="utf-8"))

    def test_complete_manually_directed_giethoorn_example(self):
        examples = Path(__file__).parent.parent / "examples"
        stem = "giethoorn-full"
        self.source = Path(self.tmp.name) / f"{stem}.srt"
        self.source.write_bytes((examples / f"{stem}.srt").read_bytes())
        self.draft.write_bytes((examples / f"{stem}.work.txt").read_bytes())
        blocks = read_source(self.source)
        self.assertEqual(len(blocks), 102)
        self.assertEqual(sum(b.music for b in blocks), 2)
        self.assertEqual(blocks[0].original, "Desa indah yang tak punya jalan raya")
        self.assertTrue(blocks[1].original.startswith("Giethoorn adalah sebuah desa"))
        voice, mapping, count, warnings, changes = build(self.source, self.draft)
        self.assertEqual(count, 15)
        self.assertEqual((warnings, changes), ([], []))
        self.assertEqual(voice.read_bytes(), (examples / f"{stem}.voice.md").read_bytes())
        self.assertEqual(mapping.read_bytes(), (examples / f"{stem}.voice.map.md").read_bytes())
        text = voice.read_text(encoding="utf-8")
        self.assertNotIn("♪", text)
        self.assertEqual(text.count("```text"), 15)
        review = mapping.read_text(encoding="utf-8")
        for block in blocks:
            self.assertIn(block.anchor, review)

    def test_standard_srt_input_and_editor_music_cue(self):
        source = Path(self.tmp.name) / "sample.srt"
        source.write_text(
            "1\n00:00:00,000 --> 00:00:05,000\nJalan itu berhenti\ndi tepi kanal.\n\n"
            "2\n00:00:05,000 --> 00:00:07,000\n♪ ♪\n\n"
            "3\n00:00:07,000 --> 00:00:13,000\nPerahu membawa mereka ke rumah.\n", encoding="utf-8"
        )
        self.draft.write_text(
            "[00:00.000–00:05.000]\n[calm] Jalan itu berhenti di tepi kanal.\n\n"
            "[00:05.000–00:07.000]\n♪ ♪\n\n"
            "[00:07.000–00:13.000]\n[deliberate] Perahu membawa mereka ke rumah.\n", encoding="utf-8"
        )
        voice, mapping, count, warnings, changes = build(source, self.draft)
        self.assertEqual((count, warnings, changes), (2, [], []))
        self.assertNotIn("♪", voice.read_text(encoding="utf-8"))
        self.assertIn("[00:05.000–00:07.000]", mapping.read_text(encoding="utf-8"))
        self.assertEqual(voice.name, "sample.voice.md")

    def test_bracketed_source_abbreviation_is_spoken_without_brackets(self):
        source = Path(self.tmp.name) / "sample.srt"
        source.write_text(
            "1\n00:00:00,000 --> 00:00:05,000\n[SupremeMarshal.] Rao entered the office.\n", encoding="utf-8"
        )
        self.draft.write_text(
            "[00:00.000–00:05.000]\n[calm] SupremeMarshal. Rao entered the office.\n", encoding="utf-8"
        )
        voice, mapping, _, _, changes = build(source, self.draft)
        self.assertEqual(changes, [])
        self.assertIn("SupremeMarshal. Rao entered the office.", voice.read_text(encoding="utf-8"))
        self.assertIn("[SupremeMarshal.] Rao", source.read_text(encoding="utf-8"))
        self.assertIn("[00:00.000–00:05.000]", mapping.read_text(encoding="utf-8"))
        self.draft.write_text(
            "[00:00.000–00:05.000]\n[calm] [SupremeMarshal.] Rao entered the office.\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "write spoken abbreviations without brackets"):
            read_draft(self.draft, read_source(source))

    def test_invalid_srt_cue_rejected(self):
        source = Path(self.tmp.name) / "sample.srt"
        source.write_text("1\n00:00:00,000 --> 00:00:05,000\nFirst line\nSecond line\nThird line\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "expected sequential number"):
            read_source(source)

    def test_reject_legacy_markdown_source(self):
        old = self.source.with_suffix(".md")
        old.write_text("[00:00.000–00:08.000] Test.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "narration .srt"):
            read_source(old)
        with self.assertRaisesRegex(ValueError, "narration .srt"):
            build(old, self.draft)

    def test_multiple_passages_within_one_source_block(self):
        self.source.write_text("1\n00:00:00,000 --> 00:00:30,000\nSatu langkah. Kemudian dua langkah.\nLalu berhenti.\n", encoding="utf-8")
        self.draft.write_text("[00:00.000–00:30.000]\n[calm]\nSatu langkah.\n\n[short pause]\nKemudian dua langkah.\n\n[deliberate]\nLalu berhenti.\n", encoding="utf-8")
        voice, mapping, count, _, changes = build(self.source, self.draft, target=48, maximum=90)
        self.assertGreater(count, 1)
        self.assertEqual(changes, [])
        self.assertIn("passage 1/3", mapping.read_text(encoding="utf-8"))
        self.assertIn("passage 3/3", mapping.read_text(encoding="utf-8"))
        self.assertIn("[short pause]\nKemudian", voice.read_text(encoding="utf-8"))

    def test_large_gap_creates_boundary_and_capped_groups(self):
        source = self.source.read_text(encoding="utf-8").replace("3\n00:00:18,000 --> 00:00:24,000\n♪ ♪\n\n", "").replace("4\n00:00:24,000", "3\n00:00:24,000")
        draft = self.draft.read_text(encoding="utf-8").replace("[00:18.000–00:24.000]\n♪ ♪\n\n", "")
        self.source.write_text(source, encoding="utf-8")
        self.draft.write_text(draft, encoding="utf-8")
        blocks = read_draft(self.draft, read_source(self.source))
        self.assertEqual(len(group(blocks, target=200, maximum=300)), 2)


if __name__ == "__main__":
    unittest.main()
