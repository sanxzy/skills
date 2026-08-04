---
name: dispatch-for-implementation
version: 1.0.0
description: |
  Dispatch implementation for one plan phase at a time using git worktree isolation and agent review gates. Use when the user asks to implement or dispatch a phase from a `generate-plan` `plan.md`, or to normalize other implementation input into phases and execute the first unfinished phase. Orchestrates dispatch-code-worker, dispatch-code-with-ui-worker, dispatch-acs-reviewer, dispatch-security-quality-reviewer, and dispatch-worker-advisor. Supports `default` and `tdd` worker modes.
---

# Dispatch For Implementation

This skill coordinates implementation of one phase at a time. It accepts a native `generate-plan` `plan.md` or other implementation input, selects one phase, creates an isolated git worktree for code changes, writes local dispatch artifacts in the main checkout, delegates implementation to a worker, runs review gates, commits approved code when required, merges with `git merge --no-ff`, updates the source plan, and stops unless the original user request explicitly asked to continue.

The coordinator orchestrates only. It must not implement code, perform codebase discovery, or make product decisions. Workers and reviewers perform all codebase exploration needed for implementation and verification.

## Trigger Boundary

Run this skill when the user explicitly asks to implement, dispatch, execute, or continue implementation for:

- A `generate-plan` `plan.md` at `_xzy-ai/sprints/<backlog>/plans/features/<NNN>/plan.md`.
- A named phase from an implementation plan.
- Free-form implementation input that should be normalized into phases.

Do not run this skill for:

- Creating specs, plans, tickets, architecture, or design documents.
- Discussion-only requests.
- Code review without implementation dispatch.
- Direct implementation by the main assistant without agent orchestration.

## Core Invariants

1. Use phase terminology everywhere. Do not call phases work units.
2. One phase is the atomic implementation phase.
3. Execute phases sequentially, never in parallel.
4. By default, execute only one phase per invocation.
5. If the original user request explicitly asks for multiple phases, repeat the same one-phase cycle for the next unfinished phase after each approved merge.
6. Native `generate-plan` compatibility is first-class: each `## Phase N` section maps to exactly one dispatch phase.
7. For native plans, skip any phase whose acceptance criteria are all checked.
8. After a phase is approved and merged, check that phase's acceptance criteria in the source `plan.md`.
9. Keep git worktree isolation per phase.
10. Write `assignment.md` and reports in the main checkout under `_xzy-ai/sprints/<backlog>/dispatch/<NNN>/...`, because `_xzy-ai/` may be local-only and not part of git worktree merges.
11. The coordinator must not perform codebase discovery. Workers and reviewers do their own exploration.
12. Escalate to the user only for missing inputs, secrets, access, environment facts, or decisions that agents cannot resolve.
13. Advisor, ACS, and security+quality retry cycles are unlimited until resolved, blocked by missing inputs, or explicitly stopped.
14. Never commit or merge unapproved code.

## Managed Paths

For backlog `<backlog>` and feature `<NNN>`, this skill manages:

```text
_xzy-ai/sprints/<backlog>/dispatch/<NNN>/progress.md
_xzy-ai/sprints/<backlog>/dispatch/<NNN>/assignments/phase-<phase>/assignment.md
_xzy-ai/sprints/<backlog>/dispatch/<NNN>/worker/report-<NN>.md
_xzy-ai/sprints/<backlog>/dispatch/<NNN>/with-ui-worker/report-<NN>.md
_xzy-ai/sprints/<backlog>/dispatch/<NNN>/reviews/dispatch-acs-reviewer/report-<NN>.md
_xzy-ai/sprints/<backlog>/dispatch/<NNN>/reviews/dispatch-security-quality-reviewer/report-<NN>.md
_xzy-ai/sprints/<backlog>/dispatch/<NNN>/advisor/report-<topic>-<NN>.md
```

The code worktree path is chosen by the coordinator and must be outside these local dispatch artifacts.

All paths passed to dispatch agents must be absolute paths. Agents operate from inside the assigned worktree, so relative paths to main-checkout artifacts are invalid.

## Worker Mode Resolution

Workers support two modes:

- `default`: implement directly with tests for functional behavior.
- `tdd`: follow Red → Green → Refactor. This is stricter and more time-consuming.

Mode resolution order:

1. Use an explicit mode supplied by the user for the current phase.
2. If no explicit mode exists, read `_xzy-ai/dispatch-mode.md` when present.
3. If no default file exists, ask the user to choose `default` or `tdd`.
4. When the user chooses interactively, ask whether to save the choice to `_xzy-ai/dispatch-mode.md`.

The selected mode applies only to the active phase.

## Input Handling

### Native `generate-plan` plan.md

A native plan has this path shape:

```text
_xzy-ai/sprints/<backlog>/plans/features/<NNN>/plan.md
```

It contains phase sections:

```markdown
## Phase 1: <Title>

**User stories covered**: ...

### What to build

...

### Acceptance criteria

- [ ] <criterion>
```

Handling rules:

1. Read the source `plan.md`.
2. Extract backlog name and feature number from the path.
3. Extract architectural decisions for background.
4. Extract each `## Phase N` section.
5. Treat each phase section as exactly one dispatch phase.
6. Select the first phase whose acceptance criteria are not all checked, unless the user explicitly named a phase.
7. If all phases are complete, stop with a concise completion summary.
8. If the source `plan.md` is specified but a phase's contract and expected output are unclear or insufficiently defined — for example, "What to build" or the acceptance criteria are missing, vague, or ambiguous in ways that affect behavior — hand off to the `discussion` skill and resolve the phase contract before dispatch. Do not dispatch an ill-defined phase.

### Other input

