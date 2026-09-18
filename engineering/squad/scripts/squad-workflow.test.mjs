import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import {
  buildExecutionManifest,
  bindAgent,
  commitUnitTransition,
  generateHandoffFromManifest,
  gitSnapshot,
  prepareDispatch,
  preflightRun,
  reconcileAgent,
  resumeTicket,
  statusRun,
  validateHandoffData,
  validateHandoffFile,
  verifyRun,
  writeExecutionManifest,
} from "./_squad-workflow.mjs";
import { readYamlFile, updateYamlFile } from "./_yaml-io.mjs";

async function runGit(cwd, args) {
  const child = Bun.spawn(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" });
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(child.stdout).text(),
    new Response(child.stderr).text(),
    child.exited,
  ]);
  assert.equal(exitCode, 0, `git ${args.join(" ")} failed: ${stderr}`);
  return stdout.trim();
}

async function runWorkflowCli(args) {
  const child = Bun.spawn(["bun", resolve(import.meta.dir, "squad.mjs"), ...args], { stdout: "pipe", stderr: "pipe" });
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(child.stdout).text(),
    new Response(child.stderr).text(),
    child.exited,
  ]);
  return { stdout: stdout.trim(), stderr: stderr.trim(), exitCode };
}

async function setupRun() {
  const workspace = await mkdtemp(join(tmpdir(), "squad-workflow-"));
  const project = join(workspace, "project");
  const sourceDirectory = join(workspace, "_xzy-ai", "sprints", "demo");
  const ticketDirectory = join(sourceDirectory, "tickets");
  const runDirectory = join(sourceDirectory, "orchestration", "RUN-001");
  const stateDirectory = join(runDirectory, "work-units", "T001");
  const worktree = join(workspace, "worktrees", "squad", "demo", "RUN-001", "T001");
  await mkdir(project, { recursive: true });
  await mkdir(ticketDirectory, { recursive: true });
  await mkdir(stateDirectory, { recursive: true });
  await runGit(project, ["init", "-b", "main"]);
  await runGit(project, ["config", "user.email", "test@example.com"]);
  await runGit(project, ["config", "user.name", "Squad Test"]);
  await writeFile(join(project, "app.txt"), "initial\n");
  await runGit(project, ["add", "."]);
  await runGit(project, ["commit", "-m", "initial"]);
  const initialHead = await runGit(project, ["rev-parse", "HEAD"]);
  const ticketPath = join(ticketDirectory, "T001.md");
  const ticketsPath = join(sourceDirectory, "tickets.md");
  await writeFile(ticketPath, "# T001\n\nImplement the behavior.\n");
  await writeFile(ticketsPath, "# Tickets\n\n- [T001](tickets/T001.md)\n");
  await runGit(project, ["worktree", "add", "-b", "squad/RUN-001/T001", worktree, initialHead]);
  const { digestFile } = await import("./_squad-workflow.mjs");
  const ticketDigest = await digestFile(ticketPath);
  const ticketsDigest = await digestFile(ticketsPath);
  const statePath = join(stateDirectory, "state.yaml");
  const runPath = join(runDirectory, "run.yaml");
  const repositorySnapshot = await gitSnapshot(project);
  const state = {
    schema_version: 1,
    run_id: "RUN-001",
    work_unit_id: "T001",
    work_unit_type: "TICKET",
    state: "READY",
    ticket_path: ticketPath,
    ticket_digest: ticketDigest,
    dependencies: [],
    attempt_number: 1,
    attempt_id: "RUN-001:T001:worker:attempt-001",
    worktree: {
      path: worktree,
      repository_id: repositorySnapshot.repository_id,
      branch: "squad/RUN-001/T001",
      baseline: initialHead,
      current_head: initialHead,
    },
  };
  const run = {
    schema_version: 1,
    run_id: "RUN-001",
    state: "EXECUTING",
    source: { tickets_index_path: ticketsPath, digest: ticketsDigest },
    project: { root: project, target_branch: "main", target_head: initialHead },
  };
  const { createYamlFile } = await import("./_yaml-io.mjs");
  await createYamlFile(runPath, run);
  await createYamlFile(statePath, state);
  return { workspace, project, ticketsPath, ticketPath, runDirectory, runPath, statePath, worktree, initialHead };
}

