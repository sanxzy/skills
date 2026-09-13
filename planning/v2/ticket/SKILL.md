---
name: ticket
version: 0.1.0
description: |
  Turn one finalized proposal output file into a dependency-ordered set of
  tracer-bullet implementation tickets with explicit blocking edges. Supports
  proposal-only, greenfield, and explicit reference-aware evidence modes.
argument-hint: "Provide a proposal path or ask to generate tickets from a proposal; optionally request reference-aware evidence."
---

# Ticket

Generate one durable, dependency-ordered ticket set from exactly one finalized proposal artifact. The proposal is the product behavior baseline. This skill decomposes that behavior into independently valuable tracer-bullet implementation tickets without turning the proposal into a technical task list or silently changing its scope. A proposal capability is not automatically one ticket or one phase: when a downstream workflow treats tickets as phases, it must preserve the same small-slice decomposition.

The output is intended for developers, implementers, reviewers, and downstream orchestration skills. Each ticket must be understandable on its own, demoable or verifiable on its own, and explicit about the other tickets that genuinely block it.

## Interface

### Input

Accept:

- an explicit path to one finalized proposal Markdown file;
- a proposal slug when the matching file is under `_xzy-ai/proposals/`;
- an explicit backlog name, when the user wants one different from the proposal slug;
- an optional request to use current codebase evidence for sequencing and testing seams;
- an explicit request to use reference material as a source of truth (reference-aware mode), optionally with reference paths or bounded questions to investigate.

The proposal must be inside the active workspace and must be a regular file. Resolve it before reading any other product source. If no proposal path or slug is supplied:

1. discover `_xzy-ai/proposals/*.md`;
2. use the only candidate when exactly one exists;
3. ask the user to choose when multiple candidates exist;
4. stop when no candidate exists.

Do not choose a proposal by modification time, filename similarity, or an unrelated conversation assumption.

The proposal is the source of truth for product intent, actors, scope, capabilities, states, authority, failure behavior, and success. Current codebase evidence may refine ticket sequencing, dependencies, compatibility, and verification seams, but it may not silently change the proposal's product behavior.

### Output

Write a local ticket set consisting of:

```text
_xzy-ai/sprints/<backlog_name>/tickets.md
_xzy-ai/sprints/<backlog_name>/tickets/<TNNN>-<slug>.md
_xzy-ai/sprints/<backlog_name>/tickets/progress.md
_xzy-ai/sprints/<backlog_name>/tickets/scouts/round-<RRR>/...
```

`tickets.md` is the canonical index. Each `<TNNN>-<slug>.md` is one canonical ticket. `progress.md` and `scouts/` are workflow state and evidence, not product tickets. Preserve unrelated files under the backlog directory.

Use the proposal filename as the default lowercase kebab-case `<backlog_name>`. Use a user-supplied backlog name only when it is lowercase kebab-case and the user explicitly requests it. Do not use an implementation project name guessed from the repository.

The generated set must:

- contain one index and one file per ticket;
- list tickets in dependency order, with blockers before dependents;
- use continuous identifiers `T001`, `T002`, and so on;
- trace every required ticket to proposal capability, journey, state, interaction, or recovery identifiers;
- describe the smallest useful complete vertical slice per ticket;
- preserve the complete expected outcome across the union of tickets rather than compressing a feature into one ticket;
- allow as many tickets as the behavior requires; do not optimize for a short ticket list or short document;
- declare exact blocking edges with `Blocked by`;
- include observable acceptance criteria for success and relevant validation, permission, empty, failure, recovery, accessibility, security, privacy, and reliability behavior;
- keep optional proposal capabilities non-blocking unless the proposal makes them necessary for the core outcome;
- contain no project implementation file paths, function names, concrete signatures, code snippets, command transcripts, unresolved alternatives, or open product questions; qualifying external reference paths are allowed only under the reference-aware citation rules.

This skill writes local Markdown artifacts only. It does not publish to GitHub, Linear, Jira, or another external tracker and does not modify source code.

## Trigger boundary

Run this skill only when the user explicitly asks to create, regenerate, replace, or resume implementation tickets from one named proposal.

Do not run it for:

- creating or revising a proposal;
- generating an implementation plan from `spec.md`;
- feature discovery or backlog generation without a finalized proposal;
- casual brainstorming;
- source-code implementation;
- ticket generation from multiple proposals in one invocation.

