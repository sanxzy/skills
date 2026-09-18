import { createHash } from "node:crypto";
import {
  access,
  mkdir,
  readdir,
  readFile,
  realpath,
  stat,
} from "node:fs/promises";
import { basename, dirname, relative, resolve, join, sep } from "node:path";

import {
  createYamlFile,
  deepEqual,
  readYamlFile,
  updateYamlFile,
  YamlToolError,
} from "./_yaml-io.mjs";

export const UNIT_STATES = Object.freeze([
  "PENDING",
  "READY",
  "ASSIGNED",
  "IMPLEMENTING",
  "AWAITING_REVIEW",
  "REVIEWING",
  "FIXING",
  "INTEGRATING",
  "DONE",
  "BLOCKED",
  "ESCALATED",
]);

export const LEGAL_UNIT_TRANSITIONS = Object.freeze({
  PENDING: ["READY", "BLOCKED"],
  READY: ["ASSIGNED", "BLOCKED"],
  ASSIGNED: ["IMPLEMENTING", "BLOCKED"],
  IMPLEMENTING: ["AWAITING_REVIEW", "BLOCKED", "ESCALATED"],
  AWAITING_REVIEW: ["REVIEWING", "BLOCKED"],
  REVIEWING: ["INTEGRATING", "FIXING", "BLOCKED", "ESCALATED"],
  FIXING: ["AWAITING_REVIEW", "BLOCKED", "ESCALATED"],
  INTEGRATING: ["DONE", "FIXING", "BLOCKED", "ESCALATED"],
  DONE: [],
  BLOCKED: [
    "PENDING",
    "READY",
    "ASSIGNED",
    "IMPLEMENTING",
    "AWAITING_REVIEW",
    "REVIEWING",
    "FIXING",
    "INTEGRATING",
    "ESCALATED",
  ],
  ESCALATED: ["BLOCKED"],
});

export const OPERATION_STATES = Object.freeze([
  "PREPARED",
  "EXECUTING",
  "SUCCEEDED",
  "FAILED",
  "UNKNOWN",
  "RECONCILING",
]);

export const TRANSITION_STATES = Object.freeze([
  "PREPARED",
  "COMMITTING",
  "COMMITTED",
  "ABORTED",
  "UNKNOWN",
]);

const SHA_PATTERN = /^sha256:[0-9a-f]{64}$/i;
const REVISION_PATTERN = /^[0-9a-f]{7,64}$/i;
const SAFE_SEGMENT_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const ATTEMPT_PATTERN = /:attempt-[0-9]{3}$/;
const ROLE_KEYS = Object.freeze({
  "squad-worker": "worker",
  worker: "worker",
  "squad-reviewer": "reviewer",
  reviewer: "reviewer",
  "squad-qa": "qa",
  qa: "qa",
  "squad-analysis-reconciliation": "analysis",
  analysis: "analysis",
});
const ROLE_NAMES = Object.freeze({
  worker: "squad-worker",
  reviewer: "squad-reviewer",
  qa: "squad-qa",
  analysis: "squad-analysis-reconciliation",
});

export class SquadWorkflowError extends YamlToolError {
  constructor(code, message, details = undefined) {
    super(code, message, details);
    this.name = "SquadWorkflowError";
  }
}

function fail(code, message, details = undefined) {
  throw new SquadWorkflowError(code, message, details);
}

function isMapping(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function asString(value) {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function requireString(value, field, issues, { absolute = false } = {}) {
  if (!asString(value)) {
    issues.push(issue(field, "REQUIRED_FIELD", value ?? null, "non-empty string", "A non-empty string is required."));
    return undefined;
  }
  if (absolute && !value.startsWith(sep)) {
    issues.push(issue(field, "ABSOLUTE_PATH_REQUIRED", value, "absolute path", "The path must be absolute."));
    return undefined;
  }
  return value;
}

function issue(field, code, actual, expected, message) {
  return { field, code, actual, expected, message };
}

function check(checks, name, actual, expected) {
  checks.push({ name, actual, expected, result: deepEqual(actual, expected) ? "PASS" : "FAIL" });
}

function normalizeDigest(value, field, issues) {
  if (!SHA_PATTERN.test(value ?? "")) {
    issues.push(issue(field, "INVALID_DIGEST", value ?? null, "sha256:<64 lowercase hexadecimal characters>", "The field must contain a canonical SHA-256 digest."));
    return undefined;
  }
  return value.toLowerCase();
}

function normalizeRevision(value, field, issues) {
  if (!REVISION_PATTERN.test(value ?? "")) {
    issues.push(issue(field, "INVALID_REVISION", value ?? null, "a Git commit revision", "The field must contain a Git commit revision or resolvable abbreviation."));
    return undefined;
  }
  return value;
}

function normalizeRole(value, field = "role", issues = []) {
  const key = ROLE_KEYS[value];
  if (!key) {
    issues.push(issue(field, "INVALID_ROLE", value ?? null, Object.keys(ROLE_KEYS), "The handoff role is not supported."));
    return undefined;
  }
  return key;
}

function padAttempt(number) {
  const parsed = Number(number);
  if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > 999999) {
    fail("INVALID_ATTEMPT", `Attempt must be a positive integer: ${number ?? "<missing>"}`, {
      field: "attempt_number",
      actual: number ?? null,
      expected: "1..999999",
    });
  }
  return String(parsed).padStart(3, "0");
}

function requireSafeSegment(value, field) {
  if (!SAFE_SEGMENT_PATTERN.test(value ?? "") || value === "." || value === "..") {
    fail("INVALID_IDENTITY", `${field} is not a safe identity segment: ${value ?? "<missing>"}`, {
      field,
      actual: value ?? null,
      expected: "[A-Za-z0-9][A-Za-z0-9._-]* without path separators",
    });
  }
  return value;
}

function pathIsInside(child, parent, { allowEqual = true } = {}) {
  const childResolved = resolve(child);
  const parentResolved = resolve(parent);
  if (allowEqual && childResolved === parentResolved) return true;
  const childRelative = relative(parentResolved, childResolved);
  return childRelative !== "" && childRelative !== ".." && !childRelative.startsWith(`..${sep}`) && !childRelative.startsWith("/") && !childRelative.includes(`${sep}${sep}`);
}

async function pathExists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

async function requireExistingPath(path, field, issues, { directory = false } = {}) {
  if (!path) return false;
  try {
    const info = await stat(path);
    if (directory && !info.isDirectory()) {
      issues.push(issue(field, "NOT_DIRECTORY", path, "existing directory", "The path must be an existing directory."));
      return false;
    }
    if (!directory && !info.isFile()) {
      issues.push(issue(field, "NOT_FILE", path, "existing regular file", "The path must be an existing regular file."));
      return false;
    }
    return true;
  } catch (error) {
    issues.push(issue(field, "PATH_NOT_FOUND", path, "existing path", "The referenced path does not exist."));
    return false;
  }
}

async function canonicalPath(path) {
  let candidate = resolve(path);
  const suffix = [];
  while (!(await pathExists(candidate))) {
    const parent = dirname(candidate);
    if (parent === candidate) return candidate;
    suffix.unshift(candidate.slice(parent.length + 1));
    candidate = parent;
  }
  const existing = await realpath(candidate);
  return suffix.length > 0 ? join(existing, ...suffix) : existing;
}

export async function digestFile(filePath) {
  const bytes = await readFile(resolve(filePath));
  return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
}

async function digestIfPresent(filePath) {
  if (!(await pathExists(filePath))) return null;
  return digestFile(filePath);
}

async function runGitRaw(cwd, args) {
  if (!globalThis.Bun?.spawn) {
    fail("RUNTIME_UNAVAILABLE", "Squad workflow commands require Bun to execute Git checks.");
  }
  const child = Bun.spawn(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" });
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(child.stdout).text(),
    new Response(child.stderr).text(),
    child.exited,
  ]);
  return { stdout: stdout.trim(), stderr: stderr.trim(), exitCode };
}

async function runGit(cwd, args, { allowFailure = false } = {}) {
  const result = await runGitRaw(cwd, args);
  if (result.exitCode !== 0 && !allowFailure) {
    fail("GIT_COMMAND_FAILED", `Git command failed: git ${args.join(" ")}`, {
      cwd: resolve(cwd),
      args,
      exit_code: result.exitCode,
      stderr: result.stderr,
    });
  }
  return result;
}

export async function resolveGitRevision(repository, revision, field = "revision") {
  if (!REVISION_PATTERN.test(revision ?? "")) {
    fail("INVALID_REVISION", `${field} is not a valid Git revision: ${revision ?? "<missing>"}`, {
      field,
      actual: revision ?? null,
      expected: "7-64 hexadecimal characters",
    });
  }
  const result = await runGit(repository, ["rev-parse", "--verify", `${revision}^{commit}`], { allowFailure: true });
  if (result.exitCode !== 0) {
    fail("REVISION_NOT_FOUND", `${field} does not resolve in the target repository: ${revision}`, {
      field,
      actual: revision,
      expected: "a commit resolvable by git cat-file",
      repository: resolve(repository),
      stderr: result.stderr,
    });
  }
  return result.stdout;
}

function parseWorktreeList(text) {
  const records = [];
  let current = null;
  for (const line of text.split("\n")) {
    if (line === "") {
      if (current) records.push(current);
      current = null;
      continue;
    }
    const [key, ...rest] = line.split(" ");
    const value = rest.join(" ");
    if (key === "worktree") {
      if (current) records.push(current);
      current = { path: value };
    } else if (current) {
      if (key === "HEAD") current.head = value;
      else if (key === "branch") current.branch = value.replace(/^refs\/heads\//, "");
      else if (key === "detached") current.branch = "DETACHED";
      else if (key === "bare") current.bare = true;
    }
  }
  if (current) records.push(current);
  return records;
}

export async function gitSnapshot(repository) {
  const supplied = resolve(repository);
  const rootResult = await runGit(supplied, ["rev-parse", "--show-toplevel"]);
  const root = await canonicalPath(rootResult.stdout);
  const commonResult = await runGit(supplied, ["rev-parse", "--git-common-dir"]);
  const repositoryId = await canonicalPath(resolve(supplied, commonResult.stdout));
  const branchResult = await runGit(supplied, ["symbolic-ref", "--quiet", "--short", "HEAD"], { allowFailure: true });
  const branch = branchResult.exitCode === 0 ? branchResult.stdout : "DETACHED";
  const head = await runGit(supplied, ["rev-parse", "HEAD"]);
  const status = await runGit(supplied, ["status", "--short"]);
  const worktrees = await Promise.all(parseWorktreeList((await runGit(supplied, ["worktree", "list", "--porcelain"])).stdout).map(async (record) => ({
    ...record,
    path: await canonicalPath(record.path),
  })));
  return {
    root,
    repository_id: repositoryId,
    branch,
    head: head.stdout,
    dirty: status.stdout.length > 0,
    status: status.stdout,
    worktrees,
  };
}

function deriveWorkspaceAndBacklog(ticketsPath) {
  const absolute = resolve(ticketsPath);
  const parts = absolute.split(sep);
  const ticketsIndex = parts.lastIndexOf("tickets.md");
  const sprints = ticketsIndex > 0 && parts[ticketsIndex - 2] === "sprints" && parts[ticketsIndex - 1];
  if (!sprints || parts[ticketsIndex - 3] !== "_xzy-ai") {
    fail("INVALID_SOURCE_PATH", `Canonical tickets path must be _xzy-ai/sprints/<backlog>/tickets.md: ${absolute}`, {
      field: "source.tickets_index_path",
      actual: absolute,
      expected: "<workspace>/_xzy-ai/sprints/<backlog>/tickets.md",
    });
  }
  const workspace = parts.slice(0, ticketsIndex - 3).join(sep) || sep;
  return { workspace, backlog: sprints };
}

async function linkedTicketRecords(ticketsPath) {
  const text = await readFile(resolve(ticketsPath), "utf8");
  const records = [];
  const linkPattern = /\[([^\]]+)\]\(([^)]+)\)/g;
  for (const match of text.matchAll(linkPattern)) {
    const label = match[1].trim();
    const href = match[2].split("#", 1)[0].trim();
    const id = label.match(/\b(?:T[0-9]{3,}|REM-[A-Za-z0-9][A-Za-z0-9._-]*)\b/)?.[0] ?? href.split("/").at(-1)?.replace(/\.[^.]+$/, "");
    if (!id || !href || href.startsWith("#")) continue;
    records.push({ id, path: resolve(dirname(ticketsPath), href) });
  }
  return records;
}

async function assertTicketLinked(ticketsPath, unitId, ticketPath, issuesOrError) {
  const records = await linkedTicketRecords(ticketsPath);
  const match = records.find((record) => record.id === unitId);
  if (!match) {
    const details = { field: "source.work_unit_path", actual: ticketPath, expected: `linked ${unitId} record in ${ticketsPath}` };
    if (Array.isArray(issuesOrError)) issuesOrError.push(issue("source.work_unit_path", "TICKET_NOT_LINKED", ticketPath, details.expected, "The selected work unit is not linked by the canonical ticket index."));
    else fail("TICKET_NOT_LINKED", `The canonical index does not link ${unitId}: ${ticketsPath}`, details);
    return;
  }
  const canonicalMatch = await canonicalPath(match.path);
  const canonicalTicket = await canonicalPath(ticketPath);
  if (canonicalMatch !== canonicalTicket) {
    const details = { field: "source.work_unit_path", actual: canonicalTicket, expected: canonicalMatch };
    if (Array.isArray(issuesOrError)) issuesOrError.push(issue("source.work_unit_path", "TICKET_PATH_MISMATCH", canonicalTicket, canonicalMatch, "The handoff ticket path differs from the canonical index link."));
    else fail("TICKET_PATH_MISMATCH", `The selected ticket path does not match the canonical index: ${ticketPath}`, details);
  }
}

function normalizeRunId(run) {
  return asString(run?.run_id) ?? asString(run?.id);
}

function normalizeUnitId(state) {
  return asString(state?.work_unit_id) ?? asString(state?.id) ?? asString(state?.unit_id);
}

function normalizeLifecycleState(state, field = "state") {
  const primary = asString(state?.state);
  const alternate = asString(state?.lifecycle_state);
  if (primary && alternate && primary !== alternate) {
    fail("AMBIGUOUS_STATE", `${field}.state and ${field}.lifecycle_state disagree.`, {
      field: `${field}.lifecycle_state`,
      actual: alternate,
      expected: primary,
    });
  }
  return primary ?? alternate;
}

function normalizeDependencies(state) {
  const raw = state?.dependencies ?? state?.blocked_by ?? state?.blockers ?? [];
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    if (typeof entry === "string") return { work_unit_id: entry };
    if (isMapping(entry)) return {
      work_unit_id: entry.work_unit_id ?? entry.id ?? entry.ticket_id,
      state: entry.state,
      state_path: entry.state_path,
    };
    return { work_unit_id: undefined, state: entry };
  });
}

function roleOperationType(roleKey) {
  if (roleKey === "worker") return "DISPATCH_WORKER";
  if (roleKey === "reviewer") return "DISPATCH_REVIEWER";
  if (roleKey === "qa") return "DISPATCH_QA";
  return "DISPATCH_ANALYSIS";
}

function roleDirectory(roleKey) {
  return roleKey === "analysis" ? "analysis" : roleKey;
}

function dispatchTargetState(roleKey, current) {
  if (roleKey === "worker" && current === "READY") return "ASSIGNED";
  if (roleKey === "reviewer" && current === "AWAITING_REVIEW") return "REVIEWING";
  return current;
}

function roleTransitionTarget(roleKey, current) {
  const target = dispatchTargetState(roleKey, current);
  return target === current ? null : target;
}

async function readOperationFiles(runDirectory) {
  const directory = join(runDirectory, "operations");
  if (!(await pathExists(directory))) return [];
  const names = (await readdir(directory)).filter((name) => name.endsWith(".yaml")).sort();
  const operations = [];
  for (const name of names) {
    try {
      const document = await readYamlFile(join(directory, name));
      operations.push({ path: document.file, digest: document.digest, value: document.value });
    } catch (error) {
      operations.push({ path: join(directory, name), error: { code: error.code ?? "READ_FAILED", message: error.message } });
    }
  }
  return operations;
}

async function readTransitionFiles(runDirectory) {
  const directory = join(runDirectory, "transitions");
  if (!(await pathExists(directory))) return [];
  const names = (await readdir(directory)).filter((name) => name.endsWith(".yaml")).sort();
  const transitions = [];
  for (const name of names) {
    try {
      const document = await readYamlFile(join(directory, name));
      transitions.push({ path: document.file, digest: document.digest, value: document.value });
    } catch (error) {
      transitions.push({ path: join(directory, name), error: { code: error.code ?? "READ_FAILED", message: error.message } });
    }
  }
  return transitions;
}

async function readWorkUnits(runDirectory) {
  const directory = join(runDirectory, "work-units");
  if (!(await pathExists(directory))) return [];
  const entries = await readdir(directory, { withFileTypes: true });
  const units = [];
  for (const entry of entries.filter((item) => item.isDirectory()).sort((left, right) => left.name.localeCompare(right.name))) {
    const statePath = join(directory, entry.name, "state.yaml");
    if (!(await pathExists(statePath))) {
      units.push({ path: statePath, directory_id: entry.name, error: { code: "STATE_NOT_FOUND", message: "Missing state.yaml" }, value: null });
      continue;
    }
    try {
      const document = await readYamlFile(statePath);
      units.push({ path: statePath, directory_id: entry.name, digest: document.digest, value: document.value });
    } catch (error) {
      units.push({ path: statePath, directory_id: entry.name, error: { code: error.code ?? "READ_FAILED", message: error.message }, value: null });
    }
  }
  return units;
}

