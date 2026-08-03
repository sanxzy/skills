# Plan Scout Report Format

The canonical scout report lives at:

```text
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/scouts/round-<RRR>/<topic>.md
```

`plan-scout` reports are technical evidence artifacts. They may include concrete file paths, symbols, tests, commands, and line references. The final `plan.md` must not leak brittle file paths outside the canonical repository-relative `references/` scope, function names, concrete signatures, code snippets, scout citations, or command transcripts.

## Required Structure

Begin every report with:

```markdown
# Plan Scout Report — <Topic title>

**Backlog:** `<backlog_name>`
**Feature:** `<feature_id>`
**Topic:** `<topic>`
**Status:** `completed` | `blocked`
**Repository root:** `<absolute repository root>`
**Report path:** `<report_path>`
```

Then include these sections in this exact order, using `None` for empty sections:

1. `Scope Investigated`
   - Included boundaries.
   - Excluded boundaries.
   - Every delegated question to resolve.
2. `Source Behavior Contract`
   - Relevant behavior from the source spec or clarified conversation.
   - User stories or behavior labels this topic affects.
   - Boundaries, exclusions, and dependencies.
3. `Current Implementation Seams`
   - Existing entry points, responsibilities, module boundaries, data boundaries, integration boundaries, and limitations relevant to implementation planning.
4. `Stable Contracts and Decisions`
   - Durable routes, models, schemas, APIs, events, permissions, integration behavior, failure handling, and constraints supported by evidence or proposed for greenfield mode.
5. `Vertical Slice Opportunities`
   - Thin end-to-end slices this evidence supports.
   - Required prerequisites or natural ordering constraints.
   - What makes each slice independently demoable or verifiable.
6. `Testing and Verification Seams`
   - Existing behavioral tests, safe validation commands and results when run, usable test seams, coverage gaps, and proposed seams for greenfield mode.
7. `Risks, Constraints, and Dependencies`
   - Technical, operational, security, privacy, reliability, accessibility, dependency, migration, compatibility, or rollout constraints relevant to planning.
8. `Conflicts and Unknowns`
   - Contradictory evidence or unresolved planning questions, or `None`.
9. `Conclusions`
   - Explicit evidence-backed answer for every delegated question.
   - Planning-relevant findings.
   - Scope coverage: `complete` or `incomplete`.
   - Evidence confidence: `high`, `medium`, or `low`.
   - Blocking reason when report status is `blocked`, otherwise `None`.
   - Recommended evidence-only follow-up discovery or `None`.

## Evidence Reference Rules

Technical evidence is expected in scout reports.

For source evidence, include:

- Repository-relative path.
- Line number or line range whenever available.
- Function, class, route, command, configuration key, test name, or other precise symbol when relevant.
- What the evidence proves or fails to prove.

For command evidence, include:

- Exact command.
- Why it was safe and non-mutating.
- Relevant result.
- Exit status when available.

For source `spec.md` or conversation context, distinguish desired behavior from current implementation evidence.

Never include secret values, credentials, tokens, private keys, session material, personal data, or sensitive environment contents in a report or return value. Reference a sensitive configuration key by name and path only, redact values as `[REDACTED]`, and describe planning implications without reproducing protected data.

Never claim that a file's existence alone proves a viable implementation seam.

## Output Contract

After writing and verifying the report, the scout returns only:

```text
report_path: _xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/scouts/round-<RRR>/<topic>.md
status: completed
```

or:

```text
report_path: _xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/scouts/round-<RRR>/<topic>.md
status: blocked
reason: <concise operational blocker>
```

The report on disk is canonical. Do not return its content inline.
