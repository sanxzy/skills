# Ticket Progress Log Format

The authoritative workflow and recovery log lives at:

```text
_xzy-ai/sprints/<backlog_name>/tickets/progress.md
```

It is pure Markdown, append-only, and written only by the main `ticket` host. `ticket-scout` agents never write it. Scout reports persist their codebase or reference evidence; this log records coordinator lifecycle, normalized context, evidence mode, recovery state, and artifact verification.

## Purpose

The log must provide:

1. a chronological account of each ticket-generation round;
2. enough source, scope, and decomposition context to resume without the live conversation;
3. concurrency protection for one proposal/backlog ticket set;
4. an immutable history of fresh attempts, resumes, pauses, cancellations, archival, and completions;
5. evidence of how the final ticket count, dependency order, and source proposal were determined.

No separate workflow state file exists. Keep all recovery-critical state in `progress.md`.

## File structure

```markdown
# Ticket Generation Progress — <backlog_name>

## Round 001

- 01 | workflow-started | mode=fresh; backlog=<backlog_name> | next: resolve-source
- 02 | source-resolved | title=<proposal-title>; source=<path>; backlog=<backlog_name>; ticket-dir=<path> | next: capture-context
- 03 | context-captured | outcome=<outcome>; actors=<actors>; capabilities=<ids>; in-scope=<scope>; out-of-scope=<scope>; language=<language>; discovery=<mode>; reference-mode=<proposal-only-or-reference-aware>; reference-scope=<scope-or-none>; reference-notes=<escaped-verbatim-notes-or-none> | next: check-existing-set
```

## Workflow rounds

A workflow round is one ticket-set generation, regeneration, or explicit resume attempt.

- Fresh generation appends the next `Round NNN` section.
- Explicit resume continues the latest non-terminal round.
- Never rewrite, reorder, renumber, or delete historical events.
- Event numbering resets to `01` inside each round.
- The round number plus event number is the unique event identity.
- Scout reports use the round number in `scouts/round-<RRR>/`.
- A regenerated set archives the exact previous canonical index and ticket files before replacement.

## Event line contract

Every event is exactly one line:

```text
- <NN> | <event-type> | <concise details> | next: <action-or-none>
```

Rules:

1. `<NN>` is a zero-padded, monotonic event number starting at `01` inside the round.
2. `<event-type>` must be one value from the fixed vocabulary below.
3. Use semicolon-separated `key=value` fields when practical.
4. Escape literal line breaks as spaces. Within values, escape `\\` as `\\\\`, `|` as `\\|`, `;` as `\\;`, and `=` as `\\=`. Never make one event span multiple lines.
5. `<action-or-none>` names the deterministic next action.
6. Do not use timestamps or YAML frontmatter.
7. Append an event immediately after its action or decision.
8. For parallel scouts, record lifecycle events in lexicographic topic order, not completion order.
9. Keep details lean but include every value needed to resume.
10. Never record secrets, credentials, tokens, private keys, session material, personal data, or sensitive environment values. Use names and `[REDACTED]` when needed.

## Fixed event vocabulary

Use only these event types:

| Event type | Required details | Meaning |
|---|---|---|
| `workflow-started` | `mode`, `backlog`, `source` | A fresh workflow round began. |
| `source-resolved` | `title`, `source`, `backlog`, `ticket-dir` | One valid proposal and its output identity were resolved. |
| `context-captured` | `outcome`, `actors`, `capabilities`, `in-scope`, `out-of-scope`, `language`, `discovery`, `reference-mode`, `reference-scope`, optional `reference-notes` | Normalized proposal context, evidence mode, and reference instructions were established or clarified. |
| `existing-ticket-set-dispositioned` | `disposition`, `existing`, optional `revision` | Existing canonical set was kept, archived for overwrite, or confirmed absent. |
| `discovery-classified` | `mode`, `basis`, `project-root`, `reference-mode`, `reference-scope` | Evidence mode and proposal-only, greenfield, or established discovery mode were recorded. |
| `scout-wave-planned` | `cycle`, `wave`, `topics`, `coverage-targets`, `briefs` | A bounded scout wave was planned. |
| `scout-started` | `cycle`, `wave`, `topic`, `scope`, `report`, `attempt`, `resume` | A scout was delegated with explicit fresh/resume intent. |
| `scout-completed` | `cycle`, `wave`, `topic`, `report` | A scout returned a completed report. |
| `scout-blocked` | `cycle`, `wave`, `topic`, `report`, `reason`, `attempt` | A scout was blocked or rejected. Use `report=none` for pre-report rejection. |
| `coverage-evaluated` | `result`, `covered`, `uncovered`, `conflicts`, `unknowns`, `reports` | Evidence coverage, including required reference evidence when reference-aware, was evaluated. |
| `ambiguity-handoff-started` | `questions`, `affected-topics`, `handoff-mode` | Ticket-affecting ambiguity was handed to `discussion`. |
| `ambiguity-handoff-completed` | `decisions`, `affected-topics`, `transcript` | Clarification reached explicit shared understanding. |
| `scope-updated` | `reason`, `affected-topics`, `stale-topics`, `retained-topics` | Clarification changed interpretation and evidence validity. |
| `tickets-synthesized` | `tickets`, `required`, `optional`, `edges`, `split-check`, optional `references` | Candidate ticket set, dependency graph, and reference coverage were synthesized before the quality gate. |
| `quality-gate-evaluated` | `result`, `defects`, `next-remediation` | Mandatory ticket quality gate was evaluated. |
| `revision-archived` | `revision`, `index`, `ticket-count` | Existing canonical set was archived and verified before overwrite. |
| `ticket-write-verified` | `index`, `tickets`, `revision`, `scout-reports` | Index and every current ticket were written, re-read, and verified. |
| `workflow-paused` | `reason`, `pending`, `resume-requires` | Work stopped in a resumable state. |
| `workflow-resumed` | `from-event`, `reports-reused`, `next-action`; optional `authorization` | A non-terminal round resumed. |
| `workflow-cancelled` | `reason` | The round ended without a current finalized ticket set. |
| `workflow-completed` | `index`, `tickets`, `revision`, `scout-reports` | The round completed successfully. |

