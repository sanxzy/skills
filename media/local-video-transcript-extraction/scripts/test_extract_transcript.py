from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

from checkpoint import Checkpoint
from extract_transcript import TranscriptionConfig, run_transcription
from media_probe import MediaInfo
from model_runtime import RuntimeDependencies, load_local_model
from normalize import normalize_segment


class FakeWord:
    def __init__(self, start: float, end: float, text: str, probability: float = 0.9) -> None:
        self.start = start
        self.end = end
        self.word = text
        self.probability = probability


class FakeSegment:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start = start
        self.end = end
        self.text = text
        self.words = (FakeWord(start, end, text),)
        self.avg_logprob = -0.1
        self.no_speech_prob = 0.01
        self.compression_ratio = 1.1


class FakeModel:
    def __init__(self, iterator_factory, *, language: str = "id") -> None:
        self.iterator_factory = iterator_factory
        self.language = language
        self.calls: list[dict[str, object]] = []

    def transcribe(self, path: str, **kwargs: object):
        self.calls.append({"path": path, **kwargs})
        return self.iterator_factory(), SimpleNamespace(language=self.language, language_probability=0.98)


def runtime() -> RuntimeDependencies:
    return RuntimeDependencies(
        whisper_model_class=object,
        engine_version="test-runtime",
        faster_whisper_module=SimpleNamespace(),
    )


