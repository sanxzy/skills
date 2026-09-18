"""Recommend retain/rollback from two measured comparison reports.

This script never edits source code or Git state.  The agent owns the code
change and applies the recommendation through the target project's normal
version-control workflow.
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


def _score(report: Mapping[str, Any], label: str) -> float:
    metrics = report.get("metrics")
    if not isinstance(metrics, Mapping) or not isinstance(metrics.get("similarity_score"), (int, float)):
        raise PixelPerfectError(f"{label} does not contain a numeric metrics.similarity_score", status="invalid_input")
    return checked_float(metrics["similarity_score"], f"{label} similarity", minimum=0.0, maximum=1.0)


def _critical_scores(report: Mapping[str, Any]) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    rows = report.get("critical_regions")
    if not isinstance(rows, list):
        return values
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("name"), str):
            continue
        value = row.get("similarity_score")
        values[row["name"]] = float(value) if isinstance(value, (int, float)) else None
    return values


def _read_report(path: object, label: str) -> dict[str, object]:
    value = read_json(path)
    if not isinstance(value, dict) or value.get("status") != "complete":
        raise PixelPerfectError(f"{label} is not a complete comparison report", status="invalid_input")
    return value


def recommend_iteration(
    current: object,
    *,
    baseline: object | None = None,
    task_name: str,
    contract_fix_reason: str | None = None,
    epsilon: float = 0.000001,
    output: object | None = None,
    cwd: object | None = None,
) -> dict[str, object]:
    current_report = _read_report(current, "current report")
    current_score = _score(current_report, "current report")
    current_critical = _critical_scores(current_report)
    baseline_score: float | None = None
    baseline_critical: dict[str, float | None] = {}
    if baseline is not None:
        baseline_report = _read_report(baseline, "baseline report")
        baseline_score = _score(baseline_report, "baseline report")
        baseline_critical = _critical_scores(baseline_report)
    if contract_fix_reason is not None:
        reason = contract_fix_reason.strip()
        if not reason:
            raise PixelPerfectError("contract-fix reason must not be blank")
        decision = "retain"
        source_action = "agent_retain_contract_fix"
        explanation = "an explicit in-scope contract fix may be retained despite a score trade-off"
    elif baseline_score is None:
        decision = "retain"
        source_action = "agent_retain_as_baseline"
        explanation = "no prior baseline was supplied; current comparison becomes the baseline candidate"
    else:
        improvement = current_score - baseline_score
        critical_regressions = [
            name for name, old in baseline_critical.items()
            if old is not None and current_critical.get(name) is not None
            and current_critical[name] + epsilon < old
        ]
        if improvement > epsilon and not critical_regressions:
            decision = "retain"
            source_action = "agent_retain"
            explanation = "global score improved without a critical-region regression"
        elif improvement < -epsilon or critical_regressions:
            decision = "rollback"
            source_action = "agent_rollback_to_baseline"
            explanation = "current evidence is worse than the baseline or regresses a critical region"
        else:
            decision = "hold"
            source_action = "agent_reinspect"
            explanation = "change is within the comparison epsilon; inspect the hypothesis before choosing"
    report: dict[str, object] = {
        "status": "complete",
        "operation": "iteration",
        "task_name": task_name,
        "decision": decision,
        "source_action": source_action,
        "explanation": explanation,
        "baseline": {
            "path": str(Path(baseline).expanduser().resolve()) if baseline is not None else None,
            "similarity_score": baseline_score,
            "critical_regions": baseline_critical,
        },
        "current": {
            "path": str(Path(current).expanduser().resolve()),
            "similarity_score": current_score,
            "critical_regions": current_critical,
        },
        "delta": None if baseline_score is None else round(current_score - baseline_score, 6),
        "contract_fix": contract_fix_reason,
        "epsilon": epsilon,
        "agent_boundary": "this report recommends a source action; it never edits code, files, or Git history",
    }
    report_path = artifact_report_path(task_name, "iteration", output, cwd=cwd)
    report["artifacts"] = {"report": str(report_path.resolve())}
    write_json(report_path, report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = PixelPerfectArgumentParser(description="Recommend retain/rollback from comparison evidence")
    parser.add_argument("--task-name", required=True)
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--contract-fix-reason")
    parser.add_argument("--epsilon", type=float, default=0.000001)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = recommend_iteration(
        args.current,
        baseline=args.baseline,
        task_name=args.task_name,
        contract_fix_reason=args.contract_fix_reason,
        epsilon=checked_float(args.epsilon, "epsilon", minimum=0.0, maximum=0.1),
        output=artifact_report_path(args.task_name, "iteration", args.output),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


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


__all__ = ["main", "recommend_iteration"]
