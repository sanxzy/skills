---
name: implement
version: 1.0.0
description: |
  Implement one plan phase directly in the current checkout with no worktrees. The host implements, verifies with normal project commands, and the bundled `impl-reviewer` agent runs an acceptance-criteria gate before the phase commit. Use when the user asks to implement or continue a phase from a `generate-plan` `plan.md`, or provides free-form implementation input for direct host-driven implementation. Resolves `default` or `tdd` mode with the user, requires a clean working tree, implements the selected phase, verifies with normal project commands, commits per mode convention, and checks the source plan's acceptance criteria.
---

# Implement

This skill implements exactly one phase directly. The host performs all codebase discovery, architecture reading, third-party documentation research, implementation, testing, and plan updates itself. The bundled `impl-reviewer` agent verifies acceptance criteria in the project root checkout before the phase commit; nothing else is delegated.

The project root is resolved from `_xzy-ai/project-root.md` at the workspace root (current working directory): the file holds exactly one `<cwd>`-relative path (forward slashes, no leading `/`, no `.` or `..` segments) that resolves to a directory inside `<cwd>`, and the codebase under development lives at `<cwd>/<entry>`. All implementation, verification, and commits happen inside the project root. Files outside the project root (for example `references/`) are read-only reference material and are never modified by this skill or its reviewer.

This is the direct, lightweight counterpart to `dispatch-for-implementation`:

| Aspect | `implement` | `dispatch-for-implementation` |
|---|---|---|
| Who implements | The host, directly | A bundled worker agent |
| Isolation | Current checkout, no worktrees | Git worktree per phase |
| Bundled agents | `impl-reviewer` | Worker + ACS, security, quality reviewers |
| Review gates | `impl-reviewer` acceptance gate (before commit) | ACS + security/quality reviewers |
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
- Implementation that should be delegated to agent orchestration with worktree isolation and worker/reviewer orchestration — use `dispatch-for-implementation` for that.

## Core Invariants

1. The host implements directly. The only bundled agent is `impl-reviewer`, which runs the acceptance gate; no other subagents or delegation.
2. First resolve the project root from `<cwd>/_xzy-ai/project-root.md`. Work in the project root checkout. No git worktrees are created.
3. The only review gate is `impl-reviewer`, run before the phase commit, in addition to the host's own verification with normal project commands.
4. The `impl-reviewer` gate runs before every phase commit for both native `plan.md` and free-form phases. The host commits only after an `APPROVED` verdict; on `REJECTED` the host may fix findings and rerun the reviewer.
5. One phase is the atomic unit. Execute exactly one phase per invocation.
6. Skip any phase whose acceptance criteria are all checked in a native plan.
7. Use phase terminology. Do not call phases work units or tickets.
8. Write no dispatch artifacts: no assignment.md, no reports, no progress.md. The `impl-reviewer` verdict is returned inline, never written to a file.
9. Escalate to the user only for mode choice, uncommitted changes, plan selection, missing verification commands, or unresolved verification failures.
10. Never commit unrelated changes. The phase commit contains only phase work.
11. Do not perform external research when internal project conventions suffice.

## Mode Resolution

Ask the user to choose `default` or `tdd` when no explicit mode is supplied — every invocation, not just the first. No persistent mode file is read or written; `_xzy-ai/dispatch-mode.md` and any implement-specific default are intentionally ignored.

- `default`: implement directly, run verification, commit once after validation passes.
- `tdd`: follow Red → Green → Refactor with mode-labeled commits.

The selected mode applies only to the active phase.

See [MODE.md](./references/MODE.md).

## Input Handling

### Native `generate-plan` plan.md

A native plan has this path shape relative to the workspace root:

```text
_xzy-ai/sprints/<backlog>/plans/features/<NNN>/plan.md
```

The plan lives under `_xzy-ai/` at the workspace root, while the codebase lives at the resolved project root. Read the plan from the workspace root, but implement only inside the project root; never modify files under `_xzy-ai/` beyond the plan's acceptance-criteria checkboxes.

Handling rules:

