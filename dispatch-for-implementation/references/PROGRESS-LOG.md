# Progress Log Format

The progress log is a **pure markdown** file at `_xzy-ai/sprints/<backlog>/dispatch/progress.md`. It tracks the chronological execution of the `dispatch-for-implementation` workflow.

## Purpose

The progress log is both:

1. A human-readable timeline of execution.
2. The authoritative record for crash recovery.

## Format

### Events Section

Timeline of execution events. Each event is a timed entry in chronological order:

```markdown
# Dispatch Progress Log — <backlog_name>

## Events

- [<ISO8601 timestamp>] <EVENT_TYPE> — <description>
```

### Issues Section

Track blockers, issues, and their resolutions:

```markdown
## Issues

- [<ISO8601 timestamp>] <ISSUE_TYPE> — <description>
  - [<ISO8601 timestamp>] RESOLVED — <how it was resolved>
```

## Event Types

| Event Type | Description |
|---|---|
| `STARTED` | Workflow started |
| `PHASE_STARTED` | New phase began |
| `DISPATCHED` | Work unit dispatched to worker |
| `WORKER_DONE` | Worker completed implementation |
| `WORKER_BLOCKED` | Worker reported a blocker |
| `ADVISOR_INVOKED` | Worker advisor called |
| `ADVISOR_DONE` | Advisor returned guidance |
| `ACS_REVIEW_PASS` | ACS review passed |
| `ACS_REVIEW_FAIL` | ACS review failed (needs fix) |
| `SECURITY_REVIEW_PASS` | Security review passed |
| `SECURITY_REVIEW_FAIL` | Security review failed (needs fix) |
| `QUALITY_GATE_PASS` | Quality gate passed |
| `QUALITY_GATE_FAIL` | Quality gate failed (needs fix) |
| `REVIEW_CYCLE` | Review cycle number (for multi-cycle scenarios) |
| `MERGED` | Worktree merged to main |
| `CLEANED` | Worktree cleanup completed |
| `COMPLETED` | Work unit fully complete |
| `PHASE_COMPLETE` | Phase complete (all WUs done) |
| `DONE` | Entire workflow complete |
| `ERROR` | Unrecoverable error |
| `ESCALATED` | Issue escalated to user |

## Issue Types

| Issue Type | Description |
|---|---|
| `BLOCKED` | Worker blocked on implementation |
| `REVIEW_FAILURE` | Review gate failure |
| `MERGE_CONFLICT` | Merge conflict on main |
| `TIMEOUT` | Agent timeout |
| `ERROR` | Unexpected error |

## Event Log Format Rules

1. **Chronological order**: Events are appended as they happen. Never reorder.
2. **ISO8601 timestamps**: All times in UTC (e.g., `2026-07-26T10:00:00Z`).
3. **Issues are nested**: Issue resolution is indented under the issue it resolves.
4. **No YAML**: Pure markdown. No frontmatter, no structured schema.
5. **One line per event**: Keep each event on one line for readability.

## Example

```markdown
# Dispatch Progress Log — user-auth-feature

## Events

- [2026-07-26T10:00:00Z] STARTED — Backlog: user-auth-feature
- [2026-07-26T10:05:00Z] PHASE_STARTED — Phase 1 (3 work units)
- [2026-07-26T10:10:00Z] DISPATCHED — Work Unit 01 — Set up Project Scaffolding
- [2026-07-26T10:20:00Z] WORKER_DONE — dispatch-code-worker completed
- [2026-07-26T10:22:00Z] ACS_REVIEW_PASS — All acceptance criteria verified
- [2026-07-26T10:25:00Z] SECURITY_REVIEW_PASS — No critical findings
- [2026-07-26T10:28:00Z] QUALITY_GATE_PASS — All checks passed
- [2026-07-26T10:30:00Z] MERGED — Worktree merged to main
- [2026-07-26T10:31:00Z] CLEANED — Worktree removed
- [2026-07-26T10:32:00Z] COMPLETED — Work Unit 01
- [2026-07-26T10:35:00Z] DISPATCHED — Work Unit 02 — Login Form
- [2026-07-26T10:55:00Z] WORKER_DONE — dispatch-code-with-ui-worker completed
- [2026-07-26T11:00:00Z] ACS_REVIEW_FAIL — Missing error state handling
- [2026-07-26T11:05:00Z] REVIEW_CYCLE — Cycle 2: restart from ACS after fix
- [2026-07-26T11:15:00Z] WORKER_DONE — Worker applied fixes
- [2026-07-26T11:18:00Z] ACS_REVIEW_PASS — All acceptance criteria verified
- [2026-07-26T11:20:00Z] SECURITY_REVIEW_PASS — No findings
- [2026-07-26T11:23:00Z] QUALITY_GATE_PASS — All checks passed
- [2026-07-26T11:25:00Z] MERGED — Worktree merged to main
- [2026-07-26T11:26:00Z] CLEANED — Worktree removed
- [2026-07-26T11:27:00Z] COMPLETED — Work Unit 02
- [2026-07-26T11:30:00Z] PHASE_COMPLETE — Phase 1 complete
- [2026-07-26T11:31:00Z] DONE — All phases complete

## Issues

- [2026-07-26T11:00:00Z] REVIEW_FAILURE — ACS review found missing error state handling for Login Form
  - [2026-07-26T11:05:00Z] RESOLVED — Worker added error state component and 2 new test cases
- [2026-07-26T11:20:00Z] BLOCKED — Worker couldn't determine which JWT library version to use
  - [2026-07-26T11:22:00Z] RESOLVED — Advisor recommended jose v5 based on package.json analysis
```

## Crash Recovery Usage

On recovery startup, the coordinator:

1. Reads the last event in the log.
2. Determines the checkpoint based on event type:
   - `DONE` → all complete, nothing to recover.
   - `COMPLETED` (with WU ID) → that work unit is done. Resume from next.
   - `MERGED` → work unit implemented but not yet ticked in ticket.md. Tick and continue.
   - Any other event → the work unit is in progress or failed. Check for stale worktrees.
3. Scans for stale worktrees matching `.worktrees/dispatch-*`.
4. Prompts the user to **Resume**, **Abort**, or **Restart**.
