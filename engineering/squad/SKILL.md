---
name: squad
version: 0.1.0
description: |
  Autonomously execute one canonical ticket set through dedicated workers,
  independent reviewers, run-level QA, durable recovery, and controlled
  integration while preserving outcome ownership.
argument-hint: "Provide a canonical tickets.md path or ask to resume a squad run."
---

# Squad

Run one canonical `tickets.md` set through autonomous, long-running,
outcome-oriented orchestration.

`Squad` is not a prompt that merely starts several agents. The host owns the
outcome and must keep coordinating until the outcome is proven or the run
reaches an explicit non-success terminal state.

> **The orchestrator owns the outcome, not the implementation.**

Workers implement. Reviewers independently verify individual work units. A
run-level QA agent verifies the integrated outcome. The host owns readiness,
context integrity, lifecycle state, evidence acceptance, recovery, target
integration, and the final outcome decision.

## 1. Trigger boundary and interface

Use this skill when the user asks to execute, dispatch, resume, or coordinate a
canonical ticket set through multiple isolated implementation workers and
reviewers.

Do not use it for:

- direct sequential implementation in the current checkout;
- creating or revising a proposal;
- generating tickets;
- running an arbitrary task list without a canonical ticket index;
- silently combining multiple ticket backlogs;
- declaring a run complete from worker reports, tests, or agent termination.

### Inputs

Accept:

- an explicit path to one canonical `_xzy-ai/sprints/<backlog>/tickets.md`;
- a resume request naming an existing non-terminal `run_id`;
- a worker mode, `default` or `tdd`, supplied before admission;
- explicit user instructions for cleanup or escalation resolution.

If no ticket path is supplied, discover canonical `tickets.md` files only when
there is exactly one unambiguous candidate. If several candidates exist, ask
the user to choose. Never select by modification time, filename similarity, or
an unrelated conversation assumption.

The canonical ticket set is the product and work contract. The host may derive
runtime profiles and evidence plans from it, but may not silently change its
behavior, scope, dependencies, or acceptance criteria.

### Outputs

The run produces:

- controlled changes in the active target branch of the resolved project;
- canonical ticket acceptance criteria checked only after ticket-level `DONE`;
- durable run state, operations, transitions, role reports, QA evidence,
  remediation records, and history under:

```text
_xzy-ai/sprints/<backlog>/orchestration/<run-id>/
```

- compact milestone and final summaries with pointers to durable evidence.

Do not publish to an external issue tracker. Do not delete durable execution
artifacts as a hidden completion side effect.

## 2. Hard invariants

These rules are non-negotiable:

1. **Outcome ownership:** the host continues until the agreed outcome is
   proven or the run is explicitly `RUN_CANCELLED` or `RUN_ABORTED`.
2. **Admission before side effects:** the complete canonical graph and source
   context pass preflight before the first worktree or agent is created.
3. **System-managed capacity:** the host dispatches eligible work; the agent
   system decides which jobs are `running` or `queued`. The host does not
   expose, calculate, or manage `max_workers`.
4. **Safe parallelism:** dependency readiness, Required priority, and ownership
   separation authorize concurrency. High-confidence overlap or uncertainty is
   serialized.
5. **Isolation:** every active implementation worker has one dedicated Git
   worktree and never writes another worktree or the target branch.
6. **Validated handoff:** no role receives incomplete, inconsistent, stale, or
   unverifiable required context.
7. **Durable-before-action:** persist and verify the state that authorizes an
   external action before performing it.
8. **Durable-before-transition:** persist, validate, and verify an agent result
   before it causes a lifecycle transition.
9. **Side-effect identity:** every side-effecting operation has an operation
   identity and either idempotent or reconciliation semantics.
10. **Transition identity:** every authoritative lifecycle change has a
    transition identity and becomes authoritative only when `COMMITTED`.
11. **Exact approval:** only an authorized reviewer explicitly approving the
    exact final revision can satisfy the review gate.
12. **Integration proof:** reviewer approval alone is not `DONE`; the exact
    revision must be integrated and pass host-owned combined validation.
13. **Aggregate proof:** all work-unit `DONE` states are eligible for run QA;
    they are not automatically `RUN_COMPLETED`.
