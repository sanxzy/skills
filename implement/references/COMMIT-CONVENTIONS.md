# Commit Conventions

All `implement` commits are created directly on the current branch of the project-root repository. There is no worktree to merge, so the branch history is the phase history.

## Template

```text
feat <feat_name> features <feature_number> phase <NNN> [state] <message>
```

| Part | Meaning |
|---|---|
| `<feat_name>` | Feature name derived from the canonical plan path. |
| `<feature_number>` | Zero-padded feature number derived from the canonical plan path. |
| `<NNN>` | Current phase number, always present and zero-padded to three digits. |
| `[state]` | TDD mode state bracket only. Omitted in default mode. |
| `<message>` | Short imperative description of the commit. |

Every implementation request uses a canonical plan. There is no direct free-form commit fallback.

## Approval and phase completion order

1. Implement and verify the current phase.
2. Run `impl-reviewer` until it returns an explicit persisted `APPROVED` verdict.
3. Commit the approved project-root code changes, including any reviewer Minor/Trivial direct fixes.
4. Update and verify the canonical plan's phase completion state as a separate workspace step.
5. Start the next phase only after both the code commit and plan update succeed.

Workspace-local reviewer reports are never included in the project phase commit.

## Default Mode

Commit once after reviewer approval:

```text
feat <feat_name> features <feature_number> phase <NNN> <message>
```

Example:

```text
feat checkout features 042 phase 003 implement cart persistence
```

## TDD Mode

Commit the Red → Green → Refactor cycle with state brackets, preserving the commits in history:

```text
feat <feat_name> features <feature_number> phase <NNN> [red] <message>
feat <feat_name> features <feature_number> phase <NNN> [green] <message>
feat <feat_name> features <feature_number> phase <NNN> [red-fix] <message>
feat <feat_name> features <feature_number> phase <NNN> [green-fix] <message>
```

- `[red]`: a new focused behavior test that fails for a missing or incorrect behavior.
- `[green]`: the smallest behavior change that makes the test pass.
- `[red-fix]`: a new or revised test triggered by a refactor regression.
- `[green-fix]`: the behavior change that resolves that regression.

Refactor itself is not a commit flag. Do not squash TDD commits. After reviewer approval, commit any approved remaining reviewer direct fixes before updating the plan.

## Scaffolding Fallback

When a phase is classified `scaffolding` and a failing test cannot be written first, commit the implementation once and note the scaffold in the message:

```text
feat <feat_name> features <feature_number> phase <NNN> [scaffold] <message>
```

## Plan Completion Updates

Do not include plan acceptance-criteria checkbox/status updates in the project phase commit. After the approved code commit, update the canonical plan separately, verify the write, and retry that update up to three times. If it still fails, preserve the code commit, do not advance to the next phase, and ask the user.

## Never Include

- Unrelated or pre-existing uncommitted changes.
- Failing or unverified work.
- Workspace-local reviewer reports.
- Plan completion updates in the project phase commit.
- Merge or worktree artifacts.
