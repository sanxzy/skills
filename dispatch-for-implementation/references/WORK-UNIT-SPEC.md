# Work Unit Spec Format

The work unit spec file is written by the coordinator **before** delegating a work unit to a worker. It is the single source of truth for what the worker needs to build.

## Path

```
_xzy-ai/sprints/<backlog_name>/dispatch/work-unit-spec-<NN>.md
```

Where `<NN>` is the numeric work unit identifier (e.g., `01`, `02`).

## Format

```markdown
# Work Unit <NN>: <Title>

**Backlog:** <backlog_name>
**Type:** <functional | scaffolding>
**Status:** dispatched

## Background

<background_detail — what the user wants, broader context>

## Previous Progress

<previous_progress_context — what has been done so far in prior work units>

## What to Build

<what_it_delivers — the end-to-end behaviour this work unit makes work>

## Acceptance Criteria

- [ ] <acceptance criterion 1>
- [ ] <acceptance criterion 2>
- [ ] <acceptance criterion 3>

## Blocked By

<list of work unit IDs that block this one, or "None — can start immediately">

## Constraints

- <any specific constraints, limitations, or requirements>
- <e.g., "Must use the existing repository pattern">
- <e.g., "Must not modify the public API">

## Notes

<coordinator notes for the worker>
```

## Example

```markdown
# Work Unit 01: Set up Project Scaffolding

**Backlog:** user-auth-feature
**Type:** scaffolding
**Status:** dispatched

## Background

Build a user authentication system for a web application. The user wants email/password login with JWT-based session management.

## Previous Progress

None — this is the first work unit.

## What to Build

A working project structure with build tooling, linting, and CI pipeline ready for development.

## Acceptance Criteria

- [ ] Project builds without errors
- [ ] Linting passes on all source files
- [ ] CI pipeline runs successfully

## Blocked By

None — can start immediately

## Constraints

- Use the existing monorepo structure
- TypeScript for all source files
- ESLint + Prettier for code quality
- GitHub Actions for CI

## Notes

This is a scaffolding work unit. No tests required. Focus on project structure and tooling configuration.
```

```markdown
# Work Unit 02: Implement Login Endpoint

**Backlog:** user-auth-feature
**Type:** functional
**Status:** dispatched

## Background

Build a user authentication system for a web application. The user wants email/password login with JWT-based session management.

## Previous Progress

- **WU-01**: Project scaffolding complete. Build tooling, linting, and CI configured. Express.js + TypeScript project structure in place.

## What to Build

Users can log in with email and password via a REST API endpoint. Successful login returns a JWT access token and refresh token.

## Acceptance Criteria

- [ ] POST /auth/login accepts email and password
- [ ] Valid credentials return 200 with JWT access token and refresh token
- [ ] Invalid credentials return 401 with error message
- [ ] Missing email or password returns 400 with validation error
- [ ] Account locked after 5 failed attempts returns 423

## Blocked By

01 — Set up Project Scaffolding

## Constraints

- Use jose library for JWT (version from package.json)
- Use bcrypt for password hashing
- Follow the existing repository pattern for data access
- Input validation with zod

## Notes

This is a functional work unit. Tests are required. TDD mode: write failing tests first if TDD mode is active.
```

## Coordinator Rules

1. Write the spec file **before** invoking the worker agent.
2. Include all required inputs that the worker expects (acceptance criteria, what_to_deliver, etc.).
3. The spec file is the worker's primary reference. The coordinator's delegation prompt should reference the spec file path, not duplicate its content.
4. Spec files are read by reviewers during the review gate sequence.
