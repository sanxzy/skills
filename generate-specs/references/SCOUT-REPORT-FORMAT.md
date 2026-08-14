# Scout Report Format

Every `spec-scout` writes one canonical technical evidence report to:

```text
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/scouts/round-<RRR>/<topic>.md
```

The report exists for analysis, auditability, and resume. It may contain implementation details and source references, but those details must not be copied into the finalized `spec.md` as project-root file paths, concrete function signatures, code snippets, or scout citations.

## Required Template

```markdown
# Spec Scout Report — <Topic title>

**Backlog:** `<backlog_name>`
**Feature:** `<feature_id>`
**Topic:** `<topic>`
**Status:** `completed` | `blocked`
**Workspace root:** `<absolute workspace root>`
**Report path:** `<report_path>`

## Scope Investigated

### Included

- <Assigned feature behavior, journey, project area, or question>

### Excluded

- <Explicit boundary>

### Questions to Resolve

1. <Question from the coordinator>
2. <Question from the coordinator>

## Current Behavior

<Describe current reachable behavior relevant to the selected feature. Cover happy paths, non-success paths, direct observations, and reasoned inferences.>

## Relevant Components and Responsibilities

| Component or responsibility | Current role | Evidence | Limitations |
|---|---|---|---|
| <Name or responsibility> | <What it does> | `<path>:<line>` | <What it does not prove> |

## Interfaces and Data Contracts

| Contract | Current behavior | Evidence | Implication for spec |
|---|---|---|---|
| <Interface, API, event, command, or contract> | <Observed behavior> | `<path>:<line>` | <Relevant durable constraint> |

## Data and State

<State, persistence, lifecycle, validation, migration, consistency, or recovery behavior relevant to the feature. Use `None` if not relevant.>

## Integrations and Constraints

### Integrations

- **<Integration>:** <Current role, behavior, configuration, evidence, and observed failure handling.>

### Constraints

- <Product, platform, data, compatibility, configuration, permission, operational, security, privacy, or reliability constraint.>

## Failure, Security, and Quality Behavior

| Quality or failure area | Current observable behavior | Evidence | Gap or constraint |
|---|---|---|---|
| Validation | <Behavior or `Not relevant`> | <reference or `None`> | <gap or `None`> |
| Permissions | <Behavior or `Not relevant`> | <reference or `None`> | <gap or `None`> |
| Security | <Behavior or `Not relevant`> | <reference or `None`> | <gap or `None`> |
| Privacy | <Behavior or `Not relevant`> | <reference or `None`> | <gap or `None`> |
| Accessibility | <Behavior or `Not relevant`> | <reference or `None`> | <gap or `None`> |
| Reliability | <Behavior or `Not relevant`> | <reference or `None`> | <gap or `None`> |
| Operability | <Behavior or `Not relevant`> | <reference or `None`> | <gap or `None`> |

## Tests and Testing Seams

### Existing Coverage

| Test or validation path | Location or command | Result | Behavior established |
|---|---|---|---|
| <Name> | `<path>:<line>` or `<command>` | <Observed result> | <What it proves> |

### Candidate Seams

| Seam | Existing or proposed | Why this seam is high enough | Evidence |
|---|---|---|---|
| <Behavior seam> | `existing` | <Rationale> | `<path>:<line>` |

### Coverage Gaps

- <Behavior not established by current tests or validation>

## Conflicts and Unknowns

### Conflicts

- <Contradictory code, test, documentation, configuration, conversation, or observed behavior, plus why it matters.>

Write `None` when no conflicts were found.

### Unknowns

- <Current-state or contract question that remains unestablished, why evidence is insufficient, and focused discovery that could resolve it.>

Write `None` when no unknowns remain in the assigned scope.

## Conclusions

### Questions Answered

1. **<Original question>:** <Evidence-backed answer.>
2. **<Original question>:** <Evidence-backed answer.>

### Spec-Relevant Findings

- <Finding that should inform Problem Statement, Solution, User Stories, Implementation Decisions, Testing Decisions, Out of Scope, or Further Notes.>

### Coverage Assessment

- **Scope coverage:** `complete` | `incomplete`
- **Evidence confidence:** `high` | `medium` | `low`
- **Blocking reason:** <Required when report status is `blocked`; otherwise `None`.>
- **Recommended follow-up discovery:** <Evidence-only follow-up scope or `None`.>
```