For non-native input:

1. Normalize the input into sequential phases using the same fields: phase number, title, background, what to build, and acceptance criteria.
2. Do not perform codebase discovery while normalizing.
3. If the input is ambiguous in ways that affect behavior, load `discussion` and resolve ambiguity before dispatch.
4. Select the first unfinished normalized phase unless the user explicitly named a phase.

## Assignment

Before delegating, write:

```text
_xzy-ai/sprints/<backlog>/dispatch/<NNN>/assignments/phase-<phase>/assignment.md
```

Follow [ASSIGNMENT-FORMAT.md](./references/ASSIGNMENT-FORMAT.md).

`assignment.md` must include:

- User background and desired outcome.
- What already happened in prior planning or dispatch processes.
- Source plan path when available.
- Selected worker mode.
- Phase number and title.
- Relevant architectural decisions from `plan.md` when available.
- The exact phase content from `plan.md`: user stories covered, what to build, and acceptance criteria.
- Prior reports from earlier failed cycles when retrying.
- Required report output paths.

`assignment.md` must not include coordinator-discovered codebase facts.

## Worker Routing

Route the selected phase by scope:

- Use `dispatch-code-with-ui-worker` for any phase with UI surface area: web, mobile, desktop, TUI, embedded UI, cross-platform UI, user interaction, visual design, layout, accessibility, or UI state. This worker owns any backend/API changes required to complete the UI-facing phase.
- Use `dispatch-code-worker` for non-UI phases: backend, infrastructure, services, libraries, automation, tooling, configuration, data, integrations, scripts, or tests without UI surface area.

If a worker returns `REJECTED: missing inputs`, the coordinator fixes the delegation if possible. If the missing input requires user decisions, secrets, access, or environment facts, ask the user.

If a worker returns `BLOCKED`, send the blocker to `dispatch-worker-advisor`. The advisor researches only and writes an advisor report. Then rerun the same worker with the advisor report. Repeat until resolved or missing inputs require the user.

## Review Gates

After worker completion, run gates in this order:

1. `dispatch-acs-reviewer`
2. `dispatch-security-quality-reviewer`

### ACS gate

The ACS reviewer verifies full relevant project state against `assignment.md` and the phase acceptance criteria. The diff is useful context, but the ACS reviewer must not review only the diff.

If ACS finds only Minor or Trivial issues, the ACS reviewer fixes them directly in the phase worktree, rechecks the affected criteria, records the direct fixes in its report, and may still approve.

If ACS rejects for Blocker, Critical, or Major findings, send findings to the same worker for fixes, then restart at ACS. Repeat until approved or missing inputs require the user.

### Security + quality gate

The merged reviewer:

- Reviews security and quality together.
- Scopes security/quality review from the phase diff.
- Independently runs required project commands itself.
- Covers linting, type checking, build, formatting, tests, coverage, static analysis, validation commands, dependency/security concerns, secrets, auth/authz, input handling, privacy, logging, config, and other applicable risk domains.

If security+quality finds only Minor or Trivial issues, the reviewer fixes them directly in the phase worktree, reruns affected checks, records the direct fixes in its report, and may still approve.

If security+quality rejects for Blocker, Critical, or Major findings, send findings to the same worker for fixes, then restart at ACS. Repeat until approved or missing inputs require the user.

## Commit and Merge Rules

Use `git merge --no-ff` for approved phase code changes.

### Default mode

1. Worker may leave changes uncommitted.
2. After ACS and security+quality approve, the coordinator creates the approved phase commit in the phase worktree:

```text
phase <NNN> [approved] <message>
```

3. Merge that commit into the main checkout with `git merge --no-ff`.

### TDD mode

Workers may create phase commits before review.

Allowed commit labels:

```text
phase <NNN> [red] <message>
phase <NNN> [green] <message>
phase <NNN> [red-fix] <message>
phase <NNN> [green-fix] <message>
```

Refactor is part of the Red → Green → Refactor cycle but is not a commit-message flag.

TDD phase commits are preserved. Do not squash them. After final approval, do not create an extra approval commit unless there are approved uncommitted changes that must be committed before merge.

## Completion

After merge:

1. Update the original `plan.md` by checking the completed phase acceptance criteria when a source plan exists.
2. Append progress events.
3. Clean up the phase worktree.
4. Stop with a concise summary unless the original user request explicitly asked to continue.
5. If continuing, select the next first unfinished phase and repeat the same workflow.

## Workflow Diagram

See [WORKFLOW.md](./references/WORKFLOW.md).

## Agents

| Agent | Role | Primary output |
|---|---|---|
| `dispatch-code-worker` | Implements non-UI phase scope. | `_xzy-ai/sprints/<backlog>/dispatch/<NNN>/worker/report-<NN>.md` |
| `dispatch-code-with-ui-worker` | Implements UI-related phase scope, including needed backend/API changes. | `_xzy-ai/sprints/<backlog>/dispatch/<NNN>/with-ui-worker/report-<NN>.md` |
| `dispatch-acs-reviewer` | Verifies implementation correctness against assignment and acceptance criteria. | `_xzy-ai/sprints/<backlog>/dispatch/<NNN>/reviews/dispatch-acs-reviewer/report-<NN>.md` |
| `dispatch-security-quality-reviewer` | Runs security review and quality gates from the phase diff. | `_xzy-ai/sprints/<backlog>/dispatch/<NNN>/reviews/dispatch-security-quality-reviewer/report-<NN>.md` |
| `dispatch-worker-advisor` | Researches blockers and provides guidance without implementing. | `_xzy-ai/sprints/<backlog>/dispatch/<NNN>/advisor/report-<topic>-<NN>.md` |
