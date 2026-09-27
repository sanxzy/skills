---
name: squad
version: 0.1.0
description: |
  Autonomously execute one canonical ticket set through dedicated workers,
  independent reviewers, run-level QA, durable recovery, and controlled
  integration while preserving outcome ownership across production and E2E
  prototype purposes.
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

## Purpose and completion markers

Resolve one run-level **purpose** before admission:

- `production` — implement and prove the real product behavior and system
  boundaries defined by the canonical tickets. It has one worker implementation
  mode: `default` or `tdd`.
- `prototype` — implement an **E2E interactive prototype** of the selected core
  product journey, from entry point through the user's value/outcome. It is not
  limited to a component, screen, or isolated feature, and it does not require
  real backend, persistence, authentication, renderer, integrations, or
  production reliability. Fake data, hardcoded/in-memory state, fake
  loading/error states, scripted responses, and simulated side effects are
  allowed when the boundary is explicit.

Prototype scope is the core value journey, not the entire product. The host,
worker, reviewer, and QA must preserve the distinction between a simulated
journey and a production claim.

Acceptance checklists are purpose-specific:

- production completion uses `- [x]`;
- prototype completion uses `- [P]`.

`[P]` means the criterion is implemented and verified as part of the E2E
prototype; it never means production completion. Do not convert `[P]` to `[x]`
in a prototype run.

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
- a purpose, `production` or `prototype`, supplied before admission;
- a worker implementation mode, `default` or `tdd`, only when purpose is
  `production`;
- explicit user instructions for cleanup or escalation resolution.

If no ticket path is supplied, discover canonical `tickets.md` files only when
there is exactly one unambiguous candidate. If several candidates exist, ask
the user to choose. Never select by modification time, filename similarity, or
an unrelated conversation assumption.

The canonical ticket set is the product and work contract. The host may derive
runtime profiles and evidence plans from it, but may not silently change its
behavior, scope, dependencies, or acceptance criteria. Purpose selects which
completion marker is authoritative for this run; it does not weaken the ticket
contract or turn prototype evidence into production evidence.

### Outputs

The run produces:

- controlled changes in the active target branch of the resolved project;
- immutable canonical ticket contract digests plus a generated run-linked
  `summaries/acceptance-status.yaml` projection after ticket-level `DONE`;
- durable run state, operations, transitions, role reports, QA evidence,
  remediation records, and history under:

```text
_xzy-ai/sprints/<backlog>/orchestration/<run-id>/
```

- a typed final summary with pointers to durable evidence; milestone reporting is
  a read-only host status projection, not an unimplemented artifact command.

Do not publish to an external issue tracker. Do not delete durable execution
artifacts as a hidden completion side effect.

## Operator map: follow this path first

This is the host's normal execution path. For exact command syntax and JSON
outputs, use [Host workflow commands](./references/WORKFLOW-COMMANDS.md). For
write authority and digest-safe YAML primitives, use
[YAML state tools](./references/YAML-STATE-TOOLS.md). The host invokes typed workflow
commands; the commands write and verify durable state. Do not hand-edit YAML or
copy SHA values between artifacts during routine execution.

