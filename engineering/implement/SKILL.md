---
name: implement
version: 1.0.0
description: |
  Implement every unfinished plan phase or ticket directly in the current checkout with no worktrees. The host consumes either a canonical `generate-plan` plan or a `ticket` ticket set, verifies with normal project commands, and the bundled `impl-reviewer` agent writes an incremental persistent report and gates each implementation unit before commit. Use when the user asks to implement or continue a plan or ticket set, or gives an implementation request without a source artifact. Resolve purpose once, resolve a production implementation mode when applicable, process units sequentially, and update the source artifact after each approved unit.
---

# Implement

This skill implements every unfinished plan phase or ticket directly, one implementation unit at a time and in dependency order. The host performs all codebase discovery, architecture reading, third-party documentation research, implementation, testing, and source-artifact completion updates itself. The bundled `impl-reviewer` agent independently verifies each unit in the project root checkout before its commit and writes the persistent review report; no implementation work is delegated. In plan mode the unit is a phase; in ticket mode the unit is a ticket.

## Purpose and implementation modes

Resolve one **purpose** before implementation begins:

- `production` — build the real product behavior, system boundaries, persistence,
  integrations, validation, and operational guarantees required by the source
  contract.
- `prototype` — build an **E2E interactive prototype** to lock the core
  product flow and interaction model before production investment. Cover the
  selected journey from entry point through the user's value/outcome, not just
  one screen, component, or isolated feature. The result must be runnable and
  feel real along that journey, but may use fake data, hardcoded or in-memory
  state, fake loading/error states, scripted responses, and simulated
  interactions. It must not imply that a backend, persistence, authentication,
  external integration, renderer, or production-grade reliability exists when
  it does not.

`production` has one implementation mode per run: `default` or `tdd`.
`prototype` has no production implementation-mode choice; follow the prototype
workflow and do not add TDD ceremony merely because the prototype is
interactive. Never let prototype shortcuts leak into a `production` run.

The project root is resolved from `_xzy-ai/project-root.md` at the workspace root (current working directory): the file holds exactly one `<cwd>`-relative path (forward slashes, no leading `/`, no `.` or `..` segments) that resolves to a directory inside `<cwd>`, and the codebase under development lives at `<cwd>/<entry>`. All implementation, verification, and commits happen inside the project root. The canonical plan or ticket index, their completion updates, and reviewer reports under workspace `_xzy-ai/` are managed workflow artifacts; other files outside the project root (for example `references/`) are read-only reference material and are never modified by this skill or its reviewer.

This is the direct, lightweight counterpart to `squad`:

| Aspect | `implement` | `squad` |
|---|---|---|
| Who implements | The host, directly | Bundled worker agents |
| Isolation | Current checkout, no worktrees | Git worktree per work unit |
| Bundled agents | `impl-reviewer` | Worker, reviewer, QA, and analysis roles |
| Review gates | `impl-reviewer` acceptance gate (before commit) | Worker/reviewer gates plus run-level QA |
| Artifacts | Workspace-local reviewer reports and canonical plan/ticket completion updates; no dispatch artifacts | Durable orchestration state, reports, evidence, and projections |
| Purpose | `production` or `prototype` | `production` or `prototype` |
| Production implementation mode | `default` or `tdd` | `default` or `tdd` |

## Trigger Boundary

Run this skill when the user explicitly asks to implement, execute, or continue implementation for:

- A canonical `generate-plan` `plan.md` at `_xzy-ai/sprints/<backlog>/plans/features/<NNN>/plan.md`.
- A canonical `ticket` `tickets.md` at `_xzy-ai/sprints/<backlog>/tickets.md`.
- A named plan phase or ticket from one of those canonical source artifacts.
- An implementation request with no source artifact; use the available `generate-plan` or `ticket` skill as a separate pre-step according to the user's source context before implementation.

Do not run this skill for:

- Creating specs, plans, tickets, architecture, or design documents as the primary request (a source-less implementation request may use `generate-plan` or `ticket` as its prerequisite).
- Discussion-only requests.
- Implementation that should be delegated to agent orchestration with worktree isolation and worker/reviewer orchestration — use `squad` for that.

## Core Invariants

