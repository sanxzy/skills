"""Standard SRT structure, editorial timing, and paired evidence checks."""

from pathlib import Path
import re
import tempfile
import unittest

from validate_script import validate


class SrtTimelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "sample.srt"
        self.source = self.path.with_suffix(".source.md")
        self.source.write_text("Source: https://www.usgs.gov/\n", encoding="utf-8")
        self.words = " ".join(["word"] * 20)

    def cue(self, number, start, end, narration=None):
        return f"{number}\n{start} --> {end}\n{self.words if narration is None else narration}"

    def check_text(self, text, **options):
        self.path.write_text(text, encoding="utf-8")
        return validate(self.path, **options)

    def timeline(self, count):
        # Twenty spoken words in each ten-second cue: 120 WPM.
        def stamp(sec):
            return f"{sec // 3600:02}:{sec // 60 % 60:02}:{sec % 60:02},000"
        return "\n\n".join(self.cue(i + 1, stamp(i * 10), stamp((i + 1) * 10)) for i in range(count))

    def test_handwritten_giethoorn_example_importable_srt(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "bagaimana-hidup-ketika-kanal-menjadi-jalan-id.srt"
        report = validate(path, target_minutes=8.0831)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (102, 694))
        self.assertFalse(any("subtitle readability" in warning for warning in report["warnings"]))
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[0].splitlines()[2], "Desa indah yang tak punya jalan raya")
        self.assertTrue(cues[1].splitlines()[2].startswith("Giethoorn adalah sebuah desa"))
        self.assertEqual(cues[-1].splitlines()[2], "♪ ♪")
        self.assertEqual(cues[-1].splitlines()[0], "102")

    def test_handwritten_nuuk_example_importable_srt(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "kota-di-tepi-es-bagaimana-warganya-hidup-id.srt"
        report = validate(path, target_minutes=8.1012)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (110, 752))
        self.assertFalse(any("subtitle readability" in warning for warning in report["warnings"]))
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[0].splitlines()[2], "Nuuk, kota terbesar di Greenland.")
        self.assertEqual(cues[-1].splitlines()[0], "110")
        self.assertEqual(cues[-1].splitlines()[2], "♪ ♪")

    def test_handwritten_yakutsk_example_importable_srt(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "pasar-musim-dingin-yang-tak-butuh-kulkas-id.srt"
        report = validate(path, target_minutes=8.4396)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (114, 807))
        self.assertFalse(any("subtitle readability" in warning for warning in report["warnings"]))
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[0].splitlines()[2], "♪ ♪")
        self.assertEqual(cues[-1].splitlines()[0], "114")
        self.assertEqual(cues[-1].splitlines()[2], "♪ ♪")

    def test_handwritten_mad_honey_example_importable_srt(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "kenapa-orang-memburu-madu-yang-bisa-meracuni-mereka-id.srt"
        report = validate(path, target_minutes=8.5051)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (138, 866))
        self.assertFalse(any("subtitle readability" in warning for warning in report["warnings"]))
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[0].splitlines()[2], "♪ ♪")
        self.assertEqual(cues[-1].splitlines()[0], "138")
        self.assertEqual(cues[-1].splitlines()[2], "♪ ♪")
        spoken = " ".join(" ".join(cue.splitlines()[2:]) for cue in cues)
        self.assertIn("jumlah kecil pun tidak otomatis aman", spoken)

    def test_handwritten_rockefeller_investigation(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "bagaimana-rockefeller-palsu-menipu-kaum-elite-amerika-id.srt"
        report = validate(path, target_minutes=26.5717)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (452, 2817))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count("\n♪ ♪\n"), 8)
        self.assertIn("[Co.]", text)
        self.assertEqual(text.strip().split("\n\n")[-1].splitlines()[0], "452")

    def test_handwritten_spain_geography_archive(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "gurun-dan-salju-dalam-satu-negara-inilah-spanyol-id.srt"
        report = validate(path, target_minutes=49.2007)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (1073, 5291))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertFalse(any(cue.splitlines()[2] == "♪ ♪" for cue in cues))
        self.assertEqual(cues[-1].splitlines()[0], "1073")

    def test_handwritten_iceland_geography_archive(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "bagaimana-islandia-mengubah-alam-yang-keras-jadi-penghasilan-id.srt"
        report = validate(path, target_minutes=43.445)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (995, 4865))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual([int(cue.splitlines()[0]) for cue in cues if cue.splitlines()[2] == "♪ ♪"], [1, 2, 3])
        self.assertIn("[B.]", cues[55])
        self.assertEqual(cues[-1].splitlines()[0], "995")

    def test_handwritten_indo_pacific_snakes_archive(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "which-snake-is-actually-the-most-dangerous-en.srt"
        report = validate(path, target_minutes=44.1105, max_unspoken_fraction=0.60)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (611, 3542))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(sum(cue.splitlines()[2] == "♪ ♪" for cue in cues), 8)
        self.assertEqual(cues[-1].splitlines()[0], "611")

    def test_handwritten_ames_transcript_archive(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "cia-mencari-pengkhianat-di-dalam-markasnya-sendiri-id.srt"
        report = validate(path, target_minutes=29.4083)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (673, 3428))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual([int(cue.splitlines()[0]) for cue in cues if cue.splitlines()[2] == "♪ ♪"], [1, 2, 23])
        self.assertEqual(cues[-1].splitlines()[0], "673")

    def test_handwritten_hornbill_wildlife_with_visual_gaps(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "why-does-this-bird-seal-itself-inside-a-tree-en.srt"
        report = validate(path, target_minutes=44.1144, max_unspoken_fraction=0.60)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (467, 2935))
        self.assertGreater(report["metrics"]["unspoken_fraction"], 0.34)
        self.assertTrue(path.with_suffix(".source.md").is_file())
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[75].splitlines()[2], "♪ ♪")
        self.assertEqual(cues[-1].splitlines()[0], "467")

    def test_handwritten_english_rockefeller_transcript_example(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "a-fake-rockefeller-fooled-americas-elite-how-en-us.srt"
        report = validate(path, target_minutes=22.405)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (538, 3006))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertIn("[Co.]", cues[216])
        self.assertIn("[U.S.]", cues[357])
        self.assertEqual(cues[-1].splitlines()[0], "538")

    def test_handwritten_kazakhstan_transcript_example(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "kota-megah-di-tengah-padang-kosong-inilah-kazakhstan-id.srt"
        report = validate(path, target_minutes=24.4167)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (552, 2814))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertIn("Salju bahkan bisa menutupi kota", cues[339])
        self.assertEqual(cues[-1].splitlines()[0], "552")

    def test_handwritten_orangutan_wildlife_with_visual_gaps(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "alone-in-the-jungle-how-does-a-young-orangutan-survive-en.srt"
        report = validate(path, target_minutes=47.3648, max_unspoken_fraction=0.60)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (312, 2078))
        self.assertGreater(report["metrics"]["unspoken_fraction"], 0.55)
        self.assertTrue(path.with_suffix(".source.md").is_file())
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(sum(c.splitlines()[2] == "♪ ♪" for c in cues), 14)
        self.assertEqual(cues[-1].splitlines()[0], "312")

    def test_handwritten_tristan_transcript_example(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "pulau-tanpa-bandara-bagaimana-warganya-bertahan-id.srt"
        report = validate(path, target_minutes=24.0167)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (445, 2542))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[0].splitlines()[2], "♪ ♪")
        self.assertEqual(cues[-1].splitlines()[0], "445")

    def test_handwritten_miyako_transcript_example(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "kasus-terungkap-setelah-tersangkanya-meninggal-id.srt"
        report = validate(path, target_minutes=29.4717)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (574, 3266))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("dua hari setelah bagian tubuh", text)
        self.assertNotIn("♪", text)
        self.assertEqual(text.strip().split("\n\n")[-1].splitlines()[0], "574")

    def test_handwritten_animal_compilation_with_real_visual_gaps(self):
        path = Path(__file__).parent.parent / "examples" / "transcript-derived" / "why-some-animals-escape-and-others-dont-en.srt"
        report = validate(path, target_minutes=36.92, max_unspoken_fraction=0.65)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (190, 1566))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        self.assertGreater(report["metrics"]["unspoken_fraction"], 0.59)
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[1].splitlines()[3], "they will get all year.")
        self.assertEqual(cues[-1].splitlines()[2], "♪ ♪")

    def test_handwritten_clouds_researched_example(self):
        path = Path(__file__).parent.parent / "examples" / "clouds-have-water-why-doesnt-it-always-rain.srt"
        report = validate(path, target_minutes=8.65)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (144, 1247))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        self.assertEqual(path.read_text(encoding="utf-8").strip().split("\n\n")[-1].splitlines()[0], "144")

    def test_handwritten_mawsynram_researched_example(self):
        path = Path(__file__).parent.parent / "examples" / "hujan-melimpah-kenapa-desa-ini-bisa-kekurangan-air.srt"
        report = validate(path, target_minutes=9.6783)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (168, 1152))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        self.assertFalse(any("subtitle readability" in warning for warning in report["warnings"]))
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[-1].splitlines()[0], "168")
        rows = re.findall(
            r"^\| C\d{2} \| (\d+)–(\d+), (\d\d:\d\d:\d\d,\d{3})–(\d\d:\d\d:\d\d,\d{3}) \|",
            path.with_suffix(".source.md").read_text(encoding="utf-8"), re.MULTILINE,
        )
        self.assertEqual(len(rows), 23)
        next_cue = 1
        for first, last, start, end in rows:
            first, last = int(first), int(last)
            self.assertEqual(first, next_cue)
            self.assertEqual(cues[first - 1].splitlines()[1].split(" --> ")[0], start)
            self.assertEqual(cues[last - 1].splitlines()[1].split(" --> ")[1], end)
            next_cue = last + 1
        self.assertEqual(next_cue, len(cues) + 1)

    def test_handwritten_hormuz_researched_example(self):
        path = Path(__file__).parent.parent / "examples" / "kenapa-satu-selat-bisa-mengguncang-ekonomi-dunia.srt"
        report = validate(path, target_minutes=10.8817)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (177, 1291))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        self.assertFalse(any("subtitle readability" in warning for warning in report["warnings"]))
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[-1].splitlines()[0], "177")
        rows = re.findall(
            r"^\| C\d{2} \| (\d+)–(\d+), (\d\d:\d\d:\d\d,\d{3})–(\d\d:\d\d:\d\d,\d{3}) \|",
            path.with_suffix(".source.md").read_text(encoding="utf-8"), re.MULTILINE,
        )
        self.assertEqual(len(rows), 24)
        next_cue = 1
        for first, last, start, end in rows:
            first, last = int(first), int(last)
            self.assertEqual(first, next_cue)
            self.assertEqual(cues[first - 1].splitlines()[1].split(" --> ")[0], start)
            self.assertEqual(cues[last - 1].splitlines()[1].split(" --> ")[1], end)
            next_cue = last + 1
        self.assertEqual(next_cue, len(cues) + 1)

    def test_handwritten_putin_researched_example(self):
        path = Path(__file__).parent.parent / "examples" / "seberapa-berbahaya-vladimir-putin.srt"
        report = validate(path, target_minutes=11.92)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (193, 1296))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        self.assertFalse(any("subtitle readability" in warning for warning in report["warnings"]))
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[-1].splitlines()[0], "193")
        rows = re.findall(
            r"^\| C\d{2} \| (\d+)–(\d+), (\d\d:\d\d:\d\d,\d{3})–(\d\d:\d\d:\d\d,\d{3}) \|",
            path.with_suffix(".source.md").read_text(encoding="utf-8"), re.MULTILINE,
        )
        self.assertEqual(len(rows), 24)
        next_cue = 1
        for first, last, start, end in rows:
            first, last = int(first), int(last)
            self.assertEqual(first, next_cue)
            self.assertEqual(cues[first - 1].splitlines()[1].split(" --> ")[0], start)
            self.assertEqual(cues[last - 1].splitlines()[1].split(" --> ")[1], end)
            next_cue = last + 1
        self.assertEqual(next_cue, len(cues) + 1)

    def test_handwritten_ames_researched_example(self):
        path = Path(__file__).parent.parent / "examples" / "pengkhianat-cia-yang-lolos-hampir-9-tahun.srt"
        report = validate(path, target_minutes=11.26)
        self.assertTrue(report["ok"], report)
        self.assertEqual((report["metrics"]["cues"], report["metrics"]["words"]), (188, 1307))
        self.assertTrue(path.with_suffix(".source.md").is_file())
        self.assertFalse(any("subtitle readability" in warning for warning in report["warnings"]))
        cues = path.read_text(encoding="utf-8").strip().split("\n\n")
        self.assertEqual(cues[0].splitlines()[2].split()[0], "Jaringan")
        self.assertEqual(cues[-1].splitlines()[0], "188")
        rows = re.findall(
            r"^\| C\d{2} \| (\d+)–(\d+), (\d\d:\d\d:\d\d,\d{3})–(\d\d:\d\d:\d\d,\d{3}) \|",
            path.with_suffix(".source.md").read_text(encoding="utf-8"), re.MULTILINE,
        )
        self.assertEqual(len(rows), 26)
        next_cue = 1
        for first, last, start, end in rows:
            first, last = int(first), int(last)
            self.assertEqual(first, next_cue)
            self.assertEqual(cues[first - 1].splitlines()[1].split(" --> ")[0], start)
            self.assertEqual(cues[last - 1].splitlines()[1].split(" --> ")[1], end)
            next_cue = last + 1
        self.assertEqual(next_cue, len(cues) + 1)

    def test_default_eight_minutes_with_short_cues(self):
        report = self.check_text(self.timeline(48))
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["metrics"]["cues"], 48)
        self.assertEqual(report["metrics"]["words"], 960)
        self.assertEqual(report["metrics"]["timeline_seconds"], 480)

    def test_explicit_duration_and_hour_timecode(self):
        self.assertTrue(self.check_text(self.timeline(30), target_minutes=5)["ok"])
        self.assertTrue(self.check_text(self.timeline(72), target_minutes=12)["ok"])
        self.assertTrue(self.check_text(self.timeline(120), target_minutes=20)["ok"])
        self.assertTrue(self.check_text(self.cue(1, "01:00:00,000", "01:00:10,000"),
                                        target_minutes=60 + 1/6, max_unspoken_fraction=1)["ok"])

    def test_music_cue_stays_in_srt_but_is_not_spoken(self):
        text = "\n\n".join([self.cue(1, "00:00:00,000", "00:00:10,000"),
                              self.cue(2, "00:00:10,000", "00:00:12,000", "♪ ♪"),
                              self.cue(3, "00:00:12,000", "00:00:22,000")])
        report = self.check_text(text, target_minutes=22/60)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["metrics"]["unspoken_seconds"], 2)
        mixed = self.cue(1, "00:00:00,000", "00:00:10,000", "♪ ♪\nNarration follows the music.")
        self.assertTrue(any("must be the only text" in e for e in
                            self.check_text(mixed, target_minutes=1/6)["errors"]))

    def test_one_sentence_per_cue_with_numeric_period_and_bracketed_abbreviation(self):
        text = self.cue(1, "00:00:00,000", "00:00:05,000", "[Archmagister.] Rao measured 2.795 liters of rain in one year.")
        self.assertTrue(self.check_text(text, target_minutes=1/12)["ok"])
        plain = self.cue(1, "00:00:00,000", "00:00:05,000", "Mr. Rao measured 2.795 liters of rain in one year.")
        self.assertTrue(any("more than one sentence" in e for e in self.check_text(plain, target_minutes=1/12)["errors"]))
        acronym = self.cue(1, "00:00:00,000", "00:00:05,000", "The [U.S.] delegation measured the river after the storm ended.")
        self.assertTrue(self.check_text(acronym, target_minutes=1/12)["ok"])
        two_sentences = self.cue(1, "00:00:00,000", "00:00:10,000", "The river rose. Roads became impassable.")
        result = self.check_text(two_sentences, target_minutes=1/6)
        self.assertFalse(result["ok"])
        self.assertTrue(any("more than one sentence" in e for e in result["errors"]))
        two_questions = self.cue(1, "00:00:00,000", "00:00:10,000", "Why did it rise? Where did the water go?")
        self.assertFalse(self.check_text(two_questions, target_minutes=1/6)["ok"])

    def test_two_visual_lines_are_one_spoken_sentence(self):
        cue = self.cue(1, "00:00:00,000", "00:00:05,000",
                       "We need to finish this today,\nso we can leave early tomorrow.")
        report = self.check_text(cue, target_minutes=1/12)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["metrics"]["words"], 12)
        self.assertFalse(self.check_text(cue.replace("today,", "today."), target_minutes=1/12)["ok"])
        self.assertFalse(self.check_text(cue + "\nA third subtitle line.", target_minutes=1/12)["ok"])

    def test_malformed_numbering_timestamp_and_three_visual_lines_rejected(self):
        base = self.cue(1, "00:00:00,000", "00:00:10,000")
        for bad in [base.replace("1\n", "2\n", 1),
                    base.replace(" --> ", " → "),
                    base.replace("00:00:00,000", "00:00:00.000"),
                    base.replace("00:00:10,000", "00:60:10,000"),
                    base + "\nAnother spoken line.\nA third subtitle line.",
                    base.replace(self.words, "")]:
            with self.subTest(bad=bad[:35]):
                self.assertFalse(self.check_text(bad, target_minutes=1/6)["ok"])

    def test_overlap_backward_and_zero_duration_rejected(self):
        for text in [self.cue(1, "00:00:00,000", "00:00:00,000"),
                     self.cue(1, "00:00:10,000", "00:00:00,000"),
                     self.cue(1, "00:00:00,000", "00:00:10,000") + "\n\n" +
                     self.cue(2, "00:00:09,000", "00:00:19,000")]:
            self.assertFalse(self.check_text(text, target_minutes=1/3)["ok"])

    def test_overlong_spoken_cues_rejected(self):
        self.assertFalse(self.check_text(self.cue(1, "00:00:00,000", "00:00:20,000"),
                                         target_minutes=1/3)["ok"])
        forty_words = " ".join(["word"] * 40)
        self.assertFalse(self.check_text(self.cue(1, "00:00:00,000", "00:00:15,000", forty_words),
                                         target_minutes=1/4)["ok"])

    def test_unreasonably_fast_or_sparse_runtime_rejected(self):
        self.assertFalse(self.check_text(self.cue(1, "00:00:00,000", "00:00:01,000"),
                                         target_minutes=1/60)["ok"])
        self.assertFalse(self.check_text(self.cue(1, "00:00:00,000", "00:00:10,000") + "\n\n" +
                                         self.cue(2, "00:07:50,000", "00:08:00,000"))["ok"])

    def test_metadata_urls_and_labels_rejected(self):
        for line in ["# Title", "https://example.com", "[S01]", "[S01.]", "[stage direction.]", "Hook: narration"]:
            self.assertFalse(self.check_text(self.cue(1, "00:00:00,000", "00:00:10,000", line),
                                             target_minutes=1/6)["ok"])
        label = "Chapter 1: " + self.words
        self.assertTrue(self.check_text(self.cue(1, "00:00:00,000", "00:00:10,000", label),
                                        target_minutes=1/6, allow_spoken_labels=True)["ok"])

    def test_source_file_required_and_md_timeline_not_accepted(self):
        self.source.unlink()
        self.assertFalse(self.check_text(self.timeline(48))["ok"])
        self.path = Path(self.temp.name) / "sample.md"
        self.assertFalse(self.check_text("[00:00.000–00:10.000] " + self.words,
                                         target_minutes=1/6)["ok"])


if __name__ == "__main__":
    unittest.main()