async function readRunDocument(runPath) {
  const document = await readYamlFile(runPath);
  if (!isMapping(document.value)) fail("INVALID_RUN", `Run file is not a YAML mapping: ${runPath}`);
  const runId = normalizeRunId(document.value);
  if (!runId) fail("INVALID_RUN", `Run file has no run_id: ${runPath}`, { field: "run_id", actual: null, expected: "non-empty run_id" });
  return { ...document, run_id: runId };
}

export async function resolveRunPath(options = {}, runId = undefined) {
  const targetId = runId ?? options.runId;
  if (options.run || options.runDir) {
    const direct = resolve(options.run ?? join(resolve(options.runDir), "run.yaml"));
    if (targetId) {
      const document = await readRunDocument(direct);
      if (document.run_id !== targetId) fail("RUN_ID_MISMATCH", `Run file contains ${document.run_id}, not ${targetId}.`, { field: "run_id", actual: document.run_id, expected: targetId });
    }
    return direct;
  }
  if (!targetId) fail("MISSING_ARGUMENT", "Provide --run, --run-dir, or a run ID.");
  requireSafeSegment(targetId, "run_id");
  const workspace = resolve(options.workspace ?? process.cwd());
  const candidates = [];
  const xzy = join(workspace, "_xzy-ai", "sprints");
  if (await pathExists(xzy)) {
    for (const backlog of await readdir(xzy, { withFileTypes: true })) {
      if (!backlog.isDirectory() || !SAFE_SEGMENT_PATTERN.test(backlog.name)) continue;
      const candidate = join(xzy, backlog.name, "orchestration", targetId, "run.yaml");
      if (await pathExists(candidate)) candidates.push(candidate);
    }
  }
  if (candidates.length === 0) {
    fail("RUN_NOT_FOUND", `Could not find run ${targetId}.`, { run_id: targetId, workspace });
  }
  if (candidates.length > 1) {
    fail("AMBIGUOUS_RUN", `More than one run ${targetId} exists. Supply --run or --run-dir.`, { run_id: targetId, candidates });
  }
  return candidates[0];
}

function expectedNormalWorktreePath(workspace, backlog, runId, unitId) {
  return join(workspace, "worktrees", "squad", backlog, runId, unitId);
}

function isRecoveryWorktree(path, normalPath) {
  const canonical = resolve(normalPath);
  const candidate = resolve(path);
  if (!pathIsInside(candidate, canonical)) return false;
  const name = candidate.slice(canonical.length + 1);
  return /^recovery-[0-9]{3}$/.test(name);
}

async function validatePathDigest(field, filePath, expectedDigest, issues) {
  const exists = await requireExistingPath(filePath, field, issues);
  if (!exists || !expectedDigest) return;
  const normalized = normalizeDigest(expectedDigest, `${field}.digest`, issues);
  if (!normalized) return;
  try {
    const actual = await digestFile(filePath);
    if (actual !== normalized) {
      issues.push(issue(`${field}.digest`, "DIGEST_MISMATCH", actual, normalized, "The referenced file digest does not match the handoff."));
    }
  } catch (error) {
    issues.push(issue(field, "READ_FAILED", error.message, "readable file", "The referenced file could not be read."));
  }
}

function addExpectedIssue(issues, field, actual, expected, code, message) {
  if (!deepEqual(actual, expected)) issues.push(issue(field, code, actual, expected, message));
}

function actualStateFromDocument(value) {
  return normalizeLifecycleState(value, "work_unit");
}

function actualUnitFromDocument(value) {
  return normalizeUnitId(value);
}

async function validateDependencyStates(statePath, dependencies, issues) {
  const workUnitsDirectory = dirname(dirname(statePath));
  for (const [index, dependency] of dependencies.entries()) {
    const id = dependency.work_unit_id;
    if (!id) {
      issues.push(issue(`dependencies[${index}].work_unit_id`, "REQUIRED_FIELD", null, "work unit ID", "Each dependency must identify a work unit."));
      continue;
    }
    const dependencyPath = dependency.state_path ? resolve(dependency.state_path) : join(workUnitsDirectory, id, "state.yaml");
    if (!(await requireExistingPath(dependencyPath, `dependencies[${index}].state_path`, issues))) continue;
    try {
      const document = await readYamlFile(dependencyPath);
      const current = actualStateFromDocument(document.value);
      addExpectedIssue(issues, `dependencies[${index}].state`, current, "DONE", "DEPENDENCY_NOT_DONE", "A dispatch dependency is not DONE.");
      if (dependency.state) addExpectedIssue(issues, `dependencies[${index}].state`, current, dependency.state, "DEPENDENCY_STATE_MISMATCH", "The handoff dependency state is stale.");
    } catch (error) {
      issues.push(issue(`dependencies[${index}]`, "DEPENDENCY_READ_FAILED", error.message, "readable state.yaml", "The dependency state could not be read."));
    }
  }
}

function validateTransitionShape(transition, currentState, issues, field = "transition") {
  if (transition === undefined || transition === null) return;
  if (!isMapping(transition)) {
    issues.push(issue(field, "INVALID_MAPPING", transition, "mapping", "The transition must be a mapping."));
    return;
  }
  const from = transition.from;
  const to = transition.to;
  if (!UNIT_STATES.includes(from)) issues.push(issue(`${field}.from`, "INVALID_STATE", from ?? null, UNIT_STATES, "The transition source is not a known work-unit state."));
  if (!UNIT_STATES.includes(to)) issues.push(issue(`${field}.to`, "INVALID_STATE", to ?? null, UNIT_STATES, "The transition destination is not a known work-unit state."));
  if (from && currentState && from !== currentState) issues.push(issue(`${field}.from`, "TRANSITION_SOURCE_MISMATCH", from, currentState, "The handoff transition source does not match the current state."));
  if (from && to && UNIT_STATES.includes(from) && !LEGAL_UNIT_TRANSITIONS[from].includes(to)) {
    issues.push(issue(field, "ILLEGAL_TRANSITION", `${from} -> ${to}`, LEGAL_UNIT_TRANSITIONS[from], "The requested lifecycle transition is not legal."));
  }
}

function validateIdentityFieldNames(handoff, issues) {
  const ambiguous = [
    ["baseline", handoff.baseline, "worktree.baseline"],
    ["current_head", handoff.current_head, "worktree.current_head"],
    ["target_head", handoff.target_head, "target.head"],
    ["target_branch", handoff.target_branch, "target.branch"],
  ];
  for (const [legacyField, legacyValue, canonicalField] of ambiguous) {
    if (legacyValue !== undefined) {
      issues.push(issue(legacyField, "AMBIGUOUS_FIELD_LOCATION", legacyValue, canonicalField, `Use ${canonicalField}; duplicate top-level identity fields are not accepted.`));
    }
  }
}

