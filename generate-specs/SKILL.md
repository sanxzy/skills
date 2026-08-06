---
name: generate-specs
version: 1.0.0
description: |
  Generate or resume one finalized engineering specification for exactly one explicitly selected feature. Use only when the user explicitly asks to create, regenerate, replace, revise, or resume a spec for one named feature from conversation context or a `features.md` artifact. Writes `_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/spec.md`, preserves per-feature progress and evidence, and delegates current-codebase discovery to bundled `spec-scout` subagents. Do not use for feature discovery, brainstorming, architecture-only design, implementation plans, tickets, or code changes.
---

Produces a durable engineering specification for exactly one feature per invocation. It synthesizes:

1. The current conversation.
2. A single explicitly selected feature from `features.md`, when supplied or discoverable.
3. Fresh feature-specific evidence from the active working tree, gathered by bundled `spec-scout` subagents when relevant code exists.

The final artifact is written to:

```text
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/spec.md
```

The main host owns feature resolution, synthesis, quality validation, user interaction, archival, write verification, and the progress log. Scouts gather evidence only and never propose or write final specs.

## Trigger Boundary

Run this skill only for an explicit request to create, regenerate, replace, revise, or resume an engineering spec for one named feature.

Do not run it for:

- Feature discovery or backlog generation.
- Casual brainstorming.
- Architecture-only design.
- Implementation planning.
- Ticket generation.
- Code implementation or modification.
- Broad design requests that do not identify exactly one target feature.

## Core Invariants

1. One invocation processes exactly one explicitly selected feature.
2. Never auto-select the next unspecced feature.
3. Never process a whole `features.md` backlog in one invocation.
4. Never guess through behavior-affecting ambiguity.
5. Never write source code, tests, configuration, dependencies, or unrelated artifacts.
6. Always preserve finalized spec history by archiving before regeneration.
7. Always write and verify the canonical current spec at `spec.md`.
8. Do not create speculative alternate specs in v1.
9. Do not maintain a backlog-level specs manifest.

## Project Location and Citation Scope

The active workspace is the current working directory (`<cwd>`). Before any discovery, feature resolution, citation handling, or artifact write:

1. Read `<cwd>/_xzy-ai/project-root.md`.
2. Require exactly one non-empty project-root entry. It must be a `<cwd>`-relative path (forward slashes, no leading `/`, no `.` or `..` segments) that resolves to a directory inside `<cwd>`.
3. Treat `<cwd>/<project-root-entry>` as the project codebase root. Do not assume a particular project layout beneath it.
4. Use the project root as the only codebase for repository discovery and pass its absolute path to scouts as `project_root`.
5. If `project-root.md` is missing, empty, malformed, or points outside `<cwd>`, pause and ask the user to correct it. Do not guess the project root.

Reference-aware behavior is manual: the workflow enters reference-aware mode only when the user explicitly asks to use references as a source of truth. Citable material may be anywhere under `<cwd>` except the project root and `_xzy-ai/` (which holds scout reports, progress logs, and generated workflow artifacts). Final citations use normalized `<cwd>`-relative paths with forward slashes, no `.` or `..` segments, and resolve to existing regular files verified by current-round scouts. Citable material is read-only.

## Managed Paths

For backlog `<backlog_name>` and feature `<NNN>`, this skill manages only:

```text
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/spec.md
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/progress.md
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/revisions/
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/scouts/round-<RRR>/
```

Preserve every unrelated artifact under the backlog directory.

## Feature Resolution

The user must name the target feature, for example `F003`, `003`, or provide the full feature text directly.

### Source from `features.md`

When a `features.md` source is available:

1. Read `features.md`.
2. Locate the explicitly named target feature.
3. Extract only that feature's identifier, title, and description.
4. Reuse the feature number for `<NNN>` and title identity.
5. Focus the entire workflow on that one feature.
6. Read neighboring features only as dependency context when needed.

If the selected feature cannot be located unambiguously, ask once for the target feature or source text. Do not choose a feature.

When `features.md` and conversation context materially disagree about actors, behavior, boundaries, or outcomes, treat the finalized `features.md` as baseline context but hand the conflict to `discussion`. Clarified decisions may refine or supersede the baseline; neither source silently overrides the other.

### Source from conversation only

When no `features.md` source applies:

1. Infer concise lowercase kebab-case `<backlog_name>` from the desired outcome using the same normalization style as `generate-features`.
2. Use the next available zero-padded number under `_xzy-ai/sprints/<backlog_name>/specs/features/`, beginning with `001`.
3. Treat `F<NNN>` as a local feature-spec identifier, not a promise to match a future `features.md` number.
4. Do not automatically renumber or reconcile if a later `features.md` assigns a different identifier.

Ask for a backlog name only when two or more materially different outcome-based names are equally plausible, or no concise two-to-five-word goal phrase distinguishes this backlog from existing backlogs.

## Required Context Gate

Generation may proceed only when all of the following are clear for the one target feature:

1. Explicit feature target or supplied feature text.
2. Desired outcome.
3. Relevant actors.
4. In-scope behavior.
5. Out-of-scope behavior or exclusions.

Use supplied input and current conversation. Discover objective source locations and repository facts yourself.

If behavior-affecting context is unclear or incomplete:

1. Gather every known ambiguity into one handoff.
2. Load and run the `discussion` skill in the same conversation when supported.
3. Give `discussion` the named gaps and relevant background.
4. Wait until `discussion` reaches explicit shared-understanding completion.
5. Resume this workflow with the enriched context.

If same-session loading or automatic resume is unavailable, append a paused event with `resume-requires=complete-discussion`, stop, and tell the user exactly which gaps must be resolved.

If a discussion handoff is abandoned or not completed, keep the workflow paused. Do not synthesize or write `spec.md`.

## Reference-Aware Mode

Reference-aware mode is a scope of how the final `spec.md` cites evidence. It is manual: entered only when the user explicitly asks to use references as a source of truth.

### Citation scope

- Only files under the workspace root and outside the project codebase root (resolved from `_xzy-ai/project-root.md`) and outside `_xzy-ai/` may be cited in the final `spec.md`.
- Paths under the project root, `AGENTS.md`, `ROADMAP.md`, `_xzy-ai/`, scout reports, and progress logs are prohibited in the final `spec.md`.

### Driving signal

- Enter reference-aware mode only when the user explicitly asks to use references. Do not enter it automatically merely because citable reference material exists outside the project root.
- If no citable material exists and the user did not require it, generate normally with no citations required.

### Behavior by context

- If the user explicitly asks to use references → enter reference-aware mode: include relevant workspace-root-relative path citations inline wherever referenced files provide context, behavior, architecture, implementation-pattern, or other evidence (Implementation Decisions, Testing Decisions, stories/criteria, and so on). Preserve any additional user instructions or notes verbatim (for example "create an original version in our project to avoid copyright issues") in the appropriate artifact section (Further Notes or equivalent) and in progress/generation notes.
- If reference-aware mode is active but investigation finds NO relevant evidence → report this to the user and ask how to proceed (continue without citations / add reference material first / other). Do not fabricate citations.
- If the user explicitly REQUIRES citations but no citable material exists → reject the request rather than proceeding without it.

### Relevance, not a fixed count

Whether citations are required depends on the presence of relevant evidence, not on a fixed number. Provenance-only citations (for example in Further Notes) do NOT satisfy the requirement when substantive evidence exists.

## Artifact Language

Use the language of the product requirements in the conversation or source feature. If mixed or unclear, use the repository's dominant documentation language. Preserve established product terms verbatim.

Keep contract tokens unchanged, including:

- `F001`, `F002`, and other feature identifiers.
- `US001`, `US002`, and other user story identifiers.
- `AC01`, `AC02`, and other acceptance-criteria identifiers.
- Required section headings defined by reference formats.
- Progress event types.

## Progress and Recovery

The authoritative per-feature workflow state is:

```text
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/progress.md
```

Follow [PROGRESS-LOG-FORMAT.md](./references/PROGRESS-LOG-FORMAT.md) exactly.

Only the main host may read workflow state for orchestration or append progress events. Scouts never write the progress log.

A fresh generation or regeneration appends the next `Round NNN` section. An explicit resume continues the latest non-terminal round. The current round number is used in scout report paths.

Before starting fresh work for a feature, read `progress.md` when it exists. If the latest round is non-terminal, refuse overlap and require explicit resume or cancellation first.

## Existing Spec Disposition

If canonical `spec.md` already exists before fresh work:

1. Ask the user to choose only:
   - `keep and stop`
   - `regenerate with archival`