14. **No false certainty:** `INCONCLUSIVE`, `UNKNOWN`, `BLOCKED`, `ESCALATED`,
    `RUN_CANCELLED`, and `RUN_ABORTED` never mean success.
15. **Scope integrity:** only an existing-scope defect may create an automatic
    `REM-*`; a gap or new requirement requires canonical clarification or user
    authority.
16. **Autonomy:** routine retries, corrections, replacements, reconciliation,
    serialization, remediation, research, and QA expansion do not ask the
    user when policy already authorizes the action.
17. **User boundary:** user discussion begins only at a true escalation or an
    explicit user control request such as pause, cancellation, or cleanup.
18. **Retention:** terminalization never destroys worktrees, reports, history,
    or evidence. Cleanup is a separate explicit operation.

## 3. Resolve and admit the run

Perform every step below before the first implementation dispatch.

### 3.1 Resolve the source

1. Resolve one canonical `tickets.md` and keep its absolute path in run state.
2. Read the complete index and every linked ticket file.
3. Confirm ticket IDs are unique, links resolve, filenames match IDs, and each
   ticket has a complete outcome, scope boundary, blocker list, and acceptance
   criteria.
4. Preserve the ticket language, product terminology, Required/Optional
   designation, and explicit external prerequisites.
5. Derive the backlog name from the canonical path. Do not combine backlogs.

### 3.2 Resolve project and target state

Read `<workspace_root>/_xzy-ai/project-root.md`. It must contain exactly one
valid workspace-relative project-root entry. If it is missing, malformed, or
outside the workspace, pause before creating execution resources; never guess.

Inside the resolved project root:

- verify that the path is a Git repository;
- record the active target branch and current target HEAD;
- require a clean target checkout before creating worktrees;
- record the initial target baseline and relevant source digests;
- never silently switch the target branch or overwrite unrelated changes.

Cross-run arbitration and global locking are out of scope. The user is
responsible for not launching competing runs against the same source and
target. If external interference is observed, the host still protects this
run by detecting target drift and blocking target-mutating actions until
reconciliation.

### 3.3 Resolve worker mode

Resolve one run-level worker mode before admission:

- `default` — worker implements, tests, validates, reports, and commits;
- `tdd` — worker follows Red → Green → Refactor and preserves meaningful TDD
  commits.

An explicit ticket or `REM-*` override is allowed only when recorded in the
handoff and run state. Never change a mode silently after implementation has
started.

### 3.4 Validate the complete graph

Build the full dependency representation and validate:

- unique and continuous ticket identities where the source requires them;
- every `Blocked by` reference;
- dependency direction and absence of unintended cycles;
- external prerequisites and whether their status can be tracked;
- Required/Optional semantics;
- ticket scope and acceptance clarity;
- contradictory ticket contracts;
- coverage of every core success criterion by the ticket set;
- safe initial ownership/overlap evidence.

A declared but unavailable external prerequisite may block its affected work
unit while unrelated work continues. An unknown prerequisite that prevents the
host from determining an executable graph is a run admission blocker.

Do not partially dispatch an invalid or materially ambiguous graph.

### 3.5 Persist the admission checkpoint

Create the run record and preflight checkpoint only after source, project,
target, mode, and graph validation have passed. Persist and read back the
checkpoint before creating a worktree or dispatching an agent.

A run admission record includes at least:

```yaml
run_id: RUN-042
source:
  tickets_path: _xzy-ai/sprints/example/tickets.md
  backlog: example
  digest: sha256:...
project:
  root: <resolved project root>
  target_branch: main
  initial_head: abc123
worker_mode: default
preflight:
  status: VALIDATED
  graph_digest: sha256:...
  outcome_coverage: VALIDATED
```

## 4. Durable artifact contract

Use the following logical structure. Exact serialization details may follow
repository conventions, but the authority boundaries and identities may not
change.

