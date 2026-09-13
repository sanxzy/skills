import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  appendYamlFile,
  createYamlFile,
  deepEqual,
  getAt,
  parseJsonPointer,
  readYamlFile,
  unlockYamlFile,
  updateYamlFile,
  verifyYamlFile,
} from "./_yaml-io.mjs";

async function withTempFile(run) {
  const directory = await mkdtemp(join(tmpdir(), "squad-yaml-"));
  const file = join(directory, "report.yaml");
  try {
    await run(file);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

test("create, update, and append use digests and atomic YAML writes", async () => {
  await withTempFile(async (file) => {
    const created = await createYamlFile(file, {
      status: "IN_PROGRESS",
      incremental_qa_log: [],
      nested: { value: 1 },
    });
    assert.equal(created.command, "create");
    assert.equal(created.changed, true);

    const initial = await readYamlFile(file);
    assert.equal(initial.value.status, "IN_PROGRESS");
    assert.deepEqual(initial.value.incremental_qa_log, []);

    const updated = await updateYamlFile(file, initial.digest, [
      { pointer: "/status", value: "COMPLETE" },
      { pointer: "/nested/value", value: 2 },
    ]);
    assert.equal(updated.changed, true);
    assert.notEqual(updated.digest, initial.digest);

    const appended = await appendYamlFile(
      file,
      updated.digest,
      "/incremental_qa_log",
      { id: "LOG-001", result: "PASS" },
    );
    assert.equal(appended.changed, true);

    const afterAppend = await readYamlFile(file);
    assert.equal(afterAppend.value.status, "COMPLETE");
    assert.equal(afterAppend.value.incremental_qa_log.length, 1);
    assert.equal(afterAppend.value.incremental_qa_log[0].id, "LOG-001");

    const retry = await appendYamlFile(
      file,
      afterAppend.digest,
      "/incremental_qa_log",
      { id: "LOG-001", result: "PASS" },
    );
    assert.equal(retry.changed, false);
    assert.equal(retry.digest, afterAppend.digest);

    const verified = await verifyYamlFile(file);
    assert.equal(verified.valid, true);
    assert.equal(verified.digest, afterAppend.digest);
  });
});

test("stale updates and conflicting duplicate appends do not mutate the file", async () => {
  await withTempFile(async (file) => {
    await createYamlFile(file, { entries: [] });
    const initial = await readYamlFile(file);
    const first = await appendYamlFile(file, initial.digest, "/entries", {
      id: "E-001",
      value: "first",
    });
    const beforeConflict = await readFile(file, "utf8");

    await assert.rejects(
      () => updateYamlFile(file, initial.digest, [{ pointer: "/state", value: "stale" }]),
      (error) => error.code === "STALE_DIGEST",
    );
    assert.equal(await readFile(file, "utf8"), beforeConflict);

    const current = await readYamlFile(file);
    await assert.rejects(
      () => appendYamlFile(file, current.digest, "/entries", {
        id: "E-001",
        value: "different",
      }),
      (error) => error.code === "APPEND_CONFLICT",
    );
    assert.equal((await readYamlFile(file)).digest, first.digest);
  });
});

test("JSON Pointer paths and explicit lock recovery are safe", async () => {
  assert.deepEqual(parseJsonPointer("/a~1b/c~0d"), ["a/b", "c~d"]);
  assert.equal(getAt({ nested: { value: 3 } }, "/nested/value"), 3);
  assert.equal(deepEqual({ a: 1, b: 2 }, { b: 2, a: 1 }), true);
  assert.throws(() => parseJsonPointer("a/b"), (error) => error.code === "INVALID_POINTER");

  await withTempFile(async (file) => {
    await createYamlFile(file, { entries: [] });
    const current = await readYamlFile(file);
    await assert.rejects(
      () => appendYamlFile(file, current.digest, "/entries", { value: "missing-id" }),
      (error) => error.code === "APPEND_ID_REQUIRED",
    );
    const unlocked = await unlockYamlFile(file, true);
    assert.equal(unlocked.changed, false);
  });
});
