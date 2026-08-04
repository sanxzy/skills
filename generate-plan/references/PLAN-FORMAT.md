# Plan Artifact Format

The finalized implementation plan lives at:

```text
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/plan.md
```

It becomes canonical current output after the host writes it, re-reads it, verifies it against the quality-gated content and this format, and records `plan-write-verified` followed by `workflow-completed` in progress.

## Purpose

`plan.md` communicates a practical multi-phase implementation plan for exactly one feature. It must be independently understandable without reopening the source conversation, scout reports, or progress log; it may rely on the specific read-only reference files cited under the canonical `references/` path rule.

The plan uses tracer-bullet vertical slices: each phase delivers a narrow, complete, verifiable path through all relevant integration layers. It should read like the existing `to-plan` output while fitting the `_xzy-ai` sprint artifact structure.

## File Path References

The plan may contain workspace-relative file paths only in the canonical form `references/<path>` (for example `references/codex/codex-rs/config/src/state.rs`), referencing files inside the single top-level `references/` directory at the workspace root. Such paths must:

- Use forward slashes and start with exactly `references/` — no leading `./` or `/`, and no `.` or `..` segments.
- Resolve to an existing regular file, not a directory. Symlinks are allowed only when they resolve to a regular file within `references/`.
- Be **path-only** in the final artifact: no line numbers, no line ranges, and no symbols are included. The coordinator re-expresses scout `path:line` evidence as durable prose plus the stable path; line-level and symbol detail stays inside scout reports and is not carried verbatim into `plan.md`.

Citations are **relevance-based**, not a fixed count: cite a `references/<path>` inline wherever a referenced file provides context, behavior, architecture, an implementation pattern, or other evidence that grounds a claim (Architectural decisions, phase "What to build", phase acceptance criteria that depend on reference seams, and similar). Provenance-only citations (the Source blockquote or a notes area) do not satisfy the requirement when substantive evidence exists.

Every inline citation also appears in the trailing `## References` section (see below). All other file paths — absolute paths, `./references/...`, anything outside workspace-root `references/`, and directory paths — remain prohibited. `references/` is read-only input: the generator and scouts never create, modify, move, rename, or delete files under it.

**Reference-aware mode:** enter reference-aware mode only when the user explicitly asks to use `references/` as the source of truth. Mere directory existence is not by itself a mandate. In reference-aware mode, embed relevant `references/<path>` citations throughout wherever referenced files provide evidence. If `references/` does not exist and the user did not require it, generate normally with no citations required. If the user explicitly requires `references/` but the directory does not exist, reject the request rather than proceeding without it.

**Path validity:** path validity rests on the current-round scout reports the coordinator trusts. Scouts verify each cited `references/<path>` resolves to an existing regular file under the workspace-root `references/` directory before writing their reports; the coordinator does not re-resolve citation paths at write time. A `references/` path that does not resolve is a format and durability defect.

## Required Structure

Use exactly these top-level sections in this order after the title:

```markdown
# Plan: F<NNN> — <Feature Title>

> Source: <durable logical source identifier>

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

---

## References

<Union of all inline `references/<path>` citations, one per line, deduplicated and lexicographically sorted, or `None` when the plan carries no inline citations.>
```

The only allowed top-level sections, in this exact order after the title, are:

1. `## Architectural decisions`
2. One or more `## Phase <N>: <Title>` sections
3. A trailing `## References` section

No other top-level sections are allowed. Add, remove, or rename architectural-decision bullets as appropriate, but preserve the `Architectural decisions` section. The `## References` section is always present, even when empty (content `None`).

### References

The `## References` section is the trailing top-level index of cited reference files. Rules:

1. It lists exactly the union of all inline `references/<path>` citations in the plan, deduplicated.
2. Entries are deterministically sorted in lexicographic order.
3. Entries are path-only (`references/<path>`), one per line, with no line numbers or symbols.
4. Index-only paths are prohibited: every entry in `## References` must also appear inline in the plan body.
5. When the plan carries no inline citations, the section body is exactly `None`.
6. In reference-aware mode, substantive evidence-backed claims must carry nearby inline citations, so an empty or near-empty `## References` section in that mode signals missing citations, not a valid outcome.

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

Use one Markdown blockquote immediately after the title. Use a durable logical source identifier rather than a file path:

```markdown
> Source: feature F003 specification
```

When generated from clarified conversation only, use a durable logical source such as:

```markdown
> Source: clarified conversation for F003
```

Do not cite scout reports, progress logs, or file paths outside the canonical `references/` scope in the final plan; qualifying workspace-relative `references/` paths remain permitted under the File Path References rule. The Source blockquote itself must remain a durable logical source identifier and must not carry file paths of any kind.

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
3. Do not include file paths except qualifying `references/` paths; keep concrete function signatures, code snippets, and scout citations prohibited.
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
8. Do not include brittle implementation details such as exact files outside the canonical `references/` scope, function names, concrete signatures, code snippets, or command transcripts.
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

- Source code, except the specific files cited by qualifying `references/` paths.
- File paths, except the specific `references/` paths cited in the plan.
- Scout reports.
- Progress logs.
- The original conversation.

The cited `references/` files are the evidence-recovery mechanism for reference-grounded claims. A reader or delegated agent must be able to re-open every cited `references/` file and recover the evidence behind those claims without scout reports, progress logs, or the original conversation. Citations in the final plan are path-only; the plan must preserve enough durable prose to explain what each cited file establishes.

If implementation file organization changes while the intended behavior and stable contracts remain the same, `plan.md` should remain useful. The plan remains useful while the specific files cited under `references/` are preserved.
