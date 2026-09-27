# Implement Purpose and Modes

`implement` resolves one purpose: `production` or `prototype`.

- `production` uses one implementation mode: `default` or `tdd`.
- `prototype` uses the interactive-prototype workflow and does not select a
  production implementation mode.

A prototype is specifically an **E2E interactive prototype**: it should
simulate the selected core product journey from entry point through the user's
value/outcome. It is not limited to a component, one screen, or an isolated
feature. Fake data, hardcoded/in-memory state, fake loading/error states,
scripted responses, and simulated side effects are allowed when they preserve
the experience being evaluated. The prototype must not claim real backend,
persistence, authentication, renderer, integration, or production reliability.

Ask once for purpose when it is not explicit. In `production`, ask once for
`default` or `tdd` when that implementation mode is not explicit. Purpose and
implementation mode are not persistent files and must not be changed silently
mid-run. Do not read or write `_xzy-ai/implement-mode.md` or
`_xzy-ai/dispatch-mode.md`.

## Completion markers

Acceptance criteria use a purpose-specific marker:

- production: `- [x]`;
- prototype: `- [P]`.

`[P]` means the criterion is implemented and verified as part of the E2E
prototype; it does not mean production behavior is complete. `[x]` remains the
production marker. Do not convert `[P]` to `[x]` during a prototype run.

## Source-specific terminology

- In **plan mode**, the implementation unit is a `phase`, and completion is recorded in the canonical `plan.md`.
- In **ticket mode**, the implementation unit is a `ticket`, and completion is recorded by updating the completed ticket's criteria with the selected marker.
- When describing behavior common to both modes, use `implementation unit`.

Do not merge multiple tickets into one implementation unit merely for convenience. Ticket mode follows the source ticket dependency order and keeps each ticket's scope intact.

## Test file naming

When a phase or ticket adds a project-owned test, use a semantic subject-and-behavior filename that follows the repository's existing convention. Do not use phase, feature, ticket, review, TDD-state, or attempt identifiers as the filename, such as `phase3-events.test.ts` or `phase13-review010.test.ts`. Prefer names like `session-runtime-redaction.test.ts` or `transport-structured.test.ts`; if a focused file already covers the behavior, extend it instead of creating another metadata-named file. The only exception is a reviewer-isolated audit test, which keeps `attempt-<NN>-<semantic-slug>.<ext>` for traceability while requiring a semantic slug.

## Purpose workflow

Use the normal implementation loop for each implementation unit:

1. Explore the relevant code and project conventions.
2. Read the selected purpose's complete contract and define the core E2E
   journey, entry point, user outcome, observable states, and fake boundaries.
3. Implement the active phase or ticket. For `prototype`, prioritize a
   complete, navigable journey over production infrastructure; for
   `production`, implement the real boundaries required by the contract.
4. Add or update independent behavior-focused verification. A prototype must
   exercise the complete supported journey, not only one component interaction.
5. Run normal verification and fix failures up to three times.
6. Run `impl-reviewer` and repeat the review/fix/verification loop until it
   explicitly returns `APPROVED`.
7. Commit the approved implementation unit once with no TDD `[state]` flag
   unless this is a production `tdd` run.
8. Update and verify the canonical plan phase or ticket acceptance criteria
   using `[x]` for production or `[P]` for prototype before starting the next
   unit.

Commit form for production `default` and prototype purpose:

```text
<compact imperative description of the delivered behavior or E2E UX journey>
```

Do not include ticket, phase, feature, backlog, run, or attempt identifiers.
See [COMMIT-CONVENTIONS.md](./COMMIT-CONVENTIONS.md) for production `tdd`
and scaffolding variants.

## Production `tdd`

Only a `production` run may select `tdd`. For functional implementation units,
use Red → Green → Refactor:

1. Red: write a focused failing behavior test and commit it. Derive its assertions from the active phase or ticket contract, not by copying the implementation; it must fail for a missing or incorrect behavior and, where applicable, cover type-preserving structural invariance without forcing dynamic values to be identical.
2. Green: implement the smallest behavior that makes the test pass and commit it.
3. Refactor: improve the implementation and tests while preserving behavior.
4. If refactoring changes behavior or causes a failure, use the appropriate `red-fix` and `green-fix` commits.
5. Run `impl-reviewer` after Red → Green → Refactor and repeat the review/fix/verification loop until it explicitly returns `APPROVED`.
6. Preserve the TDD commits. Commit any approved remaining reviewer direct fixes before updating the source artifact's completion state.

Production `tdd` commit form:

```text
[state] <compact imperative description of the test or behavior state>
```

Use these state markers:

- `[red]`
- `[green]`
- `[red-fix]`
- `[green-fix]`

Refactor itself is not a commit flag. Do not squash TDD commits. For scaffolding units where a failing test cannot meaningfully be written first, use a green-only implementation commit and include `[scaffold]` in the commit message as a note. Scaffolding still requires applicable syntax, build, configuration, or validation checks.

## Reviewer recovery

- After a completed `REJECTED` review, fix every remaining finding, rerun normal verification, and resume the same reviewer agent ID for a fresh attempt with the next report number.
- If the reviewer is interrupted, resume the same agent ID and same report up to three times. If it still stops, pause and ask the user.
- If report persistence fails after three write/read-back attempts, pause and ask the user. Never use an inline-only approval.
- Reviewer reports are workspace-local artifacts and are not part of the project code commit.

## Source-artifact completion

After an implementation unit is approved and its code changes are committed:

- in plan mode, update the completed phase's acceptance criteria/status in
  `plan.md` with `[x]` for production or `[P]` for prototype;
- in ticket mode, update every completed acceptance criterion in the selected
  ticket file with `[x]` for production or `[P]` for prototype, preserving its
  `Blocked by`, traceability, and scope fields.

Verify the source-artifact write and read-back up to three times. If it remains unsuccessful, preserve the code commit, do not start the next unit, and ask the user. A ticket is not complete merely because its code was committed; its canonical acceptance criteria must be verified as complete.