Process one proposal per invocation. If a user asks for several proposals, resolve one run at a time rather than merging their scope.

## Core invariants

1. Exactly one proposal is the product source for one ticket-set generation round.
2. The proposal must be structurally valid and finalized before tickets are synthesized.
3. Out-of-scope proposal behavior never becomes a ticket.
4. Product ambiguity is resolved before ticket synthesis; it is never hidden in a ticket.
5. Tickets are vertical slices, not horizontal database, API, UI, test, or infrastructure layers.
6. Every ticket has a real completion outcome and can be demoed or verified independently once its blockers are complete.
7. `Blocked by` contains only genuine prerequisites; do not serialize unrelated tickets.
8. Optional capabilities never block required core tickets.
9. Codebase scouts provide evidence only. They never write tickets, progress, or source code.
10. The host owns source resolution, ticket decomposition, dependency ordering, quality validation, writing, and verification.
11. Never overwrite an existing ticket set without an explicit regeneration or overwrite decision.
12. Never delete unrelated files or silently remove a previous ticket from history.
13. Reference-aware mode is opt-in and never silently replaces the proposal as the product source of truth.
14. Citable reference paths are validated, read-only, and outside the resolved project codebase root.
15. Greenfield ticket generation remains valid without implementation scouts; reference-aware greenfield generation pauses for user clarification when no bounded reference scope can be established.

## Proposal source contract

Before ticket generation, read the complete proposal and verify:

- it begins with `# Proposal:`;
- these 12 required sections are present and ordered:
  1. `## 1. Overview`;
  2. `## 2. Actors and authority`;
  3. `## 3. Scope and non-goals`;
  4. `## 4. End-to-end journey`;
  5. `## 5. Capability contracts`;
  6. `## 6. State model and transitions`;
  7. `## 7. Cross-experience interactions`;
  8. `## 8. Information, truth, and uncertainty`;
  9. `## 9. Validation, review, finalization, and revision`;
  10. `## 10. Failure and recovery`;
  11. `## 11. Edge cases and quality expectations`;
  12. `## 12. Final expected experience and success criterion`;
- at least one `CAP-*` capability is defined;
- journey, state, authority, scope, failure, and success behavior are sufficiently concrete;
- material ambiguity is not left in the proposal;
- capability, journey, state, interaction, and recovery identifiers are not duplicated or malformed;
- the final experience and core product success criterion are explicit;
- each capability states an observable trigger, an actor-visible outcome, a clear boundary, and relevant failure handling rather than hiding several independently verifiable outcomes behind one umbrella heading;
- scope decisions distinguish in-scope behavior, non-goals, explicitly deferred behavior with boundary and reason, and unknown items needing a decision; deferred behavior is never silently treated as in-scope or out-of-scope;
- when the proposal changes existing behavior, fixes a defect, or targets porting or parity, it records current versus desired behavior, what must remain unchanged or compatible, and the oracle or compatibility scope when one applies.

If the proposal is missing required sections, leaves behavior-affecting ambiguity, uses umbrella or untestable capabilities, or omits required scope, preservation, or compatibility boundaries, do not repair it inside this skill. Tell the user to revise or regenerate the proposal first. Do not use the conversation to silently supersede a finalized proposal unless the user explicitly asks to revise the proposal and that change is completed before ticket generation. Do not silently ignore material product decisions from the conversation or from referenced discussion transcripts and decision logs when they are absent from the proposal; require the proposal revision first.

## Managed paths and regeneration

For backlog `<backlog_name>`, the workflow manages only:

```text
_xzy-ai/sprints/<backlog_name>/tickets.md
_xzy-ai/sprints/<backlog_name>/tickets/progress.md
_xzy-ai/sprints/<backlog_name>/tickets/<TNNN>-<slug>.md
_xzy-ai/sprints/<backlog_name>/tickets/scouts/round-<RRR>/
_xzy-ai/sprints/<backlog_name>/tickets/revisions/<RRR>/
```

Preserve every other artifact under `_xzy-ai/sprints/<backlog_name>/`.

When `tickets.md` already exists:

1. For an explicit fresh generation, ask whether to keep the current set or regenerate it with archival.
2. If the user keeps it, append the disposition to progress and stop without changing ticket files.
3. If the user regenerates, archive the exact current index and every ticket named by that index under the next `tickets/revisions/<RRR>/` directory before writing the new set.
4. Verify the archive byte-for-byte by reading it back before replacing any canonical file.
5. Preserve the existing `progress.md`, scout reports, and prior revisions.
6. Never delete a stale ticket silently; it must remain in the archived revision.

