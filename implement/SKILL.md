---
name: implement
version: 1.0.0
description: |
  Implement one plan phase directly in the current checkout with no worktrees, no bundled agents, and no review gates. Use when the user asks to implement or continue a phase from a `generate-plan` `plan.md`, or provides free-form implementation input for direct host-driven implementation. Resolves `default` or `tdd` mode with the user, requires a clean working tree, implements the selected phase, verifies with normal project commands, commits per mode convention, and checks the source plan's acceptance criteria.
---

# Implement

This skill implements exactly one phase directly. The host performs all codebase discovery, architecture reading, third-party documentation research, implementation, testing, and plan updates itself — nothing is delegated and no bundled agents are used.

This is the direct, lightweight counterpart to `dispatch-for-implementation`:

| Aspect | `implement` | `dispatch-for-implementation` |
|---|---|---|
| Who implements | The host, directly | A bundled worker agent |
| Isolation | Current checkout, no worktrees | Git worktree per phase |
| Review gates | None — normal tests/commands only | ACS + security/quality reviewers |
| Artifacts | None written | assignment.md, reports, progress |
| Modes | `default` and `tdd` | `default` and `tdd` |

## Trigger Boundary

Run this skill when the user explicitly asks to implement, execute, or continue implementation for:

- A `generate-plan` `plan.md` at `_xzy-ai/sprints/<backlog>/plans/features/<NNN>/plan.md`.
- A named phase from an implementation plan.
- Free-form implementation input treated as a single phase.

Do not run this skill for:

- Creating specs, plans, tickets, architecture, or design documents.
- Discussion-only requests.
- Implementation that should be delegated to agent orchestration with worktrees and review gates — use `dispatch-for-implementation` for that.

## Core Invariants

1. The host implements directly. No bundled agents, no subagents, no delegation.
2. Work in the current checkout. No git worktrees are created.
3. No review gates run beyond the host's own verification with normal project commands.
4. One phase is the atomic unit. Execute exactly one phase per invocation.
5. Skip any phase whose acceptance criteria are all checked in a native plan.
6. Use phase terminology. Do not call phases work units or tickets.
7. Write no dispatch artifacts: no assignment.md, no reports, no progress.md.
8. Escalate to the user only for mode choice, uncommitted changes, plan selection, missing verification commands, or unresolved verification failures.
9. Never commit unrelated changes. The phase commit contains only phase work.
10. Do not perform external research when internal project conventions suffice.

## Mode Resolution

Ask the user to choose `default` or `tdd` when no explicit mode is supplied — every invocation, not just the first. No persistent mode file is read or written; `_xzy-ai/dispatch-mode.md` and any implement-specific default are intentionally ignored.

- `default`: implement directly, run verification, commit once after validation passes.
- `tdd`: follow Red → Green → Refactor with mode-labeled commits.

The selected mode applies only to the active phase.

See [MODE.md](./references/MODE.md).

## Input Handling

### Native `generate-plan` plan.md

A native plan has this path shape:

```text
_xzy-ai/sprints/<backlog>/plans/features/<NNN>/plan.md
```

Handling rules:

1. Find candidate plans. If exactly one plan exists in the repository, use it. If multiple candidate plans exist and the user named none, ask which feature/plan to implement.
2. Extract the backlog name, feature number, and feature name from the path.
3. Extract architectural decisions for background.
4. Extract each `## Phase N` section as one phase.
5. Select the first phase whose acceptance criteria are not all checked, unless the user explicitly named a phase.
6. If all phases are complete, stop with a concise completion summary and commit nothing.

### Free-form input

For non-plan input:

1. Treat the input as exactly one implementation phase. Multi-phase work belongs in a plan.
2. Do not persist any normalized plan or resume artifact.
3. If the input is ambiguous in ways that affect behavior, load `discussion` and resolve ambiguity before implementing.

## Preconditions

Before implementing:

1. Verify the working tree. If uncommitted changes exist, ask the user whether to commit them, stash them, or stop. The working tree must be clean before implementation begins. Pre-existing changes under `_xzy-ai/` are planning artifacts and are excluded from this requirement.
2. Confirm the mode when not explicitly supplied (`default` or `tdd`).
3. Read the phase content: user stories covered, what to build, and acceptance criteria.
4. Read `_xzy-ai/architecture.md` when present.
5. Perform codebase discovery directly: existing patterns, tests, commands, and conventions. The host owns this — it is not a violation of any restriction.
6. If relevant internal guidance is unavailable, research third-party packages with official documentation and verify latest stable versions before use.

## Implementation

1. Classify the phase from its acceptance criteria:
   - `functional`: any criterion describes observable behavior, validation, state, failure handling, integration, user-visible behavior, or business logic.
   - `scaffolding`: criteria describe only file structure, boilerplate, placeholders, configuration shape, or non-functional skeletons.
2. Implement the phase directly in the current checkout.
3. Testing rules:
   - Functional phases must include tests or a clear project-appropriate verification path in both modes.
   - Scaffolding phases do not require tests but must pass relevant syntax/build/config checks when available.
4. In `tdd` mode for functional phases, follow Red → Green → Refactor. Refactor is part of the cycle but not a commit-message flag.
5. Verify with the project's normal commands. Determine the command set from project configuration, README, AGENTS.md, or package manifests.

### Verification fallback

If no test command is identifiable, use this fallback chain:

1. Build
2. Lint
3. Typecheck
4. User-defined command

If no applicable command exists after the chain, ask the user for the correct verification command before committing.

### Retry budget

- Make up to three self-fix attempts when verification fails.
- If verification still fails after the third attempt, stop and ask the user how to proceed. Do not commit failing work.

## Commit Rules

All commits are created directly on the current branch.

Commit messages follow the feature-scoped template with mode state:

```text
feat <feat_name> features <feature_number> phase <NNN> [state] <message>
```

- `default` mode: one commit after verification passes, no `[state]` flag.
- `tdd` mode: `[red]`, `[green]`, `[red-fix]`, `[green-fix]` commits preserved in history.
- `scaffolding` phases in `tdd` mode where a failing test cannot be written first: green-only commit with a `[scaffold]` note in the message.

Feature metadata resolution:

- Native plan: feature name and number derived from the plan path.
- Free-form input: feature name from the user's input, feature number `001`.

Include the source plan's acceptance-criteria checkbox updates in the phase commit when a source plan exists. Never include unrelated changes.

See [COMMIT-CONVENTIONS.md](./references/COMMIT-CONVENTIONS.md).

## Completion

After verification passes and the phase commit is created:

1. If a source `plan.md` exists, check the completed phase's acceptance criteria in it and commit with the phase.
2. Stop with a concise summary of what was implemented and verified, unless the original user request explicitly asked to continue.
3. If continuing, select the next first unfinished phase and repeat the same cycle.

## Workflow Diagram

See [WORKFLOW.md](./references/WORKFLOW.md).

## References

- [MODE.md](./references/MODE.md) — mode semantics and resolution.
- [COMMIT-CONVENTIONS.md](./references/COMMIT-CONVENTIONS.md) — commit message templates.
- [WORKFLOW.md](./references/WORKFLOW.md) — the phase implementation cycle.