export async function validateHandoffData(handoff, handoffPath = "<inline>", options = {}) {
  const issues = [];
  const checks = [];
  if (!isMapping(handoff)) {
    fail("INVALID_HANDOFF", `Handoff is not a YAML mapping: ${handoffPath}`, {
      errors: [issue("document", "INVALID_MAPPING", handoff, "mapping", "A handoff must be a YAML mapping.")],
    });
  }
  validateIdentityFieldNames(handoff, issues);
  if (handoff.schema_version !== 1) issues.push(issue("schema_version", "UNSUPPORTED_SCHEMA", handoff.schema_version ?? null, 1, "Only handoff schema version 1 is supported."));
  if (handoff.kind !== "squad-handoff") issues.push(issue("kind", "INVALID_KIND", handoff.kind ?? null, "squad-handoff", "The typed handoff kind is required."));
  const roleKey = normalizeRole(handoff.role, "role", issues);
  const runId = requireString(handoff.run_id, "run_id", issues);
  const unitId = requireString(handoff.work_unit_id, "work_unit_id", issues);
  const attemptId = requireString(handoff.attempt_id, "attempt_id", issues);
  const operationId = requireString(handoff.operation_id, "operation_id", issues);
  for (const [field, value] of [["run_id", runId], ["work_unit_id", unitId]]) {
    if (!value) continue;
    try { requireSafeSegment(value, field); }
    catch (error) { issues.push(issue(field, error.code ?? "INVALID_IDENTITY", value, "safe identity segment", error.message)); }
  }
  if (roleKey && attemptId && runId && unitId) {
    const expectedPrefix = `${runId}:${unitId}:${roleKey}`;
    if (!attemptId.startsWith(`${expectedPrefix}:`) || !ATTEMPT_PATTERN.test(attemptId)) {
      issues.push(issue("attempt_id", "INVALID_ATTEMPT_ID", attemptId, `${expectedPrefix}:attempt-<NNN>`, "Attempt IDs must use the canonical role-scoped form."));
    }
  }
  if (operationId && runId && unitId) {
    const expectedPrefix = `${runId}:${unitId}:`;
    const action = operationId.startsWith(expectedPrefix) ? operationId.slice(expectedPrefix.length) : "";
    if (!operationId.startsWith(expectedPrefix) || operationId.split(":").length !== 3 || !/^[A-Z][A-Z0-9_]*$/.test(action)) {
      issues.push(issue("operation_id", "INVALID_OPERATION_ID", operationId, `${runId}:${unitId}:<UPPER_SNAKE_ACTION>`, "Operation IDs must use the canonical run/unit/action form."));
    }
  }
  if (handoff.review_attempt_id !== undefined && handoff.review_attempt_id !== attemptId) {
    issues.push(issue("review_attempt_id", "AMBIGUOUS_ATTEMPT_ID", handoff.review_attempt_id, "attempt_id", "Use attempt_id as the durable identity; a reviewer projection must point to that exact value."));
  }
  if (handoff.fix_attempt !== undefined && (!Number.isSafeInteger(handoff.fix_attempt) || handoff.fix_attempt < 0)) {
    issues.push(issue("fix_attempt", "INVALID_FIX_ATTEMPT", handoff.fix_attempt, "non-negative integer", "fix_attempt is a count, not a competing attempt identity."));
  }

  const source = isMapping(handoff.source) ? handoff.source : {};
  const target = isMapping(handoff.target) ? handoff.target : {};
  const worktree = isMapping(handoff.worktree) ? handoff.worktree : {};
  const artifact = isMapping(handoff.artifact) ? handoff.artifact : {};
  const report = isMapping(handoff.report) ? handoff.report : {};
  const evidence = isMapping(handoff.evidence) ? handoff.evidence : {};
  const operation = isMapping(handoff.operation) ? handoff.operation : {};
  const state = isMapping(handoff.state) ? handoff.state : {};

  const ticketsPath = requireString(source.tickets_index_path, "source.tickets_index_path", issues, { absolute: true });
  const ticketPath = requireString(source.work_unit_path, "source.work_unit_path", issues, { absolute: true });
  const ticketsDigest = normalizeDigest(source.tickets_digest, "source.tickets_digest", issues);
  const ticketDigest = normalizeDigest(source.ticket_digest, "source.ticket_digest", issues);
  const artifactRunDir = requireString(artifact.run_dir, "artifact.run_dir", issues, { absolute: true });
  const statePath = requireString(artifact.state_path, "artifact.state_path", issues, { absolute: true });
  const manifestPath = requireString(artifact.manifest_path, "artifact.manifest_path", issues, { absolute: true });
  const handoffArtifactPath = requireString(artifact.handoff_path, "artifact.handoff_path", issues, { absolute: true });
  const operationPath = requireString(artifact.operation_path, "artifact.operation_path", issues, { absolute: true });
  const reportPath = requireString(report.path, "report.path", issues, { absolute: true });
  const evidenceDirectory = requireString(evidence.directory, "evidence.directory", issues, { absolute: true });
  const manifest = isMapping(handoff.manifest) ? handoff.manifest : {};
  const manifestReferencePath = requireString(manifest.path, "manifest.path", issues, { absolute: true });
  const manifestDigest = normalizeDigest(manifest.digest, "manifest.digest", issues);
  const targetRoot = requireString(target.repository_root, "target.repository_root", issues, { absolute: true });
  const targetRepositoryId = requireString(target.repository_id, "target.repository_id", issues, { absolute: true });
  const targetBranch = requireString(target.branch, "target.branch", issues);
  const targetHead = normalizeRevision(target.head, "target.head", issues);
  const worktreePath = requireString(worktree.path, "worktree.path", issues, { absolute: true });
  const worktreeRelativePath = requireString(worktree.relative_path, "worktree.relative_path", issues);
  const worktreeRepositoryId = requireString(worktree.repository_id, "worktree.repository_id", issues, { absolute: true });
  const worktreeBranch = requireString(worktree.branch, "worktree.branch", issues);
  const baseline = normalizeRevision(worktree.baseline, "worktree.baseline", issues);
  const currentHead = normalizeRevision(worktree.current_head, "worktree.current_head", issues);
  const currentState = requireString(state.current, "state.current", issues);
  const expectedState = state.expected === undefined ? currentState : requireString(state.expected, "state.expected", issues);
  const nestedOperationId = requireString(operation.id, "operation.id", issues);
  const nestedOperationAttemptId = requireString(operation.attempt_id, "operation.attempt_id", issues);
  const operationType = requireString(operation.type, "operation.type", issues);

  if (currentState && !UNIT_STATES.includes(currentState)) issues.push(issue("state.current", "INVALID_STATE", currentState, UNIT_STATES, "The handoff state is not a known work-unit state."));
  if (expectedState && !UNIT_STATES.includes(expectedState)) issues.push(issue("state.expected", "INVALID_STATE", expectedState, UNIT_STATES, "The expected state is not a known work-unit state."));
  if (currentState && expectedState && currentState !== expectedState) validateTransitionShape({ from: currentState, to: expectedState }, currentState, issues, "state.expected_transition");
  if (nestedOperationId && nestedOperationId !== operationId) issues.push(issue("operation.id", "OPERATION_ID_MISMATCH", nestedOperationId, operationId, "The nested operation identity must match the handoff."));
  if (nestedOperationAttemptId && nestedOperationAttemptId !== attemptId) issues.push(issue("operation.attempt_id", "ATTEMPT_ID_MISMATCH", nestedOperationAttemptId, attemptId, "The operation attempt must match the handoff attempt."));
  if (operationType && !/^[A-Z][A-Z0-9_]*$/.test(operationType)) issues.push(issue("operation.type", "INVALID_OPERATION_TYPE", operationType, "UPPER_SNAKE operation type", "The operation type must use the canonical naming format."));
  if (report.digest !== null && report.digest !== undefined) normalizeDigest(report.digest, "report.digest", issues);
  if (report.expected !== undefined && !["CREATE", "EXISTING"].includes(report.expected)) issues.push(issue("report.expected", "INVALID_REPORT_EXPECTATION", report.expected, ["CREATE", "EXISTING"], "Report expectation must be CREATE or EXISTING."));
  if (report.digest === undefined && report.expected === undefined) issues.push(issue("report", "REPORT_EXPECTATION_REQUIRED", report, "digest or expected", "The handoff must state whether the report already exists."));
  if (report.expected === "EXISTING" && (report.digest === undefined || report.digest === null)) issues.push(issue("report.digest", "REPORT_DIGEST_REQUIRED", report.digest ?? null, "sha256:<digest of existing report>", "An existing report must be bound by its exact digest."));
  if (report.digest !== undefined && report.digest !== null && report.expected === undefined) issues.push(issue("report.expected", "REPORT_EXPECTATION_REQUIRED", null, "EXISTING", "An existing report digest must declare the EXISTING expectation."));
  if (report.expected === "CREATE" && report.digest !== undefined && report.digest !== null) issues.push(issue("report", "AMBIGUOUS_REPORT_SNAPSHOT", report, "expected CREATE with null digest", "A report cannot be both newly created and bound to an existing digest."));

  if (ticketsPath && ticketPath && artifactRunDir && statePath && runId && unitId) {
    try {
      const { workspace, backlog } = deriveWorkspaceAndBacklog(ticketsPath);
      const runDirectory = await canonicalPath(artifactRunDir);
      const expectedRunDirectory = await canonicalPath(join(workspace, "_xzy-ai", "sprints", backlog, "orchestration", runId));
      addExpectedIssue(issues, "artifact.run_dir", runDirectory, expectedRunDirectory, "RUN_DIRECTORY_MISMATCH", "The artifact directory is not the canonical run namespace.");
      const expectedStatePath = join(artifactRunDir, "work-units", unitId, "state.yaml");
      if (statePath) addExpectedIssue(issues, "artifact.state_path", await canonicalPath(statePath), await canonicalPath(expectedStatePath), "STATE_PATH_MISMATCH", "The handoff state path is not the canonical unit state file.");
      if (operationPath) addExpectedIssue(issues, "artifact.operation_path", await canonicalPath(operationPath), await canonicalPath(operationPathFor(artifactRunDir, operationId)), "OPERATION_PATH_MISMATCH", "The handoff operation path does not match its operation ID.");
      if (await requireExistingPath(ticketsPath, "source.tickets_index_path", issues)) {
        await validatePathDigest("source.tickets_index_path", ticketsPath, ticketsDigest, issues);
        try { await assertTicketLinked(ticketsPath, unitId, ticketPath, issues); } catch (error) { issues.push(issue("source.tickets_index_path", error.code ?? "TICKET_INDEX_READ_FAILED", error.message, `linked ${unitId} record`, "The canonical ticket link could not be checked.")); }
      }
      if (await requireExistingPath(ticketPath, "source.work_unit_path", issues)) await validatePathDigest("source.work_unit_path", ticketPath, ticketDigest, issues);
      if (await requireExistingPath(artifactRunDir, "artifact.run_dir", issues, { directory: true })) {
        const runPath = join(artifactRunDir, "run.yaml");
        if (!(await requireExistingPath(runPath, "artifact.run_dir/run.yaml", issues))) {
          issues.push(issue("artifact.run_dir", "RUN_RECORD_REQUIRED", runPath, "existing run.yaml", "The handoff run namespace must contain its authoritative run record."));
        } else {
          try {
            const runDocument = await readYamlFile(runPath);
            const runValue = runDocument.value;
            addExpectedIssue(issues, "run_id", normalizeRunId(runValue), runId, "RUN_ID_MISMATCH", "The handoff run ID differs from the run record.");
            const runSource = isMapping(runValue.source) ? runValue.source : {};
            const runTicketsPath = runSource.tickets_index_path ?? runSource.tickets_path;
            if (runTicketsPath) addExpectedIssue(issues, "source.tickets_index_path", await canonicalPath(runTicketsPath), await canonicalPath(ticketsPath), "SOURCE_PATH_MISMATCH", "The handoff source differs from the run record.");
            else issues.push(issue("run.source.tickets_index_path", "REQUIRED_FIELD", null, ticketsPath, "The run record has no canonical tickets index path."));
            const runTicketsDigest = runSource.digest ?? runSource.tickets_digest;
            if (runTicketsDigest) addExpectedIssue(issues, "source.tickets_digest", String(runTicketsDigest).toLowerCase(), ticketsDigest, "DIGEST_MISMATCH", "The handoff source digest differs from the run record.");
            else issues.push(issue("run.source.digest", "REQUIRED_DIGEST", null, ticketsDigest, "The run record has no canonical source digest."));
            const runProject = isMapping(runValue.project) ? runValue.project : {};
            const runTarget = isMapping(runValue.target) ? runValue.target : {};
            if (runProject.root ?? runValue.project_root) addExpectedIssue(issues, "target.repository_root", await canonicalPath(runProject.root ?? runValue.project_root), await canonicalPath(targetRoot), "REPOSITORY_ROOT_MISMATCH", "The handoff target root differs from the run record.");
            if (runProject.target_branch ?? runTarget.branch) addExpectedIssue(issues, "target.branch", runProject.target_branch ?? runTarget.branch, targetBranch, "BRANCH_MISMATCH", "The handoff target branch differs from the run record.");
            const runTargetHead = runProject.target_head ?? runTarget.head ?? runTarget.expected_head ?? runProject.initial_head;
            if (runTargetHead) {
              try {
                const runResolvedHead = await resolveGitRevision(targetRoot, runTargetHead, "run.target.head");
                const handoffResolvedHead = await resolveGitRevision(targetRoot, targetHead, "target.head");
                addExpectedIssue(issues, "target.head", handoffResolvedHead, runResolvedHead, "TARGET_HEAD_MISMATCH", "The handoff target HEAD differs from the run record.");
              } catch (error) {
                issues.push(issue("target.head", error.code ?? "REVISION_NOT_FOUND", targetHead, runTargetHead, error.message));
              }
            }
          } catch (error) {
            issues.push(issue("artifact.run_dir/run.yaml", "RUN_READ_FAILED", error.message, "readable run record", "The authoritative run record could not be checked."));
          }
        }
        const stateExists = await requireExistingPath(statePath, "artifact.state_path", issues);
        if (stateExists) {
          const stateDocument = await readYamlFile(statePath);
          const actualUnit = actualUnitFromDocument(stateDocument.value);
          const actualRun = normalizeRunId(stateDocument.value);
          const actualState = actualStateFromDocument(stateDocument.value);
          const actualAttempt = stateDocument.value.attempt_id;
          const durableDependencyIds = normalizeDependencies(stateDocument.value).map((dependency) => dependency.work_unit_id).sort();
          const handoffDependencyIds = normalizeDependencies(handoff).map((dependency) => dependency.work_unit_id).sort();
          addExpectedIssue(issues, "dependencies", handoffDependencyIds, durableDependencyIds, "DEPENDENCY_SET_MISMATCH", "The handoff dependency set is not the latest durable dependency set.");
          addExpectedIssue(issues, "work_unit_id", actualUnit, unitId, "WORK_UNIT_ID_MISMATCH", "The state file belongs to another work unit.");
          addExpectedIssue(issues, "run_id", actualRun, runId, "RUN_ID_MISMATCH", "The state file belongs to another run.");
          addExpectedIssue(issues, "state.current", currentState, actualState, "STATE_MISMATCH", "The handoff state is not the latest durable state.");
          if (actualAttempt && attemptId && actualAttempt !== attemptId && !(actualState === "BLOCKED" && handoff.transition?.from === "BLOCKED")) {
            issues.push(issue("attempt_id", "ATTEMPT_MISMATCH", attemptId, actualAttempt, "The handoff attempt is not the current durable attempt."));
          }
          const stateWorktree = isMapping(stateDocument.value.worktree) ? stateDocument.value.worktree : {};
          if (stateWorktree.path) addExpectedIssue(issues, "worktree.path", await canonicalPath(worktreePath), await canonicalPath(stateWorktree.path), "WORKTREE_PATH_MISMATCH", "The handoff worktree differs from durable state.");
          if (stateWorktree.branch) addExpectedIssue(issues, "worktree.branch", worktreeBranch, stateWorktree.branch, "WORKTREE_BRANCH_MISMATCH", "The handoff branch differs from durable state.");
          if (stateWorktree.baseline) {
            try {
              const durableBaseline = await resolveGitRevision(worktreePath, stateWorktree.baseline, "worktree.baseline");
              const handoffBaseline = await resolveGitRevision(worktreePath, baseline, "worktree.baseline");
              addExpectedIssue(issues, "worktree.baseline", handoffBaseline, durableBaseline, "BASELINE_MISMATCH", "The handoff baseline differs from durable state.");
            } catch (error) {
              issues.push(issue("worktree.baseline", error.code ?? "BASELINE_VALIDATION_FAILED", baseline, stateWorktree.baseline, error.message));
            }
          }
        }
      }
      if (manifestReferencePath && manifestPath) {
        const canonicalManifestPath = await canonicalPath(manifestPath);
        const canonicalManifestReference = await canonicalPath(manifestReferencePath);
        addExpectedIssue(issues, "manifest.path", canonicalManifestReference, canonicalManifestPath, "MANIFEST_PATH_MISMATCH", "The manifest reference differs from the artifact manifest path.");
        if (await pathExists(manifestPath)) {
          await validatePathDigest("manifest.path", manifestPath, manifestDigest, issues);
          try {
            const manifestDocument = await readYamlFile(manifestPath);
            const manifestValue = manifestDocument.value;
            addExpectedIssue(issues, "manifest.run_id", manifestValue.run_id, runId, "RUN_ID_MISMATCH", "The manifest belongs to another run.");
            addExpectedIssue(issues, "manifest.work_unit_id", manifestValue.work_unit_id, unitId, "WORK_UNIT_ID_MISMATCH", "The manifest belongs to another work unit.");
            addExpectedIssue(issues, "manifest.attempt_id", manifestValue.attempt_id, attemptId, "ATTEMPT_ID_MISMATCH", "The manifest belongs to another attempt.");
            addExpectedIssue(issues, "manifest.operation.id", manifestValue.operation?.id, operationId, "OPERATION_ID_MISMATCH", "The manifest operation differs from the handoff.");
          } catch (error) {
            issues.push(issue("manifest.path", "MANIFEST_READ_FAILED", error.message, "readable execution manifest", "The manifest identity could not be checked."));
          }
        } else {
          issues.push(issue("manifest.path", "PATH_NOT_FOUND", manifestPath, "existing immutable manifest", "The handoff cannot be verified without its source manifest."));
        }
      }
      if (handoffArtifactPath && handoffPath) addExpectedIssue(issues, "artifact.handoff_path", await canonicalPath(handoffArtifactPath), await canonicalPath(handoffPath), "HANDOFF_PATH_MISMATCH", "The artifact handoff path differs from the file being validated.");
      if (operationPath) {
        const operationExists = await pathExists(operationPath);
        if (!operationExists && options.requireOperation !== false) {
          issues.push(issue("artifact.operation_path", "PATH_NOT_FOUND", operationPath, "existing operation ledger", "The handoff cannot authorize dispatch before its operation is durable."));
        } else if (operationExists) {
          try {
            const operationDocument = await readYamlFile(operationPath);
            const operationValue = operationDocument.value;
            addExpectedIssue(issues, "operation.id", operationValue.operation_id, operationId, "OPERATION_ID_MISMATCH", "The durable operation ID differs from the handoff.");
            addExpectedIssue(issues, "operation.attempt_id", operationValue.attempt_id, attemptId, "ATTEMPT_ID_MISMATCH", "The durable operation attempt differs from the handoff.");
            addExpectedIssue(issues, "operation.type", operationValue.type, operationType, "OPERATION_TYPE_MISMATCH", "The durable operation type differs from the handoff.");
            addExpectedIssue(issues, "operation.input.run_id", operationValue.input?.run_id, runId, "RUN_ID_MISMATCH", "The operation belongs to another run.");
            addExpectedIssue(issues, "operation.input.work_unit_id", operationValue.input?.work_unit_id, unitId, "WORK_UNIT_ID_MISMATCH", "The operation belongs to another work unit.");
            if (operationValue.input?.handoff_path) addExpectedIssue(issues, "operation.input.handoff_path", await canonicalPath(operationValue.input.handoff_path), await canonicalPath(handoffPath), "HANDOFF_PATH_MISMATCH", "The operation input points to another handoff.");
            if (operationValue.input?.target_head) addExpectedIssue(issues, "operation.input.target_head", operationValue.input.target_head, targetHead, "TARGET_HEAD_MISMATCH", "The operation target HEAD differs from the handoff.");
            if (operationValue.input?.source_revision) addExpectedIssue(issues, "operation.input.source_revision", operationValue.input.source_revision, currentHead, "CURRENT_HEAD_MISMATCH", "The operation source revision differs from the handoff worktree HEAD.");
            if (operationValue.result?.handoff_path) {
              const canonicalResultPath = await canonicalPath(operationValue.result.handoff_path);
              const canonicalHandoffPath = await canonicalPath(handoffPath);
              addExpectedIssue(issues, "operation.result.handoff_path", canonicalResultPath, canonicalHandoffPath, "HANDOFF_PATH_MISMATCH", "The operation result points to another handoff.");
              if (operationValue.result.handoff_digest && await pathExists(handoffPath)) {
                const actualHandoffDigest = await digestFile(handoffPath);
                addExpectedIssue(issues, "operation.result.handoff_digest", actualHandoffDigest, String(operationValue.result.handoff_digest).toLowerCase(), "HANDOFF_DIGEST_MISMATCH", "The operation result digest differs from the actual handoff.");
              }
            }
            if (operationValue.status !== undefined && !OPERATION_STATES.includes(operationValue.status)) issues.push(issue("operation.status", "INVALID_OPERATION_STATUS", operationValue.status, OPERATION_STATES, "The referenced operation has an invalid status."));
            if (operation.status !== undefined) addExpectedIssue(issues, "operation.status", operationValue.status, operation.status, "OPERATION_STATUS_MISMATCH", "The nested operation status is stale.");
          } catch (error) {
            issues.push(issue("artifact.operation_path", "OPERATION_READ_FAILED", error.message, "readable operation ledger", "The referenced operation could not be read."));
          }
        }
      }
      if (reportPath) {
        const reportExists = await pathExists(reportPath);
        if (report.digest !== null && report.digest !== undefined) {
          if (reportExists) {
            await validatePathDigest("report.path", reportPath, report.digest, issues);
            try {
              const reportDocument = await readYamlFile(reportPath);
              const reportValue = reportDocument.value;
              addExpectedIssue(issues, "report.run_id", reportValue.run_id, runId, "RUN_ID_MISMATCH", "The report belongs to another run.");
              addExpectedIssue(issues, "report.work_unit_id", reportValue.work_unit_id, unitId, "WORK_UNIT_ID_MISMATCH", "The report belongs to another work unit.");
              addExpectedIssue(issues, "report.attempt_id", reportValue.attempt_id, attemptId, "ATTEMPT_ID_MISMATCH", "The report belongs to another attempt.");
              addExpectedIssue(issues, "report.role", reportValue.role, handoff.role, "ROLE_MISMATCH", "The report role differs from the handoff role.");
            } catch (error) {
              issues.push(issue("report.path", "REPORT_READ_FAILED", error.message, "readable report", "The report identity could not be checked."));
            }
          } else issues.push(issue("report.path", "PATH_NOT_FOUND", reportPath, "existing report because report.digest is present", "The report digest cannot be checked because the report is missing."));
        } else if (report.expected === "EXISTING" && !reportExists) {
          issues.push(issue("report.path", "PATH_NOT_FOUND", reportPath, "existing report", "The handoff requires an existing report."));
        } else if (report.expected === "CREATE" && reportExists) {
          issues.push(issue("report.path", "REPORT_SNAPSHOT_STALE", reportPath, "report absent at handoff creation", "The handoff snapshot predates a newly created report; generate the next role handoff from a fresh manifest."));
        }
      }
      const canonicalRunDir = await canonicalPath(artifactRunDir);
      for (const [field, path] of [["artifact.state_path", statePath], ["artifact.manifest_path", manifestPath], ["artifact.operation_path", operationPath], ["report.path", reportPath]]) {
        if (path) {
          const candidate = await canonicalPath(path);
          if (!pathIsInside(candidate, canonicalRunDir)) issues.push(issue(field, "PATH_OUTSIDE_RUN", candidate, `path inside ${canonicalRunDir}`, "Durable artifacts must remain inside the run namespace."));
        }
      }
      if (evidenceDirectory) {
        const candidate = await canonicalPath(evidenceDirectory);
        if (!pathIsInside(candidate, canonicalRunDir)) issues.push(issue("evidence.directory", "PATH_OUTSIDE_RUN", candidate, `path inside ${canonicalRunDir}`, "Evidence must remain inside the run namespace."));
      }
      if (worktreePath) {
        const normal = expectedNormalWorktreePath(workspace, backlog, runId, unitId);
        const canonicalWorktree = await canonicalPath(worktreePath);
        const canonicalNormal = await canonicalPath(normal);
        const allowed = canonicalWorktree === canonicalNormal || isRecoveryWorktree(canonicalWorktree, canonicalNormal);
        if (!allowed) issues.push(issue("worktree.path", "CANONICAL_WORKTREE_PATH", canonicalWorktree, `${canonicalNormal} or recovery-<NNN> beneath it`, "The worktree is outside the canonical squad namespace."));
        if (worktreeRelativePath) {
          const canonicalWorkspace = await canonicalPath(workspace);
          const expectedRelative = relative(canonicalWorkspace, canonicalWorktree).split(sep).join("/");
          if (worktreeRelativePath !== expectedRelative) issues.push(issue("worktree.relative_path", "WORKTREE_RELATIVE_PATH_MISMATCH", worktreeRelativePath, expectedRelative, "The relative worktree path does not match its absolute identity."));
          if (worktreeRelativePath.startsWith("/") || worktreeRelativePath.split("/").includes("..")) issues.push(issue("worktree.relative_path", "INVALID_RELATIVE_PATH", worktreeRelativePath, "workspace-relative path without ..", "The relative worktree path must not escape the workspace."));
        }
      }
      await validateDependencyStates(statePath, normalizeDependencies(handoff), issues);
      validateTransitionShape(handoff.transition, currentState, issues);
    } catch (error) {
      if (error instanceof SquadWorkflowError) issues.push(issue("source", error.code, error.message, "coherent canonical source", "The handoff source identity could not be resolved."));
      else issues.push(issue("source", "SOURCE_VALIDATION_FAILED", error.message, "coherent canonical source", "The handoff source identity could not be resolved."));
    }
  }

  let targetSnapshot = null;
  if (targetRoot && targetRepositoryId && targetBranch && targetHead) {
    try {
      targetSnapshot = await gitSnapshot(targetRoot);
      if (targetSnapshot.dirty) issues.push(issue("target.dirty", "TARGET_DIRTY", true, false, "The target checkout must be clean for a validated handoff."));
      const canonicalTargetRoot = await canonicalPath(targetRoot);
      check(checks, "target.repository_root", targetSnapshot.root, canonicalTargetRoot);
      if (targetSnapshot.root !== canonicalTargetRoot) issues.push(issue("target.repository_root", "REPOSITORY_ROOT_MISMATCH", targetSnapshot.root, canonicalTargetRoot, "The target repository root differs from the handoff."));
      check(checks, "target.repository_id", targetSnapshot.repository_id, targetRepositoryId);
      check(checks, "target.branch", targetSnapshot.branch, targetBranch);
      if (targetSnapshot.repository_id !== targetRepositoryId) issues.push(issue("target.repository_id", "REPOSITORY_ID_MISMATCH", targetSnapshot.repository_id, targetRepositoryId, "The target repository identity differs from the handoff."));
      if (targetSnapshot.branch !== targetBranch) issues.push(issue("target.branch", "BRANCH_MISMATCH", targetSnapshot.branch, targetBranch, "The target branch differs from the handoff."));
      let resolvedTargetHead;
      try {
        resolvedTargetHead = await resolveGitRevision(targetRoot, targetHead, "target.head");
        check(checks, "target.head", targetSnapshot.head, resolvedTargetHead);
        if (targetSnapshot.head !== resolvedTargetHead) issues.push(issue("target.head", "TARGET_HEAD_MISMATCH", targetSnapshot.head, resolvedTargetHead, "The target branch HEAD differs from the handoff."));
      } catch (error) {
        issues.push(issue("target.head", error.code ?? "REVISION_NOT_FOUND", targetHead, "resolvable target commit", error.message));
      }
      if (worktreePath && worktreeRepositoryId && worktreeBranch && baseline && currentHead) {
        let worktreeSnapshot = null;
        try {
          worktreeSnapshot = await gitSnapshot(worktreePath);
        } catch (error) {
          issues.push(issue("worktree.path", error.code ?? "GIT_VALIDATION_FAILED", worktreePath, "valid registered Git worktree", error.message));
        }
        if (worktreeSnapshot) {
          check(checks, "worktree.repository_id", worktreeSnapshot.repository_id, worktreeRepositoryId);
          check(checks, "worktree.branch", worktreeSnapshot.branch, worktreeBranch);
          if (worktreeSnapshot.repository_id !== targetRepositoryId) issues.push(issue("worktree.repository_id", "WORKTREE_REPOSITORY_MISMATCH", worktreeSnapshot.repository_id, targetRepositoryId, "The worktree is not derived from the target repository."));
          if (worktreeSnapshot.repository_id !== worktreeRepositoryId) issues.push(issue("worktree.repository_id", "REPOSITORY_ID_MISMATCH", worktreeSnapshot.repository_id, worktreeRepositoryId, "The worktree repository identity differs from the handoff."));
          if (worktreeSnapshot.branch !== worktreeBranch) issues.push(issue("worktree.branch", "BRANCH_MISMATCH", worktreeSnapshot.branch, worktreeBranch, "The worktree branch differs from the handoff."));
          try {
            const resolvedCurrent = await resolveGitRevision(worktreePath, currentHead, "worktree.current_head");
            check(checks, "worktree.current_head", worktreeSnapshot.head, resolvedCurrent);
            if (worktreeSnapshot.head !== resolvedCurrent) issues.push(issue("worktree.current_head", "CURRENT_HEAD_MISMATCH", worktreeSnapshot.head, resolvedCurrent, "The worktree HEAD differs from the handoff."));
          } catch (error) {
            issues.push(issue("worktree.current_head", error.code ?? "REVISION_NOT_FOUND", currentHead, "resolvable worktree commit", error.message));
          }
          let resolvedBaseline;
          try {
            resolvedBaseline = await resolveGitRevision(worktreePath, baseline, "worktree.baseline");
            if (resolvedTargetHead) {
              try {
                const mergeBase = await runGit(worktreePath, ["merge-base", worktreeSnapshot.head, resolvedTargetHead]);
                check(checks, "worktree.baseline.merge_base", resolvedBaseline, mergeBase.stdout);
                if (resolvedBaseline !== mergeBase.stdout) issues.push(issue("worktree.baseline", "BASELINE_MERGE_BASE_MISMATCH", resolvedBaseline, mergeBase.stdout, "The recorded baseline is not the Git merge-base of the worktree and target HEAD."));
              } catch (error) {
                issues.push(issue("worktree.baseline", error.code ?? "MERGE_BASE_FAILED", resolvedBaseline, "Git merge-base of worktree and target", error.message));
              }
            }
          } catch (error) {
            issues.push(issue("worktree.baseline", error.code ?? "REVISION_NOT_FOUND", baseline, "resolvable baseline commit", error.message));
          }
          const canonicalWorktreePath = await canonicalPath(worktreePath);
          const record = worktreeSnapshot.worktrees.find((item) => item.path === canonicalWorktreePath);
          if (!record) issues.push(issue("worktree.path", "WORKTREE_NOT_REGISTERED", worktreePath, "registered Git worktree", "The supplied path is not registered as a Git worktree."));
        }
      }
    } catch (error) {
      if (error instanceof SquadWorkflowError) issues.push(issue("target", error.code, error.message, "resolvable repository identity", "Git identity validation failed."));
      else issues.push(issue("target", "GIT_VALIDATION_FAILED", error.message, "resolvable repository identity", "Git identity validation failed."));
    }
  }

  if (roleKey === "reviewer") {
    const revision = handoff.implementation_revision ?? handoff.reviewer?.reviewed_revision;
    normalizeRevision(revision, "implementation_revision", issues);
    if (targetRoot && revision) {
      try {
        await resolveGitRevision(targetRoot, revision, "implementation_revision");
      } catch (error) {
        issues.push(issue("implementation_revision", error.code ?? "REVISION_NOT_FOUND", revision, "resolvable implementation commit", error.message));
      }
    }
  }

  if (issues.length > 0) {
    const result = { valid: false, handoff_path: handoffPath, checks, errors: issues };
    if (options.throwOnInvalid !== false) fail("HANDOFF_INVALID", `Handoff validation failed: ${handoffPath}`, { errors: issues, checks });
    return result;
  }
  return { valid: true, handoff_path: handoffPath, checks, errors: [] };
}

