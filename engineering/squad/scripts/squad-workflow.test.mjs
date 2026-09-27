import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import {
  buildExecutionManifest,
  bindAgent,
  acknowledgeAgent,
  rejectHandoff,
  commitUnitTransition,
  completeWorker,
  completeReview,
  completeAnalysis,
  prepareRunQa,
  completeRunQa,
  completeRun,
  resumeRun,
  reconcileRunTransition,
  commitRunTransition,
  integrateTicket,
  completeTicket,
  captureEnvironmentProfile,
  recordReferenceSnapshot,
  analyzeOwnership,
  migrateRun,
  generateHandoffFromManifest,
  gitSnapshot,
  digestFile,
  prepareDispatch,
  preflightRun,
  reconcileAgent,
  resumeTicket,
  statusRun,
  validateHandoffData,
  validateQaHandoffData,
  validateHandoffFile,
  verifyRun,
  writeExecutionManifest,
  updateAcceptanceStatusProjection,
} from "./_squad-workflow.mjs";
import { createYamlFile, readYamlFile, updateYamlFile } from "./_yaml-io.mjs";

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
    assert.equal(handoff.handoff.source.proposal_required, false);
    assert.equal(handoff.handoff.environment.admission, "ADVISORY_LEGACY");

    const invalid = structuredClone(handoff.handoff);
    invalid.worktree.baseline = "deadbee";
    const rejected = await validateHandoffData(invalid, "<bad-handoff>", { throwOnInvalid: false });
    assert.equal(rejected.valid, false);
    assert.ok(rejected.errors.some((entry) => entry.code === "REVISION_NOT_FOUND" || entry.code === "GIT_VALIDATION_FAILED"));
  } finally {
    await teardownRun(fixture);
  }
});

test("prototype purpose propagates through the manifest and handoff without a production mode", async () => {
  const fixture = await setupRun();
  try {
    const run = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, run.digest, [{ pointer: "/purpose", value: "prototype" }]);
    const built = await buildExecutionManifest({ run: fixture.runPath, state: fixture.statePath, ticket: fixture.ticketPath, role: "worker", attempt: 1 });
    assert.equal(built.manifest.decisions.purpose, "prototype");
    assert.equal(built.manifest.decisions.completion_marker, "P");
    assert.equal(built.manifest.decisions.mode, null);
    const manifest = await writeExecutionManifest(built.manifest, built.manifestPath);
    const handoff = await generateHandoffFromManifest(manifest.manifest_path);
    assert.equal(handoff.handoff.decisions.purpose, "prototype");
    assert.equal(handoff.handoff.decisions.completion_marker, "P");
    assert.equal(handoff.handoff.decisions.mode, null);
    const validation = await validateHandoffFile(handoff.handoff_path, { throwOnInvalid: false, requireOperation: false });
    assert.equal(validation.valid, true, JSON.stringify(validation.errors));
  } finally {
    await teardownRun(fixture);
  }
});

test("purpose admission requires only production implementation modes", async () => {
  const fixture = await setupRun();
  try {
    const run = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, run.digest, [{ pointer: "/purpose", value: "production" }]);
    await assert.rejects(() => buildExecutionManifest({ run: fixture.runPath, state: fixture.statePath, ticket: fixture.ticketPath, role: "worker", attempt: 1 }), (error) => error.code === "PREFLIGHT_FAILED" && error.details.issues.some((entry) => entry.code === "IMPLEMENTATION_MODE_REQUIRED"));
    const productionRun = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, productionRun.digest, [{ pointer: "/worker_mode", value: "default" }]);
    const valid = await buildExecutionManifest({ run: fixture.runPath, state: fixture.statePath, ticket: fixture.ticketPath, role: "worker", attempt: 1 });
    assert.equal(valid.manifest.decisions.mode, "default");
    const stateWithOverride = await readYamlFile(fixture.statePath);
    await updateYamlFile(fixture.statePath, stateWithOverride.digest, [{ pointer: "/worker_mode", value: "tdd" }]);
    const overridden = await buildExecutionManifest({ run: fixture.runPath, state: fixture.statePath, ticket: fixture.ticketPath, role: "worker", attempt: 1 });
    assert.equal(overridden.manifest.decisions.mode, "tdd");
    const overriddenManifest = await writeExecutionManifest(overridden.manifest, overridden.manifestPath);
    const overriddenHandoff = await generateHandoffFromManifest(overriddenManifest.manifest_path);
    const overriddenValidation = await validateHandoffFile(overriddenHandoff.handoff_path, { throwOnInvalid: false, requireOperation: false });
    assert.equal(overriddenValidation.valid, true, JSON.stringify(overriddenValidation.errors));
    const prototypeRun = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, prototypeRun.digest, [{ pointer: "/purpose", value: "prototype" }]);
    await assert.rejects(() => buildExecutionManifest({ run: fixture.runPath, state: fixture.statePath, ticket: fixture.ticketPath, role: "worker", attempt: 1 }), (error) => error.code === "PREFLIGHT_FAILED" && error.details.issues.some((entry) => entry.code === "PROTOTYPE_MODE_NOT_ALLOWED"));
  } finally {
    await teardownRun(fixture);
  }
});