```text
_xzy-ai/sprints/<backlog>/orchestration/<run-id>/
├── run.yaml                         # current run projection
├── history/events.md                # host-owned append-only chronology
├── operations/<operation-id>.yaml   # side-effect ledger
├── transitions/<transition-id>.yaml # lifecycle transaction ledger
├── work-units/<unit-id>/
│   ├── state.yaml
│   ├── handoffs/<handoff-id>.yaml
│   ├── worker/attempt-<NNN>/report.yaml
│   ├── reviewer/attempt-<NNN>/report.yaml
│   └── evidence/
├── qa/<qa-id>/
│   ├── handoff.yaml
│   ├── report.yaml
│   └── evidence/
├── analysis/<analysis-id>/report.yaml
├── remediations/<rem-id>.yaml
└── summaries/
```

Structured YAML or JSON is canonical for current state, checkpoints,
operations, transitions, handoffs, reports, proof maps, and evidence indexes.
`history/events.md` is append-only and records chronology. A summary or current
projection is never a second mutable source of truth.

Use the responsibility-specific `.mjs` entrypoint documented in
[YAML state tools](./references/YAML-STATE-TOOLS.md) for host and agent YAML
create/update/append operations. The entrypoints provide atomic writes,
expected-digest checks, idempotent stable-ID appends, and read-back support;
they do not grant authority or replace schema/lifecycle validation.

The host is the sole writer of canonical run/work-unit state and committed
lifecycle transitions. A role may write only its own designated report,
evidence, and permitted worktree changes. No role may mutate `tickets.md`,
shared state, or the target branch.

### 4.1 Operation ledger

Every side-effecting action has a stable logical operation identity and a
separate attempt identity:

```yaml
operation_id: RUN-042:TICKET-012:INTEGRATE
attempt_id: RUN-042:TICKET-012:INTEGRATE:attempt-002
type: INTEGRATE
status: PREPARED
input:
  target_head: abc123
  source_revision: def456
result: null
```

Operation status is one of:

```text
PREPARED → EXECUTING → SUCCEEDED | FAILED | UNKNOWN
UNKNOWN   → RECONCILING
```

When an operation result is uncertain, inspect the actual effect before
creating a new attempt. Do not repeat a non-idempotent action merely because
the host did not observe its result.

### 4.2 Transition ledger

Every authoritative state mutation has its own transaction identity:

```yaml
transition_id: TR-RUN-042-TICKET-012-0007
entity: TICKET-012
from: REVIEWING
to: FIXING
status: PREPARED
source:
  canonical_digest: sha256:...
  ticket_digest: sha256:...
trigger:
  operation_id: RUN-042:TICKET-012:REVIEW
  report_digest: sha256:...
checkpoint_id: CP-RUN-042-TICKET-012-0007
```

Transition status is:

```text
PREPARED → COMMITTING → COMMITTED
```

A failed or uncertain transition is `ABORTED` or `UNKNOWN` until reconciled.
Only `COMMITTED` transitions change authoritative lifecycle state.

### 4.3 Durable-before-action protocol

For every side effect:

```text
construct operation and handoff
→ persist
→ read back and verify
→ execute
→ persist raw result
→ read back and verify
→ validate result identity/schema
→ construct transition
→ persist and verify transition
→ commit transition
```

If a write or read-back fails, do not continue as if it succeeded. Keep the
previous authoritative state, record the failure or uncertainty, and use the
appropriate blocker/reconciliation path.

## 5. Work-unit lifecycle and scheduling

Tickets and accepted `REM-*` records use the same work-unit lifecycle:

```text
PENDING
→ READY
→ ASSIGNED
→ IMPLEMENTING
→ AWAITING_REVIEW
→ REVIEWING
→ INTEGRATING
→ DONE
```

Rejection returns to `FIXING` and then `AWAITING_REVIEW`. Recoverable
impediments use `BLOCKED`. Exhausted autonomous recovery or an authority
boundary uses `ESCALATED`.

A work unit is not complete merely because an agent returned or a report says
"done".

### 5.1 Readiness

A work unit is `READY` only when:

1. every required blocker is a completed work unit in `DONE`;
2. required external prerequisites are available or explicitly not needed;
3. the ticket/REM contract and handoff context are sufficient;
4. the work unit is not blocked by an active ownership conflict;
5. the canonical and target revisions relevant to dispatch are fresh.

A dependency is satisfied only by `DONE`, never by implementation completion or
isolated reviewer approval.

### 5.2 Required and Optional priority

Required work is a dispatch preference, not a barrier:

1. consider all currently `READY` Required work first;
2. serialize any unsafe overlap;
3. dispatch `READY` Optional work when it does not delay Required work;
4. continue processing Optional work until it is complete or the run reaches a
   non-success terminal state.

Never silently discard Optional work. The core milestone may be reported when
all Required work is complete, but `RUN_COMPLETED` waits for all in-scope work.

### 5.3 Dynamic dispatch

After every verified result or committed transition:

```text
observe durable state
→ recompute readiness
→ recompute ownership conflicts
→ choose deterministic eligible frontier
→ persist assignment/handoff
→ verify
→ dispatch
```

Do not wait for a whole batch if a dependency completion unlocks new work.
Dispatch eligible work to the agent system without setting a worker-count cap.
If the system queues an agent, retain the work unit in `ASSIGNED` until the
worker starts and acknowledges the handoff. Queueing is not implementation
progress.

### 5.4 Ownership and overlap

Build an effective ownership footprint from three evidence layers:

```text
declared ticket scope
+ observed repository topology/coupling
+ actual changed scope
```

Classify the result as:

```text
SAFE
CONDITIONAL
UNCERTAIN
```

- `SAFE` work may run in parallel;
- `CONDITIONAL` work may run in parallel only when the boundary is explicit and
  independently verifiable;
- `UNCERTAIN` work is serialized.

`Blocked by: None` is a behavioral dependency statement, not proof of file or
module independence. Use host inspection or the optional analysis specialist
when the codebase is large.

When actual scope drifts into another worker's footprint:

```text
persist overlap finding
→ stop new conflicting dispatch
→ preserve active worktrees/history
→ let safe in-flight work settle
→ checkpoint
→ re-evaluate ownership
→ resume with a proven boundary or serialize
```

Do not blind-cancel an active worker unless continued execution is unsafe or
unauthorized.

### 5.5 Deterministic integration order

When several approved work units wait for integration, select one at a time in
this order:

1. dependency and readiness validity;
2. Required before Optional where both are eligible;
3. ownership/overlap safety;
4. canonical index order as a stable tie-breaker.

Persist the selected order and rationale before the integration operation.
Agent completion arrival order is not authoritative.

## 6. Role dispatch and handoff integrity

Read the bundled role definition before dispatching that role:

- [squad-worker](_agents/squad-worker.md)
- [squad-reviewer](_agents/squad-reviewer.md)
- [squad-qa](_agents/squad-qa.md)
- [squad-analysis-reconciliation](_agents/squad-analysis-reconciliation.md)

Every role contract defines required inputs, permissions, allowed side effects,
prohibited actions, report schema/path, terminal statuses, and invariants.
Validate the handoff against that contract before spawning. If a required
field is missing, invalid, stale, conflicting, or unverifiable, do not spawn or
advance the role; create a structured `BLOCKED` record.

### 6.1 Worker handoff

Pass at least:

```text
canonical tickets.md index and selected ticket/REM-* record path
run/work-unit/attempt identity
current progress status
previous progress and relevant history
canonical proposal/ticket digests
assigned worktree and branch
baseline/base revision
dependencies and external prerequisites
effective ownership boundary
worker mode
expected deliverable and acceptance criteria
report path/schema
permission and credential boundary
```

The ticket file is authoritative. The progress fields are context, not a
replacement for the ticket contract.

### 6.2 Worker completion gate

A worker result may enter `AWAITING_REVIEW` only after the host verifies:

- report schema and digest;
- worker identity, work-unit identity, attempt, and mode;
- worktree/branch ownership;
- baseline and commit identity;
- changed scope against the declared/effective footprint;
- relevant tests and validation evidence;
- no unresolved side-effect ambiguity;
- report freshness against canonical and target digests;
- the expected deliverable is actually committed in the ticket worktree.

A worker's `IMPLEMENTED` status is handoff-ready, not approval or completion.

### 6.3 Reviewer dispatch and completion gate

Dispatch the dedicated reviewer as soon as the worker handoff gate passes; do
not wait for unrelated work. The reviewer uses the same ticket worktree
sequentially after the worker has reported.

Pass the reviewer:

```text
canonical tickets.md index and selected ticket/REM-* record path
current and previous progress
worker/reviewer identities
worktree/branch/baseline
canonical and implementation revisions
worker report and changed scope
tests and validation evidence
all prior review history and finding fingerprints
direct-fix history
integration context
review evidence directory for permitted independent tests
review report path/schema
```

Before `INTEGRATING`, the host verifies:

- reviewer identity and role authority;
- durable report and schema;
- explicit `APPROVED`, `REJECTED`, or `INCONCLUSIVE` verdict;
- exact reviewed/final revision;
- all finding identities and statuses;
- no unresolved Major/Critical finding;
- direct fixes are authorized, recorded, and rechecked;
- no relevant `UNKNOWN` operation;
- review is fresh for the current canonical contract and worktree.

Approval attaches to a specific final revision. Any later code change requires
another review result.

### 6.4 Review correction policy

Findings use these severities:

```text
Trivial  → cosmetic/mechanical
Minor    → localized safe correction
Major    → meaningful behavior, design, API, or verification failure
Critical → severe correctness, security, destructive, or contract failure
```

The reviewer may directly fix only safe Trivial/Minor findings. The direct fix
must be recorded, committed by the worker or host in the ticket branch, and
re-reviewed against the final revision. The reviewer must not approve an
uncommitted or unrechecked direct fix.

Major/Critical findings return to the same worker whenever possible. A reviewer
`INCONCLUSIVE` result blocks the ticket until the evidence/context/capability
problem is repaired. No reviewer silence, timeout, termination, or "looks
good" message counts as approval.

### 6.5 Worker implementation modes

For `default` mode, the worker performs the normal implementation loop and
preserves behavior-focused validation.

For `tdd` mode, the worker:

1. writes a focused Red test that fails for the missing behavior;
2. commits the Red state;
3. implements the smallest Green behavior and commits it;
4. refactors while preserving behavior and records any fix commits;
5. hands the final refactored revision to the reviewer.

Do not squash meaningful TDD commits. Reviewer gating happens after the final
TDD cycle, not after an intermediate Red or Green state.

## 7. Integration and ticket completion

A valid reviewer approval moves the work unit to `INTEGRATING`, not `DONE`.
Before every target-mutating action, verify the relevant canonical, ticket,
worker artifact, review artifact, and target HEAD digests.

The host then:

1. persists and verifies an integration operation;
2. integrates the exact approved revision into the active target branch;
3. records the target HEAD and operation result;
4. runs or validates the strongest applicable project-native combined checks;
5. confirms the ticket outcome still holds in the target state;
6. verifies all material operations are conclusive;
7. persists and verifies the canonical ticket acceptance-criteria update;
8. persists and verifies the work-unit `DONE` transition.

If merge, target validation, checks, canonical update, or checkpoint persistence
fails, the ticket remains incomplete. Preserve unaffected integrations,
attribute the failure, and route correction to the owning worker. Any changed
revision must pass review again before reintegration.

If no relevant project-native or behavioral verification seam can establish the
functional outcome, pause that work with a verification blocker and request
user guidance. Do not treat compilation or an unrelated check as proof.

## 8. Run-level outcome verification

When all currently in-scope work units are `DONE`, enter `RUN_VALIDATING`. QA
is universal at the outcome level; its execution strategy follows the actual
observable surfaces of the project. Never bypass run QA merely because ticket
reviews passed.

Create one dedicated run-level QA handoff containing:

```text
Run-Level Outcome Profile
- core success criteria
- user journeys
- observable surfaces
- evidence boundary per criterion
- Required and Optional coverage

Capability & Environment Profile
- available/unavailable capabilities
- environment identity and canonical revision
- setup state

Authority Profile
- authorized tools and strategies
- data/production boundary
- destructive-action constraints

Historical Context
- relevant tickets and REM-* records
- previous QA findings
- regression boundary
```

The host defines **what must be proven**. QA chooses **how to prove it** within
that authority envelope. Strategies may include browser, mobile, CLI/TUI,
service/API, embedded, library consumer, desktop, infrastructure, or multiple
cross-surface strategies.

A mock or test double may replace a real dependency only when the criterion's
evidence boundary explicitly permits it. QA must state what that proves and
what stronger claim remains unproven.