| Phase | Host action | Durable state/result | Next action |
|---|---|---|---|
| Admit | Resolve source/project/target; run `migrate-run` for an older run; run `environment-profile`, `analyze-ownership`, and `preflight` | Admission checkpoint, environment fingerprint, ownership report | Provision the canonical worktree |
| Dispatch worker | `prepare --role worker` → `validate-handoff` → `bind-agent` → spawn the worker | `READY → ASSIGNED`, validated worker handoff, `PREPARED/EXECUTING` operation | Wait for the agent system and worker acknowledgement |
| Acknowledge worker | When the worker has started, `acknowledge-agent <job-id> --state <state.yaml> --operation <operation.yaml>` | Committed `ASSIGNED → IMPLEMENTING` transition | Queued/unstarted jobs are not acknowledgements |
| Handoff worker | Worker writes `IMPLEMENTED` report; host runs `complete-worker` | `IMPLEMENTING → AWAITING_REVIEW`, exact revision/report, active handoff archived | Prepare the reviewer |
| Dispatch reviewer | `prepare --role reviewer` → `bind-agent` → spawn reviewer | `AWAITING_REVIEW → REVIEWING`, exact implementation revision and generated reviewer context in handoff | Wait for reviewer verdict; missing context blocks preparation |
| Optional analysis | `prepare --role analysis` → `bind-agent` → spawn analysis; host runs `complete-analysis` | Advisory report is recorded; work-unit lifecycle state does not advance | Host independently validates every recommendation |
| Accept/reject review | Host runs `complete-review` with the exact reviewer report | `APPROVED → INTEGRATING`, `REJECTED → FIXING`, or `INCONCLUSIVE → BLOCKED` | Integrate, correct, or repair evidence |
| Correct | From `FIXING`, run `prepare-correction`; repeat worker/report/review gates | New worker/reviewer attempt and operation instances; old evidence retained | Return to review |
| Reject context | Before product review, `reject-handoff` | `BLOCKED`, operation `SUPERSEDED`, explicit handoff-rejection history | Never call a context rejection `REJECTED` product review |
| Integrate | `integrate` only after exact approval; run host-owned checks | Fast-forward-only target operation and target-before/after snapshot | Supply durable validation evidence |
| Complete ticket | `complete-ticket --validation <evidence.yaml>` | `INTEGRATING → DONE`; structured evidence when required; acceptance-status projection refreshed | Identical repeat is idempotent; conflicting evidence remains blocked |
| Begin run validation | `transition-run <run-id> --from EXECUTING --to RUN_VALIDATING --reason ...` after every unit is `DONE` | Durable run transition ledger | Prepare typed run-level QA |
| Dispatch run QA | `prepare-qa --run <run.yaml>` → `bind-agent` → spawn QA | `RUN_VALIDATING → QA`, validated run-level QA handoff and operation | Wait for QA report |
| Accept QA | `complete-qa --run <run.yaml> --report <report.yaml>` | `PASSED → COMPLETING`; `FAILED`/`INCONCLUSIVE → BLOCKED` with explicit blocker | Attribute/remediate or repair evidence |
| Complete run | `complete-run --run <run.yaml>` then `verify-run --final` | `COMPLETING → RUN_COMPLETED` only after final preflight and summary | Retain artifacts; cleanup is outside this package |

### State-to-command matrix

Use the current durable state, not an agent message, to choose the next action.
`status <run-id> --ticket <unit> --explain` is the read-only way to inspect the
state, blocker, legal destinations, active handoff, operation, and next action.

| Current state | Legal normal action | Do not infer |
|---|---|---|
| `PENDING` | Resolve dependencies/source, then transition to `READY` when admitted | Readiness from a ticket label alone |
| `READY` | `prepare --role worker` | Worker progress before dispatch |
| `ASSIGNED` | Wait for system start; then `transition ... ASSIGNED IMPLEMENTING` | `ASSIGNED` means running; queued is not progress |
| `IMPLEMENTING` | Wait for worker report; then `complete-worker` | Worker termination means implementation success |
| `AWAITING_REVIEW` | `prepare --role reviewer` | Worker `IMPLEMENTED` means approval |
| `REVIEWING` | `complete-review` with exact report | Silence or a different revision means approval |
| `FIXING` | `prepare-correction` | A correction must produce a new revision and fresh approval |
| `INTEGRATING` | `integrate`, host validation, then `complete-ticket` | Merge exit code alone means `DONE` |
| `DONE` | Include in run-level QA and final verification | All units `DONE` means only eligible for run validation |
| `BLOCKED` | Inspect blocker, reconcile, repair context, or `resume-ticket` | `BLOCKED` means restart or success |
| `ESCALATED` | Present the decision package and wait for user/authority input | Escalation can be silently bypassed |

### Authority and file ownership

| Actor/entrypoint | May write | Must not write |
|---|---|---|
| Host workflow `squad.mjs` | Run/work-unit state, operations, transitions, integration target, projections | Role reports, another worktree, canonical contract scope |
| Host primitive `squad-host-state.mjs` | Low-level host YAML paths with expected digests | Routine lifecycle decisions without typed command validation |
| Worker/reviewer/QA/analysis report helper | That role's report, incremental log, permitted evidence | Shared state, another report, target branch |
| Agent system | Job scheduling/status | Host lifecycle state or capacity policy |
| Reviewer | Read-only review; explicitly permitted uncommitted Trivial/Minor fix | Approval of a different/uncommitted revision, integration |

