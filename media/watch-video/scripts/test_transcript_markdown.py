"""Focused tests for the normalized transcript Markdown presentation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import WatchVideoError  # noqa: E402
from transcript_markdown import (  # noqa: E402
    group_transcript_segments,
    render_transcript_markdown,
    write_transcript_markdown,
)


class TranscriptMarkdownTest(unittest.TestCase):
    def test_adjacent_cues_are_grouped_with_coverage_and_text_preserved(self):
        segments = [
            {"start": 1.709, "end": 5.0, "text": "Kenapa sekarang"},
            {"start": 5.1, "end": 17.269, "text": "makin banyak anak muda"},
            {"start": 20.0, "end": 21.0, "text": "Jeda membuat blok baru."},
        ]
        blocks = group_transcript_segments(segments)
        self.assertEqual(len(blocks), 2)
        self.assertEqual((blocks[0].start, blocks[0].end), (1.709, 17.269))
        self.assertEqual(blocks[0].text, "Kenapa sekarang makin banyak anak muda")
        self.assertEqual(blocks[0].segment_indexes, (0, 1))
        self.assertEqual(blocks[1].segment_indexes, (2,))

    def test_overlapping_cues_keep_the_full_block_timestamp_coverage(self):
        blocks = group_transcript_segments([
            {"start": 1.0, "end": 4.0, "text": "first"},
            {"start": 2.0, "end": 3.0, "text": "overlap"},
        ])
        self.assertEqual(len(blocks), 1)
        self.assertEqual((blocks[0].start, blocks[0].end), (1.0, 4.0))
        self.assertEqual(blocks[0].text, "first overlap")

    def test_duration_and_length_limits_prevent_unbounded_paragraphs(self):
        segments = [
            {"start": 0.0, "end": 1.0, "text": "one"},
            {"start": 1.1, "end": 2.0, "text": "two"},
            {"start": 2.1, "end": 3.0, "text": "three"},
        ]
        by_duration = group_transcript_segments(segments, max_block_seconds=2.0)
        self.assertEqual([block.segment_indexes for block in by_duration], [(0, 1), (2,)])
        by_length = group_transcript_segments(segments, max_block_chars=7)
        self.assertEqual([block.segment_indexes for block in by_length], [(0, 1), (2,)])

    def test_header_retains_provenance_quality_and_translation_metadata(self):
        markdown = render_transcript_markdown({
            "source": "translated",
            "source_language": "en",
            "output_language": "id",
            "translation_performed": True,
            "translation_provenance": {"method": "explicit adapter", "source": "automatic"},
            "quality": {
                "confidence": "low-best-effort",
                "strict_usable": False,
                "raw_segments": 4,
                "normalized_segments": 3,
                "duplicate_segments": 1,
                "rolling_segments": 0,
                "unique_text_ratio": 0.75,
                "note": "caption cues contain duplicate windows",
            },
            "segments": [{"start": 0, "end": 1, "text": "Halo dunia"}],
        })
        self.assertIn("- Source: translated", markdown)
        self.assertIn("- Source language: en", markdown)
        self.assertIn("- Output language: id", markdown)
        self.assertIn("- Quality: low-best-effort", markdown)
        self.assertIn("- Quality metrics: raw=4, normalized=3, duplicates=1, rolling=0, unique-text-ratio=0.75", markdown)
        self.assertIn("- Warning: caption cues contain duplicate windows", markdown)
        self.assertIn("- Translation: performed (explicit adapter, automatic)", markdown)
        self.assertIn("- Original transcript: retained separately", markdown)

    def test_empty_transcript_is_a_deterministic_readable_artifact(self):
        payload = {
            "source": "asr",
            "source_language": "id",
            "output_language": "id",
            "translation_performed": False,
            "quality": None,
            "segments": [],
        }
        markdown = render_transcript_markdown(payload)
        self.assertIn("# Transcript\n", markdown)
        self.assertIn("- Source: asr", markdown)
        self.assertIn("- Quality: unknown", markdown)
        self.assertIn("- Segments: 0", markdown)
        self.assertIn("- Blocks: 0", markdown)
        self.assertIn("No transcript segments available.", markdown)
        self.assertNotIn("[00:", markdown)

    def test_file_writer_reads_json_and_is_stable_on_repeated_runs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "004-transcript.json"
            target = root / "004-transcript.md"
            source.write_text(json.dumps({
                "source": "human",
                "language": "id",
                "quality": {"confidence": "high", "usable": True},
                "segments": [
                    {"start": 3599.5, "end": 3600.0, "text": "Satu"},
                    {"start": 3600.1, "end": 3601.0, "text": "Dua"},
                ],
            }), encoding="utf-8")
            write_transcript_markdown(source, target)
            first = target.read_text(encoding="utf-8")
            write_transcript_markdown(source, target)
            self.assertEqual(first, target.read_text(encoding="utf-8"))
            self.assertIn("[59:59.500–01:00:01.000] Satu Dua", first)

    def test_invalid_normalized_cue_is_rejected_instead_of_silently_dropped(self):
        with self.assertRaises(WatchVideoError):
            render_transcript_markdown({
                "source": "automatic",
                "segments": [{"start": 1, "end": 1, "text": "invalid"}],
            })


if __name__ == "__main__":
    unittest.main()