QA may perform bounded, authorized environment preparation such as building,
starting a test service, installing a test artifact, or launching an emulator.
Every mutating setup action is an operation. QA must not modify product code,
canonical scope, production, or an unauthorized external system.

### QA report gate

QA initializes the report as `IN_PROGRESS` before environment setup or test
execution, appends each proof-map decision, strategy, operation, criterion,
evidence artifact, coverage change, and limitation as it occurs, and reads
back every write. It finalizes only after the complete incremental report is
verified.

QA persists a report with:

```text
canonical revision and environment fingerprint
selected strategy/strategies and capability profile
criterion → strategy → evidence proof map
required/exercised/unverified coverage
expected versus observed outcomes
limitations and verification boundary
screenshots/video when possible for visual surfaces
logs/traces/terminal/output evidence for other surfaces
explicit verdict: PASSED | FAILED | INCONCLUSIVE
```

The host validates the report, coverage, provenance, evidence digests, and
verdict. QA cannot change ticket state or declare the run complete.

- `PASSED` enters host final completion validation; it is not automatically
  `RUN_COMPLETED`.
- `FAILED` means evidence proves a required outcome is violated; host performs
  failure attribution and remediation.
- `INCONCLUSIVE` means evidence is insufficient to prove correctness or failure;
  the affected run path becomes `BLOCKED` until capability/environment/context
  recovery succeeds.

Missing capability is inconclusive only when it is required for the affected
criterion. An unavailable mobile device does not block a run that only requires
API evidence; it does block a physical-device criterion.

## 9. Remediation and autonomous recovery

### 9.1 Existing-scope remediation

When QA proves an existing canonical outcome is violated, classify the finding:

```text
DEFECT
→ existing outcome is not satisfied; in-scope remediation is allowed

GAP
→ requirement is insufficiently specified; canonical clarification is needed

NEW REQUIREMENT
→ behavior expands the agreed outcome; source revision/user decision is needed
```

For a `DEFECT`, create a durable first-class `REM-*` record linked to:

```text
run
QA run and finding
originating core criterion
related ticket(s)
existing-scope basis
scope boundary
worker/reviewer ownership
attempt and evidence history
```

A `REM-*` uses the same work-unit lifecycle and gates. A relevant existing role
may be reused when trustworthy, but the remediation receives a new attempt and
validated handoff. `REM-* DONE` proves only the corrective work unit; the
originating criterion must be revalidated.

A `GAP`, `NEW REQUIREMENT`, or uncertain attribution never becomes hidden work.
Persist the evidence and pause for canonical clarification or user authority.

### 9.2 Impact-scoped revalidation

After remediation, revalidate the smallest scope that can provide sufficient
confidence:

```text
restored criteria
+ affected journeys and surfaces
+ justified regression boundary
```

Expand to the full canonical run profile when the remediation touches shared
infrastructure, crosses surfaces, has broad or unknown blast radius, changes
more scope than declared, or reveals an unexpected regression. Full QA means
the canonical run profile, not every repository feature.

### 9.3 Bounded autonomous recovery ladder

Routine failures do not interrupt the user:

```text
Tier 1 — same worker correction and same reviewer recheck
Tier 2 — analysis/reconciliation and explicitly authorized research
Tier 3 — direct user escalation
```

Track attempts, finding fingerprints, recurrence, severity progression,
resolved/new findings, changed scope, and recovery evidence. A default policy
may move from Tier 1 after three stalled correction cycles and from Tier 2 after
three further stalled cycles. These thresholds select a recovery tier; they
never auto-approve or auto-fail.

Invoke the optional analysis/reconciliation role for deep canonical impact,
unknown operation, or failure attribution work. Research must use bounded
questions and permitted sources. The analysis result is advisory; host
validation is required before any transition or side effect.

## 10. Blockers, changes, interruption, and escalation

### 10.1 Structured blocker

Keep the top-level state `BLOCKED` and store the reason:

```yaml
state: BLOCKED
blocker:
  type: HANDOFF_CONTEXT
  code: MISSING_WORKER_REPORT
  reason: "Reviewer handoff has no current worker report."
  source_state: AWAITING_REVIEW
  resume_state: AWAITING_REVIEW
  required_to_resume:
    - worker_report
```