1. The host implements directly. During implementation, the only bundled reviewer is `impl-reviewer`; a source-less request may invoke the separate `generate-plan` or `ticket` skill before implementation, but no implementation work is delegated.
2. First resolve the project root from `<cwd>/_xzy-ai/project-root.md`. Work in the project root checkout. No git worktrees are created.
3. The only review gate is `impl-reviewer`, run before each implementation-unit commit, in addition to the host's own verification with normal project commands.
4. The `impl-reviewer` gate runs before every unit commit. The host commits only after an explicit persisted `APPROVED` verdict; on `REJECTED` the host fixes every remaining finding, reruns normal verification, and resumes the reviewer until approval.
5. Work on only one implementation unit at a time. In plan mode process unfinished phases sequentially; in ticket mode process executable tickets in dependency order. Finish, approve, commit, and mark each unit complete before starting the next.
6. Skip any plan phase or ticket whose acceptance criteria all use the
   selected purpose marker (`[x]` for `production`, `[P]` for `prototype`).
   Never bypass an unfinished ticket blocker.
7. Use source-specific terminology: call plan units phases and ticket-set units tickets. Use `implementation unit` only when describing both modes.
8. Write no dispatch artifacts, assignment files, or host progress files. The `impl-reviewer` writes its canonical incremental report under workspace `_xzy-ai`; the completed inline result contains only its report path and verdict.
9. Completion markers are purpose-specific: production completion is recorded with `[x]`; prototype completion is recorded with `[P]`. `[P]` is not production completion, and `[x]` is not a substitute for a prototype checkpoint.
10. Never mark a source criterion complete until the selected purpose's behavior is implemented and verified at the strongest usable seam.
11. Escalate to the user for purpose or production-mode choice, uncommitted changes, plan/ticket source selection or context gaps, unavailable source-generation skill, missing verification commands, reviewer interruption/report-write failures, source-artifact update failures, or unresolved verification failures.
12. Never commit unrelated changes. The implementation-unit commit contains only that unit's project work.
13. Do not perform external research when internal project conventions suffice.

## Purpose and mode resolution

Ask the user to choose `production` or `prototype` once at the start of the
implementation run when no explicit purpose is supplied. No persistent purpose
or mode file is read or written; `_xzy-ai/implement-mode.md` and
`_xzy-ai/dispatch-mode.md` are intentionally ignored.

- In `production`, ask once for `default` or `tdd` when no explicit
  implementation mode is supplied. The selected mode applies to every phase or
  ticket unless a unit-specific override is explicit.
- In `prototype`, do not ask for `default`/`tdd`; use the interactive-prototype
  workflow. A prototype unit may use focused tests, browser/manual journeys,
  screenshots, or another falsifiable seam, but it is not required to create
  production infrastructure or persistence.

An explicit purpose or production implementation mode takes precedence over a
question. Purpose and implementation mode must remain stable for the run; do
not silently change either after implementation begins.

See [MODE.md](./references/MODE.md).

## Input Handling

### Native `generate-plan` plan.md

A native plan has this path shape relative to the workspace root:

```text
_xzy-ai/sprints/<backlog>/plans/features/<NNN>/plan.md
```

The plan lives under `_xzy-ai/` at the workspace root, while the codebase lives at the resolved project root. Read the plan from the workspace root, but implement only inside the project root. After a phase commit, update only that plan's completion checkboxes/status and allow `impl-reviewer` to write its designated reports under `_xzy-ai`; do not modify other workspace artifacts.

Handling rules:

1. Find candidate plans. If exactly one plan exists and no ticket index competes in the workspace, use it. If multiple plans exist, or both a plan and ticket index exist and the user named none, ask which source to implement.
2. Extract the backlog name, feature number, and feature name from the path.
3. Extract architectural decisions for background.
4. Extract each `## Phase N` section as one phase.
5. Select the first phase whose acceptance criteria do not all use the
   purpose's completion marker (`[x]` for `production`, `[P]` for
   `prototype`), unless the user explicitly named a phase.
6. If the source `plan.md` is specified but the selected phase's contract and expected output are unclear or insufficiently defined — for example, `What to build` or the acceptance criteria are missing, vague, or ambiguous in ways that affect behavior — hand off to the `discussion` skill and resolve the phase contract before implementing. Do not guess or proceed with an ill-defined phase.
7. If all phases are complete for the selected purpose marker, stop with a
   concise completion summary and commit nothing.

### Native `ticket` tickets.md

A native ticket set has this path shape relative to the workspace root:

```text
_xzy-ai/sprints/<backlog>/tickets.md
```

The index and per-ticket files live under `_xzy-ai/` at the workspace root, while the codebase lives at the resolved project root. Read the index and selected ticket from the workspace root, but implement only inside the project root. After a ticket commit, update only that ticket's acceptance-criteria checkboxes in its canonical ticket file; do not modify the proposal, ticket index structure, dependency edges, or other ticket files except when the user explicitly asks for a source-artifact correction.

Handling rules:

