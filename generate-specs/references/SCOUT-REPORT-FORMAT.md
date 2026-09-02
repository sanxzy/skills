# Scout Report Format

Every `spec-scout` writes one canonical technical evidence report to:

```text
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/scouts/round-<RRR>/<topic>.md
```

After validating its brief, the scout initializes the report and persists meaningful evidence incrementally. The report exists for analysis, auditability, and resume. It may contain implementation details and source references, but those details must not be copied into the finalized `spec.md` as project-root file paths, concrete function signatures, code snippets, or scout citations.

## Required Template

```markdown
# Spec Scout Report — <Topic title>

**Backlog:** `<backlog_name>`
**Feature:** `<feature_id>`
**Topic:** `<topic>`
**Status:** `in-progress` | `completed` | `blocked`
**Workspace root:** `<absolute workspace root>`
**Report path:** `<report_path>`
**Last checkpoint:** `<discovery phase or checkpoint>`
**Next step:** `<next discovery action or none>`

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

## Incremental discovery log

<Append-only canonical evidence entries. Each entry records its unique ID, affected section, observation status, evidence, checkpoint, and next step.>
```

## Incremental Lifecycle

- A fresh report is written as the complete template with `Status: in-progress` before discovery begins. This is the only full-file write. Record the validated assigned scope, exclusions, and delegated questions in `Scope Investigated`; use `Pending discovery` only for evidence sections not yet investigated and `None` only after a section has been investigated and has no applicable content.
- A resumed report must already exist with matching metadata and `Status: in-progress`. The coordinator passes the required explicit `resume=true` delegation value. Preserve its evidence and continue from `Last checkpoint` and `Next step`; never silently restart or overwrite it. If the report predates the incremental log, append that section heading once before its first entry.
- After initialization, all discovery persistence is append-only. Never use a full-file write on an existing report; never rewrite, truncate, replace, reorder, or rebuild prior content.
- After every meaningful fact, observation, conclusion, or relevant finding, append one self-contained entry to the canonical `Incremental discovery log` before continuing. Each entry must identify its affected canonical section, observation status (`observed`, `inferred`, or `pending verification`), concise evidence, checkpoint, and next step. Preserve earlier entries; a correction or conflict is a new entry, not a replacement.
- Keep the full header and section skeleton present while content is partial. Do not update earlier sections or header metadata for routine discovery; record changing checkpoint and next-step values in the appended entry. Read the report before and after each append.
- At finalization, append the final synthesis and any blocker rationale, then make only targeted metadata/marker edits for status, checkpoint, next step, and `Pending discovery`; never rewrite the report body.
- A `completed` report contains no `Pending discovery` markers. A `blocked` report may retain them when the blocker prevents full investigation and the blocker is recorded in `Conclusions`.
- An early invalid input or state returns `REJECTED: invalid input: <reason>` without creating or modifying a report. A graceful unfinished run may return `status: in-progress`.

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
11. `Incremental discovery log`

Use `Pending discovery` for an untouched section in an `in-progress` report, and use `None` only for an investigated section with no applicable content; never omit a required section.

## Status Rules

### Report status

- `in-progress`: The scout has initialized the complete report but has not finished the assigned investigation. Section content may be partial and may contain `Pending discovery` markers.
- `completed`: The assigned investigation ran to completion and every delegated question has an evidence-backed answer. Every section is investigated and no `Pending discovery` markers remain. A completed report may still contain conflicts or unknowns when those are themselves well-evidenced.
- `blocked`: Operational constraints prevented adequate investigation after valid startup, such as inaccessible repository content, unavailable required tools, prohibited mutation, or an unreadable dependency boundary. A blocked report may retain `Pending discovery` markers when the blocker is recorded.

A terminal report must not be overwritten by a fresh or resume delegation. A terminal collision returns `REJECTED: invalid input: terminal report already exists`; invalid delegation or resume state is rejected before report mutation.

Do not mark a report blocked merely because the feature is currently unsupported or the current behavior conflicts with the desired behavior.

## Evidence Rules

1. Prefer reachable behavior over isolated implementation artifacts.
2. Corroborate claims with behavioral tests, documentation, configuration, and integrations where available.
3. For reference-material evidence, cite only sources outside the project root in either the canonical workspace-root-relative form `<path>:<line-range>` or absolute form `<absolute-path>:<line-range>`. For example, Codex sources under `references/codex/codex-rs/` are cited as `references/codex/codex-rs/config/src/state.rs:155-169`. Relative paths use forward slashes with no leading `./` or `/`, and no `.` or `..` segments.
4. Before persisting a reference-material citation, verify that its path resolves to an existing regular file outside the project root. Symlinks are allowed only when they resolve to a regular file outside the project root.
5. Append each meaningful fact, observation, conclusion, or relevant finding as a self-contained entry in the canonical `Incremental discovery log` as soon as it is discovered; do not wait for a final batch, rewrite the report, or copy raw tool output.
6. Include workspace-relative `path:line` or `path:line-range` references for target-codebase evidence whenever possible; these precise paths may stay in the report (a working artifact) but must be understood as NOT carried verbatim into the final `spec.md` — the coordinator re-expresses them as durable prose and feature identifiers.
7. Include precise symbols such as functions, classes, routes, commands, test names, or configuration keys.
8. Explain what each reference proves and what it does not prove.
9. For commands, record the exact command, why it was safe and non-mutating, relevant result, and exit status when available.
10. Distinguish documentation intent from verified current behavior.
11. Do not treat a name, TODO, comment, stub, or dormant code path as proof of supported behavior.
12. Record active-working-tree evidence when uncommitted changes affect the topic.
13. Never fabricate a citation, command result, reachable path, or confidence level.
14. Never include secret values, credentials, tokens, private keys, session material, personal data, or sensitive environment contents. Cite sensitive configuration keys by name and path only, redact values as `[REDACTED]`, and describe implications without reproducing protected data.
15. Only the current round's scout reports feed final artifacts; do not silently reuse prior-round or stale reports as citation sources.

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