## Required Sections

Every report must contain all of these sections in this order:

1. `Scope Investigated`
2. `Current Behavior`
3. `Relevant Components and Responsibilities`
4. `Interfaces and Data Contracts`
5. `Data and State`
6. `Integrations and Constraints`
7. `Failure, Security, and Quality Behavior`
8. `Tests and Testing Seams`
9. `Conflicts and Unknowns`
10. `Conclusions`

Use `None` rather than omitting an empty section.

## Status Rules

### Report status

- `completed`: The assigned investigation ran to completion and every delegated question has an evidence-backed answer. A completed report may still contain conflicts or unknowns when those are themselves well-evidenced.
- `blocked`: Operational constraints prevented adequate investigation, such as inaccessible repository content, unavailable required tools, prohibited mutation, or an unreadable dependency boundary.

Do not mark a report blocked merely because the feature is currently unsupported or the current behavior conflicts with the desired behavior.

## Evidence Rules

1. Prefer reachable behavior over isolated implementation artifacts.
2. Corroborate claims with behavioral tests, documentation, configuration, and integrations where available.
3. For reference-material evidence, cite only sources outside the project root in either the canonical workspace-root-relative form `<path>:<line-range>` or absolute form `<absolute-path>:<line-range>`. For example, Codex sources under `references/codex/codex-rs/` are cited as `references/codex/codex-rs/config/src/state.rs:155-169`. Relative paths use forward slashes with no leading `./` or `/`, and no `.` or `..` segments.
4. Before writing the report, verify that every cited reference-material path resolves to an existing regular file outside the project root. Symlinks are allowed only when they resolve to a regular file outside the project root.
5. Include workspace-relative `path:line` or `path:line-range` references for target-codebase evidence whenever possible; these precise paths may stay in the report (a working artifact) but must be understood as NOT carried verbatim into the final `spec.md` — the coordinator re-expresses them as durable prose and feature identifiers.
6. Include precise symbols such as functions, classes, routes, commands, test names, or configuration keys.
7. Explain what each reference proves and what it does not prove.
8. For commands, record the exact command, why it was safe and non-mutating, relevant result, and exit status when available.
9. Distinguish documentation intent from verified current behavior.
10. Do not treat a name, TODO, comment, stub, or dormant code path as proof of supported behavior.
11. Record active-working-tree evidence when uncommitted changes affect the topic.
12. Never fabricate a citation, command result, reachable path, or confidence level.
13. Never include secret values, credentials, tokens, private keys, session material, personal data, or sensitive environment contents. Cite sensitive configuration keys by name and path only, redact values as `[REDACTED]`, and describe implications without reproducing protected data.
14. Only the current round's scout reports feed final artifacts; do not silently reuse prior-round or stale reports as citation sources.

## Scope and Overlap Rules

- Stay within the delegated question.
- Shared evidence may appear in multiple reports only when distinct questions require it.
- Cross-reference known related reports.
- Do not duplicate another report's complete analysis.
- Record newly discovered related behavior under `Conflicts and Unknowns` or `Conclusions`; do not expand into a broad unassigned audit.

## Prohibited Content

Do not include:

- Final spec wording.
- User story IDs or acceptance-criteria IDs unless they were supplied as source context.
- Tickets or implementation plans.
- Architecture recommendations unrelated to establishing evidence.
- Product assumptions presented as facts.

The report may identify evidence-backed constraints, gaps, and candidate seams but leaves all spec synthesis to the main host.