2. If the user keeps it, append the appropriate disposition or cancellation event and stop.
3. If the user regenerates, archive the exact current `spec.md` under the next revision file before writing the new canonical spec.

Revision files live at:

```text
_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/revisions/<RRR>.md
```

`<RRR>` starts at `001` and increments continuously. Never delete, prune, or rewrite revisions, scout reports, or progress history unless the user requests a separate maintenance task.

## Workflow

### Step 1: Capture normalized context

After the required context gate passes:

1. Determine artifact language.
2. Resolve source identity, backlog name, feature number, title, source text, desired outcome, actors, in-scope behavior, out-of-scope behavior, and known dependencies.
3. Create the managed directories when needed.
4. Read feature `progress.md` if present and apply recovery or overlap rules.
5. Start or resume the workflow round.
6. Append `feature-resolved` and `context-captured` events.

The progress log must contain enough normalized context to resume even when the original conversation is unavailable.

### Step 2: Determine discovery mode

The host may perform light objective discovery to classify the repository and set up the workflow, such as inspecting top-level structure, obvious project manifests, documentation indexes, and high-level signals.

This is not the primary semantic investigation for the feature. If the host cannot confidently determine that no relevant implementation exists from light discovery, use `spec-scout`.

#### Greenfield or no relevant implementation

When light host discovery verifies that no implementation relevant to the target feature exists:

- Launch zero scouts.
- Record greenfield mode in progress.
- Synthesize from confirmed feature context.
- Label implementation and testing decisions as proposed rather than existing.
- Append `coverage-evaluated` with `reports=0` and `reason=greenfield-context-sufficient` when adequate.

#### Established repository

Use fresh targeted discovery against the project codebase root (resolved from `_xzy-ai/project-root.md`), including uncommitted changes. Do not reuse `feat-scout` reports. An explicit resume may reuse only completed `spec-scout` reports produced by the same per-feature workflow round when their scopes remain valid.

### Step 3: Plan scout scopes

The host defines focused discovery topics before delegation.

Each topic must:

- Use a concise kebab-case name.
- Own a distinct feature-specific question or behavior area.
- Contribute directly to the selected feature's behavior, contracts, data, integrations, failures, or testing seams.
- State included and excluded scope.
- Name concrete questions to resolve.
- Write to `_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/scouts/round-<RRR>/<topic>.md`.

Limited intentional overlap is allowed when separate questions require shared evidence. Tell scouts to cross-reference related topics and avoid duplicating another report's full analysis.

Independent topics may run in parallel when supported; otherwise run sequentially. Before delegation, sort topics lexicographically and append `scout-wave-planned` with cycle, wave, topics, coverage targets, and recoverable briefs.

### Step 4: Delegate `spec-scout`

Delegate with every required input:

| Input | Description |
|---|---|
| `backlog_name` | Normalized backlog identifier. |
| `feature_id` | `F<NNN>` for the selected feature. |
| `feature_context` | Title, desired outcome, source text, relevant conversation decisions, scope, exclusions, and known dependencies. |
| `topic` | Unique kebab-case discovery topic for the current round. |
| `discovery_scope` | Precise included and excluded discovery boundaries. |
| `questions_to_resolve` | Specific evidence questions this report must answer. |
| `workspace_root` | Absolute workspace root. |
| `project_root` | Absolute project codebase root resolved from `_xzy-ai/project-root.md`. |
| `report_path` | Exact round-scoped scout report path. |

When the platform supports bundled subagent invocation, invoke `spec-scout` with the full contract and wait for its completion return. Parallel waves are expressed as multiple independent scout delegations when supported.

If the platform lacks required subagent support, append a paused event containing the exact scout briefs and `resume-requires=subagent-delegation-support`; tell the user delegation support is required. The host must not replace `spec-scout` as the primary semantic discovery mechanism.

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
5. If declined, append `workflow-cancelled` and do not write `spec.md`.

### Step 6: Recover from blocked scouts

For a blocked scope:

1. Read the blocked report and reason.
2. Retry the same scope once with corrected instructions and a unique topic such as `<topic>-retry`.
3. If still blocked, try one narrower replacement scope with a unique topic such as `<topic>-narrowed`.
4. Preserve every report for auditability.
5. If recovery requires more discovery budget, pause for authorization.
6. If adequate evidence remains unavailable, pause with unresolved coverage and do not write `spec.md`.

Never skip a failed required scope and claim complete coverage.