export async function validateHandoffFile(handoffPath, options = {}) {
  const document = await readYamlFile(handoffPath);
  const result = await validateHandoffData(document.value, document.file, options);
  return { ...result, digest: document.digest };
}

async function readTicketAndRunContext(runPath, statePath, ticketPathOverride) {
  const runDocument = await readRunDocument(runPath);
  const run = runDocument.value;
  const runId = runDocument.run_id;
  const stateDocument = await readYamlFile(statePath);
  if (!isMapping(stateDocument.value)) fail("INVALID_STATE", `State file is not a YAML mapping: ${statePath}`);
  const state = stateDocument.value;
  const unitId = normalizeUnitId(state);
  if (!unitId) fail("INVALID_STATE", `State file has no work_unit_id: ${statePath}`);
  const stateRunId = normalizeRunId(state);
  if (stateRunId && stateRunId !== runId) fail("RUN_ID_MISMATCH", `State ${statePath} belongs to ${stateRunId}, not ${runId}.`, { field: "run_id", actual: stateRunId, expected: runId });
  const source = isMapping(run.source) ? run.source : {};
  const ticketsPath = resolve(source.tickets_index_path ?? source.tickets_path ?? "");
  if (!ticketsPath || ticketsPath === resolve(".")) fail("INVALID_RUN", "Run source.tickets_index_path is required.");
  const { workspace, backlog } = deriveWorkspaceAndBacklog(ticketsPath);
  const ticketPath = resolve(ticketPathOverride ?? state.ticket_path ?? state.source?.work_unit_path ?? state.work_unit_path ?? "");
  if (!ticketPath || ticketPath === resolve(".")) fail("INVALID_STATE", "State ticket_path or --ticket is required to generate a manifest.");
  const project = isMapping(run.project) ? run.project : {};
  const repository = resolve(project.root ?? run.project_root ?? "");
  if (!repository || repository === resolve(".")) fail("INVALID_RUN", "Run project.root is required to generate a manifest.");
  const target = isMapping(run.target) ? run.target : {};
  const targetBranch = project.target_branch ?? target.branch;
  const targetHead = project.target_head ?? target.head ?? project.current_head ?? target.expected_head ?? project.initial_head;
  const stateWorktree = isMapping(state.worktree) ? state.worktree : {};
  const worktreePath = resolve(stateWorktree.path ?? "");
  if (!worktreePath || worktreePath === resolve(".")) fail("INVALID_STATE", "State worktree.path is required to generate a manifest.");
  return {
    runDocument,
    run,
    runId,
    stateDocument,
    state,
    unitId,
    runDirectory: resolve(dirname(runPath)),
    ticketsPath,
    ticketPath,
    workspace,
    backlog,
    repository,
    targetBranch,
    targetHead,
    stateWorktree,
    worktreePath,
  };
}

function runDirectoryFromStatePath(statePath) {
  return dirname(dirname(dirname(resolve(statePath))));
}

function operationPathFor(runDirectory, operationId) {
  return join(runDirectory, "operations", `${operationId}.yaml`);
}

function defaultManifestPath(runDirectory, unitId, roleKey, attempt) {
  return join(runDirectory, "work-units", unitId, "manifests", `${roleKey}-attempt-${attempt}.yaml`);
}

function defaultHandoffPath(runDirectory, unitId, roleKey, attempt) {
  return join(runDirectory, "work-units", unitId, "handoffs", `${roleKey}-attempt-${attempt}.yaml`);
}

function defaultReportPath(runDirectory, unitId, roleKey, attempt) {
  return join(runDirectory, "work-units", unitId, roleDirectory(roleKey), `attempt-${attempt}`, "report.yaml");
}

function defaultEvidenceDirectory(runDirectory, unitId, roleKey, attempt) {
  return join(runDirectory, "work-units", unitId, "evidence", roleDirectory(roleKey), `attempt-${attempt}`);
}

async function assertArtifactPathInsideRun(path, runDirectory, field) {
  const canonicalPathValue = await canonicalPath(path);
  const canonicalRunDirectory = await canonicalPath(runDirectory);
  if (!pathIsInside(canonicalPathValue, canonicalRunDirectory)) {
    fail("PATH_OUTSIDE_RUN", `${field} must stay inside the run namespace: ${path}`, {
      field,
      actual: canonicalPathValue,
      expected: `path inside ${canonicalRunDirectory}`,
    });
  }
}

async function stateDependencySnapshot(statePath, state) {
  const dependencies = normalizeDependencies(state);
  const results = [];
  for (const dependency of dependencies) {
    if (!dependency.work_unit_id) {
      results.push({ ...dependency, actual_state: null });
      continue;
    }
    const path = dependency.state_path ? resolve(dependency.state_path) : join(dirname(dirname(statePath)), dependency.work_unit_id, "state.yaml");
    if (!(await pathExists(path))) {
      results.push({ ...dependency, state_path: path, actual_state: null });
      continue;
    }
    const document = await readYamlFile(path);
    results.push({
      work_unit_id: dependency.work_unit_id,
      state_path: path,
      state: actualStateFromDocument(document.value),
      actual_state: actualStateFromDocument(document.value),
      digest: document.digest,
    });
  }
  return results;
}

export async function buildExecutionManifest(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const statePath = resolve(options.state ?? "");
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required for manifest generation.");
  const context = await readTicketAndRunContext(runPath, statePath, options.ticket);
  const roleIssues = [];
  const roleKey = normalizeRole(options.role ?? "worker", "role", roleIssues);
  if (!roleKey) fail("INVALID_ROLE", `Unsupported role: ${options.role ?? "<missing>"}`, { errors: roleIssues });
  const attemptNumber = padAttempt(options.attempt ?? context.state.attempt_number ?? 1);
  const roleName = ROLE_NAMES[roleKey];
  const targetSnapshot = await gitSnapshot(context.repository);
  if (!context.targetBranch) fail("TARGET_BRANCH_REQUIRED", "Run admission did not retain a target branch checkpoint.", { field: "target.branch", actual: null, expected: "target branch" });
  if (!context.targetHead) fail("TARGET_HEAD_REQUIRED", "Run admission did not retain a target HEAD checkpoint.", { field: "target.head", actual: null, expected: "target commit" });
  if (targetSnapshot.dirty) fail("TARGET_DIRTY", `Target checkout is dirty: ${context.repository}`, { field: "target.dirty", actual: true, expected: false, status: targetSnapshot.status });
  if (targetSnapshot.branch !== context.targetBranch) {
    fail("TARGET_BRANCH_MISMATCH", `Target branch is ${targetSnapshot.branch}, expected ${context.targetBranch}.`, { field: "target.branch", actual: targetSnapshot.branch, expected: context.targetBranch });
  }
  const targetHeadRevision = context.targetHead ? await resolveGitRevision(context.repository, context.targetHead, "target.head") : targetSnapshot.head;
  if (context.targetHead && targetSnapshot.head !== targetHeadRevision) {
    fail("TARGET_HEAD_MISMATCH", `Target HEAD is ${targetSnapshot.head}, expected ${targetHeadRevision}.`, { field: "target.head", actual: targetSnapshot.head, expected: targetHeadRevision });
  }
  const worktreeSnapshot = await gitSnapshot(context.worktreePath);
  const missingWorktreeIdentity = ["branch", "baseline", "current_head"].filter((field) => !context.stateWorktree[field]);
  if (missingWorktreeIdentity.length > 0) fail("WORKTREE_IDENTITY_REQUIRED", `State is missing worktree identity: ${missingWorktreeIdentity.join(", ")}`, { field: "worktree", actual: missingWorktreeIdentity, expected: ["branch", "baseline", "current_head"] });
  const baselineRevision = await resolveGitRevision(context.worktreePath, context.stateWorktree.baseline, "worktree.baseline");
  const mergeBase = await runGit(context.worktreePath, ["merge-base", worktreeSnapshot.head, targetSnapshot.head]);
  if (baselineRevision !== mergeBase.stdout) {
    fail("BASELINE_MISMATCH", `Worktree baseline ${baselineRevision} differs from Git merge-base ${mergeBase.stdout}.`, { field: "worktree.baseline", actual: baselineRevision, expected: mergeBase.stdout });
  }
  const normalWorktree = expectedNormalWorktreePath(context.workspace, context.backlog, context.runId, context.unitId);
  const canonicalWorktreePath = await canonicalPath(context.worktreePath);
  const canonicalNormalWorktree = await canonicalPath(normalWorktree);
  if (canonicalWorktreePath !== canonicalNormalWorktree && !isRecoveryWorktree(canonicalWorktreePath, canonicalNormalWorktree)) {
    fail("CANONICAL_WORKTREE_PATH", `Worktree is outside the canonical squad namespace: ${context.worktreePath}`, { field: "worktree.path", actual: canonicalWorktreePath, expected: `${canonicalNormalWorktree} or recovery-<NNN> beneath it` });
  }
  const sourceDigest = await digestFile(context.ticketsPath);
  const expectedSourceDigest = context.run.source?.digest ?? context.run.source?.tickets_digest;
  if (expectedSourceDigest && sourceDigest !== String(expectedSourceDigest).toLowerCase()) {
    fail("SOURCE_DIGEST_MISMATCH", "Canonical tickets index changed since run admission.", { field: "source.tickets_digest", actual: sourceDigest, expected: expectedSourceDigest });
  }
  await assertTicketLinked(context.ticketsPath, context.unitId, context.ticketPath);
  const ticketDigest = await digestFile(context.ticketPath);
  const expectedTicketDigest = context.state.ticket_digest ?? context.state.source?.ticket_digest;
  if (expectedTicketDigest && ticketDigest !== String(expectedTicketDigest).toLowerCase()) {
    fail("TICKET_DIGEST_MISMATCH", "Selected ticket changed since state was recorded.", { field: "source.ticket_digest", actual: ticketDigest, expected: expectedTicketDigest });
  }
  const operationType = options.operation_type ?? roleOperationType(roleKey);
  const operationId = options.operation_id ?? `${context.runId}:${context.unitId}:${operationType}`;
  const attemptId = `${context.runId}:${context.unitId}:${roleKey}:attempt-${attemptNumber}`;
  const operationPath = operationPathFor(context.runDirectory, operationId);
  const manifestPath = resolve(options.output ?? defaultManifestPath(context.runDirectory, context.unitId, roleKey, attemptNumber));
  const handoffPath = resolve(options.handoff ?? defaultHandoffPath(context.runDirectory, context.unitId, roleKey, attemptNumber));
  const reportPath = resolve(options.report ?? defaultReportPath(context.runDirectory, context.unitId, roleKey, attemptNumber));
  const evidenceDirectory = resolve(options.evidence ?? defaultEvidenceDirectory(context.runDirectory, context.unitId, roleKey, attemptNumber));
  for (const [field, path] of [["artifact.state_path", statePath], ["artifact.manifest_path", manifestPath], ["artifact.handoff_path", handoffPath], ["artifact.operation_path", operationPath], ["artifact.report_path", reportPath], ["artifact.evidence_directory", evidenceDirectory]]) await assertArtifactPathInsideRun(path, context.runDirectory, field);
  const dependencies = await stateDependencySnapshot(statePath, context.state);
  const unfinishedDependencies = dependencies.filter((dependency) => dependency.actual_state !== "DONE");
  if (unfinishedDependencies.length > 0) {
    fail("DEPENDENCY_NOT_DONE", `Work unit ${context.unitId} cannot be dispatched with unfinished dependencies.`, { field: "dependencies", actual: unfinishedDependencies.map((dependency) => ({ work_unit_id: dependency.work_unit_id, state: dependency.actual_state })), expected: "all dependencies DONE" });
  }
  const currentState = actualStateFromDocument(context.state);
  if (!UNIT_STATES.includes(currentState)) fail("INVALID_STATE", `Unknown work-unit state: ${currentState ?? "<missing>"}`, { field: "state", actual: currentState ?? null, expected: UNIT_STATES });
  const reportDigest = await digestIfPresent(reportPath);
  const manifest = {
    schema_version: 1,
    kind: "squad-execution-manifest",
    immutable: true,
    manifest_id: `${context.runId}:${context.unitId}:${roleKey}:attempt-${attemptNumber}`,
    run_id: context.runId,
    work_unit_id: context.unitId,
    work_unit_type: context.state.work_unit_type ?? (context.unitId.startsWith("REM-") ? "REMEDIATION" : "TICKET"),
    role: roleName,
    attempt_number: Number(attemptNumber),
    attempt_id: attemptId,
    source: {
      tickets_index_path: context.ticketsPath,
      tickets_digest: sourceDigest,
      work_unit_path: context.ticketPath,
      ticket_digest: ticketDigest,
    },
    artifact: {
      run_dir: context.runDirectory,
      state_path: statePath,
      manifest_path: manifestPath,
      handoff_path: handoffPath,
      operation_path: operationPath,
      report_path: reportPath,
      evidence_directory: evidenceDirectory,
      report_digest: reportDigest,
    },
    target: {
      repository_root: targetSnapshot.root,
      repository_id: targetSnapshot.repository_id,
      branch: targetSnapshot.branch,
      head: targetSnapshot.head,
    },
    worktree: {
      path: context.worktreePath,
      relative_path: relative(context.workspace, context.worktreePath).split(sep).join("/"),
      repository_id: worktreeSnapshot.repository_id,
      branch: worktreeSnapshot.branch,
      baseline: baselineRevision,
      current_head: worktreeSnapshot.head,
      dirty: worktreeSnapshot.dirty,
    },
    state: {
      current: currentState,
      blocker: context.state.blocker ?? null,
    },
    operation: {
      id: operationId,
      type: operationType,
      attempt_id: attemptId,
      status: "PREPARED",
    },
    transition_template: {
      dispatch_from: currentState,
      dispatch_to: roleTransitionTarget(roleKey, currentState) ?? currentState,
      worker_acknowledgement: roleKey === "worker" ? "IMPLEMENTING" : null,
      reviewer_acknowledgement: roleKey === "reviewer" ? "REVIEWING" : null,
    },
    dependencies,
    decisions: {
      mode: options.mode ?? context.state.worker_mode ?? context.run.worker_mode ?? null,
      scope: options.scope ?? context.state.scope ?? null,
      authority: options.authority ?? context.run.authority ?? null,
    },
    generated_without_manual_identity_copy: true,
  };
  return { manifest, context, manifestPath, handoffPath };
}

