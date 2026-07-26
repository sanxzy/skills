---
name: generate-engineering-specs
version: 0.1.0
description: Turn the current conversation into a comprehensive engineering specification using a multi-agent workflow with strict quality gates. No interview — just synthesize what you already know.
---

# Generate Engineering Specs Skill

This skill transforms the current conversation context into a complete engineering specification through a strict four-agent pipeline: Discovery → Requirements → Architecture → (user approval) → Specification Assembler. Each agent's output is validated against a formal contract schema and per-agent quality gates before the next agent runs. No user interview — synthesize what you already know from the conversation.

## Modules

- [references/CONTRACT-FORMAT.md](./references/CONTRACT-FORMAT.md) — Standard agent output contract YAML schema, per-agent deliverable schemas, and validation rules.
- [VALIDATION-CRITERIA.md](./references/VALIDATION-CRITERIA.md) — Three-tier validation framework, per-agent quality gates, confidence thresholds, retry policy, and coordinator decision matrix.
- [references/WORKFLOW-PROCESS.md](./references/WORKFLOW-PROCESS.md) — Coordinator state machine, `execution.yaml` schema, input hash algorithm, resume algorithm, dispatch flow, user approval gate, backlog name generation, and error recovery.

## Available Agents

- **spec-discovery** — Combines workspace discovery and reference research. Explores the codebase, determines greenfield/brownfield, extracts domain glossary, analyzes architecture, discovers testing patterns, reads ADRs, and researches best practices. Produces `workspace-summary.md` and `reference-summary.md`.
- **spec-requirements** — Combines requirements analysis and scope review. Produces Problem Statement, Solution, comprehensive User Stories, edge cases, Out of Scope, assumptions, and further notes. Produces `requirements.md`.
- **spec-architecture** — Combines implementation architecture, testing architecture, and gap-analysis/review. Designs architecture decisions, API contracts, schema changes, module boundaries, testing seams, and testing strategy. Cross-references all requirements for gaps and inconsistencies. Produces `implementation-decisions.md`, `testing-decisions.md`, and proposes `testing_seams` for user approval.
- **spec-assembler** — Loads all upstream artifacts, validates completeness, removes duplication, normalizes terminology, resolves cross-references, and assembles the final `spec.md` with an accompanying `assembler-report.md`.

## Coordinator Instructions

You are the coordinator. Your job is to orchestrate the four agents above in strict sequence, validate every output against references/CONTRACT-FORMAT.md and VALIDATION-CRITERIA.md, enforce the user approval gate, persist state and artifacts, handle errors and retries, and deliver the final specification.

Follow these instructions precisely. Do not skip phases, modify agent outputs (except formatting for persistence), infer missing deliverables, or proceed past a failed quality gate.

### 1. Initialization

When the skill is triggered:

1. **Read the conversation context** — understand the feature request, user's description, and any prior discussion. Do not interview the user for additional information; synthesize what already exists.

2. **Generate backlog name** — derive a kebab-case slug from the conversation topic using the algorithm in references/WORKFLOW-PROCESS.md §7. Prepend `spec-` prefix, truncate to 50 chars, handle collisions with numeric suffixes.

3. **Create sprints directory structure**:
   ```
   _xzy-ai/sprints/<backlog_name>/
     specs/
       execution.yaml
   ```

4. **Initialize `execution.yaml`** — write a fresh execution state following the schema in references/WORKFLOW-PROCESS.md §2:
   ```yaml
   execution:
     backlog_name: <generated-slug>
     status: pending
     current_phase: null
     created_at: <now>
     updated_at: <now>
     phases:
       discovery:
         status: pending
       requirements:
         status: pending
       architecture:
         status: pending
       assembler:
         status: pending
     retry_count:
       discovery: 0
       requirements: 0
       architecture: 0
       assembler: 0
   ```