### Step 7: Evaluate evidence sufficiency

Before synthesis, verify that reports collectively establish enough evidence for the selected feature's:

- Current relevant behavior, or valid greenfield mode.
- Desired final behavior and scope.
- Relevant components and responsibilities at module/contract level.
- Interfaces and data contracts.
- Data and state behavior.
- Integrations and constraints.
- Failure, security, privacy, reliability, accessibility, and quality behavior when relevant.
- Existing or proposed testing seams.
- Conflicts, unknowns, and dependency boundaries.

If completed scout reports become stale because `discussion` changes feature scope, keep unaffected reports, mark affected topics stale in progress, and launch replacement or supplemental topics in a later wave within the same round and authorized cycle.

### Step 8: Resolve behavior-affecting ambiguity

When source context and codebase evidence leave desired behavior, material scope, contracts, data, failure handling, or testing seams ambiguous:

1. Gather all known ambiguities into one handoff.
2. Append `ambiguity-handoff-started` with affected topics and questions.
3. Run the same-session `discussion` handoff described in the Required Context Gate.
4. Append `ambiguity-handoff-completed` after explicit shared-understanding confirmation.
5. Append a new `context-captured` event with clarified decisions.
6. Keep unaffected scout reports.
7. Replace or supplement only affected reports.
8. Reapply coverage evaluation.

Do not send ordinary missing implementation to `discussion`.

### Step 9: Synthesize the spec

Synthesize only after complete coverage and resolved intent.

Write the complete final behavior contract, not merely the delta from current code. Include already-supported behavior when necessary for independent understanding.

Follow [SPEC-FORMAT.md](./references/SPEC-FORMAT.md) exactly.

Top-level sections are exactly:

1. `Problem Statement`
2. `Solution`
3. `User Stories`
4. `Implementation Decisions`
5. `Testing Decisions`
6. `Out of Scope`
7. `Further Notes`
8. `References`

The `## References` section is always present as the trailing top-level section. It contains the deduplicated, lexicographically sorted union of every inline path-only citation. Every index entry must also appear inline; when there are no citations, its body is `None`.

Rules:

- Begin with `# F<NNN> — <Feature Title>`.
- Use stable `US001`, `US002`, and `AC01`, `AC02` identifiers.
- Include Given/When/Then acceptance criteria under each user story.
- Describe one decided contract.
- Do not include unresolved alternatives, open questions, or tentative choices.
- Do not include file paths except qualifying citable paths (workspace-root-relative, outside the project root and `_xzy-ai/`). In the final artifact, citations are path-only (`<path>` with no line number or symbol). Keep concrete function signatures, scout citations, and code snippets prohibited.
- In reference-aware mode, include relevant qualifying path-only citations inline throughout substantive sections wherever referenced files provide evidence, including Implementation Decisions, Testing Decisions, stories, and criteria; provenance-only citations in Further Notes do not satisfy this requirement.
- Use logical source provenance only in Further Notes, and preserve additional user-supplied reference instructions or notes verbatim there or in an equivalent artifact section and in progress/generation notes.
- For cross-feature dependencies, specify only the selected feature's observable contract and required dependency interaction; do not redefine the dependent feature.

### Step 10: Apply the quality gate

The main host alone performs this gate. Do not delegate to a reviewer.

Before writing `spec.md`, verify all of the following:

#### Source traceability

- Exactly one target feature is identified.
- Source identity is recorded in progress.
- Further Notes use logical provenance only.
- `features.md` conflicts, if any, were resolved through discussion.

#### Behavioral completeness

- Problem and solution describe the final user-observable outcome.
- Actors, success paths, non-success paths, boundaries, and exclusions are complete.
- Every user story has Given/When/Then criteria.
- Cross-feature dependencies are bounded by contract.

#### Internal consistency

- Scope, stories, implementation decisions, data, contracts, integrations, failures, and testing seams do not contradict each other.
- No unresolved behavior-affecting ambiguity remains.
- No undecided alternatives remain.

#### Testing seam viability

- Testing decisions are evidence-backed for established repositories.
- Existing seams are preferred over new seams.
- The highest usable seam is preferred.
- Greenfield testing seams are labeled proposed.
- Tests describe external behavior rather than implementation details.

#### Format and durability

