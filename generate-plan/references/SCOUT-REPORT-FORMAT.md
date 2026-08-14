# Plan Scout Report Format

The canonical scout report lives at:

```text
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/scouts/round-<RRR>/<topic>.md
```

`plan-scout` reports are technical evidence artifacts. They may include concrete file paths, symbols, tests, commands, and line references. The final `plan.md` must not leak brittle file paths under the project root, function names, concrete signatures, code snippets, or command transcripts.

## Required Structure

Begin every report with:

```markdown
# Plan Scout Report — <Topic title>

**Backlog:** `<backlog_name>`
**Feature:** `<feature_id>`
**Topic:** `<topic>`
**Status:** `completed` | `blocked`
**Workspace root:** `<absolute workspace root>`
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

## Project Root Resolution

The scout receives `workspace_root` (absolute workspace root) and `project_root` (absolute project codebase root resolved from `_xzy-ai/project-root.md`). The project root is the mutable codebase under development; its contents are never cited in the final `plan.md`, but any other regular file on the machine may be cited when relevant.

## Evidence Reference Rules

Technical evidence is expected in scout reports.

For source evidence (under the project root), include:

- Project-root-relative path.
- Line number or line range whenever available.
- Function, class, route, command, configuration key, test name, or other precise symbol when relevant.
- What the evidence proves or fails to prove.

For reference-material evidence, use either a canonical workspace-root-relative form `<path>:<line-range>` or an absolute path with an optional line range for regular files outside the project root. Relative paths use forward slashes with no leading `./`, `/`, or `..` segments. For repository-internal references, prefix the repository-relative path with its workspace-root-relative base when applicable. No bare repo-internal paths are acceptable.

Before writing the report, the scout MUST verify every cited reference-material path resolves to an existing regular file outside the project root. Symlinks are allowed only when they resolve to a regular file outside the project root. Do not fabricate citations: if a referenced file cannot be verified, record the claim without a citation and note the missing evidence in `Conflicts and Unknowns`.

Project-root (codebase) evidence may keep precise paths and symbols inside the scout report (reports are working artifacts), but the coordinator re-expresses that evidence in the final `plan.md` as durable prose plus feature identifiers — project-root paths are not carried into `plan.md` verbatim.

Only current-round evidence that the coordinator intentionally uses should feed the final artifact; prior-round or stale evidence must not be silently reused. Scout reports retain precise `path:line` and symbol names internally even though the final plan cites only path-only workspace entries.

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