1. Find candidate plans. If exactly one plan exists in the workspace, use it. If multiple candidate plans exist and the user named none, ask which feature/plan to implement.
2. Extract the backlog name, feature number, and feature name from the path.
3. Extract architectural decisions for background.
4. Extract each `## Phase N` section as one phase.
5. Select the first phase whose acceptance criteria are not all checked, unless the user explicitly named a phase.
6. If the source `plan.md` is specified but the selected phase's contract and expected output are unclear or insufficiently defined — for example, "What to build" or the acceptance criteria are missing, vague, or ambiguous in ways that affect behavior — hand off to the `discussion` skill and resolve the phase contract before implementing. Do not guess or proceed with an ill-defined phase.
7. If all phases are complete, stop with a concise completion summary and commit nothing.

### Free-form input

For non-plan input:

1. Treat the input as exactly one implementation phase. Multi-phase work belongs in a plan.
2. Do not persist any normalized plan or resume artifact.
3. If the input is ambiguous in ways that affect behavior, load `discussion` and resolve ambiguity before implementing.

## Preconditions

Before implementing:

1. Resolve the project root from `<cwd>/_xzy-ai/project-root.md`: the file holds exactly one `<cwd>`-relative entry (forward slashes, no leading `/`, no `.` or `..` segments) resolving to a directory inside `<cwd>`. If it is missing, empty, or malformed, ask the user to correct it. Do not guess.
2. Verify the working tree inside the project root. If uncommitted changes exist, ask the user whether to commit them, stash them, or stop. The project-root working tree must be clean before implementation begins. Pre-existing changes under the workspace-root `_xzy-ai/` are planning artifacts and are excluded from this requirement.
3. Confirm the mode when not explicitly supplied (`default` or `tdd`).
4. Read the phase content: user stories covered, what to build, and acceptance criteria.
5. Read `<workspace_root>/_xzy-ai/architecture.md` when present.
6. Perform codebase discovery directly inside the project root: existing patterns, tests, commands, and conventions. The host owns this — it is not a violation of any restriction.
7. If relevant internal guidance is unavailable, research third-party packages with official documentation and verify latest stable versions before use.

Treat every file outside the project root (including `references/`) as read-only reference material; never create, modify, move, rename, or delete files there. Project code paths cited in the plan are workspace-root-relative pointers into the project root; map them when implementing.

## Implementation

1. Classify the phase from its acceptance criteria:
   - `functional`: any criterion describes observable behavior, validation, state, failure handling, integration, user-visible behavior, or business logic.
   - `scaffolding`: criteria describe only file structure, boilerplate, placeholders, configuration shape, or non-functional skeletons.
2. Implement the phase directly in the project root checkout.
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

## Review Gate

Run the bundled `impl-reviewer` agent after verification passes and before any phase commit — in both `default` and `tdd` modes (in `tdd`, after Red → Green → Refactor, at the pre-finalization gate).

Delegate to `impl-reviewer` with:

- `baseline_sha` — the HEAD SHA recorded before implementation began.
- `project_root` — the absolute project codebase root resolved from `_xzy-ai/project-root.md`.
- The source `plan.md` path when one exists, otherwise the phase contract (user stories, what to build, acceptance criteria).
- Phase metadata: backlog, feature number, phase number.
- The mode (`default` or `tdd`).

The reviewer inspects `git diff <baseline_sha>...HEAD`, the uncommitted `git diff`, and `git log --oneline <baseline_sha>..HEAD` inside the project root, plus full relevant project state and project verification commands. It may directly fix only Minor/Trivial findings. The verdict is returned inline — no artifacts are written.

On `APPROVED`, proceed to the commit rules. On `REJECTED`, the host fixes Blocker/Critical/Major findings, re-runs verification, and reruns the reviewer; repeat until approved or the host is blocked and must ask the user how to proceed.

Note: the review rerun loop is separate from the three-attempt verification retry budget in "Retry budget" — do not conflate them.

Reviewer direct fixes (Minor/Trivial) remain in the working tree and are included in the phase commit.

## Commit Rules

All commits are created directly on the current branch of the project-root repository.

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

Reviewer direct fixes are included in the phase commit; the phase commit happens only after an `APPROVED` verdict.

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

## Agents

| Agent | Role | Primary output |
|---|---|---|
| `impl-reviewer` | Acceptance-criteria gate; verifies the host-implemented phase in the project root checkout before the phase commit. | Inline `APPROVED`/`REJECTED` verdict (no files written) |
