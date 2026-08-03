# Commit Conventions

All `implement` commits are created directly on the current branch. There is no worktree to merge, so the branch history is the phase history.

## Template

```text
feat <feat_name> features <feature_number> phase <NNN> [state] <message>
```

| Part | Meaning |
|---|---|
| `<feat_name>` | Feature name. Derived from the native plan path when available; otherwise from the user's free-form input. |
| `<feature_number>` | Zero-padded feature number. Derived from the native plan path (`<NNN>`); `001` for free-form input. |
| `<NNN>` | Phase number. Always present, zero-padded to three digits. |
| `[state]` | TDD mode state bracket only. Omitted in default mode. |
| `<message>` | Short imperative description of the commit. |

## Default Mode

Commit once after verification passes:

```text
feat <feat_name> features <feature_number> phase <NNN> <message>
```

Example:

```text
feat checkout features 042 phase 003 implement cart persistence
```

## TDD Mode

Commit the Red → Green → Refactor cycle with state brackets, preserved in history:

```text
feat <feat_name> features <feature_number> phase <NNN> [red] <message>
feat <feat_name> features <feature_number> phase <NNN> [green] <message>
feat <feat_name> features <feature_number> phase <NNN> [red-fix] <message>
feat <feat_name> features <feature_number> phase <NNN> [green-fix] <message>
```

- `[red]`: a new focused test that fails.
- `[green]`: the smallest behavior change that makes the test pass.
- `[red-fix]`: a new or revised test triggered by a refactor regression.
- `[green-fix]`: the behavior change that resolves that regression.

Refactor itself is not a commit flag. Do not squash TDD commits; keep the cycle readable.

## Scaffolding Fallback

When a phase is classified `scaffolding` and a failing test cannot be written first, commit the implementation once and note the scaffold in the message:

```text
feat <feat_name> features <feature_number> phase <NNN> [scaffold] <message>
```

## Plan Checkbox Updates

When a source `plan.md` exists, include its acceptance-criteria checkbox updates for the completed phase in the phase commit. Do not create a separate plan commit.

## Never Include

- Unrelated or pre-existing uncommitted changes.
- Failing or unverified work.
- Merge or worktree artifacts.
