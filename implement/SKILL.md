---
name: implement
version: 1.0.0
description: |
  Implement every unfinished phase from a canonical plan directly in the current checkout with no worktrees. When no plan exists, the host uses the available `generate-plan` skill as a separate pre-step. The host implements, verifies with normal project commands, and the bundled `impl-reviewer` agent writes an incremental persistent report and gates each phase before commit. Use when the user asks to implement or continue a plan or gives an implementation request without a plan. Resolve mode once by default, process phases sequentially, and update the source plan after each approved phase.
---

# Implement

This skill implements every unfinished plan phase directly, one phase at a time and in sequence. The host performs all codebase discovery, architecture reading, third-party documentation research, implementation, testing, and plan updates itself. The bundled `impl-reviewer` agent independently verifies each phase in the project root checkout before its commit and writes the persistent review report; no implementation work is delegated.

The project root is resolved from `_xzy-ai/project-root.md` at the workspace root (current working directory): the file holds exactly one `<cwd>`-relative path (forward slashes, no leading `/`, no `.` or `..` segments) that resolves to a directory inside `<cwd>`, and the codebase under development lives at `<cwd>/<entry>`. All implementation, verification, and commits happen inside the project root. The canonical plan and reviewer reports under workspace `_xzy-ai/` are managed workflow artifacts; other files outside the project root (for example `references/`) are read-only reference material and are never modified by this skill or its reviewer.

This is the direct, lightweight counterpart to `dispatch-for-implementation`:

| Aspect | `implement` | `dispatch-for-implementation` |
|---|---|---|
| Who implements | The host, directly | A bundled worker agent |
| Isolation | Current checkout, no worktrees | Git worktree per phase |
| Bundled agents | `impl-reviewer` | Worker + ACS, security, quality reviewers |
| Review gates | `impl-reviewer` acceptance gate (before commit) | ACS + security/quality reviewers |
| Artifacts | Workspace-local reviewer reports and canonical plan completion updates; no dispatch artifacts | assignment.md, reports, progress |
| Modes | `default` and `tdd` | `default` and `tdd` |

## Trigger Boundary

Run this skill when the user explicitly asks to implement, execute, or continue implementation for:

- A canonical `generate-plan` `plan.md` at `_xzy-ai/sprints/<backlog>/plans/features/<NNN>/plan.md`.
- A named phase from an implementation plan.
- An implementation request with no plan; use the available `generate-plan` skill as a separate pre-step before implementation.

Do not run this skill for:

- Creating specs, plans, tickets, architecture, or design documents as the primary request (a no-plan implementation request may use `generate-plan` as its prerequisite).
- Discussion-only requests.
- Implementation that should be delegated to agent orchestration with worktree isolation and worker/reviewer orchestration — use `dispatch-for-implementation` for that.

## Core Invariants

1. The host implements directly. During implementation, the only bundled reviewer is `impl-reviewer`; a no-plan request may invoke the separate `generate-plan` skill before implementation, but no implementation work is delegated.
2. First resolve the project root from `<cwd>/_xzy-ai/project-root.md`. Work in the project root checkout. No git worktrees are created.
3. The only review gate is `impl-reviewer`, run before the phase commit, in addition to the host's own verification with normal project commands.
4. The `impl-reviewer` gate runs before every phase commit. The host commits only after an explicit persisted `APPROVED` verdict; on `REJECTED` the host fixes every remaining finding, reruns normal verification, and resumes the reviewer until approval.
5. Work on only one phase at a time incrementally. Process all unfinished phases sequentially in one invocation; finish and approve, commit, and mark each phase complete before starting the next.
6. Skip any phase whose acceptance criteria are all checked in a native plan.
7. Use phase terminology. Do not call phases work units or tickets.
8. Write no dispatch artifacts, assignment files, or host progress files. The `impl-reviewer` writes its canonical incremental report under workspace `_xzy-ai`; the completed inline result contains only its report path and verdict.
9. Escalate to the user for mode choice, uncommitted changes, plan selection/context gaps, unavailable `generate-plan`, missing verification commands, reviewer interruption/report-write failures, plan-update failures, or unresolved verification failures.
10. Never commit unrelated changes. The phase commit contains only phase work.
11. Do not perform external research when internal project conventions suffice.

