---
name: dispatch-for-implementation
version: 1.0.0
description: A simpler, stricter implementation coordinator that dispatches work units one at a time to a team of 6 agents with strict required-input contracts. Fully sequential execution with phase-gated review gates. Native integration with generate-tickets ticket.md.
---

# Skill: dispatch-for-implementation

## Overview

`dispatch-for-implementation` is a multi-agent implementation coordinator that dispatches work units one at a time to a team of specialized agents with strict required-input contracts.

It runs **fully sequentially** — one work unit at a time, globally. No concurrent workers, no merge serialization, no worktree conflicts. Each work unit goes through a complete lifecycle: create worktree → implement → 3 review gates → merge → tick → cleanup.

The key design differences are:

1. **Fully sequential execution** — one work unit at a time, globally. No concurrent workers.
2. **Strict delegation** — every agent defines explicit required inputs. If the coordinator delegates without providing all required inputs, the agent **rejects** with a plain-text message listing what's missing.
3. **Direct checkbox passthrough** — if the user provides a file with `[x]` checked items, those become work units directly without transformation.
4. **Two input paths** — `ticket.md` from `generate-tickets` is parsed directly (no normalization). All other input types go through a normalization pipeline.
5. **Lightweight state** — a pure-markdown `progress.md` event log tracks all execution events and issue resolutions.

---

## Input Handling

### Two Input Paths

The coordinator uses **two separate code paths** depending on the input:

| Input Type | Path | Description |
|---|---|---|
| `ticket.md` from generate-tickets | **Direct Parse** | No normalization. Tickets are parsed into work units directly. |
| Everything else | **Normalization** | Free-form, checklists, structured plans, barrel plans, task lists, no input. |

### Native: generate-tickets `ticket.md`

When the user provides a path to a `ticket.md` file produced by `generate-tickets`, the coordinator:

1. Reads the file and parses each `## NN — Title` section into a work unit.
2. Extracts `What to build`, `Blocked by`, `Status`, and acceptance criteria (`- [ ]` items).
3. Builds a dependency graph from `Blocked by` references.
4. Derives phases from the dependency graph (see Phase Determination below).
5. If the user has pre-checked any `[x]` items in the ticket.md, those work units are **skipped** (already done).

The `ticket.md` format from `generate-tickets`:

```markdown
# Tickets — <backlog_name>

## 01 — Login Form

**What to build:** Users can log in with email and password

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Valid credentials log the user in
- [ ] Invalid credentials show an error

---

## 02 — Password Reset

**What to build:** Users can reset their password via email

**Blocked by:** 01-Login Form

**Status:** ready-for-agent

- [ ] User requests password reset
- [ ] Reset link is emailed
```

### Non-Native Inputs (Normalization Path)

For inputs that are **not** a `generate-tickets` `ticket.md`, the coordinator uses a normalization pipeline:

- **Free-form text** — the coordinator derives a single work unit with acceptance criteria.
- **Checklist** — each checked `[x]` item becomes a work unit; unchecked items are skipped.
- **Structured plan** — parsed into phases and work units.
- **Barrel plan** (generate-plan output) — treated as a barrel plan, normalized into phases and work units.
- **Task list** — each task becomes a work unit.
- **No input** — the coordinator derives work units from the conversation context.

### generate-plan Input

If the user provides `generate-plan` output (barrel plan.md + phase files), it is treated as a **barrel plan** and normalized. This is not the native path — the native path is `generate-tickets` only.

---

## Phase Determination

Phases are derived from the dependency graph of work units:

1. Work units with no blockers form **Phase 1**.
2. Work units whose blockers are all in Phase 1 form **Phase 2**.
3. And so on — topological sort by dependency depth.

Phases execute **sequentially** (Phase 1 → Phase 2 → ...). Within a phase, work units are dispatched **one at a time** in dependency order (blockers first).

---

## Agent Team

Six agents, each with explicit required inputs. If the coordinator delegates without all required inputs, the agent **rejects** immediately.

