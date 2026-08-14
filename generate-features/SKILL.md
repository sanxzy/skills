---
name: generate-features
version: 1.0.0
description: |
  Generate a finalized product feature backlog from explicit conversation or supplied context plus targeted discovery of the active codebase, or resume an interrupted `generate-features` workflow. Use ONLY when the user explicitly asks to generate, derive, identify, create, or resume a product feature list or feature backlog. Produces `_xzy-ai/sprints/<backlog_name>/features.md` and delegates current-state evidence gathering to bundled `feat-scout` subagents. Do not use for casual feature brainstorming, specifications, implementation plans, tickets, prioritization exercises, or code implementation.
---

Produces a durable, product-facing list of capabilities that still require work for a clarified outcome. It synthesizes:

1. The current conversation.
2. Any transcript, document, or other input explicitly supplied by the user.
3. Targeted end-to-end discovery of the active working tree.

The final artifact is written to:

```text
_xzy-ai/sprints/<backlog_name>/features.md
```

Established codebases are investigated by one or more bundled `feat-scout` subagents. Their technical reports are retained under:

```text
_xzy-ai/sprints/<backlog_name>/feats/scouts/<topic>.md
```

The main host owns feature synthesis, quality validation, all user interaction, and the progress log. Scouts gather evidence only and never propose or write final features.

## Trigger Boundary

Run this skill only for an explicit request to produce a finalized product feature list or backlog, or to resume an interrupted `generate-features` workflow.

Do not run it for:

- Casual feature ideation or brainstorming.
- Product specifications or requirements documents.
- Implementation plans, work units, or tickets.
- Feature prioritization without backlog generation.
- Code implementation.

## Core Definitions

### Feature

A feature is an independently recognizable product capability that delivers observable value to an intended actor. The actor may be a customer, administrator, operator, developer, or another stated stakeholder.

A feature is not:

- A technical layer, module, file, function, endpoint, migration, or infrastructure task.
- A layer-by-layer implementation breakdown.
- An already-supported capability with no remaining work.
- A speculative enhancement outside the clarified outcome.

### Work-required capability

Include a capability only when the target outcome is `partial` or `missing` in the current product behavior. For a partially supported capability, describe the complete final end-to-end outcome rather than only the implementation delta.

Omit `supported` capabilities unless preserving their behavior is necessary to define a changed end-to-end outcome reliably.

### Feature-affecting ambiguity

An ambiguity is feature-affecting when resolving it could change feature inclusion, boundaries, behavior, or scope. A normal gap between desired and current behavior is not a conflict.

Never guess through feature-affecting ambiguity. Hand it to the `discussion` skill.

## Artifact Language

Use the language of the product requirements in the conversation. If the conversation is mixed or unclear, use the repository's dominant documentation language. Preserve established product terms verbatim.

Keep contract tokens unchanged, including:

- Statuses: `supported`, `partial`, `missing`, `conflicting`, `unknown`.
- Progress event types.
- Feature identifiers such as `F001`.
- Required section headings defined by the reference formats.

## Required Context Gate

Generation may proceed only when all of the following are clear:

1. The product goal or problem.
2. The intended users or stakeholders.
3. Scope boundaries sufficient to distinguish included capabilities from unrelated ideas.

Use explicit supplied input when present; otherwise use the current conversation. Do not conduct a product interview inside this skill.

If required context is unclear or incomplete:

1. Identify every feature-affecting gap currently known.
2. Load and run the `discussion` skill in the same conversation when the host supports on-demand skill loading.
3. Give `discussion` the named gaps and relevant background.
4. Wait until `discussion` reaches its explicit shared-understanding completion gate.
5. Resume this workflow automatically with the enriched conversation.

If same-session loading or automatic resume is unavailable, stop and tell the user exactly which gaps must be resolved, ask them to run `discussion`, and instruct them to request `resume generate-features` afterward.

There is no fixed handoff limit. Continue until the intent is clear enough to finalize or the user explicitly stops.

## Project Location and Citation Scope

The active workspace is the current working directory (`<cwd>`). Before any discovery, backlog resolution, citation handling, or artifact write:

1. Read `<cwd>/_xzy-ai/project-root.md`.
2. Require exactly one non-empty project-root entry. It must be a `<cwd>`-relative path (forward slashes, no leading `/`, no `.` or `..` segments) that resolves to a directory inside `<cwd>`.
3. Treat `<cwd>/<project-root-entry>` as the project codebase root. Do not assume a particular project layout beneath it.
4. Use the project root as the only codebase for repository discovery and pass its absolute path to scouts as `project_root`.
5. If `project-root.md` is missing, empty, malformed, or points outside `<cwd>`, pause and ask the user to correct it. Do not guess the project root.

Reference-aware behavior is manual: the workflow enters reference-aware mode only when the user explicitly asks to use references as a source of truth. Citable material may be anywhere on the machine except inside the project codebase root resolved from `_xzy-ai/project-root.md`. Final citations may use either workspace-root-relative paths (forward slashes, no `.` or `..` segments) or absolute paths, and must resolve to existing regular files verified by current-round scouts. Cited files are read-only inputs to the current workflow; a workflow may still manage its own declared output paths.

## Reference-Aware Mode

Reference-aware mode is a scope of how the final `features.md` cites evidence. It is manual: entered only when the user explicitly asks to use references as a source of truth.

### Citation scope

- Any regular file outside the project codebase root (resolved from `_xzy-ai/project-root.md`) may be cited in the final `features.md`, using a workspace-root-relative or absolute path.
- Citable files are read-only inputs to the current workflow: neither the host nor scouts modify, move, rename, or delete them, except each workflow's own declared outputs.

### Driving signal

- Enter reference-aware mode only when the user explicitly asks to use references. Do not enter it automatically merely because citable reference material exists outside the project root.
- If no citable material exists and the user did not require it, generate normally with no citations required.

### Behavior by context

- If the user explicitly asks to use references → enter reference-aware mode: include relevant workspace-root-relative or absolute path citations inline wherever referenced files provide product context, background, desired outcome, goals, scope, or capability evidence. Preserve any additional user instructions or notes verbatim (for example "create an original version in our project to avoid copyright issues") in the References section area or as durable prose, and in progress/generation notes.
- If reference-aware mode is active but investigation finds NO relevant evidence → report this to the user and ask how to proceed (continue without citations / add reference material first / other). Do not fabricate citations.
- If the user explicitly REQUIRES citations but no citable material exists → reject the request rather than proceeding without it.

### Relevance, not a fixed count

Whether citations are required depends on the presence of relevant evidence, not on a fixed number. Provenance-only citations do NOT satisfy the requirement when substantive evidence exists.

## Backlog Naming

Infer `<backlog_name>` from the desired outcome and normalize it to concise lowercase kebab-case:

- Use lowercase letters, numbers when necessary, and hyphens only.
- Prefer a distinctive two-to-five-word outcome phrase.
- Do not add a date unless the date is part of the backlog's stated identity.

Ask the user for a name only when:

- Two or more materially different outcome-based names are equally plausible, or
- No concise two-to-five-word goal phrase distinguishes this backlog from existing backlogs.

Before applying the second rule, list existing directory names directly under `_xzy-ai/sprints/` when that directory exists and compare the candidate identity with them. Otherwise infer the name without confirmation.

## Managed Paths

For backlog `<backlog_name>`, this skill manages only:

```text
_xzy-ai/sprints/<backlog_name>/features.md
_xzy-ai/sprints/<backlog_name>/feats/progress.md
_xzy-ai/sprints/<backlog_name>/feats/scouts/
```

Preserve every unrelated artifact under the backlog directory.

A finalized `features.md` is immutable. Finalization attaches only after a verified `artifact-written` event. Never append, reconcile, replace, or delete a finalized artifact; ask the user to create and name a new backlog instead. If an explicit resume finds `features.md` during a non-terminal round with no `artifact-written` event, treat it as an interrupted first write: verify or correct it against the quality-gated content before finalization.

## Progress and Recovery Contract

The authoritative workflow state is:

```text
_xzy-ai/sprints/<backlog_name>/feats/progress.md
```

Follow [PROGRESS-LOG-FORMAT.md](./references/PROGRESS-LOG-FORMAT.md) exactly.

Only the main host may read workflow state for orchestration or append progress events. Scouts never write the progress log.

### Fresh generation

For a fresh generation:

