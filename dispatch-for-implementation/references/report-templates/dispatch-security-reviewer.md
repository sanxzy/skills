# Report Template: dispatch-security-reviewer

**Agent:** dispatch-security-reviewer
**Work Unit:** `<work_unit_id>`
**Report Number:** `<NN>` (numeric part of work unit ID, increments on fix cycles)
**Phase:** `<phase_name>`
**Backlog:** `<backlog_name>`
**Review Cycle:** `<cycle_number>`
**Status:** APPROVED | APPROVED_WITH_RECOMMENDATIONS | NEEDS_FIX | BLOCKED
**Timestamp:** `<ISO8601>`

## Verdict

<One-line verdict: APPROVED / APPROVED_WITH_RECOMMENDATIONS / NEEDS_FIX / BLOCKED>

## Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| Language | <...> | <...> |
| Framework | <...> | <...> |
| Database | <...> | <...> |
| Key Dependencies | <...> | <...> |

## Domains Evaluated

| Domain | Status | Reference |
|--------|--------|-----------|
| Authentication & Authorization | PASS / N/A / <finding> | OWASP A01, A07 |
| Input Validation & Injection | PASS / N/A / <finding> | OWASP A03 |
| Cryptographic Failures | PASS / N/A / <finding> | OWASP A02 |
| Insecure Design | PASS / N/A / <finding> | OWASP A04 |
| Security Misconfiguration | PASS / N/A / <finding> | OWASP A05 |
| Vulnerable Components | PASS / N/A / <finding> | OWASP A06 |
| Software & Data Integrity | PASS / N/A / <finding> | OWASP A08 |
| Logging & Monitoring | PASS / N/A / <finding> | OWASP A09 |
| API Security | PASS / N/A / <finding> | OWASP API Top 10 |
| Data Protection & Privacy | PASS / N/A / <finding> | GDPR, CCPA |
| Session Management | PASS / N/A / <finding> | OWASP ASVS |
| Error Handling | PASS / N/A / <finding> | OWASP ASVS |
| File Upload | PASS / N/A / <finding> | OWASP ASVS |
| Access Control | PASS / N/A / <finding> | OWASP A01 |
| XSS | PASS / N/A / <finding> | OWASP A03 |
| CSRF | PASS / N/A / <finding> | OWASP A01 |
| SSRF | PASS / N/A / <finding> | OWASP A10 |
| Dependency Management | PASS / N/A / <finding> | OWASP A06 |
| CI/CD Security | PASS / N/A / <finding> | OWASP |
| Infrastructure as Code | PASS / N/A / <finding> | OWASP |
| Container Security | PASS / N/A / <finding> | OWASP |

<Only include domains relevant to this work unit. Mark non-relevant domains as "N/A".>

## Findings

### Critical Findings (CVSS 9.0–10.0)

| # | Finding | File | CVSS | OWASP Reference |
|---|---------|------|------|-----------------|
| C-1 | <description> | `<path:line>` | 9.5 | A03: Injection |

### High Findings (CVSS 7.0–8.9)

| # | Finding | File | CVSS | OWASP Reference |
|---|---------|------|------|-----------------|
| H-1 | <description> | `<path:line>` | 7.5 | A02: Crypto |

### Medium Findings (CVSS 4.0–6.9)

| # | Finding | File | CVSS | OWASP Reference |
|---|---------|------|------|-----------------|
| M-1 | <description> | `<path:line>` | 5.0 | A05: Config |

### Low Findings (CVSS 0.1–3.9)

| # | Finding | File | CVSS | OWASP Reference |
|---|---------|------|------|-----------------|
| L-1 | <description> | `<path:line>` | 2.0 | A09: Logging |

### Informational

| # | Finding | File | Reference |
|---|---------|------|-----------|
| I-1 | <description> | `<path:line>` | OWASP ASVS |

## Standards Coverage

### OWASP Top 10 (2021)

| # | Category | Status |
|---|----------|--------|
| A01 | Broken Access Control | PASS / <finding> / N/A |
| A02 | Cryptographic Failures | PASS / <finding> / N/A |
| A03 | Injection | PASS / <finding> / N/A |
| ... | ... | ... |

### OWASP ASVS

<Relevant ASVS level coverage>

## Risk Assessment

| Risk Level | Count | Priority |
|---|---|---|
| Critical | <count> | Immediate fix required |
| High | <count> | Fix before merge |
| Medium | <count> | Fix in next cycle |
| Low | <count> | Address when possible |
| Informational | <count> | No action required |

## Fix Instructions

<If NEEDS_FIX or BLOCKED: detailed instructions for what the worker needs to fix, with code examples where helpful.>

<If APPROVED: "No security findings requiring action.">

---

<!-- CANONICAL ARTIFACT -->

# Security Review Report — <work_unit_id>

<Complete output repeated in full. See template sections above.>
