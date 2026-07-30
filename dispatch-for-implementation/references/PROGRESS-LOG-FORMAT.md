# Progress Log Format

The dispatch progress log lives at:

```text
_xzy-ai/sprints/<backlog>/dispatch/progress.md
```

It is append-only Markdown. The coordinator writes it; agents do not.

## Entry Format

```markdown
- <sequence> | <event> | <key=value>; <key=value> | next: <next-action>
```

## Required Events

| Event | Required fields |
|---|---|
| `dispatch-started` | `source`, `mode` |
| `phase-selected` | `phase`, `title`, `source-plan` |
| `worktree-created` | `phase`, `path` |
| `assignment-written` | `phase`, `path` |
| `worker-started` | `phase`, `agent`, `mode` |
| `worker-completed` | `phase`, `agent`, `report`, `status` |
| `worker-blocked` | `phase`, `agent`, `report`, `topic` |
| `advisor-completed` | `phase`, `report`, `topic` |
| `acs-reviewed` | `phase`, `report`, `verdict`, `direct-fixes` |
| `security-quality-reviewed` | `phase`, `report`, `verdict`, `direct-fixes` |
| `phase-committed` | `phase`, `commit`, `message` |
| `phase-merged` | `phase`, `merge-commit` |
| `plan-updated` | `phase`, `path`, `checked-criteria` |
| `worktree-cleaned` | `phase`, `path` |
| `dispatch-completed` | `phase`, `continued` |
| `dispatch-paused` | `phase`, `reason` |

## Rules

1. Append events as they happen.
2. Never rewrite earlier events.
3. Use phase terminology only.
4. Record report paths, worktree paths, commit hashes, and verdicts. All recorded paths should be absolute when they are intended for agent handoff.
5. When continuing multiple phases by explicit user request, append a new `phase-selected` event for each phase.