Use coarse blocker types such as `DEPENDENCY`, `HANDOFF_CONTEXT`, `BASELINE`,
`WORKTREE`, `OWNERSHIP_CONFLICT`, `AGENT_UNAVAILABLE`, `REVIEW`, `INTEGRATION`,
`VALIDATION`, `QA_CAPABILITY`, `OPERATION_RECONCILIATION`, `CANONICAL_CHANGE`,
`TARGET_CHANGE`, `EXTERNAL`, and `UNKNOWN`. Put precise detail in `code`,
`reason`, and metadata.

`BLOCKED` is an interruption state, not a restart state. After a candidate
resolution appears, the host verifies the blocker is gone, the baseline and
context are still current, and `resume_state` is legal. If valid, restore the
saved state; otherwise remain blocked or move to the nearest legal state.

Blockage is ticket-local whenever possible. Unrelated safe work continues.

### 10.2 Agent interruption

If a worker or reviewer stops before a valid report:

```text
persist interruption
→ preserve worktree/history/ledger
→ reconcile commits and side effects
→ BLOCKED: AGENT_UNAVAILABLE
→ transfer only the failed role when safe
→ create a new attempt and validate its handoff
```

Do not assume the old operation had no effect. Do not delete the worktree.

### 10.3 Canonical and target changes

Before each side effect or lifecycle advance, check the relevant digests. If the
canonical proposal/ticket changes:

```text
stop new dispatch and target mutation
→ persist change barrier
→ reconcile in-flight operations
→ load new source revision
→ revalidate graph and outcome profile
→ compute affected work units
→ invalidate stale handoffs/reviews/QA profiles
→ persist and verify a new admission checkpoint
→ resume only valid work
```

If target HEAD changes externally, stop integration, checklist, and completion
actions until the target is reconciled. Do not silently overwrite or validate
against an untrusted target.

Unaffected completed work remains valid. Affected work may be reusable or
invalidated. A material behavior change requires canonical source revision and
must never be applied silently to an old approval.

### 10.4 Pause and cancellation

For a user pause:

1. persist pause intent;
2. stop new dispatch;
3. inspect in-flight operations;
4. let atomic actions settle or cancel/quiesce them through tracked operations;
5. reconcile effects;
6. persist and verify run-level `PAUSED`.

Work-unit states remain unchanged. Resume validates canonical source, target,
worktrees, agents, operations, and saved context before restoring the prior run
state.

For user cancellation, perform the same controlled stop and persist
`RUN_CANCELLED`. Preserve evidence. `RUN_ABORTED` is reserved for an
unrecoverable host/system/integrity failure after recovery is exhausted. Both
are non-success.

### 10.5 True escalation

Set a work unit to `ESCALATED` or the run to a corresponding blocked/escalated
condition only when:

- normal and authorized analysis/research recovery are exhausted;
- a material scope or requirement decision is required;
- a required external credential, device, environment, or authority can only
  come from the user;
- canonical artifacts conflict without a safe interpretation;
- authoritative target, ledger, or transition state cannot be reconciled;
- safe continuation is no longer provable.

At escalation, stop the affected loop and present a complete decision package:

```text
unmet outcome
exact finding(s) and evidence
attempts and recovery tiers already used
current state, revisions, baseline, and operation status
affected work units and preserved artifacts
authority or scope boundary
possible options and a recommendation
```

The user may give free-form instructions. If the instruction changes behavior,
scope, dependency, or acceptance criteria, pause until the canonical source is
revised and the affected graph/handoffs pass admission again. An escalated
work unit does not stop unrelated safe work unless the run outcome depends on
it.

## 11. Run completion and cleanup

The run has a separate lifecycle from work units:

```text
EXECUTING
→ RUN_VALIDATING
→ QA
→ REMEDIATING → EXECUTING
→ COMPLETING
→ RUN_COMPLETED
```

Run-level `BLOCKED`, `PAUSED`, `RUN_CANCELLED`, and `RUN_ABORTED` are distinct.
Only `RUN_COMPLETED` means success.

### Final run gate

Before `RUN_COMPLETED`, the host verifies:

- every original in-scope Required and Optional ticket is `DONE`;
- every accepted in-scope `REM-*` is `DONE`;
- every required core criterion is `VERIFIED`;
- QA coverage satisfies every declared evidence boundary;
- QA revalidation has closed every material finding;
- no material operation is `UNKNOWN` or an uncommitted transition exists;
- canonical source, target HEAD, and final evidence are consistent;
- final summary and terminal snapshot are persisted and verified;
- the `RUN_COMPLETED` transition itself is `COMMITTED`.

All tickets `DONE` means the run is eligible for final validation, not that it
is complete. A cancelled or aborted run is never reported as successful.

### Explicit cleanup

After any terminal run state, retain worktrees, reports, history, operations,
transitions, QA evidence, and remediation records. Mark them cleanup-eligible
only after the terminal snapshot is durable and no recovery path depends on
them.

Cleanup requires an explicit user-invoked operation:

```text
prepare cleanup operation
→ persist and verify intent
→ inspect eligibility
→ execute idempotent/reconcilable cleanup
→ persist and verify result
```

An unknown cleanup result is reconciled by inspecting actual artifact existence;
it is never blindly repeated. Cleanup does not alter the run's terminal outcome.

## 12. User-facing reporting

At meaningful milestones, report a compact summary containing:

- run ID and current run state;
- target branch and current target revision;
- work-unit counts by state, including `REM-*`;
- Required/core milestone and full-run status;
- current blockers, remediation, or escalation;
- latest operation/transition status;
- evidence and media pointers;
- cleanup state.

Use precise vocabulary:

```text
IMPLEMENTED → worker handoff claim
APPROVED    → reviewer accepted exact revision
DONE        → work-unit outcome proven in canonical target
VERIFIED    → run-level criterion proven within its boundary
RUN_COMPLETED → aggregate outcome accepted by Host
RUN_CANCELLED / RUN_ABORTED → explicit non-success terminal outcomes
```

Never hide uncertainty behind a green summary.

## 13. Verification checklist for the host

Before claiming a run or a skill execution is complete, verify:

- one canonical ticket source was used;
- complete graph admission passed before first dispatch;
- project root, clean target, branch, and baseline were recorded;
- system capacity was not managed through a host-side worker cap;
- Required priority and Optional processing were preserved;
- overlap was evaluated from declared, topology, and actual scope evidence;
- every role handoff passed schema and freshness validation;
- queued versus running agent state was not confused with progress;
- every side effect has operation identity and reconciliation semantics;
- every lifecycle change has a committed transition identity;
- every reviewer approval is explicit, authorized, fresh, and exact-revision;
- every ticket `DONE` passed integration and canonical checklist gates;
- run-level QA used the appropriate outcome/evidence boundary;
- every QA failure was attributed before remediation;
- no hidden scope was created;
- all routine recovery happened autonomously;
- user was contacted only at a true escalation or explicit control request;
- terminal states and cleanup remain separate;
- raw reports/evidence remain available through terminalization;
- no temporary workaround or debug artifact remains.

If any check fails, keep the relevant ticket/run incomplete and follow the
recorded recovery or escalation path.

## 14. Do not

- Do not use the current checkout as a shared writable worktree for workers.
- Do not ask the user to choose routine retries, replacements, serialization,
  reconciliation, remediation, or QA expansion.
- Do not expose or manage `max_workers`.
- Do not mark `ASSIGNED` work as `IMPLEMENTING` while the system only reports it
  as queued.
- Do not advance on an incomplete or stale handoff.
- Do not treat a worker report, passing unit tests, reviewer silence, or a merge
  exit code as outcome proof.
- Do not approve a revision different from the one reviewed.
- Do not integrate a ticket with unresolved Major/Critical findings.
- Do not retry an `UNKNOWN` side effect before reconciliation.
- Do not silently mutate canonical scope or invent a remediation/new ticket.
- Do not turn a mock-only criterion result into a real-dependency claim.
- Do not let QA or analysis agents mutate lifecycle state or scope.
- Do not delete worktrees, reports, or evidence automatically at terminalization.
- Do not report `RUN_CANCELLED`, `RUN_ABORTED`, `BLOCKED`, or `ESCALATED` as
  success.