test("prototype acceptance projection uses the prototype completion marker", async () => {
  const fixture = await setupRun();
  try {
    const run = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, run.digest, [{ pointer: "/purpose", value: "prototype" }]);
    const state = await readYamlFile(fixture.statePath);
    await updateYamlFile(fixture.statePath, state.digest, [{ pointer: "/state", value: "DONE" }, { pointer: "/completion", value: { status: "DONE", marker: "x" } }]);
    const projection = await updateAcceptanceStatusProjection(fixture.runPath);
    const value = (await readYamlFile(projection.path)).value;
    assert.equal(value.purpose, "prototype");
    assert.equal(value.completion_marker, "P");
    assert.equal(value.units[0].completion.purpose, "prototype");
    assert.equal(value.units[0].completion.marker, "P");
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

test("bind-agent fails closed when prepared operation or handoff artifacts are missing", async () => {
  const operationFixture = await setupRun();
  try {
    const prepared = await prepareDispatch({ run: operationFixture.runPath, state: operationFixture.statePath, role: "worker" });
    await rm(prepared.operation_path);
    await assert.rejects(() => bindAgent({ jobId: "JOB-MISSING-OPERATION", operation: prepared.operation_path }), (error) => error.code === "OPERATION_NOT_FOUND");
  } finally {
    await teardownRun(operationFixture);
  }
  const handoffFixture = await setupRun();
  try {
    const prepared = await prepareDispatch({ run: handoffFixture.runPath, state: handoffFixture.statePath, role: "worker" });
    await rm(prepared.manifest_path);
    await assert.rejects(() => bindAgent({ jobId: "JOB-MISSING-MANIFEST", operation: prepared.operation_path }), (error) => error.code === "HANDOFF_INVALID" && error.details.errors.some((entry) => entry.code === "PATH_NOT_FOUND"));
    await rm(prepared.handoff_path);
    await assert.rejects(() => bindAgent({ jobId: "JOB-MISSING-HANDOFF", operation: prepared.operation_path }), (error) => error.code === "HANDOFF_NOT_FOUND");
    const state = await readYamlFile(handoffFixture.statePath);
    assert.equal(state.value.state, "ASSIGNED");
    assert.equal(state.value.active_handoff.operation_path, prepared.operation_path);
  } finally {
    await teardownRun(handoffFixture);
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

test("run lifecycle transitions are typed, durable, and separate from work-unit transitions", async () => {
  const fixture = await setupRun();
  try {
    await assert.rejects(
      () => commitRunTransition({ runPath: fixture.runPath, from: "EXECUTING", to: "RUN_VALIDATING", reason: "All ticket work is ready for run validation." }),
      (error) => error.code === "WORK_UNITS_INCOMPLETE",
    );
    const stateDocument = await readYamlFile(fixture.statePath);
    await updateYamlFile(fixture.statePath, stateDocument.digest, [
      { pointer: "/state", value: "DONE" },
      { pointer: "/integration", value: { source_revision: fixture.initialHead, target_before: fixture.initialHead, target_after: fixture.initialHead } },
    ]);
    const interruptedTransitionPath = join(fixture.runDirectory, "transitions", "TR-RUN-001-RUN-0001.yaml");
    await createYamlFile(interruptedTransitionPath, { schema_version: 1, transition_id: "TR-RUN-001-RUN-0001", entity_type: "RUN", entity: "RUN-001", from: "EXECUTING", to: "RUN_VALIDATING", status: "COMMITTING", reason: "interrupted", source: { run_path: fixture.runPath } });
    const reconciled = await reconcileRunTransition({ runPath: fixture.runPath, transitionPath: interruptedTransitionPath });
    assert.equal(reconciled.status, "ABORTED");
    const committed = await commitRunTransition({ runPath: fixture.runPath, from: "EXECUTING", to: "RUN_VALIDATING", reason: "All ticket work is ready for run validation." });
    assert.equal(committed.status, "COMMITTED");
    const run = await readYamlFile(fixture.runPath);
    assert.equal(run.value.state, "RUN_VALIDATING");
    const transition = await readYamlFile(committed.transition_path);
    assert.equal(transition.value.entity_type, "RUN");
    assert.equal(transition.value.entity, "RUN-001");
    await assert.rejects(
      () => commitRunTransition({ runPath: fixture.runPath, from: "RUN_VALIDATING", to: "RUN_COMPLETED", reason: "skip" }),
      (error) => error.code === "ILLEGAL_RUN_TRANSITION",
    );
    await assert.rejects(
      () => commitRunTransition({ runPath: fixture.runPath, from: "RUN_VALIDATING", to: "QA", reason: "skip" }),
      (error) => error.code === "RUN_QA_PREPARATION_REQUIRED",
    );
    const preflight = await preflightRun(fixture.runPath);
    assert.equal(preflight.valid, true, JSON.stringify(preflight.issues));
    await commitRunTransition({ runPath: fixture.runPath, from: "RUN_VALIDATING", to: "PAUSED", reason: "User requested a pause." });
    const resumed = await resumeRun({ run: fixture.runPath });
    assert.equal(resumed.state, "EXECUTING");
    assert.equal((await readYamlFile(fixture.runPath)).value.state, "EXECUTING");
  } finally {
    await teardownRun(fixture);
  }
});

test("handoff rejection is distinct from product rejection and creates a durable blocker", async () => {
  const fixture = await setupRun();
  try {
    const prepared = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" });
    await assert.rejects(() => acknowledgeAgent({ jobId: "JOB-QUEUED", state: fixture.statePath, operation: prepared.operation_path }), (error) => error.code === "AGENT_NOT_STARTED");
    const rejected = await rejectHandoff({ state: fixture.statePath, operation: prepared.operation_path, reason: "Missing required generated context." });
    assert.equal(rejected.state, "BLOCKED");
    assert.equal(rejected.outcome, "HANDOFF_REJECTED_BEFORE_PRODUCT_REVIEW");
    const operation = await readYamlFile(prepared.operation_path);
    assert.equal(operation.value.status, "SUPERSEDED");
    const state = await readYamlFile(fixture.statePath);
    assert.equal(state.value.blocker.code, "HANDOFF_REJECTED_BEFORE_PRODUCT_REVIEW");
    assert.equal(state.value.review_result, undefined);
    assert.equal(state.value.handoff_history[0].outcome, "HANDOFF_REJECTED_BEFORE_PRODUCT_REVIEW");
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
    const unrelatedPreflight = await preflightRun(fixture.runPath, { focusUnitId: "T002" });
    assert.equal(unrelatedPreflight.dispatchable, true);

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
    const oldOperation = await readYamlFile(dispatched.operation_path);
    assert.equal(oldOperation.value.status, "SUPERSEDED");
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

test("reconciliation rejects a reused external job ID before mutating state", async () => {
  const fixture = await setupRun();
  try {
    const prepared = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" });
    await bindAgent({ jobId: "JOB-REUSED", operation: prepared.operation_path });
    await createYamlFile(join(fixture.runDirectory, "operations", "RUN-001:T002:DISPATCH_WORKER:attempt-001.yaml"), {
      schema_version: 1,
      operation_id: "RUN-001:T002:DISPATCH_WORKER",
      operation_instance_id: "RUN-001:T002:DISPATCH_WORKER:attempt-001",
      work_unit_id: "T002",
      attempt_id: "RUN-001:T002:worker:attempt-001",
      type: "DISPATCH_WORKER",
      status: "EXECUTING",
      job_id: "JOB-REUSED",
      input: { run_id: "RUN-001", work_unit_id: "T002" },
      result: null,
    });
    await assert.rejects(
      () => reconcileAgent({ jobId: "JOB-REUSED", state: fixture.statePath }),
      (error) => error.code === "AMBIGUOUS_AGENT_JOB",
    );
    const state = await readYamlFile(fixture.statePath);
    assert.equal(state.value.state, "ASSIGNED");
  } finally {
    await teardownRun(fixture);
  }
});

test("reviewer preparation fails closed when generated worker evidence is missing", async () => {
  const fixture = await setupRun();
  try {
    const worker = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" });
    await bindAgent({ jobId: "JOB-CONTEXT-WORKER", operation: worker.operation_path });
    await acknowledgeAgent({ jobId: "JOB-CONTEXT-WORKER", state: fixture.statePath, operation: worker.operation_path });
    const workerHandoff = await readYamlFile(worker.handoff_path);
    await createYamlFile(workerHandoff.value.report.path, { schema_version: 1, role: "squad-worker", run_id: "RUN-001", work_unit_id: "T001", attempt_id: workerHandoff.value.attempt_id, status: "IMPLEMENTED", commits: [fixture.initialHead] });
    await completeWorker({ state: fixture.statePath, report: workerHandoff.value.report.path });
    await rm(workerHandoff.value.report.path);
    await assert.rejects(() => prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "reviewer" }), (error) => error.code === "HANDOFF_CONTEXT_REQUIRED");
    const state = await readYamlFile(fixture.statePath);
    assert.equal(state.value.state, "AWAITING_REVIEW");
    assert.equal(state.value.active_handoff, null);
  } finally {
    await teardownRun(fixture);
  }
});

test("typed worker-review-integrate-complete flow preserves exact revisions and archives handoffs", { timeout: 20000 }, async () => {
  const fixture = await setupRun();
  try {
    const workerDispatch = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" });
    const workerBound = await bindAgent({ jobId: "JOB-WORKER", operation: workerDispatch.operation_path });
    assert.equal(workerBound.operation_status, "EXECUTING");
    const workerAcknowledged = await acknowledgeAgent({ jobId: "JOB-WORKER", state: fixture.statePath, operation: workerDispatch.operation_path });
    assert.equal(workerAcknowledged.state, "IMPLEMENTING");
    await writeFile(join(fixture.worktree, "app.txt"), "implemented\n");
    await runGit(fixture.worktree, ["add", "app.txt"]);
    await runGit(fixture.worktree, ["commit", "-m", "implement behavior"]);
    const implementationRevision = await runGit(fixture.worktree, ["rev-parse", "HEAD"]);
    const workerReportPath = join(fixture.runDirectory, "work-units", "T001", "worker", "attempt-001", "report.yaml");
    await createYamlFile(workerReportPath, { schema_version: 1, role: "squad-worker", run_id: "RUN-001", work_unit_id: "T001", attempt_id: "RUN-001:T001:worker:attempt-001", status: "IMPLEMENTED", commits: [implementationRevision] });
    const workerComplete = await completeWorker({ state: fixture.statePath, report: workerReportPath });
    assert.equal(workerComplete.state, "AWAITING_REVIEW");

    const reviewerDispatch = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "reviewer" });
    const reviewerBound = await bindAgent({ jobId: "JOB-REVIEWER", operation: reviewerDispatch.operation_path });
    assert.equal(reviewerBound.operation_status, "EXECUTING");
    const reviewerOperation = await readYamlFile(reviewerDispatch.operation_path);
    const reviewerHandoff = await readYamlFile(reviewerDispatch.handoff_path);
    assert.equal(reviewerHandoff.value.reviewer_context.environment.admission, "ADVISORY_LEGACY");
    assert.equal(reviewerHandoff.value.reviewer_context.worker.report_digest.startsWith("sha256:"), true);
    await writeFile(join(fixture.worktree, "review-proof.txt"), "review\n");
    await rm(join(fixture.worktree, "review-proof.txt"));
    const reviewerAttemptId = reviewerHandoff.value.attempt_id;
    const reviewerReportPath = reviewerHandoff.value.report.path;
    await createYamlFile(reviewerReportPath, { schema_version: 1, role: "squad-reviewer", run_id: "RUN-001", work_unit_id: "T001", attempt_id: reviewerAttemptId, status: "COMPLETE", verdict: "APPROVED", reviewer: { reviewed_revision: implementationRevision, final_revision: implementationRevision } });
    const reviewComplete = await completeReview({ state: fixture.statePath, report: reviewerReportPath });
    assert.equal(reviewComplete.state, "INTEGRATING");
    assert.equal(reviewComplete.revision, implementationRevision);
    const approvedTargetCheckpoint = (await readYamlFile(fixture.statePath)).value.accepted_review.target_head;

    await writeFile(join(fixture.project, "external.txt"), "external\n");
    await runGit(fixture.project, ["add", "external.txt"]);
    await runGit(fixture.project, ["commit", "-m", "external checkpoint"]);
    const externalCheckpoint = await runGit(fixture.project, ["rev-parse", "main"]);
    const checkpointRun = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, checkpointRun.digest, [{ pointer: "/project/target_head", value: externalCheckpoint }]);
    const stateBeforeNonFastForward = await readYamlFile(fixture.statePath);
    await updateYamlFile(fixture.statePath, stateBeforeNonFastForward.digest, [{ pointer: "/accepted_review/target_head", value: externalCheckpoint }]);
    await assert.rejects(() => integrateTicket({ run: fixture.runPath, state: fixture.statePath }), (error) => error.code === "INTEGRATION_NOT_FAST_FORWARD");
    const failedIntegration = await readYamlFile(join(fixture.runDirectory, "operations", "RUN-001:T001:INTEGRATE:attempt-001.yaml"));
    assert.equal(failedIntegration.value.status, "FAILED");
    assert.equal(await runGit(fixture.project, ["rev-parse", "main"]), externalCheckpoint);
    await runGit(fixture.project, ["reset", "--hard", fixture.initialHead]);
    const resetRun = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, resetRun.digest, [{ pointer: "/project/target_head", value: fixture.initialHead }]);
    const resetState = await readYamlFile(fixture.statePath);
    await updateYamlFile(fixture.statePath, resetState.digest, [{ pointer: "/accepted_review/target_head", value: approvedTargetCheckpoint }]);
    await writeFile(join(fixture.project, "external.txt"), "external drift\n");
    await runGit(fixture.project, ["add", "external.txt"]);
    await runGit(fixture.project, ["commit", "-m", "external drift"]);
    const driftedTarget = await runGit(fixture.project, ["rev-parse", "main"]);
    await assert.rejects(() => integrateTicket({ run: fixture.runPath, state: fixture.statePath }), (error) => error.code === "TARGET_DRIFT");
    assert.equal(await runGit(fixture.project, ["rev-parse", "main"]), driftedTarget);
    await runGit(fixture.project, ["reset", "--hard", fixture.initialHead]);
    const finalCheckpointRun = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, finalCheckpointRun.digest, [{ pointer: "/project/target_head", value: fixture.initialHead }]);
    assert.equal((await readYamlFile(fixture.runPath)).value.project.target_head, fixture.initialHead);
    const integration = await integrateTicket({ run: fixture.runPath, state: fixture.statePath });
    assert.equal(integration.target_after, implementationRevision);
    const failedIntegrationAfterRetry = await readYamlFile(join(fixture.runDirectory, "operations", "RUN-001:T001:INTEGRATE:attempt-001.yaml"));
    assert.equal(failedIntegrationAfterRetry.value.status, "SUPERSEDED");
    const successfulIntegration = await readYamlFile(join(fixture.runDirectory, "operations", "RUN-001:T001:INTEGRATE:attempt-002.yaml"));
    assert.equal(successfulIntegration.value.status, "SUCCEEDED");
    const integrationRetry = await integrateTicket({ run: fixture.runPath, state: fixture.statePath });
    assert.equal(integrationRetry.target_after, implementationRevision);
    const integratingState = await readYamlFile(fixture.statePath);
    const runForValidation = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, runForValidation.digest, [{ pointer: "/validation_evidence_required", value: true }]);
    const evidencePath = join(fixture.runDirectory, "qa-validation.yaml");
    await createYamlFile(evidencePath, { schema_version: 1, kind: "squad-host-validation", status: "PASS", target: { before: integratingState.value.integration.target_before, after: integratingState.value.integration.target_after, clean: true }, integration: { source_revision: integratingState.value.integration.source_revision, operation_instance_id: integratingState.value.integration.operation_instance_id, target_before: integratingState.value.integration.target_before, target_after: integratingState.value.integration.target_after }, checks: [], acceptance: { criteria: ["focused integration check"], limitations: [] }, review: { report_digest: integratingState.value.accepted_review.report_digest } });
    const completed = await completeTicket({ state: fixture.statePath, validation: evidencePath });
    assert.equal(completed.state, "DONE");
    const idempotentCompletion = await completeTicket({ state: fixture.statePath, validation: evidencePath });
    assert.equal(idempotentCompletion.idempotent, true);
    await writeFile(join(fixture.project, "post-completion.txt"), "target moved\n");
    await runGit(fixture.project, ["add", "post-completion.txt"]);
    await runGit(fixture.project, ["commit", "-m", "post completion target movement"]);
    await assert.rejects(() => completeTicket({ state: fixture.statePath, validation: evidencePath }), (error) => error.code === "COMPLETION_EVIDENCE_CONFLICT");
    await runGit(fixture.project, ["reset", "--hard", implementationRevision]);
    const conflictingEvidencePath = join(fixture.runDirectory, "qa-validation-conflict.yaml");
    await createYamlFile(conflictingEvidencePath, { schema_version: 1, kind: "squad-host-validation", status: "PASS", target: { before: integratingState.value.integration.target_before, after: integratingState.value.integration.target_after, clean: true }, integration: { source_revision: integratingState.value.integration.source_revision, operation_instance_id: integratingState.value.integration.operation_instance_id, target_before: integratingState.value.integration.target_before, target_after: integratingState.value.integration.target_after }, checks: [], acceptance: { criteria: ["different evidence"], limitations: [] }, review: { report_digest: integratingState.value.accepted_review.report_digest } });
    await assert.rejects(() => completeTicket({ state: fixture.statePath, validation: conflictingEvidencePath }), (error) => error.code === "COMPLETION_EVIDENCE_CONFLICT");
    const state = (await readYamlFile(fixture.statePath)).value;
    assert.equal(state.completion.marker, "x");
    assert.equal(state.active_handoff, null);
    assert.equal(state.handoff_path, null);
    assert.equal(state.handoff_history.length, 2);
    assert.equal(state.integration.source_revision, implementationRevision);
    const historicalWorker = await validateHandoffFile(state.handoff_history[0].handoff_path, { historical: true, throwOnInvalid: false });
    const historicalReviewer = await validateHandoffFile(state.handoff_history[1].handoff_path, { historical: true, throwOnInvalid: false });
    assert.equal(historicalWorker.valid, true, JSON.stringify(historicalWorker.errors));
    assert.equal(historicalReviewer.valid, true, JSON.stringify(historicalReviewer.errors));
    assert.ok((await readFile(completed.acceptance_status_path, "utf8")).includes("T001"));
    const targetHead = await runGit(fixture.project, ["rev-parse", "main"]);
    assert.equal(targetHead, implementationRevision);
    const reviewerOperationAfter = await readYamlFile(reviewerDispatch.operation_path);
    assert.equal(reviewerOperationAfter.value.status, "SUCCEEDED");
    assert.equal(reviewerOperationAfter.value.operation_instance_id, reviewerOperation.value.operation_instance_id);
    const verified = await verifyRun(fixture.runPath);
    assert.equal(verified.valid, true, JSON.stringify(verified.issues));
  } finally {
    await teardownRun(fixture);
  }
});

