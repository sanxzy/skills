from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import venv
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from PIL import Image

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = SKILL_ROOT / "scripts"
FIXTURE = SKILL_ROOT / "tests" / "fixtures" / "screen.png"
sys.path.insert(0, str(SCRIPT_ROOT))

from pixel_perfect.bootstrap import runtime_directory  # noqa: E402
from pixel_perfect.cli import main as cli_main  # noqa: E402
from pixel_perfect.decomposition import build_decomposition  # noqa: E402
from pixel_perfect.images import (  # noqa: E402
    ImageAnalysisError,
    compare_images,
    inspect_image,
    parse_point,
    parse_region,
    parse_viewport,
    save_visual_artifacts,
)
from pixel_perfect.project import inspect_project  # noqa: E402
from pixel_perfect.rendering import resolve_target_url, smoke_check  # noqa: E402


class ImageAnalysisTests(unittest.TestCase):
    def test_parse_viewport_and_region(self):
        self.assertEqual(parse_viewport("1536x1024"), (1536, 1024))
        self.assertEqual(parse_point("7,3"), (7, 3))
        self.assertEqual(parse_region("sidebar=0,44,252,934"), ("sidebar", (0, 44, 252, 934)))
        with self.assertRaises(ImageAnalysisError):
            parse_viewport("1536")

    def test_inspect_reports_dimensions_and_colors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.png"
            image = Image.new("RGB", (8, 6), "#101820")
            image.putpixel((0, 0), (255, 0, 0))
            image.save(path)
            result = inspect_image(path)
            self.assertEqual(result["viewport"], "8x6")
            self.assertEqual(result["mode"], "RGB")
            self.assertTrue(result["dominant_colors"])
            self.assertEqual(result["corners"]["top_left"], [255, 0, 0])

    def test_compare_identical_images_pass_structural_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            candidate = root / "candidate.png"
            Image.new("RGB", (12, 10), "#101820").save(reference)
            Image.new("RGB", (12, 10), "#101820").save(candidate)
            report, reference_image, candidate_image = compare_images(
                reference,
                candidate,
                regions=[("center", (2, 2, 6, 5))],
                points=[(2, 2)],
            )
            self.assertEqual(report["metrics"]["mean_abs_error"], 0)
            self.assertEqual(report["samples"]["delta"][0]["delta"], [0, 0, 0])
            self.assertEqual(report["metrics"]["exact_fraction"], 1)
            self.assertEqual(report["regions"][0]["name"], "center")
            artifacts = save_visual_artifacts(
                reference_image, candidate_image, root / "artifacts"
            )
            self.assertTrue(Path(artifacts["diff"]).is_file())
            self.assertTrue(Path(artifacts["threshold_mask"]).is_file())

    def test_compare_reports_localized_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            candidate = root / "candidate.png"
            Image.new("RGB", (10, 10), "#101820").save(reference)
            changed = Image.new("RGB", (10, 10), "#101820")
            changed.putpixel((7, 3), (255, 255, 255))
            changed.save(candidate)
            report, _, _ = compare_images(
                reference, candidate, tolerance=10, points=[(7, 3)]
            )
            metrics = report["metrics"]
            self.assertGreater(metrics["mismatch_pixels"], 0)
            self.assertEqual(report["samples"]["delta"][0]["delta"], [239, 231, 223])
            self.assertEqual(metrics["mismatch_bbox"]["x"], 7)
            self.assertEqual(metrics["mismatch_bbox"]["y"], 3)
            self.assertGreater(metrics["mismatch_fraction"], 0)

    def test_compare_rejects_different_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            candidate = root / "candidate.png"
            Image.new("RGB", (4, 4), "black").save(reference)
            Image.new("RGB", (5, 4), "black").save(candidate)
            with self.assertRaises(ImageAnalysisError):
                compare_images(reference, candidate)

    def test_tolerance_controls_mismatch_and_hotspot_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference.png"
            candidate = root / "candidate.png"
            Image.new("RGB", (4, 4), (0, 0, 0)).save(reference)
            Image.new("RGB", (4, 4), (5, 5, 5)).save(candidate)
            tolerant, _, _ = compare_images(reference, candidate, tolerance=10)
            strict, _, _ = compare_images(reference, candidate, tolerance=1)
            self.assertEqual(tolerant["metrics"]["mismatch_pixels"], 0)
            self.assertEqual(tolerant["metrics"]["tile_hotspots"][0]["mismatch_fraction"], 0)
            self.assertEqual(strict["metrics"]["mismatch_pixels"], 16)
            self.assertEqual(strict["metrics"]["tile_hotspots"][0]["mismatch_fraction"], 1)


