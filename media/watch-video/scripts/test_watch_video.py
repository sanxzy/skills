"""Hermetic behavior tests for the watch-video extraction helpers."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bootstrap_ytdlp import LocalYtDlp, ensure_local_yt_dlp  # noqa: E402
from cache import CacheStore  # noqa: E402
from common import MAX_METADATA_OUTPUT, ToolUnavailableError, WatchVideoError, normalize_url, parse_time_range, parse_timestamp, run_command  # noqa: E402
from frame_sampler import sample_frames, select_timestamps  # noqa: E402
from media_assets import _download_command, find_binary  # noqa: E402
from media_cache import AUDIO_NAME, ensure_audio, ensure_video, load_video, media_cache_key, store_transcript  # noqa: E402
from resolve_media import YtDlpTool, find_yt_dlp, normalize_metadata, resolve_media  # noqa: E402
from timeline import focus_ranges_from_matches, search_transcript  # noqa: E402
from translate_transcript import translate_segments  # noqa: E402
from transcript import _subtitle_choices, acquire_subtitles, choose_subtitle_track, normalize_segments, parse_caption_text, segments_from_artifact, TranscriptSegment  # noqa: E402
from watch_video import WatchConfig, _parser, run_watch  # noqa: E402


class WatchVideoHelpersTest(unittest.TestCase):
    def test_url_normalization_removes_tracking_without_losing_video_query(self):
        actual = normalize_url("HTTPS://Example.COM/watch?v=abc&utm_source=news&si=123#fragment")
        self.assertEqual(actual, "https://example.com/watch?v=abc")

    def test_embedded_credentials_are_rejected(self):
        with self.assertRaises(WatchVideoError):
            normalize_url("https://user:secret@example.com/video")

    def test_timestamp_and_range_parser_accepts_seconds_and_clock_values(self):
        self.assertEqual(parse_timestamp("90.5"), 90.5)
        self.assertEqual(parse_timestamp("01:30"), 90.0)
        self.assertEqual(parse_timestamp("00:01:30.250"), 90.25)
        self.assertEqual(parse_time_range("00:01:00-00:02:30", duration=180), (60.0, 150.0))

    def test_shell_free_command_runner_preserves_explicit_boundary(self):
        calls = []

        def fake_runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return SimpleNamespace(returncode=0, stdout="ok", stderr="")

        result = run_command(["tool", "literal;not-shell"], runner=fake_runner, timeout=2)
        self.assertTrue(result.ok)
        self.assertEqual(calls[0][0], ["tool", "literal;not-shell"])
        self.assertFalse(calls[0][1]["shell"])

    def test_video_download_format_includes_audio_stream(self):
        command = _download_command(
            YtDlpTool(("yt-dlp",), "yt-dlp"),
            "https://example.com/video",
            Path("video.%(ext)s"),
            mode="video",
            cookies=None,
            cookies_from_browser=None,
        )
        format_index = command.index("--format")
        self.assertEqual(
            command[format_index + 1],
            "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        )

    def test_existing_venv_is_updated_in_place_and_unrelated_files_survive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            venv = root / ".venv"
            bin_dir = venv / "bin"
            bin_dir.mkdir(parents=True)
            (venv / "pyvenv.cfg").write_text(
                "home = /trusted/python\ninclude-system-site-packages = false\n",
                encoding="utf-8",
            )
            python = bin_dir / "python"
            python.write_text("#!/bin/sh\n", encoding="utf-8")
            python.chmod(0o755)
            sentinel = venv / "project-package-sentinel.txt"
            sentinel.write_text("keep me", encoding="utf-8")
            calls = []

            def fake_runner(argv, **kwargs):
                calls.append((argv, kwargs))
                if "-c" in argv:
                    return SimpleNamespace(returncode=0, stdout="2026.9\n", stderr="")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            tool = ensure_local_yt_dlp(root, runner=fake_runner, timeout=10)
            self.assertEqual(tool.venv, venv.resolve())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep me")
            pip_calls = [(argv, kwargs) for argv, kwargs in calls if "-m" in argv and "pip" in argv]
            self.assertEqual(len(pip_calls), 1)
            pip_argv, pip_call = pip_calls[0]
            self.assertFalse(any("venv" in argv for argv, _ in calls if "-m" in argv and "venv" in argv))
            self.assertIn("--isolated", pip_argv)
            self.assertIn("--upgrade", pip_argv)
            self.assertIn("yt-dlp", pip_argv)
            self.assertNotIn("PIP_TARGET", pip_call["env"])
            self.assertTrue(Path(pip_call["env"]["PIP_CACHE_DIR"]).resolve().is_relative_to(venv.resolve()))
            self.assertTrue((venv / "001-watch-video-yt-dlp.json").is_file())

    def test_missing_venv_is_created_then_yt_dlp_is_installed_locally(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = []

            def fake_runner(argv, **kwargs):
                calls.append((argv, kwargs))
                if "-m" in argv and "venv" in argv:
                    venv = root / ".venv"
                    (venv / "bin").mkdir(parents=True)
                    (venv / "pyvenv.cfg").write_text(
                        "home = /trusted/python\ninclude-system-site-packages = false\n",
                        encoding="utf-8",
                    )
                    python = venv / "bin" / "python"
                    python.write_text("#!/bin/sh\n", encoding="utf-8")
                    python.chmod(0o755)
                if "-c" in argv:
                    return SimpleNamespace(returncode=0, stdout="2026.9\n", stderr="")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            tool = ensure_local_yt_dlp(root, runner=fake_runner, timeout=10)
            self.assertTrue(tool.venv.is_dir())
            self.assertTrue((tool.venv / "001-watch-video-yt-dlp.json").is_file())
            self.assertTrue(any("-m" in argv and "venv" in argv for argv, _ in calls))
            self.assertTrue(any("-m" in argv and "pip" in argv for argv, _ in calls))

    def test_malformed_existing_venv_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            venv = root / ".venv"
            venv.mkdir()
            sentinel = venv / "keep.txt"
            sentinel.write_text("unchanged", encoding="utf-8")
            with self.assertRaises(ToolUnavailableError):
                ensure_local_yt_dlp(root, runner=lambda *args, **kwargs: self.fail("must not run"))
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")

    def test_missing_global_yt_dlp_is_routed_to_local_bootstrap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            local = LocalYtDlp(root / ".venv", root / ".venv" / "bin" / "python", "2026.9")
            with patch("resolve_media.shutil.which", return_value=None), \
                 patch("resolve_media.trusted_module_available", return_value=False), \
                 patch("resolve_media.ensure_local_yt_dlp", return_value=local) as setup:
                tool = find_yt_dlp(cwd=root)
            setup.assert_called_once()
            self.assertEqual(tool.argv, local.argv)

    def test_existing_project_venv_is_discovered_before_global_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".venv").mkdir()
            local = LocalYtDlp(root / ".venv", root / ".venv" / "bin" / "python", "2026.9")
            with patch("resolve_media.ensure_local_yt_dlp", return_value=local) as setup, \
                 patch("resolve_media.shutil.which", return_value=None) as which, \
                 patch("resolve_media.trusted_module_available", return_value=False):
                tool = find_yt_dlp(cwd=root)
            setup.assert_called_once_with(root, timeout=900.0, runner=None)
            which.assert_not_called()
            self.assertEqual(tool.argv, local.argv)

    def test_human_subtitles_win_over_automatic_even_when_language_differs(self):
        choice = choose_subtitle_track(
            {
                "language": "en",
                "subtitles": {"id": [{"ext": "vtt"}]},
                "automatic_captions": {"en": [{"ext": "vtt"}]},
            },
            preferred_languages=("en",),
        )
        self.assertEqual(choice.source, "human")
        self.assertEqual(choice.language, "id")

    def test_bounded_subtitle_policy_prioritizes_requested_language_variants(self):
        choices = _subtitle_choices(
            {
                "subtitles": {"en": [{}]},
                "automatic_captions": {
                    "id": [{}],
                    "id-orig": [{}],
                    "en": [{}],
                    "fr": [{}],
                    "de": [{}],
                },
            },
            ("id",),
            max_attempts=4,
            target_first=True,
        )
        self.assertEqual(
            [(item.source, item.language) for item in choices[:2]],
            [("automatic", "id"), ("automatic", "id-orig")],
        )
        self.assertNotIn("fr", [item.language for item in choices])

    def test_subtitle_failures_are_bounded_and_429_warnings_are_aggregated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "rate-limited-yt-dlp"
            fake.write_text("#!/bin/sh\necho 'HTTP Error 429: Too Many Requests' >&2\nexit 1\n", encoding="utf-8")
            fake.chmod(0o755)
            info = {"automatic_captions": {f"lang-{index:02d}": [{}] for index in range(10)}}
            result = acquire_subtitles(
                "https://example.com/video",
                info,
                root / "relative-subtitles",
                preferred_languages=("lang-00", "lang-01", "lang-02", "lang-03", "lang-04"),
                max_attempts=4,
                yt_dlp=str(fake),
            )
            self.assertEqual(result.status, "unavailable")
            self.assertEqual(result.attempted, 4)
            self.assertEqual(result.advertised, 10)
            self.assertTrue(any("4 subtitle language attempts returned HTTP 429" in warning for warning in result.warnings))
            self.assertLessEqual(len(result.warnings), 3)

    def test_relative_subtitle_destination_is_resolved_before_provider_invocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "fake-yt-dlp"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "output = pathlib.Path(args[args.index('--output') + 1].replace('%(ext)s', 'vtt'))\n"
                "output.parent.mkdir(parents=True, exist_ok=True)\n"
                "output.write_text('WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\nhello\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            with patch("transcript.Path.cwd", return_value=root):
                result = acquire_subtitles(
                    "https://example.com/video",
                    {"subtitles": {"en": [{}]}},
                    Path("relative-subtitles"),
                    yt_dlp=str(fake),
                )
            self.assertEqual(result.status, "usable")
            self.assertEqual(result.path.parent.parent, root.resolve() / "relative-subtitles")
            self.assertTrue(result.path.is_file())

    def test_caption_parser_removes_rolling_window_overlap_and_reports_it(self):
        records = parse_caption_text(
            """WEBVTT\n\n00:00:00.000 --> 00:00:02.000\nHello this is a rolling caption\n\n00:00:02.100 --> 00:00:04.000\nHello this is a rolling caption with more\n\n00:00:04.100 --> 00:00:06.000\nHello this is a rolling caption with more words\n"""
        )
        segments, quality = normalize_segments(records)
        self.assertFalse(quality.usable)
        self.assertEqual(quality.rolling_segments, 2)
        self.assertEqual([item.text for item in segments], [
            "Hello this is a rolling caption", "with more", "words",
        ])

    def test_dominant_exact_duplicate_caption_track_is_not_canonical(self):
        records = [(index * 1.1, index * 1.1 + 1, "same caption") for index in range(4)]
        _, quality = normalize_segments(records)
        self.assertFalse(quality.usable)
        self.assertGreater(quality.duplicate_segments, 0)

    def test_recoverable_human_track_uses_best_effort_cleaning(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "fake-yt-dlp.py"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "output = pathlib.Path(args[args.index('--output') + 1].replace('%(ext)s', 'vtt'))\n"
                "output.parent.mkdir(parents=True, exist_ok=True)\n"
                "if '--write-subs' in args:\n"
                "    text = 'WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\nsame\\n\\n00:00:01.100 --> 00:00:02.000\\nsame\\n\\n00:00:02.100 --> 00:00:03.000\\nsame\\n\\n00:00:03.100 --> 00:00:04.000\\nsame\\n'\n"
                "else:\n"
                "    text = 'WEBVTT\\n\\n00:00:00.000 --> 00:00:02.000\\nAutomatic caption is usable.\\n'\n"
                "output.write_text(text)\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            result = acquire_subtitles(
                "https://example.com/video",
                {
                    "subtitles": {"en": [{"ext": "vtt"}]},
                    "automatic_captions": {"en": [{"ext": "vtt"}]},
                },
                root / "subtitles",
                yt_dlp=str(fake),
            )
            self.assertEqual(result.status, "best_effort")
            self.assertEqual(result.choice.source, "human")
            self.assertEqual(result.quality.confidence, "low-best-effort")
            self.assertEqual(result.segments[0].text, "same")

    def test_unrecoverable_human_track_falls_through_to_automatic_captions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "fake-yt-dlp"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "output = pathlib.Path(args[args.index('--output') + 1].replace('%(ext)s', 'vtt'))\n"
                "output.parent.mkdir(parents=True, exist_ok=True)\n"
                "if '--write-subs' in args:\n"
                "    output.write_text('WEBVTT\\n\\nmalformed human track\\n')\n"
                "else:\n"
                "    output.write_text('WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\nautomatic fallback\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            result = acquire_subtitles(
                "https://example.com/video",
                {
                    "subtitles": {"en": [{}]},
                    "automatic_captions": {"en": [{}]},
                },
                root / "subtitles",
                yt_dlp=str(fake),
            )
            self.assertEqual(result.status, "usable")
            self.assertEqual(result.choice.source, "automatic")
            self.assertEqual(result.segments[0].text, "automatic fallback")

    def test_periodic_sampler_uses_interval_and_keeps_requested_point(self):
        candidates = select_timestamps(
            10,
            frame_interval=2,
            requested_times=[7.5],
        )
        timestamps = [item.timestamp for item in candidates]
        self.assertEqual(timestamps[:4], [0.0, 2.0, 4.0, 6.0])
        self.assertIn(7.5, timestamps)
        self.assertEqual(timestamps[-1], 9.95)
        requested = [item for item in candidates if abs(item.timestamp - 7.5) < 0.001]
        self.assertEqual(len(requested), 1)
        self.assertIn("requested", requested[0].signals)

    def test_periodic_sampler_has_no_frame_count_cap(self):
        candidates = select_timestamps(20, frame_interval=1)
        self.assertEqual(len(candidates), 21)
        self.assertEqual(candidates[0].timestamp, 0.0)
        self.assertEqual(candidates[-1].timestamp, 19.95)

    def test_periodic_sampler_rejects_non_positive_interval(self):
        with self.assertRaises(WatchVideoError):
            select_timestamps(10, frame_interval=0)

    def test_explicit_ffmpeg_symlink_resolves_to_a_runnable_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "real-ffmpeg"
            target.write_text("#!/bin/sh\n", encoding="utf-8")
            target.chmod(0o755)
            link = root / "ffmpeg"
            link.symlink_to(target)
            self.assertEqual(find_binary("ffmpeg", str(link)), str(target.resolve()))

    def test_transcript_search_returns_timestamped_evidence_and_focus_range(self):
        segments = [
            {"start": 10, "end": 12, "text": "The cache is enabled here."},
            {"start": 80, "end": 82, "text": "The deployment starts later."},
        ]
        matches = search_transcript(segments, "where do they discuss caching")
        self.assertEqual(matches[0]["start"], 10)
        ranges = focus_ranges_from_matches(matches, duration=100, context_seconds=5)
        self.assertEqual(ranges, ((5.0, 17.0),))

    def test_metadata_output_uses_a_dedicated_bound_and_rejects_truncation(self):
        payload = {"extractor_key": "Youtube", "id": "abc", "title": "Demo", "duration": 4}
        output = json.dumps(payload)
        result = run_command(
            ["fake-yt-dlp"],
            runner=lambda argv, **kwargs: SimpleNamespace(returncode=0, stdout=output, stderr=""),
            output_limit=8,
        )
        self.assertTrue(result.output_truncated)

        with tempfile.TemporaryDirectory() as temporary:
            tool = Path(temporary) / "fake-yt-dlp"
            tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            tool.chmod(0o755)
            oversized = json.dumps({"extractor_key": "Youtube", "id": "abc", "description": "x" * MAX_METADATA_OUTPUT})
            with self.assertRaises(WatchVideoError) as raised:
                resolve_media(
                    "https://youtube.com/watch?v=abc",
                    yt_dlp=str(tool),
                    runner=lambda argv, **kwargs: SimpleNamespace(
                        returncode=0,
                        stdout=oversized,
                        stderr="",
                    ),
                )
            self.assertEqual(raised.exception.status, "source_unavailable")
            self.assertIn("bounded structured-output", str(raised.exception))

    def test_metadata_normalization_omits_signed_urls_and_absent_fields(self):
        source = normalize_metadata(
            {
                "extractor_key": "Youtube",
                "id": "abc",
                "title": "Example",
                "uploader": "Creator",
                "formats": [{"format_id": "18", "url": "https://signed.invalid/x", "height": 720}],
                "subtitles": {"en": [{"ext": "vtt", "url": "https://signed.invalid/sub"}]},
            },
            "https://youtube.com/watch?v=abc",
        )
        self.assertEqual(source["platform"], "youtube")
        self.assertEqual(source["creator"], "Creator")
        self.assertNotIn("duration", source)
        self.assertNotIn("url", source["available_formats"][0])
        self.assertNotIn("url", source["available_subtitles"][0].get("formats", [{}])[0])

    def test_cache_publishes_semantic_files_atomically_and_rewrites_frame_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            task = workspace / ".artifacts" / "watch-video" / "cache-task"
            run_dir = task / "001-attempt-20260915-000000-abcd1234"
            frames = run_dir / "006-frames"
            frames.mkdir(parents=True)
            metadata = run_dir / "003-metadata.json"
            timeline = run_dir / "005-timeline.json"
            frame = frames / "001-frame-000000001000.jpg"
            metadata.write_text('{"title": "Example"}', encoding="utf-8")
            timeline.write_text('{"segments": []}', encoding="utf-8")
            frame.write_bytes(b"image")
            context = {
                "status": "complete",
                "extraction_status": "complete",
                "source": {"url": "https://example.com/video", "platform": "example", "id": "1"},
                "content": {"transcript_policy": "best-effort", "transcript_available": False},
                "artifacts": {
                    "metadata": str(metadata.relative_to(workspace)),
                    "timeline": str(timeline.relative_to(workspace)),
                    "frames": [{"timestamp": 1, "path": str(frame.relative_to(workspace))}],
                },
            }
            context_path = run_dir / "007-context.json"
            context_path.write_text(json.dumps(context), encoding="utf-8")
            store = CacheStore(workspace, task_directory=task)
            stored = store.store(
                "https://example.com/video",
                context["source"],
                run_dir,
                artifact_files={
                    "context": context_path,
                    "metadata": metadata,
                    "timeline": timeline,
                    "frames": frames,
                },
            )
            self.assertIsNotNone(stored)
            hit = store.lookup("https://example.com/video", needs_visual=True)
            self.assertIsNotNone(hit)
            cached_frame = workspace / hit.context["artifacts"]["frames"][0]["path"]
            self.assertTrue(cached_frame.is_file())
            self.assertNotEqual(cached_frame, frame)
            self.assertTrue(cached_frame.name.startswith("001-frame-"))
            context["status"] = "partial"
            context_path.write_text(json.dumps(context), encoding="utf-8")
            self.assertIsNone(store.store(
                "https://example.com/video",
                context["source"],
                run_dir,
                artifact_files={
                    "context": context_path,
                    "metadata": metadata,
                    "timeline": timeline,
                    "frames": frames,
                },
            ))
            self.assertIsNotNone(store.lookup("https://example.com/video", needs_visual=True))

    def test_visual_sampling_attaches_nearby_speech_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ffmpeg = root / "ffmpeg"
            ffmpeg.write_text("#!/bin/sh\n", encoding="utf-8")
            ffmpeg.chmod(0o755)
            video = root / "video.mp4"
            video.write_bytes(b"video")

            def fake_runner(argv, **kwargs):
                if "-f" in argv and "null" in argv:
                    return SimpleNamespace(returncode=0, stdout="", stderr="pts_time:2.000")
                Path(argv[-1]).write_bytes(b"frame")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            sampled = sample_frames(
                video,
                root / "frames",
                10,
                transcript=[{"start": 2, "end": 3, "text": "spoken"}],
                frame_interval=2,
                ffmpeg=str(ffmpeg),
                runner=fake_runner,
            )
            self.assertEqual(sampled.alignment_status, "aligned")
            self.assertEqual(sampled.aligned_frames, len(sampled.frames))
            self.assertTrue(sampled.frames)
            self.assertTrue(all(frame["speech_interval_ids"] for frame in sampled.frames))
            self.assertEqual(sampled.frames[0]["nearby_speech_intervals"][0]["id"], "speech-0001")

    def test_translation_adapter_preserves_timestamps_and_keeps_source_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            translator = root / "translator"
            translator.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "source = json.loads(pathlib.Path(args[args.index('--input') + 1]).read_text())\n"
                "output = pathlib.Path(args[args.index('--output') + 1])\n"
                "output.write_text(json.dumps({'segments': [{'text': 'Halo dunia'} for _ in source['segments']]}))\n",
                encoding="utf-8",
            )
            translator.chmod(0o755)
            result = translate_segments(
                (TranscriptSegment(1.0, 2.5, "Hello world"),),
                source_language="en",
                target_language="id",
                destination=root / "translation",
                command_template=f"{translator} --input {{input}} --output {{output}}",
            )
            self.assertEqual(result.status, "usable")
            self.assertEqual(result.segments[0].as_dict(), {"start": 1.0, "end": 2.5, "text": "Halo dunia"})
            self.assertEqual(result.chunks, 1)

    def test_persistent_video_cache_downloads_once_and_refreshes_explicitly(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            counter = root / "download-count.txt"
            fake = root / "fake-yt-dlp"
            fake.write_text(
                f"#!/usr/bin/env python3\n"
                f"import pathlib, sys\n"
                f"counter = pathlib.Path({str(counter)!r})\n"
                "args = sys.argv[1:]\n"
                "if '--output' not in args:\n"
                "    raise SystemExit(0)\n"
                "template = args[args.index('--output') + 1]\n"
                "if '001-video' in template:\n"
                "    output = pathlib.Path(template.replace('%(ext)s', 'mp4'))\n"
                "    output.parent.mkdir(parents=True, exist_ok=True)\n"
                "    output.write_bytes(b'fake-video')\n"
                "    count = int(counter.read_text() if counter.exists() else '0') + 1\n"
                "    counter.write_text(str(count))\n"
                "else:\n"
                "    output = pathlib.Path(template.replace('%(ext)s', 'vtt'))\n"
                "    output.parent.mkdir(parents=True, exist_ok=True)\n"
                "    output.write_text('WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\nhello\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            cache_root = root / "local-videos"
            first, downloaded, _ = ensure_video(
                "https://example.com/watch?v=one",
                root=cache_root,
                yt_dlp=str(fake),
            )
            second, downloaded_again, _ = ensure_video(
                "https://example.com/watch?v=one",
                root=cache_root,
                yt_dlp="/definitely/missing/yt-dlp",
            )
            refreshed, refreshed_download, _ = ensure_video(
                "https://example.com/watch?v=one",
                root=cache_root,
                yt_dlp=str(fake),
                refresh=True,
            )
            fallback, failed_refresh_download, failed_refresh_tool = ensure_video(
                "https://example.com/watch?v=one",
                root=cache_root,
                yt_dlp="/definitely/missing/yt-dlp",
                refresh=True,
            )
            self.assertTrue(downloaded)
            self.assertFalse(downloaded_again)
            self.assertTrue(refreshed_download)
            self.assertFalse(failed_refresh_download)
            self.assertEqual(failed_refresh_tool, "cache-fallback")
            self.assertEqual(counter.read_text(), "2")
            self.assertEqual(first.video_path, second.video_path)
            self.assertEqual(refreshed.video_path, first.video_path)
            self.assertEqual(fallback.video_path, first.video_path)
            self.assertEqual(first.key, media_cache_key("https://example.com/watch?v=one"))
            self.assertTrue((first.directory / "000-manifest.json").is_file())
            self.assertTrue(first.video_path.name.startswith("001-video."))
            stored_transcript = store_transcript(
                first,
                {
                    "source": "automatic",
                    "language": "en",
                    "source_language": "en",
                    "output_language": "en",
                    "translation_performed": False,
                    "quality": {"confidence": "high"},
                    "segments": [{"start": 0, "end": 1, "text": "hello"}],
                },
            )
            self.assertIsNotNone(stored_transcript)
            self.assertIsNotNone(load_video("https://example.com/watch?v=one", root=cache_root).read_transcript())
            refreshed_again, _, _ = ensure_video(
                "https://example.com/watch?v=one",
                root=cache_root,
                yt_dlp=str(fake),
                refresh=True,
            )
            self.assertIsNone(refreshed_again.read_transcript())
            self.assertIsNotNone(load_video("https://example.com/watch?v=one", root=cache_root))
            for path in first.directory.rglob("*"):
                if path.is_file():
                    self.assertRegex(path.name, r"^\d{3,}-", path)

    def test_pipeline_preserves_source_and_target_transcript_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "fake-yt-dlp"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "if '--dump-single-json' in args:\n"
                "    print(json.dumps({'extractor_key': 'Fake', 'id': 'translate', 'title': 'Demo', 'duration': 4, 'language': 'en', 'subtitles': {'en': [{'ext': 'vtt'}]}}))\n"
                "else:\n"
                "    template = args[args.index('--output') + 1]\n"
                "    if '001-video' in template:\n"
                "        output = pathlib.Path(template.replace('%(ext)s', 'mp4'))\n"
                "        output.parent.mkdir(parents=True, exist_ok=True)\n"
                "        output.write_bytes(b'fake-video')\n"
                "    else:\n"
                "        output = pathlib.Path(template.replace('%(ext)s', 'vtt'))\n"
                "        output.parent.mkdir(parents=True, exist_ok=True)\n"
                "        output.write_text('WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\nHello world\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            translator = root / "translator"
            translator.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "source = json.loads(pathlib.Path(args[args.index('--input') + 1]).read_text())\n"
                "output = pathlib.Path(args[args.index('--output') + 1])\n"
                "output.write_text(json.dumps({'segments': [{'text': 'Halo dunia'} for _ in source['segments']]}))\n",
                encoding="utf-8",
            )
            translator.chmod(0o755)
            context = run_watch(WatchConfig(
                url="https://example.com/translate",
                workspace=root,
                media_cache_root=root / "media-cache",
                cache="off",
                visual="never",
                yt_dlp=str(fake),
                preferred_languages=("id",),
                translation_command=f"{translator} --input {{input}} --output {{output}}",
                task_name="translation-task",
            ))
            self.assertEqual(context["status"], "complete")
            self.assertTrue(context["content"]["transcript_translation_performed"])
            self.assertEqual(context["content"]["transcript_source_language"], "en")
            self.assertEqual(context["content"]["transcript_output_language"], "id")
            self.assertIn("transcript_original", context["artifacts"])
            self.assertIn("transcript_markdown", context["artifacts"])
            output_path = root / context["artifacts"]["transcript"]
            source_path = root / context["artifacts"]["transcript_original"]
            markdown_path = root / context["artifacts"]["transcript_markdown"]
            self.assertEqual(json.loads(output_path.read_text())["segments"][0]["text"], "Halo dunia")
            self.assertEqual(json.loads(source_path.read_text())["segments"][0]["text"], "Hello world")
            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("- Source: translated", markdown)
            self.assertIn("- Source language: en", markdown)
            self.assertIn("- Output language: id", markdown)
            self.assertIn("Halo dunia", markdown)

    def test_pipeline_reuses_persistent_video_and_transcript_across_tasks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            video_count = root / "video-count"
            subtitle_count = root / "subtitle-count"
            fake = root / "fake-yt-dlp"
            fake.write_text(
                f"#!/usr/bin/env python3\n"
                f"import json, pathlib, sys\n"
                f"video_count = pathlib.Path({str(video_count)!r})\n"
                f"subtitle_count = pathlib.Path({str(subtitle_count)!r})\n"
                "args = sys.argv[1:]\n"
                "if '--dump-single-json' in args:\n"
                "    print(json.dumps({'extractor_key': 'Fake', 'id': 'persistent', 'title': 'Demo', 'duration': 4, 'language': 'en', 'subtitles': {'en': [{'ext': 'vtt'}]}}))\n"
                "else:\n"
                "    template = args[args.index('--output') + 1]\n"
                "    if '001-video' in template:\n"
                "        output = pathlib.Path(template.replace('%(ext)s', 'mp4'))\n"
                "        output.parent.mkdir(parents=True, exist_ok=True)\n"
                "        output.write_bytes(b'fake-video')\n"
                "        count = int(video_count.read_text() if video_count.exists() else '0') + 1\n"
                "        video_count.write_text(str(count))\n"
                "    else:\n"
                "        output = pathlib.Path(template.replace('%(ext)s', 'vtt'))\n"
                "        output.parent.mkdir(parents=True, exist_ok=True)\n"
                "        output.write_text('WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\nhello from cache\\n')\n"
                "        count = int(subtitle_count.read_text() if subtitle_count.exists() else '0') + 1\n"
                "        subtitle_count.write_text(str(count))\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            ffmpeg = root / "fake-ffmpeg"
            ffmpeg.write_text(
                "#!/bin/sh\n"
                "last=\n"
                "for arg do last=$arg; done\n"
                "printf 'RIFF-fake-wav' > \"$last\"\n",
                encoding="utf-8",
            )
            ffmpeg.chmod(0o755)
            media_root = root / "local-videos"
            first = run_watch(WatchConfig(
                url="https://example.com/persistent",
                workspace=root,
                media_cache_root=media_root,
                cache="off",
                visual="never",
                yt_dlp=str(fake),
                ffmpeg=str(ffmpeg),
                task_name="first-task",
            ))
            second = run_watch(WatchConfig(
                url="https://example.com/persistent",
                workspace=root,
                media_cache_root=media_root,
                cache="off",
                visual="never",
                yt_dlp="/definitely/missing/yt-dlp",
                ffmpeg=str(ffmpeg),
                task_name="second-task",
            ))
            self.assertEqual(first["status"], "complete")
            self.assertEqual(first["extraction_status"], "complete")
            self.assertEqual(first["analysis"]["status"], "pending_agent_synthesis")
            self.assertEqual(first["content"]["transcript_policy"], "best-effort")
            self.assertEqual(first["content"]["visual_transcript_alignment"]["status"], "not_requested")
            self.assertEqual(second["status"], "complete")
            self.assertNotIn("persistent transcript cache did not pass read-back validation", " ".join(first["warnings"]))
            self.assertEqual(video_count.read_text(), "1")
            self.assertEqual(subtitle_count.read_text(), "1")
            self.assertIn("persistent local video cache", " ".join(second["warnings"]))
            self.assertTrue(second["artifacts"]["media_cache"].startswith("~/.local/videos/"))
            persistent_directory = media_root / media_cache_key("https://example.com/persistent")
            self.assertTrue((persistent_directory / "000-manifest.json").is_file())
            self.assertTrue((persistent_directory / "001-video.mp4").is_file())
            self.assertTrue((persistent_directory / AUDIO_NAME).is_file())
            self.assertTrue((persistent_directory / "002-transcript.json").is_file())
            self.assertTrue((persistent_directory / "004-transcript.vtt").is_file())
            self.assertTrue((persistent_directory / "005-transcript.md").is_file())

    def test_cli_parser_uses_interval_and_fps_sampling_controls(self):
        args = _parser().parse_args([
            "https://example.com/v",
            "--range", "1:00-2:00",
            "--frame-interval", "1.5",
            "--max-subtitle-attempts", "5",
            "--translation-command", "translator --input {input} --output {output}",
        ])
        self.assertEqual(args.range_spec, "1:00-2:00")
        self.assertEqual(args.frame_interval, 1.5)
        self.assertEqual(args.max_subtitle_attempts, 5)
        self.assertEqual(args.translation_command, "translator --input {input} --output {output}")
        self.assertFalse(hasattr(args, "max_frames"))
        fps_args = _parser().parse_args(["https://example.com/v", "--fps", "2"])
        self.assertEqual(fps_args.frame_interval, 0.5)

    def test_pipeline_reports_missing_required_extractor_without_fake_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            context = run_watch(WatchConfig(
                url="https://example.com/video",
                workspace=Path(temporary),
                media_cache_root=Path(temporary) / "media-cache",
                cache="off",
                yt_dlp="/definitely/missing/yt-dlp",
                run_id="missing-extractor",
            ))
            self.assertEqual(context["status"], "tool_unavailable")
            self.assertEqual(context["content"]["transcript_available"], False)
            state_path = Path(context["artifacts"]["state"])
            if not state_path.is_absolute():
                state_path = Path(temporary) / state_path
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "tool_unavailable")
            self.assertFalse("summary" in context)

    def test_pipeline_reuses_validated_transcript_cache_without_second_extractor_call(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            fake = workspace / "fake-yt-dlp.py"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "if '--dump-single-json' in args:\n"
                "    print(json.dumps({'extractor_key': 'Fake', 'id': 'abc', 'title': 'Demo', 'duration': 4, 'language': 'en', 'subtitles': {'en': [{'ext': 'vtt'}]}}))\n"
                "else:\n"
                "    template = args[args.index('--output') + 1]\n"
                "    if '001-video' in template:\n"
                "        output = pathlib.Path(template.replace('%(ext)s', 'mp4'))\n"
                "        output.write_bytes(b'fake-video')\n"
                "    else:\n"
                "        output = pathlib.Path(template.replace('%(ext)s', 'vtt'))\n"
                "        output.write_text('WEBVTT\\n\\n00:00:00.000 --> 00:00:02.000\\nThe architecture is explained here.\\n')\n"
                "    output.parent.mkdir(parents=True, exist_ok=True)\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            first = run_watch(WatchConfig(
                url="https://example.com/video",
                workspace=workspace,
                media_cache_root=workspace / "media-cache",
                cache="auto",
                visual="never",
                yt_dlp=str(fake),
                task_name="cache-task",
            ))
            self.assertEqual(first["status"], "complete")
            self.assertTrue(first["content"]["transcript_available"])
            self.assertEqual(first["artifacts"]["task_directory"], ".artifacts/watch-video/cache-task")
            self.assertTrue(first["artifacts"]["attempt_directory"].startswith(".artifacts/watch-video/cache-task/001-attempt-"))
            for key, prefix in (("state", "001-"), ("progress", "002-"), ("metadata", "003-"), ("transcript", "004-"), ("transcript_markdown", "004-"), ("timeline", "005-"), ("context", "007-")):
                artifact_path = Path(first["artifacts"][key])
                self.assertFalse(artifact_path.is_absolute())
                self.assertTrue(artifact_path.name.startswith(prefix), (key, artifact_path))
                self.assertNotIn("/private/", first["artifacts"][key])
                self.assertNotIn("/tmp/", first["artifacts"][key])
            second = run_watch(WatchConfig(
                url="https://example.com/video",
                workspace=workspace,
                media_cache_root=workspace / "media-cache",
                cache="auto",
                visual="never",
                yt_dlp="/definitely/missing/yt-dlp",
                task_name="cache-task",
            ))
            self.assertEqual(second["status"], "complete")
            self.assertTrue(second["cache"]["hit"])
            self.assertEqual(second["source"]["id"], "abc")
            self.assertTrue(second["artifacts"]["attempt_directory"].startswith(".artifacts/watch-video/cache-task/002-attempt-"))
            first_attempt = workspace / first["artifacts"]["attempt_directory"]
            second_attempt = workspace / second["artifacts"]["attempt_directory"]
            self.assertTrue(first_attempt.is_dir())
            self.assertTrue(second_attempt.is_dir())
            self.assertTrue((first_attempt / "007-context.json").is_file())
            self.assertTrue((first_attempt / "004-transcript.md").is_file())
            self.assertTrue((second_attempt / "007-context.json").is_file())
            cached_markdown = workspace / second["artifacts"]["transcript_markdown"]
            self.assertTrue(cached_markdown.is_file())
            self.assertEqual(
                cached_markdown.read_text(encoding="utf-8"),
                (first_attempt / "004-transcript.md").read_text(encoding="utf-8"),
            )
            task_files = list((workspace / ".artifacts" / "watch-video" / "cache-task").rglob("*"))
            self.assertTrue(task_files)
            for path in task_files:
                if path.is_file():
                    self.assertRegex(path.name, r"^\d{3}-", path)

    def test_persistent_wav_cache_is_created_reused_and_invalidated_on_refresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "fake-yt-dlp"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "if '--output' not in args:\n"
                "    raise SystemExit(0)\n"
                "template = args[args.index('--output') + 1]\n"
                "if '001-video' in template:\n"
                "    output = pathlib.Path(template.replace('%(ext)s', 'mp4'))\n"
                "    output.parent.mkdir(parents=True, exist_ok=True)\n"
                "    output.write_bytes(b'fake-video')\n"
                "else:\n"
                "    output = pathlib.Path(template.replace('%(ext)s', 'vtt'))\n"
                "    output.parent.mkdir(parents=True, exist_ok=True)\n"
                "    output.write_text('WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\nhello\\n')\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            ffmpeg = root / "fake-ffmpeg"
            ffmpeg.write_text(
                "#!/bin/sh\n"
                "last=\n"
                "for arg do last=$arg; done\n"
                "printf 'RIFF-fake-wav' > \"$last\"\n",
                encoding="utf-8",
            )
            ffmpeg.chmod(0o755)
            media_root = root / "local-videos"
            url = "https://example.com/watch?v=audio"
            cache, downloaded, _ = ensure_video(url, root=media_root, yt_dlp=str(fake))
            self.assertTrue(downloaded)
            self.assertIsNone(cache.audio_path)

            calls = []

            def fake_runner(argv, **kwargs):
                calls.append(argv)
                Path(argv[-1]).write_bytes(b"RIFF-fake-wav")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with_audio, created = ensure_audio(
                cache,
                ffmpeg=str(ffmpeg),
                runner=fake_runner,
            )
            self.assertTrue(created)
            self.assertEqual(with_audio.audio_path.name, AUDIO_NAME)
            self.assertEqual(with_audio.audio_path.read_bytes(), b"RIFF-fake-wav")
            self.assertEqual(with_audio.manifest["audio"], AUDIO_NAME)
            self.assertEqual(with_audio.manifest["audio_size"], len(b"RIFF-fake-wav"))
            self.assertEqual(len(calls), 1)

            reused, created_again = ensure_audio(
                with_audio,
                ffmpeg="/definitely/missing/ffmpeg",
                runner=lambda *args, **kwargs: self.fail("verified WAV should be reused"),
            )
            self.assertFalse(created_again)
            self.assertEqual(reused.audio_path, with_audio.audio_path)
            loaded = load_video(url, root=media_root)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.audio_path, with_audio.audio_path)

            refreshed, refresh_downloaded, _ = ensure_video(
                url,
                root=media_root,
                yt_dlp=str(fake),
                refresh=True,
            )
            self.assertTrue(refresh_downloaded)
            self.assertIsNone(refreshed.audio_path)
            self.assertFalse((refreshed.directory / AUDIO_NAME).exists())

    def test_video_only_cache_uses_provider_audio_fallback_for_persistent_wav(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "fake-yt-dlp"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "output = pathlib.Path(args[args.index('--output') + 1].replace('%(ext)s', 'mp4'))\n"
                "output.parent.mkdir(parents=True, exist_ok=True)\n"
                "output.write_bytes(b'fake-video')\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            ffmpeg = root / "fake-ffmpeg"
            ffmpeg.write_text("#!/bin/sh\n", encoding="utf-8")
            ffmpeg.chmod(0o755)
            media_root = root / "local-videos"
            url = "https://example.com/video-only"
            cache, _, _ = ensure_video(url, root=media_root, yt_dlp=str(fake))
            calls = []

            def fake_runner(argv, **kwargs):
                calls.append(argv)
                if Path(argv[0]).resolve() == ffmpeg.resolve():
                    return SimpleNamespace(
                        returncode=1,
                        stdout="",
                        stderr="Output file does not contain any stream",
                    )
                template = argv[argv.index("--output") + 1]
                output = Path(template.replace("%(ext)s", "wav"))
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"RIFF-provider-wav")
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            with_audio, created = ensure_audio(
                cache,
                url=url,
                ffmpeg=str(ffmpeg),
                yt_dlp=str(fake),
                runner=fake_runner,
            )
            self.assertTrue(created)
            self.assertEqual(with_audio.manifest["audio_source"], "provider")
            self.assertEqual(with_audio.audio_path.read_bytes(), b"RIFF-provider-wav")
            self.assertTrue(any("--format" in call and "bestaudio/best" in call for call in calls))

    def test_pipeline_reports_persistent_wav_artifact_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fake = root / "fake-yt-dlp"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, pathlib, sys\n"
                "args = sys.argv[1:]\n"
                "if '--dump-single-json' in args:\n"
                "    print(json.dumps({'extractor_key': 'Fake', 'id': 'audio', 'title': 'Demo', 'duration': 4, 'language': 'en', 'subtitles': {'en': [{'ext': 'vtt'}]}}))\n"
                "else:\n"
                "    template = args[args.index('--output') + 1]\n"
                "    if '001-video' in template:\n"
                "        output = pathlib.Path(template.replace('%(ext)s', 'mp4'))\n"
                "        output.write_bytes(b'fake-video')\n"
                "    else:\n"
                "        output = pathlib.Path(template.replace('%(ext)s', 'vtt'))\n"
                "        output.write_text('WEBVTT\\n\\n00:00:00.000 --> 00:00:01.000\\nhello\\n')\n"
                "    output.parent.mkdir(parents=True, exist_ok=True)\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            ffmpeg = root / "fake-ffmpeg"
            ffmpeg.write_text(
                "#!/bin/sh\n"
                "last=\n"
                "for arg do last=$arg; done\n"
                "printf 'RIFF-fake-wav' > \"$last\"\n",
                encoding="utf-8",
            )
            ffmpeg.chmod(0o755)
            media_root = root / "local-videos"
            context = run_watch(WatchConfig(
                url="https://example.com/audio",
                workspace=root,
                media_cache_root=media_root,
                cache="off",
                visual="never",
                yt_dlp=str(fake),
                ffmpeg=str(ffmpeg),
                task_name="audio-task",
            ))
            self.assertEqual(context["status"], "complete")
            self.assertTrue(context["content"]["audio_available"])
            self.assertTrue(context["artifacts"]["audio"].endswith("/006-audio.wav"))
            audio_path = media_root / media_cache_key("https://example.com/audio") / AUDIO_NAME
            self.assertTrue(audio_path.is_file())
            self.assertEqual(audio_path.read_bytes(), b"RIFF-fake-wav")


if __name__ == "__main__":
    unittest.main()