Do not invent event types. Put unusual detail in escaped key-value fields.

## Terminal and non-terminal state

Terminal events are:

- `workflow-cancelled`;
- `workflow-completed`.

Every other event is non-terminal. A `workflow-paused` event reserves the source/backlog for explicit resume. When the latest round is non-terminal and the user did not explicitly request resume, do not start a fresh overlapping round.

## Deterministic scout waves

For each wave:

1. sort topics lexicographically;
2. validate every brief, codebase/reference path, scope, and boolean `resume` before any delegation;
3. append one `scout-wave-planned` event;
4. append `scout-started` events in sorted order;
5. delegate independent scouts in parallel when supported;
6. wait for all results;
7. append terminal `scout-completed` or `scout-blocked` events in the same sorted order;
8. retain `in-progress` reports under their open `scout-started` event.

One authorized discovery cycle allows at most five scouts per wave, three waves, and fifteen total invocations. Retries and narrower replacements consume the same budget. A rejected invocation with `report=none` consumes budget but does not increase `reports`.

## Minimum recovery context

At least one active-round `source-resolved` event must contain:

- the proposal title;
- the verified source path;
- the normalized backlog name;
- the managed ticket directory.

At least one active-round `context-captured` event must contain:

- the expected product outcome;
- actors and authority;
- required and optional capability identifiers;
- in-scope and out-of-scope boundaries;
- proposal language;
- discovery mode;
- evidence mode (`proposal-only` or `reference-aware`);
- exact reference scope or `none`;
- any additional user-supplied reference instructions or notes, escaped verbatim when present.

In reference-aware greenfield mode, if the codebase has no relevant implementation and the reference scope is not clear enough to define a bounded scout question, append `workflow-paused` with `reason=reference-scope-unclear`, record the pending clarification, and set `resume-requires=user-reference-scope-clarification`. Do not start a scout or write ticket artifacts before the user clarifies the scope.

After discussion, append a new `context-captured` event with clarified values. Earlier events remain immutable history; the latest normalized context is authoritative for recovery.

## Recovery algorithm

On explicit resume:

1. read the latest round;
2. reject resume when its latest event is terminal;
3. reconstruct source and backlog identity from `source-resolved`;
4. reconstruct normalized proposal context, evidence mode, and reference scope from the latest `context-captured`;
5. build the scout ledger from all scout lifecycle events;
6. read completed reports and matching `in-progress` reports named by the ledger;
7. read the latest `coverage-evaluated`, `scope-updated`, `tickets-synthesized`, and `quality-gate-evaluated` events;
8. determine whether archival, writing, verification, discussion, or scouting is pending;
9. append `workflow-resumed` with the checkpoint and deterministic next action;
10. continue without repeating completed actions or overwriting terminal reports.

### Recovery by last event

| Last event | Recovery action |
|---|---|
| `workflow-started` | Resolve and validate the proposal. |
| `source-resolved` | Capture context and inspect existing artifacts. |
| `context-captured` | Disposition an existing ticket set and classify discovery. |
| `existing-ticket-set-dispositioned` | Classify discovery or plan proposal-only or reference-aware synthesis. |
| `discovery-classified` | Plan codebase scouts, reference-only scouts, or record proposal-only coverage. |
| `scout-wave-planned` | Validate report states, reference scopes, and delegate fresh/resumed scouts. |
| `scout-started` | Resume matching in-progress reports or reconcile terminal results. |
| `scout-completed` or `scout-blocked` | Complete the wave ledger and evaluate coverage. |
| `coverage-evaluated` | Scout, discuss, synthesize, or request authorization as recorded. |
| `ambiguity-handoff-started` | Complete `discussion`; do not synthesize. |
| `ambiguity-handoff-completed` | Capture clarified context and revalidate affected evidence. |
| `scope-updated` | Replace stale evidence or continue when coverage is complete. |
| `tickets-synthesized` | Apply the quality gate. |
| `quality-gate-evaluated` | Archive/write when passed; follow remediation when failed. |
| `revision-archived` | Write and verify the current set. |
| `ticket-write-verified` | Append `workflow-completed`. |
| `workflow-paused` | Satisfy its recorded `resume-requires` action. |
| `workflow-resumed` | Follow its `next-action`. |
| `workflow-cancelled` or `workflow-completed` | Terminal; do not resume. |

## Granularity evidence

When recording `tickets-synthesized`, include enough detail to show that decomposition was not compressed for convenience:

- `tickets=<count>`;
- `required=<count>`;
- `optional=<count>`;
- `edges=<count>`;
- `split-check=recursive-pass`;
- `coverage=<core-outcome-and-all-required-capabilities>`.

A high ticket count is not a defect. A ticket set may be long when that is required to preserve small, independently verifiable outcomes.