class WorkspaceStorageTests(unittest.TestCase):
    def test_inspect_cli_returns_only_a_report_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            project = workspace / "project"
            project.mkdir()
            reference = workspace / "reference.png"
            Image.new("RGB", (8, 6), "#101820").save(reference)
            runtime_path = runtime_directory(workspace)
            venv.EnvBuilder(with_pip=False).create(runtime_path)
            original_cwd = Path.cwd()
            try:
                os.chdir(workspace)
                stdout = StringIO()
                with redirect_stdout(stdout):
                    status = cli_main(
                        [
                            "inspect",
                            "--runtime-ready",
                            "--no-auto-setup",
                            "--project-root",
                            "project",
                            "--reference",
                            "reference.png",
                        ]
                    )
            finally:
                os.chdir(original_cwd)
            self.assertEqual(status, 0)
            pointer = json.loads(stdout.getvalue())
            self.assertEqual(pointer["status"], "ok")
            self.assertEqual(pointer["operation"], "inspect")
            self.assertNotIn("dominant_colors", pointer)
            report = json.loads(Path(pointer["reports"]["json"]).read_text(encoding="utf-8"))
            self.assertEqual(report["reference"]["viewport"], "8x6")
            self.assertEqual(report["report"], pointer["reports"]["json"])

    def test_compare_cli_returns_only_artifact_pointers(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            project = workspace / "project"
            project.mkdir()
            reference = workspace / "reference.png"
            candidate = workspace / "candidate.png"
            Image.new("RGB", (8, 6), "#101820").save(reference)
            Image.new("RGB", (8, 6), "#101820").save(candidate)
            runtime_path = runtime_directory(workspace)
            venv.EnvBuilder(with_pip=False).create(runtime_path)
            original_cwd = Path.cwd()
            try:
                os.chdir(workspace)
                stdout = StringIO()
                with redirect_stdout(stdout):
                    status = cli_main(
                        [
                            "compare",
                            "--runtime-ready",
                            "--no-auto-setup",
                            "--project-root",
                            "project",
                            "--reference",
                            "reference.png",
                            "--candidate",
                            "candidate.png",
                        ]
                    )
            finally:
                os.chdir(original_cwd)
            self.assertEqual(status, 0)
            pointer = json.loads(stdout.getvalue())
            self.assertEqual(pointer["status"], "ok")
            self.assertEqual(pointer["operation"], "compare")
            self.assertNotIn("metrics", pointer)
            comparison = json.loads(Path(pointer["reports"]["json"]).read_text(encoding="utf-8"))
            self.assertEqual(comparison["metrics"]["mean_abs_error"], 0)
            self.assertTrue(Path(pointer["artifacts"]["diff"]).is_file())

    def test_cli_error_returns_a_persisted_error_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            project = workspace / "project"
            project.mkdir()
            runtime_path = runtime_directory(workspace)
            venv.EnvBuilder(with_pip=False).create(runtime_path)
            original_cwd = Path.cwd()
            try:
                os.chdir(workspace)
                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    status = cli_main(
                        [
                            "inspect",
                            "--runtime-ready",
                            "--no-auto-setup",
                            "--project-root",
                            "project",
                            "--reference",
                            "missing.png",
                        ]
                    )
            finally:
                os.chdir(original_cwd)
            self.assertEqual(status, 2)
            self.assertEqual(stdout.getvalue(), "")
            pointer = json.loads(stderr.getvalue())
            self.assertEqual(pointer["status"], "error")
            self.assertEqual(pointer["operation"], "inspect")
            error = json.loads(Path(pointer["error_report"]).read_text(encoding="utf-8"))
            self.assertEqual(error["status"], "error")
            self.assertIn("Image file not found", error["error"])

    def test_cli_keeps_runtime_and_artifacts_in_invocation_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            project = workspace / "project"
            project.mkdir()
            reference = workspace / "reference.png"
            Image.new("RGB", (8, 6), "#101820").save(reference)
            runtime_path = runtime_directory(workspace)
            venv.EnvBuilder(with_pip=False).create(runtime_path)
            original_cwd = Path.cwd()
            try:
                os.chdir(workspace)
                stdout = StringIO()
                with redirect_stdout(stdout):
                    status = cli_main(
                        [
                            "decompose",
                            "--runtime-ready",
                            "--no-auto-setup",
                            "--project-root",
                            str(project),
                            "--reference",
                            "reference.png",
                        ]
                    )
            finally:
                os.chdir(original_cwd)
            self.assertEqual(status, 0)
            pointer = json.loads(stdout.getvalue())
            self.assertEqual(pointer["status"], "draft")
            self.assertEqual(pointer["operation"], "decompose")
            self.assertEqual(pointer["output_dir"], str((workspace / ".artifacts/pixel-perfect").resolve()))
            self.assertNotIn("plan", pointer)
            report = json.loads(Path(pointer["reports"]["json"]).read_text(encoding="utf-8"))
            self.assertEqual(report["runtime"]["directory"], str(runtime_path.resolve()))
            self.assertTrue((workspace / ".artifacts/pixel-perfect/decomposition.json").is_file())
            self.assertTrue((workspace / ".artifacts/pixel-perfect/decomposition.md").is_file())
            self.assertFalse((project / ".artifacts").exists())
            self.assertFalse((project / ".xzy-env").exists())


class FixtureImageTests(unittest.TestCase):
    def test_real_fixture_inspection_preserves_reference_dimensions(self):
        result = inspect_image(FIXTURE, points=[(390, 1400)])
        self.assertEqual(result["width"], 780)
        self.assertEqual(result["height"], 2798)
        self.assertEqual(result["mode"], "RGB")
        self.assertEqual(result["corners"]["top_left"], [248, 249, 255])
        self.assertEqual(result["samples"][0]["rgb"], [239, 244, 255])
        self.assertTrue(result["scanlines"]["horizontal"])

    def test_real_fixture_known_mutation_is_localized(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with Image.open(FIXTURE) as source:
                reference = source.convert("RGB").crop((350, 1350, 430, 1430))
            candidate = reference.copy()
            candidate.putpixel((40, 50), (0, 0, 0))
            reference_path = root / "fixture-region.png"
            candidate_path = root / "mutated-region.png"
            reference.save(reference_path)
            candidate.save(candidate_path)
            report, _, _ = compare_images(
                reference_path,
                candidate_path,
                points=[(40, 50)],
                tolerance=10,
            )
            self.assertEqual(report["metrics"]["mismatch_bbox"]["x"], 40)
            self.assertEqual(report["metrics"]["mismatch_bbox"]["y"], 50)
            self.assertEqual(report["metrics"]["mismatch_pixels"], 1)
            self.assertEqual(report["samples"]["delta"][0]["delta"], [-239, -244, -255])


class SectionDecompositionTests(unittest.TestCase):
    def setUp(self):
        self.reference = {
            "path": "/tmp/reference.png",
            "viewport": "120x80",
            "width": 120,
            "height": 80,
            "edge_peaks": {
                "x": [{"position": 40, "score": 12.5}],
                "y": [{"position": 24, "score": 10.0}],
            },
        }
        self.project = {
            "project_root": "/tmp/project",
            "frameworks": ["static HTML"],
            "candidate_entrypoints": ["index.html"],
        }

    def test_empty_plan_is_a_draft_with_ordered_evidence(self):
        plan = build_decomposition(self.reference, self.project)
        self.assertEqual(plan["status"], "draft")
        self.assertEqual(plan["sections"], [])
        self.assertEqual(plan["implementation_order"][0]["id"], "global-frame")
        self.assertEqual(plan["suggested_boundaries"]["vertical"][0]["position"], 40)

    def test_complete_section_contract_becomes_ready(self):
        plan = build_decomposition(
            self.reference,
            self.project,
            sections=[
                {
                    "id": "main",
                    "bounds": [0, 0, 120, 80],
                    "visual_contract": ["Dark surface with one centered card"],
                    "content_state": "default",
                    "layout_owner": "index.html",
                    "dependencies": [],
                    "implementation_order": 1,
                    "verification_region": [0, 0, 120, 80],
                    "responsive_behavior": "Stack card below 640px.",
                    "acceptance_criteria": ["Card remains inside the viewport."],
                }
            ],
        )
        section = plan["sections"][0]
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(section["status"], "ready")
        self.assertEqual(section["missing_fields"], [])
        self.assertEqual(section["verification_region"]["width"], 120)

    def test_section_outside_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            build_decomposition(
                self.reference,
                self.project,
                sections=[{"id": "bad", "bounds": [100, 70, 30, 20]}],
            )


class ProjectAndRenderTests(unittest.TestCase):
    def test_project_inspection_detects_framework_and_scripts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "demo",
                        "scripts": {"dev": "vite"},
                        "dependencies": {"react": "^19.0.0", "vite": "^7.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "index.html").write_text("<main>demo</main>", encoding="utf-8")
            result = inspect_project(root)
            self.assertIn("React", result["frameworks"])
            self.assertIn("Vite", result["frameworks"])
            self.assertEqual(result["package"]["scripts"]["dev"], "vite")
            self.assertIn("index.html", result["candidate_entrypoints"])

    def test_local_entry_resolves_to_file_url_and_smoke_detects_flat_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "index.html"
            entry.write_text("<h1>demo</h1>", encoding="utf-8")
            self.assertTrue(resolve_target_url(root).startswith("file://"))
            flat = root / "flat.png"
            Image.new("RGB", (4, 4), "black").save(flat)
            self.assertEqual(smoke_check(flat)["status"], "fail")

    def test_local_url_resolves_relative_to_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            project = workspace / "project"
            project.mkdir()
            target = workspace / "target.html"
            target.write_text("<main>workspace target</main>", encoding="utf-8")
            self.assertEqual(
                resolve_target_url(project, workspace_root=workspace, url="target.html"),
                target.resolve().as_uri(),
            )


if __name__ == "__main__":
    unittest.main()
