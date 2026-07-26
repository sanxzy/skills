# Report Template: dispatch-quality-gate-reviewer

**Agent:** dispatch-quality-gate-reviewer
**Work Unit:** `<work_unit_id>`
**Report Number:** `<NN>` (numeric part of work unit ID, increments on fix cycles)
**Phase:** `<phase_name>`
**Backlog:** `<backlog_name>`
**Review Cycle:** `<cycle_number>`
**Status:** APPROVED | APPROVED_WITH_RECOMMENDATIONS | NEEDS_FIX | BLOCKED
**Timestamp:** `<ISO8601>`

## Verdict

<One-line verdict: APPROVED / APPROVED_WITH_RECOMMENDATIONS / NEEDS_FIX / BLOCKED>

## Ecosystem Detection

| Category | Detected | Details |
|----------|----------|---------|
| Language | <...> | <version> |
| Package Manager | <npm | yarn | pnpm | pip | cargo | ...> | <version> |
| Build System | <tsc | webpack | vite | cargo | go build | ...> | <version> |
| Test Framework | <jest | pytest | rspec | cargo test | ...> | <version> |
| Linter | <eslint | pylint | rubocop | clippy | ...> | <version> |
| Formatter | <prettier | black | gofmt | ...> | <version> |

## Quality Checks

| Check | Status | Tool | Output |
|-------|--------|------|--------|
| Linting | PASS / FAIL | <tool> | <N errors, N warnings> |
| Type Check | PASS / FAIL | <tool> | <N errors> |
| Build | PASS / FAIL | <tool> | <output summary> |
| Formatting | PASS / FAIL | <tool> | <N files non-compliant> |
| Tests | PASS / FAIL | <tool> | <N passed, N failed, N skipped> |
| Coverage | PASS / FAIL / SKIPPED | <tool> | <N% lines, N% branches, N% functions> |
| Static Analysis | PASS / FAIL | <tool> | <N findings> |

<For scaffolding work units: Coverage is SKIPPED.>

## Coverage Analysis

<For functional work units with coverage check:>
- Threshold: <N>% (from `.plans/coverage.md` or default 80%)
- Actual: <N>%
- Verdict: PASS / FAIL

<For scaffolding work units: "Coverage check skipped — scaffolding work unit.">

## Findings

### Blocker Findings

| # | Check | Finding | Detail |
|---|-------|---------|--------|
| B-1 | Tests / Build | <description> | <output> |

### Critical Findings

| # | Check | Finding | Detail |
|---|-------|---------|--------|
| C-1 | Linting / Type / Format | <description> | <output> |

### Major Findings

| # | Check | Finding | Detail |
|---|-------|---------|--------|
| M-1 | Coverage / Static | <description> | <output> |

### Minor Findings

| # | Check | Finding | Detail |
|---|-------|---------|--------|
| m-1 | Linting / Format | <description> | <output> |

### Trivial Findings

| # | Check | Finding | Detail |
|---|-------|---------|--------|
| t-1 | <check> | <description> | <output> |

## All Validation Commands

```bash
<exact commands run, one per line, with actual output>
```

## Fix Instructions

<If NEEDS_FIX or BLOCKED: detailed instructions for what the worker needs to fix, including exact commands to run.>

<If APPROVED: "All quality checks pass.">

---

<!-- CANONICAL ARTIFACT -->

# Quality Gate Review Report — <work_unit_id>

<Complete output repeated in full. See template sections above.>
