# Assignment Format

The coordinator writes one assignment per phase to:

```text
_xzy-ai/sprints/<backlog>/dispatch/assignments/phase-<NNN>/assignment.md
```

The assignment is the authoritative handoff from coordinator to worker and reviewers. It is written in the main checkout, not inside the phase worktree.

## Required Structure

```markdown
# Dispatch Assignment — Phase <NNN>: <Title>

**Backlog:** `<backlog>`
**Feature:** `<FNNN or unknown>`
**Phase:** `<NNN>`
**Worker mode:** `default | tdd`
**Worker:** `dispatch-code-worker | dispatch-code-with-ui-worker`
**Source plan:** `<path or none>`
**Worktree:** `<absolute path>`
**Status:** `assigned | retry`

## User background

<What the user wants and why this phase is being dispatched.>

## Prior process context

<What has already happened in planning or earlier dispatch cycles. Include prior approved phases and relevant report paths. Use `None` if this is the first phase and no prior context exists.>

## Architectural decisions

<Relevant durable decisions copied from plan.md when available. Use `None` if unavailable.>

## Phase content

### User stories covered

<Exact value from plan.md when available.>

### What to build

<Exact phase What to build content from plan.md or normalized input.>

### Acceptance criteria

- [ ] <criterion>
- [ ] <criterion>

## Retry context

<If this is a fix cycle, list ACS/security+quality/advisor reports the worker must read. Use `None` on first attempt.>

## Required report paths

- Worker report: `<path>`
- ACS review report: `<path>`
- Security+quality review report: `<path>`
- Advisor report directory: `<path>`

## Coordinator constraints

- The coordinator has not performed codebase discovery.
- The worker must perform implementation discovery inside the assigned worktree.
- Reviewers must independently verify the result.
- Code changes must stay in the assigned worktree until approved and merged.
```

## Rules

1. Preserve phase wording from `plan.md` where available.
2. Do not add coordinator-discovered codebase facts.
3. Include enough background for workers and reviewers to understand the phase without reopening the full conversation.
4. Keep unresolved questions out of the assignment. Resolve missing behavior through discussion before dispatch.
5. On retries, keep the original phase content unchanged and add reviewer/advisor report paths under `Retry context`.
