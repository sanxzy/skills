# Ticket Format

This document defines the canonical local ticket set produced from one proposal. It keeps each ticket independently actionable while preserving the proposal's product behavior and dependency graph.

## Artifact set

For backlog `<backlog_name>`, write:

```text
_xzy-ai/sprints/<backlog_name>/tickets.md
_xzy-ai/sprints/<backlog_name>/tickets/<TNNN>-<slug>.md
```

The index is the canonical entry point. Each ticket file is a durable implementation contract. Workflow `progress.md`, scout reports, and archived revisions are not tickets and must not appear in the current ticket list.

Do not write one giant ticket containing all work. Do not compress one feature or proposal capability into one ticket when it contains several independently verifiable outcomes. Prefer many small complete tickets, even when the resulting ticket set and index are long. Do not write a technical checklist split by database, API, UI, infrastructure, or test layer.

## Reference-aware citations

Reference-aware mode is opt-in and is entered only when the user explicitly asks to use references as a source of truth. The proposal remains the product contract; references provide evidence for ticket sequencing, dependencies, contracts, risks, verification seams, or implementation patterns and never silently change product behavior.

- Any existing regular file outside the resolved project codebase root may be cited as read-only reference evidence.
- A citation is either a workspace-root-relative path using forward slashes with no leading `/`, `./`, or `..` segments, or an absolute path that resolves outside the project codebase root. Symlinks are allowed only when they resolve to regular files outside that root.
- Use path-only citations in final artifacts, without line ranges or symbols. Inline citations may be wrapped in backticks; the path itself must remain the only citation value.
- The source proposal path in the index and ticket provenance is not a reference citation and is not repeated in `## References`.
- In reference-aware mode, cite substantive evidence-backed claims near the claim. Every inline citation in a ticket also appears in that ticket's `## References` section and in the index's deduplicated trailing `## References` section.
- When no references are used, each `## References` section contains exactly `None`, including proposal-only mode and reference-aware runs that proceed without citable evidence after user confirmation.
- Cited files are read-only inputs. Do not modify, move, rename, or delete them.
- Preserve any additional user-supplied reference instructions or notes verbatim in the applicable ticket/reference section; do not silently drop or paraphrase their substance.

## Index format

Use this exact top-level structure:

```markdown
# Tickets — <Proposal title>

> Source proposal: <workspace-relative proposal path>
> Backlog: <backlog_name>

## Source and scope

<The product outcome, primary actors, authority, in-scope boundary, out-of-scope boundary, and core success criterion.>

## Dependency order

| Order | Ticket | Title | Blocked by | Required or optional | Outcome |
|---|---|---|---|---|---|
| 1 | [T001](tickets/T001-<slug>.md) | <title> | None — can start immediately | Required | <outcome> |

## Tickets

- [T001 — <title>](tickets/T001-<slug>.md) — <one-line outcome>

## Traceability

| Proposal identifier | Covered by | Coverage note |
|---|---|---|
| `CAP-001` | `T001` | <how the ticket covers it> |

## References

<Union of all inline citable paths in the current index and ticket files, deduplicated and sorted, or `None` when no references are used.>
```

Rules:

1. Start ticket numbering at `T001` and continue without gaps.
2. List tickets in topological dependency order: every blocker appears before every ticket it blocks.
3. Use the same title, identifier, and filename slug in the dependency table, ticket list, and ticket file.
4. List every current ticket exactly once; do not list archived tickets as current.
5. Include every required proposal capability in traceability. Include optional capabilities only when they become explicit non-blocking tickets.
6. A proposal identifier may map to many tickets; traceability is many-to-many where the behavior requires it, not one capability to one ticket.
7. Include journey, state, interaction, and recovery identifiers when they materially constrain a ticket; do not force irrelevant identifiers into the table.
8. Explain every non-empty blocking edge with a concise product or contract reason in the relevant ticket file.
9. The index must remain understandable without the original conversation. The source proposal path is provenance, not a substitute for the copied outcome and scope.
10. Do not add implementation plans, technical file lists, function names, code snippets, or command transcripts. Qualifying external reference paths are allowed only under the citation rules above.

If the proposal has no required work, do not create an empty ticket set. Stop and report that the proposal has no outstanding implementation outcomes. The workflow may still retain its progress log, but no `tickets.md` with fabricated tickets is written.

## Per-ticket format

Every ticket file uses this structure:

```markdown
# T001 — <Ticket title>

> Source proposal: <proposal title>

**Required or optional:** Required

**Blocked by:** None — can start immediately

**Unblocks:** <ticket IDs or `None`>

## Proposal traceability

- Capabilities: `CAP-001`
- Journey steps: `J-01`
- States: `STATE-01`, `STATE-02`
- Interactions: `INT-001` or `None`
- Recovery scenarios: `REC-001` or `None`

## What to build

<One end-to-end, user-observable outcome delivered by this ticket.>

## Why this slice exists

<Why the outcome matters and why it is a valid independent slice.>

## Scope boundary

<What this ticket includes and what it deliberately leaves to later tickets.>

## Acceptance criteria

- [ ] <Observable success criterion>
- [ ] <Observable validation, empty, permission, or boundary criterion when relevant>
- [ ] <Observable failure and recovery criterion when relevant>

## Verification notes

<How an implementer or reviewer can demonstrate the outcome without relying on a particular implementation file.>

## Out of scope

- <Behavior intentionally left to another ticket or excluded by the proposal>

## References

<Relevant citable paths used by this ticket, one per line, or `None` when no reference is used.>
```

## Field rules

### Title