## Mode Resolution

Ask the user to choose `default` or `tdd` once at the start of the plan run when no explicit mode is supplied. No persistent mode file is read or written; `_xzy-ai/dispatch-mode.md` and any implement-specific default are intentionally ignored. An explicit user request may override the mode for a particular phase.

- `default`: implement each phase directly, verify it, review it, and commit it after approval.
- `tdd`: follow Red → Green → Refactor with mode-labeled commits for each phase, then review before phase completion.

The initial mode applies to every phase unless a phase-specific override is explicit.

See [MODE.md](./references/MODE.md).

## Input Handling

### Native `generate-plan` plan.md

A native plan has this path shape relative to the workspace root:

```text
_xzy-ai/sprints/<backlog>/plans/features/<NNN>/plan.md
```

The plan lives under `_xzy-ai/` at the workspace root, while the codebase lives at the resolved project root. Read the plan from the workspace root, but implement only inside the project root. After a phase commit, update only that plan's completion checkboxes/status and allow `impl-reviewer` to write its designated reports under `_xzy-ai`; do not modify other workspace artifacts.

Handling rules:

1. Find candidate plans. If exactly one plan exists in the workspace, use it. If multiple candidate plans exist and the user named none, ask which feature/plan to implement.
2. Extract the backlog name, feature number, and feature name from the path.
3. Extract architectural decisions for background.
4. Extract each `## Phase N` section as one phase.
5. Select the first phase whose acceptance criteria are not all checked, unless the user explicitly named a phase.
6. If the source `plan.md` is specified but the selected phase's contract and expected output are unclear or insufficiently defined — for example, "What to build" or the acceptance criteria are missing, vague, or ambiguous in ways that affect behavior — hand off to the `discussion` skill and resolve the phase contract before implementing. Do not guess or proceed with an ill-defined phase.
7. If all phases are complete, stop with a concise completion summary and commit nothing.

### No-plan implementation input

For an implementation request without a canonical plan:

1. Use the available `generate-plan` skill as a separate pre-step, using the request and supplied context to create and verify the canonical plan.
2. If `generate-plan` is unavailable, pause and ask the user to make it available or provide a canonical plan.
3. If required backlog, feature identity/title, outcome, scope, actors, dependencies, or Acceptance Criteria context is missing or ambiguous, use the existing context/discussion gate before generating the plan; do not guess.
4. After the plan is written and verified, continue through its unfinished phases using the native plan workflow. Do not create an ephemeral direct phase contract.

## Preconditions

Before implementing:

1. Resolve the project root from `<cwd>/_xzy-ai/project-root.md`: the file holds exactly one `<cwd>`-relative entry (forward slashes, no leading `/`, no `.` or `..` segments) resolving to a directory inside `<cwd>`. If it is missing, empty, or malformed, ask the user to correct it. Do not guess.
2. Verify the working tree inside the project root. If uncommitted changes exist, ask the user whether to commit them, stash them, or stop. The project-root working tree must be clean before implementation begins. Pre-existing changes under the workspace-root `_xzy-ai/` are planning artifacts and are excluded from this requirement.
3. Confirm the plan-run mode once when not explicitly supplied (`default` or `tdd`); apply it to all phases unless a phase-specific override is explicit.
4. Read the phase content: user stories covered, what to build, and acceptance criteria.
5. Read `<workspace_root>/_xzy-ai/architecture.md` when present.
6. Perform codebase discovery directly inside the project root: existing patterns, tests, commands, and conventions. The host owns this — it is not a violation of any restriction.
7. If relevant internal guidance is unavailable, research third-party packages with official documentation and verify latest stable versions before use.

Treat files outside the project root as read-only reference material except for the canonical plan completion update and the reviewer reports explicitly managed under workspace `_xzy-ai/`; never create, modify, move, rename, or delete other files there. Project code paths cited in the plan are workspace-root-relative pointers into the project root; map them when implementing.

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

- Make up to three self-fix attempts when normal verification fails.
- If verification still fails after the third attempt, stop and ask the user how to proceed. Do not commit failing work.
- If a reviewer invocation is interrupted, resume the same reviewer agent and report up to three times; then pause and ask the user.
- Retry each report write/read-back operation up to three times without sleeping; pause on persistent report-write failure.
- Retry each post-commit plan update and read-back up to three times; do not advance if it remains unsuccessful.

