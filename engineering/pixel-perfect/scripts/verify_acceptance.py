"""Evaluate explicit pixel-perfect acceptance gates into one machine report.

The script evaluates evidence and declared statuses; it does not inspect the
implementation, infer semantics, or replace the agent's behavior/accessibility
verification.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from ._common import (
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_report_path,
        checked_float,
        read_json,
        run_entrypoint,
        write_json,
    )
except ImportError:  # pragma: no cover - direct executable path
    from _common import (  # type: ignore
        PixelPerfectArgumentParser,
        PixelPerfectError,
        artifact_report_path,
        checked_float,
        read_json,
        run_entrypoint,
        write_json,
    )


_CERTAINTIES = {"exact", "substitute", "recreated", "missing", "unknown"}
_BEHAVIORS = {"passed", "not-in-scope", "partial", "failed", "unknown"}


def _gate(name: str, passed: bool | None, *, status: str, reasons: Sequence[str] = (), **details: object) -> dict[str, object]:
    return {
        "name": name,
        "passed": passed,
        "status": status,
        "reasons": list(reasons),
        **details,
    }


def _path_text(value: object) -> str:
    return str(Path(value).expanduser().resolve())


def _read_optional(path: object, label: str) -> tuple[dict[str, object] | None, str | None]:
    try:
        value = read_json(path)
    except PixelPerfectError as exc:
        return None, f"{label}: {exc}"
    if not isinstance(value, dict):
        return None, f"{label} is not a JSON object"
    return value, None


def _comparison_evidence(path: object, threshold: float) -> dict[str, object]:
    label = _path_text(path)
    report, error = _read_optional(path, "comparison report")
    if error is not None or report is None:
        return {
            "path": label,
            "status": "blocked",
            "passed": False,
            "reasons": [error or "comparison report is unavailable"],
        }
    if report.get("status") != "complete":
        return {
            "path": label,
            "status": "blocked",
            "passed": False,
            "reasons": ["comparison report did not complete"],
        }
    metrics = report.get("metrics")
    score = metrics.get("similarity_score") if isinstance(metrics, Mapping) else None
    dimensions = report.get("conditions", {}).get("dimensions") if isinstance(report.get("conditions"), Mapping) else None
    reference = report.get("reference")
    render = report.get("render")
    dimensions_valid = (
        isinstance(dimensions, list)
        and len(dimensions) == 2
        and all(isinstance(value, int) and value > 0 for value in dimensions)
        and isinstance(reference, Mapping)
        and isinstance(render, Mapping)
        and reference.get("normalized_size") == render.get("normalized_size") == dimensions
    )
    score_valid = isinstance(score, (int, float)) and 0.0 <= float(score) <= 1.0
    critical_rows = report.get("critical_regions")
    critical_failures: list[str] = []
    critical_unknown: list[str] = []
    if isinstance(critical_rows, list):
        for row in critical_rows:
            if not isinstance(row, Mapping):
                critical_unknown.append("malformed critical region")
                continue
            name = str(row.get("name", "unnamed"))
            if row.get("passed") is False:
                critical_failures.append(name)
            elif row.get("passed") is not True:
                critical_unknown.append(name)
    reasons: list[str] = []
    if not score_valid:
        reasons.append("metrics.similarity_score is missing or outside 0..1")
    elif float(score) < threshold:
        reasons.append(f"similarity {float(score):.6f} is below threshold {threshold:.6f}")
    if not dimensions_valid:
        reasons.append("reference/render dimensions are missing or inconsistent")
    if critical_failures:
        reasons.append("critical regions failed: " + ", ".join(critical_failures))
    if critical_unknown:
        reasons.append("critical regions are unknown: " + ", ".join(critical_unknown))
    passed = bool(
        score_valid
        and dimensions_valid
        and float(score) >= threshold
        and not critical_failures
        and not critical_unknown
    )
    return {
        "path": label,
        "status": "passed" if passed else "failed",
        "passed": passed,
        "score": round(float(score), 6) if score_valid else None,
        "dimensions": dimensions if dimensions_valid else None,
        "threshold": threshold,
        "critical_failures": critical_failures,
        "critical_unknown": critical_unknown,
        "reasons": reasons,
    }


def _sections_gate(path: object | None) -> dict[str, object]:
    if path is None:
        return _gate("sections", None, status="unknown", reasons=("no semantic section contract was supplied",))
    try:
        value = read_json(path)
    except PixelPerfectError as exc:
        return _gate("sections", False, status="blocked", reasons=(f"section contract: {exc}",))
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict):
        rows = value.get("sections") if isinstance(value.get("sections"), list) else value.get("regions")
    else:
        rows = None
    if not isinstance(rows, list):
        return _gate("sections", False, status="blocked", reasons=("section contract needs a sections list",))
    required = []
    failures = []
    unknown = []
    contract_errors = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            failures.append(f"section-{index}: malformed")
            continue
        if row.get("required", True) is not True:
            continue
        name = str(row.get("id", row.get("name", f"section-{index}"))).strip()
        required.append(name or f"section-{index}")
        raw_bbox = row.get("bbox", row.get("region"))
        if (
            not isinstance(raw_bbox, list)
            or len(raw_bbox) != 4
            or any(type(value) is not int for value in raw_bbox)
            or raw_bbox[0] < 0
            or raw_bbox[1] < 0
            or raw_bbox[2] <= 0
            or raw_bbox[3] <= 0
        ):
            contract_errors.append(f"{name or f'section-{index}'}: bbox must be [x, y, width, height]")
        threshold_value = row.get("threshold")
        if not isinstance(threshold_value, (int, float)) or isinstance(threshold_value, bool) or not 0.0 <= float(threshold_value) <= 1.0:
            contract_errors.append(f"{name or f'section-{index}'}: threshold must be between 0 and 1")
        weight_value = row.get("weight")
        if not isinstance(weight_value, (int, float)) or isinstance(weight_value, bool) or not float(weight_value) > 0:
            contract_errors.append(f"{name or f'section-{index}'}: weight must be positive")
        if type(row.get("critical")) is not bool:
            contract_errors.append(f"{name or f'section-{index}'}: critical must be boolean")
        status = row.get("status")
        if status != "matched":
            if status in {"blocked", "failed"}:
                failures.append(name or f"section-{index}")
            else:
                unknown.append(name or f"section-{index}")
    if contract_errors:
        return _gate("sections", False, status="blocked", reasons=contract_errors, required=required, failures=failures, unknown=unknown, contract_errors=contract_errors)
    if failures:
        return _gate("sections", False, status="failed", reasons=("required sections failed: " + ", ".join(failures),), required=required, failures=failures, unknown=unknown)
    if unknown:
        return _gate("sections", None, status="unknown", reasons=("required sections are not matched: " + ", ".join(unknown),), required=required, failures=failures, unknown=unknown)
    return _gate("sections", True, status="passed", required=required, failures=[], unknown=[])


def _certainty_rows(values: Sequence[str], label: str) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    for index, value in enumerate(values, start=1):
        if "=" in value:
            name, certainty = value.split("=", 1)
        else:
            name, certainty = f"{label}-{index}", value
        name, certainty = name.strip(), certainty.strip().lower()
        if not name or certainty not in _CERTAINTIES:
            errors.append(f"{label} status must use NAME=exact|substitute|recreated|missing|unknown")
            continue
        rows.append({"name": name, "certainty": certainty})
    return rows, errors


def _certainty_gate(
    label: str,
    values: Sequence[str],
    *,
    not_in_scope: bool,
    allow_non_exact: bool,
    allowance_reason: str | None,
) -> dict[str, object]:
    if not values and not_in_scope:
        return _gate(label, True, status="not-in-scope", rows=[])
    if not values:
        return _gate(label, None, status="unknown", reasons=(f"no {label} certainty was supplied",), rows=[])
    rows, errors = _certainty_rows(values, label)
    if errors:
        return _gate(label, False, status="blocked", reasons=errors, rows=rows)
    if allow_non_exact and not allowance_reason:
        return _gate(label, False, status="blocked", reasons=("allowing non-exact certainty requires --allowance-reason",), rows=rows)
    missing = [row["name"] for row in rows if row["certainty"] == "missing"]
    unknown = [row["name"] for row in rows if row["certainty"] == "unknown"]
    non_exact = [row["name"] for row in rows if row["certainty"] in {"substitute", "recreated"}]
    if missing:
        return _gate(label, False, status="failed", reasons=(f"missing {label}: " + ", ".join(missing),), rows=rows)
    if unknown:
        return _gate(label, None, status="unknown", reasons=(f"unproven {label}: " + ", ".join(unknown),), rows=rows)
    if non_exact and not allow_non_exact:
        return _gate(label, False, status="failed", reasons=(f"non-exact {label} requires explicit allowance: " + ", ".join(non_exact),), rows=rows)
    return _gate(
        label,
        True,
        status="passed" if not non_exact else "allowed-substitution",
        reasons=() if not non_exact else (allowance_reason or "",),
        rows=rows,
    )


def _behavior_gate(status: str) -> dict[str, object]:
    if status not in _BEHAVIORS:
        return _gate("behavior", False, status="blocked", reasons=(f"unknown behavior status: {status}",))
    if status in {"passed", "not-in-scope"}:
        return _gate("behavior", True, status=status)
    if status == "unknown":
        return _gate("behavior", None, status="unknown", reasons=("behavior was not independently verified",))
    return _gate("behavior", False, status=status, reasons=("in-scope behavior did not pass",))


def _target_gate(status: str) -> dict[str, object]:
    if status == "runnable":
        return _gate("target", True, status="passed")
    if status == "blocked":
        return _gate("target", False, status="blocked", reasons=("target renderer/implementation is blocked",))
    return _gate("target", None, status="unknown", reasons=("target run status was not declared",))


def _grid_gate(paths: Sequence[object], *, reviewed: bool, threshold: float) -> dict[str, object]:
    if not paths:
        return _gate("adaptive_grid", None, status="unknown", reasons=("no adaptive-grid report was supplied",), reports=[])
    reports: list[dict[str, object]] = []
    errors: list[str] = []
    hotspots = 0
    for path in paths:
        label = _path_text(path)
        report, error = _read_optional(path, "grid report")
        if error is not None or report is None or report.get("status") != "complete":
            errors.append(error or f"grid report is incomplete: {label}")
            continue
        rows = report.get("hotspots")
        high = [row for row in rows if isinstance(row, Mapping) and isinstance(row.get("severity"), (int, float)) and float(row["severity"]) >= threshold] if isinstance(rows, list) else []
        hotspots += len(high)
        reports.append({"path": label, "status": "available", "high_severity_hotspots": len(high)})
    if errors:
        return _gate("adaptive_grid", False, status="blocked", reasons=errors, reports=reports, high_severity_hotspots=hotspots)
    if not reviewed:
        return _gate(
            "adaptive_grid",
            False,
            status="review-required",
            reasons=("agent must map hotspots to semantic/critical regions and declare --grid-reviewed",),
            reports=reports,
            high_severity_hotspots=hotspots,
        )
    return _gate("adaptive_grid", True, status="reviewed", reports=reports, high_severity_hotspots=hotspots, hotspot_threshold=threshold)


def verify_acceptance(
    compare_reports: Sequence[object],
    *,
    task_name: str,
    level: str = "high",
    threshold: float | None = None,
    grid_reports: Sequence[object] = (),
    grid_reviewed: bool = False,
    sections: object | None = None,
    target_status: str = "unknown",
    behavior_status: str = "unknown",
    font_status: Sequence[str] = (),
    asset_status: Sequence[str] = (),
    fonts_not_in_scope: bool = False,
    assets_not_in_scope: bool = False,
    allow_non_exact: bool = False,
    allowance_reason: str | None = None,
    grid_hotspot_threshold: float = 0.05,
    iteration_reports: Sequence[object] = (),
    output: object | None = None,
    cwd: object | None = None,
) -> dict[str, object]:
    levels = {"exact": 0.99, "high": 0.97}
    if level not in {"exact", "high", "custom"}:
        raise PixelPerfectError("acceptance level must be exact, high, or custom")
    if level == "custom" and threshold is None:
        raise PixelPerfectError("custom acceptance requires --threshold")
    selected_threshold = checked_float(threshold if threshold is not None else levels[level], "acceptance threshold", minimum=0.0, maximum=1.0)
    comparisons = [_comparison_evidence(path, selected_threshold) for path in compare_reports]
    if not comparisons:
        comparison_gate = _gate("comparison", False, status="blocked", reasons=("at least one comparison report is required",), reports=[])
    else:
        blocked = [item for item in comparisons if item.get("status") == "blocked"]
        failed = [item for item in comparisons if item.get("passed") is False and item not in blocked]
        comparison_gate = _gate(
            "comparison",
            not blocked and not failed,
            status="blocked" if blocked else ("passed" if not failed else "failed"),
            reasons=[f"comparison evidence unavailable: {item.get('path')}" for item in blocked]
            + [f"comparison failed: {item.get('path')}" for item in failed],
            reports=comparisons,
        )
    dimensions_gate = _gate(
        "dimensions",
        bool(comparisons) and all(item.get("dimensions") is not None for item in comparisons),
        status="passed" if comparisons and all(item.get("dimensions") is not None for item in comparisons) else "failed",
        reasons=[] if comparisons and all(item.get("dimensions") is not None for item in comparisons) else ["every comparison must prove matching reference/render dimensions"],
        dimensions=[item.get("dimensions") for item in comparisons],
    )
    critical_failed = [
        f"{item.get('path')}: {name}"
        for item in comparisons
        for name in item.get("critical_failures", []) if isinstance(item.get("critical_failures"), list)
    ]
    critical_unknown = [
        f"{item.get('path')}: {name}"
        for item in comparisons
        for name in item.get("critical_unknown", []) if isinstance(item.get("critical_unknown"), list)
    ]
    critical_gate = _gate(
        "critical_regions",
        not critical_failed and not critical_unknown if comparisons else False,
        status="failed" if critical_failed else ("unknown" if critical_unknown else "passed"),
        reasons=(["critical regions failed: " + ", ".join(critical_failed)] if critical_failed else [])
        + (["critical regions unknown: " + ", ".join(critical_unknown)] if critical_unknown else []),
        failures=critical_failed,
        unknown=critical_unknown,
    )
    sections_gate = _sections_gate(sections)
    fonts_gate = _certainty_gate(
        "fonts", font_status, not_in_scope=fonts_not_in_scope,
        allow_non_exact=allow_non_exact, allowance_reason=allowance_reason,
    )
    assets_gate = _certainty_gate(
        "assets", asset_status, not_in_scope=assets_not_in_scope,
        allow_non_exact=allow_non_exact, allowance_reason=allowance_reason,
    )
    target_gate = _target_gate(target_status)
    behavior_gate = _behavior_gate(behavior_status)
    grid_gate = _grid_gate(grid_reports, reviewed=grid_reviewed, threshold=checked_float(grid_hotspot_threshold, "grid hotspot threshold", minimum=0.0, maximum=1.0))
    iteration_rows: list[dict[str, object]] = []
    iteration_errors: list[str] = []
    for path in iteration_reports:
        report, error = _read_optional(path, "iteration report")
        label = _path_text(path)
        if error is not None or report is None:
            iteration_errors.append(error or f"iteration report unavailable: {label}")
        else:
            decision = report.get("decision")
            iteration_rows.append({"path": label, "decision": decision})
            if decision != "retain":
                iteration_errors.append(f"iteration is not settled ({decision}): {label}")
    regression_gate = _gate(
        "regression",
        not iteration_errors,
        status="passed" if not iteration_errors else "failed",
        reasons=iteration_errors,
        reports=iteration_rows,
    )
    gates = {
        "comparison": comparison_gate,
        "dimensions": dimensions_gate,
        "critical_regions": critical_gate,
        "sections": sections_gate,
        "fonts": fonts_gate,
        "assets": assets_gate,
        "target": target_gate,
        "behavior": behavior_gate,
        "adaptive_grid": grid_gate,
        "regression": regression_gate,
    }
    blocking_names = [name for name, gate in gates.items() if gate.get("status") == "blocked"]
    all_passed = all(gate.get("passed") is True for gate in gates.values())
    final_status = "BLOCKED" if blocking_names else ("MATCHED" if all_passed else "PARTIAL")
    report: dict[str, object] = {
        "status": final_status,
        "operation": "acceptance",
        "task_name": task_name,
        "level": level,
        "threshold": selected_threshold,
        "gates": gates,
        "blocking_gates": blocking_names,
        "agent_boundary": "the script evaluates supplied evidence and declarations; the agent owns semantic diagnosis, implementation, and target behavior proof",
    }
    report_path = artifact_report_path(task_name, "acceptance", output, cwd=cwd)
    report["artifacts"] = {"report": str(report_path.resolve())}
    write_json(report_path, report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = PixelPerfectArgumentParser(description="Evaluate machine-readable pixel-perfect acceptance gates")
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--compare", action="append", default=[], type=Path)
    parser.add_argument("--level", choices=("exact", "high", "custom"), default="high")
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--grid", action="append", default=[], type=Path)
    parser.add_argument("--grid-reviewed", action="store_true")
    parser.add_argument("--sections", type=Path)
    parser.add_argument("--target-status", choices=("runnable", "blocked", "unknown"), default="unknown")
    parser.add_argument("--behavior-status", choices=tuple(sorted(_BEHAVIORS)), default="unknown")
    parser.add_argument("--font-status", action="append", default=[])
    parser.add_argument("--asset-status", action="append", default=[])
    parser.add_argument("--fonts-not-in-scope", action="store_true")
    parser.add_argument("--assets-not-in-scope", action="store_true")
    parser.add_argument("--allow-non-exact", action="store_true")
    parser.add_argument("--allowance-reason")
    parser.add_argument("--grid-hotspot-threshold", type=float, default=0.05)
    parser.add_argument("--iteration", action="append", default=[], type=Path)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = verify_acceptance(
        args.compare,
        task_name=args.task_name,
        level=args.level,
        threshold=args.threshold,
        grid_reports=args.grid,
        grid_reviewed=args.grid_reviewed,
        sections=args.sections,
        target_status=args.target_status,
        behavior_status=args.behavior_status,
        font_status=args.font_status,
        asset_status=args.asset_status,
        fonts_not_in_scope=args.fonts_not_in_scope,
        assets_not_in_scope=args.assets_not_in_scope,
        allow_non_exact=args.allow_non_exact,
        allowance_reason=args.allowance_reason,
        grid_hotspot_threshold=args.grid_hotspot_threshold,
        iteration_reports=args.iteration,
        output=args.output,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "MATCHED" else 2


def _entrypoint(argv: Sequence[str] | None = None) -> int:
    try:
        rerun = run_entrypoint(__file__, tuple(argv if argv is not None else sys.argv[1:]))
        if rerun is not None:
            return rerun
        return main(argv)
    except PixelPerfectError as exc:
        print(json.dumps({"status": exc.status, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_entrypoint())


__all__ = ["main", "verify_acceptance"]