Agents never mutate lifecycle state. The host owns the outcome, but it does not
own implementation details that belong in the worker worktree.

### Work-unit versus run-level state

The command examples above operate on a work unit. Run-level states
(`EXECUTING`, `RUN_VALIDATING`, `QA`, `REMEDIATING`, `COMPLETING`,
`RUN_COMPLETED`, `BLOCKED`, `PAUSED`, `RUN_CANCELLED`, and `RUN_ABORTED`) use a
separate host projection and transition ledger. Use `transition-run` for an
explicit run transition; use `prepare-qa`, `complete-qa`, and `complete-run`
for the guarded QA and terminal paths. If a run transition write is interrupted,
use `reconcile-run-transition` before creating another transition. Do not use a
work-unit `transition` to fake a run state. `verify-run --final` is read-only:
it validates a run already marked `RUN_COMPLETED` and never commits that state
itself. `squad.mjs` does not
provision admission worktrees or delete retained artifacts; the host must keep
those responsibilities explicit and must not claim they happened without
separate evidence.

### When a command fails

Stop at the reported error code. Preserve the previous authoritative state and
artifacts. Use `status`, inspect the operation/transition ledger, and follow the
matching recovery row in [the workflow runbook](./references/WORKFLOW-COMMANDS.md).
Do not repair by manually clearing pointers, resetting a worktree, repeating an
unknown side effect, or selecting the first matching job ID.

### Recovery decision table

| Observation | Host response | Terminal meaning |
|---|---|---|
| Agent stops before a conclusive report | `reconcile-agent`; inspect effect; `resume-ticket` when safe | Old operation becomes `SUPERSEDED` only after a successor is durable; never `IMPLEMENTED` by termination |
| Job ID matches multiple operations | Stop and supply the exact `--operation` after inspecting candidates | `AMBIGUOUS_AGENT_JOB`; no mutation from implicit lookup |
| Operation is `UNKNOWN`/`RECONCILING` | Inspect actual Git/report/effect; reconcile before retry | Uncertainty remains explicit until terminal ledger classification |
| Run transition is `PREPARED`/`COMMITTING` after interruption | `reconcile-run-transition`; commit only the observed source/destination result | Create another run transition while the prior ledger is unresolved || Worktree is dirty on recovery | Preserve it; classify prior effects and attribute them in the next handoff | Never stash, reset, clean, or absorb unexplained changes |
| Reviewer `REJECTED` | `complete-review` → `FIXING` → `prepare-correction`; produce a new revision and review | Old approval is invalid for any changed revision |
| Reviewer `INCONCLUSIVE` | Repair missing capability/context/evidence; resume the saved review state | Not a product pass or failure |
| Target HEAD/branch/checkout changes | Stop target mutation; reconcile checkpoint and active handoffs; preflight again | Never rebase or overwrite silently |
| Canonical ticket/proposal changes | Stop dispatch/mutation; re-admit affected graph and invalidate stale context | A source revision barrier, not a routine retry |
| QA `FAILED` | Host attributes the finding; admitted remediation controller creates only in-scope `REM-*`; revalidate affected outcome | QA observes; it does not create remediation or mark completion |
| QA `INCONCLUSIVE` or missing required capability | Preserve evidence boundary and repair capability/environment | Never downgrade the criterion to a weaker claim |

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
   worktree under `<cwd>/worktrees/squad/<backlog>/<run-id>/<work-unit-id>/` and
   never writes another worktree or the target branch.
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

### 3.3 Dedicated worktree location

`<cwd>` is the workspace root that contains `_xzy-ai/project-root.md`. Squad
uses this fixed worktree namespace and never places worker worktrees in the
resolved project root, the skill checkout, or the orchestration artifact tree:

```text
worktree root:
<cwd>/worktrees/squad/

per-work-unit path:
<cwd>/worktrees/squad/<backlog>/<run-id>/<work-unit-id>/
```

Use canonical identity segments for `<backlog>`, `<run-id>`, and
`<work-unit-id>`. Reject separators, empty segments, `.`/`..`, symlink escapes,
and path collisions. The host persists the absolute path, relative path,
repository identity, branch, baseline, and ownership in the work-unit state
and every relevant handoff.

