# Squad Host Workflow Commands

The host workflow entrypoint is:

```text
bun <squad-skill-root>/scripts/squad.mjs <command> ...
```

It is a host-only control-plane helper. It does not spawn agents, select a
worker capacity, mutate the target branch, or delete retained artifacts. It
composes the low-level `squad-host-state.mjs` YAML primitive with Git and
cross-artifact validation.

## Canonical identity schema

Generated execution manifests and handoffs use schema version `1` and these
identity locations. Do not copy the same identity into alternative locations:

```yaml
schema_version: 1
kind: squad-handoff
role: squad-worker                    # or squad-reviewer / squad-qa / squad-analysis-reconciliation
run_id: RUN-001
work_unit_id: T004
attempt_id: RUN-001:T004:worker:attempt-001
operation_id: RUN-001:T004:DISPATCH_WORKER
source:
  tickets_index_path: <absolute .../_xzy-ai/sprints/<backlog>/tickets.md>
  tickets_digest: sha256:<64 hex characters>
  work_unit_path: <absolute ticket or REM record>
  ticket_digest: sha256:<64 hex characters>
artifact:
  run_dir: <absolute .../orchestration/RUN-001>
  state_path: <absolute .../work-units/T004/state.yaml>
  manifest_path: <absolute manifest.yaml>
  handoff_path: <absolute handoff.yaml>
  operation_path: <absolute .../operations/RUN-001:T004:DISPATCH_WORKER.yaml>
  report_path: <absolute .../worker/attempt-001/report.yaml>
  evidence_directory: <absolute .../evidence/worker/attempt-001>
target:
  repository_root: <absolute project root>
  repository_id: <absolute shared Git directory>
  branch: main
  head: <commit revision>
worktree:
  path: <absolute workspace worktree>
  relative_path: worktrees/squad/<backlog>/<run-id>/<work-unit-id>
  repository_id: <absolute shared Git directory>
  branch: squad/RUN-001/T004
  baseline: <commit revision>
  current_head: <commit revision>
state:
  current: ASSIGNED
  expected: ASSIGNED
dependencies: []
operation:
  id: RUN-001:T004:DISPATCH_WORKER
  type: DISPATCH_WORKER
  attempt_id: RUN-001:T004:worker:attempt-001
report:
  path: <same artifact.report_path>
  digest: null
  expected: CREATE
evidence:
  directory: <same artifact.evidence_directory>
decisions:
  mode: default | tdd
  scope: <host-supplied scope boundary>
  authority: <host-supplied authority boundary>
manifest:
  path: <same artifact.manifest_path>
  digest: sha256:<digest of the immutable manifest>
```

`report.digest: null` with `expected: CREATE` is valid for a new worker
attempt. A handoff for a role whose report already exists must carry its exact
file digest and `expected: EXISTING`. A reviewer handoff must also carry
`implementation_revision`; the validator resolves it in the target repository.

Canonical naming is:

- operation ID: `<run-id>:<work-unit-id>:<UPPER_SNAKE_ACTION>`;
- attempt ID: `<run-id>:<work-unit-id>:<role-key>:attempt-<NNN>`;
- role keys: `worker`, `reviewer`, `qa`, and `analysis`;
- `attempt_id` is the only durable attempt identity field. Use
  `review_attempt_id` only as a descriptive projection of a reviewer
  `attempt_id`, and use `fix_attempt` only as a numeric correction count; do
  not create competing ID formats;
- state fields: `baseline`, `target.head`, and `worktree.current_head`;
- reports: `work-units/<unit>/<role>/attempt-<NNN>/report.yaml`;
- worktrees: `<workspace>/worktrees/squad/<backlog>/<run-id>/<work-unit-id>/`;
- recovery worktrees: a pre-provisioned `recovery-<NNN>` child of that unit
  directory.

The mutable operation status is read from `artifact.operation_path`; it is
intentionally not copied into the immutable handoff. A command error is JSON
on stderr and includes a stable `error` code. Identity
and invariant errors include `details.errors[]` entries with `field`, `code`,
`actual`, `expected`, and `message`. This makes a bad SHA, path, branch, or
report revision actionable before an agent is created.