async function writeImmutableYaml(filePath, value) {
  if (await pathExists(filePath)) {
    const existing = await readYamlFile(filePath);
    if (!deepEqual(existing.value, value)) {
      fail("IMMUTABLE_CONFLICT", `Immutable artifact already exists with different content: ${filePath}`, { file: filePath, existing_digest: existing.digest });
    }
    return { changed: false, file: existing.file, digest: existing.digest };
  }
  return createYamlFile(filePath, value);
}

export async function writeExecutionManifest(manifest, outputPath = manifest.artifact.manifest_path) {
  const result = await writeImmutableYaml(outputPath, manifest);
  return { ...result, manifest_path: resolve(outputPath) };
}

function handoffFromManifest(manifest, manifestDigest) {
  const roleKey = normalizeRole(manifest.role, "role", []);
  const reportPath = manifest.artifact.report_path;
  const reportDigest = manifest.artifact.report_digest ?? null;
  const reportExists = reportDigest !== null;
  const state = manifest.state ?? {};
  const current = state.current;
  const handoff = {
    schema_version: 1,
    kind: "squad-handoff",
    role: ROLE_NAMES[roleKey],
    run_id: manifest.run_id,
    work_unit_id: manifest.work_unit_id,
    attempt_id: manifest.attempt_id,
    operation_id: manifest.operation.id,
    source: {
      tickets_index_path: manifest.source.tickets_index_path,
      tickets_digest: manifest.source.tickets_digest,
      work_unit_path: manifest.source.work_unit_path,
      ticket_digest: manifest.source.ticket_digest,
    },
    artifact: {
      run_dir: manifest.artifact.run_dir,
      state_path: manifest.artifact.state_path,
      manifest_path: manifest.artifact.manifest_path,
      handoff_path: manifest.artifact.handoff_path,
      operation_path: manifest.artifact.operation_path,
      report_path: manifest.artifact.report_path,
      evidence_directory: manifest.artifact.evidence_directory,
    },
    target: {
      repository_root: manifest.target.repository_root,
      repository_id: manifest.target.repository_id,
      branch: manifest.target.branch,
      head: manifest.target.head,
    },
    worktree: {
      path: manifest.worktree.path,
      relative_path: manifest.worktree.relative_path,
      repository_id: manifest.worktree.repository_id,
      branch: manifest.worktree.branch,
      baseline: manifest.worktree.baseline,
      current_head: manifest.worktree.current_head,
    },
    state: {
      current,
      expected: current,
    },
    dependencies: (manifest.dependencies ?? []).map((dependency) => ({
      work_unit_id: dependency.work_unit_id,
      state_path: dependency.state_path,
      state: dependency.actual_state ?? dependency.state,
    })),
    operation: {
      id: manifest.operation.id,
      type: manifest.operation.type,
      attempt_id: manifest.operation.attempt_id,
    },
    report: {
      path: reportPath,
      digest: reportDigest,
      expected: reportExists ? "EXISTING" : "CREATE",
    },
    evidence: { directory: manifest.artifact.evidence_directory },
    decisions: manifest.decisions ?? {},
    manifest: {
      path: manifest.artifact.manifest_path,
      digest: manifestDigest,
    },
  };
  if (roleKey === "reviewer") {
    handoff.implementation_revision = manifest.worktree.current_head;
  }
  return handoff;
}

export async function generateHandoffFromManifest(manifestPath, outputPath = undefined) {
  const document = await readYamlFile(manifestPath);
  const manifest = document.value;
  if (!isMapping(manifest) || manifest.kind !== "squad-execution-manifest" || manifest.schema_version !== 1) {
    fail("INVALID_MANIFEST", `Not a squad execution manifest: ${manifestPath}`);
  }
  const handoffPath = resolve(outputPath ?? manifest.artifact.handoff_path);
  const handoff = handoffFromManifest({ ...manifest, artifact: { ...manifest.artifact, manifest_path: resolve(manifestPath), handoff_path: handoffPath } }, document.digest);
  const result = await writeImmutableYaml(handoffPath, handoff);
  return { ...result, handoff_path: handoffPath, handoff };
}

async function updateOperation(operationPath, expectedDigest, sets) {
  return updateYamlFile(operationPath, expectedDigest, sets);
}

async function createDispatchOperation(manifest, { status = "PREPARED", stateBefore = manifest.state.current, stateAfter = manifest.state.current } = {}) {
  const operationPath = manifest.artifact.operation_path;
  const operation = {
    schema_version: 1,
    operation_id: manifest.operation.id,
    attempt_id: manifest.attempt_id,
    type: manifest.operation.type,
    status,
    job_id: null,
    input: {
      run_id: manifest.run_id,
      work_unit_id: manifest.work_unit_id,
      manifest_path: manifest.artifact.manifest_path,
      handoff_path: manifest.artifact.handoff_path,
      state_before: stateBefore,
      state_after: stateAfter,
      target_head: manifest.target.head,
      source_revision: manifest.worktree.current_head,
    },
    result: null,
  };
  let result;
  if (await pathExists(operationPath)) {
    const existing = await readYamlFile(operationPath);
    const existingValue = existing.value;
    if (existingValue.operation_id !== operation.operation_id || existingValue.attempt_id !== operation.attempt_id || existingValue.type !== operation.type) {
      fail("OPERATION_IDENTITY_CONFLICT", `Operation path is already owned by another attempt: ${operationPath}`, { field: "operation_path", actual: { operation_id: existingValue.operation_id, attempt_id: existingValue.attempt_id, type: existingValue.type }, expected: { operation_id: operation.operation_id, attempt_id: operation.attempt_id, type: operation.type } });
    }
    if (existingValue.status !== "PREPARED") {
      fail("OPERATION_NOT_DISPATCHABLE", `Existing operation ${existingValue.operation_id} is ${existingValue.status}; create a fresh attempt or reconcile it before preparing again.`, { operation_path: operationPath, status: existingValue.status, expected: "PREPARED" });
    }
    for (const [field, expected] of [["input.manifest_path", operation.input.manifest_path], ["input.handoff_path", operation.input.handoff_path], ["input.target_head", operation.input.target_head], ["input.source_revision", operation.input.source_revision]]) {
      if (existingValue[field.split(".")[0]]?.[field.split(".")[1]] !== expected) fail("OPERATION_INPUT_CONFLICT", `Existing operation input differs at ${field}: ${operationPath}`, { field, actual: existingValue[field.split(".")[0]]?.[field.split(".")[1]] ?? null, expected });
    }
    result = { changed: false, file: existing.file, digest: existing.digest };
  } else {
    result = await writeImmutableYaml(operationPath, operation);
  }
  const document = await readYamlFile(operationPath);
  return { path: operationPath, digest: document.digest, value: document.value, write: result };
}

export async function commitUnitTransition({ statePath, workUnitId, from, to, reason, operationId = null, extraSets = [], allowUnresolvedOperation = false }) {
  if (!workUnitId) fail("MISSING_ARGUMENT", "workUnitId is required for a transition.");
  const resolvedStatePath = resolve(statePath);
  if (basename(resolvedStatePath) !== "state.yaml" || basename(dirname(resolvedStatePath)) !== workUnitId || basename(dirname(dirname(resolvedStatePath))) !== "work-units") {
    fail("INVALID_STATE_PATH", `State path is outside the canonical work-unit layout: ${resolvedStatePath}`, { field: "state_path", actual: resolvedStatePath, expected: "<run-dir>/work-units/<work-unit-id>/state.yaml" });
  }
  if (!UNIT_STATES.includes(from) || !UNIT_STATES.includes(to)) fail("INVALID_STATE", `Unknown transition: ${from} -> ${to}`, { from, to, expected: UNIT_STATES });
  if (!LEGAL_UNIT_TRANSITIONS[from].includes(to)) {
    fail("ILLEGAL_TRANSITION", `Illegal work-unit transition: ${from} -> ${to}`, { from, to, legal_to: LEGAL_UNIT_TRANSITIONS[from] });
  }
  const stateDocument = await readYamlFile(resolvedStatePath);
  const state = stateDocument.value;
  const actualUnit = normalizeUnitId(state);
  const actualState = actualStateFromDocument(state);
  if (actualUnit !== workUnitId) fail("WORK_UNIT_ID_MISMATCH", `State belongs to ${actualUnit ?? "<missing>"}, not ${workUnitId}.`, { field: "work_unit_id", actual: actualUnit ?? null, expected: workUnitId });
  if (actualState !== from) fail("TRANSITION_SOURCE_MISMATCH", `State is ${actualState}, not ${from}.`, { field: "from", actual: actualState, expected: from });
  if (!asString(reason)) fail("MISSING_ARGUMENT", "--reason is required for a transition.", { field: "reason", actual: reason ?? null, expected: "non-empty reason" });
  const runId = normalizeRunId(state);
  if (!runId) fail("INVALID_STATE", "State must contain run_id for a transition.");
  requireSafeSegment(runId, "run_id");
  requireSafeSegment(workUnitId, "work_unit_id");
  const runDirectory = runDirectoryFromStatePath(resolvedStatePath);
  if (operationId) {
    const operationPrefix = `${runId}:${workUnitId}:`;
    const operationAction = operationId.startsWith(operationPrefix) ? operationId.slice(operationPrefix.length) : "";
    if (!operationId.startsWith(operationPrefix) || operationId.split(":").length !== 3 || !/^[A-Z][A-Z0-9_]*$/.test(operationAction)) fail("INVALID_OPERATION_ID", `Invalid transition operation ID: ${operationId}`, { field: "operation_id", actual: operationId, expected: `${runId}:${workUnitId}:<UPPER_SNAKE_ACTION>` });
    const operationPath = operationPathFor(runDirectory, operationId);
    if (!(await pathExists(operationPath))) fail("OPERATION_NOT_FOUND", `Transition trigger operation is not durable: ${operationId}`, { field: "operation_id", actual: operationId, expected: "existing operation ledger" });
    const operationDocument = await readYamlFile(operationPath);
    if (operationDocument.value.operation_id !== operationId) fail("OPERATION_ID_MISMATCH", "Transition trigger does not match its operation file.", { field: "operation_id", actual: operationDocument.value.operation_id, expected: operationId });
    if (!OPERATION_STATES.includes(operationDocument.value.status)) fail("INVALID_OPERATION_STATUS", `Transition trigger operation has invalid status: ${operationDocument.value.status}`, { status: operationDocument.value.status, expected: OPERATION_STATES });
    if (!allowUnresolvedOperation && ["UNKNOWN", "RECONCILING"].includes(operationDocument.value.status)) fail("OPERATION_REQUIRES_RECONCILIATION", `Transition trigger operation ${operationId} is ${operationDocument.value.status}.`, { operation_id: operationId, status: operationDocument.value.status, expected: "conclusive operation status" });
  }
  const transitionDirectory = join(runDirectory, "transitions");
  await mkdir(transitionDirectory, { recursive: true });
  const existing = await readTransitionFiles(runDirectory);
  const prefix = `TR-${runId}-${workUnitId}-`;
  const escapedPrefix = prefix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const sequence = existing.reduce((max, item) => {
    const match = item.value?.transition_id?.match(new RegExp(`^${escapedPrefix}([0-9]{4})$`));
    return match ? Math.max(max, Number(match[1])) : max;
  }, 0) + 1;
  const transitionId = `${prefix}${String(sequence).padStart(4, "0")}`;
  const transitionPath = join(transitionDirectory, `${transitionId}.yaml`);
  const prepared = {
    schema_version: 1,
    transition_id: transitionId,
    entity: workUnitId,
    from,
    to,
    status: "PREPARED",
    reason,
    source: {
      state_path: resolvedStatePath,
      state_digest: stateDocument.digest,
    },
    trigger: operationId ? { operation_id: operationId } : null,
    checkpoint_id: `CP-${transitionId}`,
  };
  const createResult = await writeImmutableYaml(transitionPath, prepared);
  const preparedDocument = await readYamlFile(transitionPath);
  const committing = await updateYamlFile(transitionPath, preparedDocument.digest, [
    { pointer: "/status", value: "COMMITTING" },
  ]);
  try {
    const currentStateDocument = await readYamlFile(resolvedStatePath);
    if (actualStateFromDocument(currentStateDocument.value) !== from) {
      fail("TRANSITION_SOURCE_MISMATCH", "State changed before transition commit.", { field: "from", actual: actualStateFromDocument(currentStateDocument.value), expected: from });
    }
    const history = Array.isArray(currentStateDocument.value.transition_history) ? [...currentStateDocument.value.transition_history] : [];
    history.push({ transition_id: transitionId, from, to, reason });
    const sets = [
      { pointer: "/state", value: to },
      { pointer: "/last_transition_id", value: transitionId },
      { pointer: "/transition_history", value: history },
      ...extraSets,
    ];
    const stateAfter = await updateYamlFile(resolvedStatePath, currentStateDocument.digest, sets);
    const committingDocument = await readYamlFile(transitionPath);
    const committed = await updateYamlFile(transitionPath, committingDocument.digest, [
      { pointer: "/status", value: "COMMITTED" },
      { pointer: "/committed_state_digest", value: stateAfter.digest },
    ]);
    const finalState = await readYamlFile(resolvedStatePath);
    const finalTransition = await readYamlFile(transitionPath);
    if (actualStateFromDocument(finalState.value) !== to || finalTransition.value.status !== "COMMITTED") {
      fail("TRANSITION_VERIFY_FAILED", `Transition ${transitionId} did not verify after commit.`, { transition_id: transitionId, state: actualStateFromDocument(finalState.value), transition_status: finalTransition.value.status, expected_state: to, expected_transition_status: "COMMITTED" });
    }
    return {
      transition_id: transitionId,
      transition_path: transitionPath,
      status: "COMMITTED",
      state_digest: finalState.digest,
      transition_digest: finalTransition.digest,
      changed: createResult.changed || committing.changed || committed.changed,
    };
  } catch (error) {
    const details = error.details ?? {};
    fail("TRANSITION_INCOMPLETE", `Transition ${transitionId} requires reconciliation: ${error.message}`, {
      transition_id: transitionId,
      transition_path: transitionPath,
      state_path: resolvedStatePath,
      ...details,
    });
  }
}

async function allRunArtifacts(runPath) {
  const runDocument = await readRunDocument(runPath);
  const runDirectory = dirname(runPath);
  return {
    runDocument,
    runDirectory,
    units: await readWorkUnits(runDirectory),
    operations: await readOperationFiles(runDirectory),
    transitions: await readTransitionFiles(runDirectory),
  };
}

async function sourceIndexChecks(run, checks, issues) {
  const source = isMapping(run.source) ? run.source : {};
  const ticketsPath = source.tickets_index_path ?? source.tickets_path;
  if (!ticketsPath) {
    issues.push(issue("source.tickets_index_path", "REQUIRED_FIELD", null, "canonical tickets.md path", "Run source is missing its canonical ticket index."));
    return null;
  }
  const absolute = resolve(ticketsPath);
  if (!(await requireExistingPath(absolute, "source.tickets_index_path", issues))) return absolute;
  const actualDigest = await digestFile(absolute);
  const expectedDigest = source.digest ?? source.tickets_digest;
  if (!expectedDigest) {
    issues.push(issue("source.tickets_digest", "REQUIRED_DIGEST", null, "sha256:<64 hex characters>", "Run admission must retain the canonical tickets index digest."));
  } else {
    const normalized = normalizeDigest(String(expectedDigest), "source.tickets_digest", issues);
    if (normalized) {
      check(checks, "source.tickets_digest", actualDigest, normalized);
      if (actualDigest !== normalized) issues.push(issue("source.tickets_digest", "DIGEST_MISMATCH", actualDigest, normalized, "Canonical tickets index changed."));
    }
  }
  return absolute;
}

function graphCycleIssues(units, issues) {
  const byId = new Map();
  for (const unit of units) {
    if (unit.value) byId.set(normalizeUnitId(unit.value), unit);
  }
  const visiting = new Set();
  const visited = new Set();
  const visit = (id, chain = []) => {
    if (visiting.has(id)) {
      issues.push(issue("dependencies", "DEPENDENCY_CYCLE", [...chain, id], "acyclic dependency graph", "The work-unit dependency graph contains a cycle."));
      return;
    }
    if (visited.has(id)) return;
    visiting.add(id);
    const unit = byId.get(id);
    for (const dependency of normalizeDependencies(unit?.value ?? {})) if (dependency.work_unit_id && byId.has(dependency.work_unit_id)) visit(dependency.work_unit_id, [...chain, id]);
    visiting.delete(id);
    visited.add(id);
  };
  for (const id of byId.keys()) visit(id);
}

