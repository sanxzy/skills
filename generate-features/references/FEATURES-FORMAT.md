# Feature Artifact Format

The finalized product-facing artifact lives at:

```text
_xzy-ai/sprints/<backlog_name>/features.md
```

It becomes immutable after the first write is re-read, verified, and recorded by an `artifact-written` event. The host may correct that same first write before finalization when verification fails. A later feature backlog requires a new backlog name and a new artifact.

## Purpose

`features.md` communicates the durable target behavior that still requires work. It is independently understandable without reopening the source conversation or reading technical scout reports; it may rely on the specific read-only non-codebase reference files cited under the citable path rule.

It must not include implementation evidence, assumptions, open questions, tentative scope, or technical decomposition.

## Project Root Resolution

Before working with citations, resolve the project codebase root from `<cwd>/_xzy-ai/project-root.md`:

- The file holds exactly one `<cwd>`-relative project-root entry (for example `plugins`) using forward slashes, with no leading `/`, `.` or `..` segments; it must resolve to a directory inside `<cwd>`, and the project root is `<cwd>/<entry>`.
- The project root is the active codebase under development. It is mutable and its contents are never cited in final artifacts.
- If the file is missing, empty, or malformed, ask the user to correct it. Do not guess the project root.

## File Path References

The artifact may contain workspace-root-relative file paths only in canonical, path-only form (for example `references/legacy-payments/src/service.ts`), referencing files that live under the workspace root and outside the project root and outside `_xzy-ai/`. Such paths must:

- Use forward slashes with no leading `./` or `/`, and no `.` or `..` segments.
- Be path-only in the final artifact: no line number and no symbol, for maximal stability.
- Resolve to an existing regular file, not a directory. Symlinks are allowed only when they resolve to a regular file within the citable scope.

Qualifying paths are permitted inline anywhere content warrants them, including Background, Desired Outcome, Goals, In Scope, and feature descriptions. In reference-aware mode (entered only when the user explicitly asks to use references as a source of truth), relevant qualifying citations must appear inline throughout the substantive sections wherever referenced files provide evidence, and not only as provenance in a notes area.

All other file paths — absolute paths, `./...`, anything under the project root, anything under `_xzy-ai/`, and directory paths — remain prohibited. Citable reference locations are read-only input: the generator and scouts never create, modify, move, rename, or delete files in them.

Every inline citation is collected in the trailing `## References` section, which lists the deduplicated, deterministically sorted (lexicographic) union of all inline citations. Index-only paths are prohibited: every entry in `## References` must also appear inline. When there are no citations, the section body is `None`; the section itself is always present.

Path validity rests on the current-round scout reports, which scouts verify before writing (each cited path is confirmed to resolve to an existing regular file under the workspace root, outside the project root and `_xzy-ai/`). The coordinator trusts those reports and does not re-resolve citation paths at write time. A path that was not verified by a current-round scout report, or that falls under the project root or `_xzy-ai/`, is a format and durability defect; the artifact remains valid while the cited non-codebase files are preserved.

## Required Structure

Use exactly these nine top-level sections in this order:

```markdown
# Features — <Backlog title>

## Background

<Durable product and business context.>

## Intended Users

<Actors or stakeholder groups and why the outcome matters to them.>

## Problem

<The user-observable or business problem being addressed.>

## Desired Outcome

<The complete state that should be true when this backlog is delivered.>

## Goals

- <Outcome-oriented goal>
- <Outcome-oriented goal>

## In Scope

- <Included behavior or boundary>
- <Included behavior or boundary>

## Out of Scope

- <Explicit exclusion>
- <Explicit exclusion>

## Features

- [ ] F001 - <Capability title>

    <One cohesive paragraph describing the complete end-to-end outcome and all relevant user-observable behavior.>

- [ ] F002 - <Capability title>

    <One cohesive paragraph describing the complete end-to-end outcome and all relevant user-observable behavior.>

## References

- <Deduplicated, lexicographically sorted union of every inline path citation, or `None` when empty.>
```

`<Backlog title>` is a human-readable title derived from `<backlog_name>` and product terminology.

## Section Rules

### Background

Include enough stable context to explain the product area and why the backlog exists. Do not narrate the generation process, mention scouts, cite conversations, or list repository evidence. Qualifying citable paths may be included when needed to identify reference material.

