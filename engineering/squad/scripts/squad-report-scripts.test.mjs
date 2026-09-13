import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const scriptsDirectory = new URL(".", import.meta.url).pathname;
const roleScripts = [
  ["squad-worker-report.mjs", "squad-worker", "/incremental_worker_log"],
  ["squad-reviewer-report.mjs", "squad-reviewer", "/incremental_review_log"],
  ["squad-qa-report.mjs", "squad-qa", "/incremental_qa_log"],
  ["squad-analysis-report.mjs", "squad-analysis-reconciliation", "/incremental_analysis_log"],
];

async function runScript(script, args) {
  const process = Bun.spawn(["bun", join(scriptsDirectory, script), ...args], {
    stdout: "pipe",
    stderr: "pipe",
  });
  const [stdout, stderr, exitCode] = await Promise.all([
    new Response(process.stdout).text(),
    new Response(process.stderr).text(),
    process.exited,
  ]);
  assert.equal(exitCode, 0, `${script} failed: ${stderr}`);
  return stdout.trim();
}

async function withTempDirectory(run) {
  const directory = await mkdtemp(join(tmpdir(), "squad-report-scripts-"));
  try {
    await run(directory);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test("each agent report entrypoint owns its role and incremental log", async () => {
  await withTempDirectory(async (directory) => {
    for (const [script, role, logPath] of roleScripts) {
      const file = join(directory, `${role}.yaml`);
      const created = JSON.parse(await runScript(script, [
        "create",
        "--file",
        file,
        "--data",
        '{"status":"IN_PROGRESS"}',
      ]));
      assert.equal(created.changed, true);

      const initialDigest = (await runScript(script, ["digest", "--file", file])).trim();
      const appended = JSON.parse(await runScript(script, [
        "append",
        "--file",
        file,
        "--expect-digest",
        initialDigest,
        "--entry",
        '{"id":"LOG-001","result":"PASS"}',
      ]));
      assert.equal(appended.changed, true);

      const afterAppendDigest = (await runScript(script, ["digest", "--file", file])).trim();
      const updated = JSON.parse(await runScript(script, [
        "update",
        "--file",
        file,
        "--expect-digest",
        afterAppendDigest,
        "--set",
        "/status=COMPLETE",
      ]));
      assert.equal(updated.changed, true);

      const report = JSON.parse(await runScript(script, ["read", "--file", file, "--format", "json"]));
      assert.equal(report.role, role);
      assert.equal(report.status, "COMPLETE");
      assert.deepEqual(report[logPath.slice(1)], [{ id: "LOG-001", result: "PASS" }]);
      assert.equal(JSON.parse(await runScript(script, ["verify", "--file", file])).valid, true);
      assert.ok((await readFile(file, "utf8")).endsWith("\n"));
    }
  });
});

test("host state entrypoint accepts arbitrary canonical state paths", async () => {
  await withTempDirectory(async (directory) => {
    const file = join(directory, "run.yaml");
    await runScript("squad-host-state.mjs", [
      "create",
      "--file",
      file,
      "--data",
      '{"state":"EXECUTING","operations":[]}',
    ]);
    const digest = await runScript("squad-host-state.mjs", ["digest", "--file", file]);
    await runScript("squad-host-state.mjs", [
      "append",
      "--file",
      file,
      "--expect-digest",
      digest,
      "--path",
      "/operations",
      "--id-field",
      "operation_id",
      "--entry",
      '{"operation_id":"OP-001","status":"PREPARED"}',
    ]);
    const state = JSON.parse(await runScript("squad-host-state.mjs", ["read", "--file", file, "--format", "json"]));
    assert.deepEqual(state.operations, [{ operation_id: "OP-001", status: "PREPARED" }]);
  });
});