1. Read `progress.md` when present before deciding the state of any existing `features.md`.
2. If `features.md` exists and the latest workflow round is non-terminal with no `artifact-written` event, treat it as an interrupted first write and ask the user to resume that round or choose a new backlog.
3. If `features.md` exists in every other case, treat it as finalized, require a new backlog, and stop.
4. If no `features.md` exists but the latest workflow round is non-terminal, ask the user to resume that round or choose a new backlog. Do not start overlapping work.
5. Delete only the existing `feats/scouts/` directory contents.
6. Preserve `progress.md` and every unrelated artifact.
7. Append the next `Round NNN` section, beginning with event `01`.

The explicit generation request authorizes first-time artifact creation. Do not ask for another write confirmation.

### Explicit resume

When the user explicitly asks to resume:

1. Read `progress.md` and continue the latest non-terminal workflow round.
2. Trust the user's decision to reuse existing scout reports.
3. Do not delete existing reports.
4. Read every completed report needed by the recorded next action.
5. Continue discovery only for missing information.
6. Append a `resumed` event before taking the next action.

If an explicit resume predates `progress.md` but scout reports exist, trust those reports, reconstruct the minimum state from the reports and current conversation, create `progress.md`, and record the reconstruction in `context-captured` before continuing.

### Pause, cancellation, and completion

- `paused` is non-terminal and reserves the backlog for explicit resume.
- `cancelled` and `round-completed` are terminal.
- Never erase historical workflow rounds.
- Record a terminal event rather than deleting progress history.

## Workflow

### Step 1: Capture normalized context

After the required context gate passes:

1. Determine artifact language.
2. Infer or ask for `<backlog_name>`.
3. Apply the existing-artifact and recovery rules.
4. Create the managed directories when needed.
5. Start or resume the workflow round.
6. Append `context-captured` with concise but sufficient values for:
   - Product goal or problem.
   - Intended users or stakeholders.
   - Desired outcome.
   - In-scope behavior.
   - Out-of-scope behavior.
   - Explicit source artifact paths.
   - Artifact language.
   - Whether the repository appears greenfield or established.

The progress event must contain enough information to resume a greenfield run even when there are no scout reports.

### Step 2: Determine discovery mode

Inspect the repository at a high level to decide whether meaningful implementation exists.

#### Greenfield or nearly empty repository

When no meaningful existing implementation is available:

- Launch zero scouts.
- Proceed from conversation and explicit input when goal, users, and scope are clear.
- If they are not clear, hand off to `discussion`.
- Record `coverage-checked` with `reports=0` and the reason code `greenfield-context-sufficient` when coverage is adequate.

Do not create an artificial baseline scout report.

#### Established repository

Use targeted end-to-end discovery against the project codebase root (resolved from `_xzy-ai/project-root.md`). Cover only behavior relevant to the stated goal across:

- Product and project documentation.
- User-facing entry points and journeys.
- Domain behavior and state transitions.
- Integrations and configuration.
- Behavioral tests and validation paths.
- Relevant accessibility, security, privacy, reliability, and operational behavior.

Analyze the active working tree, including uncommitted changes.

### Step 3: Plan scout scopes

The main host defines focused discovery topics before delegation.

Each topic must:

- Use a concise kebab-case name.
- Own a distinct question or behavior area.
- Contribute directly to one or more stated goals or in-scope user journeys.
- State included and excluded scope.
- Name concrete questions to resolve.

Limited intentional overlap is allowed when separate questions require shared evidence. Tell scouts to cross-reference related topics and avoid duplicating another report's full analysis.

Independent topics may run in parallel when the host supports it; otherwise run them sequentially. Before any delegation, sort topics by kebab-case name and append `scout-wave-planned` with the current cycle, wave, complete topic set, coverage targets, and a compact recoverable brief for every topic containing scope, questions, and report path.

### Step 4: Delegate `feat-scout`

For each topic, delegate to `feat-scout` with every required input:

| Input | Description |
|---|---|
| `backlog_name` | Normalized backlog identifier. |
| `topic` | Unique kebab-case discovery topic. |
| `discovery_scope` | Precise included and excluded discovery boundaries. |
| `product_goal` | Product problem and desired outcome. |
| `relevant_context` | Intended actors, scope, terminology, and relevant conversation or artifact context. |
| `questions_to_resolve` | Specific current-state questions the report must answer. |
| `repository_root` | Absolute path to the active working-tree root. |
| `project_root` | Absolute path to the project codebase root, resolved from `<repository_root>/_xzy-ai/project-root.md`. |
| `report_path` | Exact path `_xzy-ai/sprints/<backlog_name>/feats/scouts/<topic>.md`. |