Provision each worktree only after the admission checkpoint is persisted and
verified. The Squad command package does not create Git worktrees or branches;
the host's admission/provisioning layer must perform and durably record this
explicit operation:

```text
record CREATE_WORKTREE intent with the canonical path and baseline
→ create the branch/worktree from the recorded baseline
→ verify `git worktree list --porcelain`, repository identity, branch, and HEAD
→ persist/read back the worktree record through the host's admitted state path
→ run `squad.mjs preflight --run <run.yaml>`
→ dispatch the worker with `squad.mjs prepare`
```

If that host provisioning layer is unavailable, stop at admission; do not claim
an isolated worktree exists and do not use `squad-host-state.mjs` as a substitute
for the missing Git operation.

The same per-work-unit path remains attached through normal correction and
review attempts; an attempt does not create an ad hoc sibling path. If the
canonical path becomes unusable and recovery requires a replacement, use an
explicitly recorded `recovery-<NNN>` child under the same run namespace only
after the original worktree and its effects are reconciled. Retain every
worktree and its evidence after terminalization; this package has no cleanup
command.

### 3.4 Resolve purpose and worker implementation mode

Resolve one run-level purpose before admission:

- `production` — the worker implements real product behavior. Resolve one
  worker implementation mode: `default` or `tdd`.
- `prototype` — the worker implements the selected E2E interactive prototype
  journey. Do not resolve a production implementation mode; prototype work
  follows the E2E journey contract and may use explicit fake boundaries.

Persist the purpose in the run admission record and every generated handoff.
For production, persist the selected `worker_mode` as `default` or `tdd`. For
prototype, leave the production worker mode unset rather than relabeling the
prototype as TDD or production default. A ticket- or `REM-*`-specific
production worker-mode override is allowed only when recorded in the handoff
and run state; it cannot introduce a mode into prototype work. Never change
the purpose or implementation mode silently after implementation has started.

### 3.5 Validate the complete graph

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

### 3.6 Persist the admission checkpoint

Create the run record and preflight checkpoint only after source, project,
target, purpose, applicable implementation mode, and graph validation have
passed. Persist and read back the
checkpoint before creating a worktree or dispatching an agent. Capture a
run-level environment profile and initial ownership analysis before first
dispatch. A new `control_plane_version: 2` run requires a profile path and
digest by default; set `environment_profile_required: false` only when the run
explicitly records an advisory profile policy. Legacy migration writes that
non-required policy safely, defaults a missing purpose to `production` with
worker mode `default`, and reports `LEGACY_ENVIRONMENT_PROFILE_MISSING` when no
profile exists. A migrated `prototype` run keeps its production worker mode
unset. Cache environment blockers only while the profile/tool fingerprint,
source digest, and affected scope remain unchanged.
Record exact revisions/file digests for every external reference used by active
work. The first worktree path must be the canonical
`<cwd>/worktrees/squad/<backlog>/<run-id>/<work-unit-id>/` location defined above.

A run admission record includes at least:

```yaml
run_id: RUN-042
control_plane_version: 2
source:
  tickets_path: _xzy-ai/sprints/example/tickets.md
  backlog: example
  digest: sha256:...
project:
  root: <resolved project root>
  target_branch: main
  initial_head: abc123
purpose: production
worker_mode: default # required for production; omit for prototype
proposal_required: false
environment_profile_required: true
validation_evidence_required: true
preflight:
  status: VALIDATED
  graph_digest: sha256:...
  outcome_coverage: VALIDATED
environment:
  profile_path: <run-dir>/environment/profile.yaml
  fingerprint: sha256:...
ownership_analysis:
  path: <run-dir>/analysis/ownership.yaml
  status: SAFE | CONDITIONAL | UNCERTAIN
```

## 4. Durable artifact contract

Use the following logical structure. Exact serialization details may follow
repository conventions, but the authority boundaries and identities may not
change.

