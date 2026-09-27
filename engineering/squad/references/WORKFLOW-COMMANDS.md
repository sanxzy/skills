# Squad Host Workflow Commands

Start with the [operator map in SKILL.md](../SKILL.md#operator-map-follow-this-path-first),
then use this file for exact command contracts, outputs, and recovery. The
[YAML state tools reference](./YAML-STATE-TOOLS.md) defines writer ownership and
low-level digest-safe operations.

The host workflow entrypoint is:

```text
bun <squad-skill-root>/scripts/squad.mjs <command> ...
```

It is a host-only control-plane helper. It does not spawn agents, select a
worker capacity, or delete retained artifacts. Ordinary commands do not mutate
the target branch; only the guarded `integrate` command performs an explicit,
fast-forward-only, durable target operation. The helper composes the low-level
`squad-host-state.mjs` YAML primitive with Git and cross-artifact validation.

## Canonical identity schema

Generated work-unit execution manifests and handoffs use schema version `1`
and these identity locations. Do not copy the same identity into alternative
locations:

```yaml
schema_version: 1
kind: squad-handoff
role: squad-worker                    # or squad-reviewer / squad-qa / squad-analysis-reconciliation
run_id: RUN-001
work_unit_id: T004
attempt_id: RUN-001:T004:worker:attempt-001
operation_id: RUN-001:T004:DISPATCH_WORKER
operation_instance_id: RUN-001:T004:DISPATCH_WORKER:attempt-001
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
  operation_path: <absolute .../operations/RUN-001:T004:DISPATCH_WORKER:attempt-001.yaml>
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
  instance_id: RUN-001:T004:DISPATCH_WORKER:attempt-001
  type: DISPATCH_WORKER
  attempt_id: RUN-001:T004:worker:attempt-001
report:
  path: <same artifact.report_path>
  digest: null
  expected: CREATE
evidence:
  directory: <same artifact.evidence_directory>
decisions:
  purpose: production | prototype
  mode: default | tdd | null # effective production mode, including an explicit unit override; null for prototype
  completion_marker: x | P
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

Run-level QA uses a separate immutable `kind: squad-qa-handoff` because it has
no work-unit worktree or unit lifecycle transition. It carries the admitted
purpose and completion marker so QA cannot confuse an E2E prototype pass with a
production pass. It carries `run_id`,
`qa_id`, `attempt_id`, `operation_id: <run-id>:RUN:DISPATCH_QA`, source/target
snapshots, `artifact.run_dir`, `artifact.operation_path`,
`artifact.report_path`, `artifact.evidence_directory`, and `state.current: QA`.
Use `validate-handoff` for this kind as well; do not force a QA handoff into the
work-unit schema.

Canonical naming is:

- logical operation ID: `<run-id>:<work-unit-id>:<UPPER_SNAKE_ACTION>`;
- operation instance ID: `<logical-operation-id>:attempt-<NNN>`; this uniquely identifies one ledger attempt;
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
on stderr and includes a stable `error` code. Identity and invariant errors
include `details.errors[]` entries with `field`, `code`, `actual`, `expected`,
`message`, and (when applicable) candidate paths. This makes a bad SHA, path,
branch, report revision, or ambiguous job binding actionable before mutation.

## Command contract at a glance

The host owns these commands. They write durable artifacts and return JSON with
`next_action` where another host/agent step is required. A role report helper is
used by the assigned role, not substituted with a host state update.

| Command | Preconditions | Durable result / next action |
|---|---|---|
| `migrate-run` | Existing run namespace | Normalizes legacy purpose/mode and active operation/handoff identity; missing legacy purpose becomes `production`/`default`, while prototype keeps mode unset; returns per-unit `MIGRATED`, `ALREADY_CURRENT`, or `BLOCKED` plus `control_plane_version: 2` |
| `environment-profile` | Admitted project root | Writes fingerprinted environment profile; required by default for `control_plane_version: 2` unless explicitly advisory |
| `analyze-ownership` | Run units and declared scopes available | Writes conservative `SAFE`/`CONDITIONAL`/`UNCERTAIN` report |
| `preflight` | Run source, target, units, worktrees, ledgers readable | `valid`, `dispatchable`, blockers, and ready frontier |
| `prepare` | Worker `READY`/`FIXING`, reviewer `AWAITING_REVIEW`, or advisory analysis on the current unit; reviewer context must be derivable | Validated work-unit handoff; `next_action: SPAWN_AGENT_WITH_VALIDATED_HANDOFF` |
| `bind-agent` | Durable `PREPARED` operation, manifest/handoff/report paths readable, validated handoff | External provider/job binding; `OBSERVE_AGENT_RESULT` |
| `acknowledge-agent` | Bound worker operation `EXECUTING`, exact job binding, handoff valid | `ASSIGNED → IMPLEMENTING`; queued/unstarted jobs are rejected |
| `reject-handoff` | Active pre-product-review handoff and `PREPARED`/`EXECUTING` operation, no product report | `BLOCKED` with `HANDOFF_REJECTED_BEFORE_PRODUCT_REVIEW`; no product verdict |
| `complete-analysis` | Active analysis handoff, exact `CONCLUSIVE`/`INCONCLUSIVE` report | Analysis operation `SUCCEEDED`; unit state unchanged; host evaluates the advisory report |
| `transition` | `--from` equals current work-unit state and destination is legal | Committed work-unit transition ledger |
| `transition-run` | `--from` equals current run state and destination is legal | Committed run transition ledger; never a work-unit transition |
| `complete-worker` | `IMPLEMENTING`, exact `IMPLEMENTED` report, clean worktree | `AWAITING_REVIEW`; active handoff archived |
| `complete-review` | `REVIEWING`, exact complete report and revision | `INTEGRATING`, `FIXING`, or `BLOCKED` according to verdict |
| `prepare-correction` | `FIXING` | New worker attempt and dispatch handoff |
| `integrate` | `INTEGRATING`, exact approved revision, clean expected target | Fast-forward integration snapshot; `RUN_HOST_VALIDATION_THEN_COMPLETE_TICKET` |
| `complete-ticket` | Successful integration, target unchanged, host validation `PASS`; structured evidence when `validation_evidence_required: true` | `DONE`; acceptance-status projection; identical repeat is idempotent, conflicting evidence is rejected |
| `prepare-qa` | Run `RUN_VALIDATING` and every unit `DONE`; or blocker `resume_state: QA` with code `AGENT_INTERRUPTED`/`QA_INCONCLUSIVE` | `RUN_VALIDATING → QA` or `BLOCKED → QA`; immutable run QA handoff |
| `complete-qa` | Run `QA`, exact complete QA report, current target revision, active QA operation | `PASSED → COMPLETING`; other verdicts → `BLOCKED` with explicit blocker |
| `complete-run` | Run `COMPLETING`, every unit `DONE`, QA `PASSED`, valid preflight | Final summary and `COMPLETING → RUN_COMPLETED` |
| `resume-run` | Run `PAUSED`, preflight valid, no unresolved operations/transitions | `PAUSED → EXECUTING`; continue eligible work |
| `reconcile-run-transition` | One uncommitted run transition; exact run/transition identity | `COMMITTED`, `ABORTED`, or explicit `UNKNOWN`; no guessed state change |
| `reconcile-agent` | Job/operation binding exists; `--state` for unit or `--run` for run QA | Effect classification and `AGENT_UNAVAILABLE` blocker |
| `resume-ticket` | `BLOCKED` with legal `resume_state` | New attempt/handoff; old effect retained and linked |
| `verify-run --final` | All units `DONE`, exact approved reviewer evidence, QA `PASSED`, final summary, run terminal transition already committed | Final verification only; it never terminalizes the run |

For every command, a non-zero result is a blocker/reconciliation signal, not a
license to edit the YAML manually. Read `status --explain` after a failure.

## Commands

### Validate a typed handoff

```text
squad.mjs validate-handoff <handoff.yaml> [--historical]
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
as role, purpose, applicable mode, completion marker, scope, and authority remain host decisions.

Generate the role view without retyping identifiers:

```text
squad.mjs handoff --manifest <manifest.yaml> [--output <handoff.yaml>]
```

### Prepare a guarded dispatch

```text
squad.mjs prepare --run <run.yaml> --state <state.yaml> --role worker
# `dispatch` is an alias for `prepare`.
squad.mjs bind-agent <job-id> --operation <operation.yaml> [--provider <agent-provider>]
squad.mjs acknowledge-agent <job-id> --state <state.yaml> --operation <operation.yaml>
squad.mjs reject-handoff --state <state.yaml> --operation <operation.yaml> --reason "missing context"
squad.mjs complete-worker --state <state.yaml> [--report <report.yaml>]
squad.mjs complete-review --state <state.yaml> [--report <report.yaml>]
squad.mjs complete-analysis --state <state.yaml> [--report <report.yaml>]
squad.mjs prepare-correction --state <state.yaml> [--attempt N]
squad.mjs integrate --state <state.yaml> [--attempt N]
squad.mjs complete-ticket --state <state.yaml> --validation <evidence.yaml> | --validation-status PASS
```

Preparation writes the dispatch operation in `PREPARED` status before the state side effect,
commits the legal `READY → ASSIGNED`, `FIXING → IMPLEMENTING`, or
`AWAITING_REVIEW → REVIEWING` transition when applicable, generates
an immutable manifest and handoff from the resulting state, validates the
exact handoff again, and records the prepared operation result. The command
returns `next_action: SPAWN_AGENT_WITH_VALIDATED_HANDOFF`; the host may then
create the agent using that exact handoff. The command itself never creates an
agent. `bind-agent` associates the external job ID with the already validated
`PREPARED` operation and moves that operation to `EXECUTING` before the host
observes the agent; the same binding is what `reconcile-agent` later uses.
The role result, not the preparation command, is what may later make that
operation `SUCCEEDED`. `complete-worker` and `complete-review` verify the exact
report, attempt, worktree revision, and operation instance before archiving the
active handoff. `complete-analysis` verifies the advisory report and operation
but deliberately leaves the work-unit lifecycle state unchanged. A reviewer
`APPROVED` result moves the unit to `INTEGRATING`; it never means `DONE`.

`integrate` performs a guarded fast-forward-only target mutation for the exact
approved revision and records target-before/target-after evidence. A reviewer
approval whose target checkpoint differs from the run checkpoint fails with
`APPROVAL_STALE`; a source that is not fast-forwardable fails with
`INTEGRATION_NOT_FAST_FORWARD`. Neither path rebases or silently rewrites the
approved revision. Target drift stops before mutation. `complete-ticket`
requires a successful integration and explicit host validation evidence before
committing `INTEGRATING → DONE`; runs with `validation_evidence_required: true`
require the structured `squad-host-validation` schema.


### Structured ticket validation evidence

When the admitted run has `validation_evidence_required: true`, the evidence
file passed to `complete-ticket` must contain:

```yaml
schema_version: 1
kind: squad-host-validation
status: PASS
target: { before: <sha>, after: <sha>, clean: true }
integration:
  source_revision: <sha>
  operation_instance_id: <integration operation instance>
  target_before: <sha>
  target_after: <sha>
checks: []
acceptance:
  criteria: []
  limitations: []
  completion_marker: x | P
review: { report_digest: sha256:... }
```

A repeated call with the same evidence digest and integration identity is
idempotent. Different evidence for an already `DONE` unit returns
`COMPLETION_EVIDENCE_CONFLICT` without mutation.

### Complete an advisory analysis

Analysis is optional and advisory. Prepare it with the normal work-unit
`prepare --role analysis`; bind and spawn the analysis agent with that exact
handoff. Consume its report only through the typed host command:

```text
squad.mjs complete-analysis --state <state.yaml> --report <analysis-report.yaml>
```

The report must belong to the active analysis attempt and have final status
`CONCLUSIVE` or `INCONCLUSIVE`. The command marks only the analysis operation
`SUCCEEDED`, archives the handoff, and leaves the work-unit state unchanged.
The host validates recommendations before any state change, retry, scope
change, or side effect. An analysis report is never an approval or a
reconciliation classification by itself.

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

### Control the run-level lifecycle and QA

Work-unit `transition` cannot change a run state. Use the separate run
controller commands:

```text
squad.mjs transition-run RUN-001 --run <run.yaml> \
  --from EXECUTING --to RUN_VALIDATING \
  --reason "All in-scope work units are DONE"

squad.mjs prepare-qa --run <run.yaml>
squad.mjs validate-handoff <run-dir>/qa/QA-001/handoff.yaml
squad.mjs bind-agent <qa-job-id> --operation <qa-operation.yaml>
# QA writes the exact report with squad-qa-report.mjs.
squad.mjs complete-qa --run <run.yaml> --report <qa-report.yaml>
squad.mjs complete-run --run <run.yaml>
squad.mjs verify-run RUN-001 --run <run.yaml> --final
```

`transition-run` requires the exact current run state and a legal destination;
it writes a run-scoped transition ledger. `prepare-qa` requires
`RUN_VALIDATING`, all work units `DONE`, a clean target, and the canonical
source/target identities; it commits `RUN_VALIDATING → QA` and creates a
separate `squad-qa-handoff`. `complete-qa` requires the active QA operation, an
exact `COMPLETE` report, and a canonical revision equal to the current target.
It commits `QA → COMPLETING` only for `PASSED`; `FAILED` and `INCONCLUSIVE`
become explicit `BLOCKED` blockers. `complete-run` requires `COMPLETING`,
passed QA, all units `DONE`, and valid preflight before committing
`COMPLETING → RUN_COMPLETED`. `verify-run --final` is read-only.

If the QA agent stops without a conclusive report, reconcile against the
run-level operation rather than a unit state:

```text
squad.mjs reconcile-agent <job-id> --run <run.yaml> --operation <qa-operation.yaml>
squad.mjs prepare-qa --run <run.yaml>   # only for allowed QA recovery blocker
```

The reconciliation result is intentionally `INCONCLUSIVE` when no durable QA
report exists; the host must not infer QA success from job termination.

For an explicit user pause, stop/quiesce tracked jobs first, then use the
run-scoped transition:

```text
squad.mjs transition-run RUN-001 --run <run.yaml> \
  --from EXECUTING --to PAUSED --reason "User requested pause"
squad.mjs resume-run RUN-001 --run <run.yaml>
```

If a run transition write is interrupted, reconcile its durable ledger before
creating another transition:

```text
squad.mjs reconcile-run-transition RUN-001 --run <run.yaml> \
  [--transition <transition.yaml>]
```

The command marks a transition `COMMITTED` only when the run projection is
already at its recorded destination, `ABORTED` only when it is still at the
recorded source, and `UNKNOWN` otherwise. `UNKNOWN` remains an escalation;
the command never guesses or edits the run projection.

`resume-run` performs preflight before restoring `EXECUTING`; it does not resume
an unresolved operation or infer that a paused agent completed.

### Commit a legal lifecycle transition

```text
squad.mjs transition T004 \
  --state <work-units/T004/state.yaml> \
  --from REVIEWING \
  --to FIXING \
  --reason "Finding F-003 requires a correction" \
  --operation RUN-001:T004:DISPATCH_REVIEWER \
  --operation-instance RUN-001:T004:DISPATCH_REVIEWER:attempt-002
```

The command requires the supplied `--from` to equal the latest durable state,
checks the transition table, writes a `PREPARED → COMMITTING → COMMITTED`
transition ledger, updates the projection with the transition identity, and
reads both artifacts back. An illegal transition or stale source state is
rejected without changing the projection. An interrupted commit remains
reconcilable instead of being treated as success. In the normal worker path,
use it only after the agent system confirms the worker acknowledged the
handoff (`ASSIGNED → IMPLEMENTING`); report completion uses `complete-worker`,
not a hand-written state update.

### Reconcile an interrupted agent and resume it

```text
squad.mjs reconcile-agent JOB-123 --state <state.yaml>
squad.mjs resume-ticket T004 --state <state.yaml> --role worker
```

`reconcile-agent` resolves exactly one durable operation by external job identity.
A reused or ambiguous job ID fails with `AMBIGUOUS_AGENT_JOB` before mutation
unless the exact `--operation` is supplied. It inspects the recorded worktree,
report, branch, HEAD, and dirty state, changes an uncertain operation through
`UNKNOWN` to `RECONCILING`, and records a structured `AGENT_UNAVAILABLE`
blocker. It never resets, cleans, stashes, deletes, or silently discards a dirty
worktree. A successful successor resume marks the old operation `SUPERSEDED`
with retained-effect evidence; this is not a success or approval verdict.

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

`status` is read-only and reports state, blocker, revision, active versus
historical handoff, exact accepted reviewer proof, latest operation/transition,
reviewer findings, environment profile, dependency readiness, dirty worktree,
control-plane version, context health, accepted revision, target checkpoint,
blocker type/code, and the next legal action. `--explain` includes the legal
destination states
and the dependency basis. It is a projection, never a second mutable source of truth.

`verify-run` rechecks source/target identity and every durable artifact,
rejects unresolved operations and uncommitted transitions, and reports QA and
work-unit completeness. `--final` additionally requires every in-scope unit to
be `DONE` with exact approved reviewer evidence, a `PASSED` QA report, a
matching durable final summary, and the run projection to already be
`RUN_COMPLETED`; verification never terminalizes the run for the host.

## Operator quickstart

This is the normal one-ticket path. Replace placeholders with absolute paths
from the admitted run; do not hand-copy SHA values between files.

### A. Admit and prepare

1. Resolve the one canonical `tickets.md`, project root, target branch, clean
target checkout, purpose, applicable worker mode, complete graph, and initial
target HEAD. Use `production` with `default`/`tdd`, or `prototype` with no
production worker mode.
2. Persist/read back `run.yaml`, the unit `state.yaml`, and the admission
checkpoint. Provision and verify the canonical isolated worktree.
3. For an older run, run `migrate-run`; it writes a safe explicit
non-required environment policy and reports `LEGACY_ENVIRONMENT_PROFILE_MISSING`
when no profile exists. Before first dispatch, run `environment-profile`,
`analyze-ownership`, and `preflight`. A new `control_plane_version: 2` run
requires a profile path and digest by default unless it explicitly records
`environment_profile_required: false`. A failed preflight is a blocker; do not
create an agent.

```text
squad.mjs migrate-run --run <run.yaml>                 # existing runs only
# A control_plane_version: 2 run requires a profile by default; set
# environment_profile_required: false only for an explicitly advisory profile.
squad.mjs environment-profile --run <run.yaml>
squad.mjs analyze-ownership --run <run.yaml>
squad.mjs preflight --run <run.yaml>
```

### B. Implement one worker attempt

4. Optional: inspect a generated manifest. Then prepare the actual dispatch
with a fresh immutable output path if needed:

```text
squad.mjs prepare --run <run.yaml> --state <state.yaml> \
  --role worker --output <dispatch-manifest.yaml>
```

Expected result: `state: ASSIGNED` and
`next_action: SPAWN_AGENT_WITH_VALIDATED_HANDOFF`. Validate the returned handoff
if inspecting it separately, bind the external job, then spawn the worker only
with that exact handoff:

```text
squad.mjs bind-agent <job-id> --provider <agent-provider> \
  --operation <operation.yaml>
```

5. Keep the unit `ASSIGNED` while the agent system queues/starts the job. After
the worker acknowledges the handoff, commit the host-owned acknowledgement:

```text
squad.mjs transition <unit-id> --state <state.yaml> \
  --from ASSIGNED --to IMPLEMENTING \
  --reason "Worker acknowledged the validated handoff" \
  --operation <logical-operation-id> \
  --operation-instance <operation-instance-id>
```

6. The worker edits/commits only its worktree and writes its own durable report.
After the report says `IMPLEMENTED`, the host records the exact report:

```text
squad.mjs complete-worker --state <state.yaml> --report <worker-report.yaml>
```

Expected result: `IMPLEMENTING → AWAITING_REVIEW`, exact implementation
revision recorded, and the worker handoff moved to historical evidence.

### C. Review and correction

7. Prepare/bind/spawn the reviewer from `AWAITING_REVIEW`. The reviewer
handoff contains the exact worker revision. The host does not edit the review
report; the reviewer writes it with `squad-reviewer-report.mjs`.

```text
squad.mjs prepare --run <run.yaml> --state <state.yaml> \
  --role reviewer --output <review-dispatch-manifest.yaml>
squad.mjs bind-agent <review-job-id> --operation <review-operation.yaml>
```

Expected result: `AWAITING_REVIEW → REVIEWING`. On the exact completed report:

```text
squad.mjs complete-review --state <state.yaml> --report <review-report.yaml>
```

The result is one of:

- `APPROVED`: `REVIEWING → INTEGRATING`;
- `REJECTED`: `REVIEWING → FIXING`;
- `INCONCLUSIVE`: `REVIEWING → BLOCKED` with an evidence/capability blocker.

For `FIXING`, run `prepare-correction`; it creates a new worker attempt. Never
reuse the old approval or review a different revision without a new handoff.

### D. Integrate and complete the unit

8. Only after `APPROVED`, run the guarded fast-forward integration:

```text
squad.mjs integrate --state <state.yaml>
```

It stops before target mutation on branch/dirty/HEAD drift. On success, run the
strongest host-owned project checks and persist their evidence. Then:

```text
squad.mjs complete-ticket --state <state.yaml> \
  --validation <host-validation.yaml>
```

The validation evidence must resolve to `PASS`/`PASSED`. Expected result:
`INTEGRATING → DONE` plus `summaries/acceptance-status.yaml`.

### E. Validate the run and retain evidence

9. Repeat the unit path for every eligible Required and Optional work unit. When
all units are `DONE`, commit the run-level transition and use the typed QA path:

```text
squad.mjs transition-run RUN-001 --run <run.yaml> \
  --from EXECUTING --to RUN_VALIDATING \
  --reason "All in-scope work units are DONE"
squad.mjs prepare-qa --run <run.yaml>
squad.mjs bind-agent <qa-job-id> --operation <qa-operation.yaml>
```

QA writes its report/evidence using `squad-qa-report.mjs` and returns `PASSED`,
`FAILED`, or `INCONCLUSIVE`. The agent never changes lifecycle state. The host
consumes the exact report:

```text
squad.mjs complete-qa --run <run.yaml> --report <qa-report.yaml>
```

10. For `PASSED`, complete and verify the run:

```text
squad.mjs complete-run --run <run.yaml>
squad.mjs verify-run RUN-001 --run <run.yaml> --final
```

For `FAILED`/`INCONCLUSIVE`, retain the blocker, attribute/remediate or repair
the evidence, and resume only through a legal typed run transition/path. This
package has no cleanup command; retain worktrees, reports, ledgers, transitions,
and evidence unless a separately authorized host cleanup controller handles
them.

## Failure runbook

| Symptom | Standard action | Do not do |
|---|---|---|
| Bad SHA/path/branch in handoff | Stop; run `validate-handoff`, repair the authoritative host input or state through the typed command, and generate a fresh immutable manifest/handoff | Spawn the worker and ask it to diagnose copied identifiers |
| Reviewer rejects exact revision | `complete-review` → `FIXING` → `prepare-correction`; preserve the worktree, create a new worker/review attempt, and re-review the new revision | Reuse the old approval |
| Reviewer is inconclusive | Repair the named capability/context/evidence, then resume the saved review state | Convert missing proof into `APPROVED` or `REJECTED` |
| Worker interruption | `reconcile-agent <job-id> --state <state.yaml>`, inspect the durable blocker, then `resume-ticket <unit-id>` | Reset/clean/delete the worktree or mark it implemented from termination |
| Run-level QA interruption | `reconcile-agent <job-id> --run <run.yaml>`, inspect the explicit blocker, then `prepare-qa --run <run.yaml>` only when `resume_state: QA` and code is `AGENT_INTERRUPTED` or `QA_INCONCLUSIVE` | Infer QA success, repeat the job blindly, or mutate `run.yaml` manually |
| Target branch drift | Stop target mutation, reconcile target HEAD and affected active handoffs, and run preflight again | Rebase or overwrite the target silently |
| Reused/ambiguous agent job ID | Supply the exact `--operation` after inspecting candidates | Reconcile the first filesystem match |
| Historical handoff after target integration | `validate-handoff <handoff.yaml> --historical`; verify the archived report digest and recorded snapshot | Treat a moving target or current state as proof that historical evidence is invalid |
| Unknown operation/transition | Inspect actual effect and durable ledger, then reconcile before a new attempt | Repeat a non-idempotent side effect blindly |
| `complete-ticket` validation is not `PASS` | Keep the unit `INTEGRATING`; repair checks or record the explicit blocker | Mark `DONE` from a merge exit code alone |
| Dirty recovery worktree | Preserve and classify its changes before resuming | Stash, discard, or absorb unexplained changes |
| Missing required QA capability | Complete the exact report as `INCONCLUSIVE`; `complete-qa` records `QA_INCONCLUSIVE` and blocks the run | Substitute a weaker strategy without authorization |
| Scope gap or new requirement | Persist the finding and escalate for canonical clarification | Create a hidden `REM-*` |

If a command reports a persistent write/read-back failure, keep the previous
authoritative state, retain all partial artifacts, and follow the operation
reconciliation path. Never turn a command error or an agent termination into a
success verdict.