| Agent | Role | Prefix |
|---|---|---|
| `dispatch-code-worker` | Implements non-UI work (backend, infrastructure, services, libraries, automation) | dispatch- |
| `dispatch-code-with-ui-worker` | Implements UI-related work (web, mobile, desktop, TUI, embedded) | dispatch- |
| `dispatch-acs-reviewer` | Validates implementation correctness against Acceptance Criteria | dispatch- |
| `dispatch-security-reviewer` | Comprehensive security review across 22 security domains | dispatch- |
| `dispatch-quality-gate-reviewer` | Validates quality by running linting, type checking, tests, coverage | dispatch- |
| `dispatch-worker-advisor` | Provides technical guidance when workers are blocked | dispatch- |

### Required Inputs Per Agent

**Workers** (`dispatch-code-worker`, `dispatch-code-with-ui-worker`):

| Input | Description |
|---|---|
| `work_unit_id` | The work unit identifier (e.g. "01 — Login Form") |
| `worktree_path` | Absolute path to the git worktree for this work unit |
| `backlog_name` | The sprint identifier |
| `acceptance_criteria` | List of acceptance criteria to implement |
| `what_it_delivers` | End-to-end behaviour this work unit makes work |
| `work_unit_type` | `functional` or `scaffolding` |
| `background_detail` | What the user wants (background context) |
| `previous_progress_context` | What has been done so far (prior work unit results) |

`dispatch-code-with-ui-worker` additionally requires:
| `design_path` | Path to design docs (if available) |

**Reviewers** (`dispatch-acs-reviewer`, `dispatch-security-reviewer`, `dispatch-quality-gate-reviewer`):

| Input | Description |
|---|---|
| `work_unit_id` | The work unit identifier |
| `worktree_path` | Absolute path to the git worktree |
| `backlog_name` | The sprint identifier |
| `implementation_report_path` | Path to the worker's report file |
| `acceptance_criteria` | List of acceptance criteria to verify against |
| `work_unit_type` | `functional` or `scaffolding` (affects review rules) |
| `previous_review_cycles` | Prior review findings for this work unit |

**Advisor** (`dispatch-worker-advisor`):

| Input | Description |
|---|---|
| `work_unit_id` | The work unit identifier |
| `worktree_path` | Absolute path to the git worktree |
| `backlog_name` | The sprint identifier |
| `blocker_description` | What the worker is blocked on |
| `implementation_report_path` | Path to the worker's report (if any) |
| `previous_advisor_rounds` | Prior advisor findings for this work unit |

### Rejection Format

When an agent detects missing required inputs, it outputs:

```
REJECTED: missing required inputs: <input1>, <input2>, ...
```

The coordinator must fix the delegation and re-invoke the agent.

---

## Workflow

### Execution Model

**Fully sequential.** At any point in time, exactly one work unit is being processed. The lifecycle for each work unit is:

```mermaid
flowchart TD
    A[Create git worktree<br/>branch: dispatch-WU-NN] --> B[Write work-unit spec<br/>to dispatch/work-unit-spec-NN.md]
    B --> C[Route to worker<br/>UI keywords → with-ui-worker<br/>else → code-worker]
    C --> D[Worker implements<br/>TDD if requested<br/>scaffolding exemption if applicable]
    D --> E[ACS Review]
    E --> F{ACS Pass?}
    F -->|No| F1[Worker fixes<br/>restart from ACS]
    F1 --> E
    F -->|Yes| G[Security Review]
    G --> H{Security Pass?}
    H -->|No| H1[Worker fixes<br/>restart from ACS]
    H1 --> E
    H -->|Yes| I[Quality Gate Review]
    I --> J{Quality Pass?}
    J -->|No| J1[Worker fixes<br/>restart from ACS]
    J1 --> E
    J -->|Yes| K[Merge worktree<br/>to main --no-ff]
    K --> L[Tick [x] in ticket.md<br/>update Status to done]
    L --> M[Cleanup worktree]
    M --> N[Log to progress.md]
```