An explicit resume continues the latest non-terminal workflow round. Do not start an overlapping fresh round while a previous round is paused or in progress.

## Project location and citation scope

The active workspace is the current working directory. Reference-aware operation uses the same project-root and citation boundary as `generate-plan`:

1. Read `<cwd>/_xzy-ai/project-root.md` before repository or reference discovery, source resolution, citation handling, or reference-aware artifact writes.
2. Require exactly one non-empty project-root entry. It must be a `<cwd>`-relative path using forward slashes, with no leading `/`, `.` or `..` segments, and must resolve to a directory inside `<cwd>`.
3. Treat `<cwd>/<project-root-entry>` as the project codebase root. It is the only codebase used for repository discovery and is never a citable source in final ticket artifacts.
4. Do not inspect or modify anything outside the active workspace except explicitly scoped, read-only citable reference files.
5. If `project-root.md` is missing, empty, malformed, or outside the workspace, pause and ask the user to correct it; do not guess the root.

Citable material is not limited to a single `references/` directory: any existing regular file anywhere on the machine outside the project codebase root may be used as read-only reference evidence. A workspace-relative citation must use forward slashes with no leading `/`, `./`, or `..` segments. An absolute citation must resolve outside the project codebase root. Symlinks are allowed only when they resolve to regular files outside that root. Final ticket artifacts use path-only citations without line ranges or symbols; the source proposal path remains provenance rather than a reference citation. Cited files are read-only inputs.

## Project location and optional discovery

The active workspace is the current working directory. The proposal source and all ticket artifacts must remain inside it.

Current-codebase discovery is optional because the ticket contract is proposal-first:

1. If the user does not request repository evidence or references and `_xzy-ai/project-root.md` is absent or invalid, use proposal-only mode and launch zero scouts.
2. If `_xzy-ai/project-root.md` exists, validate exactly one workspace-relative project-root entry before inspecting source code.
3. If the user requests repository evidence, require a valid project root; if it is missing or malformed, pause and ask the user to correct it.
4. When a valid project root contains relevant implementation, use fresh bounded `ticket-scout` reports. Do not reuse stale `plan-scout`, `spec-scout`, or `feat-scout` reports as ticket evidence.
5. When no relevant implementation exists, record greenfield mode and synthesize from the verified proposal unless reference-aware mode requires a bounded reference investigation.
6. In reference-aware greenfield mode with a clear reference scope, use fresh bounded scouts for the references only; do not treat the empty project root as implementation evidence.
7. In reference-aware greenfield mode without a clear reference scope, pause and ask the user what reference files or bounded questions to scout.

The project root is read-only evidence for this workflow. Do not modify it, commit it, or include its paths in final ticket artifacts. Scouts may retain precise project paths in private reports; final tickets carry durable behavioral consequences and only qualifying external reference citations.

## Required context gate

Generation may proceed only after the host has captured:

1. proposal path, title, and source identity;
2. backlog name and output paths;
3. primary actors and authority;
4. in-scope and out-of-scope behavior;
5. required and optional capabilities;
6. success journey, states, interactions, and recovery boundaries;
7. the proposal's language;
8. whether codebase evidence is requested or necessary;
9. any known dependencies that affect blocking edges;
10. whether evidence mode is `proposal-only` or `reference-aware`, and the explicit reference scope or paths when reference-aware;
11. when reference-aware and greenfield, whether the reference scope is bounded enough to define a scout question without inferring from an empty codebase;
12. any additional user-supplied reference instructions or notes, preserved verbatim when present.

If a ticket-affecting interpretation is unclear, gather all related questions and use the `discussion` skill when supported. Do not ask separate questions for ordinary implementation discovery. Do not synthesize a ticket set while a material ambiguity, source conflict, or missing proposal section remains unresolved.

## Reference-Aware Mode

Reference-aware mode is manual: enter it only when the user explicitly asks to use references as a source of truth. Do not activate it merely because reference files exist. The proposal remains the product contract; references provide evidence for ticket sequencing, dependencies, contracts, risks, verification seams, or implementation patterns and may not silently change proposal behavior.

### Citation scope