1. Find candidate `tickets.md` files. If exactly one exists and no plan competes in the workspace, use it. If multiple plans/ticket sets exist, or both a plan and ticket index exist and the user named none, ask which source to implement.
2. If the user provides a per-ticket file, resolve its parent `tickets.md` and use the index as the source of dependency order.
3. Extract the backlog name from the canonical path and validate every ticket link, ID, `Blocked by`, and acceptance-criteria list.
4. Select the explicitly named `TNNN` when supplied; otherwise select the
   first unfinished ticket in index order whose every ticket blocker has all
   criteria completed with the selected purpose marker (`[x]` for `production`,
   `[P]` for `prototype`) and whose external prerequisites are explicitly
   satisfied.
5. Never bypass an unfinished blocker or assume an external prerequisite is satisfied. If unfinished tickets exist but none is executable, stop and report the blocking ticket IDs or external prerequisites instead of guessing a sequence.
6. If the selected ticket's `What to build`, scope boundary, acceptance criteria, traceability, or recovery behavior is missing, vague, or ambiguous in a way that affects implementation, hand off to `discussion` and resolve the ticket contract before implementing.
7. If all current ticket acceptance criteria use the selected purpose marker,
   stop with a concise completion summary and commit nothing.
8. Ticket mode may contain many small tickets. Do not merge tickets into a larger phase for convenience; complete and review one ticket at a time.

### Source-less implementation input

For an implementation request without a canonical plan or ticket set:

1. If the request is explicitly based on a proposal, use the available `ticket` skill as a separate pre-step to create and verify `tickets.md` and its ticket files.
2. Otherwise use the available `generate-plan` skill as a separate pre-step to create and verify the canonical plan.
3. If the required source-generation skill is unavailable, pause and ask the user to make it available or provide a canonical source artifact.
4. If required source identity, outcome, scope, actors, dependencies, or acceptance-criteria context is missing or ambiguous, use the existing context/discussion gate before generating the source; do not guess.
5. After the source artifact is written and verified, continue through its unfinished phases or executable tickets using the corresponding native workflow. Do not create an ephemeral direct implementation contract.

## Preconditions

Before implementing:

1. Resolve the project root from `<cwd>/_xzy-ai/project-root.md`: the file holds exactly one `<cwd>`-relative entry (forward slashes, no leading `/`, no `.` or `..` segments) resolving to a directory inside `<cwd>`. If it is missing, empty, or malformed, ask the user to correct it. Do not guess.
2. Verify the working tree inside the project root. If uncommitted changes exist, ask the user whether to commit them, stash them, or stop. The project-root working tree must be clean before implementation begins. Pre-existing changes under the workspace-root `_xzy-ai/` are planning artifacts and are excluded from this requirement.
3. Resolve the purpose once. If the purpose is `production`, confirm the
   implementation mode once when not explicitly supplied (`default` or `tdd`);
   prototype runs do not resolve a production implementation mode. Apply the
   selected purpose and mode to all phases or tickets unless a unit-specific
   override is explicit.
4. Read the active unit content: for plan mode, user stories covered, `What to build`, and acceptance criteria; for ticket mode, `What to build`, proposal traceability, scope boundary, `Blocked by`, and acceptance criteria.
5. Read and follow rules from `<workspace_root>/_xzy-ai/architecture.md` when present.
6. Perform codebase discovery directly inside the project root: existing patterns, tests, commands, and conventions. The host owns this — it is not a violation of any restriction.
7. If sufficiently relevant internal guidance is unavailable, perform external research:
   - Use Exa Code Context Search to find UI implementation patterns and component examples.
   - Use Context7 to retrieve framework and component library documentation.
   - If Exa returns URLs, follow those URLs using web fetching instead of repeatedly querying Exa.
8. If third-party libraries are required, verify the latest stable version using the appropriate package manager before implementation:
   - `npm view` or `pnpm view` for JavaScript/TypeScript.
   - `cargo search` for Rust.
   - The equivalent package management commands for other ecosystems.
9. If the available documentation is still insufficient, inspect the installed package source code directly, for example `node_modules` or the component library source, to understand the implementation details before writing code.

Treat files outside the project root as read-only reference material except for the canonical plan phase update, selected ticket acceptance-criteria update, and reviewer reports explicitly managed under workspace `_xzy-ai/`; never create, modify, move, rename, or delete other files there. Project code paths cited in the plan or ticket are workspace-root-relative pointers into the project root; map them when implementing.

## Test file naming