test("generated artifacts complete the worker-to-final-run path without forced terminal state", { timeout: 20000 }, async () => {
  const fixture = await setupRun();
  try {
    const worker = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" });
    await bindAgent({ jobId: "JOB-E2E-WORKER", operation: worker.operation_path });
    await acknowledgeAgent({ jobId: "JOB-E2E-WORKER", state: fixture.statePath, operation: worker.operation_path });
    await writeFile(join(fixture.worktree, "app.txt"), "e2e implementation\n");
    await runGit(fixture.worktree, ["add", "app.txt"]);
    await runGit(fixture.worktree, ["commit", "-m", "e2e implementation"]);
    const implementationRevision = await runGit(fixture.worktree, ["rev-parse", "HEAD"]);
    const workerHandoff = await readYamlFile(worker.handoff_path);
    await createYamlFile(workerHandoff.value.report.path, { schema_version: 1, role: "squad-worker", run_id: "RUN-001", work_unit_id: "T001", attempt_id: workerHandoff.value.attempt_id, status: "IMPLEMENTED", commits: [implementationRevision] });
    await completeWorker({ state: fixture.statePath, report: workerHandoff.value.report.path });
    const reviewer = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "reviewer" });
    await bindAgent({ jobId: "JOB-E2E-REVIEWER", operation: reviewer.operation_path });
    const reviewerHandoff = await readYamlFile(reviewer.handoff_path);
    await createYamlFile(reviewerHandoff.value.report.path, { schema_version: 1, role: "squad-reviewer", run_id: "RUN-001", work_unit_id: "T001", attempt_id: reviewerHandoff.value.attempt_id, status: "COMPLETE", verdict: "APPROVED", reviewer: { reviewed_revision: implementationRevision, final_revision: implementationRevision } });
    await completeReview({ state: fixture.statePath, report: reviewerHandoff.value.report.path });
    await integrateTicket({ run: fixture.runPath, state: fixture.statePath });
    const integrating = (await readYamlFile(fixture.statePath)).value;
    const runBeforeValidation = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, runBeforeValidation.digest, [{ pointer: "/validation_evidence_required", value: true }]);
    const validationPath = join(fixture.runDirectory, "validation", "ticket.yaml");
    await createYamlFile(validationPath, { schema_version: 1, kind: "squad-host-validation", status: "PASS", target: { before: integrating.integration.target_before, after: integrating.integration.target_after, clean: true }, integration: { source_revision: integrating.integration.source_revision, operation_instance_id: integrating.integration.operation_instance_id, target_before: integrating.integration.target_before, target_after: integrating.integration.target_after }, checks: [{ id: "E2E", status: "PASS", command: "focused" }], acceptance: { criteria: ["behavior"], limitations: [] }, review: { report_digest: integrating.accepted_review.report_digest } });
    await completeTicket({ state: fixture.statePath, validation: validationPath });
    const runValidation = await commitRunTransition({ runPath: fixture.runPath, from: "EXECUTING", to: "RUN_VALIDATING", reason: "Generated end-to-end ticket path completed." });
    assert.equal(runValidation.status, "COMMITTED");
    const qa = await prepareRunQa({ run: fixture.runPath });
    const qaHandoff = await readYamlFile(qa.handoff_path);
    assert.equal(qaHandoff.value.source.proposal_required, false);
    assert.equal(qaHandoff.value.capability_environment_profile.admission, "ADVISORY_LEGACY");
    await bindAgent({ jobId: "JOB-E2E-QA", operation: qa.operation_path });
    await createYamlFile(qa.report_path, { schema_version: 1, role: "squad-qa", run_id: "RUN-001", qa_id: qa.qa_id, attempt_id: qa.attempt_id, status: "COMPLETE", verdict: "PASSED", canonical: { revision: implementationRevision } });
    await completeRunQa({ run: fixture.runPath, report: qa.report_path });
    await completeRun({ run: fixture.runPath });
    const final = await verifyRun(fixture.runPath, { final: true });
    assert.equal(final.valid, true, JSON.stringify(final.issues));
  } finally {
    await teardownRun(fixture);
  }
});

