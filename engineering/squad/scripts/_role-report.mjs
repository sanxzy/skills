import {
  appendYamlFile,
  createYamlFile,
  getAt,
  readYamlFile,
  setAt,
  unlockYamlFile,
  updateYamlFile,
  verifyYamlFile,
  cloneValue,
  YamlToolError,
} from "./_yaml-io.mjs";

function fail(code, message, details = undefined) {
  throw new YamlToolError(code, message, details);
}

function ensureMapping(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    fail("INVALID_REPORT", "A role report must be a YAML mapping/object.");
  }
}

export function ensureRoleReport(value, role, logPath, { initializeLog = false } = {}) {
  ensureMapping(value);
  const report = cloneValue(value);
  if (report.role === undefined) report.role = role;
  if (report.role !== role) fail("ROLE_MISMATCH", `Expected role ${role}, received ${report.role}.`);
  if (initializeLog) {
    try {
      const log = getAt(report, logPath);
      if (!Array.isArray(log)) fail("INVALID_REPORT_LOG", `Report log path is not an array: ${logPath}`);
    } catch (error) {
      if (error.code !== "MISSING_PATH") throw error;
      setAt(report, logPath, []);
    }
  }
  return report;
}

function assertRoleUpdatePaths(sets) {
  for (const { pointer } of sets) {
    if (pointer === "/role" || pointer.startsWith("/role/")) {
      fail("ROLE_IMMUTABLE", "A role report cannot update its role field.");
    }
  }
}

export async function createRoleReport(file, value, role, logPath) {
  return createYamlFile(file, ensureRoleReport(value, role, logPath, { initializeLog: true }));
}

export async function updateRoleReport(file, expectedDigest, sets, role) {
  assertRoleUpdatePaths(sets);
  const current = await readYamlFile(file);
  ensureRoleReport(current.value, role, undefined);
  return updateYamlFile(file, expectedDigest, sets);
}

export async function appendRoleReport(file, expectedDigest, entryPath, entry, role, options = {}) {
  const current = await readYamlFile(file);
  ensureRoleReport(current.value, role, undefined);
  return appendYamlFile(file, expectedDigest, entryPath, entry, options);
}

export async function readRoleReport(file, role, pointer = undefined) {
  const result = await readYamlFile(file);
  ensureRoleReport(result.value, role, undefined);
  return pointer === undefined ? result : { ...result, value: getAt(result.value, pointer) };
}

export async function verifyRoleReport(file, role) {
  const result = await verifyYamlFile(file);
  const report = await readYamlFile(file);
  ensureRoleReport(report.value, role, undefined);
  return result;
}

export { unlockYamlFile };