For project-owned tests, choose a semantic filename that describes the subject and behavior under test, using the repository's existing language and framework convention. Prefer a focused pattern such as `<subject>-<behavior>.test.<ext>` (or the equivalent convention, such as Python's `test_<subject>_<behavior>.py`). Existing `pi-work` examples include `transport-structured.test.ts`, `session-runtime-redaction.test.ts`, and `read-image-progressive-state.test.ts`.

Do not name a project-owned test file after workflow metadata or a numeric implementation unit. Names such as `phase3-events.test.ts`, `phase13-review010.test.ts`, `phaseX.test.ts`, `review010.test.ts`, or `attempt-001.test.ts` are not semantic. Do not encode a phase, feature, ticket ID, review number, TDD state, or attempt number in the filename. Instead, name the file for the domain behavior it verifies, and extend an existing focused test file when that behavior already has one.

Before creating or renaming a test file:

1. Inspect neighboring tests and the production module under test.
2. Identify the smallest stable subject/behavior phrase that distinguishes the file from nearby tests.
3. Preserve the repository's suffix and separator convention while using that semantic phrase.

Reviewer-isolated verification files are a separate audit artifact: they may use the required `attempt-<NN>-<semantic-slug>.<ext>` form, but their slug must still describe the behavior being verified rather than only repeating phase, ticket, review, or attempt metadata.

## Implementation

1. Classify the implementation unit from its acceptance criteria:
   - `functional`: any criterion describes observable behavior, validation, state, failure handling, integration, user-visible behavior, or business logic.
   - `scaffolding`: criteria describe only file structure, boilerplate, placeholders, configuration shape, or non-functional skeletons.
2. For `prototype` purpose, define the core E2E journey from entry point to
   user outcome and explicitly list every fake boundary (data, state, loading,
   error, side effect, and integration). Implement the smallest clickable
   experience that proves the whole journey; do not build real production
   systems behind it.
3. For `production` purpose, preserve the selected `default`/`tdd` contract and
   implement the real behavior and boundaries required by the source.
4. Implement the unit directly in the project root checkout.
5. Testing rules:
   - Functional production units must include behavior-focused tests or a clear project-appropriate verification path. Prototype units must include a falsifiable interactive verification path (for example, a browser/manual E2E journey, screenshot evidence, or focused test) for each supported core journey.
   - Tests must exercise externally observable behavior at the highest usable seam. Derive expected values and fixtures independently from the unit contract; do not copy production logic into the test oracle.
   - When the unit contract promises a stable public shape or type, apply type-preserving structural invariance: vary values while keeping their type/category constant, assert that the public shape and types remain stable, and allow values to vary unless exact values are part of the contract. Do not confuse structural invariance with exact-value equality or object identity.
   - Do not force dynamic or non-deterministic values to compare identically across executions or fixtures, including but not limited to IDs, timestamps, random tokens/nonces/salts, salted or randomized hashes, and randomized encryption/ciphertext. Assert contract-level properties instead, such as type, shape, format, validity, relationships, ranges, decryptability, or promised uniqueness. Exact equality is allowed only when deterministic equality is explicitly contracted or the test controls the source of variability.
   - Tautological testing is prohibited. Do not write or retain tests that duplicate the implementation's algorithm or control flow, compare a value with itself or the same implementation, assert only private/internal state, or verify mock calls solely because the implementation makes them. Interaction assertions are valid only when the interaction is part of the observable contract.
   - Replace or remove an existing tautological test before treating it as verification. A functional verification path must be able to fail when the promised behavior is wrong.
   - Scaffolding units do not require tests but must pass relevant syntax/build/config checks when available.
6. In `production` `tdd` mode for functional units, follow Red → Green → Refactor. The Red test must fail for a missing or incorrect behavior, not merely encode the intended implementation; where applicable, it must cover type-preserving structural invariance rather than one hardcoded value. Refactor is part of the cycle but not a commit-message flag. Prototype purpose does not enter this TDD mode.
7. Verify with the project's normal commands. Determine the command set from project configuration, README, AGENTS.md, or package manifests.

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
- Retry each post-commit plan or ticket completion update and read-back up to three times; do not advance if it remains unsuccessful.

## Review Gate

For each implementation unit, run the bundled `impl-reviewer` after host verification and before committing the unit. This applies to both purposes. In production `tdd`, run it after Red → Green → Refactor; in prototype, run it after the complete E2E journey has been exercised and the fake boundaries have been documented.

Delegate to `impl-reviewer` with:

- `baseline_sha` — the HEAD SHA recorded before the current unit began.
- `project_root` — the absolute project codebase root resolved from `_xzy-ai/project-root.md`.
- `source_kind` — `plan` or `tickets`.
- `source_path` — the absolute canonical `plan.md` or `tickets.md` path.
- `backlog` — the backlog identity derived from the source path.
- `feature` — the plan feature number in plan mode, or `none` in ticket mode.
- `unit_id` — the phase number in plan mode or `TNNN` in ticket mode.
- `purpose` — `production` or `prototype`.
- `completion_marker` — `x` for `production`, `P` for `prototype`.
- `mode` — `default` or `tdd` for `production`; omitted for `prototype`, including any explicit unit override.
- `previous_progress` — previous host progress text or `None` for the first attempt.
- `current_progress_status` — current host progress/status text.

Do not pass `phase_contract`, `ticket_contract`, or `report_path`. The reviewer validates the handoff, derives its own workspace-local report path, and writes a persistent incremental report. The report is not part of the project-root commit. A completed reviewer returns only:

```text
report_path: <absolute report path>
verdict: APPROVED | REJECTED
```

If the reviewer returns `REJECTED`, the host fixes every remaining finding, reruns normal verification, and resumes the same reviewer agent ID for a fresh review attempt. The fresh attempt receives the next report number; reviewer Minor/Trivial direct fixes remain allowed. Repeat until the reviewer explicitly returns `verdict: APPROVED`.

If the reviewer is interrupted, resume the same agent ID and same report up to three times. If it still stops, pause and ask the user. If report persistence fails after the reviewer's three write/read-back retries, pause for the user; never approve inline without the persistent report.

The review retry loop is separate from the three-attempt normal-verification retry budget. Reviewer direct fixes remain in the working tree and are included in the approved implementation-unit commit.

## Commit Rules

All commits are created directly on the current branch of the project-root repository.

Use the durable commit-message rules in [COMMIT-CONVENTIONS.md](./references/COMMIT-CONVENTIONS.md): commit subjects are compact, clear descriptions of the delivered behavior or UX journey and contain no mutable ticket, phase, feature, backlog, run, or attempt identifiers. TDD state markers remain explicit only for production `tdd` runs.

- `production` + `default`: after reviewer `APPROVED`, commit the implementation unit once with no `[state]` flag.
- `production` + `tdd`: `[red]`, `[green]`, `[red-fix]`, and `[green-fix]` commits are preserved; commit any approved remaining reviewer direct fixes before unit completion.
- `production` + `tdd` scaffolding units where a failing test cannot be written first: green-only commit with a `[scaffold]` note in the message.
- `prototype`: use a compact imperative commit description of the delivered E2E journey without TDD state markers or mutable workflow identifiers; record the purpose and journey in progress/review context, and complete source checklists with `[P]`.

Source metadata remains in the canonical plan/ticket and review artifacts; do not duplicate mutable workflow identifiers in the commit message. A concise implementation description is required, not a metadata-derived commit template.

Do not include plan phase or ticket acceptance-criteria updates or workspace-local reviewer reports in the project implementation-unit commit. After the approved code commit, update the canonical source artifact's completion state as a separate verified workspace step. Never include unrelated changes.

Reviewer direct fixes are included in the implementation-unit commit; the commit happens only after an explicit persisted `APPROVED` verdict.

## Completion

After each implementation unit's reviewer returns `APPROVED`:

1. Commit the approved unit code/TDD changes.
2. In plan mode, update the canonical plan's completed-phase acceptance
   criteria/status using `[x]` for `production` or `[P]` for `prototype`; in
   ticket mode, update only the completed unit's checklist with the same
   purpose-specific marker. Never convert `[P]` to `[x]` as part of a prototype
   run. Verify the source-artifact update separately and retry it up to three
   times; if it remains unsuccessful, preserve the code commit, do not advance,
   and ask the user.
3. Select the next unfinished plan phase or executable ticket and repeat the implementation, verification, review, commit, and source-update cycle.
4. When every phase or ticket is approved, committed, and marked complete, stop with a concise completion summary.

## Workflow Diagram

See [WORKFLOW.md](./references/WORKFLOW.md).

## References

- [MODE.md](./references/MODE.md) — purpose, completion-marker, and implementation-mode semantics.
- [COMMIT-CONVENTIONS.md](./references/COMMIT-CONVENTIONS.md) — durable commit-message and source-completion rules.
- [WORKFLOW.md](./references/WORKFLOW.md) — the plan-phase and ticket implementation cycle.

## Agents

| Agent | Role | Primary output |
|---|---|---|
| `impl-reviewer` | Acceptance-criteria gate; independently verifies each host-implemented phase or ticket and writes its persistent incremental report before the implementation-unit commit. | Report path and `APPROVED`/`REJECTED` verdict |