- Title follows `# F<NNN> — <Feature Title>`.
- Exactly eight required top-level sections are present in order, with `References` last and always present (`None` when empty).
- User story and acceptance-criteria identifiers are continuous.
- No file paths appear except qualifying workspace-root-relative paths outside the project root and `_xzy-ai/`, which are path-only with no line number or symbol.
- No concrete function signatures or code snippets appear.
- No scout-report citations appear; repository evidence appears only as qualifying `references/` paths.
- In reference-aware mode, evidence-backed Implementation and Testing decisions carry nearby path citations.
- The `## References` section equals the deduplicated, lexicographically sorted union of all inline citations and contains no index-only paths.
- No write-time path resolution is performed: path validity rests on the current-round scout reports, which scouts verified before writing; do not re-resolve citation paths at the gate.
- The spec remains understandable without source code, scout reports, progress logs, or the original conversation, except for the specific `references/` files it cites.

If a check fails:

- Return behavior ambiguity to `discussion`.
- Return missing or conflicting evidence to scouting.
- Fix synthesis or formatting defects internally and repeat the gate.
- Never write a partial or draft `spec.md`.

Append `quality-gate-evaluated` only after the gate passes or after recording the defect path.

### Step 11: Archive current spec when regenerating

When regenerating with an existing canonical `spec.md`:

1. Read its exact current content.
2. Write that content to the next `_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/revisions/<RRR>.md`.
3. Re-read the revision file and verify it matches the archived content.
4. Append `revision-archived` only after verification.
5. Pause if archival cannot be verified.

### Step 12: Write and verify the finalized artifact

After quality gate and required archival:

1. Write `spec.md` using the quality-gated content.
2. Re-read `spec.md` before declaring it finalized.
3. Verify it matches the quality-gated content and required format, including the presence of the `## References` section and its index consistency. Do NOT re-resolve citation paths at write time; trust the current-round scout reports for path validity.
4. If incomplete, malformed, or inconsistent, correct that same write and re-read.
5. If a verified artifact cannot be established, append `workflow-paused` with `reason=spec-write-verification-failed` and do not complete.
6. Once verified, append `spec-write-verified`.
7. Append `workflow-completed` with artifact path, revision information, and scout report count.
8. Retain all scout reports, revisions, and progress history.

## Completion Response

Return only:

- Finalized `spec.md` path.
- Whether a revision was archived, with revision path when applicable.
- Number of retained scout reports for the completed round.

Do not repeat the spec in chat.

## `spec-scout` Reference

`spec-scout` is a bundled read-only discovery agent.

**Required inputs:** `backlog_name`, `feature_id`, `feature_context`, `topic`, `discovery_scope`, `questions_to_resolve`, `workspace_root`, `project_root`, `report_path`.

**Canonical output:** `_xzy-ai/sprints/<backlog_name>/specs/features/<NNN>/scouts/round-<RRR>/<topic>.md` using the agent's embedded canonical schema, mirrored for human reference in [SCOUT-REPORT-FORMAT.md](./references/SCOUT-REPORT-FORMAT.md).

**Return:** report path, `completed` or `blocked`, and blocked reason when applicable.

## Constraints

1. Do not process more than one feature per invocation.
2. Do not choose a feature automatically.
3. Do not write `spec.md` before complete evidence coverage and a passed quality gate.
4. Do not write source code, tests, configuration, dependencies, lockfiles, or unrelated artifacts.
5. Do not overwrite a canonical spec without verified archival.
6. Do not create alternate draft specs.
7. Do not maintain a backlog-level spec manifest.
8. Preserve all scout reports, revisions, and progress history.
9. Keep `spec.md` free of file paths except qualifying workspace-root-relative citations outside the project root and `_xzy-ai/`; final citations are path-only, and the trailing `## References` index must be the deduplicated sorted union of inline citations. Keep it free of concrete function signatures, code snippets, scout citations, unresolved alternatives, and open questions. Trust current-round scout reports for citation path validity; do not re-resolve paths at write time.
10. Only the main host writes feature `progress.md`.
11. Do not exceed five scout invocations per wave, three waves, or fifteen invocations per authorized discovery cycle.
12. Treat the active working tree, including uncommitted changes, as current state.
13. Keep all workflow operations and artifacts inside the active workspace root.

## References

- [Spec Artifact Format](./references/SPEC-FORMAT.md)
- [Scout Report Format](./references/SCOUT-REPORT-FORMAT.md)
- [Progress Log Format](./references/PROGRESS-LOG-FORMAT.md)