**Review cycle rules:**
- **Max 3 cycles** per review gate. If a gate fails 3 times, escalate to user.
- **Restart-from-ACS**: After any review failure and fix, restart from the ACS review.
- **Last Loop Rule**: If a review returns APPROVED with only Minor/Trivial findings, delegate fixes to the worker without another reviewer cycle.

### Step-by-Step Workflow

#### Step 1: Startup & Mode Detection

1. Determine `backlog_name` from input.
2. Determine input path(s) and type.
3. Check if input is a `generate-tickets` `ticket.md` → Direct Parse path.
4. Otherwise → Normalization path.
5. Write initial `progress.md` event log.

#### Step 2: Git Initialization

1. If no git repo exists: `git init` + empty commit.
2. Create `_xzy-ai/sprints/<backlog>/dispatch/` directory.

#### Step 3: Input Processing

**Direct Parse path (ticket.md):**
1. Parse tickets from `ticket.md`.
2. Build dependency graph from `Blocked by` references.
3. Skip tickets with `[x]` checked (already done).
4. Derive phases from dependency depth.

**Normalization path:**
1. Detect input structure (checklist, free-form, barrel plan, etc.).
2. Normalize into work units with acceptance criteria.
3. Derive phases from work unit dependencies.

#### Step 4: Phase Execution Loop

For each phase (in order):

```
For each work_unit in phase (in dependency order):
    1. Create worktree
    2. Write spec file
    3. Delegate to worker
    4. Run review gates (ACS → Security → Quality)
    5. Merge to main
    6. Tick ticket.md + update status
    7. Cleanup worktree
    8. Log event to progress.md
```

#### Step 5: Worker Delegation

1. Determine worker type:
   - If work unit contains UI keywords (web, mobile, UI, component, view, page, form, dashboard, interface) → `dispatch-code-with-ui-worker`
   - Otherwise → `dispatch-code-worker`
2. Write work-unit spec file to `dispatch/work-unit-spec-<NN>.md`.
3. Invoke the worker with all required inputs.
4. If the worker returns `REJECTED` (missing inputs), fix and re-invoke.

#### Step 6: Review Gate Sequence

For each work unit, after the worker completes:

1. **ACS Review** — `dispatch-acs-reviewer` validates implementation against acceptance criteria.
   - Scaffolding exemption: no missing-test findings on scaffolding work units.
2. **Security Review** — `dispatch-security-reviewer` evaluates 22 security domains.
   - Scaffolding exemption does NOT apply to security review.
3. **Quality Gate** — `dispatch-quality-gate-reviewer` runs linting, type checking, tests, coverage.
   - Scaffolding exemption: coverage not enforced on scaffolding work units, but all other gates still apply.

**Review cycle rules:**

- **Max 3 cycles** per review gate. If a gate fails 3 times, escalate to user.
- **Restart-from-ACS**: After any review failure and fix, restart from the ACS review (not from the review that rejected). This ensures the full implementation still satisfies every AC after changes.
- **Last Loop Rule**: If a review returns APPROVED with only Minor/Trivial findings, delegate those fixes to the worker without another reviewer cycle. The worker writes a follow-up report confirming fixes were applied. The coordinator reads it before proceeding.

#### Step 7: Merge

1. `git checkout main`
2. `git merge --no-ff <worktree-branch>`
3. If merge conflict → escalate to user.

#### Step 8: Tick & Update

1. In `ticket.md` (or normalized plan), tick `[x]` on all acceptance criteria for this work unit.
2. Update ticket `Status` to `done`.
3. Log completion event to `progress.md`.

#### Step 9: Worktree Cleanup

1. `git worktree remove <worktree-path> --force`
2. `git worktree prune`
3. `git branch -D <worktree-branch>`

#### Step 10: Worker Blocking & Advisor

If a worker returns BLOCKED:

1. Log the blocker to `progress.md`.
2. Invoke `dispatch-worker-advisor` with the blocker description and previous context.
3. The advisor returns guidance (not implementation).
4. The coordinator presents the advisor's guidance to the worker.
5. The worker retries with the guidance.
6. If still blocked after 3 advisor rounds, escalate to user.

#### Step 11: Completion

When all work units across all phases are complete:

1. Log final event to `progress.md`.
2. Print summary: work units completed, reviews passed, issues resolved.
3. Done.

---

## State Management

### progress.md

A **pure markdown** event log at `_xzy-ai/sprints/<backlog>/dispatch/progress.md`.

Format:

```markdown
# Dispatch Progress Log — <backlog_name>

## Events

- [2026-07-26T10:00:00Z] STARTED — Phase 1, Work Unit 01 — Login Form
- [2026-07-26T10:15:00Z] WORKER_DONE — dispatch-code-worker completed
- [2026-07-26T10:20:00Z] ACS_REVIEW_PASS — All acceptance criteria verified
- [2026-07-26T10:25:00Z] SECURITY_REVIEW_PASS — No findings
- [2026-07-26T10:30:00Z] QUALITY_GATE_PASS — All checks passed
- [2026-07-26T10:35:00Z] MERGED — Worktree merged to main
- [2026-07-26T10:36:00Z] COMPLETED — Work Unit 01

## Issues

- [2026-07-26T10:40:00Z] BLOCKED — Worker stuck on JWT library version
  - [2026-07-26T10:45:00Z] RESOLVED — Advisor recommended upgrading to v9
```

### ticket.md Updates

The coordinator updates `ticket.md` (or the normalized plan file) as work progresses:

- `Status: ready-for-agent` → `Status: in-progress` when dispatched
- `Status: in-progress` → `Status: done` after merge to main
- Acceptance criteria checkboxes ticked `[x]` after merge

### Worktree Naming

```
Branch: dispatch-<backlog>-WU-<NN>
Path: .worktrees/dispatch-<backlog>-WU-<NN>
```

---

## Crash Recovery

On startup, the coordinator:

1. Scans for stale worktrees (`.worktrees/dispatch-*`).
2. Reads `progress.md` to determine the last completed event.
3. Presents the user with three options:
   - **Resume** — continue from the last completed work unit.
   - **Abort** — stop execution, leave worktrees intact for manual cleanup.
   - **Restart** — delete all worktrees and start over.

---

## Scaffolding Exemption

- **Scaffolding work units**: Pure scaffolding (setting up project structure, build tooling, CI pipeline) — no TDD, no tests.
- **Functional work units**: Full requirements — TDD in TDD mode, tests required, red-green-refactor.
- **Misclassification**: If a work unit is marked scaffolding but actually requires functional implementation, this is a **Blocker**.

Scaffolding exemption applies to:
- `dispatch-code-worker` / `dispatch-code-with-ui-worker`: skip TDD/tests
- `dispatch-acs-reviewer`: suppress missing-test findings
- `dispatch-quality-gate-reviewer`: suppress coverage enforcement

Scaffolding exemption does **NOT** apply to:
- `dispatch-security-reviewer`: all work units get full security review

---

## Constraints

| # | Constraint |
|---|---|
| 1 | Fully sequential — one work unit at a time, globally. No concurrent workers. |
| 2 | Each agent defines explicit required inputs. Missing inputs → REJECTED. |
| 3 | 3 review gates per work unit: ACS → Security → Quality. Max 3 cycles each. |
| 4 | After any review failure + fix, restart from ACS review. |
| 5 | Last Loop Rule: Minor/Trivial findings on APPROVED reviews → delegate to worker. |
| 6 | Merge with `--no-ff` after all reviews pass. |
| 7 | Tick `[x]` in ticket.md only after merge to main. |
| 8 | Artifacts stored under `_xzy-ai/sprints/<backlog>/dispatch/`. |
| 9 | Worktrees at `.worktrees/dispatch-<backlog>-WU-<NN>`. |
| 10 | progress.md is a pure markdown event log. |
| 11 | Native input: generate-tickets ticket.md (direct parse). |
| 12 | generate-plan input: treated as barrel plan (normalization path). |
| 13 | Scaffolding exemption does not apply to security review. |
| 14 | Git auto-init if no repo exists. |
| 15 | Wiki discovery: pass `wikis_path` if `<cwd>/wikis` exists. |

