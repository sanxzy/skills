# Plan Progress Log Format

The authoritative per-feature workflow and recovery log lives at:

```text
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/progress.md
```

It is pure Markdown, append-only, and written only by the main `generate-plan` host. `plan-scout` agents never read it for orchestration and never write it.

## Purpose

The log must provide:

1. A lean chronological account of every workflow event.
2. Enough normalized feature and planning context to resume without relying on the original live conversation.
3. Concurrency protection for one feature plan.
4. An immutable history of fresh attempts, resumes, pauses, cancellations, overwrites, and completions.

No separate state file exists. `progress.md` must contain all recovery-critical state.

## File Structure

```markdown
# Plan Generation Progress — <backlog_name> — F<NNN>

## Round 001

- 01 | workflow-started | mode=fresh; backlog=<backlog_name>; feature=F<NNN> | next: resolve-source
- 02 | source-resolved | feature=F<NNN>; title=<title>; source=<spec-md|conversation>; source-detail=<path-or-logical-source>; plan-dir=<path> | next: capture-context
- 03 | context-captured | outcome=<outcome>; actors=<actors>; stories=<stories>; in-scope=<scope>; out-of-scope=<scope>; dependencies=<deps-or-none>; language=<language>; repository=<greenfield-or-established|unknown> | next: classify-discovery
```

## Workflow Rounds

A workflow round is one plan generation or regeneration attempt.

- Fresh generation appends the next `Round NNN` section.
- Explicit resume continues the latest non-terminal round.
- Never rewrite, reorder, renumber, or delete historical events.
- Event numbering resets to `01` in every workflow round.
- The round number plus event number is the unique event identity.
- The round number determines scout report paths under `scouts/round-<RRR>/`.
- A fresh successful round overwrites canonical `plan.md`; no revision archive is created.

## Event Line Contract

Every event is exactly one line:

```text
- <NN> | <event-type> | <concise details> | next: <action-or-none>
```

Rules:

1. `<NN>` is a zero-padded, monotonic event number starting at `01` inside the round.
2. `<event-type>` is one fixed value from the vocabulary below.
3. `<concise details>` uses semicolon-separated `key=value` fields when practical.
4. Escape literal line breaks as spaces. Within values, escape `\` as `\\`, `|` as `\|`, `;` as `\;`, and `=` as `\=`. Never make one event span multiple lines.
5. `<action-or-none>` names the deterministic next action or `none`.
6. Do not use timestamps.
7. Do not use YAML frontmatter.
8. Append events immediately after the corresponding action or decision.
9. For parallel scouts, record lifecycle events in deterministic kebab-case topic order.
10. Keep details lean, but never omit information required to resume.
11. Never record secret values, credentials, tokens, private keys, session material, personal data, or sensitive environment contents. Use key names and `[REDACTED]` where sensitive context must be identified.

## Fixed Event Vocabulary

Use only these event types:

| Event Type | Required Details | Meaning |
|---|---|---|
| `workflow-started` | `mode`, `backlog`, `feature` | A workflow round began. |
| `source-resolved` | `feature`, `title`, `source`, `source-detail`, `plan-dir` | The single target feature and source were resolved. |
| `context-captured` | `outcome`, `actors`, `stories`, `in-scope`, `out-of-scope`, `dependencies`, `language`, `repository` | Normalized planning context was established or updated after discussion. |
| `existing-plan-dispositioned` | `disposition`, `existing` | Existing canonical `plan.md` handling was recorded. Use `disposition=overwrite`. |
| `discovery-classified` | `mode`, `basis`, `repository` | Host light discovery classified greenfield or established mode. |
| `scout-wave-planned` | `cycle`, `wave`, `topics`, `coverage-targets`, `briefs` | A bounded set of scout scopes was planned. |
| `scout-started` | `cycle`, `wave`, `topic`, `scope`, `report`, `attempt` | A scout was delegated. |
| `scout-completed` | `cycle`, `wave`, `topic`, `report` | A scout returned a completed canonical report. |
| `scout-blocked` | `cycle`, `wave`, `topic`, `report`, `reason`, `attempt` | A scout was blocked or rejected. Use `report=none` when rejection occurred before a report was written. |
| `coverage-evaluated` | `result`, `covered`, `uncovered`, `conflicts`, `unknowns`, `stale`, `reports` | Collective planning evidence coverage was evaluated. |
| `ambiguity-handoff-started` | `questions`, `affected-topics`, `handoff-mode` | Plan-affecting ambiguity was handed to `discussion`. |
| `ambiguity-handoff-completed` | `decisions`, `affected-topics`, `transcript` | Discussion reached explicit shared understanding. |
| `scope-updated` | `reason`, `affected-topics`, `stale-topics`, `retained-topics` | Clarification changed scope and evidence validity was recorded. |
| `plan-synthesized` | `phases`, `decisions`, `greenfield` | Candidate plan content was synthesized before quality gate. |
| `quality-gate-evaluated` | `result`, `defects`, `next-remediation` | Mandatory plan quality gate was evaluated. |
| `plan-write-verified` | `path`, `phases`, `overwritten`, `scout-reports` | Canonical `plan.md` was written, re-read, and verified. |
| `workflow-paused` | `reason`, `pending`, `resume-requires` | Work stopped in a resumable state. Add `authorization-needed` when relevant. |
| `workflow-resumed` | `from-event`, `reports-reused`, `next-action`; optional `authorization` | A non-terminal workflow round resumed or another discovery cycle was authorized. |
| `workflow-cancelled` | `reason` | The workflow round ended without a finalized plan. |
| `workflow-completed` | `artifact`, `phases`, `overwritten`, `scout-reports` | The workflow round completed successfully. |

Do not invent additional event types. Put unusual detail in key-value fields.

## Terminal and Non-terminal State

Terminal events:

- `workflow-cancelled`
- `workflow-completed`

Every other event is non-terminal.

A `workflow-paused` event remains active and reserves the feature plan for explicit resume.

When the latest workflow round is non-terminal and the user did not explicitly request resume, do not start another round. Ask the user to resume or cancel the active round first.

## Deterministic Ordering for Parallel Scouts

The host remains the sole progress writer.

For one scout wave:

1. Sort topics lexicographically by kebab-case topic.
2. Append `scout-wave-planned` with the complete topic set and coverage targets.
3. Append `scout-started` for each topic in sorted order before delegation.
4. Delegate scouts in parallel when supported, otherwise sequentially.
5. Wait for every result in the batch.
6. Append `scout-completed` or `scout-blocked` for each topic in the same sorted order, regardless of actual completion order.

## Discovery Cycles and Scout Waves

One authorized discovery cycle permits:

- Up to five scouts per wave.
- Up to three waves.
- Up to fifteen total scout invocations.

The progress log must include `cycle` and `wave` on every scout lifecycle event.

Count discovery budget from `scout-started` events. In `coverage-evaluated`, `reports` counts readable canonical `.md` report files only. A rejected invocation recorded with `report=none` consumes budget but does not increase `reports`.

Retries after completed or blocked discovery and narrower replacements use unique topic names. A corrected re-delegation after input rejection keeps the original planned topic and report path because discovery never began, but it must append another `scout-started` event with an incremented attempt.

When another bounded cycle is authorized, continue the same workflow round and increment `cycle` while wave numbering restarts at `1`.

## Minimum Context for Recovery

At least one `source-resolved` event in the active workflow round must contain:

- Feature identifier.
- Feature title.
- Source type.
- Source detail sufficient for recovery.
- Plan directory.

At least one `context-captured` event in the active workflow round must contain:

- Desired outcome.
- Actors.
- User stories or behavior labels.
- In-scope behavior.
- Out-of-scope behavior.
- Dependencies or `none`.
- Artifact language.
- Repository mode.

After `discussion`, append a new `context-captured` event with clarified values. The latest value supersedes earlier context for recovery; earlier events remain immutable history.

## Recovery Algorithm

On explicit resume:

1. Read the latest workflow round.
2. Reject resume when its latest event is terminal.
3. Reconstruct source identity from the latest `source-resolved` event.
4. Reconstruct normalized context from the latest `context-captured` event.
5. Build the scout ledger from all scout lifecycle events; treat `report=none` as an input rejection with no artifact to read.
6. Trust and read reports named by completed events and blocked events whose `report` is not `none`.
7. Determine covered, uncovered, stale, conflicted, and unknown areas from the latest `coverage-evaluated` and `scope-updated` events.
8. Determine pending discussion from unmatched `ambiguity-handoff-started` events.
9. Determine quality and write state from the latest `quality-gate-evaluated` and `plan-write-verified` events.
10. Append `workflow-resumed` describing the checkpoint and next action.
11. Continue from `next` on the latest event unless on-disk canonical artifacts prove that action already completed; when reconciling, append an event documenting the observed completion before continuing.

### Recovery by last event

| Last Event | Recovery Action |
|---|---|
| `workflow-started` | Resolve source and capture context. |
| `source-resolved` | Capture normalized context. |
| `context-captured` | Record existing plan disposition and classify discovery mode. |
| `existing-plan-dispositioned` | Classify discovery mode. |
| `discovery-classified` | Plan scouts or synthesize for validated greenfield mode. |
| `scout-wave-planned` | Check report paths, then delegate scouts without completed reports. |
| `scout-started` | Check assigned report path; record completion when valid, otherwise re-delegate under failure rules. |
| `scout-completed` or `scout-blocked` | Read all available wave reports, reconcile unmatched planned topics, and complete the wave ledger. |
| `coverage-evaluated` | Follow its `next` action: scout, discuss, synthesize, or request authorization. |
| `ambiguity-handoff-started` | Resume or complete `discussion`; do not synthesize. |
| `ambiguity-handoff-completed` | Capture clarified context, then revalidate affected evidence. |
| `scope-updated` | Replace stale evidence or continue synthesis when coverage remains complete. |
| `plan-synthesized` | Apply the quality gate. |
| `quality-gate-evaluated` | If passed, write artifact; if failed, follow defect path. |
| `plan-write-verified` | Append `workflow-completed`. |
| `workflow-paused` | Satisfy the recorded `resume-requires` action. |
| `workflow-resumed` | Follow its `next-action`. |
| `workflow-cancelled` or `workflow-completed` | Terminal; do not resume. |

## Example

```markdown
# Plan Generation Progress — account-recovery — F003