## Commands

### Validate a typed handoff

```text
squad.mjs validate-handoff <handoff.yaml>
```

The validator checks the YAML shape, canonical source and report digests,
state/run/unit/attempt/operation relationships, dependency `DONE` status,
canonical artifact paths, Git repository/worktree identity, `git cat-file`
resolution for every revision, branch and HEAD freshness, and legal transition
shape. A failed validation is non-zero and must stop dispatch.

### Generate an immutable execution manifest

```text
squad.mjs manifest \
  --run <run.yaml> \
  --state <work-units/T004/state.yaml> \
  [--ticket <T004.md>] \
  --role worker \
  --attempt 001 \
  [--output <manifest.yaml>]
```

The command reads the run/state/Git context, computes current digests and
identities, derives report/evidence/operation paths, records dependency
snapshots, and writes an immutable manifest. It fails rather than silently
overwriting a manifest with a different snapshot. The manifest is the source
for generated handoffs and dispatch-operation input; substantive decisions such
as role, mode, scope, and authority remain host decisions.

Generate the role view without retyping identifiers:

```text
squad.mjs handoff --manifest <manifest.yaml> [--output <handoff.yaml>]
```

### Prepare a guarded dispatch

```text
squad.mjs prepare --run <run.yaml> --state <state.yaml> --role worker
# `dispatch` is an alias for `prepare`.
squad.mjs bind-agent <job-id> --operation <operation.yaml>
```

Preparation writes the dispatch operation in `PREPARED` status before the state side effect,
commits the legal `READY → ASSIGNED` (worker) or
`AWAITING_REVIEW → REVIEWING` (reviewer) transition when applicable, generates
an immutable manifest and handoff from the resulting state, validates the
exact handoff again, and records the prepared operation result. The command
returns `next_action: SPAWN_AGENT_WITH_VALIDATED_HANDOFF`; the host may then
create the agent using that exact handoff. The command itself never creates an
agent. `bind-agent` associates the external job ID with the already validated
`PREPARED` operation and moves that operation to `EXECUTING` before the host
observes the agent; the same binding is what `reconcile-agent` later uses.
The worker result, not the preparation command, is what may later make that
operation `SUCCEEDED`.


### Preflight the whole run

```text
squad.mjs preflight --run <run.yaml>
# or: squad.mjs preflight --run-dir <orchestration-dir>
```

Preflight checks the canonical source digest, target repository/branch/HEAD,
work-unit identities and states, dependency references and cycles, recorded
worktrees, existing handoffs, operations, and transitions. It evaluates every
unit before any dispatch; a `READY` unit with an unfinished dependency is a
preflight blocker rather than an agent-time discovery.

### Commit a legal lifecycle transition

```text
squad.mjs transition T004 \
  --state <work-units/T004/state.yaml> \
  --from REVIEWING \
  --to FIXING \
  --reason "Finding F-003 requires a correction" \
  [--operation RUN-001:T004:REVIEW]
```

The command requires the supplied `--from` to equal the latest durable state,
checks the transition table, writes a `PREPARED → COMMITTING → COMMITTED`
transition ledger, updates the projection with the transition identity, and
reads both artifacts back. An illegal transition or stale source state is
rejected without changing the projection. An interrupted commit remains
reconcilable instead of being treated as success.

### Reconcile an interrupted agent and resume it

```text
squad.mjs reconcile-agent JOB-123 --state <state.yaml>
squad.mjs resume-ticket T004 --state <state.yaml> --role worker
```

`reconcile-agent` locates the durable operation by `job_id`, inspects the
recorded worktree, report, branch, HEAD, and dirty state, changes an uncertain
operation through `UNKNOWN` to `RECONCILING`, and records a structured
`AGENT_UNAVAILABLE` blocker. It never resets, cleans, stashes, deletes, or
silently discards a dirty worktree.