5. **Check for existing sprint directory** — if `_xzy-ai/sprints/<backlog_name>/` already exists with a valid `execution.yaml`, skip initialization and run the resume algorithm (see §6). If `execution.yaml` is corrupted or missing, apply error recovery per references/WORKFLOW-PROCESS.md §8.

6. **Begin the dispatch loop** — start with the Discovery phase.

### 2. Sequential Dispatch (Per Phase)

For each phase in order (Discovery → Requirements → Architecture → Assembler), execute the following dispatch procedure. Do not parallelize — each agent runs sequentially.

#### Step A: Enter Phase

1. Update `execution.yaml`:
   ```yaml
   status: in_progress
   current_phase: <phase-name>
   phases.<phase-name>.status: in_progress
   ```
2. Persist `execution.yaml` atomically (write to `.tmp` then rename).

#### Step B: Prepare Context

1. Compute `input_hash` for this phase using the algorithm in references/WORKFLOW-PROCESS.md §3:
   - Discovery: hash conversation context only
   - Requirements: hash conversation context + workspace-summary.md + reference-summary.md
   - Architecture: hash conversation context + workspace-summary.md + reference-summary.md + requirements.md
   - Assembler: hash conversation context + all upstream artifact files

2. Collect upstream artifact paths per phase:
   - Discovery: no upstream artifacts
   - Requirements: `workspace-summary.md`, `reference-summary.md`
   - Architecture: `workspace-summary.md`, `reference-summary.md`, `requirements.md`
   - Assembler: `workspace-summary.md`, `reference-summary.md`, `requirements.md`, `implementation-decisions.md`, `testing-decisions.md`

3. **Verify all required upstream artifacts exist** on disk. If any are missing, abort with a clear message about which artifact is missing and instruct the user to re-run from the phase that should have produced it.

#### Step C: Dispatch Agent

1. Update `execution.yaml`:
   ```yaml
   status: waiting_for_agent
   ```
2. Persist `execution.yaml`.
3. Call the task tool with the following inputs:
   - Agent instructions from `_agents/<agent-name>.md`
   - `conversation_context`: the full conversation
   - `backlog_name`: the generated slug
   - `upstream_artifacts`: map of artifact keys to file paths
   - `contract_format_ref`: reference to references/CONTRACT-FORMAT.md
   - `validation_criteria_ref`: reference to VALIDATION-CRITERIA.md (architecture phase only)

#### Step D: Receive and Parse

1. Update `execution.yaml`:
   ```yaml
   status: in_progress
   ```
2. Parse the agent's response as YAML. If the response is not parseable as YAML, apply non-recoverable error handling per references/WORKFLOW-PROCESS.md §8.

#### Step E: Contract Validation

Validate the agent's output against references/CONTRACT-FORMAT.md contract validation rules. Perform these checks in order:

1. **Structure Validation** (references/CONTRACT-FORMAT.md §Contract Validation Rules §1):
   - YAML parseable
   - Top-level keys include: `status`, `confidence`, `deliverables`, `missing_information`, `assumptions`, `questions_for_user`, `blocking_issues`, `recommendations`
   - No extra top-level keys

2. **Status Validation** (§2):
   - `status` is one of `success`, `partial`, `failed`
   - If `partial` or `failed`, `missing_information` or `blocking_issues` is non-empty

3. **Confidence Validation** (§3):
   - `confidence` is integer 0–100
   - If `status` is `success`, confidence >= 70 (warning only)

4. **Deliverables Validation** (§4):
   - `deliverables` not null/empty when status is `success`
   - All required deliverable keys for this agent present (see per-agent schemas in references/CONTRACT-FORMAT.md)
   - File-path deliverables are non-empty strings

5. **Array Validation** (§5):
   - `missing_information`, `assumptions`, `questions_for_user`, `blocking_issues`, `recommendations` are arrays
   - Each element is a non-empty string

If contract validation fails with fatal errors (invalid YAML, invalid status, failed without blockers), abort the workflow immediately. If retryable errors (missing deliverable, partial with info), proceed to retry logic (Step G).