async function validateWorktreeState(unit, workspace, backlog, runId, issues, targetSnapshot = null) {
  const state = unit.value;
  const worktree = isMapping(state.worktree) ? state.worktree : {};
  const currentState = actualStateFromDocument(state);
  if (!worktree.path) {
    if (["READY", "ASSIGNED", "IMPLEMENTING", "AWAITING_REVIEW", "REVIEWING", "FIXING", "INTEGRATING"].includes(currentState)) issues.push(issue(`${unit.path}:worktree.path`, "REQUIRED_FIELD", null, "canonical Git worktree path", "An active work unit must retain its isolated worktree identity."));
    return null;
  }
  const normal = expectedNormalWorktreePath(workspace, backlog, runId, normalizeUnitId(state));
  const path = resolve(worktree.path);
  const canonicalPathValue = await canonicalPath(path);
  const canonicalNormal = await canonicalPath(normal);
  if (canonicalPathValue !== canonicalNormal && !isRecoveryWorktree(canonicalPathValue, canonicalNormal)) {
    issues.push(issue(`${unit.path}:worktree.path`, "CANONICAL_WORKTREE_PATH", canonicalPathValue, `${canonicalNormal} or recovery-<NNN> beneath it`, "The worktree is outside the canonical workspace namespace."));
  }
  if (!(await pathExists(path))) {
    issues.push(issue(`${unit.path}:worktree.path`, "PATH_NOT_FOUND", path, "existing Git worktree", "The recorded worktree does not exist."));
    return null;
  }
  try {
    const snapshot = await gitSnapshot(path);
    if (snapshot.dirty && ["READY", "AWAITING_REVIEW"].includes(currentState)) issues.push(issue(`${unit.path}:worktree.dirty`, "WORKTREE_DIRTY", true, false, "A fresh worker or reviewer dispatch requires a clean worktree."));
    if (!worktree.repository_id) issues.push(issue(`${unit.path}:worktree.repository_id`, "REQUIRED_FIELD", null, "shared Git repository identity", "The worktree record must retain its repository identity."));
    else if (snapshot.repository_id !== await canonicalPath(worktree.repository_id)) issues.push(issue(`${unit.path}:worktree.repository_id`, "REPOSITORY_ID_MISMATCH", snapshot.repository_id, await canonicalPath(worktree.repository_id), "The recorded worktree repository identity is stale."));
    if (targetSnapshot && snapshot.repository_id !== targetSnapshot.repository_id) issues.push(issue(`${unit.path}:worktree.repository_id`, "WORKTREE_REPOSITORY_MISMATCH", snapshot.repository_id, targetSnapshot.repository_id, "The worktree is not derived from the run target repository."));
    if (!worktree.branch) issues.push(issue(`${unit.path}:worktree.branch`, "REQUIRED_FIELD", null, "worktree branch", "The worktree record must retain its branch."));
    else if (snapshot.branch !== worktree.branch) issues.push(issue(`${unit.path}:worktree.branch`, "BRANCH_MISMATCH", snapshot.branch, worktree.branch, "The recorded worktree branch is stale."));
    let currentRevision = snapshot.head;
    if (worktree.current_head) {
      const expected = await resolveGitRevision(path, worktree.current_head, `${unit.path}.worktree.current_head`);
      currentRevision = expected;
      if (snapshot.head !== expected) issues.push(issue(`${unit.path}:worktree.current_head`, "CURRENT_HEAD_MISMATCH", snapshot.head, expected, "The recorded worktree HEAD is stale."));
    } else {
      issues.push(issue(`${unit.path}:worktree.current_head`, "REQUIRED_FIELD", null, "current Git HEAD", "The worktree record must retain current_head."));
    }
    if (worktree.baseline) {
      try {
        const baseline = await resolveGitRevision(path, worktree.baseline, `${unit.path}.worktree.baseline`);
        const targetHead = targetSnapshot?.head;
        if (targetHead) {
          const mergeBase = await runGit(path, ["merge-base", currentRevision, targetHead]);
          if (baseline !== mergeBase.stdout) issues.push(issue(`${unit.path}:worktree.baseline`, "BASELINE_MERGE_BASE_MISMATCH", baseline, mergeBase.stdout, "The recorded baseline is not the Git merge-base of the worktree and target HEAD."));
        }
      } catch (error) {
        issues.push(issue(`${unit.path}:worktree.baseline`, error.code ?? "BASELINE_VALIDATION_FAILED", worktree.baseline, "resolvable baseline and merge-base", error.message));
      }
    } else {
      issues.push(issue(`${unit.path}:worktree.baseline`, "REQUIRED_FIELD", null, "Git baseline", "The worktree record must retain its baseline."));
    }
    return snapshot;
  } catch (error) {
    issues.push(issue(`${unit.path}:worktree`, error.code ?? "GIT_VALIDATION_FAILED", error.message, "valid Git worktree", "The recorded worktree could not be inspected."));
    return null;
  }
}

export async function preflightRun(runPath) {
  const artifacts = await allRunArtifacts(resolve(runPath));
  const run = artifacts.runDocument.value;
  const runId = artifacts.runDocument.run_id;
  const issues = [];
  const checks = [];
  const ticketsPath = await sourceIndexChecks(run, checks, issues);
  let workspace = null;
  let backlog = null;
  if (ticketsPath) {
    try {
      ({ workspace, backlog } = deriveWorkspaceAndBacklog(ticketsPath));
    } catch (error) {
      issues.push(issue("source.tickets_index_path", error.code ?? "INVALID_SOURCE_PATH", ticketsPath, "canonical tickets.md path", error.message));
    }
  }
  const project = isMapping(run.project) ? run.project : {};
  const repositoryPath = project.root ?? run.project_root;
  let targetSnapshot = null;
  if (!repositoryPath) issues.push(issue("project.root", "REQUIRED_FIELD", null, "Git repository path", "Run project root is required."));
  else {
    try {
      targetSnapshot = await gitSnapshot(repositoryPath);
    } catch (error) {
      issues.push(issue("project.root", error.code ?? "GIT_VALIDATION_FAILED", error.message, "valid Git repository", "Target Git identity could not be validated."));
    }
    if (targetSnapshot) {
      const expectedBranch = project.target_branch ?? run.target?.branch;
      if (expectedBranch) addExpectedIssue(issues, "project.target_branch", targetSnapshot.branch, expectedBranch, "TARGET_BRANCH_MISMATCH", "The target branch changed." );
      else issues.push(issue("project.target_branch", "REQUIRED_FIELD", null, "target branch checkpoint", "Preflight needs a target branch checkpoint."));
      const expectedHead = project.target_head ?? run.target?.head ?? run.target?.expected_head ?? project.initial_head;
      if (expectedHead) {
        try {
          const resolved = await resolveGitRevision(repositoryPath, expectedHead, "project.target_head");
          addExpectedIssue(issues, "project.target_head", targetSnapshot.head, resolved, "TARGET_HEAD_MISMATCH", "The target branch HEAD changed." );
        } catch (error) {
          issues.push(issue("project.target_head", error.code ?? "REVISION_NOT_FOUND", expectedHead, "resolvable target commit", error.message));
        }
      } else {
        issues.push(issue("project.target_head", "REQUIRED_FIELD", null, "target HEAD checkpoint", "Preflight needs a target HEAD checkpoint to detect drift."));
      }
      if (targetSnapshot.dirty) issues.push(issue("project.target.dirty", "TARGET_DIRTY", true, false, "The target checkout must be clean during squad execution."));
      check(checks, "target.repository_root", targetSnapshot.root, await canonicalPath(repositoryPath));
    }
  }
  const unitIds = new Set();
  const ready = [];
  for (const unit of artifacts.units) {
    if (unit.error) {
      issues.push(issue(unit.path, unit.error.code, unit.error.message, "readable state.yaml", "A work-unit state could not be read."));
      continue;
    }
    const state = unit.value;
    const id = normalizeUnitId(state);
    let current;
    try {
      current = actualStateFromDocument(state);
    } catch (error) {
      issues.push(issue(`${unit.path}:state`, error.code ?? "AMBIGUOUS_STATE", state.state ?? state.lifecycle_state ?? null, "one consistent lifecycle state", error.message));
      current = state.state ?? state.lifecycle_state;
    }
    if (!id) issues.push(issue(`${unit.path}:work_unit_id`, "REQUIRED_FIELD", null, "work unit ID", "Each work unit needs work_unit_id."));
    else if (unitIds.has(id)) issues.push(issue(`${unit.path}:work_unit_id`, "DUPLICATE_ID", id, "unique work unit ID", "Work unit IDs must be unique."));
    else unitIds.add(id);
    if (id && unit.directory_id !== id) issues.push(issue(`${unit.path}:work_unit_id`, "STATE_DIRECTORY_MISMATCH", id, unit.directory_id, "The state directory name must equal work_unit_id."));
    const stateRunId = normalizeRunId(state);
    if (stateRunId !== runId) issues.push(issue(`${unit.path}:run_id`, "RUN_ID_MISMATCH", stateRunId ?? null, runId, "The work-unit state belongs to another run."));
    if (!UNIT_STATES.includes(current)) issues.push(issue(`${unit.path}:state`, "INVALID_STATE", current ?? null, UNIT_STATES, "The work-unit state is not legal."));
    if (state.state && state.lifecycle_state && state.state !== state.lifecycle_state) issues.push(issue(`${unit.path}:lifecycle_state`, "AMBIGUOUS_STATE", state.lifecycle_state, state.state, "state and lifecycle_state must agree."));
    if (id && !state.ticket_path) issues.push(issue(`${unit.path}:ticket_path`, "REQUIRED_FIELD", null, "linked ticket path", "Each work unit must identify its canonical ticket or REM record."));
    if (ticketsPath && id && state.ticket_path) {
      const ticketPath = resolve(state.ticket_path);
      try {
        await assertTicketLinked(ticketsPath, id, ticketPath, issues);
        if (await pathExists(ticketPath)) {
          const actualTicketDigest = await digestFile(ticketPath);
          const expectedTicketDigest = state.ticket_digest;
          if (!expectedTicketDigest) issues.push(issue(`${unit.path}:ticket_digest`, "REQUIRED_DIGEST", null, "sha256:<64 hex characters>", "Each work unit must retain its ticket digest."));
          else {
            const normalizedTicketDigest = normalizeDigest(String(expectedTicketDigest), `${unit.path}:ticket_digest`, issues);
            if (normalizedTicketDigest && actualTicketDigest !== normalizedTicketDigest) issues.push(issue(`${unit.path}:ticket_digest`, "DIGEST_MISMATCH", actualTicketDigest, normalizedTicketDigest, "The ticket changed after the durable state snapshot."));
          }
        }
      } catch (error) { issues.push(issue(`${unit.path}:ticket_path`, error.code ?? "TICKET_INDEX_READ_FAILED", error.message, `linked ${id} record`, "The work-unit ticket link could not be checked.")); }
    }
    for (const [index, dependency] of normalizeDependencies(state).entries()) {
      const dependencyUnit = artifacts.units.find((candidate) => normalizeUnitId(candidate.value ?? {}) === dependency.work_unit_id);
      if (!dependencyUnit) issues.push(issue(`${unit.path}:dependencies[${index}]`, "DEPENDENCY_NOT_FOUND", dependency.work_unit_id ?? null, "work unit in run", "The dependency is not present in this run."));
      else {
        let dependencyState;
        try { dependencyState = actualStateFromDocument(dependencyUnit.value); } catch (error) {
          dependencyState = dependencyUnit.value.state ?? dependencyUnit.value.lifecycle_state;
          issues.push(issue(`${unit.path}:dependencies[${index}].state`, error.code ?? "AMBIGUOUS_STATE", dependencyState, "one consistent lifecycle state", error.message));
        }
        if (dependency.state && dependency.state !== dependencyState) issues.push(issue(`${unit.path}:dependencies[${index}].state`, "DEPENDENCY_STATE_MISMATCH", dependencyState, dependency.state, "The recorded dependency state is stale."));
        if (current === "READY" && dependencyState !== "DONE") issues.push(issue(`${unit.path}:dependencies[${index}]`, "DEPENDENCY_NOT_DONE", dependencyState, "DONE", "READY work cannot be dispatched until every dependency is DONE."));
      }
    }
    if (current === "READY") ready.push(id);
    if (workspace && backlog && id) {
      try { await validateWorktreeState(unit, workspace, backlog, runId, issues, targetSnapshot); }
      catch (error) { issues.push(issue(`${unit.path}:worktree`, error.code ?? "WORKTREE_VALIDATION_FAILED", error.message, "valid worktree state", "The worktree state could not be checked.")); }
    }
    if (state.handoff_path && await pathExists(state.handoff_path)) {
      try {
        const handoff = await validateHandoffFile(state.handoff_path, { throwOnInvalid: false });
        if (!handoff.valid) issues.push(...handoff.errors.map((entry) => ({ ...entry, field: `${unit.path}:handoff.${entry.field}` })));
      } catch (error) {
        issues.push(issue(`${unit.path}:handoff_path`, error.code ?? "HANDOFF_READ_FAILED", error.message, "valid handoff", "The recorded handoff could not be validated."));
      }
    }
  }
  graphCycleIssues(artifacts.units, issues);
  for (const operation of artifacts.operations) {
    if (operation.error) issues.push(issue(operation.path, operation.error.code, operation.error.message, "readable operation", "An operation ledger entry could not be read."));
    else {
      const value = operation.value;
      if (!OPERATION_STATES.includes(value.status)) issues.push(issue(`${operation.path}:status`, "INVALID_OPERATION_STATUS", value.status ?? null, OPERATION_STATES, "Operation status is not legal."));
      if (["UNKNOWN", "RECONCILING"].includes(value.status)) issues.push(issue(`${operation.path}:status`, "UNRESOLVED_OPERATION", value.status, "conclusive operation status", "A run with an unresolved side effect cannot dispatch new work."));
      if (value.status === "FAILED") issues.push(issue(`${operation.path}:status`, "FAILED_OPERATION", value.status, "SUCCEEDED", "A failed side effect requires recovery before new dispatch."));
      if (!value.operation_id) issues.push(issue(`${operation.path}:operation_id`, "REQUIRED_FIELD", null, "operation identity", "Every operation needs operation_id."));
      else {
        const operationUnitId = value.work_unit_id ?? value.input?.work_unit_id;
        const operationPrefix = `${runId}:${operationUnitId ?? ""}:`;
        const operationAction = value.operation_id.startsWith(operationPrefix) ? value.operation_id.slice(operationPrefix.length) : "";
        if (value.operation_id.split(":").length !== 3 || !operationUnitId || !operationAction || !/^[A-Z][A-Z0-9_]*$/.test(operationAction)) issues.push(issue(`${operation.path}:operation_id`, "INVALID_OPERATION_ID", value.operation_id, `${runId}:<work-unit-id>:<UPPER_SNAKE_ACTION>`, "Operation IDs must use the canonical naming format."));
      }
      if (value.input?.run_id && value.input.run_id !== runId) issues.push(issue(`${operation.path}:input.run_id`, "RUN_ID_MISMATCH", value.input.run_id, runId, "The operation belongs to another run."));
      if (value.input?.work_unit_id && !artifacts.units.some((unit) => normalizeUnitId(unit.value ?? {}) === value.input.work_unit_id)) issues.push(issue(`${operation.path}:input.work_unit_id`, "WORK_UNIT_ID_MISMATCH", value.input.work_unit_id, "work unit in run", "The operation references a work unit outside this run."));
    }
  }
  for (const transition of artifacts.transitions) {
    if (transition.error) issues.push(issue(transition.path, transition.error.code, transition.error.message, "readable transition", "A transition ledger entry could not be read."));
    else {
      const value = transition.value;
      if (!TRANSITION_STATES.includes(value.status)) issues.push(issue(`${transition.path}:status`, "INVALID_TRANSITION_STATUS", value.status ?? null, TRANSITION_STATES, "Transition status is not legal."));
      if (value.status !== "COMMITTED" && value.status !== "ABORTED") issues.push(issue(`${transition.path}:status`, "UNCOMMITTED_TRANSITION", value.status ?? null, ["COMMITTED", "ABORTED"], "A run with an uncommitted transition cannot dispatch new work."));
      if (!value.entity) issues.push(issue(`${transition.path}:entity`, "REQUIRED_FIELD", null, "work unit ID", "Every transition must name its entity."));
      else if (!artifacts.units.some((unit) => normalizeUnitId(unit.value ?? {}) === value.entity)) issues.push(issue(`${transition.path}:entity`, "ENTITY_NOT_FOUND", value.entity, "work unit in run", "The transition entity is not present in this run."));
      validateTransitionShape({ from: value.from, to: value.to }, value.from, issues, `${transition.path}:transition`);
    }
  }
  return {
    valid: issues.length === 0,
    run_id: runId,
    run_path: resolve(runPath),
    state: run.state ?? run.status ?? null,
    target: targetSnapshot ? { branch: targetSnapshot.branch, head: targetSnapshot.head, dirty: targetSnapshot.dirty } : null,
    ready,
    work_unit_count: artifacts.units.length,
    operation_count: artifacts.operations.length,
    transition_count: artifacts.transitions.length,
    checks,
    issues,
  };
}

