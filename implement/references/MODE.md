# Implement Modes

`implement` supports `default` and `tdd`. When the user does not explicitly provide a mode, ask once at the start of the plan run. Apply that mode to every phase unless the user explicitly requests a different mode for a particular phase.

Do not read or write `_xzy-ai/implement-mode.md` or `_xzy-ai/dispatch-mode.md`. Mode is not persistent. An explicit mode supplied for a phase takes precedence over the plan-run default.

## Default

Use the normal implementation loop for each phase:

1. Explore the relevant code and project conventions.
2. Implement the phase.
3. Add or update tests for functional behavior, or run project-appropriate checks for scaffolding.
4. Run normal verification and fix failures up to three times.
5. Run `impl-reviewer` and repeat the review/fix/verification loop until it explicitly returns `APPROVED`.
6. Commit the approved phase once with no `[state]` flag.
7. Update the canonical plan completion state separately before starting the next phase.

The commit has no mode-state bracket:

```text
feat <feat_name> features <feature_number> phase <NNN> <message>
```

## TDD

For functional phases, use Red → Green → Refactor:

1. Red: write a focused failing test and commit it.
2. Green: implement the smallest behavior that makes the test pass and commit it.
3. Refactor: improve the implementation and tests while preserving behavior.
4. If refactoring changes behavior or causes a failure, use the appropriate `red-fix` and `green-fix` commits.
5. Run `impl-reviewer` after Red → Green → Refactor and repeat the review/fix/verification loop until it explicitly returns `APPROVED`.
6. Preserve the TDD commits. Commit any approved remaining reviewer direct fixes before updating the plan completion state.

TDD commits are created directly on the current branch and remain in history. Use these states:

- `[red]`
- `[green]`
- `[red-fix]`
- `[green-fix]`

For scaffolding phases where a failing test cannot meaningfully be written first, use a green-only implementation commit and include `[scaffold]` in the commit message as a note. Scaffolding still requires applicable syntax, build, configuration, or validation checks.

## Reviewer recovery

- After a completed `REJECTED` review, fix every remaining finding, rerun normal verification, and resume the same reviewer agent ID for a fresh attempt with the next report number.
- If the reviewer is interrupted, resume the same agent ID and same report up to three times. If it still stops, pause and ask the user.
- If report persistence fails after three write/read-back attempts, pause and ask the user. Never use an inline-only approval.
- Reviewer reports are workspace-local artifacts and are not part of the project code commit.

## Plan completion

After a phase is approved and its code changes are committed, update the canonical plan's phase completion state as a separate workspace step. Verify the write and retry it up to three times. If it remains unsuccessful, preserve the code commit, do not start the next phase, and ask the user.