test("analysis completion records an advisory report without advancing lifecycle state", async () => {
  const fixture = await setupRun();
  try {
    const prepared = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "analysis" });
    const handoff = await readYamlFile(prepared.handoff_path);
    await bindAgent({ jobId: "JOB-ANALYSIS", operation: prepared.operation_path });
    const reportPath = handoff.value.report.path;
    await createYamlFile(reportPath, { schema_version: 1, role: "squad-analysis-reconciliation", run_id: "RUN-001", work_unit_id: "T001", attempt_id: handoff.value.attempt_id, analysis_id: handoff.value.analysis_id, kind: "CANONICAL_IMPACT", status: "CONCLUSIVE", conclusions: { unaffected: [], affected: [], unknown: [] }, uncertainty: { level: "LOW", unresolved: [] } });
    const completed = await completeAnalysis({ state: fixture.statePath, report: reportPath });
    assert.equal(completed.state, "READY");
    assert.equal(completed.outcome, "CONCLUSIVE");
    const state = await readYamlFile(fixture.statePath);
    assert.equal(state.value.active_handoff, null);
    assert.equal(state.value.analysis_history.length, 1);
    const operation = await readYamlFile(prepared.operation_path);
    assert.equal(operation.value.status, "SUCCEEDED");
  } finally {
    await teardownRun(fixture);
  }
});

