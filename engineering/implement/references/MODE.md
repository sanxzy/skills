# Implement Modes

`implement` supports `default` and `tdd`. When the user does not explicitly provide a mode, ask once at the start of the implementation run. Apply that mode to every implementation unit unless the user explicitly requests a different mode for a particular phase or ticket.

Do not read or write `_xzy-ai/implement-mode.md` or `_xzy-ai/dispatch-mode.md`. Mode is not persistent. An explicit mode supplied for a unit takes precedence over the implementation-run default.

## Source-specific terminology

- In **plan mode**, the implementation unit is a `phase`, and completion is recorded in the canonical `plan.md`.
- In **ticket mode**, the implementation unit is a `ticket`, and completion is recorded by checking the completed ticket's acceptance criteria in its canonical ticket file.
- When describing behavior common to both modes, use `implementation unit`.

Do not merge multiple tickets into one implementation unit merely for convenience. Ticket mode follows the source ticket dependency order and keeps each ticket's scope intact.

## Test file naming

When a phase or ticket adds a project-owned test, use a semantic subject-and-behavior filename that follows the repository's existing convention. Do not use phase, feature, ticket, review, TDD-state, or attempt identifiers as the filename, such as `phase3-events.test.ts` or `phase13-review010.test.ts`. Prefer names like `session-runtime-redaction.test.ts` or `transport-structured.test.ts`; if a focused file already covers the behavior, extend it instead of creating another metadata-named file. The only exception is a reviewer-isolated audit test, which keeps `attempt-<NN>-<semantic-slug>.<ext>` for traceability while requiring a semantic slug.

## Default

Use the normal implementation loop for each implementation unit:

1. Explore the relevant code and project conventions.
2. Implement the active phase or ticket.
3. Add or update behavior-focused tests for functional behavior, using an oracle independent from the production implementation; never use tautological tests. When the contract promises a stable shape or type, apply type-preserving structural invariance by varying same-type/category values and asserting the public structure/types, not exact dynamic values. Do not force dynamic values, including but not limited to IDs, timestamps, tokens, nonces/salts, salted/randomized hashes, or randomized encryption/ciphertext, to compare identically; assert their contract-level properties instead. Exact equality is allowed when deterministic equality is explicitly contracted or variability is controlled. For scaffolding, run project-appropriate checks.
4. Run normal verification and fix failures up to three times.
5. Run `impl-reviewer` and repeat the review/fix/verification loop until it explicitly returns `APPROVED`.
6. Commit the approved implementation unit once with no `[state]` flag.
7. Update and verify the canonical plan phase or ticket acceptance criteria separately before starting the next unit.

Plan mode commit form:

```text
feat <feat_name> features <feature_number> phase <NNN> <message>
```

Ticket mode commit form:

```text
feat <backlog_name> ticket <TNNN> <message>
```

See [COMMIT-CONVENTIONS.md](./COMMIT-CONVENTIONS.md) for TDD and scaffolding variants.

## TDD

For functional implementation units, use Red → Green → Refactor:

1. Red: write a focused failing behavior test and commit it. Derive its assertions from the active phase or ticket contract, not by copying the implementation; it must fail for a missing or incorrect behavior and, where applicable, cover type-preserving structural invariance without forcing dynamic values to be identical.
2. Green: implement the smallest behavior that makes the test pass and commit it.
3. Refactor: improve the implementation and tests while preserving behavior.
4. If refactoring changes behavior or causes a failure, use the appropriate `red-fix` and `green-fix` commits.
5. Run `impl-reviewer` after Red → Green → Refactor and repeat the review/fix/verification loop until it explicitly returns `APPROVED`.
6. Preserve the TDD commits. Commit any approved remaining reviewer direct fixes before updating the source artifact's completion state.

Plan mode TDD commit form:

```text
feat <feat_name> features <feature_number> phase <NNN> [state] <message>
```

Ticket mode TDD commit form:

```text
feat <backlog_name> ticket <TNNN> [state] <message>
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

- in plan mode, check the completed phase's acceptance criteria/status in `plan.md`;
- in ticket mode, check every completed acceptance criterion in the selected ticket file and preserve its `Blocked by`, traceability, and scope fields.

Verify the source-artifact write and read-back up to three times. If it remains unsuccessful, preserve the code commit, do not start the next unit, and ask the user. A ticket is not complete merely because its code was committed; its canonical acceptance criteria must be verified as complete.