- Any existing regular file outside the resolved project codebase root may be used as read-only reference evidence.
- Reference paths may be workspace-root-relative or absolute. Relative paths use forward slashes and no leading `/`, `./`, or `..` segments. Absolute paths must resolve outside the project codebase root.
- Scouts verify reference paths before citing them. Final `tickets.md` and ticket files carry path-only citations without line ranges or symbols; the report may retain precise line-level evidence.
- Every inline citation in a ticket must appear in that ticket's `## References` section; every inline citation in the index must appear in the index's trailing `## References` section; the index section is the deduplicated union of all current-artifact citations. When no references are used, the sections contain `None`.
- Cited files are read-only. Neither the coordinator nor a scout may modify, move, rename, or delete them.

### Behavior by context

- If the user explicitly asks to use references, enter reference-aware mode and preserve relevant path citations in substantive index and ticket content wherever references provide evidence.
- Preserve any additional user-supplied reference instructions or notes verbatim in the applicable ticket/reference section and in the progress context; do not silently drop or paraphrase their substance.
- If reference-aware investigation finds no relevant evidence, tell the user and ask whether to continue without citations, add reference material, or take another action. Do not fabricate citations. If the user explicitly requires citations and no citable material exists, reject the request.
- In an established codebase, derive bounded reference and codebase questions from the proposal and available evidence, then delegate only those questions to fresh `ticket-scout` reports.
- In a greenfield codebase, do not invent a scout scope from an empty project. Continue with proposal-only ticket synthesis when references are not requested. If reference-aware mode is requested but no concrete reference paths or bounded questions identify what to investigate, pause before scouting or writing ticket artifacts with `reason=reference-scope-unclear` and ask: `The project is greenfield, and reference-aware mode has no bounded reference scope to investigate. Which reference files or specific questions should I scout?`
- When a clear reference scope is supplied in greenfield mode, delegate bounded reference-only scouts; do not inspect the empty codebase as if it contained implementation evidence. A reference-only scout may complete with `None` for current implementation evidence when the references answer its bounded questions. If the scoped references are insufficient, follow the no-relevant-evidence rule above.

## Workflow

### 1. Resolve and validate the proposal

1. Resolve the explicit proposal path, slug, or unique proposal candidate.
2. Confirm it stays inside the workspace and is a regular file.
3. Read the complete file.
4. Validate the proposal title, 12 required sections, stable identifiers, scope, authority, state behavior, recovery behavior, core success criterion, capability specificity, scope taxonomy, and work-type boundaries from the proposal source contract.
5. Reconcile newer product decisions from the current conversation and from referenced discussion transcripts or decision logs against the proposal. If material decisions are absent from or contradict the proposal, pause and require a proposal revision before synthesis; neither silently fold the newer detail into tickets nor silently ignore it.
6. Derive or confirm the backlog name.
7. Determine artifact language from the proposal; preserve product terminology exactly.
8. Resolve and validate evidence mode and any reference scope before discovery or managed artifact writes.
9. Create only the managed output directories after source and evidence validation passes.
10. Read existing `progress.md` and apply fresh/resume and overlap rules.
11. Check existing `tickets.md` and apply the regeneration disposition before drafting.
12. Append `workflow-started`, `source-resolved`, and `context-captured` progress events.

### 2. Classify evidence and discovery mode

Perform only light classification first and record two independent dimensions:

- **evidence mode** — `proposal-only` when the proposal is the only source of truth, or `reference-aware` when the user explicitly asks to use citable references;
- **discovery mode** — `greenfield` when no relevant implementation exists, or `established` when relevant implementation exists and evidence is needed for sequencing or verification.

Apply the following rules:

- In `proposal-only` mode, launch zero scouts when no current-codebase evidence is requested or when discovery confirms greenfield context is sufficient. Record `coverage-evaluated` with `reports=0` and the reason.
- In `proposal-only` established mode, use fresh bounded `ticket-scout` reports only when the user requests or the workflow requires current-codebase evidence.
- In `reference-aware` established mode, define bounded reference and codebase questions, then use fresh `ticket-scout` reports for those questions. Do not reuse stale `plan-scout`, `spec-scout`, or `feat-scout` reports as ticket evidence.
- In `reference-aware` greenfield mode, do not scout an empty codebase. If the user supplied clear reference paths or bounded questions, delegate reference-only scouting. If not, pause before scouting or writing artifacts and ask the clarification specified in `Reference-Aware Mode`.