Use `# TNNN — <short outcome title>`. The title must name the actor-visible outcome, not a technical layer. Good titles describe a user result such as `Review an incomplete submission`; poor titles describe `Create database table` or `Build API endpoint`.

### Source proposal

Use the proposal title in each ticket. The index carries the verified workspace-relative source path. Do not make the ticket depend on reopening the proposal to understand its behavior.

### References

In reference-aware mode, cite relevant external reference paths in the ticket's substantive sections and repeat exactly those paths in the ticket's trailing `## References` section. The index's trailing `## References` section is the deduplicated, lexicographically sorted union of every inline citation in the index and all current ticket files. When no reference-aware evidence is used, each references section contains exactly `None`.

### Required or optional

Use `Required` for an outcome needed by the proposal's core success criterion. Use `Optional` only for behavior explicitly listed as optional in the proposal. Optional tickets must not block required tickets.

### Blocked by

Use one of:

- `None — can start immediately`;
- a comma-separated list of existing ticket IDs and titles;
- `External prerequisite — <observable prerequisite>` when the proposal names a prerequisite outside this ticket set.

Every listed blocker must be a genuine prerequisite for starting this ticket, not merely a related task or a preferred sequence. A ticket must not depend on an optional ticket unless the proposal explicitly makes that optional outcome a prerequisite.

### Unblocks

List the current ticket IDs that directly depend on this ticket, or `None`. This is a convenience check, not a second source of truth; it must agree with every dependent ticket's `Blocked by` field.

### Proposal traceability

Use only identifiers present in the source proposal. At least one `CAP-*` or another direct behavior identifier is required. Traceability explains why the ticket exists; it does not license adding behavior absent from the proposal.

### What to build

Describe one complete path through the product needed for the ticket's outcome. Include the actor, trigger, visible result, system response, state change, and final outcome. Include relevant uncertainty, authority, review, or correction behavior. Do not list implementation layers or files.

### Why this slice exists

Explain the independent value or prerequisite boundary in product terms. If the ticket is a prerequisite, state the observable capability it unlocks. Do not justify a ticket only by saying that a developer needs setup.

### Scope boundary

State the behavior included in this slice and the neighboring proposal behavior intentionally left for later tickets. Prevent overlap and hidden work. Do not turn the boundary into a task list.

### Acceptance criteria

Use unchecked Markdown checklist items. Criteria must be observable, testable, falsifiable, and scoped to this ticket. Name the trigger and the actor-visible result in each criterion so pass or fail can be decided without implementation knowledge. Use untestable adjectives such as fast, seamless, robust, full, efficient, or gracefully only alongside such an observable test. Include:

- the normal success path;
- invalid or incomplete input when relevant;
- empty, permission, authority, or boundary behavior when relevant;
- partial failure, preserved progress, retry, correction, cancellation, or fallback when relevant;
- preserved existing behavior or compatibility behavior when the ticket changes prior behavior, fixes a defect, or targets porting or parity;
- accessibility, privacy, security, reliability, or audit behavior when it materially affects the promised outcome.

Do not assert that a particular file, function, framework, endpoint, database, library, command, or test file exists. Do not copy every proposal sentence mechanically; slice the criteria to this ticket's outcome. Do not write umbrella criteria that hide several independently verifiable outcomes behind one checklist item.

### Verification notes

Describe a concise demonstration or behavioral verification path. It may mention a user flow, test seam, review observation, or acceptance session, but it must not prescribe a command transcript or implementation structure.

### Out of scope

List only neighboring behavior explicitly deferred or excluded. Every deferred behavior should be covered by another ticket or by the proposal's out-of-scope boundary. Do not use out-of-scope text to hide unresolved ambiguity.

## Granularity and expected-outcome test

Run this test for every proposal capability and every resulting ticket:

1. Can an actor name the ticket's outcome without technical vocabulary?
2. Does the ticket have a distinct trigger, visible result, and completion condition?
3. Does the slice cross every necessary implementation concern without describing those concerns as separate tasks?
4. Can it be demonstrated or verified once its listed blockers are complete?
5. Does it have its own meaningful acceptance criteria and recovery boundary?
6. Does the capability contain another independently verifiable outcome that should become a separate ticket?
7. Would combining this ticket with a neighbor hide a meaningful user decision, state, validation, or failure path?
8. Would splitting it create a fragment with no independent product value?
9. Does the union of the resulting tickets still cover the complete expected outcome and core success criterion?

If a capability still contains multiple independently verifiable outcomes, split it again. Do not stop at one ticket per capability, and do not merge valid slices merely to reduce the count or shorten the artifact. There is no artificial maximum ticket count, phase count, or document length; behavioral completeness and small scope are the constraints.

## Dependency-graph test

Before finalization:

- all ticket IDs are unique and continuous;
- every `Blocked by` reference resolves to a current ticket or an explicitly named external prerequisite;
- every `Unblocks` reference resolves to a current ticket;
- no ticket blocks itself;
- no cycle exists;
- blockers precede dependents in the index;
- independent frontier tickets remain parallel;
- optional tickets do not block required tickets;
- the index and per-ticket edges agree exactly;
- reference-aware citations use only qualifying external regular-file paths, every inline citation is listed in the appropriate references section, and the index union is deduplicated and sorted.

## Language and durability

Use the proposal's language and preserve its product vocabulary. Keep the current ticket files self-contained and implementation-agnostic. The ticket set may mention stable product contracts, permissions, state names, and domain terms from the proposal, but must not prescribe concrete source files, functions, signatures, code, or infrastructure. Reference-aware citations are the only allowed exception for qualifying external file paths, and they must remain read-only evidence rather than implementation instructions.