## Review Gate

For each phase, run the bundled `impl-reviewer` after host verification and before committing the phase. This applies in both `default` and `tdd` modes; in `tdd`, run it after Red → Green → Refactor and before phase completion.

Delegate to `impl-reviewer` with:

- `baseline_sha` — the HEAD SHA recorded before the current phase began.
- `project_root` — the absolute project codebase root resolved from `_xzy-ai/project-root.md`.
- `plan_path` — the absolute canonical `plan.md` path. Every implementation request has one because no-plan requests use `generate-plan` first.
- `backlog` and `feature` — the plan identity.
- `phase` — the current phase number.
- `mode` — `default` or `tdd`, including any explicit phase override.
- `previous_progress` — previous host progress text or `None` for the first attempt.
- `current_progress_status` — current host progress/status text.

Do not pass `phase_contract` or `report_path`. The reviewer validates the handoff, derives its own workspace-local report path, and writes a persistent incremental report. The report is not part of the project-root commit. A completed reviewer returns only:

```text
report_path: <absolute report path>
verdict: APPROVED | REJECTED
```

If the reviewer returns `REJECTED`, the host fixes every remaining finding, reruns normal verification, and resumes the same reviewer agent ID for a fresh review attempt. The fresh attempt receives the next report number; reviewer Minor/Trivial direct fixes remain allowed. Repeat until the reviewer explicitly returns `verdict: APPROVED`.

If the reviewer is interrupted, resume the same agent ID and same report up to three times. If it still stops, pause and ask the user. If report persistence fails after the reviewer's three write/read-back retries, pause for the user; never approve inline without the persistent report.

The review retry loop is separate from the three-attempt normal-verification retry budget. Reviewer direct fixes remain in the working tree and are included in the approved phase commit.

## Commit Rules

All commits are created directly on the current branch of the project-root repository.

Commit messages follow the feature-scoped template with mode state:

```text
feat <feat_name> features <feature_number> phase <NNN> [state] <message>
```

- `default` mode: after reviewer `APPROVED`, commit the phase once with no `[state]` flag.
- `tdd` mode: `[red]`, `[green]`, `[red-fix]`, and `[green-fix]` commits are preserved; commit any approved remaining reviewer direct fixes before phase completion.
- `scaffolding` phases in `tdd` mode where a failing test cannot be written first: green-only commit with a `[scaffold]` note in the message.

Feature metadata is always derived from the canonical plan path. There is no direct free-form commit fallback.

Do not include plan acceptance-criteria checkbox updates or workspace-local reviewer reports in the project phase commit. After the approved code commit, update the canonical plan's completion state as a separate verified workspace step. Never include unrelated changes.

Reviewer direct fixes are included in the phase commit; the phase commit happens only after an explicit persisted `APPROVED` verdict.

See [COMMIT-CONVENTIONS.md](./references/COMMIT-CONVENTIONS.md).

## Completion

After each phase's reviewer returns `APPROVED`:

1. Commit the approved phase code/TDD changes.
2. Update the canonical plan's completed-phase acceptance criteria/status separately and verify the write. Retry this update up to three times; if it remains unsuccessful, preserve the code commit, do not advance, and ask the user.
3. Select the next unfinished phase and repeat the implementation, verification, review, commit, and plan-update cycle.
4. When every phase is approved, committed, and marked complete, stop with a concise completion summary.

## Workflow Diagram

See [WORKFLOW.md](./references/WORKFLOW.md).

## References

- [MODE.md](./references/MODE.md) — mode semantics and resolution.
- [COMMIT-CONVENTIONS.md](./references/COMMIT-CONVENTIONS.md) — commit message templates.
- [WORKFLOW.md](./references/WORKFLOW.md) — the phase implementation cycle.

## Agents

| Agent | Role | Primary output |
|---|---|---|
| `impl-reviewer` | Acceptance-criteria gate; independently verifies each host-implemented phase and writes its persistent incremental report before the phase commit. | Report path and `APPROVED`/`REJECTED` verdict |
