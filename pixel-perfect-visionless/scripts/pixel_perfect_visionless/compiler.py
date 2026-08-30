"""Public Compiler interface for the visionless visual UI pipeline."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from . import __version__
from .artifacts import RunArtifacts
from .bootstrap import ensure_environment
from .reporting import (
    comparison_markdown,
    compile_markdown,
    inspection_markdown,
    structured_diff_markdown,
    verification_markdown,
)

if TYPE_CHECKING:
    from .bootstrap import Runtime


class CompilerError(RuntimeError):
    """A compiler operation failed after writing its persistent error result."""

    def __init__(self, message: str, *, run_dir: Path | None = None):
        super().__init__(message)
        self.run_dir = run_dir


class Compiler:
    """Small public interface backed by the persistent visionless pipeline."""

    def __init__(
        self,
        *,
        workspace_root: Path | None = None,
        project_root: Path | None = None,
        output_root: Path | None = None,
        install: bool = True,
        base_python: Path | None = None,
    ):
        self.workspace_root = Path(workspace_root or Path.cwd()).expanduser().resolve()
        self.project_root = Path(project_root or self.workspace_root).expanduser().resolve()
        if output_root:
            output_path = Path(output_root).expanduser()
            self.output_root = output_path.resolve() if output_path.is_absolute() else (self.workspace_root / output_path).resolve()
        else:
            self.output_root = None
        self.install = install
        self.base_python = Path(base_python).expanduser().resolve() if base_python else None
        self._runtime_cache: Runtime | None = None

    def setup(self, *, install_browser: bool = False, run_dir: Path | None = None) -> dict[str, Any]:
        def operation(writer: RunArtifacts) -> dict[str, Any]:
            from .browser import find_system_browser

            needs_playwright = install_browser and find_system_browser() is None
            runtime = self._runtime(need_browser=needs_playwright)
            if install_browser:
                from .bootstrap import ensure_playwright_browser

                if find_system_browser() is None:
                    ensure_playwright_browser(runtime, install=self.install)
            manifest = self._manifest(runtime, configuration={"install_browser": install_browser})
            writer.write_manifest(manifest)
            return {
                "status": "ok",
                "operation": "setup",
                "runtime": runtime.as_dict(),
                "manifest": manifest,
                "commands": runtime.command_records(),
            }

        return self._execute("setup", operation, run_dir=run_dir)

    def inspect(
        self,
        image: str | Path,
        *,
        points: list[tuple[int, int]] | None = None,
        run_dir: Path | None = None,
    ) -> dict[str, Any]:
        source = self._input_path(image)

        def operation(writer: RunArtifacts) -> dict[str, Any]:
            runtime = self._runtime()
            from .images import inspect_image
            from .project import inspect_project

            report = inspect_image(source, points=points or [])
            report["project"] = inspect_project(self.project_root)
            report["runtime"] = runtime.as_dict()
            manifest = self._manifest(runtime, source=source, configuration={"points": points or []})
            writer.write_manifest(manifest)
            writer.write_json("inspection.json", report)
            writer.write_text("inspection.md", inspection_markdown(report))
            return {
                "status": "ok",
                "operation": "inspect",
                "inspection": report,
                "artifacts": {
                    "inspection_json": str(writer.path("inspection.json")),
                    "inspection_markdown": str(writer.path("inspection.md")),
                    "manifest": str(writer.path("manifest.json")),
                },
                "runtime": runtime.as_dict(),
            }

        return self._execute("inspect", operation, run_dir=run_dir)

    def compile(
        self,
        image: str | Path,
        *,
        debug_artifacts: bool = False,
        run_dir: Path | None = None,
    ) -> dict[str, Any]:
        source = self._input_path(image)

        def operation(writer: RunArtifacts) -> dict[str, Any]:
            from .extraction import extract_image
            from .ir import build_ir
            from .projections import ascii_projection, debug_overlay, layout_text

            runtime = self._runtime()
            extraction = extract_image(source, tesseract=runtime.tesseract)
            ir = build_ir(extraction)
            manifest = self._manifest(
                runtime,
                source=source,
                configuration={"debug_artifacts": debug_artifacts, "ocr_language": "eng"},
            )
            writer.write_manifest(manifest)
            struct_path = writer.write_json("design.struct.json", ir)
            layout_path = writer.write_text("design.layout.txt", layout_text(ir))
            ascii_path = writer.write_text("design.ascii", ascii_projection(ir))
            artifacts: dict[str, str] = {
                "struct": str(struct_path),
                "layout": str(layout_path),
                "ascii": str(ascii_path),
                "manifest": str(writer.path("manifest.json")),
            }
            if debug_artifacts:
                debug_root = writer.path("debug")
                debug_root.mkdir(parents=True, exist_ok=True)
                original = extraction.debug["original"]
                original_path = writer.write_image("debug/original.png", original)
                from PIL import Image

                grayscale_path = writer.write_image("debug/grayscale.png", Image.fromarray(extraction.debug["grayscale"]))
                edges_path = writer.write_image("debug/edges.png", Image.fromarray(extraction.debug["edges"]))
                geometry_path = writer.write_image("debug/detected-geometry.png", debug_overlay(original, ir))
                artifacts.update(
                    {
                        "debug_original": str(original_path),
                        "debug_grayscale": str(grayscale_path),
                        "debug_edges": str(edges_path),
                        "debug_geometry": str(geometry_path),
                    }
                )
            writer.write_json("compile.json", {"ir": ir, "artifacts": artifacts, "manifest": manifest})
            writer.write_text("compile.md", compile_markdown(ir, artifacts))
            return {
                "status": "ok",
                "operation": "compile",
                "ir": ir,
                "artifacts": artifacts,
                "manifest": manifest,
                "runtime": runtime.as_dict(),
            }

        return self._execute("compile", operation, run_dir=run_dir)

    def render(
        self,
        *,
        url: str | None = None,
        entry: str | None = None,
        reference: str | Path | None = None,
        viewport: str | None = None,
        browser: str | None = None,
        wait_ms: int = 250,
        timeout: float = 60.0,
        ready_selector: str | None = None,
        run_dir: Path | None = None,
    ) -> dict[str, Any]:
        reference_path = self._input_path(reference) if reference else None

        def operation(writer: RunArtifacts) -> dict[str, Any]:
            from .browser import find_system_browser
            from .images import inspect_image, parse_viewport
            from .rendering import render_target, resolve_target_url

            needs_playwright = browser is not None and browser.lower() in {"playwright", "chromium-playwright"}
            if browser is None and find_system_browser() is None:
                needs_playwright = True
            runtime = self._runtime(need_browser=needs_playwright)

            resolved_viewport = viewport
            if not resolved_viewport:
                if not reference_path:
                    raise ValueError("Provide reference or viewport for render")
                resolved_viewport = inspect_image(reference_path)["viewport"]
            parse_viewport(resolved_viewport)
            target = resolve_target_url(
                self.project_root,
                workspace_root=self.workspace_root,
                url=url,
                entry=entry,
            )
            output = writer.path("candidate.png")
            render_report = render_target(
                runtime,
                url=target,
                output=output,
                viewport=resolved_viewport,
                browser=browser,
                wait_ms=wait_ms,
                timeout=timeout,
                ready_selector=ready_selector,
                install=self.install,
            )
            result = {
                "status": "ok",
                "operation": "render",
                "viewport": resolved_viewport,
                "render": render_report,
                "runtime": runtime.as_dict(),
                "artifacts": {"candidate": str(output)},
            }
            writer.write_manifest(self._manifest(runtime, source=reference_path, configuration={"viewport": resolved_viewport, "url": target}))
            result["artifacts"].update({"report": str(writer.path("render.json")), "report_markdown": str(writer.path("render.md")), "manifest": str(writer.path("manifest.json"))})
            writer.write_json("render.json", result)
            writer.write_text("render.md", _render_markdown(result))
            return result

        return self._execute("render", operation, run_dir=run_dir)

    def compare(
        self,
        reference: str | Path,
        candidate: str | Path,
        *,
        tolerance: int = 10,
        regions: list[tuple[str, tuple[int, int, int, int]]] | None = None,
        points: list[tuple[int, int]] | None = None,
        run_dir: Path | None = None,
    ) -> dict[str, Any]:
        reference_path = self._input_path(reference)
        candidate_path = self._input_path(candidate)

        def operation(writer: RunArtifacts) -> dict[str, Any]:
            from .comparison import compare_irs
            from .extraction import extract_image
            from .images import compare_images
            from .ir import build_ir

            runtime = self._runtime()
            pixel_report, reference_image, candidate_image = compare_images(
                reference_path,
                candidate_path,
                regions=regions or [],
                tolerance=tolerance,
                points=points or [],
            )
            reference_ir = build_ir(extract_image(reference_path, tesseract=runtime.tesseract))
            candidate_ir = build_ir(extract_image(candidate_path, tesseract=runtime.tesseract))
            structured = compare_irs(reference_ir, candidate_ir, pixel_report)
            return self._write_comparison(
                writer,
                runtime,
                pixel_report,
                structured,
                reference_ir,
                candidate_ir,
                reference_image,
                candidate_image,
                configuration={"tolerance": tolerance, "regions": regions or [], "points": points or []},
            )

        return self._execute("compare", operation, run_dir=run_dir)

    def verify(
        self,
        reference: str | Path,
        *,
        candidate: str | Path | None = None,
        url: str | None = None,
        entry: str | None = None,
        viewport: str | None = None,
        browser: str | None = None,
        wait_ms: int = 250,
        timeout: float = 60.0,
        ready_selector: str | None = None,
        tolerance: int = 10,
        max_mae: float = 10.0,
        max_region_mae: float | None = None,
        min_within_tolerance: float = 0.85,
        max_hotspot_mean_error: float = 64.0,
        regions: list[tuple[str, tuple[int, int, int, int]]] | None = None,
        points: list[tuple[int, int]] | None = None,
        run_dir: Path | None = None,
    ) -> dict[str, Any]:
        reference_path = self._input_path(reference)
        candidate_path = self._input_path(candidate) if candidate else None

        def operation(writer: RunArtifacts) -> dict[str, Any]:
            if max_mae < 0:
                raise ValueError("max_mae must be non-negative")
            if max_region_mae is not None and max_region_mae < 0:
                raise ValueError("max_region_mae must be non-negative")
            if not 0 <= min_within_tolerance <= 1:
                raise ValueError("min_within_tolerance must be between 0 and 1")
            if max_hotspot_mean_error < 0:
                raise ValueError("max_hotspot_mean_error must be non-negative")
            from .browser import find_system_browser
            from .comparison import compare_irs
            from .extraction import extract_image
            from .images import compare_images, inspect_image, parse_viewport
            from .ir import build_ir
            from .smoke import smoke_check

            needs_playwright = candidate_path is None and (
                browser is not None and browser.lower() in {"playwright", "chromium-playwright"}
                or browser is None and find_system_browser() is None
            )
            runtime = self._runtime(need_browser=needs_playwright)
            render_report = None
            resolved_viewport = viewport or inspect_image(reference_path)["viewport"]
            parse_viewport(resolved_viewport)
            candidate_for_compare = candidate_path
            if candidate_for_compare is None:
                from .rendering import render_target, resolve_target_url

                target = resolve_target_url(self.project_root, workspace_root=self.workspace_root, url=url, entry=entry)
                candidate_for_compare = writer.path("candidate.png")
                render_report = render_target(
                    runtime,
                    url=target,
                    output=candidate_for_compare,
                    viewport=resolved_viewport,
                    browser=browser,
                    wait_ms=wait_ms,
                    timeout=timeout,
                    ready_selector=ready_selector,
                    install=self.install,
                )
            pixel_report, reference_image, candidate_image = compare_images(
                reference_path,
                candidate_for_compare,
                regions=regions or [],
                tolerance=tolerance,
                points=points or [],
            )
            reference_ir = build_ir(extract_image(reference_path, tesseract=runtime.tesseract))
            candidate_ir = build_ir(extract_image(candidate_for_compare, tesseract=runtime.tesseract))
            structured = compare_irs(reference_ir, candidate_ir, pixel_report)
            comparison = self._write_comparison(
                writer,
                runtime,
                pixel_report,
                structured,
                reference_ir,
                candidate_ir,
                reference_image,
                candidate_image,
                configuration={"tolerance": tolerance, "regions": regions or [], "points": points or [], "viewport": resolved_viewport},
                write_result=False,
            )
            metrics = pixel_report["metrics"]
            hottest_tile = metrics["tile_hotspots"][0]["mean_error"] if metrics["tile_hotspots"] else 0.0
            checks = [
                {"name": "dimensions", "status": "pass", "detail": f"reference and candidate are both {pixel_report['viewport']}"},
                {"name": "mean_abs_error", "status": "pass" if metrics["mean_abs_error"] <= max_mae else "fail", "detail": f"{metrics['mean_abs_error']:.4f} <= {max_mae:.4f}"},
                {"name": "within_tolerance_fraction", "status": "pass" if metrics["within_tolerance_fraction"] >= min_within_tolerance else "fail", "detail": f"{metrics['within_tolerance_fraction']:.4f} >= {min_within_tolerance:.4f}"},
                {"name": "hottest_tile", "status": "pass" if hottest_tile <= max_hotspot_mean_error else "fail", "detail": f"{hottest_tile:.4f} <= {max_hotspot_mean_error:.4f}"},
            ]
            region_limit = max_region_mae if max_region_mae is not None else max_mae * 1.5
            for region in pixel_report.get("regions", []):
                checks.append({
                    "name": f"region_{region['name']}_mean_abs_error",
                    "status": "pass" if region["mean_abs_error"] <= region_limit else "fail",
                    "detail": f"{region['mean_abs_error']:.4f} <= {region_limit:.4f}",
                })
            candidate_smoke = smoke_check(candidate_for_compare)
            checks.append({
                "name": "candidate_smoke",
                "status": candidate_smoke["status"],
                "detail": f"{candidate_smoke['sample_unique_colors']} sampled colors; non_flat={candidate_smoke['non_flat']}",
            })
            if render_report:
                errors = render_report.get("console_errors", []) + render_report.get("page_errors", [])
                checks.append({"name": "browser_runtime_errors", "status": "pass" if not errors else "fail", "detail": "none" if not errors else "; ".join(errors[:5])})
            passed = all(check["status"] == "pass" for check in checks)
            result = {
                "status": "pass" if passed else "fail",
                "operation": "verify",
                "viewport": resolved_viewport,
                "candidate": str(Path(candidate_for_compare).resolve()),
                "reference": str(reference_path),
                "checks": checks,
                "comparison": comparison["comparison"],
                "structured_diff": structured,
                "smoke": candidate_smoke,
                "render": render_report,
                "runtime": runtime.as_dict(),
                "artifacts": comparison["artifacts"],
            }
            result["artifacts"]["verification"] = str(writer.path("verification.json"))
            result["artifacts"]["verification_markdown"] = str(writer.path("verification.md"))
            writer.write_json("verification.json", result)
            writer.write_text("verification.md", verification_markdown(result))
            writer.write_manifest(self._manifest(runtime, source=reference_path, configuration={"tolerance": tolerance, "max_mae": max_mae, "max_region_mae": max_region_mae, "min_within_tolerance": min_within_tolerance}))
            return result

        return self._execute("verify", operation, run_dir=run_dir)

    def _runtime(self, *, need_browser: bool = False) -> Runtime:
        if self._runtime_cache is None or (need_browser and not self._runtime_cache.playwright_available):
            self._runtime_cache = ensure_environment(
                self.project_root,
                workspace_root=self.workspace_root,
                install=self.install,
                need_playwright=need_browser,
                base_python=self.base_python,
            )
        return self._runtime_cache

    def _input_path(self, value: str | Path | None) -> Path:
        if value is None:
            raise ValueError("Image path is required")
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.workspace_root / path
        return path.resolve()

    def _manifest(self, runtime: Runtime, *, source: Path | None = None, configuration: dict[str, Any] | None = None) -> dict[str, Any]:
        from .images import source_sha256

        manifest: dict[str, Any] = {
            "schema": "visual-ui-run",
            "version": 1,
            "compiler_version": __version__,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "runtime": runtime.as_dict(),
            "configuration": configuration or {},
        }
        if source:
            manifest["source"] = {"path": str(source), "sha256": source_sha256(source)}
        return manifest

    def _write_comparison(
        self,
        writer: RunArtifacts,
        runtime: Runtime,
        pixel_report: dict[str, Any],
        structured: dict[str, Any],
        reference_ir: dict[str, Any],
        candidate_ir: dict[str, Any],
        reference_image: Any,
        candidate_image: Any,
        *,
        configuration: dict[str, Any],
        write_result: bool = True,
    ) -> dict[str, Any]:
        from .images import source_sha256

        reference_struct = writer.write_json("reference.struct.json", reference_ir)
        candidate_struct = writer.write_json("candidate.struct.json", candidate_ir)
        visual = writer.path("visual")
        visual_artifacts = self._save_visual_artifacts(reference_image, candidate_image, visual, int(configuration.get("tolerance", 10)))
        comparison = {"schema": "visual-ui-comparison", "version": 1, "pixel": pixel_report, "structured": structured}
        comparison_path = writer.write_json("comparison.json", comparison)
        diff_path = writer.write_json("diff.json", structured)
        comparison_md = writer.write_text("comparison.md", comparison_markdown(pixel_report, structured))
        diff_md = writer.write_text("diff.md", structured_diff_markdown(structured))
        manifest = self._manifest(runtime, source=Path(pixel_report["reference"]), configuration=configuration)
        manifest["candidate"] = {"path": pixel_report["candidate"], "sha256": source_sha256(Path(pixel_report["candidate"]))}
        writer.write_manifest(manifest)
        artifacts = {
            "reference_struct": str(reference_struct),
            "candidate_struct": str(candidate_struct),
            "comparison": str(comparison_path),
            "comparison_markdown": str(comparison_md),
            "diff": str(diff_path),
            "diff_markdown": str(diff_md),
            "manifest": str(writer.path("manifest.json")),
            **visual_artifacts,
        }
        result = {
            "status": "ok",
            "operation": "compare",
            "comparison": comparison,
            "artifacts": artifacts,
            "runtime": runtime.as_dict(),
        }
        if write_result:
            writer.write_json("compare.json", result)
            writer.write_text("compare.md", comparison_markdown(pixel_report, structured))
        return {"comparison": comparison, "structured": structured, "artifacts": artifacts, "result": result}

    @staticmethod
    def _save_visual_artifacts(reference: Any, candidate: Any, output: Path, tolerance: int) -> dict[str, str]:
        from .images import save_visual_artifacts

        return save_visual_artifacts(reference, candidate, output, tolerance=tolerance)

    def _execute(
        self,
        operation_name: str,
        callback: Callable[[RunArtifacts], dict[str, Any]],
        *,
        run_dir: Path | None = None,
    ) -> dict[str, Any]:
        writer: RunArtifacts | None = None
        try:
            writer = RunArtifacts.from_workspace(
                self.workspace_root,
                operation_name,
                output_root=self.output_root,
                run_dir=run_dir,
            )
            result = callback(writer)
            result.setdefault("operation", operation_name)
            result.setdefault("status", "ok")
            writer.finalize(result, markdown=_operation_markdown(result, operation_name))
            return {**result, "run_dir": str(writer.run_dir), "result_json": str(writer.path("result.json")), "result_markdown": str(writer.path("result.md"))}
        except Exception as exc:
            if writer is None and run_dir is not None:
                try:
                    writer = RunArtifacts.from_workspace(
                        self.workspace_root,
                        operation_name,
                        output_root=self.output_root,
                    )
                except Exception:
                    writer = None
            error_result = {
                "status": "error",
                "operation": operation_name,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
            if writer is not None:
                try:
                    writer.finalize(error_result)
                except Exception:
                    pass
            raise CompilerError(str(exc), run_dir=writer.run_dir if writer is not None else None) from exc


def _render_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Pixel-perfect visionless render",
            "",
            f"- Status: **{result.get('status', 'unknown').upper()}**",
            f"- Viewport: `{result.get('viewport')}`",
            f"- Candidate: `{result.get('artifacts', {}).get('candidate')}`",
            "",
        ]
    )


def _operation_markdown(result: dict[str, Any], operation: str) -> str:
    if operation == "verify":
        return verification_markdown(result)
    if operation == "compile" and result.get("ir"):
        return compile_markdown(result["ir"], result.get("artifacts"))
    if operation == "compare" and result.get("comparison"):
        return comparison_markdown(result["comparison"]["pixel"], result["comparison"]["structured"])
    if operation == "render":
        return _render_markdown(result)
    if operation == "inspect" and result.get("inspection"):
        return inspection_markdown(result["inspection"])
    return "\n".join(
        [
            f"# Pixel-perfect visionless {operation}",
            "",
            f"- Status: **{result.get('status', 'unknown').upper()}**",
            f"- Operation: `{operation}`",
            "",
        ]
    )