---

## Agent Reference

### dispatch-code-worker

Implements non-UI work (backend, infrastructure, services, libraries, automation). Supports Default and TDD modes. Reads the work-unit spec file from disk. Writes an implementation report.

**Required Inputs:** `work_unit_id`, `worktree_path`, `backlog_name`, `acceptance_criteria`, `what_it_delivers`, `work_unit_type`, `background_detail`, `previous_progress_context`

**Output:** Report file at `dispatch/worker/report-<NN>.md` + stdout summary.

### dispatch-code-with-ui-worker

Implements UI-related work (web, mobile, desktop, TUI, embedded). Same process as code-worker plus design alignment and accessibility compliance (WCAG).

**Required Inputs:** All of `dispatch-code-worker` + `design_path` (optional but recommended)

**Output:** Report file at `dispatch/with-ui-worker/report-<NN>.md` + stdout summary.

### dispatch-acs-reviewer

Validates implementation correctness against Acceptance Criteria. Independently verifies by investigating actual source code, not trusting reports alone.

**Required Inputs:** `work_unit_id`, `worktree_path`, `backlog_name`, `implementation_report_path`, `acceptance_criteria`, `work_unit_type`, `previous_review_cycles`

**Output:** Report file at `dispatch/reviews/dispatch-acs-reviewer/report-<NN>.md` + stdout summary.

### dispatch-security-reviewer

Comprehensive security review across 22 security domains (OWASP Top 10, API Security, ASVS, WSTG, etc.).

**Required Inputs:** Same as ACS reviewer.

**Output:** Report file at `dispatch/reviews/dispatch-security-reviewer/report-<NN>.md` + stdout summary.

### dispatch-quality-gate-reviewer

Validates implementation quality by running linting, type checking, compilation, formatting, tests, coverage, static analysis.

**Required Inputs:** Same as ACS reviewer.

**Output:** Report file at `dispatch/reviews/dispatch-quality-gate-reviewer/report-<NN>.md` + stdout summary.

### dispatch-worker-advisor

Provides technical guidance when workers are blocked. Never performs implementation.

**Required Inputs:** `work_unit_id`, `worktree_path`, `backlog_name`, `blocker_description`, `implementation_report_path`, `previous_advisor_rounds`

**Output:** Report file at `dispatch/advisor/report-<topic>-<NN>.md` + stdout summary.

---

## Report Files as Canonical Artifacts

Each completed agent produces a **report file** that is the canonical record of its output. Reports are stored under `_xzy-ai/sprints/<backlog>/dispatch/`.

| Agent | Report Path |
|---|---|
| code-worker | `dispatch/worker/report-<NN>.md` |
| code-with-ui-worker | `dispatch/with-ui-worker/report-<NN>.md` |
| acs-reviewer | `dispatch/reviews/dispatch-acs-reviewer/report-<NN>.md` |
| security-reviewer | `dispatch/reviews/dispatch-security-reviewer/report-<NN>.md` |
| quality-gate-reviewer | `dispatch/reviews/dispatch-quality-gate-reviewer/report-<NN>.md` |
| worker-advisor | `dispatch/advisor/report-<topic>-<NN>.md` |

Report numbering is **per-role** (worker report-001, acs-reviewer report-001, etc.). On fix cycles, the report number increments.

---

## References

- [Progress Log Format](references/PROGRESS-LOG.md) — Event log format and issue tracking
- [Report Templates](references/report-templates/) — Templates for each agent's report
- [Work Unit Spec Format](references/WORK-UNIT-SPEC.md) — Format of the spec file written before worker delegation
- [Scaffolding Exemption](references/SCAFFOLDING-EXEMPTION.md) — Detailed rules and examples
