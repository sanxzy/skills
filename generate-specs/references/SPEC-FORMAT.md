# Spec Artifact Format

The finalized engineering spec lives at:

```text
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/spec.md
```

It becomes canonical current output only after the host writes it, re-reads it, verifies it against the quality-gated content and this format, and records `spec-write-verified` followed by `workflow-completed` in progress.

## Purpose

`spec.md` communicates the complete final behavior contract for exactly one feature. It must be independently understandable without reopening the source conversation, scout reports, or progress log; it may rely on the specific read-only reference files cited under the canonical `references/` path rule.

The spec may include module-level, interface-level, data-contract, API-contract, and testing-seam decisions, but it must not include concrete function signatures, code snippets, scout citations, unresolved alternatives, or open questions.

## File Path References

The spec may contain workspace-relative file paths only in the canonical form `references/<path>` (for example `references/legacy-payments/src/service.ts`), referencing files inside the single top-level `references/` directory at the workspace root. Such paths must:

- Use forward slashes and start with exactly `references/` — no leading `./` or `/`, and no `.` or `..` segments.
- Be path-only in the final artifact: `references/<path>` with no line number and no symbol, for maximal stability.
- Resolve to an existing regular file, not a directory. Symlinks are allowed only when they resolve to a regular file within `references/`.

Qualifying `references/` paths are permitted inline anywhere content warrants them, including context, stories, and implementation guidance. In reference-aware mode (when the user explicitly asked to use `references/`), relevant qualifying citations must appear inline throughout the substantive sections wherever referenced files provide evidence — Implementation Decisions, Testing Decisions, stories/criteria, and other sections — and not only as provenance in Further Notes.

All other file paths — absolute paths, `./references/...`, anything outside workspace-root `references/`, and directory paths — remain prohibited. `references/` is read-only input: the generator and scouts never create, modify, move, rename, or delete files under it.

Every inline citation is collected in the trailing `## References` section, which lists the deduplicated, deterministically sorted (lexicographic) union of all inline citations. Index-only paths are prohibited: every entry in `## References` must also appear inline. When there are no citations, the section body is `None`; the section itself is always present.

Path validity rests on the current-round scout reports, which scouts verify before writing (each cited `references/<path>` is confirmed to resolve to an existing regular file under the workspace-root `references/` directory). The coordinator trusts those reports and does not re-resolve citation paths at write time. A `references/` path that was not verified by a current-round scout report is a format and durability defect; the spec remains valid while the cited `references/` files are preserved.

## Required Structure

Use exactly these eight top-level sections in this order after the title:

```markdown
# F<NNN> — <Feature Title>

## Problem Statement

<The problem from the relevant actor's perspective.>

## Solution

<The complete final behavior and outcome from the relevant actor's perspective.>

## User Stories

### US001 — <Short story title>

As an <actor>, I want <capability>, so that <benefit>.

#### Acceptance Criteria

- AC01
  - Given <initial context>
  - When <actor action or system event>
  - Then <observable result>
- AC02
  - Given <initial context>
  - When <actor action or system event>
  - Then <observable result>

## Implementation Decisions

- <Decision about module responsibilities, interfaces, data contracts, API contracts, integration behavior, state, permissions, failure behavior, or constraints.>

## Testing Decisions

- <Decision about behavior-focused tests, preferred seams, existing or proposed coverage, and what makes a good test.>

## Out of Scope

- <Explicit exclusion.>

## Further Notes

- <Rationale, logical source provenance, dependencies, or non-blocking observations.>

## References

- <Deduplicated, lexicographically sorted union of every inline `references/<path>` citation, or `None` when empty.>
```

No other top-level sections are allowed. `References` is always present and always last; it is `None` when there are no citations. Details such as edge cases, acceptance criteria, dependencies, and constraints must live inside the appropriate required section.

## Section Rules

### Title

Use:

```markdown
# F<NNN> — <Feature Title>
```

Rules:

1. Use the selected `features.md` identifier when sourced from `features.md`.
2. Use the local per-backlog feature-spec identifier when sourced from conversation only.
3. Do not add YAML frontmatter.
4. Do not add a metadata block.

### Problem Statement

Describe the unmet need or undesirable current state from the actor's perspective. Keep it focused on the one selected feature.

Do not describe implementation tasks, repository evidence, or generation process. Qualifying `references/` paths may be included when needed to identify reference material.

### Solution

Describe the complete final behavior contract for the selected feature. Include success behavior, material non-success behavior, boundaries, integrations, permissions, quality behavior, and dependency interactions when they affect the promised outcome.

Do not reduce the spec to only the missing delta from current code.

### User Stories

Use sequential story identifiers:

```markdown
### US001 — <Short story title>

As an <actor>, I want <capability>, so that <benefit>.
```

Rules:

1. Begin at `US001` and number continuously with no gaps.
2. Each story contains one actor, one capability, and one benefit.
3. Stories collectively cover the selected feature's complete final behavior.
4. Include successful, failure, boundary, empty, permission, validation, accessibility, security, privacy, reliability, or recoverable-dependency behavior when material.
5. Do not use user stories for unrelated dependent features.

### Acceptance Criteria

Every user story must include `#### Acceptance Criteria`.

Use scenario identifiers that restart per story:

```markdown
- AC01
  - Given <initial context>
  - When <actor action or system event>
  - Then <observable result>
```

Rules:

1. Begin at `AC01` within each story and number continuously with no gaps.
2. Every scenario must contain explicit `Given`, `When`, and `Then` clauses.
3. Criteria must be externally observable and testable.
4. Include success criteria and, where applicable, failure and boundary criteria.
5. Do not assert implementation details as acceptance criteria.

### Implementation Decisions

Record decided implementation-relevant contracts at durable prose level. Acceptable content includes:

- Module or component responsibilities without file paths (except qualifying `references/` paths).
- Interface responsibilities without concrete signatures.
- Data contracts and schema behavior without code snippets.
- API contracts without concrete source references (except qualifying `references/` paths).
- State transitions.
- Integration behavior.
- Permission, security, privacy, reliability, and failure-handling decisions.
- Constraints derived from existing codebase evidence or greenfield context.

Rules:

1. Record one decided contract, not alternatives.
2. Label decisions as proposed when greenfield mode means no existing implementation evidence exists.
3. Do not include source file paths except qualifying `references/` paths.
4. Do not include concrete function signatures.
5. Do not include code snippets.
6. Do not cite scout reports.
7. In reference-aware mode, cite relevant reference-backed decisions inline with path-only `references/<path>` citations.
8. Do not include open questions.

### Testing Decisions

Record behavior-focused testing decisions. Include:

- What makes a good test for the feature.
- Which behavioral seams should be tested.
- Existing seams or prior-art patterns when evidence exists.
- Proposed seams when greenfield.
- Why the seam is high enough to avoid over-testing implementation details.

Rules:

1. Prefer existing seams over new seams.
2. Prefer the highest usable seam.
3. Test external behavior, not implementation details.
4. Do not include source file paths or concrete test filenames, except qualifying `references/` paths (path-only inline citations in reference-aware mode).
5. Do not include commands unless needed as durable testing-contract prose; avoid repository-specific command transcripts.
6. Do not leave testing alternatives unresolved.

### Out of Scope

List explicit exclusions needed to prevent scope ambiguity.

Do not use this section for open questions, unresolved future decisions, or unrelated backlog items.

### Further Notes

Use only for:

- Rationale for important decisions.
- Logical source provenance, such as `Derived from finalized feature F003 and clarified conversation decisions`.
- Known cross-feature dependencies by identifier or title.
- Non-blocking observations that do not change behavior, scope, interfaces, data, failure handling, or testing seams.
- Preservation of additional user-supplied reference instructions or notes verbatim (for example "create an original version in our project to avoid copyright issues").

Except for qualifying `references/` paths, do not include artifact paths, scout-report citations, repository evidence, generation-process narration, open questions, tentative choices, or unresolved options.

### References

The trailing `References` section lists every inline path-only `references/<path>` citation, deduplicated and deterministically sorted (lexicographic). Index-only paths are prohibited — every entry must also appear inline. When there are no citations, the body is `None`. This section is the reader's index of the cited read-only reference files.

## Cross-feature Dependency Rules

When the selected feature depends on another feature:

1. Specify only the selected feature's observable contract and required dependency interaction.
2. Identify the dependent feature in Further Notes when known.
3. Do not expand or redefine the dependent feature's internal behavior.
4. Use `discussion` if the dependency contract is unresolved and materially affects the selected feature.

## Language Rules

Use product-requirement language from the source context. If mixed or unclear, use the repository's dominant documentation language. Preserve product terms verbatim.

Keep the following tokens unchanged:

- `F<NNN>` feature identifiers.
- `US<NNN>` story identifiers.
- `AC<NN>` acceptance-criteria identifiers.
- Required section headings.

## Durability Gate

Before finalization, confirm that a reader or delegated agent can understand the selected feature's complete final behavior and recover the evidence behind every reference-grounded claim by reopening each cited `references/` file, without access to:

- Source code, except the specific `references/` files cited in the spec.
- File paths, except the specific path-only `references/` citations in the spec.
- Scout reports.
- Progress logs.
- The original conversation.
- Implementation plans.
- Tickets.

The cited `references/` files are the evidence-recovery mechanism; scout reports, progress logs, and the original conversation are not. Current-round scouts verify cited paths before reporting, and the coordinator trusts that verification rather than re-resolving paths at write time. If implementation changes while the intended behavior remains the same, `spec.md` should remain accurate while the cited `references/` files are preserved.