test("run-level QA dispatch and terminal completion are typed and evidence-gated", async () => {
  const fixture = await setupRun();
  try {
    const reviewerReportPath = join(fixture.runDirectory, "work-units", "T001", "reviewer", "attempt-001", "report.yaml");
    await createYamlFile(reviewerReportPath, { schema_version: 1, role: "squad-reviewer", run_id: "RUN-001", work_unit_id: "T001", attempt_id: "RUN-001:T001:reviewer:attempt-001", status: "COMPLETE", verdict: "APPROVED", reviewer: { final_revision: fixture.initialHead, reviewed_revision: fixture.initialHead } });
    const reviewerReport = await readYamlFile(reviewerReportPath);
    const stateDocument = await readYamlFile(fixture.statePath);
    await updateYamlFile(fixture.statePath, stateDocument.digest, [
      { pointer: "/state", value: "DONE" },
      { pointer: "/integration", value: { source_revision: fixture.initialHead, target_before: fixture.initialHead, target_after: fixture.initialHead, integrated_at: "2026-01-01T00:00:00.000Z" } },
      { pointer: "/accepted_review", value: { report_path: reviewerReportPath, report_digest: reviewerReport.digest, revision: fixture.initialHead } },
    ]);
    const runDocument = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, runDocument.digest, [{ pointer: "/state", value: "RUN_VALIDATING" }]);
    const prepared = await prepareRunQa({ run: fixture.runPath });
    assert.equal(prepared.state, "QA");
    const handoff = await validateHandoffFile(prepared.handoff_path, { throwOnInvalid: false });
    assert.equal(handoff.valid, true, JSON.stringify(handoff.errors));
    const invalidQaHandoff = structuredClone(handoff.value ?? (await readYamlFile(prepared.handoff_path)).value);
    invalidQaHandoff.target.branch = "not-the-target";
    const invalidQaValidation = await validateQaHandoffData(invalidQaHandoff, prepared.handoff_path, { throwOnInvalid: false });
    assert.equal(invalidQaValidation.valid, false);
    assert.ok(invalidQaValidation.errors.some((entry) => entry.code === "BRANCH_MISMATCH"));
    await bindAgent({ jobId: "JOB-QA", operation: prepared.operation_path });
    await createYamlFile(prepared.report_path, { schema_version: 1, role: "squad-qa", run_id: "RUN-001", qa_id: prepared.qa_id, attempt_id: prepared.attempt_id, status: "COMPLETE", verdict: "PASSED", canonical: { revision: fixture.initialHead } });
    const qaComplete = await completeRunQa({ run: fixture.runPath, report: prepared.report_path });
    assert.equal(qaComplete.state, "COMPLETING");
    const completed = await completeRun({ run: fixture.runPath });
    assert.equal(completed.state, "RUN_COMPLETED");
    const verified = await verifyRun(fixture.runPath);
    assert.equal(verified.valid, true, JSON.stringify(verified.issues));
    const finalVerified = await verifyRun(fixture.runPath, { final: true });
    assert.equal(finalVerified.valid, true, JSON.stringify(finalVerified.issues));
    const finalRun = await readYamlFile(fixture.runPath);
    assert.equal(finalRun.value.state, "RUN_COMPLETED");
    assert.ok(finalRun.value.final_summary_path);
  } finally {
    await teardownRun(fixture);
  }
});