## Round 001

- 01 | workflow-started | mode=fresh; backlog=account-recovery; feature=F003 | next: resolve-source
- 02 | source-resolved | feature=F003; title=Password recovery; source=spec-md; source-detail=_xzy-ai/sprints/account-recovery/specs/features/003/spec.md; plan-dir=_xzy-ai/sprints/account-recovery/plans/features/003 | next: capture-context
- 03 | context-captured | outcome=customers recover account access safely; actors=registered customers; stories=US001,US002; in-scope=request reset, verify identity, set replacement credential; out-of-scope=account registration; dependencies=notification delivery; language=English; repository=established | next: classify-discovery
- 04 | existing-plan-dispositioned | disposition=overwrite; existing=none | next: classify-discovery
- 05 | discovery-classified | mode=established; basis=top-level app and tests present; repository=established | next: plan-scouts
- 06 | scout-wave-planned | cycle=1; wave=1; topics=implementation-seams,testing-seams; coverage-targets=stable contracts, vertical slice boundaries, verification strategy; briefs=implementation-seams{scope:feature-relevant implementation boundaries,report:_xzy-ai/sprints/account-recovery/plans/features/003/scouts/round-001/implementation-seams.md},testing-seams{scope:behavioral verification seams,report:_xzy-ai/sprints/account-recovery/plans/features/003/scouts/round-001/testing-seams.md} | next: start-scouts
- 07 | scout-started | cycle=1; wave=1; topic=implementation-seams; scope=feature-relevant implementation boundaries; report=_xzy-ai/sprints/account-recovery/plans/features/003/scouts/round-001/implementation-seams.md; attempt=1 | next: await-wave
- 08 | scout-started | cycle=1; wave=1; topic=testing-seams; scope=behavioral verification seams; report=_xzy-ai/sprints/account-recovery/plans/features/003/scouts/round-001/testing-seams.md; attempt=1 | next: await-wave
- 09 | scout-completed | cycle=1; wave=1; topic=implementation-seams; report=_xzy-ai/sprints/account-recovery/plans/features/003/scouts/round-001/implementation-seams.md | next: complete-wave
- 10 | scout-completed | cycle=1; wave=1; topic=testing-seams; report=_xzy-ai/sprints/account-recovery/plans/features/003/scouts/round-001/testing-seams.md | next: check-coverage
- 11 | coverage-evaluated | result=complete; covered=stable contracts, vertical slice boundaries, verification strategy; uncovered=none; conflicts=none; unknowns=none; stale=none; reports=2 | next: synthesize-plan
- 12 | plan-synthesized | phases=4; decisions=5; greenfield=false | next: quality-gate
- 13 | quality-gate-evaluated | result=passed; defects=none; next-remediation=none | next: write-plan
- 14 | plan-write-verified | path=_xzy-ai/sprints/account-recovery/plans/features/003/plan.md; phases=4; overwritten=false; scout-reports=2 | next: complete-workflow
- 15 | workflow-completed | artifact=_xzy-ai/sprints/account-recovery/plans/features/003/plan.md; phases=4; overwritten=false; scout-reports=2 | next: none
```
