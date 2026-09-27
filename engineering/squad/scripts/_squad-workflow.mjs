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
  FIXING: ["IMPLEMENTING", "AWAITING_REVIEW", "BLOCKED", "ESCALATED"],
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

export const RUN_STATES = Object.freeze([
  "EXECUTING",
  "RUN_VALIDATING",
  "QA",
  "REMEDIATING",
  "COMPLETING",
  "RUN_COMPLETED",
  "BLOCKED",
  "PAUSED",
  "RUN_CANCELLED",
  "RUN_ABORTED",
]);

export const LEGAL_RUN_TRANSITIONS = Object.freeze({
  EXECUTING: ["RUN_VALIDATING", "BLOCKED", "PAUSED", "RUN_CANCELLED", "RUN_ABORTED"],
  RUN_VALIDATING: ["QA", "EXECUTING", "BLOCKED", "PAUSED", "RUN_CANCELLED", "RUN_ABORTED"],
  QA: ["COMPLETING", "REMEDIATING", "BLOCKED", "EXECUTING", "PAUSED", "RUN_CANCELLED", "RUN_ABORTED"],
  REMEDIATING: ["EXECUTING", "BLOCKED", "PAUSED", "RUN_CANCELLED", "RUN_ABORTED"],
  COMPLETING: ["RUN_COMPLETED", "BLOCKED", "PAUSED", "RUN_CANCELLED", "RUN_ABORTED"],
  RUN_COMPLETED: [],
  BLOCKED: ["EXECUTING", "RUN_VALIDATING", "QA", "REMEDIATING", "COMPLETING", "PAUSED", "RUN_CANCELLED", "RUN_ABORTED"],
  PAUSED: ["EXECUTING", "RUN_CANCELLED", "RUN_ABORTED"],
  RUN_CANCELLED: [],
  RUN_ABORTED: [],
});

