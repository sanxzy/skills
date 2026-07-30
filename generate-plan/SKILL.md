---
name: generate-plan
version: 1.0.0
description: |
  Generate or resume one finalized tracer-bullet implementation plan for exactly one explicitly selected feature from conversation context or a `spec.md` artifact. Writes `_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/plan.md`, preserves per-feature progress and evidence, overwrites existing canonical plans without revisions, and delegates planning evidence discovery to bundled `plan-scout` subagents. Do not use for feature discovery, engineering specs, tickets, code implementation, or broad planning that does not identify one target feature.
---

Produces a durable implementation plan for exactly one feature per invocation. It synthesizes:

1. The current conversation.
2. A single source `spec.md`, when supplied or discoverable.
3. Fresh feature-specific planning evidence from the active working tree, gathered by bundled `plan-scout` subagents when relevant code exists.

The final artifact is written to:

```text
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/plan.md
```

The main host owns source resolution, synthesis, quality validation, user interaction, overwrite handling, write verification, and the progress log. Scouts gather evidence only and never propose or write the final plan.

## Trigger Boundary

Run this skill only for an explicit request to create, regenerate, replace, revise, or resume an implementation plan for one named feature.

Do not run it for:

- Feature discovery or backlog generation.
- Engineering spec generation.
- Ticket generation.
- Casual brainstorming.
- Code implementation or modification.
- Broad planning requests that do not identify exactly one target feature.

## Core Invariants

1. One invocation processes exactly one explicitly selected feature.
2. Prefer `spec.md` as the behavioral baseline when supplied or discoverable.
3. When no `spec.md` exists, proceed only after conversation context explicitly establishes backlog, feature identifier, feature title, behavior, scope, and exclusions.
4. Never infer `<NNN>` through assumptions.
5. Never process a whole `features.md` backlog in one invocation.
6. Never guess through plan-affecting ambiguity.
7. Never write source code, tests, configuration, dependencies, lockfiles, or unrelated artifacts.
8. Always overwrite canonical `plan.md` on successful generation; do not create revisions.
9. Always write and verify the canonical current plan at `plan.md`.
10. Keep final `plan.md` durable and free of brittle source paths, concrete function names, concrete signatures, code snippets, command transcripts, scout citations, unresolved alternatives, and open questions.

## Managed Paths

For backlog `<backlog_name>` and feature `<NNN>`, this skill manages only:

```text
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/plan.md
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/progress.md
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/scouts/round-<RRR>/
```

Preserve every unrelated artifact under the backlog directory.

## Source Resolution

The user must identify the target feature, for example `F003`, `003`, a path to `spec.md`, or explicit feature text containing a stable feature identifier.

### Source from `spec.md`

When a `spec.md` source is available:

1. Read `spec.md`.
2. Extract the feature identifier, title, problem, solution, user stories, acceptance criteria, implementation decisions, testing decisions, scope exclusions, and notes.
3. Reuse the feature number for `<NNN>` and title identity.
4. Infer `<backlog_name>` from the path when the path matches `_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/spec.md`.
5. Focus the entire workflow on that one feature.
6. Treat `spec.md` as the source behavior contract unless the user explicitly says it is stale.

If the selected `spec.md` cannot be located unambiguously, ask once for the path or target feature. Do not choose a feature.

When `spec.md` and conversation context materially disagree about actors, behavior, boundaries, dependencies, or outcomes, treat `spec.md` as baseline context but hand the conflict to `discussion`. Clarified decisions may refine or supersede the baseline; neither source silently overrides the other.

### Source from conversation only

When no `spec.md` source applies:

1. Require explicit backlog name.
2. Require explicit feature identifier matching `F<NNN>` or `<NNN>`.
3. Require explicit feature title.
4. Require explicit desired outcome, actors, in-scope behavior, out-of-scope behavior, and known dependencies.
5. Use clarified conversation as the source behavior contract.

If any required source identity or behavior context is missing, hand off to `discussion`. Do not infer or generate `<NNN>` through assumptions.

## Required Context Gate

Generation may proceed only when all of the following are clear for the one target feature:

1. Backlog name.
2. Feature identifier and title.
3. Source behavior contract from `spec.md` or clarified conversation.
4. Desired outcome.
5. Relevant actors.
6. User stories or behavior labels covered by the plan.
7. In-scope behavior.
8. Out-of-scope behavior or exclusions.
9. Known dependencies and dependency boundaries.
10. Whether existing implementation evidence is needed for planning.

Use supplied input and current conversation. Discover objective source locations and repository facts yourself.

If plan-affecting context is unclear or incomplete:

1. Gather every known ambiguity into one handoff.
2. Load and run the `discussion` skill in the same conversation when supported.
3. Give `discussion` the named gaps and relevant background.
4. Wait until `discussion` reaches explicit shared-understanding completion.
5. Resume this workflow with the enriched context.

If same-session loading or automatic resume is unavailable, append a paused event with `resume-requires=complete-discussion`, stop, and tell the user exactly which gaps must be resolved.

If a discussion handoff is abandoned or not completed, keep the workflow paused. Do not synthesize or write `plan.md`.

## Artifact Language

Use the language of the source spec or product requirements in conversation. If mixed or unclear, use the repository's dominant documentation language. Preserve established product terms verbatim.

Keep contract tokens unchanged, including:

- `F001`, `F002`, and other feature identifiers.
- `US001`, `US002`, and other user story identifiers.
- Required section headings defined by reference formats.
- Progress event types.

## Progress and Recovery

The authoritative per-feature workflow state is:

```text
_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/progress.md
```

Follow [PROGRESS-LOG-FORMAT.md](./references/PROGRESS-LOG-FORMAT.md) exactly.

Only the main host may read workflow state for orchestration or append progress events. Scouts never write the progress log.

A fresh generation appends the next `Round NNN` section. An explicit resume continues the latest non-terminal round. The current round number is used in scout report paths.

Before starting fresh work for a feature, read `progress.md` when it exists. If the latest round is non-terminal, refuse overlap and require explicit resume or cancellation first.

## Existing Plan Disposition

If canonical `plan.md` already exists before fresh work:

1. Treat the user's generation request as authorization to overwrite the canonical plan.
2. Do not ask for archival or revision handling.
3. Append `existing-plan-dispositioned` with `disposition=overwrite` and `existing=<path>`.
4. Preserve progress history and scout reports.
5. Overwrite `plan.md` only after the new plan passes quality gate.

## Workflow

### Step 1: Capture normalized context

After the required context gate passes:

1. Determine artifact language.
2. Resolve source identity, backlog name, feature number, feature title, source text, desired outcome, actors, user stories or behavior labels, in-scope behavior, out-of-scope behavior, and known dependencies.
3. Create the managed directories when needed.
4. Read feature `progress.md` if present and apply recovery or overlap rules.
5. Start or resume the workflow round.
6. Append `source-resolved` and `context-captured` events.
7. Append `existing-plan-dispositioned` after checking whether canonical `plan.md` exists.

The progress log must contain enough normalized context to resume even when the original conversation is unavailable.

### Step 2: Determine discovery mode

The host may perform light objective discovery to classify the repository and set up the workflow, such as inspecting top-level structure, obvious project manifests, documentation indexes, source directories, and test directories.

This is not the primary semantic investigation for the plan. If the host cannot confidently determine that no relevant implementation exists from light discovery, use `plan-scout`.

#### Greenfield or no relevant implementation

When light host discovery verifies that no implementation relevant to the target feature exists:

- Launch zero scouts.
- Record greenfield mode in progress.
- Synthesize from confirmed source context.
- Label architectural decisions and testing seams as proposed.
- Append `coverage-evaluated` with `reports=0` and `reason=greenfield-context-sufficient` when adequate.

#### Established repository

Use fresh targeted discovery against the active working tree, including uncommitted changes. Do not reuse `feat-scout` or `spec-scout` reports as canonical plan evidence. An explicit resume may reuse only completed `plan-scout` reports produced by the same per-feature workflow round when their scopes remain valid.

### Step 3: Plan scout scopes

The host defines focused discovery topics before delegation.

Each topic must:

- Use a concise kebab-case name.
- Own a distinct feature-specific planning question or behavior area.
- Contribute directly to stable contracts, vertical slice boundaries, dependencies, risks, or testing seams.
- State included and excluded scope.
- Name concrete questions to resolve.
- Write to `_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/scouts/round-<RRR>/<topic>.md`.

Useful topic categories include:

- Existing implementation seams and integration boundaries.
- Data, state, schema, migration, and contract implications.
- User-facing, API-facing, job-facing, or operator-facing entry points.
- Testing and validation seams.
- Dependencies, reliability, security, privacy, accessibility, and operational constraints.
- Natural end-to-end slice ordering.

Limited intentional overlap is allowed when separate questions require shared evidence. Tell scouts to cross-reference related topics and avoid duplicating another report's full analysis.

Independent topics may run in parallel when supported; otherwise run sequentially. Before delegation, sort topics lexicographically and append `scout-wave-planned` with cycle, wave, topics, coverage targets, and recoverable briefs.