```text
_xzy-ai/sprints/<backlog>/orchestration/<run-id>/
├── run.yaml                         # current run projection
├── history/events.md                # host-owned append-only chronology
├── operations/<operation-instance-id>.yaml # side-effect ledger
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
Git worktrees are not stored below the orchestration artifact tree; their
canonical paths are under `<cwd>/worktrees/squad/<backlog>/<run-id>/` and are
recorded in the corresponding work-unit state and handoffs.
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

Current state stores at most one `active_handoff`; completed handoffs are never
rewritten and are retained in `handoff_history` with report digests, revisions,
and outcome pointers. Active preflight validates only the active handoff. A
historical handoff is verified against its recorded target/worktree snapshot,
not against a later target HEAD.

### 4.1 Operation ledger

Every side-effecting action has a stable logical operation identity, a unique
operation instance, and a role-scoped attempt identity:

```yaml
operation_id: RUN-042:TICKET-012:INTEGRATE
operation_instance_id: RUN-042:TICKET-012:INTEGRATE:attempt-002
attempt_id: RUN-042:TICKET-012:reviewer:attempt-002
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
UNKNOWN   → RECONCILING → RECONCILED | SUPERSEDED
```

`RECONCILED` and `SUPERSEDED` mean the side effect was inspected and linked to
retained evidence or a successor attempt. They never mean implementation,
approval, integration, or product success.

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

### 4.4 Typed host workflow and generated context

Use the host-only workflow entrypoint in
[`references/WORKFLOW-COMMANDS.md`](./references/WORKFLOW-COMMANDS.md) for
normal execution. It provides `validate-handoff`, `manifest`, `handoff`,
`prepare`/`dispatch`, `preflight`, `transition`, `transition-run`,
`acknowledge-agent`, `reject-handoff`, `reconcile-agent`, `resume-ticket`,
`bind-agent`, `complete-worker`, `complete-review`, `complete-analysis`,
`prepare-correction`, `integrate`, `complete-ticket`, `prepare-qa`,
`complete-qa`, `complete-run`, `environment-profile`,
`reference-snapshot`, `analyze-ownership`, `migrate-run`, `status`, and
`verify-run`. The commands compose the responsibility-specific YAML primitives
with Git identity and cross-artifact checks; they do not spawn agents, manage
capacity, or delete retained evidence. Only the typed `integrate` command may
mutate the target, and it does so through a durable, fast-forward-only,
reconcilable operation.

A typed handoff is generated from one immutable per-ticket execution manifest.
The manifest derives source/state/report/evidence paths, SHA digests, branch,
worktree, baseline, current HEAD, target HEAD, operation identity, attempt
identity, and dependency snapshots from the latest durable artifacts. The host
supplies substantive decisions such as role, purpose, applicable implementation
mode, scope, authority, and
acceptance context; it does not manually duplicate identifiers across YAML
files. A manifest or handoff with a conflicting immutable snapshot is rejected
rather than overwritten.

`validate-handoff` is a pre-dispatch gate, not an advisory lint. It resolves
all referenced revisions with Git, checks the actual repository/worktree and
registered worktree path, compares source/report/state/operation/attempt
identities, verifies dependency `DONE` status, and rejects illegal transition
or naming variants. Errors identify the exact field plus actual and expected
values. The host must run it before creating an agent.

The state-machine command is the only normal workflow entrypoint for lifecycle
transitions. It requires the durable `--from` value to match, checks the legal
transition table, persists a transition ledger through
`PREPARED → COMMITTING → COMMITTED`, updates the projection, and reads both
artifacts back. Generic JSON Pointer updates remain available in
`squad-host-state.mjs` as low-level primitives, not as the operator's primary
workflow.

Interruption follows one durable path: `reconcile-agent` resolves exactly one
external job binding, inspects the actual report, commit, branch, HEAD, and
dirty worktree, records `UNKNOWN`/`RECONCILING` operation state and an
`AGENT_UNAVAILABLE` blocker, and preserves all effects. Ambiguous job IDs fail
before mutation. `resume-ticket` creates a fresh operation instance and
attempt, reuses the same worktree when safe, or requires a pre-provisioned
`recovery-<NNN>` child without destructive reset; a successful successor marks
the old operation `SUPERSEDED`. `status` and `verify-run` expose the next legal
action, active versus historical handoffs, exact reviewer proof, findings,
environment/reference evidence, dependency readiness, dirty state, and
unresolved uncertainty.

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
module independence. `squad.mjs analyze-ownership` records declared scope,
observed changed scope, pairwise classification, and its conservative
parallel/serialization recommendation. Missing scope or drift is
`UNCERTAIN`, never an invitation to guess. Use host inspection or the optional
analysis specialist when the codebase is large.

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

### 5.5 Environment and reference evidence

Before first dispatch, capture `environment/profile.yaml` with runtime,
package-manager, repository, dependency-lock, and declared generated-artifact
presence/digests. Verification results use `PASS`, `PRODUCT_FAIL`,
`ENVIRONMENT_BLOCKED`, or `NOT_EXERCISED`; a cached baseline blocker is reusable
only when the environment fingerprint, canonical revision, and affected scope
match. Never fabricate generated artifacts merely to make a check collect.

For each external reference repository, run `reference-snapshot` and record the
exact repository revision plus file digests. A later reference update creates a
new snapshot and requires impact analysis for active handoffs that cite the old
snapshot. Reference evidence is read-only and never silently broadens ticket
scope.

### 5.6 Deterministic integration order

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
purpose: production or prototype
worker implementation mode: default or tdd for production; omitted for prototype
expected deliverable, E2E journey (when prototype), and acceptance criteria
report path/schema
permission and credential boundary
```

