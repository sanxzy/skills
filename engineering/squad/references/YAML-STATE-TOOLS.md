# Squad YAML State Tools

Read the [operator map in SKILL.md](../SKILL.md#operator-map-follow-this-path-first)
and the [host workflow command contracts](./WORKFLOW-COMMANDS.md) before using
these primitives. This file explains writer ownership, report boundaries, and
digest-safe exceptional mutations.

Squad has a host workflow entrypoint and separate responsibility-specific YAML
entrypoints. The public scripts are not interchangeable:

| Responsibility | Entry point | Writable purpose |
|---|---|---|
| Host workflow | `scripts/squad.mjs` | Typed handoffs, execution manifests, Git identity checks, legal transitions, preflight, recovery, status, and run verification |
| Host primitive | `scripts/squad-host-state.mjs` | Low-level canonical run/work-unit state, operations, transitions, and host-owned indexes |
| Worker | `scripts/squad-worker-report.mjs` | The assigned worker report and incremental worker log |
| Reviewer | `scripts/squad-reviewer-report.mjs` | The assigned reviewer report and incremental review log |
| QA | `scripts/squad-qa-report.mjs` | The run-level QA report and incremental QA log |
| Analysis | `scripts/squad-analysis-report.mjs` | The assigned analysis/reconciliation report and incremental analysis log |

The high-level host command contracts, canonical identity schema, quickstart,
and failure runbook are in [WORKFLOW-COMMANDS.md](./WORKFLOW-COMMANDS.md).

The control plane keeps the logical `operation_id` stable for idempotency and
adds a unique `operation_instance_id` per attempt. Current state may point to
one `active_handoff`; completed handoffs remain immutable in
`handoff_history` and are validated with historical snapshot semantics. The
admitted purpose (`production` or `prototype`), applicable implementation mode,
and completion marker (`[x]` or `[P]`) are durable run/handoff decisions, not
free-form agent assumptions.

## Runtime and authority

The scripts are `.mjs` files executed with Bun and use Bun's built-in YAML
parser/serializer. No third-party package dependency is required:

```text
bun <squad-skill-root>/scripts/<entrypoint>.mjs <command> ...
```

The high-level `squad.mjs` entrypoint performs cross-artifact and Git checks,
then composes the low-level YAML primitives. It does not spawn agents or choose
capacity. Ordinary commands do not mutate the target branch; only the guarded
`integrate` command performs a durable fast-forward-only target operation. No
command deletes retained artifacts.

The low-level host entrypoint and role report entrypoints perform file
operations only. They do not grant authority, choose a lifecycle transition,
authorize a capability, or broaden a role's writable scope. The host remains
the sole writer of canonical run/work-unit state and committed transitions. An
agent may use only its own entrypoint for its designated report, evidence index,
and permitted worktree files.

Use the exact host-provided path. Do not use an agent entrypoint to modify
`tickets.md`, proposal scope, another role's report, or a target branch.

## Host workflow commands

Use the host workflow entrypoint for normal operations:

```text
squad.mjs validate-handoff <handoff.yaml>
squad.mjs manifest --run <run.yaml> --state <state.yaml> [--ticket <ticket.md>] --role worker
squad.mjs handoff --manifest <manifest.yaml>
squad.mjs prepare --run <run.yaml> --state <state.yaml> --role worker
squad.mjs bind-agent <job-id> --operation <operation.yaml> [--provider <agent-provider>]
squad.mjs acknowledge-agent <job-id> --state <state.yaml> --operation <operation.yaml>
squad.mjs reject-handoff --state <state.yaml> --operation <operation.yaml> --reason <text>
squad.mjs complete-worker --state <state.yaml> [--report <report.yaml>]
squad.mjs complete-review --state <state.yaml> [--report <report.yaml>]
squad.mjs complete-analysis --state <state.yaml> [--report <report.yaml>]
squad.mjs prepare-correction --state <state.yaml>
squad.mjs integrate --state <state.yaml>
squad.mjs complete-ticket --state <state.yaml> --validation <evidence.yaml>
squad.mjs transition-run RUN-001 --run <run.yaml> --from EXECUTING --to RUN_VALIDATING --reason <text>
squad.mjs prepare-qa --run <run.yaml>
squad.mjs complete-qa --run <run.yaml> --report <qa-report.yaml>
squad.mjs complete-run --run <run.yaml>
squad.mjs resume-run RUN-001 --run <run.yaml>
squad.mjs reconcile-run-transition RUN-001 --run <run.yaml> [--transition <transition.yaml>]
squad.mjs environment-profile --run <run.yaml>
squad.mjs reference-snapshot --run <run.yaml> --repository <path>
squad.mjs analyze-ownership --run <run.yaml>
squad.mjs migrate-run --run <run.yaml>
squad.mjs preflight --run <run.yaml>
squad.mjs transition T004 --state <state.yaml> --from REVIEWING --to FIXING --reason <finding>
squad.mjs reconcile-agent <job-id> --state <state.yaml> | --run <run.yaml>
squad.mjs resume-ticket T004 --state <state.yaml>
squad.mjs status RUN-001 --run <run.yaml> --explain
squad.mjs verify-run RUN-001 --run <run.yaml>
```

`prepare`/`dispatch` validates and persists the dispatch operation before
returning a handoff-ready result; it carries the admitted purpose and applicable
implementation mode into the generated manifest/handoff but does not create an
agent. `bind-agent`
only binds readable, validated artifacts. `acknowledge-agent` is the typed
`ASSIGNED → IMPLEMENTING` path; `reject-handoff` records a pre-product-review
context rejection without creating a product verdict. `transition` uses the work-unit legal state table; `transition-run` uses the separate run
state table and ledger. `complete-worker` and `complete-review` consume exact
role reports; `complete-analysis` consumes an advisory report without changing
unit lifecycle state; `prepare-qa`, `complete-qa`, `complete-run`, and
`resume-run` control the run-level QA/pause/terminal path. `integrate` is the only target-mutating command;
`complete-ticket` requires host validation evidence.
Recovery commands preserve dirty worktrees and make a new attempt rather than
overwriting the old one. See [the operator map and workflow runbook](./WORKFLOW-COMMANDS.md)
for the exact preconditions, outputs, and recovery branches.

## Authority boundary: choose the right writer

| Need | Use | Who writes |
|---|---|---|
| Normal lifecycle, handoffs, Git identity, recovery, integration | `scripts/squad.mjs` | Host workflow; typed validation and read-back |
| Worker/reviewer/QA/analysis report or incremental log | Role-specific report entrypoint | The assigned role only |
| Agent scheduling/job status | Agent system | Agent system; host records the durable binding |
| Exceptional host reconciliation | `squad-host-state.mjs` | Host, with expected digest and an explicit reason |

Do not use a role report helper to mutate shared state. Do not use the low-level
host primitive to skip a typed gate because a routine command is inconvenient.
If a low-level mutation is unavoidable, record why in the operation/history and
run `preflight` again before continuing.

## Low-level primitive commands

The host primitive supports arbitrary canonical YAML paths:

```text
squad-host-state.mjs create --file <path> --data <json|yaml|@file|->
squad-host-state.mjs update --file <path> --expect-digest <sha256:...> --set <json-pointer>=<value> [...]
squad-host-state.mjs append --file <path> --expect-digest <sha256:...> --path <json-pointer> --entry <json|yaml|@file|-> [--id-field <field>] [--id <value>]
squad-host-state.mjs read --file <path> [--path <json-pointer>] [--format yaml|json]
squad-host-state.mjs digest --file <path>
squad-host-state.mjs verify --file <path>
squad-host-state.mjs unlock --file <path> --force
```

Each agent report entrypoint supports the same create/update/read/digest/verify
and unlock commands, but appends only to its fixed responsibility log path:

```text
squad-worker-report.mjs   → /incremental_worker_log
squad-reviewer-report.mjs → /incremental_review_log
squad-qa-report.mjs       → /incremental_qa_log
squad-analysis-report.mjs → /incremental_analysis_log
```

Agent `append` therefore does not accept `--path`; this prevents an agent from
using its report helper to target another report section. Agent `create`
ensures the expected `role` and fixed incremental log exist. Agent `update`,
`read`, `digest`, and `verify` reject a report with a different role. Input
values may be inline JSON/YAML, read from `@<path>`, or read from stdin with
`-`. Mutation commands print a JSON result containing `command`, absolute
`file`, `changed`, and digest fields. `digest` prints the current
`sha256:<hex>` value; `read` prints the selected YAML/JSON value; `verify`
prints a parse-validity result and digest.

## Safe mutation protocol

1. Read the current file and obtain its digest with the responsibility-specific
   `digest` or `read` command.
2. Call `update` or `append` with that exact `--expect-digest`.
3. Capture the command result and its new digest.
4. Read or `verify` the file and confirm the expected entry/value, role, and
   digest.
5. Treat a `STALE_DIGEST`, `LOCKED`, or other error as a failed operation; do
   not overwrite the file with a newly selected digest without reconciliation.

`create` fails if the destination already exists. `update` and `append` require
an expected digest, use an exclusive sibling lock, preserve the existing file
mode, write a temporary file, sync it, and atomically rename it into place.

`append` requires a stable, non-empty identity field. It is idempotent when an
entry with the same identity already has identical content; it returns
`changed: false` without rewriting the file. The same identity with different
content returns `APPEND_CONFLICT` and does not mutate the file. Use
`--id-field operation_instance_id` for host operation arrays or another stable
field when `id` is not the entry key. `RECONCILED` and `SUPERSEDED` are terminal
ledger classifications for inspected effects; neither means product success.

If a process is interrupted while holding a sibling `.lock` directory, first
verify that no writer is active and that the operation is reconciled, then use
that responsibility's `unlock --force` command. Never remove an active lock or
retry an unknown side effect blindly.

## Report usage

For a worker, reviewer, QA, or analysis report:

- use the responsibility-specific entrypoint, never the host entrypoint;
- `create` the report as `IN_PROGRESS`/`PENDING` before the first product or
  environment side effect;
- `append` each proof, criterion, strategy, operation, evidence, finding, or
  limitation immediately with a stable entry ID;
- read back after every mutation and retain the returned digest/evidence pointer;
- on interruption, resume the same report path and idempotently retry the same
  entry; create a new report path for a new attempt or invalidated revision;
- never claim a final verdict from an unverified or inline-only report.

The helper's atomic write and digest check protect the file, but the caller is
still responsible for validating schema, canonical revision, authority, entry
meaning, and outcome semantics.

Role reports do not advance lifecycle state by themselves:

- worker `IMPLEMENTED` → host validates with `complete-worker`;
- reviewer `APPROVED`/`REJECTED`/`INCONCLUSIVE` → host validates with
  `complete-review`;
- QA `PASSED`/`FAILED`/`INCONCLUSIVE` → `complete-qa` records the exact verdict and commits the guarded run transition or blocker;
- analysis `CONCLUSIVE`/`INCONCLUSIVE` → `complete-analysis` archives advisory input only; host validates every effect.

A report path, digest, attempt, exact revision, purpose, and completion marker
must remain linked when the host accepts the result. A report verdict is never
a substitute for a committed transition.
