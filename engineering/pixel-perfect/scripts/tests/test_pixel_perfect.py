"""Hermetic and fixture-backed tests for the pixel-perfect script layer."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _common import PixelPerfectError, read_json  # noqa: E402
from analyze_grid import analyze_grid  # noqa: E402
from compare_images import compare_images  # noqa: E402
from generate_diff import generate_diff  # noqa: E402
from iteration import recommend_iteration  # noqa: E402
from normalize_images import normalize_pair  # noqa: E402
from preflight import preflight  # noqa: E402
from quick import quick_run  # noqa: E402
from render_browser import render_browser  # noqa: E402
from runtime import ensure_runtime  # noqa: E402
from verify_acceptance import verify_acceptance  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures"
LAND = FIXTURES / "land.png"
DASHBOARD = FIXTURES / "dashboard.png"


class PixelPerfectScriptsTest(unittest.TestCase):
    def test_fixture_pair_normalizes_without_resizing(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = normalize_pair(LAND, DASHBOARD, Path(temporary) / "normalized")
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["conditions"]["dimensions"], [1536, 1024])
            self.assertEqual(result["conditions"]["dimension_policy"], "strict; no implicit resize")
            self.assertTrue(Path(result["artifacts"]["reference"]).is_file())
            self.assertTrue(Path(result["artifacts"]["render"]).is_file())
            manifest = read_json(result["artifacts"]["manifest"])
            self.assertEqual(manifest["operation"], "normalize")

    def test_missing_and_mismatched_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(PixelPerfectError):
                compare_images(LAND, root / "missing.png")
            from PIL import Image

            small = root / "small.png"
            Image.new("RGB", (8, 8), (0, 0, 0)).save(small)
            with self.assertRaises(PixelPerfectError):
                compare_images(LAND, small)

    def test_fixture_pair_produces_nonzero_metrics_and_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            compared = compare_images(
                LAND,
                DASHBOARD,
                mode="color-aware",
                structure_background="#ffffff",
                output=root / "compare.json",
            )
            metrics = compared["metrics"]
            self.assertEqual(compared["status"], "complete")
            self.assertGreater(metrics["changed_pixels"], 0)
            self.assertLess(metrics["similarity_score"], 1.0)
            self.assertIsNotNone(metrics["bbox"])
            self.assertIn("structure", compared)
            self.assertIsNotNone(compared["structure"]["bbox_displacement"])
            self.assertTrue(Path(compared["artifacts"]["report"]).is_file())

            diff = generate_diff(LAND, DASHBOARD, root / "diff")
            self.assertTrue(Path(diff["artifacts"]["diff"]).is_file())
            self.assertTrue(Path(diff["artifacts"]["heatmap"]).is_file())
            self.assertGreater(diff["metrics"]["changed_pixels"], 0)

    def test_alpha_inputs_are_composited_to_rgb_with_recorded_backdrop(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            from PIL import Image

            reference = root / "alpha-reference.png"
            render = root / "alpha-render.png"
            Image.new("RGBA", (8, 8), (255, 0, 0, 128)).save(reference)
            Image.new("RGBA", (8, 8), (255, 0, 0, 128)).save(render)
            result = normalize_pair(reference, render, root / "normalized", background="#000000")
            self.assertTrue(result["reference"]["alpha_composited"])
            self.assertEqual(result["conditions"]["background"], "#000000")
            with Image.open(result["artifacts"]["reference"]) as image:
                self.assertEqual(image.mode, "RGB")

    def test_identical_fixture_copy_is_exactly_equal(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "land-copy.png"
            shutil.copy2(LAND, copied)
            result = compare_images(LAND, copied, mode="exact", tolerance=0)
            self.assertEqual(result["metrics"]["changed_pixels"], 0)
            self.assertEqual(result["metrics"]["difference_percentage"], 0.0)
            self.assertEqual(result["metrics"]["similarity_score"], 1.0)
            self.assertIsNone(result["metrics"]["bbox"])

    def test_quick_mode_builds_a_small_complete_evidence_chain(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = quick_run(
                LAND,
                DASHBOARD,
                task_name="quick-run",
                cwd=root,
            )
            self.assertEqual(result["status"], "complete")
            self.assertEqual([step["operation"] for step in result["steps"]], ["normalize", "compare", "diff"])
            self.assertTrue(Path(result["artifacts"]["report"]).is_file())
            task_root = root / ".artifacts" / "pixel-perfect" / "quick-run"
            self.assertTrue((task_root / "001-normalize" / "001-reference.png").is_file())
            self.assertTrue((task_root / "002-compare" / "001-compare.json").is_file())
            self.assertTrue((task_root / "003-diff" / "002-heatmap.png").is_file())

    def test_browser_adapter_fails_explicitly_when_requested_executable_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = root / "index.html"
            page.write_text("<html><body>fixture</body></html>", encoding="utf-8")
            with self.assertRaises(PixelPerfectError):
                render_browser(
                    page,
                    task_name="browser-failure",
                    backend="chrome",
                    browser_path=root / "missing-browser",
                    cwd=root,
                )

    def test_preflight_reports_input_conditions_and_local_capabilities(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = preflight(
                [LAND],
                task_name="preflight-run",
                viewport="1536x1024",
                dpr=1.0,
                cwd=Path(temporary),
            )
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["references"][0]["dimensions"], [1536, 1024])
            self.assertFalse(result["references"][0]["has_alpha"])
            self.assertEqual(result["requested_conditions"]["viewport"], [1536, 1024])
            self.assertTrue(Path(result["artifacts"]["report"]).is_file())

    def test_acceptance_gate_can_reach_matched_only_with_explicit_declarations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copied = root / "land-copy.png"
            shutil.copy2(LAND, copied)
            compare_path = root / "001-compare.json"
            grid_path = root / "002-grid.json"
            compare_images(LAND, copied, mode="exact", output=compare_path)
            analyze_grid(LAND, copied, max_depth=0, output=grid_path)
            sections = root / "sections.json"
            sections.write_text(json.dumps({"sections": [{
                "id": "screen",
                "bbox": [0, 0, 1536, 1024],
                "threshold": 0.97,
                "weight": 1,
                "critical": False,
                "status": "matched",
            }]}), encoding="utf-8")
            result = verify_acceptance(
                [compare_path],
                task_name="accept-run",
                grid_reports=[grid_path],
                grid_reviewed=True,
                sections=sections,
                target_status="runnable",
                behavior_status="not-in-scope",
                fonts_not_in_scope=True,
                assets_not_in_scope=True,
                cwd=root,
            )
            self.assertEqual(result["status"], "MATCHED")
            self.assertTrue(all(gate["passed"] is True for gate in result["gates"].values()))

    def test_acceptance_without_comparison_is_blocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = verify_acceptance(
                [],
                task_name="blocked-acceptance",
                fonts_not_in_scope=True,
                assets_not_in_scope=True,
                cwd=Path(temporary),
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("comparison", result["blocking_gates"])

    def test_iteration_recommends_retain_without_overwriting_comparison_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copied = root / "land-copy.png"
            shutil.copy2(LAND, copied)
            baseline = root / "001-baseline.json"
            current = root / "002-current.json"
            compare_images(LAND, copied, mode="exact", output=baseline)
            compare_images(LAND, copied, mode="exact", output=current)
            result = recommend_iteration(
                current,
                baseline=baseline,
                task_name="iteration-run",
                cwd=root,
            )
            self.assertEqual(result["decision"], "hold")
            self.assertEqual(result["delta"], 0.0)
            self.assertTrue(Path(result["artifacts"]["report"]).is_file())

    def test_adaptive_grid_preserves_full_image_coordinates(self):
        result = analyze_grid(
            LAND,
            DASHBOARD,
            grid="4x4",
            min_cell=64,
            max_depth=2,
            max_leaves=64,
            top=5,
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["grid"]["coordinate_space"], "full normalized image pixels; bbox is [x, y, width, height]")
        self.assertTrue(result["grid"]["refined_paths"])
        for cell in result["hotspots"]:
            x, y, width, height = cell["bbox"]
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertGreater(width, 0)
            self.assertGreater(height, 0)
            self.assertLessEqual(x + width, 1536)
            self.assertLessEqual(y + height, 1024)

    def test_region_weighting_and_critical_threshold_are_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            regions_path = Path(temporary) / "regions.json"
            regions_path.write_text(json.dumps({
                "regions": [
                    {"name": "focal", "bbox": [0, 0, 768, 512], "weight": 3, "critical": True, "threshold": 0.99},
                    {"name": "rest", "bbox": [768, 512, 768, 512], "weight": 1},
                ]
            }), encoding="utf-8")
            result = compare_images(
                LAND,
                DASHBOARD,
                mode="region-weighted",
                regions=regions_path,
            )
            self.assertIn("weighted_similarity", result)
            self.assertEqual(len(result["critical_regions"]), 1)
            self.assertFalse(result["critical_regions"][0]["passed"])

    def test_ignore_mask_requires_a_reason_and_excludes_pixels(self):
        with tempfile.TemporaryDirectory() as temporary:
            mask_path = Path(temporary) / "mask.png"
            from PIL import Image, ImageDraw

            mask = Image.new("L", (1536, 1024), 0)
            ImageDraw.Draw(mask).rectangle((0, 0, 100, 100), fill=255)
            mask.save(mask_path)
            with self.assertRaises(PixelPerfectError):
                compare_images(LAND, DASHBOARD, ignore_mask=mask_path)
            result = compare_images(
                LAND,
                DASHBOARD,
                ignore_mask=mask_path,
                mask_reason="fixture mask for dynamic top-left area",
            )
            self.assertGreater(result["metrics"]["ignored_pixels"], 0)
            self.assertLess(result["metrics"]["considered_pixels"], result["metrics"]["total_pixels"])

    def test_public_dispatcher_uses_canonical_numeric_artifacts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            completed = subprocess.run(
                [
                    str(SCRIPT_DIR / "pixel-perfect"),
                    "normalize",
                    "--task-name", "fixture-run",
                    "--reference", str(LAND),
                    "--render", str(DASHBOARD),
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            result = json.loads(completed.stdout)
            stage = root / ".artifacts" / "pixel-perfect" / "fixture-run" / "001-normalize"
            self.assertEqual(Path(result["artifacts"]["directory"]).resolve(), stage.resolve())
            self.assertTrue((stage / "001-reference.png").is_file())
            self.assertTrue((stage / "002-render.png").is_file())
            self.assertTrue((stage / "003-manifest.json").is_file())
            comparison = subprocess.run(
                [
                    str(SCRIPT_DIR / "pixel-perfect"),
                    "compare",
                    "--task-name", "fixture-run",
                    "--reference", str(stage / "001-reference.png"),
                    "--render", str(stage / "002-render.png"),
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            comparison_result = json.loads(comparison.stdout)
            compare_stage = root / ".artifacts" / "pixel-perfect" / "fixture-run" / "002-compare"
            self.assertEqual(Path(comparison_result["artifacts"]["report"]).resolve(), (compare_stage / "001-compare.json").resolve())
            self.assertTrue((compare_stage / "001-compare.json").is_file())
            rejected = subprocess.run(
                [
                    str(SCRIPT_DIR / "pixel-perfect"),
                    "normalize",
                    "--task-name", "fixture-run",
                    "--reference", str(LAND),
                    "--render", str(DASHBOARD),
                    "--output-dir", str(root / "outside-artifacts"),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertEqual(json.loads(rejected.stdout)["status"], "failed")
            self.assertFalse((root / "outside-artifacts").exists())

    def test_existing_venv_is_reused_and_sentinel_survives_dependency_update(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            existing = root / ".venv"
            subprocess.run(
                [sys.executable, "-m", "venv", "--without-pip", str(existing)],
                check=True,
                capture_output=True,
                text=True,
            )
            sentinel = existing / "preserve-me.txt"
            sentinel.write_text("unrelated project data", encoding="utf-8")
            config_before = (existing / "pyvenv.cfg").read_bytes()
            runtime = ensure_runtime(root)
            self.assertTrue(runtime.reused)
            self.assertTrue(sentinel.is_file())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unrelated project data")
            self.assertEqual((existing / "pyvenv.cfg").read_bytes(), config_before)
            self.assertEqual(runtime.python.parent.parent, existing.resolve())
            self.assertTrue((existing / "bin" / "pip").exists() or (existing / "bin" / "pip3").exists())


if __name__ == "__main__":
    unittest.main()