class LocalTranscriptTests(unittest.TestCase):
    def _fixture(self):
        root = Path(tempfile.mkdtemp(prefix="local-transcript-test-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        media = root / "sample.mp4"
        media.write_bytes(b"fixture media")
        model_dir = root / "model"
        model_dir.mkdir()
        (model_dir / "model.bin").write_bytes(b"model")
        (model_dir / "config.json").write_text("{}", encoding="utf-8")
        (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
        info = MediaInfo(media.resolve(), "video", media.stat().st_size, 4.0)
        return root, media, model_dir, info

    def _artifact_paths(self, root: Path):
        task_directory = root / ".artifacts" / "transcript" / "test-task"
        return task_directory / "result.json", task_directory / "work"

    def _result_path(self, root: Path, value: str):
        path = Path(value)
        return path if path.is_absolute() else root / path

    def _config(self, media: Path, model_dir: Path, output: Path, work: Path, **kwargs):
        kwargs.setdefault("formats", ("json", "txt", "srt", "vtt"))
        return TranscriptionConfig(
            media_path=media,
            output=output,
            workspace=media.parent,
            task_name="test-task",
            work_dir=work,
            model_path=model_dir,
            enforce_python_environment=False,
            **kwargs,
        )

    def test_default_artifacts_use_workspace_task_namespace(self):
        root, media, model_dir, media_info = self._fixture()
        result = run_transcription(
            TranscriptionConfig(
                media_path=media,
                workspace=root,
                task_name="meeting",
                model_path=model_dir,
                enforce_python_environment=False,
            ),
            runtime=runtime(),
            model=FakeModel(lambda: iter([FakeSegment(0.0, 4.0, "Satu dua")])),
            media=media_info,
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["artifacts"]["task_directory"], "./.artifacts/transcript/meeting")
        self.assertEqual(result["outputs"]["json"], "./.artifacts/transcript/meeting/sample.transcript.json")
        self.assertTrue((root / ".artifacts" / "transcript" / "meeting" / "sample.transcript.json").is_file())

    def test_model_loader_uses_fixed_local_constructor_and_offline_flag(self):
        root, _, model_dir, _ = self._fixture()
        calls = []

        def constructor(path, **kwargs):
            calls.append((path, kwargs))
            return object()

        load_local_model(model_dir, runtime=runtime(), loader=constructor)
        self.assertEqual(calls[0][0], str(model_dir.resolve()))
        self.assertEqual(calls[0][1], {"device": "cpu", "compute_type": "int8", "local_files_only": True})

    def test_normalizes_words_and_diagnostics(self):
        segment = normalize_segment(FakeSegment(0.2, 1.4, "  Halo   dunia. "), 0, duration=2.0)
        self.assertIsNotNone(segment)
        assert segment is not None
        value = segment.as_dict()
        self.assertEqual(value["text"], "Halo dunia.")
        self.assertEqual(value["words"][0]["text"], "Halo dunia.")
        self.assertEqual(value["no_speech_prob"], 0.01)

    def test_incremental_failure_leaves_readable_partial_checkpoint(self):
        root, media, model_dir, media_info = self._fixture()
        output, work = self._artifact_paths(root)

        def interrupted():
            yield FakeSegment(0.0, 2.0, "Satu")
            raise RuntimeError("decoder stopped")

        model = FakeModel(interrupted)
        result = run_transcription(
            self._config(media, model_dir, output, work),
            runtime=runtime(),
            model=model,
            media=media_info,
        )
        self.assertEqual(result["status"], "partial")
        self.assertFalse(output.exists())
        checkpoint = Checkpoint.load(work / "checkpoint.jsonl")
        self.assertEqual(len(checkpoint.segments), 1)
        self.assertEqual(checkpoint.segments[0].text, "Satu")
        self.assertTrue(self._result_path(root, result["partial"]).is_file())

    def test_resume_recovers_before_an_incomplete_trailing_checkpoint_record(self):
        root, media, model_dir, media_info = self._fixture()
        output, work = self._artifact_paths(root)

        def interrupted():
            yield FakeSegment(0.0, 2.0, "Satu")
            raise RuntimeError("decoder stopped")

        first = run_transcription(
            self._config(media, model_dir, output, work),
            runtime=runtime(),
            model=FakeModel(interrupted),
            media=media_info,
        )
        self.assertEqual(first["status"], "partial")
        with (work / "checkpoint.jsonl").open("a", encoding="utf-8") as stream:
            stream.write("{\"record_type\":\"segment\"")

        second = run_transcription(
            self._config(media, model_dir, output, work, resume=True),
            runtime=runtime(),
            model=FakeModel(lambda: iter([FakeSegment(0.0, 2.0, "Satu"), FakeSegment(2.0, 4.0, "Dua")])),
            media=media_info,
        )
        self.assertEqual(second["status"], "completed")
        self.assertTrue(any("incomplete trailing" in warning for warning in second.get("warnings", [])))

    def test_resume_reprocesses_bounded_overlap_without_duplicate_segments(self):
        root, media, model_dir, media_info = self._fixture()
        output, work = self._artifact_paths(root)

        def interrupted():
            yield FakeSegment(0.0, 2.0, "Satu")
            raise RuntimeError("decoder stopped")

        first = run_transcription(
            self._config(media, model_dir, output, work),
            runtime=runtime(),
            model=FakeModel(interrupted),
            media=media_info,
        )
        self.assertEqual(first["status"], "partial")

        def resumed():
            yield FakeSegment(0.0, 2.0, "Satu")
            yield FakeSegment(2.0, 4.0, "Dua")

        second_model = FakeModel(resumed)
        second = run_transcription(
            self._config(media, model_dir, output, work, resume=True),
            runtime=runtime(),
            model=second_model,
            media=media_info,
        )
        self.assertEqual(second["status"], "completed")
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in payload["segments"]], [0, 1])
        self.assertEqual([item["text"] for item in payload["segments"]], ["Satu", "Dua"])
        self.assertEqual(second_model.calls[0]["clip_timestamps"], "0.000,0")
        self.assertTrue(output.with_suffix(".txt").is_file())
        self.assertIn("00:00:00,000 --> 00:00:02,000", output.with_suffix(".srt").read_text(encoding="utf-8"))
        self.assertIn("WEBVTT", output.with_suffix(".vtt").read_text(encoding="utf-8"))

    def test_resume_recreates_missing_requested_projection_from_a_terminal_checkpoint(self):
        root, media, model_dir, media_info = self._fixture()
        output, work = self._artifact_paths(root)
        first = run_transcription(
            self._config(media, model_dir, output, work, formats=("json",)),
            runtime=runtime(),
            model=FakeModel(lambda: iter([FakeSegment(0.0, 4.0, "Satu dua")])),
            media=media_info,
        )
        self.assertEqual(first["status"], "completed")
        self.assertFalse(output.with_suffix(".txt").exists())
        second = run_transcription(
            self._config(media, model_dir, output, work, resume=True),
            runtime=runtime(),
            model=FakeModel(lambda: iter([FakeSegment(0.0, 4.0, "Satu dua")])),
            media=media_info,
        )
        self.assertEqual(second["status"], "completed")
        self.assertTrue(output.with_suffix(".txt").is_file())

    def test_cancellation_flushes_current_segment_and_does_not_publish_completed_outputs(self):
        root, media, model_dir, media_info = self._fixture()
        output, work = self._artifact_paths(root)
        cancel = threading.Event()

        def cancellable():
            yield FakeSegment(0.0, 2.0, "Satu")
            cancel.set()
            yield FakeSegment(2.0, 4.0, "Dua")

        result = run_transcription(
            self._config(media, model_dir, output, work),
            runtime=runtime(),
            model=FakeModel(cancellable),
            media=media_info,
            cancel_event=cancel,
        )
        self.assertEqual(result["status"], "cancelled")
        self.assertFalse(output.exists())
        checkpoint = Checkpoint.load(work / "checkpoint.jsonl")
        self.assertEqual(checkpoint.status, "cancelled")
        # The segment already requested when cancellation became visible may
        # finish; every acknowledged segment must remain durable.
        self.assertEqual(len(checkpoint.segments), 2)

    def test_fresh_attempt_preserves_previous_partial_artifact(self):
        root, media, model_dir, media_info = self._fixture()
        output, work = self._artifact_paths(root)

        def interrupted():
            yield FakeSegment(0.0, 2.0, "Satu")
            raise RuntimeError("decoder stopped")

        first = run_transcription(
            self._config(media, model_dir, output, work),
            runtime=runtime(),
            model=FakeModel(interrupted),
            media=media_info,
        )
        self.assertEqual(first["status"], "partial")
        previous_partial = self._result_path(root, first["partial"])
        self.assertTrue(previous_partial.is_file())

        second = run_transcription(
            self._config(media, model_dir, output, work, formats=("json",)),
            runtime=runtime(),
            model=FakeModel(lambda: iter([FakeSegment(0.0, 4.0, "Satu dua")])),
            media=media_info,
        )
        self.assertEqual(second["status"], "completed")
        self.assertFalse(previous_partial.exists())
        self.assertTrue(list(output.parent.glob("result.partial.previous-*.json")))
        self.assertTrue(list((work).glob("checkpoint.previous-*.jsonl")))

    def test_remote_input_is_rejected_before_runtime_work(self):
        result = run_transcription(
            TranscriptionConfig(
                media_path=Path("https://example.test/video.mp4"),
                output=None,
                enforce_python_environment=False,
            ),
            runtime=runtime(),
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "remote_input_unsupported")

    def test_missing_model_fails_before_media_inspection(self):
        root, media, _, media_info = self._fixture()
        missing_model = root / "missing-model"
        output, work = self._artifact_paths(root)
        result = run_transcription(
            TranscriptionConfig(
                media_path=media,
                output=output,
                workspace=root,
                task_name="test-task",
                work_dir=work,
                model_path=missing_model,
                enforce_python_environment=False,
            ),
            runtime=runtime(),
            model=FakeModel(lambda: iter(())),
            media=None,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "model_missing")

    def test_silent_media_completes_with_explicit_no_speech_diagnostic(self):
        root, media, model_dir, media_info = self._fixture()
        output, work = self._artifact_paths(root)
        result = run_transcription(
            self._config(media, model_dir, output, work, formats=("json",)),
            runtime=runtime(),
            model=FakeModel(lambda: iter(())),
            media=media_info,
        )
        self.assertEqual(result["status"], "completed")
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["segments"], [])
        self.assertEqual(payload["settings"]["task"], "transcribe")
        self.assertTrue(payload["diagnostics"]["no_speech_detected"])
        self.assertEqual(payload["progress"]["percentage"], 100.0)

    def test_checkpoint_records_each_segment_before_progress(self):
        root, media, model_dir, media_info = self._fixture()
        output, work = self._artifact_paths(root)
        result = run_transcription(
            self._config(media, model_dir, output, work, formats=("json",)),
            runtime=runtime(),
            model=FakeModel(lambda: iter([FakeSegment(0.0, 1.0, "Satu")])),
            media=media_info,
        )
        self.assertEqual(result["status"], "completed")
        records = [json.loads(line) for line in (work / "checkpoint.jsonl").read_text(encoding="utf-8").splitlines()]
        segment_index = next(index for index, record in enumerate(records) if record.get("record_type") == "segment")
        progress_index = next(index for index, record in enumerate(records) if record.get("record_type") == "progress")
        self.assertLess(segment_index, progress_index)
        compact = Checkpoint.load(work / "checkpoint.jsonl", retain_segments=False)
        self.assertEqual(compact.segments, [])
        self.assertEqual(len(compact.read_segments()), 1)


if __name__ == "__main__":
    unittest.main()