export async function prepareDispatch(options) {
  const runPath = await resolveRunPath(options, options.runId);
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required for dispatch preparation.");
  const preflight = await preflightRun(runPath);
  if (!preflight.valid) fail("PREFLIGHT_FAILED", `Run preflight failed before dispatch preparation: ${runPath}`, { run_id: preflight.run_id, issues: preflight.issues });
  const roleIssues = [];
  const roleKey = normalizeRole(options.role ?? "worker", "role", roleIssues);
  if (!roleKey) fail("INVALID_ROLE", "Unsupported dispatch role.", { errors: roleIssues });
  const initial = await buildExecutionManifest({ ...options, output: options.output, handoff: options.handoff, role: roleKey });
  const current = initial.manifest.state.current;
  if (initial.manifest.worktree.dirty && ((roleKey === "worker" && current === "READY") || (roleKey === "reviewer" && current === "AWAITING_REVIEW"))) {
    fail("WORKTREE_DIRTY", `Cannot dispatch a fresh ${roleKey} attempt from a dirty worktree.`, { field: "worktree.dirty", actual: true, expected: false, worktree: initial.manifest.worktree.path, next_action: "CLASSIFY_OR_RECONCILE_WORKTREE" });
  }
  const next = dispatchTargetState(roleKey, current);
  const manifest = initial.manifest;
  manifest.transition_template.dispatch_to = next;
  const operation = await createDispatchOperation(manifest, { stateBefore: current, stateAfter: next });
  if (next !== current) {
    try {
      await commitUnitTransition({
        statePath: manifest.artifact.state_path,
        workUnitId: manifest.work_unit_id,
        from: current,
        to: next,
        reason: `Prepared ${roleKey} dispatch from one canonical execution manifest.`,
        operationId: manifest.operation.id,
      });
    } catch (error) {
      try {
        const currentOperation = await readYamlFile(operation.path);
        await updateOperation(operation.path, currentOperation.digest, [
          { pointer: "/status", value: "UNKNOWN" },
          { pointer: "/reconciliation_required", value: true },
        ]);
      } catch {
        // Preserve the original transition failure; the operation remains durable
        // and must be reconciled by the host.
      }
      throw error;
    }
  }
  const finalManifestResult = await buildExecutionManifest({ ...options, output: initial.manifestPath, handoff: initial.handoffPath, role: roleKey, attempt: manifest.attempt_number });
  const writtenManifest = await writeExecutionManifest(finalManifestResult.manifest, finalManifestResult.manifestPath);
  const handoffResult = await generateHandoffFromManifest(finalManifestResult.manifestPath, finalManifestResult.handoffPath);
  const validation = await validateHandoffFile(handoffResult.handoff_path, { throwOnInvalid: false });
  if (!validation.valid) {
    try {
      const currentOperation = await readYamlFile(operation.path);
      await updateOperation(operation.path, currentOperation.digest, [
        { pointer: "/status", value: "UNKNOWN" },
        { pointer: "/reconciliation_required", value: true },
        { pointer: "/validation_errors", value: validation.errors },
      ]);
    } catch {
      // Keep the primary validation result and durable artifacts for reconciliation.
    }
    fail("HANDOFF_INVALID", `Generated handoff failed validation: ${handoffResult.handoff_path}`, { errors: validation.errors });
  }
  const finalOperation = await readYamlFile(operation.path);
  const operationAfter = await updateOperation(operation.path, finalOperation.digest, [
    { pointer: "/result", value: { ready_to_dispatch: true, handoff_path: handoffResult.handoff_path, handoff_digest: validation.digest, manifest_path: finalManifestResult.manifestPath, manifest_digest: writtenManifest.digest } },
  ]);
  const stateAfterOperation = await readYamlFile(manifest.artifact.state_path);
  const stateIndex = await updateYamlFile(manifest.artifact.state_path, stateAfterOperation.digest, [
    { pointer: "/last_role", value: roleKey },
    { pointer: "/last_operation_id", value: manifest.operation.id },
    { pointer: "/manifest_path", value: finalManifestResult.manifestPath },
    { pointer: "/handoff_path", value: handoffResult.handoff_path },
  ]);
  const finalValidation = await validateHandoffFile(handoffResult.handoff_path, { throwOnInvalid: false });
  if (!finalValidation.valid) fail("HANDOFF_STALE", `State changed while dispatch was being prepared: ${handoffResult.handoff_path}`, { errors: finalValidation.errors });
  return {
    run_id: manifest.run_id,
    work_unit_id: manifest.work_unit_id,
    role: ROLE_NAMES[roleKey],
    state: next,
    operation_path: operation.path,
    operation_status: "PREPARED",
    manifest_path: finalManifestResult.manifestPath,
    handoff_path: handoffResult.handoff_path,
    handoff_digest: validation.digest,
    next_action: "SPAWN_AGENT_WITH_VALIDATED_HANDOFF",
    changed: writtenManifest.changed || handoffResult.changed || operationAfter.changed || stateIndex.changed,
  };
}

function findOperationByJob(operations, jobId) {
  return operations.find((entry) => {
    const value = entry.value;
    return value && (value.job_id === jobId || value.agent_job_id === jobId || value.input?.job_id === jobId || value.result?.job_id === jobId);
  });
}

async function listFilesRecursive(directory) {
  if (!(await pathExists(directory))) return [];
  const output = [];
  const entries = await readdir(directory, { withFileTypes: true });
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) output.push(...await listFilesRecursive(path));
    else output.push(path);
  }
  return output;
}

async function findReports(runDirectory, unitId) {
  const root = join(runDirectory, "work-units", unitId);
  const files = (await listFilesRecursive(root)).filter((path) => path.endsWith("report.yaml")).sort();
  const reports = [];
  for (const path of files) {
    try {
      const document = await readYamlFile(path);
      reports.push({ path, digest: document.digest, value: document.value });
    } catch {
      reports.push({ path, error: "unreadable" });
    }
  }
  return reports;
}

export async function bindAgent(options) {
  const jobId = options.jobId ?? options.position;
  if (!jobId) fail("MISSING_ARGUMENT", "bind-agent requires an agent job ID.");
  if (!options.operation) fail("MISSING_ARGUMENT", "--operation is required to bind an agent job.");
  const operationPath = resolve(options.operation);
  const operationDocument = await readYamlFile(operationPath);
  const operation = operationDocument.value;
  if (!OPERATION_STATES.includes(operation.status)) fail("INVALID_OPERATION_STATUS", `Operation has unsupported status: ${operation.status}`, { status: operation.status, expected: OPERATION_STATES });
  if (operation.job_id && operation.job_id !== jobId) fail("AGENT_JOB_MISMATCH", `Operation is already bound to ${operation.job_id}.`, { field: "job_id", actual: operation.job_id, expected: jobId });
  const handoffPath = operation.result?.handoff_path ?? operation.input?.handoff_path;
  if (!handoffPath) fail("HANDOFF_REQUIRED", "The dispatch operation has no generated handoff path.");
  const validation = await validateHandoffFile(handoffPath, { throwOnInvalid: false });
  if (!validation.valid) fail("HANDOFF_INVALID", `Cannot bind an unvalidated handoff: ${handoffPath}`, { errors: validation.errors });
  if (operation.status === "EXECUTING" && operation.job_id === jobId) {
    return { operation_path: operationPath, operation_id: operation.operation_id, job_id: jobId, operation_status: operation.status, handoff_path: handoffPath, handoff_digest: validation.digest, changed: false, next_action: "OBSERVE_AGENT_RESULT" };
  }
  if (operation.status !== "PREPARED") fail("OPERATION_NOT_DISPATCHABLE", `Operation ${operation.operation_id} is ${operation.status}, not dispatch-ready.`, { status: operation.status, expected: ["PREPARED"] });
  const updated = await updateOperation(operationPath, operationDocument.digest, [
    { pointer: "/job_id", value: jobId },
    { pointer: "/status", value: "EXECUTING" },
    { pointer: "/dispatch_binding", value: { job_id: jobId, handoff_path: handoffPath, handoff_digest: validation.digest } },
  ]);
  const readBack = await readYamlFile(operationPath);
  if (readBack.value.job_id !== jobId || readBack.value.status !== "EXECUTING") fail("BIND_VERIFY_FAILED", `Agent binding did not verify: ${operationPath}`, { operation_path: operationPath, expected_job_id: jobId, actual_job_id: readBack.value.job_id, expected_status: "EXECUTING", actual_status: readBack.value.status });
  return { operation_path: operationPath, operation_id: operation.operation_id, job_id: jobId, operation_status: "EXECUTING", handoff_path: handoffPath, handoff_digest: validation.digest, changed: updated.changed, next_action: "SPAWN_OR_OBSERVE_AGENT" };
}

export async function reconcileAgent(options) {
  const jobId = options.jobId ?? options.position;
  if (!jobId) fail("MISSING_ARGUMENT", "reconcile-agent requires a job ID.");
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required for agent reconciliation.");
  const statePath = resolve(options.state);
  const stateDocument = await readYamlFile(statePath);
  const state = stateDocument.value;
  const runId = normalizeRunId(state);
  const unitId = normalizeUnitId(state);
  if (!runId || !unitId) fail("INVALID_STATE", "State must contain run_id and work_unit_id for reconciliation.");
  const runDirectory = runDirectoryFromStatePath(statePath);
  const operations = await readOperationFiles(runDirectory);
  const operation = options.operation ? {
    ...(await readYamlFile(options.operation)),
    path: resolve(options.operation),
  } : findOperationByJob(operations, jobId);
  if (!operation || !operation.value) fail("OPERATION_NOT_FOUND", `No durable operation is associated with agent job ${jobId}.`, { job_id: jobId, operation_paths: operations.map((entry) => entry.path) });
  const operationValue = operation.value;
  if (!pathIsInside(await canonicalPath(operation.path), await canonicalPath(runDirectory))) fail("OPERATION_PATH_OUTSIDE_RUN", `Operation path is outside the run namespace: ${operation.path}`, { field: "operation.path", actual: operation.path, expected: `path inside ${runDirectory}` });
  const operationUnitId = operationValue.work_unit_id ?? operationValue.input?.work_unit_id;
  if (operationUnitId !== unitId) fail("WORK_UNIT_ID_MISMATCH", "Operation belongs to another work unit.", { field: "operation.work_unit_id", actual: operationUnitId ?? null, expected: unitId });
  if (state.attempt_id && operationValue.attempt_id && state.attempt_id !== operationValue.attempt_id && actualStateFromDocument(state) !== "BLOCKED") fail("ATTEMPT_MISMATCH", "Agent operation belongs to a different active attempt.", { field: "attempt_id", actual: operationValue.attempt_id, expected: state.attempt_id });
  const stateWorktree = isMapping(state.worktree) ? state.worktree : {};
  const worktreePath = stateWorktree.path ? resolve(stateWorktree.path) : null;
  let snapshot = null;
  if (worktreePath && await pathExists(worktreePath)) {
    try { snapshot = await gitSnapshot(worktreePath); } catch { snapshot = null; }
  }
  const reports = await findReports(runDirectory, unitId);
  const report = options.report ? reports.find((entry) => resolve(entry.path) === resolve(options.report)) : reports.find((entry) => entry.value?.attempt_id === operationValue.attempt_id) ?? reports.at(-1);
  const baseline = stateWorktree.baseline;
  let effect = "INCONCLUSIVE";
  if (snapshot && baseline) {
    try {
      const resolvedBaseline = await resolveGitRevision(worktreePath, baseline, "worktree.baseline");
      if (snapshot.head === resolvedBaseline && !snapshot.dirty && !report) effect = "EFFECT_ABSENT";
      else if (snapshot.head !== resolvedBaseline || snapshot.dirty || report?.value) effect = "EFFECT_APPLIED";
    } catch {
      effect = "INCONCLUSIVE";
    }
  } else if (!snapshot && !report) effect = "INCONCLUSIVE";
  const reconciliation = {
    job_id: jobId,
    observed_at: new Date().toISOString(),
    effect,
    worktree: snapshot ? { path: worktreePath, branch: snapshot.branch, head: snapshot.head, dirty: snapshot.dirty, status: snapshot.status } : { path: worktreePath, available: false },
    report: report ? { path: report.path, digest: report.digest, status: report.value?.status ?? null } : null,
    preserves_dirty_worktree: true,
  };
  let operationDocument = await readYamlFile(operation.path);
  if (!OPERATION_STATES.includes(operationDocument.value.status)) fail("INVALID_OPERATION_STATUS", `Operation has unsupported status: ${operationDocument.value.status}`, { status: operationDocument.value.status, expected: OPERATION_STATES });
  if (operationDocument.value.status !== "UNKNOWN" && operationDocument.value.status !== "RECONCILING") {
    const unknown = await updateOperation(operation.path, operationDocument.digest, [
      { pointer: "/status", value: "UNKNOWN" },
      { pointer: "/reconciliation", value: reconciliation },
    ]);
    operationDocument = await readYamlFile(operation.path);
    await updateOperation(operation.path, operationDocument.digest, [
      { pointer: "/status", value: "RECONCILING" },
      { pointer: "/reconciliation", value: reconciliation },
    ]);
    operationDocument = await readYamlFile(operation.path);
    reconciliation.operation_unknown_digest = unknown.digest;
  } else {
    await updateOperation(operation.path, operationDocument.digest, [
      { pointer: "/status", value: "RECONCILING" },
      { pointer: "/reconciliation", value: reconciliation },
    ]);
  }
  const currentState = actualStateFromDocument(state);
  const previousBlocker = isMapping(state.blocker) ? state.blocker : {};
  const resumeState = previousBlocker.resume_state && previousBlocker.resume_state !== "BLOCKED" ? previousBlocker.resume_state : currentState;
  const operationRole = String(operationValue.type ?? "").match(/(?:DISPATCH|RESUME)_(WORKER|REVIEWER|QA|ANALYSIS)$/)?.[1]?.toLowerCase() ?? null;
  const blocker = {
    type: "AGENT_UNAVAILABLE",
    code: "AGENT_INTERRUPTED",
    reason: `Agent job ${jobId} stopped before a conclusive durable result; side effects were inspected and retained.`,
    source_state: currentState,
    resume_state: resumeState,
    role: operationRole,
    required_to_resume: ["operation_reconciliation", "validated_handoff"],
    metadata: {
      job_id: jobId,
      operation_id: operationValue.operation_id,
      operation_status: "RECONCILING",
      role: operationRole,
      effect,
      worktree_dirty: snapshot?.dirty ?? null,
      worktree_head: snapshot?.head ?? null,
    },
  };
  let blockedResult = null;
  if (currentState && currentState !== "BLOCKED") {
    blockedResult = await commitUnitTransition({
      statePath,
      workUnitId: unitId,
      from: currentState,
      to: "BLOCKED",
      reason: blocker.reason,
      operationId: operationValue.operation_id,
      extraSets: [{ pointer: "/blocker", value: blocker }],
      allowUnresolvedOperation: true,
    });
  } else {
    const latest = await readYamlFile(statePath);
    blockedResult = await updateYamlFile(statePath, latest.digest, [
      { pointer: "/blocker", value: blocker },
    ]);
  }
  return {
    job_id: jobId,
    run_id: runId,
    work_unit_id: unitId,
    operation_id: operationValue.operation_id,
    operation_path: operation.path,
    operation_status: "RECONCILING",
    effect,
    blocker,
    worktree: reconciliation.worktree,
    report: reconciliation.report,
    state: "BLOCKED",
    state_change: blockedResult,
    next_action: "RESUME_TICKET",
  };
}

async function blockFailedResume(statePath, workUnitId, resumeState, reason, operationId = null) {
  try {
    const latest = await readYamlFile(statePath);
    const current = actualStateFromDocument(latest.value);
    const blocker = {
      type: reason.code?.includes("TARGET") ? "TARGET_CHANGE" : "HANDOFF_CONTEXT",
      code: "RESUME_PREPARATION_FAILED",
      reason: `Resume preparation failed and was returned to a durable blocker: ${reason.message}`,
      source_state: current,
      resume_state: resumeState,
      required_to_resume: ["repair_resume_context", "validated_handoff"],
      metadata: { operation_id: operationId, error_code: reason.code ?? "UNEXPECTED_ERROR" },
    };
    if (current !== "BLOCKED" && LEGAL_UNIT_TRANSITIONS[current]?.includes("BLOCKED")) {
      await commitUnitTransition({ statePath, workUnitId, from: current, to: "BLOCKED", reason: blocker.reason, operationId, extraSets: [{ pointer: "/blocker", value: blocker }], allowUnresolvedOperation: true });
    } else {
      const currentDocument = await readYamlFile(statePath);
      await updateYamlFile(statePath, currentDocument.digest, [{ pointer: "/blocker", value: blocker }]);
    }
  } catch {
    // The original preparation error remains authoritative; the preserved
    // state and artifacts require normal host reconciliation if this write
    // also fails.
  }
}

async function nextAttemptNumber(runDirectory, unitId, roleKey, state) {
  const values = [Number(state.attempt_number) || 0];
  for (const operation of await readOperationFiles(runDirectory)) {
    if (operation.value?.work_unit_id === unitId || operation.value?.input?.work_unit_id === unitId) {
      const match = String(operation.value.attempt_id ?? "").match(/:attempt-([0-9]{3})$/);
      if (match) values.push(Number(match[1]));
    }
  }
  for (const report of await findReports(runDirectory, unitId)) {
    const match = String(report.value?.attempt_id ?? "").match(new RegExp(`:${roleKey}:attempt-([0-9]{3})$`));
    if (match) values.push(Number(match[1]));
  }
  return Math.max(...values) + 1;
}

