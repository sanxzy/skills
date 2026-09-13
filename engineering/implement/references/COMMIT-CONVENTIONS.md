# Commit Conventions

All `implement` commits are created directly on the current branch of the project-root repository. There is no worktree to merge, so the branch history is the implementation-unit history.

## Source-specific templates

### Plan mode

```text
feat <feat_name> features <feature_number> phase <NNN> [state] <message>
```

| Part | Meaning |
|---|---|
| `<feat_name>` | Feature name derived from the canonical plan path. |
| `<feature_number>` | Zero-padded feature number derived from the canonical plan path. |
| `<NNN>` | Current phase number, always present and zero-padded to three digits. |
| `[state]` | TDD mode state bracket only. Omitted in default mode. |
| `<message>` | Short imperative description of the phase. |

Example:

```text
feat checkout features 042 phase 003 implement cart persistence
```

### Ticket mode

```text
feat <backlog_name> ticket <TNNN> [state] <message>
```

| Part | Meaning |
|---|---|
| `<backlog_name>` | Lowercase backlog name derived from `_xzy-ai/sprints/<backlog>/tickets.md`. |
| `<TNNN>` | Ticket identifier from the canonical ticket file, such as `T003`. |
| `[state]` | TDD mode state bracket only. Omitted in default mode. |
| `<message>` | Short imperative description of the ticket outcome. |

Example:

```text
feat account-recovery ticket T003 review incomplete submission
```

Ticket commits preserve the ticket ID exactly. Do not replace it with a phase number or a feature number.

## Approval and source completion order

For either source mode:

1. Implement and verify the current phase or ticket.
2. Run `impl-reviewer` until it returns an explicit persisted `APPROVED` verdict.
3. Commit the approved project-root code changes, including any reviewer Minor/Trivial direct fixes.
4. Update and verify the canonical source artifact separately:
   - plan mode: phase acceptance-criteria/status update;
   - ticket mode: selected ticket acceptance-criteria update.
5. Start the next phase or executable ticket only after both the code commit and source update succeed.

Workspace-local reviewer reports are never included in the project implementation-unit commit.

## Default mode

Commit once after reviewer approval:

Plan mode:

```text
feat <feat_name> features <feature_number> phase <NNN> <message>
```

Ticket mode:

```text
feat <backlog_name> ticket <TNNN> <message>
```

Do not add a state bracket in default mode.

## TDD mode

Preserve the Red → Green → Refactor cycle in history. Use these state markers in both source modes:

- `[red]` — a focused behavior test that fails for a missing or incorrect behavior;
- `[green]` — the smallest behavior change that makes the test pass;
- `[red-fix]` — a new or revised test triggered by a refactor regression;
- `[green-fix]` — the behavior change that resolves that regression.

Plan mode examples:

```text
feat <feat_name> features <feature_number> phase <NNN> [red] add recovery behavior test
feat <feat_name> features <feature_number> phase <NNN> [green] implement recovery behavior
feat <feat_name> features <feature_number> phase <NNN> [red-fix] cover corrected boundary
feat <feat_name> features <feature_number> phase <NNN> [green-fix] preserve corrected behavior
```

Ticket mode examples:

```text
feat <backlog_name> ticket <TNNN> [red] add review behavior test
feat <backlog_name> ticket <TNNN> [green] implement review outcome
feat <backlog_name> ticket <TNNN> [red-fix] cover corrected boundary
feat <backlog_name> ticket <TNNN> [green-fix] preserve corrected behavior
```

Refactor itself is not a commit flag. Do not squash TDD commits. After reviewer approval, commit any approved remaining reviewer direct fixes before updating the source artifact.

## Scaffolding fallback

When an implementation unit is classified `scaffolding` and a failing test cannot be written first, commit the implementation once and note the scaffold in the message:

Plan mode:

```text
feat <feat_name> features <feature_number> phase <NNN> [scaffold] establish project boundary
```

Ticket mode:

```text
feat <backlog_name> ticket <TNNN> [scaffold] establish user-visible foundation
```

The scaffold must still have a valid source acceptance contract and pass applicable syntax, build, configuration, or validation checks. Do not use a scaffold commit to hide a technical-only task that has no contract-level outcome.

## Source-artifact updates

Do not include plan phase or ticket acceptance-criteria updates in the project implementation-unit commit. After the approved code commit, update the canonical source artifact separately and verify the write/read-back. If the update still fails after three retries, preserve the code commit, do not advance, and ask the user.

In ticket mode, check only the completed ticket's acceptance criteria. Do not alter `Blocked by`, proposal traceability, scope boundaries, dependency order, or other ticket contracts during routine completion.

## Never include

- unrelated or pre-existing uncommitted changes;
- failing or unverified work;
- workspace-local reviewer reports;
- plan or ticket completion updates in the project implementation-unit commit;
- merge or worktree artifacts;
- a phase number in place of a ticket identifier for a ticket-mode commit;
- a ticket identifier in place of a feature/phase identity for a plan-mode commit.