export const OPERATION_STATES = Object.freeze([
  "PREPARED",
  "EXECUTING",
  "SUCCEEDED",
  "FAILED",
  "UNKNOWN",
  "RECONCILING",
  "RECONCILED",
  "SUPERSEDED",
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
const ATTEMPT_PATTERN = /:attempt-[0-9]{3,6}$/;
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

export const PURPOSES = Object.freeze(["production", "prototype"]);
export const PRODUCTION_IMPLEMENTATION_MODES = Object.freeze(["default", "tdd"]);

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

function normalizePurpose(value, field = "purpose", issues = [], defaultValue = "production") {
  const purpose = value === undefined || value === null ? defaultValue : value;
  if (!PURPOSES.includes(purpose)) {
    issues.push(issue(field, "INVALID_PURPOSE", purpose, PURPOSES, "Purpose must be production or prototype."));
    return undefined;
  }
  return purpose;
}

function runPurposeValue(run) {
  return run?.purpose ?? (isMapping(run?.admission) ? run.admission.purpose : undefined) ?? "production";
}

function completionMarkerForPurpose(purpose) {
  return purpose === "prototype" ? "P" : "x";
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
  if (roleKey === "worker" && current === "FIXING") return "IMPLEMENTING";
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

function actualRunState(value) {
  const primary = asString(value?.state);
  const alternatives = [asString(value?.run_state), asString(value?.status)].filter(Boolean);
  const distinctAlternatives = [...new Set(alternatives)];
  if (distinctAlternatives.length > 1) fail("AMBIGUOUS_RUN_STATE", "run.run_state and run.status disagree.", { field: "run.run_state", actual: distinctAlternatives[0], expected: distinctAlternatives[1] });
  const alternate = distinctAlternatives[0] ?? null;
  if (primary && alternate && primary !== alternate) fail("AMBIGUOUS_RUN_STATE", "run.state and run.status/run_state disagree.", { field: "run.state", actual: primary, expected: alternate });
  return primary ?? alternate;
}

function validateRunTransitionShape(transition, currentState, issues, field = "transition") {
  if (!isMapping(transition)) {
    issues.push(issue(field, "INVALID_MAPPING", transition, "mapping", "The run transition must be a mapping."));
    return;
  }
  const from = transition.from;
  const to = transition.to;
  if (!RUN_STATES.includes(from)) issues.push(issue(`${field}.from`, "INVALID_RUN_STATE", from ?? null, RUN_STATES, "The run transition source is not known."));
  if (!RUN_STATES.includes(to)) issues.push(issue(`${field}.to`, "INVALID_RUN_STATE", to ?? null, RUN_STATES, "The run transition destination is not known."));
  if (from && currentState && from !== currentState) issues.push(issue(`${field}.from`, "RUN_TRANSITION_SOURCE_MISMATCH", from, currentState, "The run transition source does not match the current run state."));
  if (from && to && RUN_STATES.includes(from) && !LEGAL_RUN_TRANSITIONS[from].includes(to)) issues.push(issue(field, "ILLEGAL_RUN_TRANSITION", `${from} -> ${to}`, LEGAL_RUN_TRANSITIONS[from], "The requested run lifecycle transition is not legal."));
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
  const historical = options.historical === true;
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
  const analysisId = roleKey === "analysis" ? requireString(handoff.analysis_id, "analysis_id", issues) : null;
  const rawOperationInstanceId = handoff.operation_instance_id ?? (isMapping(handoff.operation) ? handoff.operation.instance_id : undefined);
  const operationInstanceId = rawOperationInstanceId === undefined ? undefined : requireString(rawOperationInstanceId, "operation_instance_id", issues);
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
    if (operationInstanceId && (!operationInstanceId.startsWith(`${operationId}:attempt-`) || !/:attempt-[0-9]{3,6}$/.test(operationInstanceId))) {
      issues.push(issue("operation_instance_id", "INVALID_OPERATION_INSTANCE_ID", operationInstanceId, `${operationId}:attempt-<NNN>`, "Operation instances must be unique per logical operation attempt."));
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
  const decisions = isMapping(handoff.decisions) ? handoff.decisions : {};
  const purpose = normalizePurpose(decisions.purpose, "decisions.purpose", issues);
  const completionMarker = decisions.completion_marker ?? completionMarkerForPurpose(purpose);
  if (completionMarker !== "x" && completionMarker !== "P") issues.push(issue("decisions.completion_marker", "INVALID_COMPLETION_MARKER", completionMarker, ["x", "P"], "Completion marker must be x for production or P for prototype."));
  if (purpose && completionMarker !== completionMarkerForPurpose(purpose)) issues.push(issue("decisions.completion_marker", "COMPLETION_MARKER_MISMATCH", completionMarker, completionMarkerForPurpose(purpose), "Completion marker must match the admitted purpose."));
  const implementationMode = decisions.mode;
  if (implementationMode !== undefined && implementationMode !== null && !PRODUCTION_IMPLEMENTATION_MODES.includes(implementationMode)) issues.push(issue("decisions.mode", "INVALID_IMPLEMENTATION_MODE", implementationMode, PRODUCTION_IMPLEMENTATION_MODES, "Implementation mode must be default or tdd when present."));
  if (purpose === "prototype" && implementationMode !== undefined && implementationMode !== null) issues.push(issue("decisions.mode", "PROTOTYPE_MODE_NOT_ALLOWED", implementationMode, null, "Prototype purpose does not select a production implementation mode."));

  const ticketsPath = requireString(source.tickets_index_path, "source.tickets_index_path", issues, { absolute: true });
  const ticketPath = requireString(source.work_unit_path, "source.work_unit_path", issues, { absolute: true });
  const ticketsDigest = normalizeDigest(source.tickets_digest, "source.tickets_digest", issues);
  const ticketDigest = normalizeDigest(source.ticket_digest, "source.ticket_digest", issues);
  const proposalPath = source.proposal_path === undefined ? null : requireString(source.proposal_path, "source.proposal_path", issues, { absolute: true });
  const proposalDigest = source.proposal_digest === undefined || source.proposal_digest === null ? null : normalizeDigest(source.proposal_digest, "source.proposal_digest", issues);
  if (source.proposal_required !== undefined && typeof source.proposal_required !== "boolean") issues.push(issue("source.proposal_required", "INVALID_BOOLEAN", source.proposal_required, "boolean", "Proposal admission must be explicit when present."));
  const reviewerContext = roleKey === "reviewer" ? (isMapping(handoff.reviewer_context) ? handoff.reviewer_context : null) : null;
  if (roleKey === "reviewer" && !reviewerContext) issues.push(issue("reviewer_context", "HANDOFF_CONTEXT_REQUIRED", null, "generated reviewer context", "A reviewer handoff must contain the host-generated worker/context contract."));
  if (reviewerContext) {
    if (!isMapping(reviewerContext.worker)) issues.push(issue("reviewer_context.worker", "HANDOFF_CONTEXT_REQUIRED", null, "worker context", "Reviewer context must retain the exact worker evidence boundary."));
    else {
      requireString(reviewerContext.worker.report_path, "reviewer_context.worker.report_path", issues, { absolute: true });
      normalizeDigest(reviewerContext.worker.report_digest, "reviewer_context.worker.report_digest", issues);
      normalizeRevision(reviewerContext.worker.revision, "reviewer_context.worker.revision", issues);
      requireString(reviewerContext.worker.attempt_id, "reviewer_context.worker.attempt_id", issues);
    }
    if (!Array.isArray(reviewerContext.prior_reviews)) issues.push(issue("reviewer_context.prior_reviews", "HANDOFF_CONTEXT_REQUIRED", reviewerContext.prior_reviews ?? null, "array", "Reviewer context must retain prior review history."));
    if (!isMapping(reviewerContext.report_schema)) issues.push(issue("reviewer_context.report_schema", "HANDOFF_CONTEXT_REQUIRED", null, "report schema", "Reviewer context must retain the exact report contract."));
  }
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
  const nestedOperationInstanceId = operation.instance_id === undefined ? undefined : requireString(operation.instance_id, "operation.instance_id", issues);
  const nestedOperationAttemptId = requireString(operation.attempt_id, "operation.attempt_id", issues);
  const operationType = requireString(operation.type, "operation.type", issues);

  if (currentState && !UNIT_STATES.includes(currentState)) issues.push(issue("state.current", "INVALID_STATE", currentState, UNIT_STATES, "The handoff state is not a known work-unit state."));
  if (expectedState && !UNIT_STATES.includes(expectedState)) issues.push(issue("state.expected", "INVALID_STATE", expectedState, UNIT_STATES, "The expected state is not a known work-unit state."));
  if (currentState && expectedState && currentState !== expectedState) validateTransitionShape({ from: currentState, to: expectedState }, currentState, issues, "state.expected_transition");
  if (nestedOperationId && nestedOperationId !== operationId) issues.push(issue("operation.id", "OPERATION_ID_MISMATCH", nestedOperationId, operationId, "The nested operation identity must match the handoff."));
  if (nestedOperationInstanceId && operationInstanceId && nestedOperationInstanceId !== operationInstanceId) issues.push(issue("operation.instance_id", "OPERATION_INSTANCE_ID_MISMATCH", nestedOperationInstanceId, operationInstanceId, "The nested operation instance must match the handoff."));
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
      if (operationPath) addExpectedIssue(issues, "artifact.operation_path", await canonicalPath(operationPath), await canonicalPath(operationPathFor(artifactRunDir, operationId, operationInstanceId)), "OPERATION_PATH_MISMATCH", "The handoff operation path does not match its operation identity.");
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
            const runPurposeIssues = [];
            const runPurpose = normalizePurpose(runPurposeValue(runValue), "run.purpose", runPurposeIssues);
            issues.push(...runPurposeIssues);
            addExpectedIssue(issues, "decisions.purpose", purpose, runPurpose, "PURPOSE_MISMATCH", "The handoff purpose differs from the admitted run.");
            addExpectedIssue(issues, "decisions.completion_marker", completionMarker, completionMarkerForPurpose(runPurpose), "COMPLETION_MARKER_MISMATCH", "The handoff completion marker differs from the admitted purpose.");
            const runSource = isMapping(runValue.source) ? runValue.source : {};
            const runProposal = proposalProjection(runValue);
            if (!historical && source.proposal_required !== undefined && source.proposal_required !== runProposal.required) issues.push(issue("source.proposal_required", "PROPOSAL_REQUIREMENT_MISMATCH", source.proposal_required, runProposal.required, "The handoff proposal admission flag differs from the admitted run."));
            if (runProposal.required) {
              if (!proposalPath) issues.push(issue("source.proposal_path", "MISSING_PROPOSAL_PATH", null, "required canonical proposal path", "The handoff omitted a required proposal identity."));
              else if (runProposal.path) addExpectedIssue(issues, "source.proposal_path", await canonicalPath(proposalPath), await canonicalPath(runProposal.path), "PROPOSAL_PATH_MISMATCH", "The handoff proposal path differs from the admitted run.");
              if (!proposalDigest) issues.push(issue("source.proposal_digest", "MISSING_PROPOSAL_DIGEST", null, "sha256:<64 hex characters>", "The handoff omitted a required proposal digest."));
              else if (runProposal.digest) addExpectedIssue(issues, "source.proposal_digest", proposalDigest, String(runProposal.digest).toLowerCase(), "DIGEST_MISMATCH", "The handoff proposal digest differs from the admitted run.");
            }
            if (proposalPath && proposalDigest) await validatePathDigest("source.proposal_path", proposalPath, proposalDigest, issues);
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
                if (!historical) addExpectedIssue(issues, "target.head", handoffResolvedHead, runResolvedHead, "TARGET_HEAD_MISMATCH", "The handoff target HEAD differs from the run record.");
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
          const runForMode = (await readYamlFile(join(artifactRunDir, "run.yaml"))).value;
          const statePurpose = stateDocument.value.purpose;
          if (!historical && statePurpose !== undefined && statePurpose !== null) {
            if (!PURPOSES.includes(statePurpose)) issues.push(issue("state.purpose", "INVALID_PURPOSE", statePurpose, PURPOSES, "Unit state purpose must be production or prototype."));
            else addExpectedIssue(issues, "state.purpose", statePurpose, runPurposeValue(runForMode), "PURPOSE_MISMATCH", "The unit state purpose differs from the admitted run.");
          }
          const runWorkerMode = runForMode.worker_mode ?? (isMapping(runForMode.admission) ? runForMode.admission.worker_mode : undefined);
          const unitWorkerMode = historical ? undefined : stateDocument.value.worker_mode;
          if (!historical && unitWorkerMode !== undefined && unitWorkerMode !== null && !PRODUCTION_IMPLEMENTATION_MODES.includes(unitWorkerMode)) issues.push(issue("state.worker_mode", "INVALID_IMPLEMENTATION_MODE", unitWorkerMode, PRODUCTION_IMPLEMENTATION_MODES, "Unit-specific worker mode must be default or tdd."));
          if (!historical && runPurposeValue(runForMode) === "prototype" && unitWorkerMode !== undefined && unitWorkerMode !== null) issues.push(issue("state.worker_mode", "PROTOTYPE_MODE_NOT_ALLOWED", unitWorkerMode, null, "Prototype purpose does not select a production implementation mode."));
          const effectiveWorkerMode = unitWorkerMode ?? runWorkerMode;
          if (!historical && effectiveWorkerMode !== undefined && effectiveWorkerMode !== null) addExpectedIssue(issues, "decisions.mode", implementationMode, effectiveWorkerMode, "IMPLEMENTATION_MODE_MISMATCH", "The handoff implementation mode differs from the admitted run or unit override.");
          const durableDependencyIds = normalizeDependencies(stateDocument.value).map((dependency) => dependency.work_unit_id).sort();
          const handoffDependencyIds = normalizeDependencies(handoff).map((dependency) => dependency.work_unit_id).sort();
          addExpectedIssue(issues, "dependencies", handoffDependencyIds, durableDependencyIds, "DEPENDENCY_SET_MISMATCH", "The handoff dependency set is not the latest durable dependency set.");
          addExpectedIssue(issues, "work_unit_id", actualUnit, unitId, "WORK_UNIT_ID_MISMATCH", "The state file belongs to another work unit.");
          addExpectedIssue(issues, "run_id", actualRun, runId, "RUN_ID_MISMATCH", "The state file belongs to another run.");
          if (!historical) addExpectedIssue(issues, "state.current", currentState, actualState, "STATE_MISMATCH", "The handoff state is not the latest durable state.");
          if (!historical && roleKey !== "analysis" && actualAttempt && attemptId && actualAttempt !== attemptId && !(actualState === "BLOCKED" && handoff.transition?.from === "BLOCKED")) {
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
            if (operationInstanceId) addExpectedIssue(issues, "manifest.operation.instance_id", manifestValue.operation?.instance_id, operationInstanceId, "OPERATION_INSTANCE_ID_MISMATCH", "The manifest operation instance differs from the handoff.");
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
            if (operationInstanceId) addExpectedIssue(issues, "operation.instance_id", operationValue.operation_instance_id ?? operationValue.operation_id, operationInstanceId, "OPERATION_INSTANCE_ID_MISMATCH", "The durable operation instance differs from the handoff.");
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
      if (reviewerContext?.worker?.report_path) {
        const workerReportPath = resolve(reviewerContext.worker.report_path);
        if (await requireExistingPath(workerReportPath, "reviewer_context.worker.report_path", issues)) {
          await validatePathDigest("reviewer_context.worker.report_path", workerReportPath, reviewerContext.worker.report_digest, issues);
          try {
            const workerReport = await readYamlFile(workerReportPath);
            addExpectedIssue(issues, "reviewer_context.worker.report.role", workerReport.value?.role, "squad-worker", "ROLE_MISMATCH", "Reviewer context points to a non-worker report.");
            addExpectedIssue(issues, "reviewer_context.worker.report.run_id", workerReport.value?.run_id, runId, "RUN_ID_MISMATCH", "Reviewer context worker report belongs to another run.");
            addExpectedIssue(issues, "reviewer_context.worker.report.work_unit_id", workerReport.value?.work_unit_id, unitId, "WORK_UNIT_ID_MISMATCH", "Reviewer context worker report belongs to another work unit.");
            const reportRevision = workerReport.value?.worker?.final_revision ?? workerReport.value?.final_revision ?? workerReport.value?.implementation_revision ?? workerReport.value?.commits?.at(-1) ?? null;
            if (reportRevision && reviewerContext.worker.revision) {
              const resolvedReportRevision = await resolveGitRevision(targetRoot, reportRevision, "reviewer_context.worker.report.revision");
              const resolvedContextRevision = await resolveGitRevision(targetRoot, reviewerContext.worker.revision, "reviewer_context.worker.revision");
              addExpectedIssue(issues, "reviewer_context.worker.revision", resolvedContextRevision, resolvedReportRevision, "REVIEWER_CONTEXT_REVISION_MISMATCH", "Reviewer context worker revision differs from worker report.");
            }
          } catch (error) { issues.push(issue("reviewer_context.worker.report_path", error.code ?? "REPORT_READ_FAILED", workerReportPath, "readable worker report", error.message)); }
        }
      }
      if (!historical && reportPath && !(await pathExists(dirname(reportPath)))) issues.push(issue("report.parent", "REPORT_PARENT_REQUIRED", dirname(reportPath), "existing report parent directory", "Dispatch preparation must provision the report parent before bind."));
      if (!historical && evidenceDirectory && !(await pathExists(evidenceDirectory))) issues.push(issue("evidence.directory", "EVIDENCE_DIRECTORY_REQUIRED", evidenceDirectory, "existing evidence directory", "Dispatch preparation must provision the evidence directory before bind."));
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
        } else if (!historical && report.expected === "CREATE" && reportExists) {
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
      if (targetSnapshot.dirty && !historical) issues.push(issue("target.dirty", "TARGET_DIRTY", true, false, "The target checkout must be clean for a validated active handoff."));
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
        if (historical) checks.push({ name: "target.head.resolves", actual: resolvedTargetHead, expected: "historical handoff target commit", result: "PASS" });
        else {
          check(checks, "target.head", targetSnapshot.head, resolvedTargetHead);
          if (targetSnapshot.head !== resolvedTargetHead) issues.push(issue("target.head", "TARGET_HEAD_MISMATCH", targetSnapshot.head, resolvedTargetHead, "The target branch HEAD differs from the active handoff."));
        }
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
            if (!historical && worktreeSnapshot.head !== resolvedCurrent) issues.push(issue("worktree.current_head", "CURRENT_HEAD_MISMATCH", worktreeSnapshot.head, resolvedCurrent, "The active worktree HEAD differs from the handoff."));
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

  if (roleKey === "analysis" && analysisId && !/^ANALYSIS-|^RUN-/.test(analysisId)) issues.push(issue("analysis_id", "INVALID_ANALYSIS_ID", analysisId, "ANALYSIS-<NNN> or run-scoped analysis identity", "An analysis handoff must retain a stable analysis identity."));

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

export async function validateQaHandoffData(handoff, handoffPath = "<inline>", options = {}) {
  const issues = [];
  const checks = [];
  if (!isMapping(handoff)) fail("INVALID_QA_HANDOFF", `QA handoff is not a YAML mapping: ${handoffPath}`, { errors: [issue("document", "INVALID_MAPPING", handoff, "mapping", "A QA handoff must be a YAML mapping.")] });
  if (handoff.schema_version !== 1) issues.push(issue("schema_version", "UNSUPPORTED_SCHEMA", handoff.schema_version ?? null, 1, "Only QA handoff schema version 1 is supported."));
  if (handoff.kind !== "squad-qa-handoff") issues.push(issue("kind", "INVALID_KIND", handoff.kind ?? null, "squad-qa-handoff", "The QA handoff kind is required."));
  if (handoff.role !== "squad-qa") issues.push(issue("role", "INVALID_ROLE", handoff.role ?? null, "squad-qa", "The QA handoff must target the QA role."));
  const runId = requireString(handoff.run_id, "run_id", issues);
  const qaId = requireString(handoff.qa_id, "qa_id", issues);
  const attemptId = requireString(handoff.attempt_id, "attempt_id", issues);
  const operationId = requireString(handoff.operation_id, "operation_id", issues);
  const operationInstanceId = requireString(handoff.operation_instance_id, "operation_instance_id", issues);
  const source = isMapping(handoff.source) ? handoff.source : {};
  const artifact = isMapping(handoff.artifact) ? handoff.artifact : {};
  const target = isMapping(handoff.target) ? handoff.target : {};
  const state = isMapping(handoff.state) ? handoff.state : {};
  const purpose = normalizePurpose(handoff.purpose, "purpose", issues);
  const completionMarker = handoff.completion_marker ?? completionMarkerForPurpose(purpose);
  if (completionMarker !== "x" && completionMarker !== "P") issues.push(issue("completion_marker", "INVALID_COMPLETION_MARKER", completionMarker, ["x", "P"], "Completion marker must be x for production or P for prototype."));
  if (purpose && completionMarker !== completionMarkerForPurpose(purpose)) issues.push(issue("completion_marker", "COMPLETION_MARKER_MISMATCH", completionMarker, completionMarkerForPurpose(purpose), "Completion marker must match the admitted purpose."));
  const sourcePath = requireString(source.tickets_index_path, "source.tickets_index_path", issues, { absolute: true });
  const sourceDigest = normalizeDigest(source.tickets_digest, "source.tickets_digest", issues);
  const proposalPath = source.proposal_path === undefined ? null : requireString(source.proposal_path, "source.proposal_path", issues, { absolute: true });
  const proposalDigest = source.proposal_digest === undefined || source.proposal_digest === null ? null : normalizeDigest(source.proposal_digest, "source.proposal_digest", issues);
  if (source.proposal_required !== undefined && typeof source.proposal_required !== "boolean") issues.push(issue("source.proposal_required", "INVALID_BOOLEAN", source.proposal_required, "boolean", "Proposal admission must be explicit when present."));
  const runDir = requireString(artifact.run_dir, "artifact.run_dir", issues, { absolute: true });
  const handoffArtifactPath = requireString(artifact.handoff_path, "artifact.handoff_path", issues, { absolute: true });
  const operationPath = requireString(artifact.operation_path, "artifact.operation_path", issues, { absolute: true });
  const reportPath = requireString(artifact.report_path, "artifact.report_path", issues, { absolute: true });
  const evidenceDirectory = requireString(artifact.evidence_directory, "artifact.evidence_directory", issues, { absolute: true });
  const targetRoot = requireString(target.repository_root, "target.repository_root", issues, { absolute: true });
  const targetRepositoryId = requireString(target.repository_id, "target.repository_id", issues, { absolute: true });
  const targetBranch = requireString(target.branch, "target.branch", issues);
  const targetHead = normalizeRevision(target.head, "target.head", issues);
  if (runId && qaId && !qaId.startsWith("QA-")) issues.push(issue("qa_id", "INVALID_QA_ID", qaId, "QA-<NNN>", "QA attempts use a stable QA identity."));
  if (operationId && runId && operationId !== `${runId}:RUN:DISPATCH_QA`) issues.push(issue("operation_id", "INVALID_OPERATION_ID", operationId, `${runId}:RUN:DISPATCH_QA`, "Run-level QA dispatch uses the RUN operation namespace."));
  if (operationInstanceId && operationId && (!operationInstanceId.startsWith(`${operationId}:attempt-`) || !/:attempt-[0-9]{3,6}$/.test(operationInstanceId))) issues.push(issue("operation_instance_id", "INVALID_OPERATION_INSTANCE_ID", operationInstanceId, `${operationId}:attempt-<NNN>`, "QA operation instances identify one attempt."));
  if (sourcePath && sourceDigest) await validatePathDigest("source.tickets_index_path", sourcePath, sourceDigest, issues);
  if (runDir && sourcePath && runId) {
    try {
      const { workspace, backlog } = deriveWorkspaceAndBacklog(sourcePath);
      addExpectedIssue(issues, "artifact.run_dir", await canonicalPath(runDir), await canonicalPath(join(workspace, "_xzy-ai", "sprints", backlog, "orchestration", runId)), "RUN_DIRECTORY_MISMATCH", "The QA handoff is outside the canonical run namespace.");
    } catch (error) { issues.push(issue("artifact.run_dir", error.code ?? "INVALID_SOURCE_PATH", runDir, "canonical run directory", error.message)); }
  }
  const runPath = runDir ? join(runDir, "run.yaml") : null;
  if (runPath && await pathExists(runPath)) {
    try {
      const runDocument = await readRunDocument(runPath);
      addExpectedIssue(issues, "run_id", runDocument.run_id, runId, "RUN_ID_MISMATCH", "The QA handoff belongs to another run.");
      const runPurposeIssues = [];
      const runPurpose = normalizePurpose(runPurposeValue(runDocument.value), "run.purpose", runPurposeIssues);
      issues.push(...runPurposeIssues);
      addExpectedIssue(issues, "purpose", purpose, runPurpose, "PURPOSE_MISMATCH", "The QA handoff purpose differs from the admitted run.");
      addExpectedIssue(issues, "completion_marker", completionMarker, completionMarkerForPurpose(runPurpose), "COMPLETION_MARKER_MISMATCH", "The QA handoff completion marker differs from the admitted purpose.");
      const runSource = isMapping(runDocument.value.source) ? runDocument.value.source : {};
      const runSourceDigest = runSource.digest ?? runSource.tickets_digest;
      if (runSourceDigest) addExpectedIssue(issues, "source.tickets_digest", String(runSourceDigest).toLowerCase(), sourceDigest, "DIGEST_MISMATCH", "The QA source digest is stale.");
      const runProposal = proposalProjection(runDocument.value);
      if (!options.historical && source.proposal_required !== undefined && source.proposal_required !== runProposal.required) issues.push(issue("source.proposal_required", "PROPOSAL_REQUIREMENT_MISMATCH", source.proposal_required, runProposal.required, "The QA proposal admission flag differs from the admitted run."));
      if (runProposal.required) {
        if (!proposalPath) issues.push(issue("source.proposal_path", "MISSING_PROPOSAL_PATH", null, "required canonical proposal path", "The QA handoff omitted a required proposal identity."));
        else if (runProposal.path) addExpectedIssue(issues, "source.proposal_path", await canonicalPath(proposalPath), await canonicalPath(runProposal.path), "PROPOSAL_PATH_MISMATCH", "The QA proposal path differs from the admitted run.");
        if (!proposalDigest) issues.push(issue("source.proposal_digest", "MISSING_PROPOSAL_DIGEST", null, "sha256:<64 hex characters>", "The QA handoff omitted a required proposal digest."));
        else if (runProposal.digest) addExpectedIssue(issues, "source.proposal_digest", proposalDigest, String(runProposal.digest).toLowerCase(), "DIGEST_MISMATCH", "The QA proposal digest differs from the admitted run.");
      }
      if (proposalPath && proposalDigest) await validatePathDigest("source.proposal_path", proposalPath, proposalDigest, issues);
      if (!options.historical) addExpectedIssue(issues, "state.current", actualRunState(runDocument.value), state.current ?? "QA", "RUN_STATE_MISMATCH", "The QA handoff is not for the current run state.");
    } catch (error) { issues.push(issue("artifact.run_dir/run.yaml", error.code ?? "RUN_READ_FAILED", runPath, "readable run.yaml", error.message)); }
  } else if (runPath) issues.push(issue("artifact.run_dir/run.yaml", "PATH_NOT_FOUND", runPath, "existing run.yaml", "The QA handoff needs an authoritative run record."));
  for (const [field, path] of [["artifact.handoff_path", handoffArtifactPath], ["artifact.operation_path", operationPath], ["artifact.report_path", reportPath]]) {
    if (path && runDir && !pathIsInside(await canonicalPath(path), await canonicalPath(runDir))) issues.push(issue(field, "PATH_OUTSIDE_RUN", path, `path inside ${runDir}`, "QA artifacts must remain in the run namespace."));
  }
  if (evidenceDirectory && runDir && !pathIsInside(await canonicalPath(evidenceDirectory), await canonicalPath(runDir))) issues.push(issue("artifact.evidence_directory", "PATH_OUTSIDE_RUN", evidenceDirectory, `path inside ${runDir}`, "QA evidence must remain in the run namespace."));
  if (!options.historical && reportPath && !(await pathExists(dirname(reportPath)))) issues.push(issue("artifact.report.parent", "REPORT_PARENT_REQUIRED", dirname(reportPath), "existing report parent directory", "QA preparation must provision the report parent before bind."));
  if (!options.historical && evidenceDirectory && !(await pathExists(evidenceDirectory))) issues.push(issue("artifact.evidence_directory", "EVIDENCE_DIRECTORY_REQUIRED", evidenceDirectory, "existing evidence directory", "QA preparation must provision the evidence directory before bind."));
  if (handoffArtifactPath) addExpectedIssue(issues, "artifact.handoff_path", await canonicalPath(handoffArtifactPath), await canonicalPath(handoffPath), "HANDOFF_PATH_MISMATCH", "The QA artifact does not point to the handoff being validated.");
  if (handoff.report?.path && reportPath) addExpectedIssue(issues, "report.path", await canonicalPath(handoff.report.path), await canonicalPath(reportPath), "REPORT_PATH_MISMATCH", "The QA report projection differs from the artifact report path.");
  if (reportPath && await pathExists(reportPath) && handoff.report?.expected === "CREATE" && !options.historical) issues.push(issue("artifact.report_path", "REPORT_SNAPSHOT_STALE", reportPath, "report absent at handoff creation", "Generate a fresh QA handoff for a new report."));
  if (targetRoot && targetRepositoryId && targetBranch && targetHead) {
    try {
      const snapshot = await gitSnapshot(targetRoot);
      const canonicalTargetRoot = await canonicalPath(targetRoot);
      check(checks, "target.repository_root", snapshot.root, canonicalTargetRoot);
      addExpectedIssue(issues, "target.repository_root", snapshot.root, canonicalTargetRoot, "REPOSITORY_ROOT_MISMATCH", "The QA target root differs from the handoff.");
      check(checks, "target.repository_id", snapshot.repository_id, targetRepositoryId);
      addExpectedIssue(issues, "target.repository_id", snapshot.repository_id, targetRepositoryId, "REPOSITORY_ID_MISMATCH", "The QA target repository identity differs from the handoff.");
      check(checks, "target.branch", snapshot.branch, targetBranch);
      addExpectedIssue(issues, "target.branch", snapshot.branch, targetBranch, "BRANCH_MISMATCH", "The QA target branch differs from the handoff.");
      const resolvedHead = await resolveGitRevision(targetRoot, targetHead, "target.head");
      if (!options.historical) {
        check(checks, "target.head", snapshot.head, resolvedHead);
        addExpectedIssue(issues, "target.head", snapshot.head, resolvedHead, "TARGET_HEAD_MISMATCH", "The active QA target HEAD differs from the handoff.");
      }
      if (!options.historical && snapshot.dirty) issues.push(issue("target.dirty", "TARGET_DIRTY", true, false, "The target must be clean for an active QA handoff."));
    } catch (error) { issues.push(issue("target", error.code ?? "GIT_VALIDATION_FAILED", error.message, "valid target identity", "The QA target could not be verified.")); }
  }
  if (operationPath && await pathExists(operationPath)) {
    const operationDocument = await readYamlFile(operationPath);
    addExpectedIssue(issues, "operation.id", operationDocument.value.operation_id, operationId, "OPERATION_ID_MISMATCH", "The QA operation differs from the handoff.");
    addExpectedIssue(issues, "operation.instance_id", operationDocument.value.operation_instance_id, operationInstanceId, "OPERATION_INSTANCE_ID_MISMATCH", "The QA operation instance differs from the handoff.");
    addExpectedIssue(issues, "operation.attempt_id", operationDocument.value.attempt_id, attemptId, "ATTEMPT_ID_MISMATCH", "The QA operation attempt differs from the handoff.");
  } else if (operationPath && options.requireOperation !== false) issues.push(issue("artifact.operation_path", "PATH_NOT_FOUND", operationPath, "existing QA operation", "The QA dispatch operation must be durable before binding an agent."));
  if (issues.length > 0) {
    const result = { valid: false, handoff_path: handoffPath, checks, errors: issues };
    if (options.throwOnInvalid !== false) fail("QA_HANDOFF_INVALID", `QA handoff validation failed: ${handoffPath}`, { errors: issues, checks });
    return result;
  }
  return { valid: true, handoff_path: handoffPath, checks, errors: [] };
}

export async function validateHandoffFile(handoffPath, options = {}) {
  const document = await readYamlFile(handoffPath);
  const result = document.value?.kind === "squad-qa-handoff"
    ? await validateQaHandoffData(document.value, document.file, options)
    : await validateHandoffData(document.value, document.file, options);
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
    proposal: proposalProjection(run),
    stateWorktree,
    worktreePath,
  };
}

function runDirectoryFromStatePath(statePath) {
  return dirname(dirname(dirname(resolve(statePath))));
}

function operationInstanceIdFor(operationId, attemptNumber) {
  const attempt = String(attemptNumber).replace(/^attempt-/, "").padStart(3, "0");
  return `${operationId}:attempt-${attempt}`;
}

function operationPathFor(runDirectory, operationId, operationInstanceId = operationId) {
  return join(runDirectory, "operations", `${operationInstanceId}.yaml`);
}

async function resolveOperationPath(runDirectory, operationId, operationInstanceId = undefined) {
  if (operationInstanceId) return operationPathFor(runDirectory, operationId, operationInstanceId);
  const legacyPath = operationPathFor(runDirectory, operationId);
  if (await pathExists(legacyPath)) return legacyPath;
  const candidates = (await readOperationFiles(runDirectory)).filter((entry) => entry.value?.operation_id === operationId);
  if (candidates.length === 1) return candidates[0].path;
  if (candidates.length > 1) {
    fail("AMBIGUOUS_OPERATION", `More than one operation instance matches ${operationId}.`, {
      operation_id: operationId,
      candidates: candidates.map((entry) => ({ path: entry.path, operation_instance_id: entry.value?.operation_instance_id, attempt_id: entry.value?.attempt_id })),
    });
  }
  return legacyPath;
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

async function buildReviewerContext(context, currentState) {
  const reports = await findReports(context.runDirectory, context.unitId);
  const workerReports = reports.filter((entry) => entry.value?.role === "squad-worker" || entry.value?.role === "worker");
  const reviewerReports = reports.filter((entry) => entry.value?.role === "squad-reviewer" || entry.value?.role === "reviewer");
  const latestWorker = workerReports.at(-1) ?? null;
  const latestReviewHistory = reviewerReports.map((entry) => ({ path: entry.path, digest: entry.digest, attempt_id: entry.value?.attempt_id ?? null, status: entry.value?.status ?? null, verdict: entry.value?.verdict ?? entry.value?.review?.verdict ?? null, reviewed_revision: entry.value?.reviewer?.final_revision ?? entry.value?.final_revision ?? entry.value?.reviewed_revision ?? null }));
  const workerOperation = (await readOperationFiles(context.runDirectory)).filter((entry) => entry.value?.work_unit_id === context.unitId && /(?:DISPATCH|RESUME)_WORKER$/.test(String(entry.value?.type ?? "")) && (!latestWorker?.value?.attempt_id || entry.value?.attempt_id === latestWorker.value.attempt_id)).at(-1) ?? null;
  const activeWorkerHandoff = [...(Array.isArray(context.state.handoff_history) ? context.state.handoff_history : [])].reverse().find((entry) => entry.role === "worker" || entry.role === "squad-worker") ?? null;
  const lastWorkerCompletion = context.state.last_completion?.role === "worker" ? context.state.last_completion : null;
  const workerReportPath = latestWorker?.path ?? lastWorkerCompletion?.report_path ?? activeWorkerHandoff?.report_path ?? null;
  const workerReportDigest = latestWorker?.digest ?? lastWorkerCompletion?.report_digest ?? activeWorkerHandoff?.report_digest ?? null;
  const workerRevision = context.state.implementation_revision ?? lastWorkerCompletion?.revision ?? activeWorkerHandoff?.revision ?? null;
  const reviewerContext = {
    work_unit_type: context.state.work_unit_type ?? (context.unitId.startsWith("REM-") ? "REMEDIATION" : "TICKET"),
    purpose: runPurposeValue(context.run),
    completion_marker: completionMarkerForPurpose(runPurposeValue(context.run)),
    proposal: context.proposal,
    worker: { report_path: workerReportPath, report_digest: workerReportDigest, revision: workerRevision, attempt_id: latestWorker?.value?.attempt_id ?? activeWorkerHandoff?.attempt_id ?? null, operation_id: workerOperation?.value?.operation_id ?? null, operation_instance_id: workerOperation?.value?.operation_instance_id ?? workerOperation?.value?.operation_id ?? null, job_id: workerOperation?.value?.job_id ?? null, changed_scope: latestWorker?.value?.changed_scope ?? latestWorker?.value?.changed_paths ?? context.state.changed_scope ?? null, validation: latestWorker?.value?.validation ?? context.state.last_completion?.validation ?? context.state.completion?.validation ?? null },
    prior_reviews: latestReviewHistory,
    transition: { current_state: currentState, last_transition_id: context.state.last_transition_id ?? null, last_operation_id: context.state.last_operation_id ?? null, integration: context.state.integration ?? null },
    environment: environmentAdmissionProjection(context.run),
    report_schema: { role: "squad-reviewer", status: "COMPLETE", verdicts: ["APPROVED", "REJECTED", "INCONCLUSIVE"], exact_revision_required: true },
  };
  const workerReportReadable = reviewerContext.worker.report_path ? await pathExists(reviewerContext.worker.report_path) : false;
  if (currentState === "AWAITING_REVIEW" && (!workerReportReadable || !reviewerContext.worker.report_digest || !reviewerContext.worker.revision)) fail("HANDOFF_CONTEXT_REQUIRED", `Reviewer context is incomplete for ${context.unitId}.`, { work_unit_id: context.unitId, expected: ["readable worker report path", "worker report digest", "implementation revision"], actual: reviewerContext.worker });
  return reviewerContext;
}

export async function buildExecutionManifest(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const statePath = resolve(options.state ?? "");
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required for manifest generation.");
  const context = await readTicketAndRunContext(runPath, statePath, options.ticket);
  const admissionIssues = [];
  await validateRunAdmissionContext(context.run, [], admissionIssues);
  if (admissionIssues.length > 0) fail("PREFLIGHT_FAILED", `Run admission context is incomplete: ${runPath}`, { issues: admissionIssues });
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
  const operationInstanceId = options.operation_instance_id ?? operationInstanceIdFor(operationId, attemptNumber);
  const operationPath = operationPathFor(context.runDirectory, operationId, operationInstanceId);
  const manifestPath = resolve(options.output ?? defaultManifestPath(context.runDirectory, context.unitId, roleKey, attemptNumber));
  const handoffPath = resolve(options.handoff ?? defaultHandoffPath(context.runDirectory, context.unitId, roleKey, attemptNumber));
  const reportPath = resolve(options.report ?? defaultReportPath(context.runDirectory, context.unitId, roleKey, attemptNumber));
  const evidenceDirectory = resolve(options.evidence ?? defaultEvidenceDirectory(context.runDirectory, context.unitId, roleKey, attemptNumber));
  for (const [field, path] of [["artifact.state_path", statePath], ["artifact.manifest_path", manifestPath], ["artifact.handoff_path", handoffPath], ["artifact.operation_path", operationPath], ["artifact.report_path", reportPath], ["artifact.evidence_directory", evidenceDirectory]]) await assertArtifactPathInsideRun(path, context.runDirectory, field);
  await mkdir(dirname(reportPath), { recursive: true });
  await mkdir(evidenceDirectory, { recursive: true });
  const dependencies = await stateDependencySnapshot(statePath, context.state);
  const unfinishedDependencies = dependencies.filter((dependency) => dependency.actual_state !== "DONE");
  if (unfinishedDependencies.length > 0) {
    fail("DEPENDENCY_NOT_DONE", `Work unit ${context.unitId} cannot be dispatched with unfinished dependencies.`, { field: "dependencies", actual: unfinishedDependencies.map((dependency) => ({ work_unit_id: dependency.work_unit_id, state: dependency.actual_state })), expected: "all dependencies DONE" });
  }
  const currentState = actualStateFromDocument(context.state);
  if (!UNIT_STATES.includes(currentState)) fail("INVALID_STATE", `Unknown work-unit state: ${currentState ?? "<missing>"}`, { field: "state", actual: currentState ?? null, expected: UNIT_STATES });
  const reviewerContext = roleKey === "reviewer" ? await buildReviewerContext(context, currentState) : null;
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
    ...(roleKey === "analysis" ? { analysis_id: options.analysis_id ?? `${context.runId}:${context.unitId}:analysis:attempt-${attemptNumber}` } : {}),
    ...(roleKey === "reviewer" ? { reviewer_context: reviewerContext } : {}),
    environment: environmentAdmissionProjection(context.run),
    attempt_number: Number(attemptNumber),
    attempt_id: attemptId,
    source: {
      tickets_index_path: context.ticketsPath,
      tickets_digest: sourceDigest,
      work_unit_path: context.ticketPath,
      ticket_digest: ticketDigest,
      proposal_required: context.proposal?.required === true,
      ...(context.proposal?.path ? { proposal_path: resolve(context.proposal.path), proposal_digest: context.proposal.digest ?? null } : {}),
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
      instance_id: operationInstanceId,
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
      purpose: options.purpose ?? context.state.purpose ?? runPurposeValue(context.run),
      mode: options.mode ?? context.state.worker_mode ?? context.run.worker_mode ?? null,
      completion_marker: completionMarkerForPurpose(options.purpose ?? context.state.purpose ?? runPurposeValue(context.run)),
      scope: options.scope ?? context.state.scope ?? null,
      authority: options.authority ?? context.run.authority ?? null,
      environment: context.run.environment ?? null,
      reference_snapshots: context.state.reference_snapshots ?? context.run.reference_snapshots ?? [],
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
    operation_instance_id: manifest.operation.instance_id,
    source: {
      tickets_index_path: manifest.source.tickets_index_path,
      tickets_digest: manifest.source.tickets_digest,
      work_unit_path: manifest.source.work_unit_path,
      ticket_digest: manifest.source.ticket_digest,
      proposal_required: manifest.source.proposal_required === true,
      ...(manifest.source.proposal_path ? { proposal_path: manifest.source.proposal_path, proposal_digest: manifest.source.proposal_digest ?? null } : {}),
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
    environment: manifest.environment ?? environmentAdmissionProjection({}),
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
      instance_id: manifest.operation.instance_id,
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
    ...(roleKey === "reviewer" ? { reviewer_context: manifest.reviewer_context } : {}),
    manifest: {
      path: manifest.artifact.manifest_path,
      digest: manifestDigest,
    },
  };
  if (roleKey === "reviewer") {
    handoff.implementation_revision = manifest.worktree.current_head;
  }
  if (roleKey === "analysis") {
    handoff.analysis_id = manifest.analysis_id;
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
    operation_instance_id: manifest.operation.instance_id,
    work_unit_id: manifest.work_unit_id,
    attempt_id: manifest.attempt_id,
    type: manifest.operation.type,
    status,
    job_id: null,
    agent_provider: null,
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
    if (existingValue.operation_id !== operation.operation_id || (existingValue.operation_instance_id ?? existingValue.operation_id) !== operation.operation_instance_id || existingValue.attempt_id !== operation.attempt_id || existingValue.type !== operation.type) {
      fail("OPERATION_IDENTITY_CONFLICT", `Operation path is already owned by another attempt: ${operationPath}`, { field: "operation_path", actual: { operation_id: existingValue.operation_id, operation_instance_id: existingValue.operation_instance_id, attempt_id: existingValue.attempt_id, type: existingValue.type }, expected: { operation_id: operation.operation_id, operation_instance_id: operation.operation_instance_id, attempt_id: operation.attempt_id, type: operation.type } });
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

export async function commitUnitTransition({ statePath, workUnitId, from, to, reason, operationId = null, operationInstanceId = null, extraSets = [], allowUnresolvedOperation = false }) {
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
    if (operationInstanceId && (!operationInstanceId.startsWith(`${operationId}:attempt-`) || !/:attempt-[0-9]{3,6}$/.test(operationInstanceId))) fail("INVALID_OPERATION_INSTANCE_ID", `Invalid transition operation instance: ${operationInstanceId}`, { field: "operation_instance_id", actual: operationInstanceId, expected: `${operationId}:attempt-<NNN>` });
    const operationPath = await resolveOperationPath(runDirectory, operationId, operationInstanceId);
    if (!(await pathExists(operationPath))) fail("OPERATION_NOT_FOUND", `Transition trigger operation is not durable: ${operationInstanceId ?? operationId}`, { field: "operation_instance_id", actual: operationInstanceId ?? null, expected: "existing operation ledger" });
    const operationDocument = await readYamlFile(operationPath);
    if (operationDocument.value.operation_id !== operationId) fail("OPERATION_ID_MISMATCH", "Transition trigger does not match its operation file.", { field: "operation_id", actual: operationDocument.value.operation_id, expected: operationId });
    if (operationInstanceId && (operationDocument.value.operation_instance_id ?? operationDocument.value.operation_id) !== operationInstanceId) fail("OPERATION_INSTANCE_ID_MISMATCH", "Transition trigger does not match its operation instance file.", { field: "operation_instance_id", actual: operationDocument.value.operation_instance_id ?? operationDocument.value.operation_id, expected: operationInstanceId });
    if (!OPERATION_STATES.includes(operationDocument.value.status)) fail("INVALID_OPERATION_STATUS", `Transition trigger operation has invalid status: ${operationDocument.value.status}`, { status: operationDocument.value.status, expected: OPERATION_STATES });
    if (!allowUnresolvedOperation && ["UNKNOWN", "RECONCILING"].includes(operationDocument.value.status)) fail("OPERATION_REQUIRES_RECONCILIATION", `Transition trigger operation ${operationId} is ${operationDocument.value.status}.`, { operation_id: operationId, operation_instance_id: operationInstanceId, status: operationDocument.value.status, expected: "conclusive operation status" });
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
    trigger: operationId ? { operation_id: operationId, operation_instance_id: operationInstanceId } : null,
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

export async function commitRunTransition({ runPath, runId = null, from, to, reason, extraSets = [], controller = null }) {
  const resolvedRunPath = resolve(runPath);
  const runDocument = await readRunDocument(resolvedRunPath);
  const actualRunId = runId ?? runDocument.run_id;
  if (actualRunId !== runDocument.run_id) fail("RUN_ID_MISMATCH", `Run file contains ${runDocument.run_id}, not ${actualRunId}.`, { field: "run_id", actual: runDocument.run_id, expected: actualRunId });
  const currentState = actualRunState(runDocument.value);
  validateRunTransitionShape({ from, to }, currentState, []);
  if (!RUN_STATES.includes(from) || !RUN_STATES.includes(to)) fail("INVALID_RUN_STATE", `Unknown run transition: ${from} -> ${to}`, { from, to, expected: RUN_STATES });
  if (currentState !== from) fail("RUN_TRANSITION_SOURCE_MISMATCH", `Run is ${currentState ?? "<missing>"}, not ${from}.`, { field: "from", actual: currentState ?? null, expected: from });
  if (!LEGAL_RUN_TRANSITIONS[from].includes(to)) fail("ILLEGAL_RUN_TRANSITION", `Illegal run transition: ${from} -> ${to}`, { from, to, legal_to: LEGAL_RUN_TRANSITIONS[from] });
  if (!asString(reason)) fail("MISSING_ARGUMENT", "--reason is required for a run transition.", { field: "reason", actual: reason ?? null, expected: "non-empty reason" });
  if (to === "QA" && controller !== "prepare-qa") fail("RUN_QA_PREPARATION_REQUIRED", "Only prepare-qa may enter the run-level QA state.", { from, to, required_command: "prepare-qa" });
  if (to === "COMPLETING" && controller !== "complete-qa") fail("RUN_QA_COMPLETION_REQUIRED", "Only complete-qa may enter COMPLETING.", { from, to, required_command: "complete-qa" });
  if (to === "RUN_COMPLETED" && controller !== "complete-run") fail("RUN_COMPLETION_REQUIRED", "Only complete-run may terminalize a run as RUN_COMPLETED.", { from, to, required_command: "complete-run" });
  if (from === "PAUSED" && to === "EXECUTING" && controller !== "resume-run") fail("RUN_RESUME_REQUIRED", "Only resume-run may resume a paused run.", { from, to, required_command: "resume-run" });
  if (to === "RUN_VALIDATING") {
    const artifacts = await allRunArtifacts(resolvedRunPath);
    const incomplete = artifacts.units.filter((unit) => !unit.value || actualStateFromDocument(unit.value) !== "DONE");
    if (artifacts.units.length === 0) fail("NO_WORK_UNITS", "Run validation requires at least one in-scope work unit.");
    if (incomplete.length > 0) fail("WORK_UNITS_INCOMPLETE", "Run validation cannot start until every in-scope work unit is DONE.", { work_units: incomplete.map((unit) => ({ work_unit_id: normalizeUnitId(unit.value), state: actualStateFromDocument(unit.value) })) });
  }
  const runDirectory = dirname(resolvedRunPath);
  const existing = await readTransitionFiles(runDirectory);
  const unresolvedTransitions = existing.filter((item) => item.value?.entity_type === "RUN" && item.value?.entity === actualRunId && !["COMMITTED", "ABORTED"].includes(item.value?.status));
  if (unresolvedTransitions.length > 0) fail("TRANSITION_REQUIRES_RECONCILIATION", "A prior run transition is not terminal; reconcile it before creating another run transition.", { run_id: actualRunId, transitions: unresolvedTransitions.map((item) => ({ path: item.path, transition_id: item.value?.transition_id, status: item.value?.status })) });
  const prefix = `TR-${actualRunId}-RUN-`;
  const escapedPrefix = prefix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const sequence = existing.reduce((max, item) => {
    if (item.value?.entity !== actualRunId || item.value?.entity_type !== "RUN") return max;
    const match = item.value?.transition_id?.match(new RegExp(`^${escapedPrefix}([0-9]{4})$`));
    return match ? Math.max(max, Number(match[1])) : max;
  }, 0) + 1;
  const transitionId = `${prefix}${String(sequence).padStart(4, "0")}`;
  const transitionPath = join(runDirectory, "transitions", `${transitionId}.yaml`);
  const prepared = {
    schema_version: 1,
    transition_id: transitionId,
    entity_type: "RUN",
    entity: actualRunId,
    from,
    to,
    status: "PREPARED",
    reason,
    source: { run_path: resolvedRunPath, run_digest: runDocument.digest },
    trigger: null,
    checkpoint_id: `CP-${transitionId}`,
  };
  const created = await writeImmutableYaml(transitionPath, prepared);
  const preparedDocument = await readYamlFile(transitionPath);
  const committing = await updateYamlFile(transitionPath, preparedDocument.digest, [{ pointer: "/status", value: "COMMITTING" }]);
  try {
    const currentRunDocument = await readRunDocument(resolvedRunPath);
    if (actualRunState(currentRunDocument.value) !== from) fail("RUN_TRANSITION_SOURCE_MISMATCH", "Run state changed before transition commit.", { actual: actualRunState(currentRunDocument.value), expected: from });
    const history = Array.isArray(currentRunDocument.value.transition_history) ? [...currentRunDocument.value.transition_history] : [];
    history.push({ transition_id: transitionId, from, to, reason });
    const runStateSets = [{ pointer: "/state", value: to }];
    if (to === "PAUSED") runStateSets.push({ pointer: "/paused_from_state", value: from });
    if (from === "PAUSED" && to === "EXECUTING") runStateSets.push({ pointer: "/paused_from_state", value: null });
    if (!Object.prototype.hasOwnProperty.call(currentRunDocument.value, "state") && Object.prototype.hasOwnProperty.call(currentRunDocument.value, "status")) runStateSets.push({ pointer: "/status", value: to });
    if (!Object.prototype.hasOwnProperty.call(currentRunDocument.value, "state") && Object.prototype.hasOwnProperty.call(currentRunDocument.value, "run_state")) runStateSets.push({ pointer: "/run_state", value: to });
    const stateAfter = await updateYamlFile(resolvedRunPath, currentRunDocument.digest, [
      ...runStateSets,
      { pointer: "/last_transition_id", value: transitionId },
      { pointer: "/transition_history", value: history },
      ...extraSets,
    ]);
    const committingDocument = await readYamlFile(transitionPath);
    const committed = await updateYamlFile(transitionPath, committingDocument.digest, [{ pointer: "/status", value: "COMMITTED" }, { pointer: "/committed_run_digest", value: stateAfter.digest }]);
    const finalRun = await readRunDocument(resolvedRunPath);
    const finalTransition = await readYamlFile(transitionPath);
    if (actualRunState(finalRun.value) !== to || finalTransition.value.status !== "COMMITTED") fail("RUN_TRANSITION_VERIFY_FAILED", `Run transition ${transitionId} did not verify.`, { transition_id: transitionId, run_state: actualRunState(finalRun.value), transition_status: finalTransition.value.status, expected_state: to, expected_transition_status: "COMMITTED" });
    return { transition_id: transitionId, transition_path: transitionPath, status: "COMMITTED", state_digest: finalRun.digest, transition_digest: finalTransition.digest, changed: created.changed || committing.changed || committed.changed };
  } catch (error) {
    fail("RUN_TRANSITION_INCOMPLETE", `Run transition ${transitionId} requires reconciliation: ${error.message}`, { transition_id: transitionId, transition_path: transitionPath, run_path: resolvedRunPath, ...(error.details ?? {}) });
  }
}

export async function reconcileRunTransition({ runPath, transitionPath = null }) {
  const resolvedRunPath = resolve(runPath);
  const runDocument = await readRunDocument(resolvedRunPath);
  const runDirectory = dirname(resolvedRunPath);
  const candidates = (await readTransitionFiles(runDirectory)).filter((entry) => entry.value?.entity_type === "RUN" && entry.value?.entity === runDocument.run_id && !["COMMITTED", "ABORTED"].includes(entry.value?.status));
  let candidate;
  if (transitionPath) {
    candidate = candidates.find((entry) => resolve(entry.path) === resolve(transitionPath));
    if (!candidate) {
      const document = await readYamlFile(transitionPath);
      candidate = { path: resolve(transitionPath), value: document.value, digest: document.digest };
    }
  } else if (candidates.length === 1) candidate = candidates[0];
  else if (candidates.length > 1) fail("AMBIGUOUS_RUN_TRANSITION", "More than one run transition requires reconciliation; supply --transition.", { run_id: runDocument.run_id, candidates: candidates.map((entry) => ({ path: entry.path, transition_id: entry.value?.transition_id, status: entry.value?.status })) });
  if (!candidate?.value) fail("RUN_TRANSITION_NOT_FOUND", "No uncommitted run transition requires reconciliation.", { run_id: runDocument.run_id, transition_path: transitionPath });
  const transition = candidate.value;
  if (["COMMITTED", "ABORTED"].includes(transition.status)) return { run_id: runDocument.run_id, transition_id: transition.transition_id, transition_path: candidate.path, status: transition.status, outcome: "ALREADY_TERMINAL", current_state: actualRunState(runDocument.value), digest: candidate.digest, next_action: "VERIFY_RUN" };
  if (transition.entity_type !== "RUN" || transition.entity !== runDocument.run_id) fail("RUN_TRANSITION_IDENTITY_MISMATCH", "The selected transition does not belong to this run.", { actual: { entity_type: transition.entity_type ?? null, entity: transition.entity ?? null }, expected: { entity_type: "RUN", entity: runDocument.run_id } });
  const currentState = actualRunState(runDocument.value);
  let status;
  let outcome;
  if (currentState === transition.to) {
    status = "COMMITTED";
    outcome = "EFFECT_APPLIED";
  } else if (currentState === transition.from) {
    status = "ABORTED";
    outcome = "EFFECT_ABSENT";
  } else {
    status = "UNKNOWN";
    outcome = "INCONCLUSIVE";
  }
  const reconciliation = { observed_at: new Date().toISOString(), outcome, current_run_state: currentState, recorded_from: transition.from, recorded_to: transition.to, authoritative: status === "COMMITTED" || status === "ABORTED" };
  const updated = await updateYamlFile(candidate.path, candidate.digest, [{ pointer: "/status", value: status }, { pointer: "/reconciliation", value: reconciliation }, ...(status === "COMMITTED" ? [{ pointer: "/committed_run_digest", value: runDocument.digest }] : [])]);
  return { run_id: runDocument.run_id, transition_id: transition.transition_id, transition_path: candidate.path, status, outcome, current_state: currentState, digest: updated.digest, next_action: status === "COMMITTED" ? "VERIFY_RUN" : status === "ABORTED" ? "RETRY_TYPED_TRANSITION" : "ESCALATE_RUN_TRANSITION" };
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

function proposalProjection(run) {
  const source = isMapping(run?.source) ? run.source : {};
  const proposal = isMapping(run?.proposal) ? run.proposal : (isMapping(source.proposal) ? source.proposal : {});
  return {
    required: run?.proposal_required === true || run?.admission?.proposal_required === true,
    path: proposal.path ?? proposal.proposal_path ?? source.proposal_path ?? null,
    digest: proposal.digest ?? proposal.proposal_digest ?? source.proposal_digest ?? null,
  };
}

function environmentProfileRequired(run) {
  const admission = isMapping(run?.admission) ? run.admission : {};
  if (run?.environment_profile_required === true || admission.environment_profile_required === true) return true;
  if (run?.environment_profile_required === false || admission.environment_profile_required === false) return false;
  return Number(run?.control_plane_version ?? 0) >= 2;
}

function environmentAdmissionProjection(run) {
  const required = environmentProfileRequired(run);
  return {
    required,
    admission: required ? "REQUIRED" : (Number(run?.control_plane_version ?? 0) < 2 ? "ADVISORY_LEGACY" : "ADVISORY"),
    profile_path: run?.environment?.profile_path ?? null,
    profile_digest: run?.environment?.profile_digest ?? null,
    fingerprint: run?.environment?.fingerprint ?? null,
  };
}

async function validateRunAdmissionContext(run, checks, issues) {
  const purpose = normalizePurpose(runPurposeValue(run), "purpose", issues);
  const explicitPurpose = run?.purpose ?? (isMapping(run?.admission) ? run.admission.purpose : undefined);
  const workerMode = run?.worker_mode ?? (isMapping(run?.admission) ? run.admission.worker_mode : undefined);
  if (purpose === "production" && explicitPurpose !== undefined && (workerMode === undefined || workerMode === null)) {
    issues.push(issue("worker_mode", "IMPLEMENTATION_MODE_REQUIRED", null, PRODUCTION_IMPLEMENTATION_MODES, "An explicit production purpose requires default or tdd worker mode."));
  }
  if (workerMode !== undefined && workerMode !== null && !PRODUCTION_IMPLEMENTATION_MODES.includes(workerMode)) {
    issues.push(issue("worker_mode", "INVALID_IMPLEMENTATION_MODE", workerMode, PRODUCTION_IMPLEMENTATION_MODES, "Production worker mode must be default or tdd."));
  }
  if (purpose === "prototype" && workerMode !== undefined && workerMode !== null) {
    issues.push(issue("worker_mode", "PROTOTYPE_MODE_NOT_ALLOWED", workerMode, null, "Prototype purpose does not select a production implementation mode."));
  }
  const proposal = proposalProjection(run);
  if (proposal.required && !proposal.path) issues.push(issue("proposal.path", "MISSING_PROPOSAL_PATH", null, "required canonical proposal path", "This run profile requires a canonical proposal artifact."));
  if (proposal.path) {
    const proposalPath = resolve(proposal.path);
    if (!(await pathExists(proposalPath))) issues.push(issue("proposal.path", "PATH_NOT_FOUND", proposalPath, "existing proposal artifact", "The recorded proposal path cannot be read."));
    else {
      const actualDigest = await digestFile(proposalPath);
      if (!proposal.digest) issues.push(issue("proposal.digest", "MISSING_PROPOSAL_DIGEST", null, "sha256:<64 hex characters>", "The recorded proposal has no immutable digest."));
      else {
        const normalized = normalizeDigest(String(proposal.digest), "proposal.digest", issues);
        if (normalized) {
          check(checks, "proposal.digest", actualDigest, normalized);
          addExpectedIssue(issues, "proposal.digest", actualDigest, normalized, "DIGEST_MISMATCH", "The canonical proposal changed after admission.");
        }
      }
    }
  } else if (proposal.digest) issues.push(issue("proposal.path", "PROPOSAL_PATH_REQUIRED", null, "path for recorded proposal digest", "A proposal digest cannot be recorded without its source path."));

  const environmentRequired = environmentProfileRequired(run);
  if (!environmentRequired) return;
  const environment = isMapping(run?.environment) ? run.environment : {};
  if (!environment.profile_path) {
    issues.push(issue("environment.profile_path", "MISSING_ENVIRONMENT_PROFILE", null, "run environment profile path", "This run profile requires an environment profile before dispatch."));
    return;
  }
  const profilePath = resolve(environment.profile_path);
  if (!(await pathExists(profilePath))) {
    issues.push(issue("environment.profile_path", "PATH_NOT_FOUND", profilePath, "existing environment profile", "The required environment profile cannot be read."));
    return;
  }
  const actualDigest = await digestFile(profilePath);
  if (!environment.profile_digest) issues.push(issue("environment.profile_digest", "MISSING_ENVIRONMENT_PROFILE_DIGEST", null, "sha256:<64 hex characters>", "The environment profile must be digest-bound."));
  else {
    const normalized = normalizeDigest(String(environment.profile_digest), "environment.profile_digest", issues);
    if (normalized) {
      check(checks, "environment.profile_digest", actualDigest, normalized);
      addExpectedIssue(issues, "environment.profile_digest", actualDigest, normalized, "DIGEST_MISMATCH", "The environment profile changed after admission.");
    }
  }
  try {
    const profile = await readYamlFile(profilePath);
    addExpectedIssue(issues, "environment.profile.run_id", profile.value?.run_id, run.run_id, "RUN_ID_MISMATCH", "The environment profile belongs to another run.");
    if (profile.value?.fingerprint) normalizeDigest(profile.value.fingerprint, "environment.fingerprint", issues);
  } catch (error) {
    issues.push(issue("environment.profile_path", error.code ?? "ENVIRONMENT_PROFILE_READ_FAILED", profilePath, "readable environment profile", error.message));
  }
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
        if (targetHead && currentState !== "DONE") {
          const mergeBase = await runGit(path, ["merge-base", currentRevision, targetHead]);
          if (baseline !== mergeBase.stdout) issues.push(issue(`${unit.path}:worktree.baseline`, "BASELINE_MERGE_BASE_MISMATCH", baseline, mergeBase.stdout, "The recorded baseline is not the Git merge-base of the active worktree and target HEAD."));
        } else if (currentState === "DONE" && !isMapping(state.integration)) {
          issues.push(issue(`${unit.path}:integration`, "INTEGRATION_SNAPSHOT_REQUIRED", null, "integration.target_before and integration.target_after", "A completed work unit must retain an immutable integration snapshot."));
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

export async function preflightRun(runPath, { focusUnitId = null } = {}) {
  const artifacts = await allRunArtifacts(resolve(runPath));
  const run = artifacts.runDocument.value;
  const runId = artifacts.runDocument.run_id;
  const issues = [];
  let runState;
  try {
    runState = actualRunState(run);
    if (!RUN_STATES.includes(runState)) issues.push(issue("run.state", "INVALID_RUN_STATE", runState ?? null, RUN_STATES, "The run projection has no legal lifecycle state."));
  } catch (error) {
    issues.push(issue("run.state", error.code ?? "AMBIGUOUS_RUN_STATE", run.state ?? run.status ?? null, RUN_STATES, error.message));
  }
  const checks = [];
  await validateRunAdmissionContext(run, checks, issues);
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
    if (state.purpose !== undefined && state.purpose !== null && !PURPOSES.includes(state.purpose)) issues.push(issue(`${unit.path}:purpose`, "INVALID_PURPOSE", state.purpose, PURPOSES, "Unit state purpose must be production or prototype."));
    if (state.purpose !== undefined && state.purpose !== null && PURPOSES.includes(state.purpose) && state.purpose !== runPurposeValue(run)) issues.push(issue(`${unit.path}:purpose`, "PURPOSE_MISMATCH", state.purpose, runPurposeValue(run), "The work-unit purpose differs from the admitted run."));
    if (state.worker_mode !== undefined && state.worker_mode !== null && !PRODUCTION_IMPLEMENTATION_MODES.includes(state.worker_mode)) issues.push(issue(`${unit.path}:worker_mode`, "INVALID_IMPLEMENTATION_MODE", state.worker_mode, PRODUCTION_IMPLEMENTATION_MODES, "Unit-specific worker mode must be default or tdd."));
    if (runPurposeValue(run) === "prototype" && state.worker_mode !== undefined && state.worker_mode !== null) issues.push(issue(`${unit.path}:worker_mode`, "PROTOTYPE_MODE_NOT_ALLOWED", state.worker_mode, null, "Prototype purpose does not select a production implementation mode."));
    if (!UNIT_STATES.includes(current)) issues.push(issue(`${unit.path}:state`, "INVALID_STATE", current ?? null, UNIT_STATES, "The work-unit state is not legal."));
    if (current === "DONE" && isMapping(state.completion)) {
      const expectedPurpose = runPurposeValue(run);
      const expectedMarker = completionMarkerForPurpose(expectedPurpose);
      if (state.completion.purpose !== undefined && state.completion.purpose !== expectedPurpose) issues.push(issue(`${unit.path}:completion.purpose`, "COMPLETION_PURPOSE_MISMATCH", state.completion.purpose, expectedPurpose, "A completed work unit must retain the admitted run purpose."));
      if (state.completion.marker !== undefined && state.completion.marker !== expectedMarker) issues.push(issue(`${unit.path}:completion.marker`, "COMPLETION_MARKER_MISMATCH", state.completion.marker, expectedMarker, "A completed work unit must use the marker for the admitted purpose."));
    }
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
    const activeHandoff = Object.prototype.hasOwnProperty.call(state, "active_handoff") ? state.active_handoff : (state.handoff_path ? { handoff_path: state.handoff_path } : null);
    if (activeHandoff?.handoff_path && await pathExists(activeHandoff.handoff_path)) {
      try {
        const handoff = await validateHandoffFile(activeHandoff.handoff_path, { throwOnInvalid: false });
        if (!handoff.valid) issues.push(...handoff.errors.map((entry) => ({ ...entry, field: `${unit.path}:active_handoff.${entry.field}`, work_unit_id: id })));
      } catch (error) {
        issues.push(issue(`${unit.path}:active_handoff.handoff_path`, error.code ?? "HANDOFF_READ_FAILED", activeHandoff.handoff_path, "valid active handoff", "The active handoff could not be validated."));
      }
    }
  }
  graphCycleIssues(artifacts.units, issues);
  for (const operation of artifacts.operations) {
    if (operation.error) issues.push(issue(operation.path, operation.error.code, operation.error.message, "readable operation", "An operation ledger entry could not be read."));
    else {
      const value = operation.value;
      if (!OPERATION_STATES.includes(value.status)) issues.push(issue(`${operation.path}:status`, "INVALID_OPERATION_STATUS", value.status ?? null, OPERATION_STATES, "Operation status is not legal."));
      const operationUnitId = value.work_unit_id ?? value.input?.work_unit_id ?? null;
      if (["EXECUTING", "UNKNOWN", "RECONCILING"].includes(value.status)) {
        const unresolved = issue(`${operation.path}:status`, "UNRESOLVED_OPERATION", value.status, "conclusive operation status", "An unresolved side effect blocks only its owning work unit until reconciliation.");
        unresolved.work_unit_id = operationUnitId;
        unresolved.run_level = operationUnitId === "RUN";
        issues.push(unresolved);
      }
      if (value.status === "FAILED") {
        const failed = issue(`${operation.path}:status`, "FAILED_OPERATION", value.status, "SUCCEEDED or reconciled terminal status", "A failed side effect requires recovery before its owning work unit can continue.");
        failed.work_unit_id = operationUnitId;
        failed.run_level = operationUnitId === "RUN";
        issues.push(failed);
      }
      if (!value.operation_id) issues.push(issue(`${operation.path}:operation_id`, "REQUIRED_FIELD", null, "operation identity", "Every operation needs operation_id."));
      else {
        const operationPrefix = `${runId}:${operationUnitId ?? ""}:`;
        const operationAction = value.operation_id.startsWith(operationPrefix) ? value.operation_id.slice(operationPrefix.length) : "";
        const operationNamespace = operationUnitId === "RUN" ? "RUN" : "<work-unit-id>";
        if (value.operation_id.split(":").length !== 3 || !operationUnitId || !operationAction || !/^[A-Z][A-Z0-9_]*$/.test(operationAction) || (operationUnitId === "RUN" && value.operation_id !== `${runId}:RUN:${operationAction}`)) issues.push(issue(`${operation.path}:operation_id`, "INVALID_OPERATION_ID", value.operation_id, `${runId}:${operationNamespace}:<UPPER_SNAKE_ACTION>`, "Operation IDs must use the canonical naming format."));
      }
      if (value.operation_instance_id && (!value.operation_instance_id.startsWith(`${value.operation_id}:attempt-`) || !/:attempt-[0-9]{3,6}$/.test(value.operation_instance_id))) issues.push(issue(`${operation.path}:operation_instance_id`, "INVALID_OPERATION_INSTANCE_ID", value.operation_instance_id, `${value.operation_id}:attempt-<NNN>`, "The operation instance must identify one attempt."));
      if (value.input?.run_id && value.input.run_id !== runId) issues.push(issue(`${operation.path}:input.run_id`, "RUN_ID_MISMATCH", value.input.run_id, runId, "The operation belongs to another run."));
      if (value.input?.work_unit_id && value.input.work_unit_id !== "RUN" && !artifacts.units.some((unit) => normalizeUnitId(unit.value ?? {}) === value.input.work_unit_id)) issues.push(issue(`${operation.path}:input.work_unit_id`, "WORK_UNIT_ID_MISMATCH", value.input.work_unit_id, "work unit in run or RUN", "The operation references a work unit outside this run."));
    }
  }
  for (const transition of artifacts.transitions) {
    if (transition.error) issues.push(issue(transition.path, transition.error.code, transition.error.message, "readable transition", "A transition ledger entry could not be read."));
    else {
      const value = transition.value;
      if (!TRANSITION_STATES.includes(value.status)) issues.push(issue(`${transition.path}:status`, "INVALID_TRANSITION_STATUS", value.status ?? null, TRANSITION_STATES, "Transition status is not legal."));
      if (value.status !== "COMMITTED" && value.status !== "ABORTED") issues.push(issue(`${transition.path}:status`, "UNCOMMITTED_TRANSITION", value.status ?? null, ["COMMITTED", "ABORTED"], "A run with an uncommitted transition cannot dispatch new work."));
      if (value.entity_type === "RUN") {
        if (value.entity !== runId) issues.push(issue(`${transition.path}:entity`, "RUN_ID_MISMATCH", value.entity, runId, "The run transition belongs to another run."));
        validateRunTransitionShape({ from: value.from, to: value.to }, null, issues, `${transition.path}:transition`);
      } else {
        if (!value.entity) issues.push(issue(`${transition.path}:entity`, "REQUIRED_FIELD", null, "work unit ID", "Every transition must name its entity."));
        else if (!artifacts.units.some((unit) => normalizeUnitId(unit.value ?? {}) === value.entity)) issues.push(issue(`${transition.path}:entity`, "ENTITY_NOT_FOUND", value.entity, "work unit in run", "The transition entity is not present in this run."));
        validateTransitionShape({ from: value.from, to: value.to }, value.from, issues, `${transition.path}:transition`);
      }
    }
  }
  const blockingIssues = focusUnitId ? issues.filter((entry) => entry.run_level || !entry.work_unit_id || entry.work_unit_id === focusUnitId) : issues;
  return {
    valid: issues.length === 0,
    dispatchable: blockingIssues.length === 0,
    focus_unit_id: focusUnitId,
    blocking_issues: blockingIssues,
    run_id: runId,
    run_path: resolve(runPath),
    state: runState ?? null,
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
  const dispatchStateDocument = await readYamlFile(options.state);
  const focusUnitId = normalizeUnitId(dispatchStateDocument.value);
  const preflight = await preflightRun(runPath, { focusUnitId });
  if (!preflight.valid && !preflight.dispatchable) fail("PREFLIGHT_FAILED", `Run preflight failed before dispatch preparation: ${runPath}`, { run_id: preflight.run_id, issues: preflight.blocking_issues ?? preflight.issues });
  const roleIssues = [];
  const roleKey = normalizeRole(options.role ?? "worker", "role", roleIssues);
  if (!roleKey) fail("INVALID_ROLE", "Unsupported dispatch role.", { errors: roleIssues });
  const latestDispatchStateDocument = await readYamlFile(options.state);
  const latestDispatchState = latestDispatchStateDocument.value;
  const latestDispatchStateValue = actualStateFromDocument(latestDispatchState);
  const currentAttemptRole = String(latestDispatchState.attempt_id ?? "").split(":")[2] ?? null;
  if (roleKey === "reviewer" && latestDispatchStateValue === "AWAITING_REVIEW" && currentAttemptRole !== "reviewer") {
    const reviewerAttempt = padAttempt(options.attempt ?? await nextAttemptNumber(runPath ? dirname(runPath) : runPath, normalizeUnitId(latestDispatchState), "reviewer", latestDispatchState));
    await updateYamlFile(options.state, latestDispatchStateDocument.digest, [
      { pointer: "/attempt_number", value: Number(reviewerAttempt) },
      { pointer: "/attempt_id", value: `${normalizeRunId(latestDispatchState)}:${normalizeUnitId(latestDispatchState)}:reviewer:attempt-${reviewerAttempt}` },
      { pointer: "/last_role", value: "reviewer" },
    ]);
  }
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
        operationInstanceId: manifest.operation.instance_id,
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
    { pointer: "/last_operation_instance_id", value: manifest.operation.instance_id },
    { pointer: "/manifest_path", value: finalManifestResult.manifestPath },
    { pointer: "/handoff_path", value: handoffResult.handoff_path },
    { pointer: "/active_handoff", value: {
      role: roleKey,
      ...(roleKey === "analysis" ? { analysis_id: manifest.analysis_id } : {}),
      attempt_id: manifest.attempt_id,
      operation_id: manifest.operation.id,
      operation_instance_id: manifest.operation.instance_id,
      operation_path: operation.path,
      manifest_path: finalManifestResult.manifestPath,
      handoff_path: handoffResult.handoff_path,
      handoff_digest: validation.digest,
      report_path: finalManifestResult.manifest.artifact.report_path,
      target_branch: finalManifestResult.manifest.target.branch,
      target_head: finalManifestResult.manifest.target.head,
      state: next,
    } },
  ]);
  const finalValidation = await validateHandoffFile(handoffResult.handoff_path, { throwOnInvalid: false });
  if (!finalValidation.valid) fail("HANDOFF_STALE", `State changed while dispatch was being prepared: ${handoffResult.handoff_path}`, { errors: finalValidation.errors });
  return {
    run_id: manifest.run_id,
    work_unit_id: manifest.work_unit_id,
    role: ROLE_NAMES[roleKey],
    state: next,
    operation_path: operation.path,
    operation_id: manifest.operation.id,
    operation_instance_id: manifest.operation.instance_id,
    operation_status: "PREPARED",
    manifest_path: finalManifestResult.manifestPath,
    handoff_path: handoffResult.handoff_path,
    handoff_digest: validation.digest,
    next_action: "SPAWN_AGENT_WITH_VALIDATED_HANDOFF",
    changed: writtenManifest.changed || handoffResult.changed || operationAfter.changed || stateIndex.changed,
  };
}

function activeHandoffFromState(state) {
  if (Object.prototype.hasOwnProperty.call(state, "active_handoff")) return isMapping(state.active_handoff) ? state.active_handoff : null;
  return state.handoff_path ? { handoff_path: state.handoff_path, manifest_path: state.manifest_path, role: state.last_role } : null;
}

function archiveActiveHandoffSets(state, { outcome, reportPath, reportDigest, revision, completedAt }) {
  const active = activeHandoffFromState(state);
  const history = Array.isArray(state.handoff_history) ? [...state.handoff_history] : [];
  if (active) history.push({
    ...active,
    outcome,
    report_path: reportPath ?? active.report_path ?? null,
    report_digest: reportDigest ?? null,
    revision: revision ?? null,
    archived_at: completedAt,
  });
  return [
    { pointer: "/handoff_history", value: history },
    { pointer: "/active_handoff", value: null },
    { pointer: "/manifest_path", value: null },
    { pointer: "/handoff_path", value: null },
  ];
}

async function completionContext(options, roleKey) {
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required for role completion.");
  const statePath = resolve(options.state);
  const stateDocument = await readYamlFile(statePath);
  const state = stateDocument.value;
  const runId = normalizeRunId(state);
  const unitId = normalizeUnitId(state);
  if (!runId || !unitId) fail("INVALID_STATE", "State must contain run_id and work_unit_id for completion.");
  const active = activeHandoffFromState(state);
  if (!active) fail("ACTIVE_HANDOFF_REQUIRED", `No active ${roleKey} handoff is recorded for ${unitId}.`, { work_unit_id: unitId, role: roleKey });
  const activeRole = normalizeRole(active.role ?? roleKey, "active_handoff.role", []);
  if (activeRole !== roleKey) fail("ROLE_MISMATCH", `Active handoff belongs to ${activeRole ?? "another role"}, not ${roleKey}.`, { actual: activeRole ?? null, expected: roleKey });
  const runDirectory = runDirectoryFromStatePath(statePath);
  const reportPath = resolve(options.report ?? active.report_path ?? "");
  if (!reportPath || reportPath === resolve(".")) {
    if (active.handoff_path && await pathExists(active.handoff_path)) {
      const handoffDocument = await readYamlFile(active.handoff_path);
      if (handoffDocument.value.report?.path) {
        return completionContext({ ...options, report: handoffDocument.value.report.path }, roleKey);
      }
    }
    fail("REPORT_REQUIRED", `A ${roleKey} completion requires the exact durable report path.`, { work_unit_id: unitId, attempt_id: active.attempt_id });
  }
  const reportDocument = await readYamlFile(reportPath);
  const report = reportDocument.value;
  const runDocument = await readRunDocument(join(runDirectory, "run.yaml"));
  const purposeIssues = [];
  const admittedPurpose = normalizePurpose(runPurposeValue(runDocument.value), "purpose", purposeIssues);
  if (purposeIssues.length > 0) fail("INVALID_PURPOSE", "The run has an invalid admitted purpose.", { errors: purposeIssues });
  const reportPurpose = report.purpose ?? report.worker?.purpose ?? report.reviewer?.purpose ?? null;
  if (admittedPurpose === "prototype" && reportPurpose !== "prototype") fail("REPORT_PURPOSE_REQUIRED", `A prototype ${roleKey} report must identify prototype purpose.`, { actual: reportPurpose, expected: "prototype" });
  if (reportPurpose !== null && reportPurpose !== admittedPurpose) fail("REPORT_PURPOSE_MISMATCH", `The ${roleKey} report purpose differs from the admitted run.`, { actual: reportPurpose, expected: admittedPurpose });
  const reportMarker = report.completion_marker ?? report.worker?.completion_marker ?? report.reviewer?.completion_marker ?? null;
  if (reportMarker !== null && reportMarker !== completionMarkerForPurpose(admittedPurpose)) fail("REPORT_COMPLETION_MARKER_MISMATCH", `The ${roleKey} report completion marker differs from the admitted purpose.`, { actual: reportMarker, expected: completionMarkerForPurpose(admittedPurpose) });
  if (report.run_id && report.run_id !== runId) fail("RUN_ID_MISMATCH", "Completion report belongs to another run.", { actual: report.run_id, expected: runId });
  if (report.work_unit_id && report.work_unit_id !== unitId) fail("WORK_UNIT_ID_MISMATCH", "Completion report belongs to another work unit.", { actual: report.work_unit_id, expected: unitId });
  if (active.attempt_id && report.attempt_id !== active.attempt_id) fail("ATTEMPT_MISMATCH", "Completion report does not belong to the active attempt.", { actual: report.attempt_id ?? null, expected: active.attempt_id });
  const reportRole = normalizeRole(report.role ?? roleKey, "report.role", []);
  if (reportRole !== roleKey) fail("ROLE_MISMATCH", "Completion report belongs to another role.", { actual: reportRole ?? null, expected: roleKey });
  const operationPath = active.operation_path ?? await resolveOperationPath(runDirectory, active.operation_id, active.operation_instance_id);
  if (!(await pathExists(operationPath))) fail("OPERATION_NOT_FOUND", `Active operation is not durable: ${operationPath}`, { operation_path: operationPath });
  const operationDocument = await readYamlFile(operationPath);
  const operation = operationDocument.value;
  if (active.operation_id && operation.operation_id !== active.operation_id) fail("OPERATION_ID_MISMATCH", "Active operation does not match the active handoff.", { actual: operation.operation_id, expected: active.operation_id });
  if (active.operation_instance_id && (operation.operation_instance_id ?? operation.operation_id) !== active.operation_instance_id) fail("OPERATION_INSTANCE_ID_MISMATCH", "Active operation instance does not match the active handoff.", { actual: operation.operation_instance_id ?? operation.operation_id, expected: active.operation_instance_id });
  const stateWorktree = isMapping(state.worktree) ? state.worktree : {};
  const worktree = await gitSnapshot(stateWorktree.path);
  if (stateWorktree.branch && worktree.branch !== stateWorktree.branch) fail("WORKTREE_BRANCH_MISMATCH", "Completion worktree branch changed.", { actual: worktree.branch, expected: stateWorktree.branch });
  if (worktree.dirty) fail("WORKTREE_DIRTY", "A role cannot complete with unexplained uncommitted worktree changes.", { worktree: worktree.path, status: worktree.status });
  const expectedRevision = worktree.head;
  if (roleKey === "reviewer") {
    const reviewedRevision = report.reviewer?.final_revision ?? report.final_revision ?? report.reviewer?.reviewed_revision ?? report.reviewed_revision;
    if (!reviewedRevision) fail("REVIEW_REVISION_REQUIRED", "An approval/rejection report must identify its exact reviewed revision.");
    const resolvedReviewedRevision = await resolveGitRevision(stateWorktree.path, reviewedRevision, "reviewed_revision");
    if (resolvedReviewedRevision !== expectedRevision) fail("REVIEW_REVISION_MISMATCH", "The reviewer report is not for the current worktree revision.", { actual: resolvedReviewedRevision, expected: expectedRevision });
  }
  return { statePath, stateDocument, state, runId, unitId, active, runDirectory, reportPath, reportDocument, report, operationPath, operationDocument, operation, worktree, expectedRevision };
}

async function completeRole(options, roleKey) {
  const context = await completionContext(options, roleKey);
  const { state, report, operationDocument, operationPath, reportPath, reportDocument, expectedRevision } = context;
  const current = actualStateFromDocument(state);
  const completedAt = new Date().toISOString();
  let nextState;
  let outcome;
  const extraSets = [];
  if (roleKey === "worker") {
    if (current !== "IMPLEMENTING") fail("INVALID_COMPLETION_STATE", `Worker completion requires IMPLEMENTING, not ${current}.`, { actual: current, expected: "IMPLEMENTING" });
    if (report.status !== "IMPLEMENTED") fail("INVALID_WORKER_RESULT", `Worker report must have status IMPLEMENTED, not ${report.status ?? "<missing>"}.`, { actual: report.status ?? null, expected: "IMPLEMENTED" });
    nextState = "AWAITING_REVIEW";
    outcome = "IMPLEMENTED";
    extraSets.push({ pointer: "/implementation_revision", value: expectedRevision });
  } else {
    if (current !== "REVIEWING") fail("INVALID_COMPLETION_STATE", `Reviewer completion requires REVIEWING, not ${current}.`, { actual: current, expected: "REVIEWING" });
    if (report.status !== "COMPLETE") fail("INVALID_REVIEW_RESULT", `Reviewer report must have status COMPLETE, not ${report.status ?? "<missing>"}.`, { actual: report.status ?? null, expected: "COMPLETE" });
    const verdict = report.verdict ?? report.review?.verdict;
    if (!["APPROVED", "REJECTED", "INCONCLUSIVE"].includes(verdict)) fail("INVALID_REVIEW_VERDICT", `Reviewer report has no supported final verdict: ${verdict ?? "<missing>"}.`, { actual: verdict ?? null, expected: ["APPROVED", "REJECTED", "INCONCLUSIVE"] });
    outcome = verdict;
    nextState = verdict === "APPROVED" ? "INTEGRATING" : verdict === "REJECTED" ? "FIXING" : "BLOCKED";
    extraSets.push({ pointer: "/review_result", value: { verdict, report_path: reportPath, report_digest: reportDocument.digest, reviewed_revision: expectedRevision, completed_at: completedAt } });
    if (verdict === "APPROVED") extraSets.push({ pointer: "/accepted_review", value: { report_path: reportPath, report_digest: reportDocument.digest, attempt_id: context.active.attempt_id, revision: expectedRevision, target_branch: context.active.target_branch ?? null, target_head: context.active.target_head ?? null, completed_at: completedAt } });
    if (verdict === "INCONCLUSIVE") extraSets.push({ pointer: "/blocker", value: { type: "REVIEW", code: "REVIEW_INCONCLUSIVE", reason: "Reviewer evidence is inconclusive; repair the evidence or capability before resuming.", source_state: current, resume_state: "REVIEWING", required_to_resume: ["repair_review_evidence"], metadata: { report_path: reportPath, report_digest: reportDocument.digest } } });
  }
  if (!["EXECUTING", "SUCCEEDED"].includes(operationDocument.value.status)) fail("OPERATION_NOT_EXECUTING", `Cannot complete ${roleKey} operation in ${operationDocument.value.status}.`, { operation_path: operationPath, status: operationDocument.value.status, expected: ["EXECUTING", "SUCCEEDED"] });
  let operationUpdate = { changed: false, digest: operationDocument.digest };
  if (operationDocument.value.status === "EXECUTING") operationUpdate = await updateOperation(operationPath, operationDocument.digest, [
    { pointer: "/status", value: "SUCCEEDED" },
    { pointer: "/result", value: { report_path: reportPath, report_digest: reportDocument.digest, final_revision: expectedRevision, outcome, completed_at: completedAt } },
  ]);
  const archiveSets = archiveActiveHandoffSets(state, { outcome, reportPath, reportDigest: reportDocument.digest, revision: expectedRevision, completedAt });
  extraSets.push(...archiveSets, { pointer: "/last_completed_attempt_id", value: context.active.attempt_id }, { pointer: "/last_completion", value: { role: roleKey, outcome, report_path: reportPath, report_digest: reportDocument.digest, revision: expectedRevision, completed_at: completedAt } }, { pointer: "/worktree/current_head", value: expectedRevision });
  const transition = await commitUnitTransition({
    statePath: context.statePath,
    workUnitId: context.unitId,
    from: current,
    to: nextState,
    reason: `${roleKey} result ${outcome} was durably verified against ${expectedRevision}.`,
    operationId: context.operation.operation_id,
    operationInstanceId: context.operation.operation_instance_id ?? context.operation.operation_id,
    extraSets,
  });
  return { run_id: context.runId, work_unit_id: context.unitId, role: ROLE_NAMES[roleKey], state: nextState, outcome, revision: expectedRevision, report_path: reportPath, report_digest: reportDocument.digest, operation_path: operationPath, operation_id: context.operation.operation_id, operation_instance_id: context.operation.operation_instance_id ?? context.operation.operation_id, operation_status: "SUCCEEDED", transition_id: transition.transition_id, changed: operationUpdate.changed || transition.changed, next_action: nextState === "AWAITING_REVIEW" ? "PREPARE_REVIEWER_DISPATCH" : nextState === "INTEGRATING" ? "INTEGRATE_EXACT_APPROVED_REVISION" : nextState === "FIXING" ? "PREPARE_CORRECTION" : "RESOLVE_REVIEW_BLOCKER" };
}

export async function completeWorker(options) {
  return completeRole(options, "worker");
}

export async function completeReview(options) {
  return completeRole(options, "reviewer");
}

export async function completeAnalysis(options) {
  const context = await completionContext(options, "analysis");
  const { state, statePath, stateDocument, report, reportPath, reportDocument, operation, operationPath, operationDocument, expectedRevision } = context;
  if (!report.analysis_id || report.analysis_id !== context.active.analysis_id) fail("ANALYSIS_ID_MISMATCH", "Analysis report must identify the exact active analysis request.", { actual: report.analysis_id ?? null, expected: context.active.analysis_id ?? null });
  if (!["CONCLUSIVE", "INCONCLUSIVE"].includes(report.status)) fail("INVALID_ANALYSIS_RESULT", `Analysis report must have status CONCLUSIVE or INCONCLUSIVE, not ${report.status ?? "<missing>"}.`, { actual: report.status ?? null, expected: ["CONCLUSIVE", "INCONCLUSIVE"] });
  const completedAt = new Date().toISOString();
  if (!["EXECUTING", "SUCCEEDED"].includes(operationDocument.value.status)) fail("OPERATION_NOT_EXECUTING", `Cannot complete analysis operation in ${operationDocument.value.status}.`, { operation_path: operationPath, status: operationDocument.value.status, expected: ["EXECUTING", "SUCCEEDED"] });
  if (operationDocument.value.status === "EXECUTING") await updateOperation(operationPath, operationDocument.digest, [{ pointer: "/status", value: "SUCCEEDED" }, { pointer: "/result", value: { report_path: reportPath, report_digest: reportDocument.digest, outcome: report.status, completed_at: completedAt } }]);
  const history = Array.isArray(state.analysis_history) ? [...state.analysis_history] : [];
  history.push({ ...(activeHandoffFromState(state) ?? {}), report_path: reportPath, report_digest: reportDocument.digest, status: report.status, completed_at: completedAt });
  const archiveSets = archiveActiveHandoffSets(state, { outcome: report.status, reportPath, reportDigest: reportDocument.digest, revision: expectedRevision, completedAt });
  const updated = await updateYamlFile(statePath, stateDocument.digest, [
    { pointer: "/analysis_history", value: history },
    { pointer: "/last_analysis", value: { report_path: reportPath, report_digest: reportDocument.digest, status: report.status, completed_at: completedAt } },
    ...archiveSets,
  ]);
  return { run_id: context.runId, work_unit_id: context.unitId, role: ROLE_NAMES.analysis, state: actualStateFromDocument(state), outcome: report.status, report_path: reportPath, report_digest: reportDocument.digest, operation_path: operationPath, operation_id: operation.operation_id, operation_instance_id: operation.operation_instance_id ?? operation.operation_id, operation_status: "SUCCEEDED", state_digest: updated.digest, changed: updated.changed, next_action: "HOST_EVALUATE_ADVISORY_REPORT" };
}

export async function prepareCorrection(options) {
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required to prepare a correction.");
  const statePath = resolve(options.state);
  const stateDocument = await readYamlFile(statePath);
  const state = stateDocument.value;
  const unitId = normalizeUnitId(state);
  const runId = normalizeRunId(state);
  if (!unitId || !runId) fail("INVALID_STATE", "Correction state must contain run_id and work_unit_id.");
  if (actualStateFromDocument(state) !== "FIXING") fail("INVALID_CORRECTION_STATE", `Correction preparation requires FIXING, not ${actualStateFromDocument(state)}.`, { actual: actualStateFromDocument(state), expected: "FIXING" });
  const runDirectory = runDirectoryFromStatePath(statePath);
  const attemptNumber = padAttempt(options.attempt ?? await nextAttemptNumber(runDirectory, unitId, "worker", state));
  const attemptId = `${runId}:${unitId}:worker:attempt-${attemptNumber}`;
  const updated = await updateYamlFile(statePath, stateDocument.digest, [
    { pointer: "/attempt_number", value: Number(attemptNumber) },
    { pointer: "/attempt_id", value: attemptId },
    { pointer: "/last_role", value: "worker" },
    { pointer: "/correction_attempt", value: Number(state.correction_attempt ?? 0) + 1 },
  ]);
  try {
    const result = await prepareDispatch({ ...options, state: statePath, role: "worker", attempt: Number(attemptNumber) });
    return { ...result, correction_attempt: Number(state.correction_attempt ?? 0) + 1, state_changed: updated.changed };
  } catch (error) {
    await blockFailedResume(statePath, unitId, "FIXING", error);
    throw error;
  }
}

export async function updateAcceptanceStatusProjection(runPath) {
  const runFile = basename(resolve(runPath)) === "run.yaml" ? resolve(runPath) : join(resolve(runPath), "run.yaml");
  const artifacts = await allRunArtifacts(runFile);
  const purpose = runPurposeValue(artifacts.runDocument.value);
  const completionMarker = completionMarkerForPurpose(purpose);
  const projectionPath = join(artifacts.runDirectory, "summaries", "acceptance-status.yaml");
  const units = artifacts.units.filter((unit) => unit.value).map((unit) => ({
    work_unit_id: normalizeUnitId(unit.value),
    state: actualStateFromDocument(unit.value),
    implementation_revision: unit.value.implementation_revision ?? null,
    accepted_review: unit.value.accepted_review ? { report_path: unit.value.accepted_review.report_path, report_digest: unit.value.accepted_review.report_digest, revision: unit.value.accepted_review.revision } : null,
    integrated_revision: unit.value.integrated_revision ?? unit.value.integration?.source_revision ?? null,
    completion: unit.value.completion ? { status: unit.value.completion.status, purpose, marker: completionMarker, validation: unit.value.completion.validation } : null,
  })).sort((left, right) => left.work_unit_id.localeCompare(right.work_unit_id));
  const value = {
    schema_version: 1,
    kind: "squad-acceptance-status",
    run_id: artifacts.runDocument.run_id,
    purpose,
    completion_marker: completionMarker,
    contract_digest: artifacts.runDocument.value.source?.digest ?? artifacts.runDocument.value.source?.tickets_digest ?? null,
    generated_at: new Date().toISOString(),
    units,
  };
  const result = await pathExists(projectionPath)
    ? await updateYamlFile(projectionPath, (await readYamlFile(projectionPath)).digest, [{ pointer: "", value }])
    : await createYamlFile(projectionPath, value);
  return { ...result, path: projectionPath };
}

function optionList(value) {
  if (Array.isArray(value)) return value.flatMap((entry) => optionList(entry));
  if (typeof value !== "string") return [];
  return value.split(",").map((entry) => entry.trim()).filter(Boolean);
}

function fingerprintValue(value) {
  return `sha256:${createHash("sha256").update(JSON.stringify(value)).digest("hex")}`;
}

export async function captureEnvironmentProfile(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const runDocument = await readRunDocument(runPath);
  const run = runDocument.value;
  const projectRootValue = options.project ?? run.project?.root ?? run.project_root;
  if (!asString(projectRootValue)) fail("PROJECT_ROOT_REQUIRED", "Environment profiling requires the admitted project root.");
  const projectRoot = resolve(projectRootValue);
  const repository = await gitSnapshot(projectRoot);
  const packageFiles = ["package.json", "bun.lock", "bun.lockb", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"];
  const packageState = [];
  for (const relativePath of packageFiles) {
    const path = join(projectRoot, relativePath);
    if (await pathExists(path)) packageState.push({ path: relativePath, present: true, digest: await digestFile(path) });
  }
  const generatedState = [];
  for (const relativePath of optionList(options.generated)) {
    const path = join(projectRoot, relativePath);
    if (!(await pathExists(path))) {
      generatedState.push({ path: relativePath, present: false, digest: null });
      continue;
    }
    const info = await stat(path);
    generatedState.push({ path: relativePath, present: true, digest: info.isFile() ? await digestFile(path) : null, kind: info.isDirectory() ? "directory" : "file" });
  }
  const identity = {
    bun: globalThis.Bun?.version ?? null,
    node: process.versions.node,
    platform: process.platform,
    architecture: process.arch,
    package_manager: packageState.find((entry) => entry.path === "bun.lockb" || entry.path === "bun.lock") ? "bun" : packageState.find((entry) => entry.path === "pnpm-lock.yaml") ? "pnpm" : packageState.find((entry) => entry.path === "yarn.lock") ? "yarn" : packageState.find((entry) => entry.path === "package-lock.json") ? "npm" : "unknown",
  };
  const fingerprintBasis = { identity, repository_id: repository.repository_id, target_branch: repository.branch, target_head: repository.head, package_files: packageState, generated_artifacts: generatedState };
  const profile = {
    schema_version: 1,
    kind: "squad-environment-profile",
    run_id: runDocument.run_id,
    captured_at: new Date().toISOString(),
    fingerprint: fingerprintValue(fingerprintBasis),
    identity,
    project: { root: repository.root, repository_id: repository.repository_id, branch: repository.branch, head: repository.head, dirty: repository.dirty },
    package_files: packageState,
    generated_artifacts: generatedState,
    verification_policy: { known_blockers_are_reusable_only_when_fingerprint_matches: true, secrets_redacted: true },
  };
  const profilePath = join(dirname(runPath), "environment", "profile.yaml");
  const profileResult = await pathExists(profilePath)
    ? await updateYamlFile(profilePath, (await readYamlFile(profilePath)).digest, [{ pointer: "", value: profile }])
    : await createYamlFile(profilePath, profile);
  const latestRun = await readRunDocument(runPath);
  const runUpdate = await updateYamlFile(runPath, latestRun.digest, [{ pointer: "/environment", value: { profile_path: profilePath, profile_digest: profileResult.digest, fingerprint: profile.fingerprint } }]);
  return { run_id: runDocument.run_id, path: profilePath, digest: profileResult.digest, fingerprint: profile.fingerprint, changed: profileResult.changed || runUpdate.changed };
}

export async function recordReferenceSnapshot(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const runDocument = await readRunDocument(runPath);
  const repositoryValue = options.repository ?? options.referenceRoot;
  if (!asString(repositoryValue)) fail("REFERENCE_REPOSITORY_REQUIRED", "--repository is required for a reference snapshot.");
  const repository = resolve(repositoryValue);
  const repositorySnapshot = await gitSnapshot(repository);
  const revision = await resolveGitRevision(repository, options.revision ?? repositorySnapshot.head, "reference.revision");
  const files = optionList(options.files);
  const capturedFiles = [];
  for (const relativePath of files) {
    if (relativePath.startsWith("/") || relativePath.split("/").includes("..")) fail("INVALID_REFERENCE_PATH", `Reference file must be repository-relative: ${relativePath}`, { path: relativePath });
    const result = await runGit(repository, ["show", `${revision}:${relativePath}`], { allowFailure: true });
    if (result.exitCode !== 0) fail("REFERENCE_FILE_NOT_FOUND", `Reference file is not present at ${revision}: ${relativePath}`, { path: relativePath, revision, stderr: result.stderr });
    capturedFiles.push({ path: relativePath, digest: `sha256:${createHash("sha256").update(result.stdout).digest("hex")}` });
  }
  const snapshotId = `reference-${basename(repository).replace(/[^A-Za-z0-9._-]/g, "-")}-${revision.slice(0, 12)}`;
  const snapshotPath = join(dirname(runPath), "references", `${snapshotId}.yaml`);
  const existingSnapshot = await pathExists(snapshotPath) ? await readYamlFile(snapshotPath) : null;
  const snapshot = { schema_version: 1, kind: "squad-reference-snapshot", snapshot_id: snapshotId, repository: { root: repositorySnapshot.root, repository_id: repositorySnapshot.repository_id, revision }, files: capturedFiles, read_only: true, captured_at: existingSnapshot?.value?.captured_at ?? new Date().toISOString(), impact: "REQUIRES_IMPACT_ANALYSIS_WHEN_REFERENCED_WORK_CHANGES" };
  const written = await writeImmutableYaml(snapshotPath, snapshot);
  const latestRun = await readRunDocument(runPath);
  const snapshots = Array.isArray(latestRun.value.reference_snapshots) ? [...latestRun.value.reference_snapshots] : [];
  if (!snapshots.some((entry) => entry.snapshot_id === snapshotId)) snapshots.push({ snapshot_id: snapshotId, path: snapshotPath, digest: written.digest, revision, repository: repositorySnapshot.root });
  const runUpdate = await updateYamlFile(runPath, latestRun.digest, [{ pointer: "/reference_snapshots", value: snapshots }]);
  return { run_id: runDocument.run_id, snapshot_id: snapshotId, path: snapshotPath, digest: written.digest, revision, files: capturedFiles, changed: written.changed || runUpdate.changed };
}

function declaredScopePaths(state) {
  const raw = state.scope_paths ?? (isMapping(state.scope) ? state.scope.files ?? state.scope.paths : state.scope);
  return optionList(raw).map((path) => path.replaceAll("\\\\", "/").replace(/^\.\//, "")).filter(Boolean);
}

function scopesOverlap(left, right) {
  return left === right || left.startsWith(`${right}/`) || right.startsWith(`${left}/`);
}

export async function analyzeOwnership(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const artifacts = await allRunArtifacts(runPath);
  const units = [];
  for (const unit of artifacts.units) {
    if (!unit.value) continue;
    const scope = declaredScopePaths(unit.value);
    let changed = [];
    if (unit.value.worktree?.path && unit.value.worktree?.baseline && await pathExists(unit.value.worktree.path)) {
      const diff = await runGit(unit.value.worktree.path, ["diff", "--name-only", `${unit.value.worktree.baseline}...HEAD`], { allowFailure: true });
      if (diff.exitCode === 0) changed = diff.stdout.split("\\n").map((path) => path.trim()).filter(Boolean);
    }
    const drift = changed.filter((path) => scope.length === 0 || !scope.some((declared) => scopesOverlap(path, declared)));
    const dependencies = normalizeDependencies(unit.value);
    const dependencyBlockers = dependencies.filter((dependency) => {
      const dependencyUnit = artifacts.units.find((candidate) => normalizeUnitId(candidate.value ?? {}) === dependency.work_unit_id);
      return !dependencyUnit?.value || actualStateFromDocument(dependencyUnit.value) !== "DONE";
    }).map((dependency) => dependency.work_unit_id);
    units.push({ work_unit_id: normalizeUnitId(unit.value), state: actualStateFromDocument(unit.value), dependency_blockers: dependencyBlockers, declared_scope: scope, changed_scope: changed, scope_drift: drift, confidence: scope.length === 0 || drift.length > 0 ? "UNCERTAIN" : "CONDITIONAL" });
  }
  const pairs = [];
  for (let leftIndex = 0; leftIndex < units.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < units.length; rightIndex += 1) {
      const left = units[leftIndex];
      const right = units[rightIndex];
      const overlap = left.declared_scope.some((leftPath) => right.declared_scope.some((rightPath) => scopesOverlap(leftPath, rightPath)));
      const classification = left.confidence === "UNCERTAIN" || right.confidence === "UNCERTAIN" ? "UNCERTAIN" : overlap ? "CONDITIONAL" : "SAFE";
      pairs.push({ left: left.work_unit_id, right: right.work_unit_id, classification, recommendation: classification === "SAFE" ? "PARALLEL_ALLOWED" : "SERIALIZE_OR_PROVE_BOUNDARY" });
    }
  }
  const readyIds = new Set(units.filter((unit) => unit.state === "READY" && unit.dependency_blockers.length === 0).map((unit) => unit.work_unit_id));
  const activeIds = new Set(units.filter((unit) => !["DONE", "PENDING"].includes(unit.state)).map((unit) => unit.work_unit_id));
  const frontierPairs = pairs.filter((pair) => pair.classification !== "SAFE" && (readyIds.has(pair.left) || readyIds.has(pair.right) || activeIds.has(pair.left) || activeIds.has(pair.right)));
  const frontier = { ready: [...readyIds].sort(), dependency_blocked: units.filter((unit) => unit.dependency_blockers.length > 0).map((unit) => ({ work_unit_id: unit.work_unit_id, blockers: unit.dependency_blockers })).sort((left, right) => left.work_unit_id.localeCompare(right.work_unit_id)), active_conflicts: frontierPairs, recommended_serialization: [...new Set(frontierPairs.flatMap((pair) => [pair.left, pair.right]))].sort() };
  const report = { schema_version: 1, kind: "squad-ownership-analysis", run_id: artifacts.runDocument.run_id, generated_at: new Date().toISOString(), units, pairs, frontier };
  const reportPath = options.output ? resolve(options.output) : join(artifacts.runDirectory, "analysis", "ownership.yaml");
  const written = await pathExists(reportPath) ? await updateYamlFile(reportPath, (await readYamlFile(reportPath)).digest, [{ pointer: "", value: report }]) : await createYamlFile(reportPath, report);
  const runDocument = await readRunDocument(runPath);
  const runUpdate = await updateYamlFile(runPath, runDocument.digest, [{ pointer: "/ownership_analysis", value: { path: reportPath, digest: written.digest } }]);
  return { run_id: artifacts.runDocument.run_id, path: reportPath, digest: written.digest, pairs, frontier, changed: written.changed || runUpdate.changed };
}

function migratedArtifactPath(filePath, suffix) {
  const extension = filePath.endsWith(".yaml") ? ".yaml" : "";
  const base = extension ? filePath.slice(0, -extension.length) : filePath;
  return `${base}.${suffix}${extension}`;
}

function attemptNumberFromIdentity(...values) {
  for (const value of values) {
    const match = String(value ?? "").match(/:attempt-([0-9]{1,6})$/);
    if (match) return padAttempt(Number(match[1]));
  }
  return "001";
}

async function normalizeLegacyActiveOperation(runDirectory, state, active, { purpose, workerMode } = {}) {
  const operationId = active?.operation_id;
  if (!operationId) return { status: "BLOCKED", code: "LEGACY_OPERATION_ID_MISSING", reason: "Active legacy handoff has no logical operation identity." };
  let operationPath = active.operation_path ? resolve(active.operation_path) : await resolveOperationPath(runDirectory, operationId, active.operation_instance_id);
  if (!(await pathExists(operationPath))) return { status: "BLOCKED", code: "LEGACY_OPERATION_NOT_FOUND", reason: `Active operation is not readable: ${operationPath}`, operation_path: operationPath };
  const operationDocument = await readYamlFile(operationPath);
  const operation = operationDocument.value;
  const existingInstance = operation.operation_instance_id;
  const attemptNumber = attemptNumberFromIdentity(existingInstance, operation.attempt_id, active.attempt_id, state.attempt_id, state.attempt_number);
  const operationInstanceId = existingInstance && /:attempt-[0-9]{3,6}$/.test(existingInstance) ? existingInstance : operationInstanceIdFor(operationId, attemptNumber);
  const expectedOperationPath = operationPathFor(runDirectory, operationId, operationInstanceId);
  const knownSuccessorPath = operation.migration?.successor_operation_path ?? (await pathExists(expectedOperationPath) ? expectedOperationPath : null);
  if (knownSuccessorPath && resolve(knownSuccessorPath) !== resolve(operationPath) && await pathExists(knownSuccessorPath)) {
    const successorDocument = await readYamlFile(knownSuccessorPath);
    const successor = successorDocument.value;
    const successorHandoffPath = successor.result?.handoff_path ?? successor.input?.handoff_path;
    if (!successorHandoffPath || !(await pathExists(successorHandoffPath))) return { status: "BLOCKED", code: "LEGACY_SUCCESSOR_INCOMPLETE", reason: `Legacy successor operation exists without a readable handoff: ${knownSuccessorPath}`, operation_path: operationPath, successor_operation_path: knownSuccessorPath };
    const successorHandoff = await readYamlFile(successorHandoffPath);
    const successorValidation = await validateHandoffFile(successorHandoffPath, { throwOnInvalid: false });
    if (!successorValidation.valid) return { status: "BLOCKED", code: "MIGRATED_HANDOFF_INVALID", reason: `Legacy successor handoff is not valid: ${successorHandoffPath}`, operation_path: operationPath, successor_operation_path: knownSuccessorPath, errors: successorValidation.errors };
    const successorManifestPath = successorHandoff.value.manifest?.path ?? successorHandoff.value.artifact?.manifest_path ?? successor.input?.manifest_path ?? null;
    const normalizedActive = { ...active, operation_instance_id: successor.operation_instance_id ?? operationInstanceId, operation_path: resolve(knownSuccessorPath), handoff_path: resolve(successorHandoffPath), handoff_digest: successorHandoff.digest, ...(successorManifestPath ? { manifest_path: resolve(successorManifestPath) } : {}) };
    const alreadyCurrent = active.operation_instance_id === normalizedActive.operation_instance_id && resolve(active.operation_path ?? "") === normalizedActive.operation_path && resolve(active.handoff_path ?? "") === normalizedActive.handoff_path;
    return { status: alreadyCurrent ? "ALREADY_CURRENT" : "MIGRATED", operation_path: normalizedActive.operation_path, operation_instance_id: normalizedActive.operation_instance_id, active: normalizedActive, successor_digest: successorDocument.digest };
  }
  const handoffPath = active.handoff_path ? resolve(active.handoff_path) : null;
  if (!handoffPath || !(await pathExists(handoffPath))) return { status: "BLOCKED", code: "LEGACY_HANDOFF_NOT_FOUND", reason: `Active handoff is not readable: ${handoffPath ?? "<missing>"}`, operation_path: operationPath };
  const oldHandoffDocument = await readYamlFile(handoffPath);
  const oldHandoff = oldHandoffDocument.value;
  const handoffAlreadyCurrent = oldHandoff.operation_instance_id === operationInstanceId && resolve(oldHandoff.artifact?.operation_path ?? "") === resolve(expectedOperationPath) && resolve(operationPath) === resolve(expectedOperationPath);
  if (handoffAlreadyCurrent && operation.operation_instance_id === operationInstanceId) {
    return { status: "ALREADY_CURRENT", active: { ...active, operation_instance_id: operationInstanceId, operation_path: expectedOperationPath, handoff_digest: oldHandoffDocument.digest } };
  }
  const oldManifestPath = oldHandoff.manifest?.path ?? oldHandoff.artifact?.manifest_path ?? active.manifest_path ?? null;
  const newManifestPath = oldManifestPath && await pathExists(oldManifestPath) ? migratedArtifactPath(resolve(oldManifestPath), `migrated-${attemptNumber}`) : oldManifestPath;
  const newHandoffPath = migratedArtifactPath(handoffPath, `migrated-${attemptNumber}`);
  let manifestDocument = null;
  let newManifestDigest = null;
  if (oldManifestPath && await pathExists(oldManifestPath)) {
    manifestDocument = await readYamlFile(oldManifestPath);
    const manifest = structuredClone(manifestDocument.value);
    manifest.decisions = {
      ...(isMapping(manifest.decisions) ? manifest.decisions : {}),
      purpose: purpose ?? "production",
      mode: workerMode ?? null,
      completion_marker: completionMarkerForPurpose(purpose ?? "production"),
    };
    manifest.operation = { ...(isMapping(manifest.operation) ? manifest.operation : {}), instance_id: operationInstanceId };
    manifest.artifact = { ...(isMapping(manifest.artifact) ? manifest.artifact : {}), operation_path: expectedOperationPath, manifest_path: newManifestPath, handoff_path: newHandoffPath };
    const writtenManifest = await writeImmutableYaml(newManifestPath, manifest);
    newManifestDigest = writtenManifest.digest;
  }
  const migratedHandoff = structuredClone(oldHandoff);
  migratedHandoff.decisions = {
    ...(isMapping(migratedHandoff.decisions) ? migratedHandoff.decisions : {}),
    purpose: purpose ?? "production",
    mode: workerMode ?? null,
    completion_marker: completionMarkerForPurpose(purpose ?? "production"),
  };
  migratedHandoff.operation_instance_id = operationInstanceId;
  migratedHandoff.operation = { ...(isMapping(migratedHandoff.operation) ? migratedHandoff.operation : {}), instance_id: operationInstanceId };
  migratedHandoff.artifact = { ...(isMapping(migratedHandoff.artifact) ? migratedHandoff.artifact : {}), operation_path: expectedOperationPath, ...(newManifestPath ? { manifest_path: newManifestPath } : {}) , handoff_path: newHandoffPath };
  if (migratedHandoff.manifest && newManifestPath) migratedHandoff.manifest = { ...migratedHandoff.manifest, path: newManifestPath, digest: newManifestDigest };
  const writtenHandoff = await writeImmutableYaml(newHandoffPath, migratedHandoff);
  const migratedOperation = structuredClone(operation);
  migratedOperation.operation_instance_id = operationInstanceId;
  migratedOperation.input = { ...(isMapping(migratedOperation.input) ? migratedOperation.input : {}), ...(newManifestPath ? { manifest_path: newManifestPath } : {}), handoff_path: newHandoffPath };
  migratedOperation.result = migratedOperation.result ? { ...migratedOperation.result, ...(newManifestPath ? { manifest_path: newManifestPath, manifest_digest: newManifestDigest } : {}), handoff_path: newHandoffPath, handoff_digest: writtenHandoff.digest } : null;
  migratedOperation.migration = { from_path: operationPath, from_operation_instance_id: operation.operation_instance_id ?? null, migrated_at: new Date().toISOString() };
  const writtenOperation = await writeImmutableYaml(expectedOperationPath, migratedOperation);
  const migratedValidation = await validateHandoffFile(newHandoffPath, { throwOnInvalid: false });
  if (!migratedValidation.valid) return { status: "BLOCKED", code: "MIGRATED_HANDOFF_INVALID", reason: `Migrated handoff is not valid: ${newHandoffPath}`, operation_path: operationPath, successor_operation_path: expectedOperationPath, errors: migratedValidation.errors };
  if (resolve(operationPath) !== resolve(expectedOperationPath) && operation.status !== "SUPERSEDED") {
    const latestLegacy = await readYamlFile(operationPath);
    await updateOperation(operationPath, latestLegacy.digest, [{ pointer: "/status", value: "SUPERSEDED" }, { pointer: "/migration/successor_operation_instance_id", value: operationInstanceId }, { pointer: "/migration/successor_operation_path", value: expectedOperationPath }]);
  }
  return { status: "MIGRATED", operation_path: expectedOperationPath, operation_instance_id: operationInstanceId, active: { ...active, operation_instance_id: operationInstanceId, operation_path: expectedOperationPath, handoff_path: newHandoffPath, handoff_digest: writtenHandoff.digest, ...(newManifestPath ? { manifest_path: newManifestPath } : {}) }, successor_digest: writtenOperation.digest };
}

export async function migrateRun(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const artifacts = await allRunArtifacts(runPath);
  const latestRun = await readRunDocument(runPath);
  const wasLegacyRun = Number(latestRun.value.control_plane_version ?? 1) < 2;
  const admittedPurpose = runPurposeValue(latestRun.value);
  const admittedWorkerMode = latestRun.value.worker_mode ?? (isMapping(latestRun.value.admission) ? latestRun.value.admission.worker_mode : undefined);
  const migrationWorkerMode = admittedWorkerMode ?? (wasLegacyRun && admittedPurpose === "production" ? "default" : null);
  const migrated = [];
  for (const unit of artifacts.units) {
    if (!unit.value) continue;
    const state = unit.value;
    const currentState = actualStateFromDocument(state);
    const sets = [];
    let active = Object.prototype.hasOwnProperty.call(state, "active_handoff") && isMapping(state.active_handoff)
      ? state.active_handoff
      : state.handoff_path
        ? { handoff_path: state.handoff_path, manifest_path: state.manifest_path ?? null, role: state.last_role ?? null }
        : null;
    if (active?.handoff_path && await pathExists(active.handoff_path)) {
      const handoff = await readYamlFile(active.handoff_path);
      active = { ...active, attempt_id: active.attempt_id ?? handoff.value.attempt_id, operation_id: active.operation_id ?? handoff.value.operation_id, operation_instance_id: active.operation_instance_id ?? handoff.value.operation_instance_id ?? null, operation_path: active.operation_path ?? handoff.value.artifact?.operation_path ?? null, report_path: active.report_path ?? handoff.value.report?.path ?? null, target_branch: active.target_branch ?? handoff.value.target?.branch ?? null, target_head: active.target_head ?? handoff.value.target?.head ?? null, handoff_digest: handoff.digest };
    }
    let migrationStatus = "ALREADY_CURRENT";
    let migrationDetail = null;
    if (currentState !== "DONE" && active) {
      migrationDetail = await normalizeLegacyActiveOperation(dirname(runPath), state, active, { purpose: admittedPurpose, workerMode: state.worker_mode ?? migrationWorkerMode });
      migrationStatus = migrationDetail.status;
      if (migrationDetail.active) {
        active = migrationDetail.active;
        sets.push({ pointer: "/active_handoff", value: active }, { pointer: "/manifest_path", value: active.manifest_path ?? null }, { pointer: "/handoff_path", value: active.handoff_path ?? null }, { pointer: "/last_operation_instance_id", value: active.operation_instance_id ?? null });
      } else if (migrationStatus === "BLOCKED") {
        sets.push({ pointer: "/blocker", value: { type: "MIGRATION", code: migrationDetail.code, reason: migrationDetail.reason, source_state: currentState, resume_state: currentState, required_to_resume: ["repair_legacy_operation_identity"], metadata: { operation_path: migrationDetail.operation_path ?? null } } });
      }
    }
    if (currentState === "DONE" && active && !Object.prototype.hasOwnProperty.call(state, "active_handoff")) {
      const previousHistory = Array.isArray(state.handoff_history) ? [...state.handoff_history] : [];
      sets.push({ pointer: "/handoff_history", value: [...previousHistory, { ...active, outcome: state.last_completion?.outcome ?? "DONE", archived_at: state.last_completion?.completed_at ?? null }] }, { pointer: "/active_handoff", value: null }, { pointer: "/manifest_path", value: null }, { pointer: "/handoff_path", value: null });
    }
    if (!Array.isArray(state.handoff_history)) sets.push({ pointer: "/handoff_history", value: [] });
    if (sets.length > 0) {
      const latestState = await readYamlFile(unit.path);
      const result = await updateYamlFile(unit.path, latestState.digest, sets);
      migrated.push({ work_unit_id: normalizeUnitId(state), path: unit.path, digest: result.digest, status: migrationStatus, ...(migrationDetail?.code ? { code: migrationDetail.code } : {}) });
    } else if (active || currentState !== "DONE") migrated.push({ work_unit_id: normalizeUnitId(state), path: unit.path, digest: unit.digest, status: migrationStatus, ...(migrationDetail?.code ? { code: migrationDetail.code } : {}) });
  }
  const hadEnvironmentProfile = Boolean(latestRun.value.environment?.profile_path && latestRun.value.environment?.profile_digest);
  const runSets = [];
  if (wasLegacyRun) runSets.push({ pointer: "/control_plane_version", value: 2 });
  const explicitPurpose = latestRun.value.purpose ?? (isMapping(latestRun.value.admission) ? latestRun.value.admission.purpose : undefined);
  const explicitWorkerMode = latestRun.value.worker_mode ?? (isMapping(latestRun.value.admission) ? latestRun.value.admission.worker_mode : undefined);
  if (explicitPurpose === undefined || explicitPurpose === null) {
    runSets.push({ pointer: "/purpose", value: "production" });
    if (explicitWorkerMode === undefined || explicitWorkerMode === null) runSets.push({ pointer: "/worker_mode", value: "default" });
  } else if (wasLegacyRun && runPurposeValue(latestRun.value) === "production" && (explicitWorkerMode === undefined || explicitWorkerMode === null)) {
    runSets.push({ pointer: "/worker_mode", value: "default" });
  }
  if (!Object.prototype.hasOwnProperty.call(latestRun.value, "proposal_required")) runSets.push({ pointer: "/proposal_required", value: false });
  if (!Object.prototype.hasOwnProperty.call(latestRun.value, "environment_profile_required")) runSets.push({ pointer: "/environment_profile_required", value: false });
  if (!Object.prototype.hasOwnProperty.call(latestRun.value, "validation_evidence_required")) runSets.push({ pointer: "/validation_evidence_required", value: false });
  if (runSets.length > 0) await updateYamlFile(runPath, latestRun.digest, runSets);
  const blocked = migrated.filter((entry) => entry.status === "BLOCKED");
  const legacyEnvironmentProfile = wasLegacyRun && !hadEnvironmentProfile
    ? { status: "LEGACY_ENVIRONMENT_PROFILE_MISSING", required: false, next_action: "environment-profile" }
    : null;
  return { run_id: latestRun.run_id, control_plane_version: 2, migrated, blocked, legacy_environment_profile: legacyEnvironmentProfile, changed: migrated.some((entry) => entry.status === "MIGRATED") || runSets.length > 0 };
}

async function nextOperationAttemptNumber(runDirectory, operationId) {
  const numbers = [];
  for (const entry of await readOperationFiles(runDirectory)) {
    if (entry.value?.operation_id !== operationId) continue;
    const match = String(entry.value.operation_instance_id ?? "").match(/:attempt-([0-9]{3,6})$/);
    if (match) numbers.push(Number(match[1]));
  }
  return Math.max(0, ...numbers) + 1;
}

async function createIntegrationOperation(runDirectory, operationId, operationInstanceId, input) {
  const operationPath = operationPathFor(runDirectory, operationId, operationInstanceId);
  const operation = {
    schema_version: 1,
    operation_id: operationId,
    operation_instance_id: operationInstanceId,
    work_unit_id: input.work_unit_id,
    attempt_id: input.attempt_id,
    type: "INTEGRATE",
    status: "PREPARED",
    job_id: null,
    input,
    result: null,
  };
  const written = await writeImmutableYaml(operationPath, operation);
  const document = await readYamlFile(operationPath);
  return { path: operationPath, digest: document.digest, value: document.value, write: written };
}

export async function integrateTicket(options) {
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required for integration.");
  const statePath = resolve(options.state);
  const stateDocument = await readYamlFile(statePath);
  const state = stateDocument.value;
  const unitId = normalizeUnitId(state);
  const runId = normalizeRunId(state);
  if (!unitId || !runId) fail("INVALID_STATE", "Integration state must contain run_id and work_unit_id.");
  if (actualStateFromDocument(state) !== "INTEGRATING") fail("INVALID_INTEGRATION_STATE", `Integration requires INTEGRATING, not ${actualStateFromDocument(state)}.`, { actual: actualStateFromDocument(state), expected: "INTEGRATING" });
  if (!isMapping(state.accepted_review) || !state.accepted_review.revision) fail("APPROVED_REVISION_REQUIRED", "Integration requires a durable exact-revision reviewer approval.");
  const runPath = await resolveRunPath(options, options.runId ?? runId);
  const context = await readTicketAndRunContext(runPath, statePath, options.ticket);
  const sourceRevision = await resolveGitRevision(context.repository, state.accepted_review.revision, "accepted_review.revision");
  const targetSnapshot = await gitSnapshot(context.repository);
  if (targetSnapshot.dirty) fail("TARGET_DIRTY", "Cannot integrate into a dirty target checkout.", { target: context.repository, status: targetSnapshot.status });
  if (targetSnapshot.branch !== context.targetBranch) fail("TARGET_BRANCH_MISMATCH", "Target branch changed before integration.", { actual: targetSnapshot.branch, expected: context.targetBranch });
  const expectedTarget = context.targetHead ? await resolveGitRevision(context.repository, context.targetHead, "target.head") : targetSnapshot.head;
  const operationId = options.operation_id ?? `${runId}:${unitId}:INTEGRATE`;
  const existingSuccessful = (await readOperationFiles(context.runDirectory)).find((entry) => entry.value?.operation_id === operationId && entry.value?.type === "INTEGRATE" && entry.value?.status === "SUCCEEDED" && entry.value?.input?.source_revision === sourceRevision);
  if (!existingSuccessful) {
    if (!state.accepted_review.target_head) fail("APPROVAL_TARGET_CHECKPOINT_REQUIRED", "Reviewer approval has no target checkpoint; generate a fresh reviewer handoff before integration.", { field: "accepted_review.target_head", expected: expectedTarget });
    const approvedTarget = await resolveGitRevision(context.repository, state.accepted_review.target_head, "accepted_review.target_head");
    if (approvedTarget !== expectedTarget) fail("APPROVAL_STALE", "Reviewer approval was produced against an older target checkpoint.", { actual: approvedTarget, expected: expectedTarget, recorded_target: context.targetHead, approved_target: state.accepted_review.target_head, next_action: "PREPARE_FRESH_REVIEWER_HANDOFF" });
  }
  let operation;
  if (existingSuccessful) {
    const recordedTarget = existingSuccessful.value.result?.target_after;
    if (recordedTarget && targetSnapshot.head !== recordedTarget) fail("TARGET_DRIFT", "The target no longer matches the recorded successful integration; reconcile before retrying.", { actual: targetSnapshot.head, expected: recordedTarget });
    operation = existingSuccessful;
  } else {
    if (targetSnapshot.head !== expectedTarget) fail("TARGET_DRIFT", "Target HEAD changed before integration; no target mutation was attempted.", { actual: targetSnapshot.head, expected: expectedTarget });
    const attemptNumber = padAttempt(options.attempt ?? await nextOperationAttemptNumber(context.runDirectory, operationId));
    const operationInstanceId = options.operation_instance_id ?? operationInstanceIdFor(operationId, attemptNumber);
    operation = await createIntegrationOperation(context.runDirectory, operationId, operationInstanceId, {
      run_id: runId,
      work_unit_id: unitId,
      attempt_id: state.attempt_id ?? state.accepted_review.attempt_id,
      target_before: targetSnapshot.head,
      source_revision: sourceRevision,
      target_branch: context.targetBranch,
    });
  }
  if (operation.value.status !== "SUCCEEDED") {
    let currentOperation = await readYamlFile(operation.path);
    if (currentOperation.value.status === "PREPARED") {
      currentOperation = await readYamlFile(operation.path);
      await updateOperation(operation.path, currentOperation.digest, [{ pointer: "/status", value: "EXECUTING" }]);
      currentOperation = await readYamlFile(operation.path);
    }
    if (currentOperation.value.status !== "EXECUTING") fail("INTEGRATION_OPERATION_NOT_EXECUTING", `Integration operation is ${currentOperation.value.status}.`, { operation_path: operation.path, status: currentOperation.value.status });
    try {
      const before = await gitSnapshot(context.repository);
      if (before.head !== sourceRevision) {
        if (before.head !== expectedTarget) fail("TARGET_DRIFT", "Target HEAD changed during integration preparation; no merge was attempted.", { actual: before.head, expected: expectedTarget });
        try {
          await runGit(context.repository, ["merge", "--ff-only", sourceRevision]);
        } catch (error) {
          if (error.code === "GIT_COMMAND_FAILED") fail("INTEGRATION_NOT_FAST_FORWARD", "Approved revision is not a fast-forward descendant of the current target checkpoint.", { source_revision: sourceRevision, target_before: before.head, expected_target: expectedTarget, next_action: "REVIEW_AGAINST_CURRENT_TARGET" });
          throw error;
        }
      }
      const after = await gitSnapshot(context.repository);
      if (after.head !== sourceRevision) fail("INTEGRATION_REVISION_MISMATCH", "Target did not end at the exact approved revision.", { actual: after.head, expected: sourceRevision });
      const resultDocument = await readYamlFile(operation.path);
      await updateOperation(operation.path, resultDocument.digest, [{ pointer: "/status", value: "SUCCEEDED" }, { pointer: "/result", value: { source_revision: sourceRevision, target_before: before.head, target_after: after.head, completed_at: new Date().toISOString() } }]);
    } catch (error) {
      try {
        const failedDocument = await readYamlFile(operation.path);
        if (["PREPARED", "EXECUTING"].includes(failedDocument.value.status)) await updateOperation(operation.path, failedDocument.digest, [{ pointer: "/status", value: "FAILED" }, { pointer: "/result", value: { error: error.code ?? "INTEGRATION_FAILED", message: error.message } }]);
      } catch {
        // Preserve the original failure; the durable operation remains for reconciliation.
      }
      throw error;
    }
    operation = { ...(await readYamlFile(operation.path)), path: operation.path };
    for (const previous of await readOperationFiles(context.runDirectory)) {
      if (previous.path === operation.path || previous.value?.operation_id !== operation.value.operation_id || previous.value?.status !== "FAILED" || previous.value?.input?.source_revision !== sourceRevision) continue;
      await updateOperation(previous.path, previous.digest, [
        { pointer: "/status", value: "SUPERSEDED" },
        { pointer: "/reconciliation/successor_operation_instance_id", value: operation.value.operation_instance_id ?? operation.value.operation_id },
        { pointer: "/reconciliation/final_status", value: "FAILED_EFFECT_RETAINED_FOR_SUCCESSOR" },
      ]);
    }
  }
  const operationResult = operation.value.result ?? (await readYamlFile(operation.path)).value.result;
  const targetAfter = operationResult.target_after ?? sourceRevision;
  const latestState = await readYamlFile(statePath);
  const stateSets = [
    { pointer: "/integrated_revision", value: sourceRevision },
    { pointer: "/integration", value: { operation_id: operation.value.operation_id, operation_instance_id: operation.value.operation_instance_id ?? operation.value.operation_id, operation_path: operation.path, source_revision: sourceRevision, target_before: operationResult.target_before ?? expectedTarget, target_after: targetAfter, completed_at: operationResult.completed_at ?? new Date().toISOString() } },
    { pointer: "/worktree/current_head", value: sourceRevision },
  ];
  const stateAfter = await updateYamlFile(statePath, latestState.digest, stateSets);
  const runDocument = await readRunDocument(runPath);
  const runTargetPath = isMapping(runDocument.value.project) ? "/project/target_head" : "/target/head";
  const currentRunTarget = isMapping(runDocument.value.project) ? runDocument.value.project.target_head : runDocument.value.target?.head;
  if (currentRunTarget !== targetAfter) await updateYamlFile(runPath, runDocument.digest, [{ pointer: runTargetPath, value: targetAfter }, { pointer: "/last_integrated_work_unit_id", value: unitId }, { pointer: "/last_integration_operation_id", value: operation.value.operation_id }, { pointer: "/last_integration_operation_instance_id", value: operation.value.operation_instance_id ?? operation.value.operation_id }]);
  return { run_id: runId, work_unit_id: unitId, state: "INTEGRATING", operation_path: operation.path, operation_id: operation.value.operation_id, operation_instance_id: operation.value.operation_instance_id ?? operation.value.operation_id, source_revision: sourceRevision, target_before: operationResult.target_before ?? expectedTarget, target_after: targetAfter, state_changed: stateAfter.changed, next_action: "RUN_HOST_VALIDATION_THEN_COMPLETE_TICKET" };
}

async function readTicketValidationEvidence(options, state, run, statePath, required) {
  if (!options.validation && !options.validationStatus) fail("VALIDATION_EVIDENCE_REQUIRED", "Provide --validation with a durable validation evidence path or --validation-status with an explicit host result.");
  if (required && !options.validation) fail("STRUCTURED_VALIDATION_REQUIRED", "This run requires a durable structured validation evidence file, not --validation-status alone.");
  let document = null;
  let value = { status: options.validationStatus ?? "PASS" };
  let evidencePath = null;
  if (options.validation) {
    evidencePath = resolve(options.validation);
    const runDirectory = runDirectoryFromStatePath(statePath);
    if (!pathIsInside(await canonicalPath(evidencePath), await canonicalPath(runDirectory))) fail("VALIDATION_PATH_OUTSIDE_RUN", "Validation evidence must remain inside the run namespace.", { actual: evidencePath, expected: `path inside ${runDirectory}` });
    document = await readYamlFile(evidencePath);
    value = document.value;
  }
  const status = value?.status ?? value?.verdict ?? "PASS";
  if (status !== "PASS" && status !== "PASSED") fail("VALIDATION_NOT_PASSED", `Host validation is ${status}.`, { actual: status, expected: ["PASS", "PASSED"] });
  const purposeIssues = [];
  const purpose = normalizePurpose(runPurposeValue(run), "purpose", purposeIssues);
  if (purposeIssues.length > 0) fail("INVALID_PURPOSE", "Host validation requires a valid admitted purpose.", { errors: purposeIssues });
  const completionMarker = completionMarkerForPurpose(purpose);
  if (value?.acceptance?.completion_marker !== undefined && value.acceptance.completion_marker !== completionMarker) fail("VALIDATION_COMPLETION_MARKER_MISMATCH", "Host validation completion marker does not match the admitted purpose.", { actual: value.acceptance.completion_marker, expected: completionMarker });
  if (required) {
    const errors = [];
    if (value.schema_version !== 1) errors.push(issue("schema_version", "UNSUPPORTED_SCHEMA", value.schema_version ?? null, 1, "Structured host validation requires schema version 1."));
    if (value.kind !== "squad-host-validation") errors.push(issue("kind", "INVALID_VALIDATION_KIND", value.kind ?? null, "squad-host-validation", "Structured host validation must identify its kind."));
    if (!isMapping(value.target)) errors.push(issue("target", "VALIDATION_FIELD_REQUIRED", null, "target.before/after/clean", "Validation must bind the exact target snapshot."));
    if (!isMapping(value.integration)) errors.push(issue("integration", "VALIDATION_FIELD_REQUIRED", null, "source_revision/operation_instance_id/target_before/target_after", "Validation must bind the integration operation."));
    if (!Array.isArray(value.checks)) errors.push(issue("checks", "VALIDATION_FIELD_REQUIRED", value.checks ?? null, "array", "Validation must record applicable checks."));
    if (!isMapping(value.acceptance)) errors.push(issue("acceptance", "VALIDATION_FIELD_REQUIRED", null, "criteria/limitations", "Validation must record acceptance coverage and limitations."));
    if (value.target?.clean !== true) errors.push(issue("target.clean", "TARGET_CLEAN_REQUIRED", value.target?.clean ?? null, true, "Structured validation must prove a clean target."));
    if (errors.length > 0) fail("INVALID_VALIDATION_EVIDENCE", "Structured host validation evidence is incomplete.", { errors });
    const targetRoot = run.project?.root ?? run.project_root;
    for (const [field, actual, expected] of [["integration.source_revision", value.integration.source_revision, state.integration.source_revision], ["integration.target_before", value.integration.target_before, state.integration.target_before], ["integration.target_after", value.integration.target_after, state.integration.target_after]]) {
      if (!actual) fail("VALIDATION_FIELD_REQUIRED", `${field} is required in structured validation evidence.`, { field });
      const resolvedActual = await resolveGitRevision(targetRoot, actual, field);
      const resolvedExpected = await resolveGitRevision(targetRoot, expected, `state.integration.${field.split(".").at(-1)}`);
      if (resolvedActual !== resolvedExpected) fail("VALIDATION_INTEGRATION_MISMATCH", `${field} does not match the durable integration snapshot.`, { field, actual: resolvedActual, expected: resolvedExpected });
    }
    if (value.integration.operation_instance_id !== (state.integration.operation_instance_id ?? state.integration.operation_id)) fail("VALIDATION_OPERATION_MISMATCH", "Validation evidence points to another integration operation instance.", { actual: value.integration.operation_instance_id ?? null, expected: state.integration.operation_instance_id ?? state.integration.operation_id });
    if (state.accepted_review?.report_digest && value.review?.report_digest !== state.accepted_review.report_digest) fail("VALIDATION_REVIEW_MISMATCH", "Validation evidence does not bind the accepted reviewer report digest.", { actual: value.review?.report_digest ?? null, expected: state.accepted_review.report_digest });
  }
  return { status, purpose, completion_marker: completionMarker, evidence_path: evidencePath, evidence_digest: document?.digest ?? null, ...(required ? { kind: value.kind, schema_version: value.schema_version, target: value.target, integration: value.integration, checks: value.checks, acceptance: value.acceptance, review: value.review ?? null } : {}) };
}

function validationMatches(existing, requested) {
  if (!existing || existing.status !== requested.status || existing.evidence_path !== requested.evidence_path || existing.evidence_digest !== requested.evidence_digest || (existing.kind && existing.kind !== requested.kind)) return false;
  if (existing.integration || requested.integration) {
    const existingIntegration = existing.integration ?? {};
    const requestedIntegration = requested.integration ?? {};
    for (const field of ["source_revision", "operation_instance_id", "target_before", "target_after"]) {
      if (existingIntegration[field] !== requestedIntegration[field]) return false;
    }
  }
  return true;
}

export async function completeTicket(options) {
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required to complete a ticket.");
  const statePath = resolve(options.state);
  const stateDocument = await readYamlFile(statePath);
  const state = stateDocument.value;
  const unitId = normalizeUnitId(state);
  const runDocument = await readRunDocument(join(runDirectoryFromStatePath(statePath), "run.yaml"));
  const run = runDocument.value;
  const requiredValidation = run.validation_evidence_required === true || run.admission?.validation_evidence_required === true;
  if (actualStateFromDocument(state) === "DONE") {
    const requestedValidation = await readTicketValidationEvidence(options, state, run, statePath, requiredValidation);
    const expectedMarker = requestedValidation.completion_marker;
    if (state.completion?.purpose !== undefined && state.completion.purpose !== requestedValidation.purpose) fail("COMPLETION_PURPOSE_MISMATCH", "Completed ticket purpose does not match the admitted run purpose.", { actual: state.completion.purpose, expected: requestedValidation.purpose });
    if (state.completion?.marker !== undefined && state.completion.marker !== expectedMarker) fail("COMPLETION_MARKER_MISMATCH", "Completed ticket marker does not match the admitted run purpose.", { actual: state.completion.marker, expected: expectedMarker });
    const targetRoot = run.project?.root ?? run.project_root;
    if (targetRoot && state.integration?.target_after) {
      const targetSnapshot = await gitSnapshot(targetRoot);
      const expectedTarget = await resolveGitRevision(targetRoot, state.integration.target_after, "state.integration.target_after");
      if (targetSnapshot.head !== expectedTarget) fail("COMPLETION_EVIDENCE_CONFLICT", "Ticket is already DONE but the target moved after completion.", { actual: targetSnapshot.head, expected: expectedTarget, next_action: "RETAIN_DONE_AND_REVIEW_TARGET_CHANGE" });
    }
    if (validationMatches(state.completion?.validation, requestedValidation)) return { work_unit_id: unitId, state: "DONE", integrated_revision: state.integration?.source_revision ?? state.integrated_revision ?? null, validation: state.completion.validation, transition_id: state.last_transition_id ?? null, acceptance_status_path: join(runDirectoryFromStatePath(statePath), "summaries", "acceptance-status.yaml"), projection_error: null, idempotent: true, next_action: "RUN_QA_OR_VERIFY_CRITERIA" };
    fail("COMPLETION_EVIDENCE_CONFLICT", "Ticket is already DONE with different validation evidence.", { existing: state.completion?.validation ?? null, requested: requestedValidation });
  }
  if (actualStateFromDocument(state) !== "INTEGRATING") fail("INVALID_COMPLETION_STATE", `Ticket completion requires INTEGRATING, not ${actualStateFromDocument(state)}.`, { actual: actualStateFromDocument(state), expected: "INTEGRATING" });
  if (!isMapping(state.integration) || !state.integration.operation_path) fail("INTEGRATION_REQUIRED", "Ticket completion requires a durable successful integration record.");
  const operationDocument = await readYamlFile(state.integration.operation_path);
  if (operationDocument.value.status !== "SUCCEEDED") fail("INTEGRATION_NOT_SUCCEEDED", `Integration operation is ${operationDocument.value.status}.`, { operation_path: state.integration.operation_path, status: operationDocument.value.status });
  const validation = await readTicketValidationEvidence(options, state, run, statePath, requiredValidation);
  const targetRoot = run.project?.root ?? run.project_root;
  if (targetRoot) {
    const targetSnapshot = await gitSnapshot(targetRoot);
    if (targetSnapshot.head !== state.integration.target_after) fail("TARGET_HEAD_MISMATCH", "Target moved after integration and before completion.", { actual: targetSnapshot.head, expected: state.integration.target_after });
  }
  const purposeIssues = [];
  const purpose = normalizePurpose(runPurposeValue(run), "purpose", purposeIssues);
  if (purposeIssues.length > 0) fail("INVALID_PURPOSE", "Ticket completion requires a valid admitted purpose.", { errors: purposeIssues });
  const completionMarker = completionMarkerForPurpose(purpose);
  const completedAt = new Date().toISOString();
  const transition = await commitUnitTransition({ statePath, workUnitId: unitId, from: "INTEGRATING", to: "DONE", reason: `Exact approved revision ${state.integration.source_revision} integrated and host validation passed for ${purpose}.`, operationId: operationDocument.value.operation_id, operationInstanceId: operationDocument.value.operation_instance_id ?? operationDocument.value.operation_id, extraSets: [{ pointer: "/completion", value: { status: "DONE", purpose, marker: completionMarker, validation, completed_at: completedAt } } ] });
  let projection;
  try {
    projection = await updateAcceptanceStatusProjection(runDirectoryFromStatePath(statePath));
  } catch (error) {
    projection = { path: join(runDirectoryFromStatePath(statePath), "summaries", "acceptance-status.yaml"), error: { code: error.code ?? "PROJECTION_WRITE_FAILED", message: error.message } };
  }
  return { work_unit_id: unitId, state: "DONE", integrated_revision: state.integration.source_revision, validation, transition_id: transition.transition_id, acceptance_status_path: projection.path, projection_error: projection.error ?? null, next_action: projection.error ? "REPAIR_ACCEPTANCE_PROJECTION" : "RUN_QA_OR_VERIFY_CRITERIA" };
}

async function nextQaAttemptNumber(runDirectory) {
  const qaDirectory = join(runDirectory, "qa");
  if (!(await pathExists(qaDirectory))) return 1;
  const values = (await readdir(qaDirectory, { withFileTypes: true }))
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name.match(/^QA-([0-9]{3,6})$/)?.[1])
    .filter(Boolean)
    .map(Number);
  return Math.max(0, ...values) + 1;
}

async function createRunDispatchOperation(runDirectory, operationId, operationInstanceId, input) {
  const operationPath = operationPathFor(runDirectory, operationId, operationInstanceId);
  const operation = {
    schema_version: 1,
    operation_id: operationId,
    operation_instance_id: operationInstanceId,
    work_unit_id: "RUN",
    attempt_id: input.attempt_id,
    type: input.type,
    status: "PREPARED",
    job_id: null,
    agent_provider: null,
    input: { ...input, work_unit_id: "RUN" },
    result: null,
  };
  const written = await writeImmutableYaml(operationPath, operation);
  const document = await readYamlFile(operationPath);
  return { path: operationPath, digest: document.digest, value: document.value, write: written };
}

export async function prepareRunQa(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const runDocument = await readRunDocument(runPath);
  const run = runDocument.value;
  const previousBlocker = isMapping(run.blocker) ? run.blocker : null;
  const runDirectory = dirname(runPath);
  const currentRunState = actualRunState(run);
  const recovering = currentRunState === "BLOCKED" && run.blocker?.resume_state === "QA" && ["AGENT_INTERRUPTED", "QA_INCONCLUSIVE"].includes(run.blocker?.code);
  if (currentRunState !== "RUN_VALIDATING" && !recovering) fail("INVALID_QA_PREPARATION_STATE", `QA preparation requires RUN_VALIDATING or a QA recovery blocker, not ${currentRunState}.`, { actual: currentRunState, expected: ["RUN_VALIDATING", "BLOCKED"] });
  if (!recovering) {
    const preflight = await preflightRun(runPath);
    if (!preflight.valid) fail("PREFLIGHT_FAILED", "Run-level QA preparation requires a valid run preflight.", { issues: preflight.issues });
  }
  const artifacts = await allRunArtifacts(runPath);
  const incomplete = artifacts.units.filter((unit) => !unit.value || actualStateFromDocument(unit.value) !== "DONE");
  if (artifacts.units.length === 0) fail("NO_WORK_UNITS", "Run-level QA requires at least one in-scope work unit.");
  if (incomplete.length > 0) fail("WORK_UNITS_INCOMPLETE", "Run-level QA cannot start until every in-scope work unit is DONE.", { work_units: incomplete.map((unit) => ({ work_unit_id: normalizeUnitId(unit.value), state: actualStateFromDocument(unit.value) })) });
  const projectRoot = run.project?.root ?? run.project_root;
  if (!projectRoot) fail("PROJECT_ROOT_REQUIRED", "Run-level QA requires an admitted project root.");
  const target = await gitSnapshot(projectRoot);
  const expectedBranch = run.project?.target_branch ?? run.target?.branch;
  if (expectedBranch && target.branch !== expectedBranch) fail("TARGET_BRANCH_MISMATCH", "Run-level QA target branch changed.", { actual: target.branch, expected: expectedBranch });
  const expectedHead = run.project?.target_head ?? run.target?.head;
  if (expectedHead) {
    const resolvedExpectedHead = await resolveGitRevision(projectRoot, expectedHead, "project.target_head");
    if (target.head !== resolvedExpectedHead) fail("TARGET_DRIFT", "Run-level QA target HEAD changed since the run checkpoint.", { actual: target.head, expected: resolvedExpectedHead });
  }
  if (target.dirty) fail("TARGET_DIRTY", "Run-level QA requires a clean target checkout.", { status: target.status });
  const attemptNumber = padAttempt(options.attempt ?? await nextQaAttemptNumber(runDirectory));
  const qaId = `QA-${attemptNumber}`;
  const attemptId = `${runDocument.run_id}:qa:attempt-${attemptNumber}`;
  const operationId = `${runDocument.run_id}:RUN:DISPATCH_QA`;
  const operationInstanceId = options.operation_instance_id ?? operationInstanceIdFor(operationId, attemptNumber);
  const qaDirectory = join(runDirectory, "qa", qaId);
  const handoffPath = resolve(options.handoff ?? join(qaDirectory, "handoff.yaml"));
  const reportPath = resolve(options.report ?? join(qaDirectory, "report.yaml"));
  const evidenceDirectory = resolve(options.evidence ?? join(qaDirectory, "evidence"));
  const operationPath = operationPathFor(runDirectory, operationId, operationInstanceId);
  await mkdir(dirname(reportPath), { recursive: true });
  await mkdir(evidenceDirectory, { recursive: true });
  const sourcePath = run.source?.tickets_index_path ?? run.source?.tickets_path;
  const proposal = proposalProjection(run);
  if (!sourcePath) fail("SOURCE_REQUIRED", "Run-level QA requires the canonical tickets index.");
  const sourceDigest = await digestFile(sourcePath);
  const expectedSourceDigest = run.source?.digest ?? run.source?.tickets_digest;
  if (expectedSourceDigest && sourceDigest !== String(expectedSourceDigest).toLowerCase()) fail("SOURCE_DIGEST_MISMATCH", "Canonical tickets index changed before run-level QA.", { actual: sourceDigest, expected: expectedSourceDigest });
  const operation = await createRunDispatchOperation(runDirectory, operationId, operationInstanceId, {
    run_id: runDocument.run_id,
    qa_id: qaId,
    attempt_id: attemptId,
    type: "DISPATCH_QA",
    manifest_path: null,
    handoff_path: handoffPath,
    report_path: reportPath,
    evidence_directory: evidenceDirectory,
    target_head: target.head,
    source_revision: target.head,
  });
  let transition;
  try {
    transition = recovering
      ? await commitRunTransition({ runPath, runId: runDocument.run_id, from: "BLOCKED", to: "QA", reason: "Resume QA after agent reconciliation.", controller: "prepare-qa" })
      : await commitRunTransition({ runPath, runId: runDocument.run_id, from: "RUN_VALIDATING", to: "QA", reason: "All work units are DONE and the run-level QA handoff is ready.", controller: "prepare-qa" });
  } catch (error) {
    const currentOperation = await readYamlFile(operation.path);
    if (["PREPARED", "COMMITTING"].includes(currentOperation.value.status)) await updateOperation(operation.path, currentOperation.digest, [{ pointer: "/status", value: "UNKNOWN" }, { pointer: "/reconciliation_required", value: true }, { pointer: "/failure", value: { code: error.code ?? "RUN_TRANSITION_FAILED", message: error.message } }]);
    throw error;
  }
  const refreshedRun = await readRunDocument(runPath);
  const handoff = {
    schema_version: 1,
    kind: "squad-qa-handoff",
    role: "squad-qa",
    run_id: runDocument.run_id,
    purpose: runPurposeValue(run),
    completion_marker: completionMarkerForPurpose(runPurposeValue(run)),
    qa_id: qaId,
    attempt_id: attemptId,
    operation_id: operationId,
    operation_instance_id: operationInstanceId,
    source: { tickets_index_path: sourcePath, tickets_digest: sourceDigest, proposal_required: proposal.required, ...(proposal.path ? { proposal_path: resolve(proposal.path), proposal_digest: proposal.digest } : {}) },
    artifact: { run_dir: runDirectory, handoff_path: handoffPath, operation_path: operationPath, report_path: reportPath, evidence_directory: evidenceDirectory },
    target: { repository_root: target.root, repository_id: target.repository_id, branch: target.branch, head: target.head },
    state: { current: actualRunState(refreshedRun.value), expected: "QA" },
    report: { path: reportPath, digest: null, expected: "CREATE" },
    outcome_profile: run.outcome_profile ?? { core_success_criteria: run.core_success_criteria ?? [], required_optional_coverage: run.required_optional_coverage ?? null },
    capability_environment_profile: { ...(isMapping(run.environment) ? run.environment : {}), ...environmentAdmissionProjection(run) },
    authority_profile: run.authority ?? null,
    historical_context: { tickets: artifacts.units.map((unit) => normalizeUnitId(unit.value)), qa_findings: run.qa?.findings ?? [], regression_boundary: run.regression_boundary ?? null },
  };
  await writeImmutableYaml(handoffPath, handoff);
  const handoffDocument = await readYamlFile(handoffPath);
  const validation = await validateQaHandoffData(handoff, handoffPath, { throwOnInvalid: false });
  if (!validation.valid) {
    const currentOperation = await readYamlFile(operation.path);
    await updateOperation(operation.path, currentOperation.digest, [{ pointer: "/status", value: "UNKNOWN" }, { pointer: "/validation_errors", value: validation.errors }]);
    fail("QA_HANDOFF_INVALID", `Generated QA handoff failed validation: ${handoffPath}`, { errors: validation.errors });
  }
  const operationDocument = await readYamlFile(operation.path);
  await updateOperation(operation.path, operationDocument.digest, [{ pointer: "/result", value: { ready_to_dispatch: true, handoff_path: handoffPath, handoff_digest: handoffDocument.digest, report_path: reportPath, evidence_directory: evidenceDirectory } }]);
  const latest = await readRunDocument(runPath);
  const activeQa = { qa_id: qaId, attempt_id: attemptId, operation_id: operationId, operation_instance_id: operationInstanceId, operation_path: operationPath, handoff_path: handoffPath, handoff_digest: handoffDocument.digest, report_path: reportPath, evidence_directory: evidenceDirectory };
  await updateYamlFile(runPath, latest.digest, [{ pointer: "/active_qa", value: activeQa }, { pointer: "/qa", value: { ...activeQa, status: "PENDING", verdict: null }, }, { pointer: "/blocker", value: null }]);
  const oldOperationId = previousBlocker?.metadata?.operation_id;
  const oldOperationInstanceId = previousBlocker?.metadata?.operation_instance_id;
  if (oldOperationId && oldOperationInstanceId) {
    const oldPath = await resolveOperationPath(runDirectory, oldOperationId, oldOperationInstanceId);
    if (await pathExists(oldPath)) {
      const oldDocument = await readYamlFile(oldPath);
      if (["UNKNOWN", "RECONCILING"].includes(oldDocument.value.status)) await updateOperation(oldPath, oldDocument.digest, [{ pointer: "/status", value: "SUPERSEDED" }, { pointer: "/reconciliation/successor_operation_instance_id", value: operationInstanceId }]);
    }
  }
  return { run_id: runDocument.run_id, qa_id: qaId, attempt_id: attemptId, operation_path: operationPath, operation_id: operationId, operation_instance_id: operationInstanceId, handoff_path: handoffPath, report_path: reportPath, evidence_directory: evidenceDirectory, state: "QA", transition_id: transition.transition_id, next_action: "SPAWN_AGENT_WITH_VALIDATED_HANDOFF" };
}

export async function completeRunQa(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const runDocument = await readRunDocument(runPath);
  const run = runDocument.value;
  if (actualRunState(run) !== "QA") fail("INVALID_QA_COMPLETION_STATE", `QA completion requires QA, not ${actualRunState(run)}.`, { actual: actualRunState(run), expected: "QA" });
  const activeQa = run.active_qa ?? {};
  if (!activeQa.handoff_path) fail("QA_HANDOFF_REQUIRED", "The run has no active QA handoff.");
  const handoffValidation = await validateHandoffFile(activeQa.handoff_path, { historical: true, throwOnInvalid: false });
  if (!handoffValidation.valid) fail("QA_HANDOFF_INVALID", "The active QA handoff is no longer structurally valid.", { errors: handoffValidation.errors });
  const reportInput = options.report ?? activeQa.report_path ?? run.qa?.report_path;
  if (!reportInput) fail("QA_REPORT_REQUIRED", "The exact QA report path is required.");
  const reportPath = resolve(reportInput);
  const reportDocument = await readYamlFile(reportPath);
  const report = reportDocument.value;
  if (resolve(reportPath) !== resolve(activeQa.report_path ?? reportPath)) fail("QA_REPORT_PATH_MISMATCH", "The QA report is not the active report path.", { actual: reportPath, expected: activeQa.report_path ?? null });
  if (report.role !== "squad-qa" || report.run_id !== runDocument.run_id || report.qa_id !== activeQa.qa_id || report.attempt_id !== activeQa.attempt_id) fail("QA_REPORT_IDENTITY_MISMATCH", "The QA report does not belong to this active run-level QA attempt.", { role: report.role ?? null, run_id: report.run_id ?? null, qa_id: report.qa_id ?? null, attempt_id: report.attempt_id ?? null, expected: { role: "squad-qa", run_id: runDocument.run_id, qa_id: activeQa.qa_id ?? null, attempt_id: activeQa.attempt_id ?? null } });
  const admittedPurposeIssues = [];
  const admittedPurpose = normalizePurpose(runPurposeValue(run), "purpose", admittedPurposeIssues);
  if (admittedPurpose === "prototype" && report.purpose === undefined) fail("QA_PURPOSE_REQUIRED", "A prototype QA report must record its prototype purpose explicitly.", { expected: "prototype" });
  const reportPurpose = normalizePurpose(report.purpose, "report.purpose", [], admittedPurpose ?? "production");
  if (admittedPurposeIssues.length > 0) fail("INVALID_PURPOSE", "The run has an invalid admitted purpose.", { errors: admittedPurposeIssues });
  if (reportPurpose !== admittedPurpose) fail("QA_PURPOSE_MISMATCH", "The QA report purpose does not match the admitted run purpose.", { actual: reportPurpose, expected: admittedPurpose });
  const reportMarker = report.completion_marker ?? completionMarkerForPurpose(reportPurpose);
  if (reportMarker !== completionMarkerForPurpose(admittedPurpose)) fail("QA_COMPLETION_MARKER_MISMATCH", "The QA report completion marker does not match the admitted purpose.", { actual: reportMarker, expected: completionMarkerForPurpose(admittedPurpose) });
  if (report.status !== "COMPLETE") fail("QA_REPORT_INCOMPLETE", `QA report is ${report.status ?? "<missing>"}, not COMPLETE.`);
  if (!["PASSED", "FAILED", "INCONCLUSIVE"].includes(report.verdict)) fail("INVALID_QA_VERDICT", `Unsupported QA verdict: ${report.verdict ?? "<missing>"}.`, { expected: ["PASSED", "FAILED", "INCONCLUSIVE"] });
  const targetRoot = run.project?.root ?? run.project_root;
  const target = await gitSnapshot(targetRoot);
  const canonicalRevision = report.canonical?.revision;
  if (!canonicalRevision) fail("QA_REVISION_REQUIRED", "QA report must identify the canonical integrated revision.");
  const resolvedCanonical = await resolveGitRevision(targetRoot, canonicalRevision, "qa.canonical.revision");
  if (resolvedCanonical !== target.head) fail("QA_REVISION_MISMATCH", "QA report is not for the current target revision.", { actual: resolvedCanonical, expected: target.head });
  const operationPath = activeQa.operation_path;
  if (!operationPath) fail("QA_OPERATION_REQUIRED", "The run has no active QA operation.");
  const operationDocument = await readYamlFile(operationPath);
  if (!["EXECUTING", "SUCCEEDED"].includes(operationDocument.value.status)) fail("QA_OPERATION_NOT_EXECUTING", `QA operation is ${operationDocument.value.status}.`, { expected: ["EXECUTING", "SUCCEEDED"] });
  if (operationDocument.value.status === "EXECUTING") {
    await updateOperation(operationPath, operationDocument.digest, [{ pointer: "/status", value: "SUCCEEDED" }, { pointer: "/result", value: { report_path: reportPath, report_digest: reportDocument.digest, verdict: report.verdict, canonical_revision: resolvedCanonical, completed_at: new Date().toISOString() } }]);
  }
  const history = Array.isArray(run.qa_history) ? [...run.qa_history] : [];
  history.push({ ...(run.active_qa ?? {}), report_path: reportPath, report_digest: reportDocument.digest, verdict: report.verdict, canonical_revision: resolvedCanonical, completed_at: new Date().toISOString() });
  const nextState = report.verdict === "PASSED" ? "COMPLETING" : "BLOCKED";
  const extraSets = [
    { pointer: "/qa", value: { ...(run.qa ?? {}), report_path: reportPath, report_digest: reportDocument.digest, verdict: report.verdict, status: "COMPLETE", canonical_revision: resolvedCanonical } },
    { pointer: "/qa_history", value: history },
    { pointer: "/active_qa", value: null },
  ];
  if (nextState === "BLOCKED") extraSets.push({ pointer: "/blocker", value: { type: report.verdict === "FAILED" ? "QA_OUTCOME" : "QA_CAPABILITY", code: report.verdict === "FAILED" ? "QA_FAILURE_ATTRIBUTION_REQUIRED" : "QA_INCONCLUSIVE", reason: report.verdict === "FAILED" ? "QA evidence reports a failure; host attribution/remediation is required." : "QA evidence is inconclusive; repair the evidence boundary before resuming.", source_state: "QA", resume_state: "QA", required_to_resume: [report.verdict === "FAILED" ? "attribute_qa_failure" : "repair_qa_evidence"], metadata: { report_path: reportPath, report_digest: reportDocument.digest } } });
  const transition = await commitRunTransition({ runPath, runId: runDocument.run_id, from: "QA", to: nextState, reason: `QA report ${report.verdict} was durably recorded.`, extraSets, ...(nextState === "COMPLETING" ? { controller: "complete-qa" } : {}) });
  return { run_id: runDocument.run_id, state: nextState, verdict: report.verdict, report_path: reportPath, report_digest: reportDocument.digest, transition_id: transition.transition_id, next_action: nextState === "COMPLETING" ? "COMPLETE_RUN" : "RESOLVE_QA_BLOCKER" };
}

export async function resumeRun(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const runDocument = await readRunDocument(runPath);
  const run = runDocument.value;
  if (actualRunState(run) !== "PAUSED") fail("RUN_NOT_PAUSED", `Run resume requires PAUSED, not ${actualRunState(run)}.`, { actual: actualRunState(run), expected: "PAUSED" });
  const preflight = await preflightRun(runPath);
  if (!preflight.valid) fail("PREFLIGHT_FAILED", "A paused run cannot resume until its source, target, operations, and transitions pass preflight.", { issues: preflight.issues });
  const transition = await commitRunTransition({ runPath, runId: runDocument.run_id, from: "PAUSED", to: "EXECUTING", reason: "Resume passed run preflight after an explicit pause.", controller: "resume-run" });
  return { run_id: runDocument.run_id, state: "EXECUTING", transition_id: transition.transition_id, next_action: "CONTINUE_ELIGIBLE_WORK" };
}

export async function completeRun(options) {
  const runPath = await resolveRunPath(options, options.runId);
  const runDocument = await readRunDocument(runPath);
  const run = runDocument.value;
  if (actualRunState(run) !== "COMPLETING") fail("INVALID_RUN_COMPLETION_STATE", `Run completion requires COMPLETING, not ${actualRunState(run)}.`, { actual: actualRunState(run), expected: "COMPLETING" });
  const artifacts = await allRunArtifacts(runPath);
  const incomplete = artifacts.units.filter((unit) => !unit.value || actualStateFromDocument(unit.value) !== "DONE");
  if (artifacts.units.length === 0) fail("NO_WORK_UNITS", "Run completion requires at least one in-scope work unit.");
  if (incomplete.length > 0) fail("WORK_UNITS_INCOMPLETE", "Run completion requires every work unit to be DONE.", { work_units: incomplete.map((unit) => ({ work_unit_id: normalizeUnitId(unit.value), state: actualStateFromDocument(unit.value) })) });
  if (run.qa?.verdict !== "PASSED" || !run.qa?.report_path) fail("QA_NOT_PASSED", "Run completion requires a durable PASSED QA report.", { verdict: run.qa?.verdict ?? null });
  const qaReport = await readYamlFile(run.qa.report_path);
  if (run.qa.report_digest && qaReport.digest !== run.qa.report_digest) fail("QA_REPORT_DIGEST_MISMATCH", "The recorded QA report digest differs from the current report.", { actual: qaReport.digest, expected: run.qa.report_digest });
  if (qaReport.value.status !== "COMPLETE" || qaReport.value.verdict !== "PASSED") fail("QA_NOT_PASSED", "The recorded QA report is not a complete PASSED report.", { status: qaReport.value.status ?? null, verdict: qaReport.value.verdict ?? null });
  const preflight = await preflightRun(runPath);
  if (!preflight.valid) fail("PREFLIGHT_FAILED", "Run completion requires a valid preflight.", { issues: preflight.issues });
  const target = await gitSnapshot(run.project?.root ?? run.project_root);
  const finalSummaryPath = join(dirname(runPath), "summaries", "final.yaml");
  const purpose = runPurposeValue(run);
  const finalSummary = { schema_version: 1, kind: "squad-final-summary", run_id: runDocument.run_id, purpose, completion_marker: completionMarkerForPurpose(purpose), target: { branch: target.branch, head: target.head, repository_id: target.repository_id }, qa: { report_path: run.qa.report_path, report_digest: run.qa.report_digest, verdict: run.qa.verdict }, work_units: artifacts.units.map((unit) => ({ work_unit_id: normalizeUnitId(unit.value), state: actualStateFromDocument(unit.value), completion_marker: completionMarkerForPurpose(purpose), integrated_revision: unit.value.integrated_revision ?? unit.value.integration?.source_revision ?? null })), completed_at: new Date().toISOString() };
  const written = await writeImmutableYaml(finalSummaryPath, finalSummary);
  const transition = await commitRunTransition({ runPath, runId: runDocument.run_id, from: "COMPLETING", to: "RUN_COMPLETED", reason: "All work units, QA evidence, and final target validation passed.", controller: "complete-run", extraSets: [{ pointer: "/final_summary_path", value: finalSummaryPath }, { pointer: "/final_summary_digest", value: written.digest }, { pointer: "/cleanup_state", value: "RETAINED_UNTIL_EXPLICIT_CLEANUP" }] });
  return { run_id: runDocument.run_id, state: "RUN_COMPLETED", transition_id: transition.transition_id, final_summary_path: finalSummaryPath, final_summary_digest: written.digest, next_action: "EXPLICIT_CLEANUP_ONLY" };
}

function operationsForJob(operations, jobId, workUnitId = undefined) {
  return operations.filter((entry) => {
    const value = entry.value;
    if (!value || !(value.job_id === jobId || value.agent_job_id === jobId || value.input?.job_id === jobId || value.result?.job_id === jobId)) return false;
    if (!workUnitId) return true;
    return (value.work_unit_id ?? value.input?.work_unit_id) === workUnitId;
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
  if (!(await pathExists(operationPath))) fail("OPERATION_NOT_FOUND", `Dispatch operation is not readable: ${operationPath}`, { operation_path: operationPath });
  const operationDocument = await readYamlFile(operationPath);
  const operation = operationDocument.value;
  const runDirectory = dirname(dirname(operationPath));
  const duplicateBindings = operationsForJob(await readOperationFiles(runDirectory), jobId).filter((entry) => resolve(entry.path) !== operationPath);
  if (duplicateBindings.length > 0) {
    fail("AMBIGUOUS_AGENT_JOB", `Agent job ${jobId} is already bound to another operation.`, {
      job_id: jobId,
      operation_path: operationPath,
      candidates: duplicateBindings.map((entry) => ({ path: entry.path, operation_id: entry.value?.operation_id, operation_instance_id: entry.value?.operation_instance_id ?? entry.value?.operation_id, attempt_id: entry.value?.attempt_id })),
    });
  }
  if (!OPERATION_STATES.includes(operation.status)) fail("INVALID_OPERATION_STATUS", `Operation has unsupported status: ${operation.status}`, { status: operation.status, expected: OPERATION_STATES });
  if (operation.job_id && operation.job_id !== jobId) fail("AGENT_JOB_MISMATCH", `Operation is already bound to ${operation.job_id}.`, { field: "job_id", actual: operation.job_id, expected: jobId });
  const handoffPath = operation.result?.handoff_path ?? operation.input?.handoff_path;
  if (!handoffPath) fail("HANDOFF_REQUIRED", "The dispatch operation has no generated handoff path.");
  if (!(await pathExists(handoffPath))) fail("HANDOFF_NOT_FOUND", `Generated handoff is not readable: ${handoffPath}`, { handoff_path: handoffPath, operation_path: operationPath });
  const validation = await validateHandoffFile(handoffPath, { throwOnInvalid: false });
  if (!validation.valid) fail("HANDOFF_INVALID", `Cannot bind an unvalidated handoff: ${handoffPath}`, { errors: validation.errors });
  if (operation.status === "EXECUTING" && operation.job_id === jobId) {
    return { operation_path: operationPath, operation_id: operation.operation_id, operation_instance_id: operation.operation_instance_id ?? operation.operation_id, job_id: jobId, operation_status: operation.status, handoff_path: handoffPath, handoff_digest: validation.digest, changed: false, next_action: "OBSERVE_AGENT_RESULT" };
  }
  if (operation.status !== "PREPARED") fail("OPERATION_NOT_DISPATCHABLE", `Operation ${operation.operation_id} is ${operation.status}, not dispatch-ready.`, { status: operation.status, expected: ["PREPARED"] });
  const updated = await updateOperation(operationPath, operationDocument.digest, [
    { pointer: "/job_id", value: jobId },
    { pointer: "/agent_provider", value: options.provider ?? options.agentProvider ?? operation.agent_provider ?? "unknown" },
    { pointer: "/status", value: "EXECUTING" },
    { pointer: "/dispatch_binding", value: { provider: options.provider ?? options.agentProvider ?? operation.agent_provider ?? "unknown", job_id: jobId, handoff_path: handoffPath, handoff_digest: validation.digest, operation_id: operation.operation_id, operation_instance_id: operation.operation_instance_id ?? operation.operation_id, attempt_id: operation.attempt_id } },
  ]);
  const readBack = await readYamlFile(operationPath);
  if (readBack.value.job_id !== jobId || readBack.value.status !== "EXECUTING") fail("BIND_VERIFY_FAILED", `Agent binding did not verify: ${operationPath}`, { operation_path: operationPath, expected_job_id: jobId, actual_job_id: readBack.value.job_id, expected_status: "EXECUTING", actual_status: readBack.value.status });
  return { operation_path: operationPath, operation_id: operation.operation_id, operation_instance_id: operation.operation_instance_id ?? operation.operation_id, job_id: jobId, operation_status: "EXECUTING", handoff_path: handoffPath, handoff_digest: validation.digest, changed: updated.changed, next_action: "SPAWN_OR_OBSERVE_AGENT" };
}

async function reconcileRunAgent(options) {
  const jobId = options.jobId ?? options.position;
  const runPath = await resolveRunPath(options, options.runId);
  const runDocument = await readRunDocument(runPath);
  const run = runDocument.value;
  const runDirectory = dirname(runPath);
  const operations = await readOperationFiles(runDirectory);
  let operation;
  if (options.operation) operation = { ...(await readYamlFile(options.operation)), path: resolve(options.operation) };
  else {
    const candidates = operationsForJob(operations, jobId, "RUN");
    if (candidates.length > 1) fail("AMBIGUOUS_AGENT_JOB", `Agent job ${jobId} is bound to multiple run operations; supply --operation.`, { job_id: jobId, candidates: candidates.map((entry) => ({ path: entry.path, operation_id: entry.value?.operation_id, operation_instance_id: entry.value?.operation_instance_id ?? entry.value?.operation_id })) });
    operation = candidates[0];
  }
  if (!operation?.value) fail("OPERATION_NOT_FOUND", `No durable run operation is associated with agent job ${jobId}.`, { job_id: jobId, operation_paths: operations.map((entry) => entry.path) });
  const operationValue = operation.value;
  if ((operationValue.work_unit_id ?? operationValue.input?.work_unit_id) !== "RUN") fail("WORK_UNIT_ID_MISMATCH", "The selected operation is not run-scoped.", { actual: operationValue.work_unit_id ?? operationValue.input?.work_unit_id ?? null, expected: "RUN" });
  if (!pathIsInside(await canonicalPath(operation.path), await canonicalPath(runDirectory))) fail("OPERATION_PATH_OUTSIDE_RUN", `Operation path is outside the run namespace: ${operation.path}`, { operation_path: operation.path, run_directory: runDirectory });
  const reportPath = options.report ?? operationValue.input?.report_path ?? run.active_qa?.report_path ?? null;
  const reportAvailable = reportPath ? await pathExists(reportPath) : false;
  const reconciliation = { job_id: jobId, observed_at: new Date().toISOString(), effect: reportAvailable ? "EFFECT_APPLIED" : "INCONCLUSIVE", report: reportAvailable ? { path: resolve(reportPath), digest: (await readYamlFile(reportPath)).digest } : null, preserves_target: true, uncertainty: reportAvailable ? null : "QA side effects cannot be inferred without a durable QA report." };
  let operationDocument = await readYamlFile(operation.path);
  if (!["PREPARED", "EXECUTING", "UNKNOWN", "RECONCILING"].includes(operationDocument.value.status)) fail("INVALID_OPERATION_STATUS", `Run operation has unsupported reconciliation status: ${operationDocument.value.status}`, { status: operationDocument.value.status });
  if (operationDocument.value.status !== "RECONCILING") {
    if (operationDocument.value.status !== "UNKNOWN") {
      await updateOperation(operation.path, operationDocument.digest, [{ pointer: "/status", value: "UNKNOWN" }, { pointer: "/reconciliation", value: reconciliation }]);
      operationDocument = await readYamlFile(operation.path);
    }
    await updateOperation(operation.path, operationDocument.digest, [{ pointer: "/status", value: "RECONCILING" }, { pointer: "/reconciliation", value: reconciliation }]);
  } else await updateOperation(operation.path, operationDocument.digest, [{ pointer: "/reconciliation", value: reconciliation }]);
  const currentState = actualRunState(run);
  const blocker = { type: "AGENT_UNAVAILABLE", code: "AGENT_INTERRUPTED", reason: `Agent job ${jobId} stopped before a conclusive run-level result; QA side effects were inspected and retained.`, source_state: currentState, resume_state: currentState === "QA" ? "QA" : "RUN_VALIDATING", role: "qa", required_to_resume: ["operation_reconciliation", "validated_qa_handoff"], metadata: { job_id: jobId, operation_id: operationValue.operation_id, operation_instance_id: operationValue.operation_instance_id ?? operationValue.operation_id, operation_status: "RECONCILING", effect: reconciliation.effect, report_path: reportPath } };
  let stateChange;
  if (currentState !== "BLOCKED") stateChange = await commitRunTransition({ runPath, runId: runDocument.run_id, from: currentState, to: "BLOCKED", reason: blocker.reason, extraSets: [{ pointer: "/blocker", value: blocker }] });
  else {
    const latest = await readRunDocument(runPath);
    stateChange = await updateYamlFile(runPath, latest.digest, [{ pointer: "/blocker", value: blocker }]);
  }
  return { job_id: jobId, run_id: runDocument.run_id, operation_id: operationValue.operation_id, operation_instance_id: operationValue.operation_instance_id ?? operationValue.operation_id, operation_path: operation.path, operation_status: "RECONCILING", effect: reconciliation.effect, blocker, state: "BLOCKED", state_change: stateChange, next_action: "PREPARE_QA" };
}

export async function rejectHandoff(options) {
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required for handoff rejection.");
  if (!options.reason) fail("MISSING_ARGUMENT", "--reason is required for handoff rejection.");
  const statePath = resolve(options.state);
  const stateDocument = await readYamlFile(statePath);
  const state = stateDocument.value;
  const unitId = normalizeUnitId(state);
  const runId = normalizeRunId(state);
  if (!unitId || !runId) fail("INVALID_STATE", "State must contain run_id and work_unit_id for handoff rejection.");
  const active = activeHandoffFromState(state);
  if (!active?.handoff_path) fail("ACTIVE_HANDOFF_REQUIRED", "No active handoff is available to reject.");
  const runDirectory = runDirectoryFromStatePath(statePath);
  const operationPath = resolve(options.operation ?? active.operation_path ?? await resolveOperationPath(runDirectory, active.operation_id, active.operation_instance_id));
  const operationDocument = await readYamlFile(operationPath);
  if (!["PREPARED", "EXECUTING"].includes(operationDocument.value.status)) fail("HANDOFF_REJECTION_NOT_ALLOWED", `Operation is ${operationDocument.value.status}; handoff rejection is only for pre-product-review dispatches.`, { status: operationDocument.value.status, expected: ["PREPARED", "EXECUTING"] });
  const reportPath = active.report_path;
  if (reportPath && await pathExists(reportPath)) fail("PRODUCT_REPORT_EXISTS", "A product role report already exists; use the role completion command instead of rejecting the handoff.", { report_path: reportPath });
  const operationUpdate = await updateOperation(operationPath, operationDocument.digest, [{ pointer: "/status", value: "SUPERSEDED" }, { pointer: "/result", value: { outcome: "HANDOFF_REJECTED_BEFORE_PRODUCT_REVIEW", reason: options.reason, rejected_at: new Date().toISOString() } }]);
  const currentState = actualStateFromDocument(state);
  const blocker = { type: "HANDOFF_CONTEXT", code: "HANDOFF_REJECTED_BEFORE_PRODUCT_REVIEW", reason: options.reason, source_state: currentState, resume_state: currentState, required_to_resume: ["repair_handoff_context", "validated_successor_handoff"], metadata: { operation_id: operationDocument.value.operation_id, operation_instance_id: operationDocument.value.operation_instance_id ?? operationDocument.value.operation_id, operation_path: operationPath, handoff_path: active.handoff_path } };
  const archiveSets = archiveActiveHandoffSets(state, { outcome: "HANDOFF_REJECTED_BEFORE_PRODUCT_REVIEW", reportPath: null, reportDigest: null, revision: null, completedAt: new Date().toISOString() });
  const transition = await commitUnitTransition({ statePath, workUnitId: unitId, from: currentState, to: "BLOCKED", reason: `Handoff rejected before product review: ${options.reason}`, operationId: operationDocument.value.operation_id, operationInstanceId: operationDocument.value.operation_instance_id ?? operationDocument.value.operation_id, extraSets: [{ pointer: "/blocker", value: blocker }, ...archiveSets] });
  return { run_id: runId, work_unit_id: unitId, state: "BLOCKED", outcome: "HANDOFF_REJECTED_BEFORE_PRODUCT_REVIEW", operation_path: operationPath, operation_id: operationDocument.value.operation_id, operation_instance_id: operationDocument.value.operation_instance_id ?? operationDocument.value.operation_id, operation_status: "SUPERSEDED", transition_id: transition.transition_id, operation_digest: operationUpdate.digest, next_action: "REPAIR_CONTEXT_THEN_RESUME_TICKET" };
}

export async function acknowledgeAgent(options) {
  const jobId = options.jobId ?? options.position;
  if (!jobId) fail("MISSING_ARGUMENT", "acknowledge-agent requires a job ID.");
  if (!options.state) fail("MISSING_ARGUMENT", "--state is required for worker acknowledgement.");
  const statePath = resolve(options.state);
  const stateDocument = await readYamlFile(statePath);
  const state = stateDocument.value;
  const unitId = normalizeUnitId(state);
  const runId = normalizeRunId(state);
  if (!unitId || !runId) fail("INVALID_STATE", "State must contain run_id and work_unit_id for acknowledgement.");
  const currentState = actualStateFromDocument(state);
  if (!['ASSIGNED', 'IMPLEMENTING'].includes(currentState)) fail("INVALID_ACKNOWLEDGEMENT_STATE", `Worker acknowledgement requires ASSIGNED or IMPLEMENTING, not ${currentState}.`, { actual: currentState, expected: ["ASSIGNED", "IMPLEMENTING"] });
  const runDirectory = runDirectoryFromStatePath(statePath);
  let operation;
  if (options.operation) operation = { ...(await readYamlFile(options.operation)), path: resolve(options.operation) };
  else {
    const candidates = operationsForJob(await readOperationFiles(runDirectory), jobId, unitId);
    if (candidates.length > 1) fail("AMBIGUOUS_AGENT_JOB", `Agent job ${jobId} is bound to multiple operations; supply --operation.`, { job_id: jobId, work_unit_id: unitId, candidates: candidates.map((entry) => ({ path: entry.path, operation_id: entry.value?.operation_id, operation_instance_id: entry.value?.operation_instance_id ?? entry.value?.operation_id })) });
    operation = candidates[0];
  }
  if (!operation?.value) fail("OPERATION_NOT_FOUND", `No durable operation is associated with agent job ${jobId}.`, { job_id: jobId, work_unit_id: unitId });
  const operationValue = operation.value;
  if (operationValue.status !== "EXECUTING") fail("AGENT_NOT_STARTED", `Agent operation is ${operationValue.status}, not EXECUTING.`, { status: operationValue.status, expected: "EXECUTING", next_action: "WAIT_FOR_AGENT_SYSTEM_START" });
  if (operationValue.job_id !== jobId) fail("AGENT_JOB_MISMATCH", "The operation is not bound to the acknowledged job.", { actual: operationValue.job_id ?? null, expected: jobId });
  if (operationValue.work_unit_id !== unitId) fail("WORK_UNIT_ID_MISMATCH", "The operation belongs to another work unit.", { actual: operationValue.work_unit_id ?? null, expected: unitId });
  const handoffPath = operationValue.result?.handoff_path ?? operationValue.input?.handoff_path;
  if (!handoffPath) fail("HANDOFF_REQUIRED", "Acknowledgement operation has no handoff path.");
  const validation = await validateHandoffFile(handoffPath, { throwOnInvalid: false });
  if (!validation.valid) fail("HANDOFF_INVALID", "Cannot acknowledge an invalid worker handoff.", { errors: validation.errors });
  if (currentState === "IMPLEMENTING") return { run_id: runId, work_unit_id: unitId, job_id: jobId, operation_path: operation.path, operation_id: operationValue.operation_id, operation_instance_id: operationValue.operation_instance_id ?? operationValue.operation_id, state: currentState, transition_id: state.last_transition_id ?? null, idempotent: true, next_action: "WAIT_FOR_WORKER_REPORT" };
  const transition = await commitUnitTransition({ statePath, workUnitId: unitId, from: "ASSIGNED", to: "IMPLEMENTING", reason: `Worker job ${jobId} acknowledged the validated handoff.`, operationId: operationValue.operation_id, operationInstanceId: operationValue.operation_instance_id ?? operationValue.operation_id });
  return { run_id: runId, work_unit_id: unitId, job_id: jobId, operation_path: operation.path, operation_id: operationValue.operation_id, operation_instance_id: operationValue.operation_instance_id ?? operationValue.operation_id, state: "IMPLEMENTING", transition_id: transition.transition_id, handoff_path: handoffPath, handoff_digest: validation.digest, next_action: "WAIT_FOR_WORKER_REPORT" };
}

export async function reconcileAgent(options) {
  const jobId = options.jobId ?? options.position;
  if (!jobId) fail("MISSING_ARGUMENT", "reconcile-agent requires a job ID.");
  if (!options.state && options.run) return reconcileRunAgent(options);
  if (!options.state) fail("MISSING_ARGUMENT", "--state or --run is required for agent reconciliation.");
  const statePath = resolve(options.state);
  const stateDocument = await readYamlFile(statePath);
  const state = stateDocument.value;
  const runId = normalizeRunId(state);
  const unitId = normalizeUnitId(state);
  if (!runId || !unitId) fail("INVALID_STATE", "State must contain run_id and work_unit_id for reconciliation.");
  const runDirectory = runDirectoryFromStatePath(statePath);
  const operations = await readOperationFiles(runDirectory);
  let operation;
  if (options.operation) {
    operation = {
      ...(await readYamlFile(options.operation)),
      path: resolve(options.operation),
    };
  } else {
    const candidates = operationsForJob(operations, jobId);
    if (candidates.length > 1) {
      fail("AMBIGUOUS_AGENT_JOB", `Agent job ${jobId} is bound to multiple operations for ${unitId}; supply --operation.`, {
        job_id: jobId,
        work_unit_id: unitId,
        candidates: candidates.map((entry) => ({ path: entry.path, operation_id: entry.value?.operation_id, operation_instance_id: entry.value?.operation_instance_id ?? entry.value?.operation_id, attempt_id: entry.value?.attempt_id })),
      });
    }
    operation = candidates[0];
  }
  if (!operation || !operation.value) fail("OPERATION_NOT_FOUND", `No durable operation is associated with agent job ${jobId}.`, { job_id: jobId, work_unit_id: unitId, operation_paths: operations.map((entry) => entry.path) });
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
      operation_instance_id: operationValue.operation_instance_id ?? operationValue.operation_id,
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
      operationInstanceId: operationValue.operation_instance_id ?? operationValue.operation_id,
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
    operation_instance_id: operationValue.operation_instance_id ?? operationValue.operation_id,
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

async function blockFailedResume(statePath, workUnitId, resumeState, reason, operationId = null, operationInstanceId = null) {
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
      metadata: { operation_id: operationId, operation_instance_id: operationInstanceId, error_code: reason.code ?? "UNEXPECTED_ERROR" },
    };
    if (current !== "BLOCKED" && LEGAL_UNIT_TRANSITIONS[current]?.includes("BLOCKED")) {
      await commitUnitTransition({ statePath, workUnitId, from: current, to: "BLOCKED", reason: blocker.reason, operationId, operationInstanceId, extraSets: [{ pointer: "/blocker", value: blocker }], allowUnresolvedOperation: true });
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
      const match = String(operation.value.attempt_id ?? "").match(/:attempt-([0-9]{3,6})$/);
      if (match) values.push(Number(match[1]));
    }
  }
  for (const report of await findReports(runDirectory, unitId)) {
    const match = String(report.value?.attempt_id ?? "").match(new RegExp(`:${roleKey}:attempt-([0-9]{3,6})$`));
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
  const oldOperationInstanceId = blocker.metadata?.operation_instance_id ?? blocker.operation_instance_id ?? null;
  const stateUpdate = await updateYamlFile(statePath, stateDocument.digest, [
    { pointer: "/attempt_number", value: Number(attemptNumber) },
    { pointer: "/attempt_id", value: attemptId },
    { pointer: "/last_role", value: roleKey },
    { pointer: "/worktree/path", value: worktreePath },
    { pointer: "/worktree/repository_id", value: latestSnapshot.repository_id },
    { pointer: "/worktree/branch", value: latestSnapshot.branch },
    { pointer: "/worktree/current_head", value: latestSnapshot.head },
    { pointer: "/resume_from_operation_id", value: oldOperationId },
    { pointer: "/resume_from_operation_instance_id", value: oldOperationInstanceId },
  ]);
  const transition = await commitUnitTransition({
    statePath,
    workUnitId: unitId,
    from: "BLOCKED",
    to: resumeState,
    reason: `Resume ${roleKey} attempt ${attemptNumber} after durable agent reconciliation.`,
    operationId: oldOperationId,
    operationInstanceId: oldOperationInstanceId,
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
    { pointer: "/last_operation_instance_id", value: manifestResult.manifest.operation.instance_id },
    { pointer: "/active_handoff", value: {
      role: roleKey,
      attempt_id: manifestResult.manifest.attempt_id,
      operation_id: manifestResult.manifest.operation.id,
      operation_instance_id: manifestResult.manifest.operation.instance_id,
      operation_path: operation.path,
      manifest_path: manifestResult.manifestPath,
      handoff_path: handoff.handoff_path,
      handoff_digest: validation.digest,
      report_path: manifestResult.manifest.artifact.report_path,
      target_branch: manifestResult.manifest.target.branch,
      target_head: manifestResult.manifest.target.head,
      state: resumeState,
    } },
    { pointer: "/blocker", value: null },
  ]);
  if (oldOperationId) {
    const oldOperationPath = await resolveOperationPath(runDirectory, oldOperationId, oldOperationInstanceId);
    if (await pathExists(oldOperationPath)) {
      const oldOperationDocument = await readYamlFile(oldOperationPath);
      if (["UNKNOWN", "RECONCILING"].includes(oldOperationDocument.value.status)) {
        await updateOperation(oldOperationPath, oldOperationDocument.digest, [
          { pointer: "/status", value: "SUPERSEDED" },
          { pointer: "/reconciliation/final_status", value: "EFFECT_RETAINED_FOR_SUCCESSOR" },
          { pointer: "/reconciliation/successor_operation_id", value: manifestResult.manifest.operation.id },
          { pointer: "/reconciliation/successor_operation_instance_id", value: manifestResult.manifest.operation.instance_id },
        ]);
      }
    }
  }
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
    operation_id: manifestResult.manifest.operation.id,
    operation_instance_id: manifestResult.manifest.operation.instance_id,
    handoff_path: handoff.handoff_path,
    manifest_path: manifestResult.manifestPath,
    handoff_digest: validation.digest,
      state_changed: stateUpdate.changed || recorded.changed,
      operation_changed: operationUpdate.changed,
      next_action: "SPAWN_AGENT_WITH_VALIDATED_HANDOFF",
    };
  } catch (error) {
    await blockFailedResume(statePath, unitId, resumeState, error, oldOperationId, oldOperationInstanceId);
    throw error;
  }
}

function legalNextRunAction(state) {
  if (state === "EXECUTING") return "ADVANCE_TO_RUN_VALIDATING_WHEN_UNITS_DONE";
  if (state === "RUN_VALIDATING") return "PREPARE_RUN_QA";
  if (state === "QA") return "COMPLETE_RUN_QA_REPORT";
  if (state === "REMEDIATING") return "CREATE_OR_RESUME_REMEDIATION";
  if (state === "COMPLETING") return "COMMIT_RUN_COMPLETION_THEN_VERIFY_FINAL";
  if (state === "BLOCKED") return "RESOLVE_RUN_BLOCKER";
  if (state === "PAUSED") return "RESUME_OR_CANCEL_RUN";
  if (state === "RUN_COMPLETED" || state === "RUN_CANCELLED" || state === "RUN_ABORTED") return "RETAIN_OR_EXPLICITLY_CLEANUP";
  return "INSPECT_RUN_STATE";
}

function legalNextAction(state, dependenciesReady, blocker) {
  if (state === "DONE") return "RUN_QA_OR_VERIFY_CRITERIA";
  if (state === "BLOCKED") return blocker?.required_to_resume?.[0] ?? "RESOLVE_BLOCKER";
  if (state === "READY") return dependenciesReady ? "PREPARE_WORKER_DISPATCH" : "WAIT_FOR_DEPENDENCIES";
  if (state === "ASSIGNED") return "WAIT_FOR_AGENT_ACKNOWLEDGEMENT";
  if (state === "IMPLEMENTING") return "WAIT_FOR_WORKER_REPORT";
  if (state === "AWAITING_REVIEW") return "PREPARE_REVIEWER_DISPATCH";
  if (state === "REVIEWING") return "WAIT_FOR_REVIEW_VERDICT";
  if (state === "FIXING") return "PREPARE_CORRECTION";
  if (state === "INTEGRATING") return "INTEGRATE_EXACT_APPROVED_REVISION";
  if (state === "ESCALATED") return "USER_OR_AUTHORITY_DECISION";
  return "INSPECT_STATE";
}

function artifactAttemptNumber(entry) {
  const match = String(entry.value?.attempt_id ?? entry.value?.operation_instance_id ?? "").match(/:attempt-([0-9]{3,6})$/);
  return match ? Number(match[1]) : -1;
}

function latestArtifact(entries) {
  return [...entries].sort((left, right) => artifactAttemptNumber(left) - artifactAttemptNumber(right) || String(left.value?.completed_at ?? left.value?.created_at ?? left.path).localeCompare(String(right.value?.completed_at ?? right.value?.created_at ?? right.path))).at(-1) ?? null;
}

async function latestReportForUnit(runDirectory, unitId, role = undefined) {
  const reports = await findReports(runDirectory, unitId);
  const matching = role ? reports.filter((entry) => entry.value?.role === ROLE_NAMES[role] || entry.value?.role === role) : reports;
  return latestArtifact(matching);
}

function contextHealth(run, artifacts) {
  if ((run.control_plane_version ?? 1) < 2) return "MIGRATION_REQUIRED";
  if (artifacts.units.some((unit) => unit.error) || artifacts.operations.some((operation) => operation.error)) return "CORRUPT";
  if (environmentProfileRequired(run) && (!run.environment?.profile_path || !run.environment?.profile_digest)) return "ENVIRONMENT_PROFILE_MISSING";
  const proposal = proposalProjection(run);
  if (proposal.required && (!proposal.path || !proposal.digest)) return "PROPOSAL_CONTEXT_MISSING";
  if (run.blocker?.type === "HANDOFF_CONTEXT" || run.blocker?.code === "HANDOFF_REJECTED_BEFORE_PRODUCT_REVIEW") return "HANDOFF_INVALID";
  return "CURRENT";
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
    const latestOperation = unit.value.last_operation_instance_id
      ? unitOperations.find((entry) => (entry.value?.operation_instance_id ?? entry.value?.operation_id) === unit.value.last_operation_instance_id) ?? latestArtifact(unitOperations)
      : unit.value.last_operation_id
        ? unitOperations.find((entry) => entry.value?.operation_id === unit.value.last_operation_id) ?? latestArtifact(unitOperations)
        : latestArtifact(unitOperations);
    const latestTransition = latestArtifact(artifacts.transitions.filter((entry) => entry.value?.entity === id));
    const reviewer = unit.value.accepted_review?.report_path && await pathExists(unit.value.accepted_review.report_path)
      ? { ...(await readYamlFile(unit.value.accepted_review.report_path)), path: resolve(unit.value.accepted_review.report_path) }
      : await latestReportForUnit(runDirectory, id, "reviewer");
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
      active_handoff: unit.value.active_handoff ?? null,
      accepted_review: unit.value.accepted_review ?? null,
      accepted_revision: unit.value.accepted_review?.revision ?? unit.value.accepted_review?.final_revision ?? null,
      latest_operation: latestOperation ? { path: latestOperation.path, operation_id: latestOperation.value.operation_id, operation_instance_id: latestOperation.value.operation_instance_id ?? latestOperation.value.operation_id, status: latestOperation.value.status, attempt_id: latestOperation.value.attempt_id } : null,
      latest_transition: latestTransition ? { path: latestTransition.path, transition_id: latestTransition.value.transition_id, status: latestTransition.value.status, from: latestTransition.value.from, to: latestTransition.value.to } : null,
      report_verdict: reviewer?.value?.verdict ?? reviewer?.value?.review?.verdict ?? null,
      open_findings: (reviewer?.value?.findings ?? []).filter((finding) => !["RESOLVED", "CLOSED"].includes(finding.status)).map((finding) => ({ id: finding.id ?? finding.finding_id ?? null, severity: finding.severity ?? null, status: finding.status ?? null })),
      environment: run.environment ?? null,
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
    purpose: runPurposeValue(run),
    completion_marker: completionMarkerForPurpose(runPurposeValue(run)),
    control_plane_version: run.control_plane_version ?? 1,
    context_health: contextHealth(run, artifacts),
    run_state: actualRunState(run),
    run_legal_next_states: LEGAL_RUN_TRANSITIONS[actualRunState(run)] ?? [],
    run_next_legal_action: legalNextRunAction(actualRunState(run)),
    next_command: legalNextRunAction(actualRunState(run)),
    active_operation_instance_id: run.active_qa?.operation_instance_id ?? workUnits.find((unit) => unit.active_handoff?.operation_instance_id)?.active_handoff?.operation_instance_id ?? null,
    accepted_revision: options.ticket && workUnits[0] ? workUnits[0].accepted_revision : null,
    target_checkpoint: run.project?.target_head ?? run.target?.head ?? null,
    target,
    work_unit_counts: counts,
    work_units: workUnits,
    required_core_status: run.required_core_status ?? null,
    environment: run.environment ?? null,
    reference_snapshots: run.reference_snapshots ?? [],
    ownership_analysis: run.ownership_analysis ?? null,
    run_blocker: run.blocker ?? null,
    blocker_type: run.blocker?.type ?? null,
    blocker_code: run.blocker?.code ?? null,
    blockers: [
      ...(run.blocker ? [{ scope: "RUN", blocker: run.blocker }] : []),
      ...workUnits.filter((unit) => unit.blocker).map((unit) => ({ work_unit_id: unit.work_unit_id, blocker: unit.blocker })),
    ],
    latest_operation: latestArtifact(artifacts.operations) ? { operation_id: latestArtifact(artifacts.operations).value?.operation_id ?? null, operation_instance_id: latestArtifact(artifacts.operations).value?.operation_instance_id ?? latestArtifact(artifacts.operations).value?.operation_id ?? null, status: latestArtifact(artifacts.operations).value?.status ?? null } : null,
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
      if (report.value.canonical?.revision && preflight.target?.head) {
        try {
          const resolvedQaRevision = await resolveGitRevision(run.project?.root ?? run.project_root, report.value.canonical.revision, "qa.canonical.revision");
          if (resolvedQaRevision !== preflight.target.head) issues.push(issue("qa.canonical.revision", "QA_REVISION_MISMATCH", resolvedQaRevision, preflight.target.head, "QA evidence was produced against another target revision."));
        } catch (error) { issues.push(issue("qa.canonical.revision", error.code ?? "REVISION_NOT_FOUND", report.value.canonical.revision, preflight.target.head, error.message)); }
      }
      if (final && report.value.verdict !== "PASSED") issues.push(issue("qa.verdict", "QA_NOT_PASSED", report.value.verdict ?? null, "PASSED", "Final run verification requires a passed QA report."));
    } catch (error) { issues.push(issue("qa.report_path", error.code ?? "QA_READ_FAILED", error.message, "readable QA report", "The QA report could not be verified.")); }
  } else if (final) issues.push(issue("qa.report_path", "QA_REPORT_REQUIRED", qaPath ?? null, "existing QA report", "Final run verification requires durable QA evidence."));
  for (const unit of artifacts.units) {
    if (!unit.value || actualStateFromDocument(unit.value) !== "DONE") continue;
    const unitId = normalizeUnitId(unit.value);
    let reviewer = null;
    if (unit.value.accepted_review?.report_path && await pathExists(unit.value.accepted_review.report_path)) {
      const document = await readYamlFile(unit.value.accepted_review.report_path);
      reviewer = { path: document.file, digest: document.digest, value: document.value };
      if (unit.value.accepted_review.report_digest && unit.value.accepted_review.report_digest !== document.digest) issues.push(issue(`${unit.path}:accepted_review.report_digest`, "DIGEST_MISMATCH", document.digest, unit.value.accepted_review.report_digest, "The accepted reviewer report changed after completion."));
    } else reviewer = await latestReportForUnit(dirname(runPath), unitId, "reviewer");
    if (!reviewer || reviewer.error) {
      if (final) issues.push(issue(`${unit.path}:review`, "REVIEW_REPORT_REQUIRED", reviewer?.path ?? null, "durable APPROVED reviewer report", "A DONE work unit must retain its exact approval evidence."));
      continue;
    }
    const verdict = reviewer.value.verdict ?? reviewer.value.review?.verdict;
    if (verdict !== "APPROVED") issues.push(issue(`${unit.path}:review.verdict`, "REVIEW_NOT_APPROVED", verdict ?? null, "APPROVED", "A DONE work unit cannot rely on a non-approval verdict."));
    const approvedRevision = reviewer.value.reviewer?.final_revision ?? reviewer.value.final_revision ?? reviewer.value.reviewer?.reviewed_revision ?? reviewer.value.reviewed_revision;
    const integratedRevision = unit.value.integrated_revision ?? unit.value.integration?.source_revision ?? unit.value.approved_revision;
    if (!approvedRevision) issues.push(issue(`${unit.path}:review.revision`, "REVIEW_REVISION_REQUIRED", null, "exact approved revision", "Reviewer evidence must identify the exact approved revision."));
    if (approvedRevision && integratedRevision) {
      try {
        const repositoryRoot = run.project?.root ?? run.project_root;
        const resolvedApprovedRevision = await resolveGitRevision(repositoryRoot, approvedRevision, "approved_revision");
        const resolvedIntegratedRevision = await resolveGitRevision(repositoryRoot, integratedRevision, "integrated_revision");
        if (resolvedApprovedRevision !== resolvedIntegratedRevision) issues.push(issue(`${unit.path}:review.revision`, "REVIEW_REVISION_MISMATCH", approvedRevision, integratedRevision, "Reviewer approval does not match the integrated revision."));
      } catch (error) {
        issues.push(issue(`${unit.path}:review.revision`, error.code ?? "REVISION_NOT_FOUND", error.message, "resolvable approved and integrated revisions", "The exact approval/integration revision relationship could not be verified."));
      }
    }
  }
  if (final && !allDone) issues.push(issue("work_units", "WORK_UNITS_INCOMPLETE", artifacts.units.map((unit) => ({ id: normalizeUnitId(unit.value ?? {}), state: actualStateFromDocument(unit.value ?? {}) })), "all work units DONE", "Final run verification requires every in-scope work unit to be DONE."));
  if (final && actualRunState(run) !== "RUN_COMPLETED") issues.push(issue("run.state", "RUN_NOT_COMPLETED", actualRunState(run) ?? null, "RUN_COMPLETED", "Final verification does not itself terminalize a run."));
  if (final) {
    if (!run.final_summary_path || !(await pathExists(run.final_summary_path))) issues.push(issue("final_summary_path", "FINAL_SUMMARY_REQUIRED", run.final_summary_path ?? null, "existing final summary", "Final verification requires the durable final summary."));
    else {
      try {
        const finalSummary = await readYamlFile(run.final_summary_path);
        if (run.final_summary_digest && finalSummary.digest !== run.final_summary_digest) issues.push(issue("final_summary_digest", "DIGEST_MISMATCH", finalSummary.digest, run.final_summary_digest, "The final summary changed after terminalization."));
        if (finalSummary.value.run_id !== artifacts.runDocument.run_id) issues.push(issue("final_summary.run_id", "RUN_ID_MISMATCH", finalSummary.value.run_id ?? null, artifacts.runDocument.run_id, "The final summary belongs to another run."));
        if (finalSummary.value.purpose !== undefined && finalSummary.value.purpose !== runPurposeValue(run)) issues.push(issue("final_summary.purpose", "PURPOSE_MISMATCH", finalSummary.value.purpose, runPurposeValue(run), "The final summary purpose differs from the admitted run."));
        if (finalSummary.value.completion_marker !== undefined && finalSummary.value.completion_marker !== completionMarkerForPurpose(runPurposeValue(run))) issues.push(issue("final_summary.completion_marker", "COMPLETION_MARKER_MISMATCH", finalSummary.value.completion_marker, completionMarkerForPurpose(runPurposeValue(run)), "The final summary completion marker differs from the admitted purpose."));
      } catch (error) { issues.push(issue("final_summary_path", error.code ?? "FINAL_SUMMARY_READ_FAILED", error.message, "readable final summary", "The final summary could not be verified.")); }
    }
  }
  return { ...preflight, valid: issues.length === 0, final, purpose: runPurposeValue(run), completion_marker: completionMarkerForPurpose(runPurposeValue(run)), all_work_units_done: allDone, qa, issues };
}
