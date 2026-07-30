# Plan Artifact Format

The finalized implementation plan lives at:

```text
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/plan.md
```

It becomes canonical current output after the host writes it, re-reads it, verifies it against the quality-gated content and this format, and records `plan-write-verified` followed by `workflow-completed` in progress.

## Purpose

`plan.md` communicates a practical multi-phase implementation plan for exactly one feature. It must be independently understandable without reopening the source conversation, scout reports, source code, or progress log.

The plan uses tracer-bullet vertical slices: each phase delivers a narrow, complete, verifiable path through all relevant integration layers. It should read like the existing `to-plan` output while fitting the `_xzy-ai` sprint artifact structure.

## Required Structure

Use exactly these top-level sections in this order after the title:

```markdown
# Plan: F<NNN> — <Feature Title>

> Source: <spec path, conversation, or logical source>

## Architectural decisions

Durable decisions that apply across all phases:

- **Routes**: ...
- **Schema**: ...
- **Key models**: ...
- **Contracts**: ...
- **Testing seam**: ...

---

## Phase 1: <Title>

**User stories covered**: <US identifiers or concise story labels>

### What to build

<A concise end-to-end behavior description for this vertical slice.>

### Acceptance criteria

- [ ] <Observable criterion>
- [ ] <Observable criterion>

---

## Phase 2: <Title>

**User stories covered**: ...

### What to build

...

### Acceptance criteria

- [ ] ...
```

No other top-level sections are allowed. Add, remove, or rename architectural-decision bullets as appropriate, but preserve the `Architectural decisions` section.

## Section Rules

### Title

Use:

```markdown
# Plan: F<NNN> — <Feature Title>
```

Rules:

1. Use the selected feature identifier when known from `spec.md` or explicit conversation.
2. Do not infer a feature identifier from weak context.
3. Do not add YAML frontmatter.
4. Do not add a metadata table.

### Source

Use one Markdown blockquote immediately after the title:

```markdown
> Source: _xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/spec.md
```

When generated from clarified conversation only, use a durable logical source such as:

```markdown
> Source: clarified conversation for F003
```

Do not cite scout reports or progress logs in the final plan.

### Architectural decisions

Record high-level durable decisions that are unlikely to change throughout implementation. Include only decisions that help later phases stay coherent.

Acceptable content includes:

- Route structures and URL patterns.
- Stable data model or schema shape.
- API, command, event, or integration contracts.
- Authorization, permission, failure, privacy, reliability, or operational boundaries.
- Testing strategy and behavioral seam.

Rules:

1. Keep decisions durable and contract-level.
2. Include stable product or system names when useful.
3. Do not include source file paths, concrete function signatures, code snippets, or scout citations.
4. Do not include unresolved alternatives or open questions.
5. Label decisions as proposed when greenfield mode means no existing implementation evidence exists.

### Phase sections

Each phase must use:

```markdown
## Phase <N>: <Title>

**User stories covered**: <list>

### What to build

<description>

### Acceptance criteria

- [ ] <criterion>
```

Rules:

1. Begin at Phase 1 and number continuously with no gaps.
2. Each phase is a tracer-bullet vertical slice, not a horizontal technical layer.
3. Each phase must be demoable or verifiable on its own.
4. Prefer many thin phases over a few broad phases.
5. Order prerequisite slices first, then follow the natural user journey.
6. Each phase should cut through every relevant layer needed for that slice, such as schema, domain behavior, API, UI, integration, and tests, without listing the plan as layer-by-layer tasks.
7. A phase may mention durable routes, models, contracts, or data shapes from the architectural decisions.
8. Do not include brittle implementation details such as exact files, function names, concrete signatures, code snippets, or command transcripts.
9. Do not include tasks unrelated to the selected feature.

### User stories covered

When the source is `spec.md`, reference `US001`, `US002`, and similar story identifiers from the spec. When generated from conversation only, use concise story labels or explicit behavior labels.

### What to build

Describe the end-to-end behavior delivered by this slice. Include success behavior and material non-success behavior when part of the slice.

Do not write a checklist of implementation layers. The description should remain outcome-oriented and implementation-guiding.

### Acceptance criteria

Use unchecked Markdown checklist items. Criteria must be observable, testable, and scoped to the phase.

Rules:

1. Include success criteria and material failure, boundary, permission, validation, empty, accessibility, security, privacy, reliability, or recoverable-dependency criteria when relevant.
2. Do not duplicate the full spec acceptance criteria mechanically; slice them into the smallest useful phase-level checks.
3. Do not assert implementation details as acceptance criteria.
4. Do not include open questions.

## Language Rules

Use the language of the source spec or clarified product requirements. If mixed or unclear, use the repository's dominant documentation language. Preserve established product terms verbatim.

Keep the following tokens unchanged:

- `F<NNN>` feature identifiers.
- `US<NNN>` user story identifiers.
- Phase numbering.
- Required section headings.

## Durability Gate

Before finalization, confirm that a reader can understand the implementation sequence without access to:

- Source code.
- File paths.
- Scout reports.
- Progress logs.
- The original conversation.

If implementation file organization changes while the intended behavior and stable contracts remain the same, `plan.md` should remain useful.