`resume-ticket` selects the next attempt (or an explicitly requested
replacement), preserves the existing worktree when usable, creates a new
attempt-scoped operation/manifest/handoff, validates it against the latest
state, and only then restores the recorded legal resume state. A replacement
path must already be provisioned under the canonical unit directory; the
command does not guess a repository or create an untracked sibling worktree.

### Read status and verify the run

```text
squad.mjs status RUN-001 --run <run.yaml> --ticket T004 --explain
squad.mjs verify-run RUN-001 --run <run.yaml>
squad.mjs verify-run RUN-001 --run <run.yaml> --final
```

`status` is read-only and reports state, blocker, revision, latest
operation/transition, reviewer verdict, dependency readiness, dirty worktree,
and the next legal action. `--explain` includes the legal destination states
and the dependency basis.

`verify-run` rechecks source/target identity and every durable artifact,
rejects unresolved operations and uncommitted transitions, and reports QA and
work-unit completeness. `--final` additionally requires every in-scope unit to
be `DONE`, a `PASSED` QA report, and the run projection to already be
`RUN_COMPLETED`; verification never terminalizes the run for the host.

## Operator quickstart

This is the normal one-ticket path. Replace placeholders with absolute paths
from the admitted run; do not hand-copy SHA values between files.

1. Read and admit the canonical `tickets.md`, project root, target branch, and
   clean target checkout.
2. Persist `run.yaml`, `work-units/T004/state.yaml`, and the admission
   checkpoint.
3. Provision the canonical worktree and verify its branch and baseline.
4. Run `squad.mjs preflight --run <run.yaml>`.
5. Optionally inspect an immutable context snapshot:
   `squad.mjs manifest --run <run.yaml> --state <state.yaml> --role worker --output <inspection-manifest.yaml>` (the ticket path is taken from state; `--ticket` is an explicit override).
6. Run `squad.mjs prepare --run <run.yaml> --state <state.yaml> --role worker --output <dispatch-manifest.yaml>`. Use a fresh output path when an inspection manifest already exists; manifests are immutable.
7. Run `squad.mjs bind-agent <job-id> --operation <operation.yaml>`, then spawn
   the worker only with the returned validated handoff; the durable job binding
   is what recovery later uses.
8. After a valid worker report, use a generated reviewer manifest/handoff and
   dispatch the reviewer; require the exact worker revision in the reviewer
   handoff.
9. On `APPROVED`, integrate only that exact revision, run host-owned checks,
   and use `transition` for each legal lifecycle advance.
10. When every unit is `DONE`, run universal QA, retain its evidence, and use
    `status`/`verify-run` to inspect the aggregate outcome.
11. Only after the host commits the terminal `RUN_COMPLETED` transition is the
    run successful. Cleanup is a separate explicit operation.

## Failure runbook

| Symptom | Standard action | Do not do |
|---|---|---|
| Bad SHA/path/branch in handoff | Stop; run `validate-handoff`, repair the source manifest, and generate a fresh handoff | Spawn the worker and ask it to diagnose copied identifiers |
| Reviewer rejects exact revision | Transition to `FIXING`, preserve the worktree, create a new worker/review attempt, and re-review the new revision | Reuse the old approval |
| Worker interruption | `reconcile-agent <job-id>`, inspect the durable blocker, then `resume-ticket <unit-id>` | Reset/clean/delete the worktree or mark it implemented from termination |
| Target branch drift | Stop target mutation, reconcile target HEAD and affected handoffs, and run preflight again | Rebase or overwrite the target silently |
| Unknown operation/transition | Inspect actual effect and durable ledger, then reconcile before a new attempt | Repeat a non-idempotent side effect blindly |
| Dirty recovery worktree | Preserve and classify its changes before resuming | Stash, discard, or absorb unexplained changes |
| Missing required QA capability | Record `INCONCLUSIVE` with its evidence boundary and block the affected path | Substitute a weaker strategy without authorization |
| Scope gap or new requirement | Persist the finding and escalate for canonical clarification | Create a hidden `REM-*` |

If a command reports a persistent write/read-back failure, keep the previous
authoritative state, retain all partial artifacts, and follow the operation
reconciliation path. Never turn a command error or an agent termination into a
success verdict.