### 3. Plan discovery scopes

Define focused topics before delegating any scout. Sort topics lexicographically. Each topic must have:

- a lowercase kebab-case name;
- a bounded included and excluded scope;
- concrete evidence questions;
- a direct connection to ticket boundaries, dependencies, current behavior, risk, or testing;
- a safe report path under `_xzy-ai/sprints/<backlog_name>/tickets/scouts/round-<RRR>/`;
- an explicit `resume` boolean;
- when reference-aware, the explicitly permitted reference paths or bounded reference scope and the `reference_mode` value passed to the scout.

Useful topics include:

- `current-behavior` — which proposal outcomes are already supported or partial;
- `integration-boundaries` — existing user-facing entry points and dependency edges;
- `data-and-state` — current state and compatibility constraints;
- `testing-seams` — highest usable behavioral verification seams;
- `risks-and-dependencies` — permissions, privacy, reliability, accessibility, migration, and operational constraints;
- `reference-context` — relevant external reference guidance and the product decisions it can evidence, only in reference-aware mode.

Use no more than five scouts per wave, three waves, or fifteen scout invocations per authorized discovery cycle. A corrected retry or narrower replacement consumes budget.

Before any delegation, validate every brief. If validation fails, return `REJECTED: missing required inputs: ...` or `REJECTED: invalid input: ...` and do not append a scout lifecycle event or mutate a report.

### 4. Delegate `ticket-scout`

Provide every required input listed in [Scout Report Format](./references/SCOUT-REPORT-FORMAT.md), including `reference_mode` and `reference_scope`. Include any additional user-supplied reference instructions or notes verbatim in `proposal_context`. Before each delegation, append `scout-started` with the cycle, wave, topic, scope, report path, attempt, and `resume` value. In reference-aware mode, the brief must identify the read-only reference paths or bounded reference questions the scout may investigate.

A scout returns only:

```text
report_path: <path>
status: completed | in-progress | blocked
reason: <required only when blocked>
```

Read every returned report, including partial `in-progress` evidence, before evaluating coverage. A returned `in-progress` report cannot satisfy complete coverage. The host remains the only progress writer.

If a scout rejects its input, record `scout-blocked` with `report=none`, correct the coordinator input, and retry the same topic once. If a terminal report collision occurs, preserve the report and pause for a new report path. For an operationally blocked report, retry once with corrected instructions and then use one narrower replacement scope; preserve every report.

### 5. Evaluate evidence coverage

Before synthesis, verify that the proposal and reports establish:

- the complete product outcome, exclusions, explicitly deferred behavior with boundaries, and unknown items;
- current supported, partial, or missing behavior when discovery was used;
- stable contract and state implications;
- vertical-slice opportunities and genuine prerequisites;
- dependency, permission, privacy, security, accessibility, reliability, migration, rollout, and operational constraints when relevant;
- usable behavioral verification seams for every ticket candidate;
- conflicts, unknowns, and stale evidence;
- relevant reference evidence and verified citation paths when reference-aware;
- omission checks: every required capability, journey step, state, interaction, recovery scenario, and material edge case maps to at least one ticket candidate or is explicitly classified as a cross-cutting principle with its enforcing tickets named; deferred behavior never becomes a ticket candidate while its boundary is preserved; non-goals never become ticket candidates.

If coverage leaves a required identifier, edge case, preservation boundary, or compatibility boundary without a ticket, return to decomposition rather than leaving the gap implicit. If reference-aware investigation finds no relevant evidence, tell the user and ask whether to continue without citations, add reference material, or take another action. Do not fabricate citations. If evidence changes the interpretation of the proposal, do not silently alter tickets. Hand the conflict to `discussion` or ask the user to revise the proposal. Re-run affected discovery after clarified scope.

### 6. Decompose the proposal into ticket candidates

Start from the primary journey and required capabilities. Model the complete expected outcome first, then decompose it repeatedly into the smallest useful complete slices. Use journey steps, meaningful state transitions, validation boundaries, review decisions, interaction hand-offs, and recovery scenarios to find split points.

Do not stop at one ticket per capability or one ticket per feature. One proposal capability may legitimately produce many tickets when its journey contains several independently verifiable outcomes. A long ticket set and a long index are acceptable; a falsely broad ticket is not.

Apply these rules:

1. A ticket delivers one smallest useful independently recognizable actor outcome.
2. A ticket cuts through every relevant layer required for that outcome, but describes the result rather than listing technical layers.
3. Scope size is judged by behavioral independence, not by a maximum ticket count, document length, or arbitrary phase limit.
4. A ticket includes its own success path and material non-success behavior.
5. A prerequisite ticket is allowed only when its outcome is itself demoable or verifiable and genuinely gates another ticket.
6. Do not create setup, scaffolding, schema-only, API-only, UI-only, test-only, or documentation-only tickets without an independent product outcome.
7. When a wide mechanical refactor cannot remain green as a vertical slice, use an explicit expand–migrate–contract sequence and state the compatibility boundary; do not hide it inside an unrelated ticket.
8. Keep optional capabilities out of the core blocking chain. Include them as non-blocking tickets only when the proposal makes them a concrete desired outcome.
9. Combine steps only when splitting them would create a non-demoable fragment or break the expected outcome.
10. Split a broad capability when it contains distinct actor decisions, visible states, completion conditions, validation boundaries, or recovery paths.
11. Re-run the granularity test recursively after every split. If a resulting ticket still contains two independently verifiable outcomes, split it again.
12. When uncertain whether to merge or split, prefer the smaller ticket if both resulting slices remain behaviorally complete.
13. For enhancements, defect fixes, and porting or parity work, preserve existing behavior explicitly: include the current-versus-desired boundary, unchanged or compatible behavior, and the oracle or compatibility scope in the affected tickets rather than leaving preservation implicit.
14. For deferred behavior, record the boundary and next step in the nearest ticket scope boundary without turning the deferred work itself into a ticket.

The union of tickets must still cover the proposal's complete expected outcome, core success criterion, required capabilities, and material failure/recovery behavior. Each candidate must be traceable to one or more proposal IDs (`CAP-*`, `J-*`, `STATE-*`, `INT-*`, or `REC-*`). No ticket may be justified only by an implementation file or scout suggestion.

### 7. Order and validate blocking edges

Build a directed dependency graph where an edge `T001 -> T002` means T001 must finish before T002 can start. Then:

- place blockers before dependents;
- keep independent tickets parallel when possible;
- reject cycles and resolve them by splitting or removing an unjustified edge;
- avoid transitive duplicate edges when a direct blocker is already implied by another blocker, unless the direct relationship matters for recovery;
- ensure every ticket is reachable from the initial frontier or explain the external prerequisite;
- ensure optional tickets do not block required tickets;
- ensure every `Blocked by` entry names an existing ticket ID and title;
- ensure no ticket depends on a later ticket.

The index must show the dependency order and a concise reason for every non-empty blocking edge.

### 8. Synthesize artifacts

Read [Ticket Format](./references/TICKET-FORMAT.md) before writing. Synthesize:

- the canonical `tickets.md` index;
- one complete ticket file per ticket;
- a dependency order with blockers first;
- proposal traceability for every ticket;
- observable acceptance criteria and relevant recovery behavior, with each criterion naming its trigger and actor-visible result so pass or fail can be decided without implementation knowledge, and with untestable adjectives allowed only alongside such an observable test;
- preservation or compatibility criteria in affected tickets when the proposal changes existing behavior, fixes a defect, or targets porting or parity;
- no project implementation paths or code snippets; qualifying external reference paths are allowed only under the reference-aware citation rules.
- in reference-aware mode, path-only citations in substantive ticket and index content, with matching `## References` sections as required by [Ticket Format](./references/TICKET-FORMAT.md).

Tickets must use the language of the proposal. Keep identifiers, domain names, state names, and authority terms unchanged.

### 9. Apply the quality gate

The host alone performs this gate. Do not delegate it.

#### Source integrity

- exactly one valid proposal is identified;
- all required proposal sections and identifiers were read;
- out-of-scope behavior is absent and deferred behavior appears only as a recorded boundary, never as a ticket;
- proposal conflicts and ticket-affecting ambiguity are resolved, including newer conversation or transcript decisions reconciled against the proposal;
- umbrella or untestable capabilities, missing scope taxonomy, and missing preservation or compatibility boundaries were rejected back to proposal revision rather than carried into tickets;
- every ticket traces to proposal behavior.

#### Vertical-slice quality