async function teardownRun(fixture) {
  await runGit(fixture.project, ["worktree", "remove", "--force", fixture.worktree]).catch(() => {});
  await rm(fixture.workspace, { recursive: true, force: true });
}

test("manifest and typed handoff use one Git-verified identity", async () => {
  const fixture = await setupRun();
  try {
    const built = await buildExecutionManifest({ run: fixture.runPath, state: fixture.statePath, ticket: fixture.ticketPath, role: "worker", attempt: 1 });
    const manifest = await writeExecutionManifest(built.manifest, built.manifestPath);
    const handoff = await generateHandoffFromManifest(manifest.manifest_path);
    const validation = await validateHandoffFile(handoff.handoff_path, { throwOnInvalid: false, requireOperation: false });
    assert.equal(validation.valid, true, JSON.stringify(validation.errors));
    assert.equal(validation.checks.find((entry) => entry.name === "target.head")?.result, "PASS");
    assert.equal(handoff.handoff.operation_id, "RUN-001:T001:DISPATCH_WORKER");
    assert.equal(handoff.handoff.attempt_id, "RUN-001:T001:worker:attempt-001");

    const invalid = structuredClone(handoff.handoff);
    invalid.worktree.baseline = "deadbee";
    const rejected = await validateHandoffData(invalid, "<bad-handoff>", { throwOnInvalid: false });
    assert.equal(rejected.valid, false);
    assert.ok(rejected.errors.some((entry) => entry.code === "REVISION_NOT_FOUND" || entry.code === "GIT_VALIDATION_FAILED"));
  } finally {
    await teardownRun(fixture);
  }
});

test("dispatch preparation rejects target drift before an agent can be spawned", async () => {
  const fixture = await setupRun();
  try {
    const result = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" });
    assert.equal(result.operation_status, "PREPARED");
    assert.equal(result.state, "ASSIGNED");
    const handoff = await validateHandoffFile(result.handoff_path, { throwOnInvalid: false });
    assert.equal(handoff.valid, true, JSON.stringify(handoff.errors));
    const state = await readYamlFile(fixture.statePath);
    assert.equal(state.value.state, "ASSIGNED");
    const retry = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" });
    assert.equal(retry.operation_status, "PREPARED");
    assert.equal(retry.handoff_path, result.handoff_path);

    const run = await readYamlFile(fixture.runPath);
    const changed = structuredClone(run.value);
    changed.project.target_head = "deadbee";
    await updateYamlFile(fixture.runPath, run.digest, [{ pointer: "/project/target_head", value: "deadbee" }]);
    await assert.rejects(
      () => prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker", attempt: 2 }),
      (error) => error.code === "PREFLIGHT_FAILED" || error.code === "REVISION_NOT_FOUND" || error.code === "TARGET_HEAD_MISMATCH",
    );
    assert.deepEqual(changed.project.target_head, "deadbee");
  } finally {
    await teardownRun(fixture);
  }
});

test("transition engine rejects illegal transitions and commits legal transitions durably", async () => {
  const fixture = await setupRun();
  try {
    await assert.rejects(
      () => commitUnitTransition({ statePath: fixture.statePath, workUnitId: "T001", from: "READY", to: "DONE", reason: "invalid" }),
      (error) => error.code === "ILLEGAL_TRANSITION",
    );
    const result = await commitUnitTransition({ statePath: fixture.statePath, workUnitId: "T001", from: "READY", to: "ASSIGNED", reason: "dispatch gate passed" });
    assert.equal(result.status, "COMMITTED");
    const state = await readYamlFile(fixture.statePath);
    const transition = await readYamlFile(result.transition_path);
    assert.equal(state.value.state, "ASSIGNED");
    assert.equal(transition.value.status, "COMMITTED");
    assert.equal(transition.value.to, "ASSIGNED");
  } finally {
    await teardownRun(fixture);
  }
});

