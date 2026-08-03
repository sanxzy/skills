# Implement Modes

`implement` supports `default` and `tdd`. When the user does not explicitly provide a mode, ask the user to choose one on every invocation.

Do not read or write `_xzy-ai/implement-mode.md` or `_xzy-ai/dispatch-mode.md`. Mode is not persistent. An explicit mode supplied in the request takes precedence over the prompt.

## Default

Use the normal implementation loop:

1. Explore the relevant code and project conventions.
2. Implement the phase.
3. Add or update tests for functional behavior, or run project-appropriate checks for scaffolding.
4. Run verification commands.
5. Fix failures up to three times.
6. Commit once after verification passes.

The commit has no mode-state bracket:

```text
feat <feat_name> features <feature_number> phase <NNN> <message>
```

## TDD

For functional phases, use Red → Green → Refactor:

1. Red: write a focused failing test and commit it.
2. Green: implement the smallest behavior that passes and commit it.
3. Refactor: improve the implementation and tests while preserving behavior.
4. If refactoring changes behavior or causes a failure, use the appropriate `red-fix` and `green-fix` commits.

TDD commits are created directly on the current branch and remain in history. Use these states:

- `[red]`
- `[green]`
- `[red-fix]`
- `[green-fix]`

For scaffolding phases where a failing test cannot meaningfully be written first, use a green-only implementation commit and include `[scaffold]` in the commit message as a note. Scaffolding still requires applicable syntax, build, configuration, or validation checks.

## Interrupted Runs

No resume artifacts are written. If a run is interrupted, treat the phase as incomplete and re-run it from scratch on the next invocation. Handle any resulting uncommitted changes through the clean-tree precondition before starting again.
