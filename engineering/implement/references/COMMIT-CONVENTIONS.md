# Commit Conventions

All `implement` commits are created directly on the current branch of the project-root repository. There is no worktree to merge, so the branch history is the implementation-unit history.

## Durable commit-message format

Commit messages are long-lived implementation context. Plans, tickets, phase
numbers, feature numbers, backlog names, run IDs, and attempt IDs are mutable
workflow metadata and must not be used as commit-message identity.

Every commit subject must be a compact, clear, imperative description of what
was delivered. The subject should remain understandable if the source ticket
or plan is later edited or removed.

Default and prototype commits use:

```text
<imperative description of the delivered behavior or UX journey>
```

Examples:

```text
Preserve editor state while switching media panels
Prototype the project-to-export editing journey
```

Do not include ticket IDs, phase/feature numbers, backlog names, run IDs,
attempt numbers, or similar mutable identifiers. Source identity remains in the
canonical artifact and review report, not in the commit subject.

## Approval and source completion order

For either source mode and purpose:

1. Implement and verify the current phase or ticket. In `prototype`, verify the
   complete E2E core journey and record its fake boundaries.
2. Run `impl-reviewer` until it returns an explicit persisted `APPROVED` verdict.
3. Commit the approved project-root code changes, including any reviewer Minor/Trivial direct fixes.
4. Update and verify the canonical source artifact separately:
   - plan mode: phase acceptance-criteria/status update using `[x]` for
     `production` or `[P]` for `prototype`;
   - ticket mode: selected ticket acceptance-criteria update using the same
     purpose-specific marker.
5. Start the next phase or executable ticket only after both the code commit and source update succeed.

Workspace-local reviewer reports are never included in the project implementation-unit commit.

## Production `default` mode

Commit once after reviewer approval using a compact imperative description of
the delivered behavior. Do not add a TDD state bracket or mutable workflow
identifier.

## Prototype purpose

Prototype commits use the same durable message form without TDD state markers.
The commit should describe the completed E2E journey or interaction model;
completion is recorded separately with `[P]` in the source artifact.

## Production `tdd` mode

Preserve the Red → Green → Refactor cycle in history. Use these state markers in both plan and ticket source modes:

- `[red]` — a focused behavior test that fails for a missing or incorrect behavior;
- `[green]` — the smallest behavior change that makes the test pass;
- `[red-fix]` — a new or revised test triggered by a refactor regression;
- `[green-fix]` — the behavior change that resolves that regression.

Use only the state marker needed to preserve the TDD sequence, followed by a
compact description. Do not add ticket/phase/feature/backlog/run/attempt
identifiers.

```text
[red] Add a failing test for interrupted export recovery
[green] Preserve export state across interruption
[red-fix] Cover recovery after a partial progress update
[green-fix] Restore the corrected recovery boundary
```

Refactor itself is not a commit flag. Do not squash TDD commits. After reviewer approval, commit any approved remaining reviewer direct fixes before updating the source artifact.

## Scaffolding fallback

When an implementation unit is classified `scaffolding` and a failing test cannot be written first, commit the implementation once and note the scaffold in the message:

```text
[scaffold] Establish the user-visible prototype foundation
```

The scaffold must still have a valid source acceptance contract and pass applicable syntax, build, configuration, or validation checks. Do not use a scaffold commit to hide a technical-only task that has no contract-level outcome.

## Source-artifact updates

Do not include plan phase or ticket acceptance-criteria updates in the project implementation-unit commit. After the approved code commit, update the canonical source artifact separately and verify the write/read-back. If the update still fails after three retries, preserve the code commit, do not advance, and ask the user.

In ticket mode, update only the completed ticket's acceptance criteria, using
`[x]` for `production` and `[P]` for `prototype`. Do not alter `Blocked by`,
proposal traceability, scope boundaries, dependency order, or other ticket
contracts during routine completion. A `[P]` criterion is a prototype result,
not a production completion claim.

## Never include

- unrelated or pre-existing uncommitted changes;
- failing or unverified work;
- workspace-local reviewer reports;
- plan or ticket completion updates in the project implementation-unit commit;
- merge or worktree artifacts;
- ticket, phase, feature, backlog, run, attempt, or other mutable workflow
  identifiers in the commit message;