### Step 4: Delegate `plan-scout`

Delegate with every required input:

| Input | Description |
|---|---|
| `backlog_name` | Normalized backlog identifier. |
| `feature_id` | `F<NNN>` for the selected feature. |
| `feature_context` | Feature title, source behavior contract, user stories or behavior labels, relevant conversation decisions, scope, exclusions, and known dependencies. |
| `topic` | Unique kebab-case discovery topic for the current round. |
| `discovery_scope` | Precise included and excluded discovery boundaries. |
| `questions_to_resolve` | Specific planning evidence questions this report must answer. |
| `repository_root` | Absolute active working-tree root. |
| `report_path` | Exact round-scoped scout report path. |

When the platform supports bundled subagent invocation, invoke `plan-scout` with the full contract and wait for its completion return. Parallel waves are expressed as multiple independent scout delegations when supported.

If the platform lacks required subagent support, append a paused event containing the exact scout briefs and `resume-requires=subagent-delegation-support`; tell the user delegation support is required. The host must not replace `plan-scout` as the primary semantic discovery mechanism for established repositories.

A scout returns only:

```text
report_path: <path>
status: completed | blocked
reason: <required only when blocked>
```

The on-disk report is canonical. Read every returned report before evaluating coverage.

If a scout returns `REJECTED`, treat it as a consumed invocation, record it as blocked, correct coordinator input, and retry the same topic once. If rejected again, pause with `resume-requires=correct-coordinator-inputs`.

### Step 5: Apply the discovery budget

One authorized discovery cycle allows:

- At most five scout invocations per wave.
- At most three waves.
- At most fifteen total scout invocations.

Initial scouts, corrected retries, blocked retries, and narrower replacements all consume budget.

If complete evidence remains unavailable after the cycle:

1. Append `coverage-evaluated` with uncovered areas.
2. Append `workflow-paused` with `reason=discovery-cycle-exhausted`, uncovered areas, and exact authorization needed.
3. Ask whether to authorize another bounded cycle.
4. If authorized, append `workflow-resumed` and continue with the next cycle number inside the same round.
5. If declined, append `workflow-cancelled` and do not write `plan.md`.

### Step 6: Recover from blocked scouts

For a blocked scope:

1. Read the blocked report and reason.
2. Retry the same scope once with corrected instructions and a unique topic such as `<topic>-retry`.
3. If still blocked, try one narrower replacement scope with a unique topic such as `<topic>-narrowed`.
4. Preserve every report for auditability.
5. If recovery requires more discovery budget, pause for authorization.
6. If adequate evidence remains unavailable, pause with unresolved coverage and do not write `plan.md`.

Never skip a failed required scope and claim complete coverage.

### Step 7: Evaluate evidence sufficiency

Before synthesis, verify that source context and scout reports collectively establish enough evidence for the selected feature's:

- Source behavior contract.
- Stable architectural decisions.
- Current relevant implementation seams, or valid greenfield mode.
- Interface, data, state, integration, and dependency boundaries relevant to slicing.
- Testing and verification seams.
- Natural vertical slice ordering and prerequisites.
- Failure, security, privacy, reliability, accessibility, migration, rollout, and operational constraints when relevant.
- Conflicts, unknowns, and dependency boundaries.

If completed scout reports become stale because `discussion` changes feature scope, keep unaffected reports, mark affected topics stale in progress, and launch replacement or supplemental topics in a later wave within the same round and authorized cycle.

### Step 8: Resolve plan-affecting ambiguity

When source context and codebase evidence leave behavior, material scope, stable contracts, dependencies, testing seams, or vertical slice ordering ambiguous:

1. Gather all known ambiguities into one handoff.
2. Append `ambiguity-handoff-started` with affected topics and questions.
3. Run the same-session `discussion` handoff described in the Required Context Gate.
4. Append `ambiguity-handoff-completed` after explicit shared-understanding confirmation.
5. Append a new `context-captured` event with clarified decisions.
6. Keep unaffected scout reports.
7. Replace or supplement only affected reports.
8. Reapply coverage evaluation.

Do not send ordinary missing implementation to `discussion`.

### Step 9: Synthesize the plan

Synthesize only after complete coverage and resolved intent.

Follow [PLAN-FORMAT.md](./references/PLAN-FORMAT.md) exactly.

The final plan must:

1. Use `# Plan: F<NNN> — <Feature Title>`.
2. Include exactly one `> Source: ...` blockquote.
3. Include `## Architectural decisions`.
4. Include sequential `## Phase <N>: <Title>` sections.
5. Use tracer-bullet vertical slices.
6. Include `**User stories covered**`, `### What to build`, and `### Acceptance criteria` for every phase.
7. Preserve stable story identifiers such as `US001` when available.
8. Describe durable implementation guidance without brittle source references.
9. Order phases by prerequisites and natural user journey.
10. Keep the plan independently understandable.