### Intended Users

Name every actor whose outcome materially shapes the feature list. Actors may include customers, administrators, operators, developers, or other stakeholders.

### Problem

Describe the current unmet need or undesirable observable state. Keep it product-facing and avoid source-code diagnosis.

### Desired Outcome

Describe the final observable state across the scoped journey. Do not phrase it as implementation work.

### Goals

List durable outcome goals. Do not use tasks, milestones, priority labels, or implementation deliverables.

### In Scope

State behavior and boundaries included in this backlog. This section defines the interpretation boundary for the feature list; it does not duplicate every feature description.

### Out of Scope

State meaningful exclusions needed to prevent scope ambiguity. Do not use this section for unresolved questions.

### Features

Include only capabilities requiring work. The list is flat and ordered by product dependency followed by the natural user journey.

### References

The trailing `References` section lists every inline path-only citation, deduplicated and deterministically sorted (lexicographic). Index-only paths are prohibited — every entry must also appear inline. When there are no citations, the body is `None`. This section is the reader's index of the cited read-only non-codebase reference files.

## Feature Item Contract

Every feature uses a zero-padded identifier, a concise title, and one detailed paragraph:

```markdown
- [ ] F<NNN> - <Capability title>

    <Complete end-to-end behavior paragraph.>
```

Rules:

1. Begin at `F001` and number continuously with no gaps.
2. Assign identifiers only after final ordering.
3. Use one unchecked checklist item per independently valuable capability.
4. Do not bold the ID or title.
5. Place one blank line between the title line and description.
6. Indent the description by four spaces so it belongs to the checklist item.
7. Use one cohesive paragraph, not nested bullets, subfeatures, or acceptance criteria.
8. Describe the complete final outcome, including material happy and non-success paths.
9. Include validation, rejection, permissions, empty states, recoverable failures, accessibility, security, privacy, reliability, or similar qualities when they materially affect the promised outcome.
10. For a partially supported capability, describe the whole target behavior rather than only the missing delta.
11. Exclude implementation details, files, paths, functions, tests, layers, APIs, data structures, migrations, and technical sequencing. Qualifying path-only non-codebase citations are allowed in reference-aware mode.
12. Do not add status, effort, risk, or priority labels unless priority is explicitly part of the supplied product context.

## Granularity Rules

Split one candidate into separate features when each part delivers independently recognizable value and can be understood as a complete observable outcome.

Keep behavior together when its steps are inseparable parts of one end-to-end outcome.

Do not use broad parent items with nested children. Do not split by UI, backend, data, integration, or other technical layer.

## Inclusion Rules

Include:

- Capabilities classified as `missing`.
- Complete target outcomes for capabilities classified as `partial`.
- Unstated capabilities proven necessary for the clarified end-to-end outcome.

Exclude from the finalized feature list:

- Capabilities already classified as `supported`, unless preserving their behavior is necessary to define a changed outcome.
- Speculative enhancements.
- Purely technical enablers without an independently recognizable actor outcome.

Do not finalize at all while an `unknown` capability could affect the feature set or a `conflicting` capability remains unresolved. Return those cases to focused discovery or `discussion`; never silently omit them and proceed.

## No-work Variant

When the intended outcome is already fully supported, preserve every required section and write:

```markdown
## Features

No outstanding features
```

Do not add checklist items. Do not list supported capabilities as checked features.

## Language Rules

Use the product-requirement language from the conversation. If mixed or unclear, use the repository's dominant documentation language. Preserve product terms verbatim.

Keep the following tokens unchanged:

- `F001`, `F002`, and other feature identifiers.
- Markdown checklist syntax.
- The `No outstanding features` sentinel.
- Required section headings.

## Durability Gate

Before finalization, confirm that a reader or delegated agent can understand the full intended product outcome and recover the evidence behind every reference-grounded claim by reopening each cited non-codebase file, without access to:

- Project source code under the resolved project root.
- File paths, except the specific path-only citations.
- Test files.
- Scout reports.
- The original conversation.
- Implementation plans.

The cited non-codebase files are the evidence-recovery mechanism; scout reports, progress logs, and the original conversation are not. If implementation changes while the desired outcome remains the same, `features.md` should still remain accurate while the cited non-codebase files are preserved.