Before delegation, append one `scout-started` event per scout in deterministic topic order. After all results from that batch return, append one `scout-completed` or `scout-blocked` event per result in the same deterministic topic order, regardless of actual completion order.

A scout returns only:

```text
report_path: <path>
status: completed | blocked
reason: <required only when blocked>
```

The on-disk report is canonical. Read every returned report before evaluating coverage.

If a scout returns `REJECTED`:

1. Treat the rejected delegation as a consumed scout invocation.
2. Append `scout-blocked` with the current `cycle`, `wave`, original `topic`, `report=none`, escaped `reason=rejected:<message>`, and attempt number.
3. Correct the missing or invalid coordinator input instead of inferring product or codebase facts.
4. Append a new `scout-started` event with the same cycle, wave, topic, scope, and report path plus the incremented attempt, then re-delegate the same topic and scope once with corrected inputs. Do not rename the topic for an input rejection.
5. Preserve the original `scout-wave-planned` brief; the corrected delegation fulfills that same planned topic.
6. If the corrected delegation is rejected again, append its matching `scout-blocked`, then append `paused` with `reason=scout-contract-rejected`, the rejected topic in `pending`, and `resume-requires=correct-coordinator-inputs`; report the coordinator-contract failure. Do not continue to a narrower discovery scope because discovery never began.
7. Never leave a `scout-started` event without a corresponding `scout-completed` or `scout-blocked` event.

### Step 5: Apply the discovery budget

One authorized discovery cycle allows:

- At most five scout invocations per wave, concurrent when supported and sequential otherwise.
- At most three scout waves.
- At most fifteen total scout invocations.

Every initial scout, corrected retry, and narrower replacement counts toward the cycle budget.

If complete coverage still fails after the cycle:

1. Append `coverage-checked` with the uncovered areas.
2. Append `paused` with `reason=discovery-cycle-exhausted`, the uncovered areas in both `pending` and `uncovered`, `resume-requires=authorize-next-cycle`, and the exact `authorization-needed`.
3. Ask the user whether to authorize another bounded cycle.
4. If authorized, append `resumed` with the paused event identity, retained report count, `authorization=discovery-cycle-<N>`, and the next action; continue under the same workflow round with the next cycle number.
5. If declined, append `cancelled` and do not write `features.md`.

### Step 6: Recover from blocked scouts

For a blocked scope:

1. Read the blocked report and reason.
2. Retry the same scope once with corrected instructions and a unique topic such as `<topic>-retry`.
3. If still blocked, try one narrower replacement scope with a unique topic such as `<topic>-narrowed`.
4. Preserve every report for auditability.
5. If recovery requires more discovery budget, pause for authorization before continuing.
6. If adequate evidence remains unavailable after the narrower attempt, append `paused` with `reason=discovery-incomplete`, the unresolved coverage in `pending`, and `resume-requires=resolve-discovery-blocker`; report the unresolved coverage and do not generate `features.md`.

Never skip a failed scope and claim complete coverage.

### Step 7: Evaluate evidence sufficiency

Collectively, scout reports must cover every stated goal and in-scope user journey.

Before synthesis, verify that the reports establish:

- Current observable end-to-end behavior.
- Capability status using exactly `supported`, `partial`, `missing`, `conflicting`, or `unknown`.
- Relevant actors and journey states.
- Relevant constraints and integrations.
- User-observable quality behavior.
- Conflicts and unknowns.
- Supporting implementation evidence.

Use status outcomes as follows:

| Status | Main-host action |
|---|---|
| `supported` | Omit from work-required features unless preservation is necessary to define a changed outcome. |
| `partial` | Include the complete final outcome as a candidate feature. |
| `missing` | Include the required outcome as a candidate feature. |
| `conflicting` | Follow up with discovery when the current state is unclear; use `discussion` when desired behavior or scope is ambiguous. |
| `unknown` | Launch focused follow-up discovery. Never synthesize from unknown evidence. |

Append `coverage-checked` after every wave. Include covered goals, uncovered goals, conflicts, unknowns, and the next action.

### Step 8: Resolve feature-affecting conflicts

When conversation intent and current codebase evidence are incompatible in a way that leaves desired behavior or material scope unclear:

1. Gather all currently known ambiguities into one handoff.
2. Append `discussion-started` with the affected topics and questions.
3. Run the same-session `discussion` handoff described in the Required Context Gate.
4. Append `discussion-completed` after explicit shared-understanding confirmation, including the discussion transcript path when one was written.
5. Append another `context-captured` event containing the clarified decisions and transcript path in `sources`.
6. Keep unaffected scout reports.
7. Replace or supplement only reports whose scope was affected by the clarified decision.
8. Reapply the complete coverage gate.

Do not send ordinary missing implementation to `discussion`.

### Step 9: Synthesize candidate features

Synthesize only after complete goal coverage and resolved intent.

Rules:

1. Include only `partial` and `missing` work-required capabilities.
2. Add an unstated capability only when clarified intent and codebase evidence establish that it is necessary for the complete end-to-end outcome.
3. Do not add speculative enhancements.
4. Split capabilities when each part delivers a separately valuable and observable outcome.
5. Keep inseparable behavior in one feature when it forms one end-to-end outcome.
6. Keep the list flat. Do not create parent features, subfeatures, or nested behavior lists.
7. Describe the complete final behavior for partial capabilities.
8. Cover all relevant success and non-success states in one cohesive paragraph, including validation, rejection, permissions, empty states, and recoverable failures when they affect the promised outcome.
9. Embed accessibility, security, privacy, reliability, and similar user-observable qualities in affected features. Create a standalone feature only when the quality is an independently recognizable outcome.
10. Exclude implementation details, source references, layers, technical sequencing, and acceptance-criteria breakdowns. Qualifying path citations are allowed when reference-aware mode is active.
11. Apply no feature quota.
12. Order prerequisites first, then follow the natural user journey.
13. Do not add priority labels unless the source context explicitly contains them.
14. Assign sequential identifiers after ordering: `F001`, `F002`, and so on, with no gaps.
15. In reference-aware mode, include relevant path-only citations inline wherever referenced files provide context, background, desired outcome, goals, scope, or capability evidence. Collect every inline citation in the trailing `## References` section, and preserve the user's additional reference-related instructions or notes verbatim in the References section area or as durable prose and in progress/generation notes.

### Step 10: Apply the internal quality gate

The main host alone performs this gate. Do not delegate to a reviewer.

Before writing `features.md`, verify all of the following:

#### Context

- Goal or problem is clear.
- Intended users or stakeholders are clear.
- In-scope and out-of-scope boundaries are clear.
- No feature-affecting assumptions or open questions remain.

#### Evidence

- Every stated goal and in-scope user journey has current-state evidence or is validly greenfield.
- Every included feature corresponds to work that is `partial` or `missing`.
- No `unknown` capability affects the feature set.
- Any `conflicting` evidence has been resolved or shown not to affect desired behavior.

#### Feature quality

- Each item is an independently valuable product capability.
- Each item is behaviorally complete end to end.
- Relevant happy and non-success paths are included.
- Features do not overlap or duplicate one another.
- Necessary implied capabilities are included; speculative enhancements are excluded.
- Cross-cutting qualities are embedded appropriately.
- The ordered list covers the intended scope completely and contains no unrelated additions.

#### Durability

- No section of `features.md` cites files, paths, functions, tests, configuration, layers, APIs, or other implementation artifacts, except qualifying path-only citations in reference-aware mode.
- Every inline citation is a qualifying workspace-root-relative or absolute path outside the project root, and every cited path was verified by a current-round scout report.
- The trailing `## References` section equals the deduplicated, lexicographically sorted union of all inline citations and contains no index-only paths; its body is `None` when there are no citations.
- In reference-aware mode, evidence-backed substantive sections carry nearby path citations.
- No feature is framed as a technical task or implementation delta.
- No assumptions, tentative items, or open-question sections remain.

#### Format

- The document title follows `# Features — <Backlog title>`.
- All nine required sections are present in order, with `References` last.
- Feature identifiers are continuous from `F001` in final order.
- Every feature follows the required multi-line checklist format.
- There are no nested feature items.
- A no-work result uses the full document structure and no checklist items.
- When there are no citations, the `## References` body is `None`.

Append `quality-checked` with `result=passed`, either `features=<count>` or `result-detail=no-outstanding-features`, and `defects=none` only after every check passes. If a check fails:

- Fix synthesis defects internally and repeat the gate.
- Return evidence gaps to scouting.
- Return feature-affecting ambiguity to `discussion`.
- Never write a partial or draft `features.md`.

