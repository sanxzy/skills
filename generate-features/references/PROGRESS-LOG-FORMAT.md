# Progress Log Format

The authoritative workflow and recovery log lives at:

```text
_xzy-ai/sprints/<backlog_name>/feats/progress.md
```

It is pure Markdown, append-only, and written only by the main `generate-features` host. `feat-scout` agents never write it.

## Purpose

The log must provide:

1. A lean chronological account of every workflow event.
2. Enough normalized context to resume without relying on the original live conversation.
3. Concurrency protection for one backlog.
4. An immutable history of fresh attempts, resumes, pauses, cancellations, and completions.

No separate context or state file exists. `progress.md` must contain all recovery-critical state.

## File Structure

```markdown
# Feature Generation Progress — <backlog_name>

## Round 001

- 01 | round-started | mode=fresh; backlog=<backlog_name> | next: capture-context
- 02 | context-captured | goal=<goal>; users=<users>; outcome=<outcome>; in-scope=<scope>; out-of-scope=<scope>; sources=<paths-or-conversation>; language=<language>; repository=<greenfield-or-established> | next: plan-discovery

## Round 002

- 01 | round-started | mode=fresh; backlog=<backlog_name> | next: capture-context
```

## Workflow Rounds

A workflow round is one generation attempt.

- Fresh generation appends the next `Round NNN` section.
- Explicit resume continues the latest non-terminal round.
- Never rewrite, reorder, renumber, or delete historical events.
- Event numbering resets to `01` in every workflow round.
- The round number plus event number is the unique event identity.
- Workflow rounds are distinct from scout waves.

A fresh round may delete stale scout report files, but it must preserve this log.

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
| `round-started` | `mode`, `backlog` | A fresh workflow round began. |
| `context-captured` | `goal`, `users`, `outcome`, `in-scope`, `out-of-scope`, `sources`, `language`, `repository` | Normalized context was established or updated after discussion. |
| `scout-wave-planned` | `cycle`, `wave`, `topics`, `coverage-targets`, `briefs` | A bounded set of scout scopes was planned; `briefs` records each topic's scope, questions, and report path compactly enough for recovery. |
| `scout-started` | `cycle`, `wave`, `topic`, `scope`, `report` | A scout was delegated. |
| `scout-completed` | `cycle`, `wave`, `topic`, `report` | A scout returned a completed canonical report. |
| `scout-blocked` | `cycle`, `wave`, `topic`, `report`, `reason`, `attempt` | A scout was blocked or rejected. Use `report=none` when rejection occurred before a report was written. |
| `coverage-checked` | `result`, `covered`, `uncovered`, `conflicts`, `unknowns`, `reports` | Collective evidence coverage was evaluated. |
| `discussion-started` | `questions`, `affected-topics`, `handoff-mode` | Feature-affecting ambiguity was handed to `discussion`. |
| `discussion-completed` | `decisions`, `affected-topics`, `transcript` | Discussion reached explicit shared understanding; use `transcript=conversation` when no file was written. |
| `quality-checked` | `result`, either `features` or `result-detail=no-outstanding-features`, `defects` | The internal finalization gate was evaluated. |
| `artifact-written` | `path`, `features` or `result=no-outstanding-features`, `scout-reports` | The immutable final artifact was written and verified. |
| `paused` | `reason`, `pending`, `resume-requires` | Work stopped in a resumable state; add `uncovered` or `authorization-needed` when relevant. |
| `resumed` | `from-event`, `reports-reused`, `next-action`; optional `authorization` | The latest non-terminal workflow round resumed or another bounded discovery cycle was authorized. |
| `cancelled` | `reason` | The workflow round ended without a feature artifact. |
| `round-completed` | `artifact`, `features` or `result=no-outstanding-features`, `scout-reports` | The workflow round completed successfully. |

Do not invent additional event types. Put unusual detail in the event's key-value fields.

## Terminal and Non-terminal State

Terminal events:

- `cancelled`
- `round-completed`

Every other event is non-terminal.

A `paused` event remains active and reserves the backlog for explicit resume.

When the latest workflow round is non-terminal and the user did not explicitly request resume, do not start another round. Ask the user to resume the active round or choose a new backlog.

## Deterministic Ordering for Parallel Scouts

The host remains the sole writer.

For one scout wave:

1. Sort topics lexicographically by kebab-case topic.
2. Append `scout-wave-planned` with the complete topic set and coverage targets.
3. Append `scout-started` for each topic in sorted order before delegation.
4. Delegate scouts in parallel when supported, otherwise sequentially.
5. Wait for every result in the batch.
6. Append `scout-completed` or `scout-blocked` for each topic in the same sorted order, regardless of actual completion time.

This preserves reproducible event numbering without allowing concurrent report agents to write progress state.

## Discovery Cycles and Scout Waves

One authorized discovery cycle permits:

- Up to five scouts per wave.
- Up to three waves.
- Up to fifteen total scout invocations.

The progress log must include `cycle` and `wave` on every scout lifecycle event.

Count discovery budget from `scout-started` events. In `coverage-checked`, `reports` counts readable canonical `.md` report files only; a rejected invocation recorded with `report=none` consumes budget but does not increase `reports`.

Retries after completed or blocked discovery and narrower replacements use unique topic names. A corrected re-delegation after input rejection keeps the original planned topic and report path because discovery never began, but it must append another `scout-started` event with an incremented attempt so budget accounting remains exact.

When another bounded cycle is authorized, continue the same workflow round and increment `cycle` while wave numbering restarts at `1`.

## Minimum Context for Recovery

At least one `context-captured` event in the active workflow round must contain:

- Product goal or problem.
- Intended users or stakeholders.
- Desired outcome.
- In-scope boundaries.
- Out-of-scope boundaries.
- Explicit input or source artifact paths, or `conversation` when no artifact exists.
- Artifact language.
- Repository mode: `greenfield` or `established`.

After `discussion`, append a new `context-captured` event with the clarified values. The latest value supersedes earlier context for recovery; earlier events remain immutable history.

## Recovery Algorithm

On explicit resume:

1. Read the latest workflow round.
2. Reject resume when its latest event is terminal.
3. Reconstruct normalized context from the latest `context-captured` event.
4. Build the scout ledger from all `scout-started`, `scout-completed`, and `scout-blocked` events; treat `report=none` as an input rejection with no artifact to read.
5. Trust and read reports named by completed events and blocked events whose `report` is not `none`.
6. Determine covered and uncovered areas from the latest `coverage-checked` event.
7. Determine pending discussion from unmatched `discussion-started` events.
8. Determine quality or artifact state from the latest `quality-checked` and `artifact-written` events.
9. Append `resumed` describing the checkpoint and next action.
10. Continue from `next` on the latest event unless on-disk canonical artifacts prove that action already completed; when reconciling, append an event documenting the observed completion before continuing.

### Recovery by last event

| Last Event | Recovery Action |
|---|---|
| `round-started` | Capture normalized context. |
| `context-captured` | Determine discovery mode and plan scouting, or synthesize for a validated greenfield run. |
| `scout-wave-planned` | Check report paths, then delegate scouts without completed reports. |
| `scout-started` | Check the assigned report path; record completion when valid, otherwise re-delegate under failure rules. |
| `scout-completed` or `scout-blocked` | Read all available wave reports, skip `report=none` rejection events, reconcile unmatched planned topics, and complete the wave ledger. |
| `coverage-checked` | Follow its `next` action: scout, discuss, synthesize, or request authorization. |
| `discussion-started` | Resume or complete `discussion`; do not synthesize. |
| `discussion-completed` | Capture clarified context, then revalidate affected evidence. |
| `quality-checked` | If passed, write artifact; if failed, follow the recorded defect path. |
| `artifact-written` | Verify artifact, then append `round-completed`. |
| `paused` | Satisfy the recorded `resume-requires` action: obtain authorization or clarification, complete missing discovery, correct coordinator inputs, or retry the verified artifact write. |
| `resumed` | Follow its `next-action`. |
| `cancelled` or `round-completed` | Terminal; do not resume. |

## Example: Established Repository

```markdown
# Feature Generation Progress — account-recovery

## Round 001

- 01 | round-started | mode=fresh; backlog=account-recovery | next: capture-context
- 02 | context-captured | goal=restore account access safely; users=registered customers; outcome=customers recover access without support intervention; in-scope=request reset, verify identity, set replacement credential; out-of-scope=account registration; sources=conversation; language=English; repository=established | next: plan-discovery
- 03 | scout-wave-planned | cycle=1; wave=1; topics=credential-reset,email-delivery; coverage-targets=recovery journey, delivery outcomes; briefs=credential-reset{scope:request through credential replacement,questions:current success and failure behavior,report:_xzy-ai/sprints/account-recovery/feats/scouts/credential-reset.md},email-delivery{scope:recovery notification delivery,questions:delivery and failure outcomes,report:_xzy-ai/sprints/account-recovery/feats/scouts/email-delivery.md} | next: start-scouts
- 04 | scout-started | cycle=1; wave=1; topic=credential-reset; scope=request through credential replacement; report=_xzy-ai/sprints/account-recovery/feats/scouts/credential-reset.md | next: await-wave
- 05 | scout-started | cycle=1; wave=1; topic=email-delivery; scope=recovery notification delivery and failure states; report=_xzy-ai/sprints/account-recovery/feats/scouts/email-delivery.md | next: await-wave
- 06 | scout-completed | cycle=1; wave=1; topic=credential-reset; report=_xzy-ai/sprints/account-recovery/feats/scouts/credential-reset.md | next: complete-wave
- 07 | scout-completed | cycle=1; wave=1; topic=email-delivery; report=_xzy-ai/sprints/account-recovery/feats/scouts/email-delivery.md | next: check-coverage
- 08 | coverage-checked | result=complete; covered=recovery journey, delivery outcomes; uncovered=none; conflicts=none; unknowns=none; reports=2 | next: synthesize
- 09 | quality-checked | result=passed; features=2; defects=none | next: write-artifact
- 10 | artifact-written | path=_xzy-ai/sprints/account-recovery/features.md; features=2; scout-reports=2 | next: complete-round
- 11 | round-completed | artifact=_xzy-ai/sprints/account-recovery/features.md; features=2; scout-reports=2 | next: none
```

## Example: Greenfield Generation

A greenfield repository may skip scouts when conversation context is sufficient:

```markdown
# Feature Generation Progress — operator-alerting

## Round 001

- 01 | round-started | mode=fresh; backlog=operator-alerting | next: capture-context
- 02 | context-captured | goal=notify operators about service-impacting conditions; users=operators; outcome=operators receive actionable alerts and understand recovery; in-scope=alert delivery, acknowledgement, recovery notification; out-of-scope=service remediation automation; sources=conversation; language=English; repository=greenfield | next: check-coverage
- 03 | coverage-checked | result=complete; covered=stated operator journey; uncovered=none; conflicts=none; unknowns=none; reports=0; reason=greenfield-context-sufficient | next: synthesize
- 04 | quality-checked | result=passed; features=2; defects=none | next: write-artifact
- 05 | artifact-written | path=_xzy-ai/sprints/operator-alerting/features.md; features=2; scout-reports=0 | next: complete-round
- 06 | round-completed | artifact=_xzy-ai/sprints/operator-alerting/features.md; features=2; scout-reports=0 | next: none
```