test("migrate-run normalizes a legacy logical operation and typed completion remains usable", { timeout: 20000 }, async () => {
  const fixture = await setupRun();
  try {
    const prepared = await prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" });
    const currentOperation = (await readYamlFile(prepared.operation_path)).value;
    const currentManifest = (await readYamlFile(prepared.manifest_path)).value;
    const currentHandoff = (await readYamlFile(prepared.handoff_path)).value;
    const legacyOperationPath = join(fixture.runDirectory, "operations", "RUN-001:T001:DISPATCH_WORKER.yaml");
    const legacyManifestPath = join(fixture.runDirectory, "work-units", "T001", "manifests", "legacy-worker.yaml");
    const legacyHandoffPath = join(fixture.runDirectory, "work-units", "T001", "handoffs", "legacy-worker.yaml");
    const legacyOperation = structuredClone(currentOperation);
    delete legacyOperation.operation_instance_id;
    legacyOperation.input = { ...legacyOperation.input, manifest_path: legacyManifestPath, handoff_path: legacyHandoffPath };
    await createYamlFile(legacyOperationPath, legacyOperation);
    const legacyManifest = structuredClone(currentManifest);
    delete legacyManifest.operation.instance_id;
    legacyManifest.artifact = { ...legacyManifest.artifact, manifest_path: legacyManifestPath, handoff_path: legacyHandoffPath, operation_path: legacyOperationPath };
    const legacyManifestWrite = await createYamlFile(legacyManifestPath, legacyManifest);
    const legacyHandoff = structuredClone(currentHandoff);
    delete legacyHandoff.operation_instance_id;
    delete legacyHandoff.operation.instance_id;
    legacyHandoff.artifact = { ...legacyHandoff.artifact, manifest_path: legacyManifestPath, handoff_path: legacyHandoffPath, operation_path: legacyOperationPath };
    legacyHandoff.manifest = { path: legacyManifestPath, digest: legacyManifestWrite.digest };
    const legacyHandoffWrite = await createYamlFile(legacyHandoffPath, legacyHandoff);
    await rm(prepared.operation_path);
    await rm(prepared.manifest_path);
    await rm(prepared.handoff_path);
    const stateDocument = await readYamlFile(fixture.statePath);
    const legacyActiveHandoff = { ...stateDocument.value.active_handoff, operation_instance_id: null, operation_path: legacyOperationPath, manifest_path: legacyManifestPath, handoff_path: legacyHandoffPath, handoff_digest: legacyHandoffWrite.digest };
    await updateYamlFile(fixture.statePath, stateDocument.digest, [{ pointer: "/active_handoff", value: legacyActiveHandoff }, { pointer: "/operation_path", value: legacyOperationPath }, { pointer: "/manifest_path", value: legacyManifestPath }, { pointer: "/handoff_path", value: legacyHandoffPath }]);
    const migrated = await migrateRun({ run: fixture.runPath });
    assert.equal(migrated.migrated[0].status, "MIGRATED");
    assert.equal(migrated.legacy_environment_profile.status, "LEGACY_ENVIRONMENT_PROFILE_MISSING");
    const migratedRun = (await readYamlFile(fixture.runPath)).value;
    assert.equal(migratedRun.purpose, "production");
    assert.equal(migratedRun.worker_mode, "default");
    const migratedPreflight = await preflightRun(fixture.runPath);
    assert.equal(migratedPreflight.valid, true, JSON.stringify(migratedPreflight.issues));
    const migratedState = (await readYamlFile(fixture.statePath)).value;
    assert.match(migratedState.active_handoff.operation_instance_id, /:attempt-001$/);
    assert.notEqual(migratedState.active_handoff.operation_path, legacyOperationPath);
    const migratedHandoff = await validateHandoffFile(migratedState.active_handoff.handoff_path, { throwOnInvalid: false });
    assert.equal(migratedHandoff.valid, true, JSON.stringify(migratedHandoff.errors));
    const partialState = await readYamlFile(fixture.statePath);
    await updateYamlFile(fixture.statePath, partialState.digest, [{ pointer: "/active_handoff", value: legacyActiveHandoff }, { pointer: "/operation_path", value: legacyOperationPath }, { pointer: "/manifest_path", value: legacyManifestPath }, { pointer: "/handoff_path", value: legacyHandoffPath }]);
    const retried = await migrateRun({ run: fixture.runPath });
    assert.equal(retried.migrated[0].status, "MIGRATED");
    const repeated = await migrateRun({ run: fixture.runPath });
    assert.equal(repeated.migrated[0].status, "ALREADY_CURRENT");
    assert.equal(repeated.changed, false);
    const operationNames = (await readdir(join(fixture.runDirectory, "operations"))).filter((name) => name.endsWith(".yaml"));
    assert.equal(operationNames.filter((name) => name.includes(":attempt-001")).length, 1);
    await bindAgent({ jobId: "JOB-MIGRATED", operation: migratedState.active_handoff.operation_path });
    const operation = await readYamlFile(migratedState.active_handoff.operation_path);
    await commitUnitTransition({ statePath: fixture.statePath, workUnitId: "T001", from: "ASSIGNED", to: "IMPLEMENTING", reason: "Migrated worker acknowledged.", operationId: operation.value.operation_id, operationInstanceId: operation.value.operation_instance_id });
    await createYamlFile(migratedState.active_handoff.report_path, { schema_version: 1, role: "squad-worker", run_id: "RUN-001", work_unit_id: "T001", attempt_id: migratedState.active_handoff.attempt_id, status: "IMPLEMENTED", commits: [fixture.initialHead] });
    const completed = await completeWorker({ state: fixture.statePath, report: migratedState.active_handoff.report_path });
    assert.equal(completed.state, "AWAITING_REVIEW");
  } finally {
    await teardownRun(fixture);
  }
});