### Step 11: Write the finalized artifact

Write `features.md` using [FEATURES-FORMAT.md](./references/FEATURES-FORMAT.md) exactly.

The nine required sections are:

1. `Background`
2. `Intended Users`
3. `Problem`
4. `Desired Outcome`
5. `Goals`
6. `In Scope`
7. `Out of Scope`
8. `Features`
9. `References`

Each feature uses:

```markdown
- [ ] F001 - Capability title

    One cohesive paragraph describing the complete end-to-end outcome and all relevant user-observable behavior.
```

In reference-aware mode, include relevant path citations inline in substantive sections and collect every inline citation in the trailing `## References` section, deduplicated and lexicographically sorted. When there are no citations, the `## References` body is `None`.

When no work-required capabilities remain, preserve all nine sections and write only:

```markdown
No outstanding features
```

under `Features`. Do not list supported capabilities as checked items.

After the write:

1. Re-read `features.md` before declaring it finalized.
2. Verify it matches the quality-gated content and required format, including the presence of the `## References` section and its index consistency (deduplicated, sorted union of inline citations, no index-only paths). This verification must NOT re-resolve citation paths: path validity rests on the current-round scout reports the coordinator trusts, and scouts verify paths before reporting.
3. If the write is incomplete, malformed, or differs from the quality-gated content, correct that same first-time write immediately and re-read it. This atomic write-verification cycle occurs before immutability attaches and before `artifact-written` is logged.
4. If a correct write cannot be established, append `paused` with `reason=artifact-write-failed`, `pending=verified-artifact-write`, and `resume-requires=retry-write`; report the failure and do not append `artifact-written` or `round-completed`.
5. Once verified, the artifact becomes immutable.
6. Count every retained `.md` report under `feats/scouts/`.
7. Append `artifact-written` with `path`, either `features=<count>` or `result=no-outstanding-features`, and `scout-reports=<count>`.
8. Append `round-completed` with `artifact`, either `features=<count>` or `result=no-outstanding-features`, `scout-reports=<count>`, and `next: none`.
9. Retain all scout reports and progress history.

## Completion Response

Return only:

- Finalized `features.md` path.
- Number of feature checklist items, or `No outstanding features`.
- Number of retained scout reports.

Do not repeat the feature list in chat.

## `feat-scout` Reference

`feat-scout` is a bundled read-only discovery agent.

**Required inputs:** `backlog_name`, `topic`, `discovery_scope`, `product_goal`, `relevant_context`, `questions_to_resolve`, `repository_root`, `project_root`, `report_path`.

**Canonical output:** `_xzy-ai/sprints/<backlog_name>/feats/scouts/<topic>.md` using the agent's embedded canonical schema, mirrored for human reference in [SCOUT-REPORT-FORMAT.md](./references/SCOUT-REPORT-FORMAT.md).

**Return:** report path, `completed` or `blocked`, and blocked reason when applicable.

## Constraints

1. Do not interview the user about product requirements inside this skill; use `discussion` for feature-affecting ambiguity.
2. Do not write `features.md` before complete evidence coverage and a passed quality gate.
3. Do not modify an existing finalized `features.md`.
4. Do not modify source code, tests, configuration, dependencies, or unrelated project artifacts.
5. Delete only stale scout reports during a fresh workflow round.
6. Preserve scout reports after finalization.
7. Keep `features.md` entirely free of implementation evidence; only qualifying workspace-root-relative or absolute path citations outside the project root may be cited, path-only and in reference-aware mode, with the trailing `## References` index as the deduplicated sorted union of inline citations.
8. Keep feature descriptions outcome-focused, end-to-end, flat, and durable.
9. Only the main host writes `feats/progress.md`.
10. Do not exceed five scout invocations per wave, three waves, or fifteen invocations per authorized discovery cycle; run a wave concurrently only when supported.
11. Do not proceed with incomplete discovery after a scout failure.
12. Treat the active working tree, including uncommitted changes, as current state.
13. Keep all workflow operations and artifacts inside the active repository root.

## References

- [Feature Artifact Format](./references/FEATURES-FORMAT.md)
- [Scout Report Format](./references/SCOUT-REPORT-FORMAT.md)
- [Progress Log Format](./references/PROGRESS-LOG-FORMAT.md)