- every ticket is independently demoable or verifiable after its blockers;
- no ticket is merely a technical layer or vague umbrella;
- each ticket has one smallest useful actor outcome, trigger, boundary, and completion condition;
- each ticket contains success and relevant invalid, empty, permission, failure, recovery, accessibility, privacy, security, and reliability behavior;
- every broad capability was tested for further meaningful splits rather than being emitted as one feature-sized ticket;
- the ticket set is allowed to be long and contains no artificial maximum or compression for convenience;
- the union of tickets covers the proposal's complete expected outcome and core success criterion, including required identifiers, material edge cases, preservation boundaries, and compatibility boundaries;
- optional tickets do not block required tickets;
- the dependency graph is acyclic, minimal, and ordered.

#### Artifact completeness

- `tickets.md` and every ticket file follow `TICKET-FORMAT.md`;
- ticket IDs are continuous and filenames match their IDs and slugs;
- every `Blocked by` entry resolves to a ticket in the same set or explicitly names an external prerequisite;
- acceptance criteria are observable and testable without requiring a particular file or function, with each criterion naming its trigger and actor-visible result and with untestable adjectives allowed only alongside an observable test;
- the index lists all and only the current ticket files;
- no project source paths, function names, signatures, code snippets, command transcripts, unresolved alternatives, or open questions appear, except qualifying external reference paths in reference-aware mode;
- in reference-aware mode, every substantive reference-backed claim has a nearby qualifying path-only citation, and the index and ticket-level `## References` sections are complete and consistent;
- the source proposal, ticket count, dependency order, and revision status are visible in the index.

#### Durability

- each ticket can be understood without reopening the conversation;
- the index plus ticket files preserve enough behavior and dependency context for an implementer to begin at the frontier;
- retained scout reports are evidence only and are not required to understand the ticket contract;
- artifacts are written inside the active workspace and existing sets are archived before replacement;
- cited reference files remain outside the project codebase root, are read-only, and are not required for proposal-only ticket generation.

If a check fails, return to proposal clarification, discovery, decomposition, or synthesis as appropriate. Never write a partial ticket set.

### 10. Archive, write, and verify

After the quality gate passes:

1. archive the existing canonical ticket set when regeneration requires it;
2. write `tickets.md` and all ticket files under their managed paths;
3. read every written file back;
4. verify IDs, filename slugs, proposal traceability, blockers, dependency order, acceptance criteria, index membership, and reference sections;
5. verify no ticket is missing, duplicated, stale, or unlisted;
6. append `ticket-write-verified` with the index path, ticket count, revision, and scout count;
7. append `workflow-completed`.

If any write or verification step fails, preserve the progress checkpoint, do not claim completion, and pause with the exact remediation required.

## Companion files

The main `SKILL.md` owns the interface, workflow, decomposition rules, quality gate, and write behavior. Read these companions before running the workflow:

- [Ticket Format](./references/TICKET-FORMAT.md) — canonical index and per-ticket structure, traceability, acceptance criteria, and dependency rules;
- [Progress Log Format](./references/PROGRESS-LOG-FORMAT.md) — append-only workflow state and recovery events;
- [Scout Report Format](./references/SCOUT-REPORT-FORMAT.md) — evidence-only discovery contract for `ticket-scout`.

The bundled `ticket-scout` is optional. It runs for established codebase evidence, for reference-aware runs with a clear bounded reference scope, or for an explicit codebase-evidence request. It never scouts an empty greenfield codebase without a bounded question, and it never writes canonical tickets or progress. Do not require external trackers, transcripts, scratch files, or other skills to understand the workflow.

## Do not

- Do not read a `spec.md` or `features.md` as a substitute for the proposal source in this skill.
- Do not process multiple proposals in one invocation.
- Do not turn every capability into exactly one ticket; repeatedly split broad capabilities into the smallest useful complete slices.
- Do not merge tickets merely to reduce the ticket count, phase count, or document length.
- Do not create horizontal tickets for database, API, UI, tests, infrastructure, or documentation alone.
- Do not use implementation paths, function names, concrete signatures, code snippets, or command transcripts in final ticket artifacts.
- Do not add behavior that appears only in scout evidence and not in the proposal.
- Do not alter the proposal from inside this skill.
- Do not make optional capabilities block the core journey.
- Do not create cycles, hidden dependencies, or blanket sequential edges.
- Do not overwrite an existing ticket set without archival and explicit regeneration handling.
- Do not publish to an external issue tracker or modify source code.
