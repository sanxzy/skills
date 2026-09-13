# Squad YAML State Tools

Squad uses separate `.mjs` entrypoints for each responsibility. The public
scripts are not interchangeable:

| Responsibility | Entry point | Writable purpose |
|---|---|---|
| Host | `scripts/squad-host-state.mjs` | Canonical run/work-unit state, operations, transitions, and host-owned indexes |
| Worker | `scripts/squad-worker-report.mjs` | The assigned worker report and incremental worker log |
| Reviewer | `scripts/squad-reviewer-report.mjs` | The assigned reviewer report and incremental review log |
| QA | `scripts/squad-qa-report.mjs` | The run-level QA report and incremental QA log |
| Analysis | `scripts/squad-analysis-report.mjs` | The assigned analysis/reconciliation report and incremental analysis log |

The entrypoints use the private `_yaml-io.mjs` and `_role-report.mjs` modules
for safe YAML primitives. Those modules are not public commands and do not
replace the responsibility-specific boundary.

## Runtime and authority

The scripts are `.mjs` files executed with Bun and use Bun's built-in YAML
parser/serializer. No third-party package dependency is required:

```text
bun <squad-skill-root>/scripts/<responsibility-script>.mjs <command> ...
```

The scripts perform file operations only. They do not grant authority, choose a
lifecycle transition, authorize a capability, or broaden a role's writable
scope. The host remains the sole writer of canonical run/work-unit state and
committed transitions. An agent may use only its own entrypoint for its
designated report, evidence index, and permitted worktree files.

Use the exact host-provided path. Do not use an agent entrypoint to modify
`tickets.md`, proposal scope, another role's report, or a target branch.

## Commands

The host entrypoint supports arbitrary canonical YAML paths:

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
`-`. `update` uses RFC 6901 JSON Pointer paths. For example,
`--set /status=COMPLETE` sets a scalar string and
`--set /coverage/exercised='["CSC-001"]'` sets a JSON array.

Mutation commands print a JSON result containing `command`, absolute `file`,
`changed`, and digest fields. `digest` prints the current `sha256:<hex>` value;
`read` prints the selected YAML/JSON value; `verify` prints a parse-validity
result and digest.

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
`--id-field operation_id` for host operation arrays or another stable field
when `id` is not the entry key.

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
- `update` only explicit fields such as final `status` and `verdict`, always
  with the current digest;
- read back after every mutation and retain the returned digest/evidence
  pointer;
- on interruption, resume the same report path and idempotently retry the same
  entry; create a new report path for a new attempt or invalidated revision;
- never claim a final verdict from an unverified or inline-only report.

The helper's atomic write and digest check protect the file, but the caller is
still responsible for validating schema, canonical revision, authority,
entry meaning, and outcome semantics.
