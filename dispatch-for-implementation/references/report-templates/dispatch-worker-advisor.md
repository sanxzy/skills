# Report Template: dispatch-worker-advisor

**Agent:** dispatch-worker-advisor
**Work Unit:** `<work_unit_id>`
**Topic:** `<topic_slug>` (kebab-case from blocker description)
**Advisor Round:** `<NN>` (advisor round number, starts at 1)
**Backlog:** `<backlog_name>`
**Status:** DONE | UNRESOLVED
**Timestamp:** `<ISO8601>`

## Blocker Summary

<Restate the blocker from the coordinator's delegation. Describe what the worker is trying to achieve and what's blocking them.>

## Root Cause

<What is causing the blockage? Be specific. Include technical details, version conflicts, architectural contradictions, missing dependencies, etc.>

## Internal Research

### Codebase Analysis

<What was found in the codebase: relevant files, patterns, conventions, existing solutions.>

### Project Documentation

<What was found in project docs, ADRs, architecture documents.>

## External Research

### Documentation

| Source | Finding | Confidence |
|--------|---------|------------|
| Context7 — <library> | <finding> | <0-100> |
| Exa — <topic> | <finding> | <0-100> |

### Code Examples & Known Issues

| Source | Finding | URL |
|--------|---------|-----|
| <GitHub Issues> | <finding> | <url> |
| <Stack Overflow> | <finding> | <url> |

## Recommended Approach

<Specific, actionable guidance for the worker. Include code examples where helpful.>

```
<code example if applicable>
```

### Why This Approach

<Justification for the recommendation. Why is this the best path forward?>

### Confidence

**Confidence:** <integer 0-100>

<50-70: "Moderate confidence — verify against your specific implementation.">
<70-85: "High confidence — this aligns with the codebase conventions and library documentation.">
<85-100: "Very high confidence — this is the documented solution and matches existing patterns.">

## Alternatives Considered

### Alternative 1: <Title>

**Pros:**
- <pro>

**Cons:**
- <con>

### Alternative 2: <Title>

**Pros:**
- <pro>

**Cons:**
- <con>

## References

- [<Title>](<URL>) — <description>
- [<Title>](<URL>) — <description>

## Limitations

<List any caveats, warnings, or limitations of the recommended approach.>

## Previous Advisor Rounds

<Summary of prior advisor guidance, if any. Note whether the worker has already tried these approaches.>

---

<!-- CANONICAL ARTIFACT -->

# Advisor Report — <work_unit_id> — Round <NN>

<Complete output repeated in full. See template sections above.>
