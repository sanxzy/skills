# Report Template: dispatch-acs-reviewer

**Agent:** dispatch-acs-reviewer
**Work Unit:** `<work_unit_id>`
**Report Number:** `<NN>` (numeric part of work unit ID, increments on fix cycles)
**Phase:** `<phase_name>`
**Backlog:** `<backlog_name>`
**Review Cycle:** `<cycle_number>`
**Status:** APPROVED | APPROVED_WITH_RECOMMENDATIONS | NEEDS_FIX | BLOCKED
**Timestamp:** `<ISO8601>`

## Verdict

<One-line verdict: APPROVED / APPROVED_WITH_RECOMMENDATIONS / NEEDS_FIX / BLOCKED>

## Verification Summary

<Summary of how the implementation was verified. Include which files were inspected, which tests were run, and which acceptance criteria were checked.>

## Work Unit Classification

| Field | Value |
|---|---|
| Type | `<functional | scaffolding>` |
| Classification Correct | Yes / No |
| Notes | <if scaffolding misclassified, explain why> |

## Acceptance Criteria Status

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | <criterion text> | [x] PASS / [ ] FAIL | <file:line or test name> |
| 2 | <criterion text> | [x] PASS / [ ] FAIL | <file:line or test name> |
| 3 | <criterion text> | [x] PASS / [ ] FAIL | <file:line or test name> |

## Test Verification

<For functional work units: verify tests exist and pass. List test files, test counts.>

<For scaffolding work units: "Tests skipped — scaffolding work unit.">

## Regression Check

<Check if the implementation introduces regressions in existing functionality. Reference previous review cycle findings if any.>

## Findings

### Blocker Findings

| # | Finding | File | Severity |
|---|---------|------|----------|
| B-1 | <description> | `<path:line>` | Blocker |

### Critical Findings

| # | Finding | File | Severity |
|---|---------|------|----------|
| C-1 | <description> | `<path:line>` | Critical |

### Major Findings

| # | Finding | File | Severity |
|---|---------|------|----------|
| M-1 | <description> | `<path:line>` | Major |

### Minor Findings

| # | Finding | File | Severity |
|---|---------|------|----------|
| m-1 | <description> | `<path:line>` | Minor |

### Trivial Findings

| # | Finding | File | Severity |
|---|---------|------|----------|
| t-1 | <description> | `<path:line>` | Trivial |

## Fix Instructions

<If NEEDS_FIX or BLOCKED: detailed instructions for what the worker needs to fix.>

<If APPROVED: "None — all acceptance criteria met.">

## Last Loop Rule

<If APPROVED with only Minor/Trivial findings: "Last Loop Rule applies — fixes delegated to worker without another review cycle.">

<If no Minor/Trivial findings: "No Last Loop Rule needed.">

---

<!-- CANONICAL ARTIFACT -->

# ACS Review Report — <work_unit_id>

**Agent:** dispatch-acs-reviewer
**Work Unit:** `<work_unit_id>`
**Report Number:** `<NN>`
**Phase:** `<phase_name>`
**Backlog:** `<backlog_name>`
**Review Cycle:** `<cycle_number>`
**Status:** APPROVED | APPROVED_WITH_RECOMMENDATIONS | NEEDS_FIX | BLOCKED
**Timestamp:** `<ISO8601>`

## Verdict

<One-line verdict>

## Verification Summary

<Summary of verification>

## Work Unit Classification

| Field | Value |
|---|---|
| Type | `<functional | scaffolding>` |
| Classification Correct | Yes / No |
| Notes | <if scaffolding misclassified, explain why> |

## Acceptance Criteria Status

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | <criterion text> | [x] PASS / [ ] FAIL | <file:line or test name> |
| 2 | <criterion text> | [x] PASS / [ ] FAIL | <file:line or test name> |
| 3 | <criterion text> | [x] PASS / [ ] FAIL | <file:line or test name> |

## Test Verification

<For functional work units: verify tests exist and pass.>
<For scaffolding work units: "Tests skipped — scaffolding work unit.">

## Regression Check

<Regression check summary>

## Findings

<All findings tables repeated in full>

## Fix Instructions

<Fix instructions>

## Last Loop Rule

<Last Loop Rule status>