The ticket file is authoritative. The progress fields are context, not a
replacement for the ticket contract.

### 6.2 Worker completion gate

A worker result may enter `AWAITING_REVIEW` only after the host verifies:

- report schema and digest;
- worker identity, work-unit identity, attempt, purpose, and applicable mode;
- worktree/branch ownership;
- baseline and commit identity;
- changed scope against the declared/effective footprint;
- relevant tests and validation evidence;
- no unresolved side-effect ambiguity;
- report freshness against canonical and target digests;
- the expected deliverable is actually committed in the ticket worktree.

A worker's `IMPLEMENTED` status is handoff-ready, not approval or completion.
The host records it with `complete-worker`, which verifies the exact report,
operation instance, clean worktree, and final revision before moving
`IMPLEMENTING → AWAITING_REVIEW` and archiving the active handoff.

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
another review result. The host records the result with `complete-review`; it
moves `APPROVED` to `INTEGRATING`, `REJECTED` to `FIXING`, and
`INCONCLUSIVE` to a structured review blocker. It never reuses a latest report
by filesystem order when an exact accepted report pointer exists.

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

### 6.5 Worker purpose and implementation modes

For `production` + `default` mode, the worker performs the normal
implementation loop, builds the real product behavior, validates it, reports
it, and commits it.

For `production` + `tdd` mode, the worker:

1. writes a focused Red test that fails for the missing behavior;
2. commits the Red state;
3. implements the smallest Green behavior and commits it;
4. refactors while preserving behavior and records any fix commits;
5. hands the final refactored revision to the reviewer.

For `prototype` purpose, there is no production implementation mode. The worker
must:

1. identify the core E2E journey, its entry point, value/outcome, states,
   transitions, and supported happy/error/loading paths;
2. implement a runnable, navigable experience through the full journey rather
   than stopping at a polished screen or isolated component;
3. use fake data, hardcoded/in-memory state, fake loading, scripted responses,
   and simulated side effects only where the boundary is explicit;
4. avoid building or implying real backend, persistence, authentication,
   renderer, or production reliability;
5. verify the journey at the strongest usable interactive seam and report the
   fake boundaries and remaining production gaps.

Do not squash meaningful production TDD commits. Reviewer gating happens after
the final production TDD cycle or complete prototype journey, not after an
intermediate state.

Commit messages are durable implementation context because tickets may later be
edited or removed. Every worker commit must use a compact, clear, imperative
description of what was delivered. Never include ticket IDs, run IDs,
phase/feature numbers, attempt numbers, backlog names, or other mutable workflow
identifiers in the commit subject. Production TDD may retain only `[red]`,
`[green]`, `[red-fix]`, or `[green-fix]` state markers when needed to preserve
history.

## 7. Integration and ticket completion

A valid reviewer approval moves the work unit to `INTEGRATING`, not `DONE`.
Before every target-mutating action, verify the relevant canonical, ticket,
worker artifact, review artifact, and target HEAD digests.

The host then:

1. runs the typed `integrate` operation with the exact accepted revision;
2. checks target branch, cleanliness, and expected target HEAD before mutation;
3. performs only the guarded fast-forward merge and records target-before/target-after;
4. updates the run target checkpoint and work-unit integration snapshot;
5. runs or validates the strongest applicable project-native combined checks;
6. confirms the ticket outcome still holds in the target state;
7. runs `complete-ticket` with durable host validation evidence. When
   `validation_evidence_required: true`, use the structured
   `squad-host-validation` schema bound to the exact integration operation and
   target before/after;
8. commits the work-unit `DONE` transition and refreshes the generated acceptance-status projection. The projection records the run purpose and completion marker (`x` for production, `P` for prototype). Repeating the same evidence is idempotent; conflicting evidence cannot change `DONE`.

Integration is reconcilable, not a pretend multi-file atomic transaction. The
host serializes only the target-mutating operation; it does not reserve the
whole worker/reviewer pipeline. If the reviewer target checkpoint differs from
the current run checkpoint, integration returns `APPROVAL_STALE` and requires a
fresh reviewer handoff. If the approved source is not a fast-forward descendant,
it returns `INTEGRATION_NOT_FAST_FORWARD`; it never silently rebases or creates
a new merge revision. If Git succeeds but a checkpoint write fails, the
operation result remains authoritative for reconciliation; rerunning must
inspect the actual target before attempting anything again. Historical worktree baselines and handoffs are retained rather
than rewritten to follow a later target HEAD. Canonical ticket contract files
are not mutated merely to display completion status; the run-linked
`acceptance-status.yaml` projection carries that mutable execution metadata.

If merge, target validation, checks, projection, or checkpoint persistence
fails, the ticket remains incomplete or explicitly marked for reconciliation.
Preserve unaffected integrations, attribute the failure, and route correction
to the owning worker. Any changed revision must pass review again before
reintegration.

If no relevant project-native or behavioral verification seam can establish the
functional outcome, pause that work with a verification blocker and request
user guidance. Do not treat compilation or an unrelated check as proof.

## 8. Run-level outcome verification

When all currently in-scope work units are `DONE`, commit the typed run
transition to `RUN_VALIDATING`:

```text
squad.mjs transition-run <run-id> --run <run.yaml> \
  --from EXECUTING --to RUN_VALIDATING \
  --reason "All in-scope work units are DONE; begin outcome validation"
```

Then create and validate the dedicated QA handoff through the host workflow:

```text
squad.mjs prepare-qa --run <run.yaml>
squad.mjs validate-handoff <run-dir>/qa/QA-001/handoff.yaml
squad.mjs bind-agent <job-id> --operation <run-dir>/operations/<qa-operation>.yaml
```

`prepare-qa` is the typed run-level controller path. It requires every
work-unit state to be `DONE`, a clean target, and the run to be
`RUN_VALIDATING`; it commits `RUN_VALIDATING → QA` and writes an immutable
run-level handoff. On a reconciled QA interruption or inconclusive evidence,
the same command resumes only from a `BLOCKED` run whose blocker has
`resume_state: QA` and an allowed recovery code; a proven QA failure must be
attributed/remediated before another QA attempt.

QA is universal at the outcome level; its execution strategy follows the actual
observable surfaces of the project. Never bypass run QA merely because ticket
reviews passed.

The handoff contains:

```text
Purpose Profile
- purpose: production | prototype
- completion marker: [x] | [P]
- prototype core E2E journey, entry point, user outcome, and explicit fake boundaries when applicable

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

For `production`, a mock or test double may replace a real dependency only when
the criterion's evidence boundary explicitly permits it. For `prototype`, fake
data, fake loading, hardcoded state, scripted responses, and simulated
side-effects are expected when declared by the purpose profile. QA must state
what the prototype evidence proves, what it does not prove, and what stronger
production claim remains unproven.

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

Before calling `complete-qa`, the host must validate the report's coverage,
provenance, evidence digests, and declared evidence boundary in addition to the
command's identity/status/revision checks. QA cannot change ticket state or
declare the run complete.

- `PASSED` is consumed by the host with the exact report path:
  `squad.mjs complete-qa --run <run.yaml> --report <report.yaml>`. This commits
  `QA → COMPLETING`; it is not automatically `RUN_COMPLETED`.
- `FAILED` means evidence proves a required outcome is violated; `complete-qa`
  records a `QA_FAILURE_ATTRIBUTION_REQUIRED` blocker and the host performs
  attribution/remediation.
- `INCONCLUSIVE` means evidence is insufficient to prove correctness or failure;
  `complete-qa` records a `QA_INCONCLUSIVE` blocker until
  capability/environment/context recovery succeeds.

After a passed QA report, the host runs:

```text
squad.mjs complete-run --run <run.yaml>
squad.mjs verify-run <run-id> --run <run.yaml> --final
```

`complete-run` requires `COMPLETING`, all work units `DONE`, a passed QA report,
valid preflight, and a clean target. It writes the final summary and commits
`COMPLETING → RUN_COMPLETED`; `verify-run --final` then verifies that terminal
projection without mutating it.

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

For a `DEFECT`, the host's admitted remediation/provisioning controller must
create a durable first-class `REM-*` record linked to:

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

The bundled `squad.mjs` command package does not create a new `REM-*` record;
it only executes an already admitted work-unit state. Do not create a
remediation by routine raw YAML mutation. If the host remediation controller is
unavailable, preserve the QA evidence and block/escalate instead of claiming a
new scope or hidden work unit.

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
`RUN_CANCELLED` with `transition-run`. Preserve evidence. For a pause, after
tracked jobs are stopped/quiesced, use `resume-run` later; it performs preflight
before restoring `PAUSED → EXECUTING`. `RUN_ABORTED` is reserved for an
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
EXECUTING --transition-run--> RUN_VALIDATING --prepare-qa--> QA
QA --complete-qa(PASSED)--> COMPLETING
QA --complete-qa(FAILED|INCONCLUSIVE)--> BLOCKED
REMEDIATING → EXECUTING
COMPLETING --complete-run--> RUN_COMPLETED
```

The typed run commands are deliberately separate from work-unit commands:
`transition-run` commits an explicitly legal run transition, `prepare-qa`
creates the run-level operation/handoff, `complete-qa` consumes the exact QA
report, and `complete-run` is the only normal success terminalization path.

Run-level `BLOCKED`, `PAUSED`, `RUN_CANCELLED`, and `RUN_ABORTED` are distinct.
Only `RUN_COMPLETED` means success.

### Final run gate

Before `RUN_COMPLETED`, the host verifies:

- every original in-scope Required and Optional ticket is `DONE`;
- every accepted in-scope `REM-*` is `DONE`;
- every required core criterion is `VERIFIED` with the selected purpose boundary;
- every completion record/projection uses `[x]` for production or `[P]` for prototype; the canonical ticket contract remains immutable;
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

This package intentionally has **no cleanup command**. It retains worktrees,
reports, ledgers, transitions, and evidence. If a separate host-level cleanup
controller is explicitly authorized, that controller must persist intent,
inspect eligibility, execute an idempotent/reconcilable cleanup, and retain the
run summary/terminal evidence. An unknown cleanup result is reconciled by
inspecting actual artifact existence; it is never blindly repeated. Cleanup
does not alter the run's terminal outcome.

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
- purpose was resolved and persisted before first dispatch;
- production uses `default`/`tdd` only, while prototype has no production implementation mode;
- prototype scope covers the selected E2E journey from entry point to user outcome;
- complete graph admission passed before first dispatch;
- project root, clean target, branch, and baseline were recorded;
- system capacity was not managed through a host-side worker cap;
- Required priority and Optional processing were preserved;
- overlap was evaluated from declared, topology, and actual scope evidence;
- every role handoff passed schema and freshness validation;
- queued versus running agent state was not confused with progress;
- every side effect has logical operation identity, unique operation instance, and reconciliation semantics;
- every external agent job binding is attributable to run, unit, operation instance, provider, and attempt;
- every lifecycle change has a committed transition identity;
- active handoffs are separated from immutable historical evidence;
- every reviewer approval is explicit, authorized, fresh, and exact-revision;
- every ticket `DONE` passed exact integration and host validation evidence gates;
- acceptance status records the purpose and uses `[x]` for production or `[P]` for prototype;
- acceptance status is a projection and canonical contract digests remain attributable;
- environment blockers and reference snapshots have precise fingerprints/provenance;
- run-level QA used the appropriate outcome/evidence boundary;
- prototype QA exercised the complete declared E2E journey and recorded fake boundaries;
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