#### Step F: Quality Gate Enforcement

After contract validation passes, apply the per-agent content quality gates from VALIDATION-CRITERIA.md:

1. **Tier 2: Content Quality** — check that referenced files exist with substantive content, specificity, actionability, and no placeholder text ("TODO", "TBD", etc.).

2. **Tier 3: Consistency** — check terminology match with upstream artifacts, no contradictions, dependency traceability, assumption alignment.

3. **Per-Agent Gates** (VALIDATION-CRITERIA.md §Per-Agent Validation Gates):

   **Discovery Agent:**
   - Must explicitly state greenfield or brownfield
   - Must list domain glossary terms (empty allowed for greenfield with no context)
   - If brownfield: must include architecture summary. If greenfield: must note no existing architecture
   - Must document testing patterns (or note absence)
   - Must list ADRs/references found (or note absence)

   **Requirements Agent:**
   - Problem statement present, >1 sentence, clearly defines the problem
   - Solution present and directly addresses the problem
   - User stories non-empty array, each follows "As a <actor>, I want <feature>, so that <benefit>" template
   - Out of scope present (may be empty)
   - No unresolved ambiguities; edge cases addressed

   **Architecture Agent:**
   - Implementation decisions documented with rationale, alternatives, and final choice
   - At least one testing seam proposed with name, type, and rationale
   - Seam references existing patterns when available
   - APIs/interfaces defined (or explicitly deferred)
   - Schema changes documented (or explicitly noted as none)

   **Specification Assembler:**
   - All spec sections present (Problem, Solution, User Stories, Implementation Decisions, Testing Decisions, Out of Scope, Further Notes)
   - No duplicate content across sections
   - Consistent terminology throughout
   - Valid cross-references
   - If `consistency_issues` non-empty, each issue addressed in the spec

For each gate: if pass condition is met, proceed. If fail condition, proceed to retry logic (Step G). If warning only, proceed with annotation in `execution.yaml`.

#### Step G: Decision — Proceed / Retry / Escalate

Apply the coordinator decision matrix from VALIDATION-CRITERIA.md §Coordinator Decision Matrix:

| Status | Confidence | Validation | Action |
|--------|------------|------------|--------|
| `success` | >= 80 | All gates pass | **PROCEED** — persist, advance |
| `success` | 70–79 | All gates pass | **PROCEED_WITH_NOTE** — persist with warning |
| `success` | >= 70 | Gate failure | **RETRY** with gate feedback |
| `success` | < 70 | All gates pass | **RETRY** with enhanced context |
| `partial` | any | Tier 1 pass | **RETRY** with missing info |
| `failed` | any | any | **RETRY** (if < 3) or **ESCALATE** (if >= 3) |
| any | any | Fatal | **ESCALATE** — abort immediately |

**PROCEED / PROCEED_WITH_NOTE:**
1. Write the validated agent contract YAML to `_xzy-ai/sprints/<backlog_name>/specs/<phase>-output.yaml`
2. Write referenced artifact files to their specified paths under `specs/`
3. Update `execution.yaml`:
   ```yaml
   status: validated
   phases.<phase-name>.status: completed
   phases.<phase-name>.checkpoint:
     agent: <phase-name>
     version: 0.1.0
     input_hash: <computed-hash>
     output_artifact: specs/<phase>-output.yaml
     validation_result: pass | low_pass
     confidence: <from-agent-output>
     timestamp: <now>
   ```
4. If `current_phase` is architecture: after persisting, proceed to the User Approval Gate (§5) before advancing to Assembler.
5. If `current_phase` is discovery, requirements, or approved architecture: advance to next phase (goto Step A for next agent).
6. If `current_phase` is assembler and validation passes: mark workflow as completed (goto §7 Final Output).

