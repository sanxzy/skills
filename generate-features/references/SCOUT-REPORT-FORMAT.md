# Scout Report Format

Every `feat-scout` writes one canonical technical evidence report to:

```text
_xzy-ai/sprints/<backlog_name>/feats/scouts/<topic>.md
```

The report exists for analysis and auditability. It may contain implementation details, but none of those details may be copied into the finalized `features.md`.

## Required Template

```markdown
# Feature Scout Report — <Topic title>

**Backlog:** `<backlog_name>`
**Topic:** `<topic>`
**Status:** `completed` | `blocked`
**Repository root:** `<absolute repository root>`
**Report path:** `<report_path>`

## Scope

### Included

- <Assigned behavior, journey, project area, or question>

### Excluded

- <Explicit boundary>

### Questions to Resolve

1. <Question from the coordinator>
2. <Question from the coordinator>

## Current End-to-End Behavior

<Describe current reachable behavior from actor trigger through observable outcome. Cover relevant happy and non-success states. Distinguish direct observation from inference.>

## Capability Status

| Capability | Status | Rationale | Evidence |
|---|---|---|---|
| <Current capability being assessed> | `supported` | <Why> | `<path>:<line>` |
| <Current capability being assessed> | `partial` | <Why> | `<path>:<line>` |

## User Journeys

### <Journey name>

1. **Actor and trigger:** <Who begins the journey and how.>
2. **Current path:** <Observed end-to-end path.>
3. **Observable outcome:** <What the actor sees or can accomplish.>
4. **Non-success behavior:** <Validation, rejection, empty, permission, dependency, or recovery states.>
5. **Capability status:** `supported` | `partial` | `missing` | `conflicting` | `unknown`
6. **Evidence:** <Precise references.>

## Implementation Evidence

| Evidence | Location | What It Establishes | Limitations |
|---|---|---|---|
| <Function, class, route, component, command, configuration, or document> | `<path>:<line-range>` | <Claim supported by this evidence> | <What it does not prove> |

## Tests and Validation

### Existing Coverage

| Test or validation path | Location or command | Result | Behavior established |
|---|---|---|---|
| <Name> | `<path>:<line>` or `<command>` | <Observed result> | <What it proves> |

### Coverage Gaps

- <Behavior not established by current tests or validation>

## Integrations and Constraints

### Integrations

- **<Integration>:** <Current role, behavior, configuration, evidence, and observed failure handling.>

### Constraints

- <Product, platform, data, compatibility, configuration, permission, or operational constraint relevant to the topic.>

## Quality Behavior

| Quality | Current observable behavior | Status | Evidence |
|---|---|---|---|
| Accessibility | <Behavior or `Not relevant to scope`> | <one of the five statuses or `None` when not relevant> | <reference or `None`> |
| Security | <Behavior or `Not relevant to scope`> | <one of the five statuses or `None` when not relevant> | <reference or `None`> |
| Privacy | <Behavior or `Not relevant to scope`> | <one of the five statuses or `None` when not relevant> | <reference or `None`> |
| Reliability | <Behavior or `Not relevant to scope`> | <one of the five statuses or `None` when not relevant> | <reference or `None`> |
| Operability | <Behavior or `Not relevant to scope`> | <one of the five statuses or `None` when not relevant> | <reference or `None`> |

## Conflicts

- <Contradictory code, test, documentation, configuration, conversation, or observed behavior, plus why it matters.>

Write `None` when no conflicts were found.

## Unknowns

- <Current-state question that remains unestablished, why evidence is insufficient, and what focused discovery could resolve it.>

Write `None` when no unknowns remain in the assigned scope.

## Cross-topic Dependencies

- **<related-topic or behavior>:** <Why it matters, what this report established, and what another scout should investigate.>

Write `None` when the topic is self-contained.

## Conclusions

### Questions Answered

1. **<Original question>:** <Evidence-backed answer.>
2. **<Original question>:** <Evidence-backed answer.>

### Coverage Assessment

- **Scope coverage:** `complete` | `incomplete`
- **Evidence confidence:** `high` | `medium` | `low`
- **Blocking reason:** <Required when report status is `blocked`; otherwise `None`.>
- **Recommended follow-up discovery:** <Evidence-only follow-up scope or `None`.>
```

## Required Sections

Every report must contain all of these sections in this order:

1. `Scope`
2. `Current End-to-End Behavior`
3. `Capability Status`
4. `User Journeys`
5. `Implementation Evidence`
6. `Tests and Validation`
7. `Integrations and Constraints`
8. `Quality Behavior`
9. `Conflicts`
10. `Unknowns`
11. `Cross-topic Dependencies`
12. `Conclusions`

Use `None` rather than omitting an empty section.

## Status Rules

### Report status

- `completed`: The assigned investigation ran to completion and every delegated question has an evidence-backed answer. A completed report may still classify a capability as `conflicting` or `unknown` when that classification accurately represents the available evidence.
- `blocked`: Operational constraints prevented adequate investigation, such as inaccessible repository content, unavailable required tools, prohibited mutation, or an unreadable dependency boundary.

Do not mark a report blocked merely because the capability itself is missing or current behavior is conflicting.

### Capability status

Use exactly:

| Status | Rule |
|---|---|
| `supported` | Reachable end-to-end behavior adequately satisfies the relevant desired outcome. |
| `partial` | Material parts of the end-to-end outcome work, but necessary behavior is incomplete or inconsistent. |
| `missing` | No reachable current behavior satisfies the outcome. |
| `conflicting` | Reliable evidence sources disagree about current behavior. |
| `unknown` | Available evidence cannot establish current behavior. |

Every status row must contain rationale and evidence.

## Evidence Rules

1. Prefer reachable end-to-end behavior over isolated implementation artifacts.
2. Corroborate claims with behavioral tests, documentation, configuration, and integrations where available.
3. Include repository-relative `path:line` or `path:line-range` references whenever possible.
4. Include precise symbols such as functions, classes, routes, commands, test names, or configuration keys.
5. Explain what each reference proves and what it does not prove.
6. For commands, record the exact command, relevant result, and exit status when available.
7. Distinguish documentation intent from verified current behavior.
8. Do not treat a name, TODO, comment, stub, or dormant code path as proof of a supported capability.
9. Record active-working-tree evidence when uncommitted changes affect the topic.
10. Never fabricate a citation, command result, reachable path, or confidence level.
11. Never include secret values, credentials, tokens, private keys, session material, personal data, or sensitive environment contents. Cite sensitive configuration keys by name and path only, redact values as `[REDACTED]`, and describe implications without reproducing protected data.

## Scope and Overlap Rules

- Stay within the delegated question.
- Shared evidence may appear in multiple reports only when distinct questions require it.
- Cross-reference known related reports.
- Do not duplicate another report's complete analysis.
- Record newly discovered related behavior under `Cross-topic Dependencies`; do not expand into a broad unassigned audit.

## Prohibited Content

Do not include:

- Proposed final feature wording.
- Feature IDs.
- Feature ordering or priority.
- Tickets or implementation plans.
- Architecture recommendations unrelated to establishing current state.
- Product assumptions presented as facts.

The report may identify evidence-backed capability gaps but leaves all feature synthesis to the main host.