### Step 10: Apply the quality gate

The main host alone performs this gate. Do not delegate to a reviewer.

Before writing `plan.md`, verify all of the following:

#### Source traceability

- Exactly one target feature is identified.
- Source identity is recorded in progress.
- The plan source is `spec.md` or clarified conversation.
- Source conflicts, if any, were resolved through discussion.

#### Tracer-bullet quality

- Every phase is a thin vertical slice.
- Every phase is demoable or verifiable on its own.
- No phase is merely a horizontal technical layer.
- Phase ordering reflects prerequisites and the natural user journey.
- User stories or behavior labels are covered completely without unrelated additions.

#### Planning completeness

- Architectural decisions are durable and sufficient to keep phases coherent.
- Relevant success, non-success, boundary, permission, validation, accessibility, security, privacy, reliability, dependency, and operational behavior is represented in the appropriate phase.
- Testing and verification expectations are included in phase acceptance criteria or durable testing-seam decisions.
- No unresolved plan-affecting ambiguity remains.

#### Format and durability

- Required sections and headings match `PLAN-FORMAT.md`.
- Phase numbers are continuous.
- No source file paths, concrete function signatures, function names, code snippets, command transcripts, scout-report citations, or progress citations appear in `plan.md`.
- No unresolved alternatives or open questions appear.
- The plan remains understandable without source code, scout reports, progress logs, or the original conversation.

If a check fails:

- Return plan ambiguity to `discussion`.
- Return missing or conflicting evidence to scouting.
- Fix synthesis or formatting defects internally and repeat the gate.
- Never write a partial or draft `plan.md`.

Append `quality-gate-evaluated` only after the gate passes or after recording the defect path.

### Step 11: Write and verify the finalized artifact

After quality gate:

1. Write `plan.md` using the quality-gated content.
2. Re-read `plan.md` before declaring it finalized.
3. Verify it matches the quality-gated content and required format.
4. If incomplete, malformed, or inconsistent, correct that same write and re-read.
5. If a verified artifact cannot be established, append `workflow-paused` with `reason=plan-write-verification-failed` and do not complete.
6. Once verified, append `plan-write-verified` with `overwritten=true` when a prior canonical plan existed, otherwise `overwritten=false`.
7. Append `workflow-completed` with artifact path, phase count, overwritten status, and scout report count.
8. Retain all scout reports and progress history.

## Completion Response

Return only:

- Finalized `plan.md` path.
- Number of phases.
- Whether an existing plan was overwritten.
- Number of retained scout reports for the completed round.

Do not repeat the plan in chat.

## `plan-scout` Reference

`plan-scout` is a bundled read-only discovery agent.

**Required inputs:** `backlog_name`, `feature_id`, `feature_context`, `topic`, `discovery_scope`, `questions_to_resolve`, `repository_root`, `report_path`.

**Canonical output:** `_xzy-ai/sprints/<backlog_name>/plans/features/<NNN>/scouts/round-<RRR>/<topic>.md` using the agent's embedded canonical schema, mirrored for human reference in [SCOUT-REPORT-FORMAT.md](./references/SCOUT-REPORT-FORMAT.md).

**Return:** report path, `completed` or `blocked`, and blocked reason when applicable.

## Constraints

1. Do not process more than one feature per invocation.
2. Do not choose a feature automatically.
3. Do not infer `<NNN>` without explicit source identity.
4. Do not write `plan.md` before complete evidence coverage and a passed quality gate.
5. Do not write source code, tests, configuration, dependencies, lockfiles, or unrelated artifacts.
6. Overwrite canonical `plan.md` only after quality gate; do not create revisions.
7. Preserve all scout reports and progress history.
8. Keep `plan.md` free of file paths, concrete function signatures, function names, code snippets, command transcripts, scout citations, unresolved alternatives, and open questions.
9. Only the main host writes feature `progress.md`.
10. Do not exceed five scout invocations per wave, three waves, or fifteen invocations per authorized discovery cycle.
11. Treat the active working tree, including uncommitted changes, as current state.
12. Keep all workflow operations and artifacts inside the active repository root.

## References

- [Plan Artifact Format](./references/PLAN-FORMAT.md)
- [Scout Report Format](./references/SCOUT-REPORT-FORMAT.md)
- [Progress Log Format](./references/PROGRESS-LOG-FORMAT.md)