**RETRY:**
1. Increment `retry_count.<phase-name>` in execution metadata.
2. If `retry_count >= 3`: mark phase as failed, set `execution.yaml status: failed`, present failure to user with agent output and validation errors. Offer: retry from this phase or abort.
3. If `retry_count < 3`: re-dispatch the same agent with structured feedback (see Retry Feedback Format in VALIDATION-CRITERIA.md §Retry Feedback Format). Include the previous output, specific validation errors, and enhanced context (e.g., pointing to specific upstream artifacts the agent may have missed).
4. Update `execution.yaml status: in_progress` and persist before re-dispatching.

**ESCALATE:**
1. Set `execution.yaml status: aborted`, `phases.<phase-name>.status: failed`.
2. Persist `execution.yaml`.
3. Present abort reason to user with: failing agent output (if parseable), validation errors, and list of partial artifacts preserved.
4. Stop workflow.

### 3. Contract Validation

Always validate agent output against the full contract schema in references/CONTRACT-FORMAT.md before accepting it. The validation checks are enumerated in the "Contract Validation Rules" section of references/CONTRACT-FORMAT.md. Implement them exactly as specified — do not add or omit checks.

Key validation rules to remember:
- All 8 top-level keys must be present: `status`, `confidence`, `deliverables`, `missing_information`, `assumptions`, `questions_for_user`, `blocking_issues`, `recommendations`
- `status` must be exactly `success`, `partial`, or `failed`
- `confidence` must be integer 0–100, not float, not string
- Required deliverable keys vary by agent (see per-agent schemas)
- Array fields must be arrays (even if empty)
- All array elements must be non-empty strings

After structural validation, validate the referenced artifact files exist on disk and contain substantive content.

### 4. Quality Gate Enforcement

Apply the three-tier validation framework from VALIDATION-CRITERIA.md in order:

1. **Tier 1: Contract Compliance** — is the YAML structurally valid?
2. **Tier 2: Content Quality** — are the artifacts substantive and actionable?
3. **Tier 3: Consistency** — is the output consistent with upstream artifacts?

Then apply the per-agent gates from VALIDATION-CRITERIA.md §Per-Agent Validation Gates.

Never proceed past a gate failure. Never skip a tier. A gate failure always triggers a retry regardless of confidence score.

### 5. User Approval Gate

After the Architecture Agent's output passes validation:

1. Extract `testing_seams` from the agent's deliverables array.
2. Update `execution.yaml`:
   ```yaml
   status: waiting_for_user
   phases.architecture.status: waiting_approval
   ```
3. Present the testing seams to the user with this format:
   ```
   The Architecture Agent has proposed the following testing seams:

   <testing_seams formatted for readability>

   Do you approve these testing seams? Options:
   - **approve** — proceed to Specification Assembler
   - **reject with feedback** — provide reason, Architecture Agent re-runs
   - **request changes** — specify changes, Architecture Agent re-runs
   ```
4. Wait for user response.

**On approval:**
- Set `phases.architecture.user_approval: approved` in `execution.yaml`
- Set `status: validated`
- Advance to Assembler phase

**On rejection or request changes:**
- Collect user feedback text
- Set `phases.architecture.user_approval: rejected`
- Set `phases.architecture.user_feedback: <feedback>`
- Re-dispatch Architecture Agent with original input + user feedback appended as additional guidance
- On re-dispatch: reset validation to start of dispatch flow (validate output again from scratch)
- Do not advance to Assembler until approval is granted

### 6. Resume Support

When entering an existing sprint directory, follow the resume algorithm from references/WORKFLOW-PROCESS.md §4:

1. Parse `execution.yaml` from `_xzy-ai/sprints/<backlog_name>/specs/execution.yaml`.
2. If `execution.yaml` is corrupted or missing → apply error recovery per references/WORKFLOW-PROCESS.md §8 (re-derive state from existing artifacts or start fresh).
3. Run `determine_resume_point()`:
   - For each phase (discovery → requirements → architecture → assembler):
     - If `completed` and input hash matches and artifact exists → skip (immutable unless inputs changed)
     - If `completed` and hash mismatches → mark pending, resume from here
     - If `completed` and artifact missing → mark pending, resume from here
     - If `waiting_approval` (architecture) → present approval gate
     - If `pending` → execute this phase
     - If `failed` → retry (increment retry counter)
     - If `in_progress` → restart (assume crash)
4. If all complete → verify `spec.md` exists and is non-empty. If yes, present final output. If not, restart Assembler.
5. Begin dispatch flow from the resume point.

**Key resume rules:**
- Previously completed artifacts are immutable unless invalidated (hash mismatch, missing file, or dependency changed).
- Only recompute artifacts whose dependencies changed.
- Downstream phases whose inputs changed are always recomputed, even if their checkpoint shows `completed`.
- Input hash is computed per the algorithm in references/WORKFLOW-PROCESS.md §3 (SHA256 of concatenated inputs, first 16 hex chars).

### 7. Error Handling

| Scenario | Action |
|----------|--------|
| Agent returns unparseable output | Abort workflow (non-recoverable). Preserve raw output to `<phase>-raw-output.txt`. |
| Agent timeout (120s default) | Retry once automatically. If times out again, abort workflow. |
| Missing upstream artifact | Abort with clear message about which artifact is missing and which phase should produce it. |
| Corrupted `execution.yaml` | Attempt to re-derive state from existing artifact files on disk. If none exist, start fresh. |
| `_xzy-ai/sprints/` missing | Create directory and start fresh. |
| File system errors (permission, disk full) | Notify user and abort. |
| 4th consecutive failure on same agent | Abort workflow. Preserve partial artifacts. Report to user. |
| `questions_for_user` non-empty in agent output | Pause execution, present questions to user one at a time, wait for answers, then retry the agent with answers appended. |
| Critical confidence (< 50) | Escalate to user — do not retry automatically. |

**Atomic persistence rule:** Write new files to a `.tmp` path first, then use rename to the final path. Only update `execution.yaml` after all artifact files for the phase are written. If a write fails mid-phase, the previous checkpoint remains intact.

### 8. Final Output

After the Specification Assembler passes validation:

1. Verify `spec.md` exists at `_xzy-ai/sprints/<backlog_name>/spec.md` and is non-empty.
2. Set `execution.yaml status: completed`, `updated_at: <now>`.
3. Persist final `execution.yaml`.
4. Present the final output to the user:
   ```
   Engineering specification generated successfully.

   Final spec: _xzy-ai/sprints/<backlog_name>/spec.md
   Artifacts:  _xzy-ai/sprints/<backlog_name>/specs/

   Summary:
   - Discovery: <pass/low_pass>, confidence <n>
   - Requirements: <pass/low_pass>, confidence <n>
   - Architecture: <pass/low_pass>, confidence <n>
   - Assembler: <pass/low_pass>, confidence <n>
   - Consistency issues found: <count>
   ```

### Important Rules (Do Not Violate)

- **Never skip phases** — always run all four agents in order.
- **Never modify agent output** — except formatting for persistence (e.g., wrapping YAML in code blocks). Content, structure, and decisions must be preserved exactly.
- **Never infer missing deliverables** — if an agent did not produce a required deliverable, reject and retry. Do not fill in gaps yourself.
- **Always validate against contract before proceeding** — even if the output looks correct, run all validation checks.
- **Always persist validated artifacts** — write contract YAML and referenced files to the specs directory.
- **Always update `execution.yaml` after each checkpoint** — status, phase completion, checkpoint metadata. If execution.yaml is out of date, resume will not work correctly.
- **Use the task tool to dispatch all 4 agents** — each agent runs as a separate task invocation.
- **No interview** — this skill synthesizes from the existing conversation. Do not ask the user questions unless the agent output contains `questions_for_user` or the user approval gate requires it.
