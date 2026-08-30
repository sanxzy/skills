from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from PIL import Image

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = SKILL_ROOT / "scripts"
FIXTURE = SKILL_ROOT / "tests" / "fixtures" / "screen.png"
SYNTHETIC = SKILL_ROOT / "tests" / "fixtures" / "synthetic.png"
sys.path.insert(0, str(SCRIPT_ROOT))

from pixel_perfect_visionless.artifacts import RunArtifacts  # noqa: E402
from pixel_perfect_visionless.bootstrap import runtime_directory  # noqa: E402
from pixel_perfect_visionless.browser import find_system_browser  # noqa: E402
from pixel_perfect_visionless.cli import main  # noqa: E402
from pixel_perfect_visionless.compiler import Compiler, CompilerError  # noqa: E402
from pixel_perfect_visionless.extraction import PRIMITIVE_TYPES, extract_image  # noqa: E402
from pixel_perfect_visionless.images import compare_images, inspect_image  # noqa: E402
from pixel_perfect_visionless.ir import build_ir  # noqa: E402


class VisionlessTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        self.project = self.workspace / "project"
        self.project.mkdir()
        self.runtime_link = runtime_directory(self.workspace)
        self.runtime_link.parent.mkdir(parents=True, exist_ok=True)
        self.runtime_link.symlink_to(Path(sys.prefix), target_is_directory=True)
        self.tesseract = Path(shutil.which("tesseract") or "")
        if not self.tesseract.is_file():
            self.skipTest("Tesseract is required for visionless integration tests")

    def tearDown(self):
        self.temp.cleanup()

    def compiler(self) -> Compiler:
        return Compiler(
            workspace_root=self.workspace,
            project_root=self.project,
            install=False,
        )


class ExtractionTests(VisionlessTestCase):
    def test_real_fixture_preserves_source_facts_and_full_catalog(self):
        result = extract_image(FIXTURE, tesseract=self.tesseract)
        self.assertEqual(result.source["width"], 780)
        self.assertEqual(result.source["height"], 2798)
        self.assertTrue(result.source["preserved"])
        self.assertTrue(result.nodes)
        self.assertEqual(result.capabilities["ocr"]["language"], "eng")
        self.assertEqual(set(result.capabilities["primitive_catalog"]), set(PRIMITIVE_TYPES))
        self.assertTrue(any(item["status"] == "unknown" for item in result.capabilities["primitive_catalog"].values()))

    def test_synthetic_fixture_builds_layered_ir_with_relationships(self):
        extraction = extract_image(SYNTHETIC, tesseract=self.tesseract)
        ir = build_ir(extraction)
        self.assertEqual(ir["schema"], "visual-ui-ir")
        self.assertEqual(ir["version"], 1)
        self.assertEqual(ir["source"]["viewport"], "320x220")
        self.assertEqual(ir["scene_graph"]["root"], "viewport")
        self.assertTrue(ir["relationships"])
        self.assertTrue(all("confidence" in item for item in ir["relationships"]))
        text_nodes = [node for node in ir["nodes"] if node["primitiveType"] == "text"]
        self.assertTrue(any(node.get("observed", {}).get("text") == "Welcome back" for node in text_nodes))
        email = next(node for node in text_nodes if node.get("observed", {}).get("text") == "Email")
        self.assertLessEqual(abs(email["absoluteBounds"]["x"] - 48), 4)
        self.assertTrue(any(node["primitiveType"] in {"rectangle", "rounded_rectangle", "container"} for node in ir["nodes"]))
        self.assertTrue(any(node["inference"]["semantic"]["candidates"] for node in ir["nodes"]))

    def test_same_input_has_stable_ir_content(self):
        first = build_ir(extract_image(SYNTHETIC, tesseract=self.tesseract))
        second = build_ir(extract_image(SYNTHETIC, tesseract=self.tesseract))
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )


class CompilerAndPersistenceTests(VisionlessTestCase):
    def _write_render_target(self):
        (self.project / "index.html").write_text(
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><style>html,body{margin:0;width:320px;height:220px;background:#f8fafc}main{margin:20px 24px;padding:20px;background:white;border:1px solid #cbd5e1;border-radius:12px}h1{font:700 20px sans-serif;color:#0f172a;margin:0 0 12px}p{font:14px sans-serif;color:#475569;margin:0}</style></head><body><main><h1>Welcome back</h1><p>Rendered smoke</p></main></body></html>",
            encoding="utf-8",
        )

    def _require_browser(self):
        if find_system_browser() is None:
            self.skipTest("A system browser is required for browser integration coverage")

    def test_inspect_persists_report_and_project_facts(self):
        result = self.compiler().inspect(FIXTURE, points=[(0, 0)])
        run = Path(result["run_dir"])
        self.assertTrue((run / "inspection.json").is_file())
        self.assertTrue((run / "inspection.md").is_file())
        report = json.loads((run / "inspection.json").read_text(encoding="utf-8"))
        self.assertEqual(report["viewport"], "780x2798")
        self.assertEqual(report["samples"][0]["x"], 0)
        self.assertEqual(report["project"]["project_root"], str(self.project.resolve()))

    def test_render_persists_candidate_and_report(self):
        self._require_browser()
        self._write_render_target()
        result = self.compiler().render(entry="index.html", viewport="320x220")
        run = Path(result["run_dir"])
        self.assertTrue((run / "candidate.png").is_file())
        self.assertTrue((run / "render.json").is_file())
        saved = json.loads((run / "render.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["render"]["size"], {"width": 320, "height": 220})
        self.assertEqual(saved["artifacts"]["report"], str((run / "render.json").resolve()))

    def test_verify_render_path_persists_verdict_and_nested_comparison(self):
        self._require_browser()
        self._write_render_target()
        result = self.compiler().verify(SYNTHETIC, entry="index.html", viewport="320x220")
        run = Path(result["run_dir"])
        self.assertIn(result["status"], {"pass", "fail"})
        self.assertTrue((run / "candidate.png").is_file())
        self.assertTrue((run / "comparison.json").is_file())
        self.assertTrue((run / "verification.json").is_file())
        saved = json.loads((run / "verification.json").read_text(encoding="utf-8"))
        self.assertIsNotNone(saved["render"])
        self.assertEqual(saved["artifacts"]["verification"], str((run / "verification.json").resolve()))

    def test_compile_writes_all_primary_and_debug_artifacts(self):
        result = self.compiler().compile(SYNTHETIC, debug_artifacts=True)
        run = Path(result["run_dir"])
        for name in (
            "design.struct.json",
            "design.layout.txt",
            "design.ascii",
            "compile.json",
            "compile.md",
            "manifest.json",
            "result.json",
            "result.md",
            "debug/original.png",
            "debug/grayscale.png",
            "debug/edges.png",
            "debug/detected-geometry.png",
        ):
            self.assertTrue((run / name).is_file(), name)
        ir = json.loads((run / "design.struct.json").read_text(encoding="utf-8"))
        self.assertEqual(ir["schema"], "visual-ui-ir")
        self.assertIn("## Observed scene", (run / "design.layout.txt").read_text(encoding="utf-8"))
        self.assertIn("## Relationships", (run / "design.layout.txt").read_text(encoding="utf-8"))
        self.assertIn("## Inference", (run / "design.layout.txt").read_text(encoding="utf-8"))
        self.assertTrue((self.workspace / ".artifacts/pixel-perfect-visionless/latest.json").is_file())

    def test_compare_identical_images_persists_pixel_and_structured_outputs(self):
        result = self.compiler().compare(SYNTHETIC, SYNTHETIC)
        run = Path(result["run_dir"])
        comparison = json.loads((run / "comparison.json").read_text(encoding="utf-8"))
        self.assertEqual(comparison["pixel"]["metrics"]["mean_abs_error"], 0)
        self.assertEqual(comparison["structured"]["overall_similarity"], 1.0)
        self.assertTrue((run / "diff.json").is_file())
        self.assertTrue((run / "visual/overlay.png").is_file())
        self.assertTrue((run / "visual/diff-overlay.png").is_file())
        self.assertTrue((run / "visual/diff.png").is_file())
        self.assertTrue((run / "visual/threshold-mask.png").is_file())

    def test_structured_compare_exposes_expected_actual_delta(self):
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate.png"
            with Image.open(SYNTHETIC) as source:
                changed = source.convert("RGB")
            changed.putpixel((10, 10), (0, 0, 0))
            changed.save(candidate)
            result = self.compiler().compare(SYNTHETIC, candidate)
        structured = result["comparison"]["structured"]["structured"]
        self.assertTrue(structured["matches"])
        match = structured["matches"][0]
        self.assertIn("expected", match)
        self.assertIn("actual", match)
        self.assertIn("delta", match)
        self.assertIn("confidence", match)

    def test_default_runs_are_immutable_and_latest_points_to_newest(self):
        compiler = self.compiler()
        first = compiler.compile(SYNTHETIC)
        second = compiler.compile(SYNTHETIC)
        self.assertNotEqual(first["run_dir"], second["run_dir"])
        latest = json.loads((self.workspace / ".artifacts/pixel-perfect-visionless/latest.json").read_text(encoding="utf-8"))
        self.assertEqual(Path(latest["run_dir"]).resolve(), Path(second["run_dir"]).resolve())
        self.assertTrue(Path(first["result_json"]).is_file())

    def test_completed_run_cannot_be_overwritten_and_error_is_persisted_elsewhere(self):
        compiler = self.compiler()
        first = compiler.compile(SYNTHETIC)
        with self.assertRaises(CompilerError):
            compiler.compile(SYNTHETIC, run_dir=Path(first["run_dir"]))
        latest = json.loads((self.workspace / ".artifacts/pixel-perfect-visionless/latest.json").read_text(encoding="utf-8"))
        error = json.loads(Path(latest["result"]).read_text(encoding="utf-8"))
        self.assertEqual(error["status"], "error")
        self.assertIn("immutable", error["error"])

    def test_verify_persists_acceptance_checks_and_region_metrics(self):
        result = self.compiler().verify(
            SYNTHETIC,
            candidate=SYNTHETIC,
            regions=[("card", (24, 20, 272, 180))],
        )
        self.assertEqual(result["status"], "pass")
        self.assertTrue(any(check["name"].startswith("region_card") for check in result["checks"]))
        self.assertTrue(Path(result["run_dir"], "verification.json").is_file())

    def test_cli_stdout_is_only_persistent_pointer(self):
        original_cwd = Path.cwd()
        stdout = StringIO()
        try:
            os.chdir(self.workspace)
            with redirect_stdout(stdout):
                status = main(
                    [
                        "compile",
                        "--runtime-ready",
                        "--no-auto-setup",
                        "--project-root",
                        "project",
                        "--reference",
                        str(SYNTHETIC),
                    ]
                )
        finally:
            os.chdir(original_cwd)
        self.assertEqual(status, 0)
        pointer = json.loads(stdout.getvalue())
        self.assertEqual(pointer["status"], "ok")
        self.assertEqual(pointer["operation"], "compile")
        self.assertNotIn("nodes", pointer)
        self.assertTrue(Path(pointer["result_json"]).is_file())

    def test_missing_tesseract_persists_compiler_error(self):
        with patch("pixel_perfect_visionless.bootstrap.find_tesseract", return_value=None):
            with self.assertRaises(CompilerError):
                self.compiler().compile(SYNTHETIC)
        runs = sorted((self.workspace / ".artifacts/pixel-perfect-visionless/runs").iterdir())
        error = json.loads((runs[-1] / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(error["status"], "error")
        self.assertIn("Required Tesseract binary", error["error"])

    def test_missing_english_language_data_persists_compiler_error(self):
        with patch("pixel_perfect_visionless.bootstrap.find_tesseract", return_value=self.tesseract), patch(
            "pixel_perfect_visionless.bootstrap._tesseract_details", return_value=("tesseract-test", ("osd",))
        ):
            with self.assertRaises(CompilerError):
                self.compiler().compile(SYNTHETIC)
        runs = sorted((self.workspace / ".artifacts/pixel-perfect-visionless/runs").iterdir())
        error = json.loads((runs[-1] / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(error["status"], "error")
        self.assertIn("language data 'eng'", error["error"])

    def test_missing_runtime_persists_error_before_exit(self):
        other = self.workspace / "other"
        other.mkdir()
        original_cwd = Path.cwd()
        stdout = StringIO()
        try:
            os.chdir(other)
            with redirect_stdout(stdout):
                status = main(
                    [
                        "compile",
                        "--runtime-ready",
                        "--no-auto-setup",
                        "--project-root",
                        str(self.project),
                        "--reference",
                        str(SYNTHETIC),
                    ]
                )
        finally:
            os.chdir(original_cwd)
        self.assertEqual(status, 2)
        pointer = json.loads(stdout.getvalue())
        error = json.loads(Path(pointer["result_json"]).read_text(encoding="utf-8"))
        self.assertEqual(error["status"], "error")
        self.assertIn("Missing visionless environment", error["error"])


class ImageComparisonTests(VisionlessTestCase):
    def test_known_single_pixel_mutation_is_not_tautological(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            candidate = root / "candidate.png"
            with Image.open(SYNTHETIC) as source:
                source.convert("RGB").save(reference)
                changed = source.convert("RGB")
            changed.putpixel((10, 10), (0, 0, 0))
            changed.save(candidate)
            report, _, _ = compare_images(reference, candidate, tolerance=10, points=[(10, 10)])
            self.assertEqual(report["metrics"]["mismatch_pixels"], 1)
            self.assertEqual(report["samples"]["delta"][0]["delta"], [-244, -247, -252])
            self.assertEqual(report["metrics"]["mismatch_bbox"]["x"], 10)
            self.assertEqual(report["metrics"]["mismatch_bbox"]["y"], 10)

    def test_inspection_preserves_real_fixture_dimensions(self):
        report = inspect_image(FIXTURE)
        self.assertEqual(report["viewport"], "780x2798")
        self.assertEqual(report["mode"], "RGBA")
        self.assertTrue(report["dominant_colors"])
        self.assertTrue(report["edge_peaks"]["x"])