export async function resumeTicket(options) {
  const unitId = options.unitId ?? options.position;
  if (!unitId) fail("MISSING_ARGUMENT", "resume-ticket requires a work-unit ID.");
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required to resume a ticket.");
  const statePath = resolve(options.state);
  const stateDocument = await readYamlFile(statePath);
  const state = stateDocument.value;
  const runId = normalizeRunId(state);
  if (normalizeUnitId(state) !== unitId) fail("WORK_UNIT_ID_MISMATCH", "State file does not belong to the requested work unit.", { field: "work_unit_id", actual: normalizeUnitId(state), expected: unitId });
  if (actualStateFromDocument(state) !== "BLOCKED") fail("RESUME_NOT_BLOCKED", `Work unit ${unitId} is not BLOCKED.`, { actual: actualStateFromDocument(state), expected: "BLOCKED" });
  const blocker = isMapping(state.blocker) ? state.blocker : {};
  const resumeState = blocker.resume_state;
  if (!UNIT_STATES.includes(resumeState) || resumeState === "BLOCKED") fail("INVALID_RESUME_STATE", `Blocker has no legal resume_state: ${resumeState ?? "<missing>"}`, { field: "blocker.resume_state", actual: resumeState ?? null, expected: UNIT_STATES.filter((value) => value !== "BLOCKED") });
  const roleIssues = [];
  const roleKey = normalizeRole(options.role ?? state.last_role ?? blocker.role ?? "worker", "role", roleIssues);
  if (!roleKey) fail("INVALID_ROLE", "The resume role is invalid.", { errors: roleIssues });
  const runDirectory = runDirectoryFromStatePath(statePath);
  const attemptNumber = padAttempt(options.attempt ?? await nextAttemptNumber(runDirectory, unitId, roleKey, state));
  const stateWorktree = isMapping(state.worktree) ? state.worktree : {};
  const normalPath = stateWorktree.path ? resolve(stateWorktree.path) : null;
  const strategy = options.strategy ?? ((normalPath && await pathExists(normalPath)) ? "resume" : "replacement");
  if (!["resume", "replacement"].includes(strategy)) fail("INVALID_STRATEGY", `Unknown resume strategy: ${strategy}`, { expected: ["resume", "replacement"] });
  let worktreePath = normalPath;
  if (strategy === "replacement") {
    const canonical = normalPath ? normalPath.replace(/\/recovery-[0-9]{3}$/, "") : null;
    if (!canonical) fail("WORKTREE_NOT_READY", "A replacement requires the recorded canonical worktree path.");
    let sequence = 1;
    while (await pathExists(join(canonical, `recovery-${String(sequence).padStart(3, "0")}`))) sequence += 1;
    worktreePath = resolve(options.replacementWorktree ?? join(canonical, `recovery-${String(sequence).padStart(3, "0")}`));
    if (!(await pathExists(worktreePath))) {
      fail("WORKTREE_NOT_READY", `Replacement path is recorded but not provisioned: ${worktreePath}`, { path: worktreePath, next_action: "PROVISION_RECONCILED_WORKTREE" });
    }
  }
  const latestSnapshot = await gitSnapshot(worktreePath);
  const attemptId = `${runId}:${unitId}:${roleKey}:attempt-${attemptNumber}`;
  const oldOperationId = blocker.metadata?.operation_id ?? blocker.operation_id ?? null;
  const stateUpdate = await updateYamlFile(statePath, stateDocument.digest, [
    { pointer: "/attempt_number", value: Number(attemptNumber) },
    { pointer: "/attempt_id", value: attemptId },
    { pointer: "/last_role", value: roleKey },
    { pointer: "/worktree/path", value: worktreePath },
    { pointer: "/worktree/repository_id", value: latestSnapshot.repository_id },
    { pointer: "/worktree/branch", value: latestSnapshot.branch },
    { pointer: "/worktree/current_head", value: latestSnapshot.head },
    { pointer: "/resume_from_operation_id", value: oldOperationId },
  ]);
  const transition = await commitUnitTransition({
    statePath,
    workUnitId: unitId,
    from: "BLOCKED",
    to: resumeState,
    reason: `Resume ${roleKey} attempt ${attemptNumber} after durable agent reconciliation.`,
    operationId: oldOperationId,
    allowUnresolvedOperation: true,
  });
  try {
    const resumeOperationId = `${runId}:${unitId}:RESUME_${roleKey.toUpperCase()}`;
    const manifestResult = await buildExecutionManifest({
    ...options,
    run: options.run ?? join(runDirectory, "run.yaml"),
    state: statePath,
    role: roleKey,
    operation_id: resumeOperationId,
    operation_type: `RESUME_${roleKey.toUpperCase()}`,
    attempt: attemptNumber,
    output: options.output,
    handoff: options.handoff,
    worktree: worktreePath,
  });
  const manifestWrite = await writeExecutionManifest(manifestResult.manifest, manifestResult.manifestPath);
  const operation = await createDispatchOperation(manifestResult.manifest, { stateBefore: resumeState, stateAfter: resumeState });
  const handoff = await generateHandoffFromManifest(manifestResult.manifestPath, manifestResult.handoffPath);
  const validation = await validateHandoffFile(handoff.handoff_path, { throwOnInvalid: false });
  if (!validation.valid) fail("HANDOFF_INVALID", `Resumed handoff failed validation: ${handoff.handoff_path}`, { errors: validation.errors });
  const operationDocument = await readYamlFile(operation.path);
  const operationUpdate = await updateOperation(operation.path, operationDocument.digest, [
    { pointer: "/result", value: { ready_to_dispatch: true, handoff_path: handoff.handoff_path, handoff_digest: validation.digest, manifest_path: manifestResult.manifestPath, manifest_digest: manifestWrite.digest } },
  ]);
  const stateAfterHandoff = await readYamlFile(statePath);
  const recorded = await updateYamlFile(statePath, stateAfterHandoff.digest, [
    { pointer: "/manifest_path", value: manifestResult.manifestPath },
    { pointer: "/handoff_path", value: handoff.handoff_path },
    { pointer: "/last_operation_id", value: manifestResult.manifest.operation.id },
    { pointer: "/blocker", value: null },
  ]);
  return {
    run_id: runId,
    work_unit_id: unitId,
    role: ROLE_NAMES[roleKey],
    strategy,
    attempt_id: attemptId,
    state: resumeState,
    worktree: { path: worktreePath, dirty: latestSnapshot.dirty, head: latestSnapshot.head },
    transition_id: transition.transition_id,
    operation_path: operation.path,
    handoff_path: handoff.handoff_path,
    manifest_path: manifestResult.manifestPath,
    handoff_digest: validation.digest,
      state_changed: stateUpdate.changed || recorded.changed,
      operation_changed: operationUpdate.changed,
      next_action: "SPAWN_AGENT_WITH_VALIDATED_HANDOFF",
    };
  } catch (error) {
    await blockFailedResume(statePath, unitId, resumeState, error, oldOperationId);
    throw error;
  }
}

function legalNextAction(state, dependenciesReady, blocker) {
  if (state === "DONE") return "RUN_QA_OR_VERIFY_CRITERIA";
  if (state === "BLOCKED") return blocker?.required_to_resume?.[0] ?? "RESOLVE_BLOCKER";
  if (state === "READY") return dependenciesReady ? "PREPARE_WORKER_DISPATCH" : "WAIT_FOR_DEPENDENCIES";
  if (state === "ASSIGNED") return "WAIT_FOR_AGENT_ACKNOWLEDGEMENT";
  if (state === "IMPLEMENTING") return "WAIT_FOR_WORKER_REPORT";
  if (state === "AWAITING_REVIEW") return "PREPARE_REVIEWER_DISPATCH";
  if (state === "REVIEWING") return "WAIT_FOR_REVIEW_VERDICT";
  if (state === "FIXING") return "WAIT_FOR_WORKER_CORRECTION";
  if (state === "INTEGRATING") return "INTEGRATE_EXACT_APPROVED_REVISION";
  if (state === "ESCALATED") return "USER_OR_AUTHORITY_DECISION";
  return "INSPECT_STATE";
}

async function latestReportForUnit(runDirectory, unitId, role = undefined) {
  const reports = await findReports(runDirectory, unitId);
  const matching = role ? reports.filter((entry) => entry.value?.role === ROLE_NAMES[role] || entry.value?.role === role) : reports;
  return matching.at(-1) ?? null;
}

export async function statusRun(runPath, options = {}) {
  const artifacts = await allRunArtifacts(resolve(runPath));
  const run = artifacts.runDocument.value;
  const runDirectory = dirname(runPath);
  const targetRoot = run.project?.root ?? run.project_root;
  let target = null;
  if (targetRoot && await pathExists(targetRoot)) {
    try {
      const snapshot = await gitSnapshot(targetRoot);
      target = { repository_root: snapshot.root, branch: snapshot.branch, head: snapshot.head, dirty: snapshot.dirty };
    } catch (error) { target = { error: error.message }; }
  }
  const qaPath = run.qa?.report_path ?? run.qa_report_path;
  let qa = run.qa ?? null;
  if (qaPath && await pathExists(qaPath)) {
    try {
      const qaDocument = await readYamlFile(qaPath);
      qa = { path: resolve(qaPath), digest: qaDocument.digest, verdict: qaDocument.value.verdict ?? null, status: qaDocument.value.status ?? null };
    } catch (error) {
      qa = { path: resolve(qaPath), error: error.message };
    }
  }
  const requestedUnit = options.ticket;
  const workUnits = [];
  for (const unit of artifacts.units) {
    if (unit.error || !unit.value) continue;
    const id = normalizeUnitId(unit.value);
    if (requestedUnit && id !== requestedUnit) continue;
    const current = actualStateFromDocument(unit.value);
    const dependencies = normalizeDependencies(unit.value);
    const dependencyRows = dependencies.map((dependency) => {
      const found = artifacts.units.find((candidate) => normalizeUnitId(candidate.value ?? {}) === dependency.work_unit_id);
      return { work_unit_id: dependency.work_unit_id, state: found ? actualStateFromDocument(found.value) : null, ready: Boolean(found && actualStateFromDocument(found.value) === "DONE") };
    });
    const unitOperations = artifacts.operations.filter((entry) => entry.value?.work_unit_id === id || entry.value?.input?.work_unit_id === id || entry.value?.operation_id?.startsWith(`${artifacts.runDocument.run_id}:${id}:`));
    const latestOperation = unit.value.last_operation_id ? unitOperations.find((entry) => entry.value?.operation_id === unit.value.last_operation_id) ?? unitOperations.at(-1) : unitOperations.at(-1);
    const latestTransition = artifacts.transitions.filter((entry) => entry.value?.entity === id).at(-1);
    const reviewer = await latestReportForUnit(runDirectory, id, "reviewer");
    const worktreePath = unit.value.worktree?.path;
    let worktree = null;
    if (worktreePath && await pathExists(worktreePath)) {
      try {
        const snapshot = await gitSnapshot(worktreePath);
        worktree = { path: resolve(worktreePath), branch: snapshot.branch, head: snapshot.head, dirty: snapshot.dirty };
      } catch (error) { worktree = { path: resolve(worktreePath), error: error.message }; }
    }
    workUnits.push({
      work_unit_id: id,
      state: current,
      blocker: unit.value.blocker ?? null,
      revision: unit.value.current_head ?? unit.value.worktree?.current_head ?? unit.value.commit?.revision ?? null,
      latest_operation: latestOperation ? { path: latestOperation.path, operation_id: latestOperation.value.operation_id, status: latestOperation.value.status, attempt_id: latestOperation.value.attempt_id } : null,
      latest_transition: latestTransition ? { path: latestTransition.path, transition_id: latestTransition.value.transition_id, status: latestTransition.value.status, from: latestTransition.value.from, to: latestTransition.value.to } : null,
      report_verdict: reviewer?.value?.verdict ?? reviewer?.value?.review?.verdict ?? null,
      dependencies: dependencyRows,
      dependencies_ready: dependencyRows.every((entry) => entry.ready),
      dirty_worktree: worktree?.dirty ?? null,
      worktree,
      next_legal_action: legalNextAction(current, dependencyRows.every((entry) => entry.ready), unit.value.blocker),
      ...(options.explain ? { explanation: { state: current, legal_next_states: LEGAL_UNIT_TRANSITIONS[current] ?? [], dependency_rows: dependencyRows, blocker: unit.value.blocker ?? null } } : {}),
    });
  }
  const counts = {};
  for (const unit of workUnits) counts[unit.state] = (counts[unit.state] ?? 0) + 1;
  return {
    run_id: artifacts.runDocument.run_id,
    run_path: resolve(runPath),
    run_state: run.state ?? run.status ?? null,
    target,
    work_unit_counts: counts,
    work_units: workUnits,
    required_core_status: run.required_core_status ?? null,
    blockers: workUnits.filter((unit) => unit.blocker).map((unit) => ({ work_unit_id: unit.work_unit_id, blocker: unit.blocker })),
    latest_operation: artifacts.operations.at(-1) ? { operation_id: artifacts.operations.at(-1).value?.operation_id ?? null, status: artifacts.operations.at(-1).value?.status ?? null } : null,
    qa,
    cleanup_state: run.cleanup_state ?? "RETAINED_UNTIL_EXPLICIT_CLEANUP",
  };
}

export async function verifyRun(runPath, { final = false } = {}) {
  const preflight = await preflightRun(runPath);
  const issues = [...preflight.issues];
  const artifacts = await allRunArtifacts(resolve(runPath));
  const run = artifacts.runDocument.value;
  for (const operation of artifacts.operations) {
    if (["PREPARED", "EXECUTING", "UNKNOWN", "RECONCILING"].includes(operation.value?.status)) issues.push(issue(`${operation.path}:status`, "UNRESOLVED_OPERATION", operation.value.status, "SUCCEEDED or FAILED conclusive operation status", "Run verification cannot accept an unresolved side effect."));
    if (operation.value?.status === "FAILED") issues.push(issue(`${operation.path}:status`, "FAILED_OPERATION", operation.value.status, "SUCCEEDED", "A failed side effect requires recovery or an explicit non-success terminal state."));
  }
  for (const transition of artifacts.transitions) {
    if (transition.value?.status !== "COMMITTED" && transition.value?.status !== "ABORTED") issues.push(issue(`${transition.path}:status`, "UNCOMMITTED_TRANSITION", transition.value?.status ?? null, ["COMMITTED", "ABORTED"], "Run verification cannot accept an uncommitted lifecycle transition."));
  }
  const allDone = artifacts.units.length > 0 && artifacts.units.every((unit) => actualStateFromDocument(unit.value ?? {}) === "DONE");
  const qaPath = run.qa?.report_path ?? run.qa_report_path;
  let qa = null;
  if (qaPath && await pathExists(qaPath)) {
    try {
      const report = await readYamlFile(qaPath);
      qa = { path: resolve(qaPath), digest: report.digest, verdict: report.value.verdict, status: report.value.status };
      if (report.value.canonical?.revision && preflight.target?.head && report.value.canonical.revision !== preflight.target.head) issues.push(issue("qa.canonical.revision", "QA_REVISION_MISMATCH", report.value.canonical.revision, preflight.target.head, "QA evidence was produced against another target revision."));
      if (final && report.value.verdict !== "PASSED") issues.push(issue("qa.verdict", "QA_NOT_PASSED", report.value.verdict ?? null, "PASSED", "Final run verification requires a passed QA report."));
    } catch (error) { issues.push(issue("qa.report_path", error.code ?? "QA_READ_FAILED", error.message, "readable QA report", "The QA report could not be verified.")); }
  } else if (final) issues.push(issue("qa.report_path", "QA_REPORT_REQUIRED", qaPath ?? null, "existing QA report", "Final run verification requires durable QA evidence."));
  for (const unit of artifacts.units) {
    if (!unit.value || actualStateFromDocument(unit.value) !== "DONE") continue;
    const unitId = normalizeUnitId(unit.value);
    const reviewer = await latestReportForUnit(dirname(runPath), unitId, "reviewer");
    if (!reviewer || reviewer.error) {
      if (final) issues.push(issue(`${unit.path}:review`, "REVIEW_REPORT_REQUIRED", reviewer?.path ?? null, "durable APPROVED reviewer report", "A DONE work unit must retain its exact approval evidence."));
      continue;
    }
    const verdict = reviewer.value.verdict ?? reviewer.value.review?.verdict;
    if (verdict !== "APPROVED") issues.push(issue(`${unit.path}:review.verdict`, "REVIEW_NOT_APPROVED", verdict ?? null, "APPROVED", "A DONE work unit cannot rely on a non-approval verdict."));
    const approvedRevision = reviewer.value.reviewer?.final_revision ?? reviewer.value.final_revision ?? reviewer.value.reviewer?.reviewed_revision;
    const integratedRevision = unit.value.integrated_revision ?? unit.value.integration?.source_revision ?? unit.value.approved_revision;
    if (approvedRevision && integratedRevision && approvedRevision !== integratedRevision) issues.push(issue(`${unit.path}:review.revision`, "REVIEW_REVISION_MISMATCH", approvedRevision, integratedRevision, "Reviewer approval does not match the integrated revision."));
  }
  if (final && !allDone) issues.push(issue("work_units", "WORK_UNITS_INCOMPLETE", artifacts.units.map((unit) => ({ id: normalizeUnitId(unit.value ?? {}), state: actualStateFromDocument(unit.value ?? {}) })), "all work units DONE", "Final run verification requires every in-scope work unit to be DONE."));
  if (final && run.state !== "RUN_COMPLETED") issues.push(issue("run.state", "RUN_NOT_COMPLETED", run.state ?? null, "RUN_COMPLETED", "Final verification does not itself terminalize a run."));
  return { ...preflight, valid: issues.length === 0, final, all_work_units_done: allDone, qa, issues };
}