test("agent interruption becomes a durable blocker and resume preserves the worktree", async () => {
  const fixture = await setupRun();
  try {
    const dispatched = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" });
    const bound = await bindAgent({ jobId: "JOB-001", operation: dispatched.operation_path });
    assert.equal(bound.operation_status, "EXECUTING");
    const boundHandoff = await validateHandoffFile(dispatched.handoff_path, { throwOnInvalid: false });
    assert.equal(boundHandoff.valid, true, JSON.stringify(boundHandoff.errors));
    const reconciled = await reconcileAgent({ jobId: "JOB-001", state: fixture.statePath });
    assert.equal(reconciled.state, "BLOCKED");
    assert.equal(reconciled.operation_status, "RECONCILING");
    const blocked = await readYamlFile(fixture.statePath);
    assert.equal(blocked.value.blocker.type, "AGENT_UNAVAILABLE");
    assert.equal(blocked.value.worktree.path, fixture.worktree);

    const resumed = await resumeTicket({ unitId: "T001", state: fixture.statePath, role: "worker" });
    assert.equal(resumed.strategy, "resume");
    assert.equal(resumed.state, "ASSIGNED");
    assert.equal(resumed.worktree.dirty, false);
    assert.equal(resumed.attempt_id, "RUN-001:T001:worker:attempt-002");
    const resumedHandoff = await validateHandoffFile(resumed.handoff_path, { throwOnInvalid: false });
    assert.equal(resumedHandoff.valid, true, JSON.stringify(resumedHandoff.errors));
    const state = await readYamlFile(fixture.statePath);
    assert.equal(state.value.blocker, null);
    assert.equal(state.value.attempt_id, resumed.attempt_id);
  } finally {
    await teardownRun(fixture);
  }
});

test("the host CLI exposes guarded workflow commands and structured errors", async () => {
  const fixture = await setupRun();
  try {
    const prepared = await runWorkflowCli(["prepare", "--run", fixture.runPath, "--state", fixture.statePath, "--role", "worker"]);
    assert.equal(prepared.exitCode, 0, prepared.stderr);
    const preparedResult = JSON.parse(prepared.stdout);
    const handoff = await runWorkflowCli(["validate-handoff", preparedResult.handoff_path]);
    assert.equal(handoff.exitCode, 0, handoff.stderr);
    assert.equal(JSON.parse(handoff.stdout).valid, true);
    const status = await runWorkflowCli(["status", "RUN-001", "--run", fixture.runPath, "--ticket", "T001", "--explain"]);
    assert.equal(status.exitCode, 0, status.stderr);
    assert.equal(JSON.parse(status.stdout).work_units[0].state, "ASSIGNED");
    const illegal = await runWorkflowCli(["transition", "T001", "--state", fixture.statePath, "--from", "ASSIGNED", "--to", "DONE", "--reason", "skip"]) ;
    assert.equal(illegal.exitCode, 1);
    const error = JSON.parse(illegal.stderr);
    assert.equal(error.error, "ILLEGAL_TRANSITION");
    assert.equal(error.details.from, "ASSIGNED");
    assert.ok(Array.isArray(error.details.legal_to));
  } finally {
    await teardownRun(fixture);
  }
});

test("preflight and dashboard expose dependency, revision, and next-action state", async () => {
  const fixture = await setupRun();
  try {
    const preflight = await preflightRun(fixture.runPath);
    assert.equal(preflight.valid, true, JSON.stringify(preflight.issues));
    assert.deepEqual(preflight.ready, ["T001"]);
    const dashboard = await statusRun(fixture.runPath, { explain: true });
    assert.equal(dashboard.work_units[0].next_legal_action, "PREPARE_WORKER_DISPATCH");
    assert.deepEqual(dashboard.work_units[0].explanation.legal_next_states, ["ASSIGNED", "BLOCKED"]);
    const verification = await verifyRun(fixture.runPath);
    assert.equal(verification.valid, true, JSON.stringify(verification.issues));
  } finally {
    await teardownRun(fixture);
  }
});