test("environment, reference, ownership, and migration artifacts remain durable projections", async () => {
  const fixture = await setupRun();
  try {
    const runBeforeEnvironment = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, runBeforeEnvironment.digest, [{ pointer: "/control_plane_version", value: 2 }]);
    const defaultMissingEnvironment = await preflightRun(fixture.runPath);
    assert.equal(defaultMissingEnvironment.valid, false);
    assert.ok(defaultMissingEnvironment.issues.some((entry) => entry.code === "MISSING_ENVIRONMENT_PROFILE"));
    await assert.rejects(() => prepareDispatch({ run: fixture.runPath, state: fixture.statePath, role: "worker" }), (error) => error.code === "PREFLIGHT_FAILED" && error.details.issues.some((entry) => entry.code === "MISSING_ENVIRONMENT_PROFILE"));
    const runWithRequiredEnvironment = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, runWithRequiredEnvironment.digest, [{ pointer: "/environment_profile_required", value: true }]);
    const missingEnvironment = await preflightRun(fixture.runPath);
    assert.equal(missingEnvironment.valid, false);
    assert.ok(missingEnvironment.issues.some((entry) => entry.code === "MISSING_ENVIRONMENT_PROFILE"));
    const environment = await captureEnvironmentProfile({ run: fixture.runPath, generated: "generated/provider.json" });
    assert.ok(environment.fingerprint.startsWith("sha256:"));
    const environmentPreflight = await preflightRun(fixture.runPath);
    assert.equal(environmentPreflight.valid, true, JSON.stringify(environmentPreflight.issues));
    const proposalPath = join(fixture.runDirectory, "proposal.md");
    await writeFile(proposalPath, "# Proposal\n\nCanonical proposal.\n");
    const proposalDigest = await digestFile(proposalPath);
    const runBeforeProposal = await readYamlFile(fixture.runPath);
    await updateYamlFile(fixture.runPath, runBeforeProposal.digest, [{ pointer: "/proposal_required", value: true }, { pointer: "/proposal", value: { path: proposalPath, digest: proposalDigest } }]);
    const proposalPreflight = await preflightRun(fixture.runPath);
    assert.equal(proposalPreflight.valid, true, JSON.stringify(proposalPreflight.issues));
    const proposalManifest = await buildExecutionManifest({ run: fixture.runPath, state: fixture.statePath, ticket: fixture.ticketPath, role: "worker", attempt: 1 });
    assert.equal(proposalManifest.manifest.source.proposal_required, true);
    assert.equal(proposalManifest.manifest.source.proposal_digest, proposalDigest);
    const environmentCli = await runWorkflowCli(["environment-profile", "--run", fixture.runPath]);
    assert.equal(environmentCli.exitCode, 0, environmentCli.stderr);
    const runAfterEnvironment = (await readYamlFile(fixture.runPath)).value;
    assert.equal(runAfterEnvironment.environment.profile_path, environment.path);

    const reference = await recordReferenceSnapshot({ run: fixture.runPath, repository: fixture.project, revision: fixture.initialHead, files: "app.txt" });
    assert.equal(reference.files[0].path, "app.txt");
    assert.ok((await readYamlFile(fixture.runPath)).value.reference_snapshots.length === 1);

    const stateDocument = await readYamlFile(fixture.statePath);
    await updateYamlFile(fixture.statePath, stateDocument.digest, [{ pointer: "/scope_paths", value: ["app.txt"] }]);
    const ownership = await analyzeOwnership({ run: fixture.runPath });
    assert.equal(ownership.pairs.length, 0);
    assert.ok(ownership.frontier);
    assert.deepEqual(ownership.frontier.ready, ["T001"]);
    assert.equal(ownership.path.endsWith("analysis/ownership.yaml"), true);

    const migrated = await migrateRun({ run: fixture.runPath });
    assert.equal(migrated.control_plane_version, 2);
    assert.equal((await readYamlFile(fixture.runPath)).value.control_plane_version, 2);
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
    assert.equal(dashboard.context_health, "MIGRATION_REQUIRED");
    assert.equal(dashboard.next_command, "ADVANCE_TO_RUN_VALIDATING_WHEN_UNITS_DONE");
    assert.deepEqual(dashboard.work_units[0].explanation.legal_next_states, ["ASSIGNED", "BLOCKED"]);
    const verification = await verifyRun(fixture.runPath);
    assert.equal(verification.valid, true, JSON.stringify(verification.issues));
  } finally {
    await teardownRun(fixture);
  }
});
