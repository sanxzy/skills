# Scaffolding Exemption

The scaffolding exemption allows pure scaffolding work units to skip TDD and test requirements. However, misclassification is a **Blocker**.

## What Qualifies as Scaffolding

**Scaffolding work units** are limited to work that sets up the project environment without implementing business logic:

| Scaffolding Examples | NOT Scaffolding |
|---|---|
| Setting up project structure (directories, configs) | Implementing a route handler |
| Configuring build tooling (webpack, vite, tsc) | Writing a database migration |
| Setting up CI pipeline | Adding a data model |
| Installing and configuring dependencies | Implementing business logic |
| Configuring linting/formatting | Adding API endpoints |
| Setting up test framework | Writing middleware |
| Configuring code generation | Adding authentication logic |
| Setting up Docker/container config | Writing a service |
| Initial package.json and tsconfig | Any code that processes data |

**Rule of thumb**: If the work unit produces **behaviour** (something the user can interact with or that processes data), it's functional. If it produces **configuration**, it's scaffolding.

## Exemption Rules

### Workers

**Scaffolding work units:**
- No TDD required (even if TDD mode is active)
- No tests required
- Default mode only

**Functional work units:**
- Full TDD in TDD mode (red-green-refactor)
- Tests required
- Default or TDD mode as configured

### ACS Reviewer

**Scaffolding work units:**
- Skip missing-test verification
- Do not raise missing-test findings
- Still verify that configuration meets acceptance criteria (e.g., "linting passes", "project builds")

**Functional work units:**
- Full test verification
- Missing tests is a finding

### Quality Gate Reviewer

**Scaffolding work units:**
- Coverage check is **skipped** (not enforced)
- All other checks still apply (linting, formatting, build)
- Tests check: scaffolding may legitimately have no tests

**Functional work units:**
- All checks apply including coverage

### Security Reviewer

**Scaffolding exemption does NOT apply to security review.** Every work unit gets a full security review, regardless of type. Scaffolding work units can introduce security vulnerabilities (e.g., insecure dependency versions, misconfigured CI secrets, exposed Docker ports).

## Misclassification

If a work unit is classified as `scaffolding` but actually requires functional implementation:

- **This is a Blocker.**
- The ACS reviewer must flag it.
- The coordinator must re-classify the work unit as `functional` and re-delegate.

## Determining Work Unit Type

When processing inputs:

- `ticket.md` from `generate-tickets`: inferred from ticket title and description. Keywords like "Set up", "Configure", "Scaffold", "Initialize", "Project structure", "Build tooling", "CI" → scaffolding. Everything else → functional.
- **Normalization path**: inferred from work unit content using the same keyword matching.
