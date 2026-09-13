import { createHash, randomBytes } from "node:crypto";
import { open, readFile, stat, mkdir, rename, chmod, rm, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, resolve, basename, join } from "node:path";

const DEFAULT_MODE = 0o600;
const DIGEST_PATTERN = /^sha256:[0-9a-f]{64}$/i;

export class YamlToolError extends Error {
  constructor(code, message, details = undefined) {
    super(message);
    this.name = "YamlToolError";
    this.code = code;
    this.details = details;
  }
}

function fail(code, message, details = undefined) {
  throw new YamlToolError(code, message, details);
}

function requireBunYaml() {
  if (!globalThis.Bun?.YAML?.parse || !globalThis.Bun?.YAML?.stringify) {
    fail(
      "RUNTIME_UNAVAILABLE",
      "The squad YAML tools require Bun's built-in Bun.YAML API; run them with Bun.",
    );
  }
}

function absolutePath(file) {
  if (!file || typeof file !== "string") fail("INVALID_PATH", "A YAML file path is required.");
  return resolve(file);
}

function digestBytes(bytes) {
  return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
}

function normalizeDigest(value) {
  if (!DIGEST_PATTERN.test(value ?? "")) {
    fail("INVALID_DIGEST", `Expected a sha256 digest, received: ${value ?? "<missing>"}`);
  }
  return value.toLowerCase();
}

export function parseYamlText(text, source = "<input>") {
  requireBunYaml();
  if (text.trim() === "") fail("EMPTY_DOCUMENT", `${source} is empty.`);
  try {
    const value = Bun.YAML.parse(text);
    if (value === undefined) fail("EMPTY_DOCUMENT", `${source} has no YAML value.`);
    return value;
  } catch (error) {
    if (error instanceof YamlToolError) throw error;
    fail("INVALID_YAML", `Could not parse YAML from ${source}.`, { message: error.message });
  }
}

export function serializeYaml(value) {
  requireBunYaml();
  let text;
  try {
    text = Bun.YAML.stringify(value, undefined, 2);
  } catch (error) {
    fail("SERIALIZE_FAILED", "Could not serialize the YAML document.", { message: error.message });
  }
  return text.endsWith("\n") ? text : `${text}\n`;
}

export function formatValue(value, format = "yaml") {
  if (format === "json") return JSON.stringify(value, null, 2);
  if (format !== "yaml") fail("INVALID_FORMAT", `Unsupported format: ${format}`);
  return serializeYaml(value);
}

export function deepEqual(left, right) {
  if (Object.is(left, right)) return true;
  if (typeof left !== typeof right || left === null || right === null) return false;
  if (Array.isArray(left) || Array.isArray(right)) {
    if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) return false;
    return left.every((value, index) => deepEqual(value, right[index]));
  }
  if (typeof left !== "object") return false;
  const leftKeys = Object.keys(left).sort();
  const rightKeys = Object.keys(right).sort();
  if (!deepEqual(leftKeys, rightKeys)) return false;
  return leftKeys.every((key) => deepEqual(left[key], right[key]));
}

function rejectUnsafeKey(key) {
  if (["__proto__", "constructor", "prototype"].includes(key)) {
    fail("INVALID_POINTER", `Unsafe YAML path segment: ${key}`);
  }
}

function hasOwn(object, key) {
  return Object.prototype.hasOwnProperty.call(object, key);
}

export function parseJsonPointer(pointer) {
  if (typeof pointer !== "string") fail("INVALID_POINTER", "A JSON Pointer path is required.");
  if (pointer === "") return [];
  if (!pointer.startsWith("/")) {
    fail("INVALID_POINTER", `JSON Pointer must start with '/': ${pointer}`);
  }
  return pointer.slice(1).split("/").map((segment) => {
    if (/~(?![01])/.test(segment)) {
      fail("INVALID_POINTER", `Invalid JSON Pointer escape in: ${segment}`);
    }
    const decoded = segment.replace(/~1/g, "/").replace(/~0/g, "~");
    rejectUnsafeKey(decoded);
    return decoded;
  });
}

function arrayIndex(segment, length, allowEnd = false) {
  if (!/^(0|[1-9][0-9]*)$/.test(segment)) {
    fail("INVALID_POINTER", `Expected an array index, received: ${segment}`);
  }
  const index = Number(segment);
  const max = allowEnd ? length : length - 1;
  if (!Number.isSafeInteger(index) || index < 0 || index > max) {
    fail("INVALID_POINTER", `Array index is out of range: ${segment}`);
  }
  return index;
}

export function getAt(document, pointer) {
  const segments = parseJsonPointer(pointer);
  let current = document;
  for (const segment of segments) {
    if (Array.isArray(current)) {
      current = current[arrayIndex(segment, current.length)];
    } else if (current !== null && typeof current === "object") {
      if (!hasOwn(current, segment)) fail("MISSING_PATH", `YAML path does not exist: ${pointer}`);
      current = current[segment];
    } else {
      fail("MISSING_PATH", `YAML path does not exist: ${pointer}`);
    }
  }
  return current;
}

export function setAt(document, pointer, value) {
  const segments = parseJsonPointer(pointer);
  if (segments.length === 0) return value;

  let current = document;
  for (let index = 0; index < segments.length - 1; index += 1) {
    const segment = segments[index];
    const next = segments[index + 1];
    if (Array.isArray(current)) {
      const position = arrayIndex(segment, current.length);
      if (current[position] === null || typeof current[position] !== "object") {
        current[position] = /^(0|[1-9][0-9]*)$/.test(next) ? [] : {};
      }
      current = current[position];
    } else if (current !== null && typeof current === "object") {
      rejectUnsafeKey(segment);
      if (!hasOwn(current, segment) || current[segment] === null || typeof current[segment] !== "object") {
        current[segment] = /^(0|[1-9][0-9]*)$/.test(next) ? [] : {};
      }
      current = current[segment];
    } else {
      fail("INVALID_POINTER", `Cannot traverse YAML path: ${pointer}`);
    }
  }

  const last = segments.at(-1);
  if (Array.isArray(current)) {
    if (last === "-") {
      current.push(value);
    } else {
      const position = arrayIndex(last, current.length, true);
      current[position] = value;
    }
  } else if (current !== null && typeof current === "object") {
    rejectUnsafeKey(last);
    current[last] = value;
  } else {
    fail("INVALID_POINTER", `Cannot assign YAML path: ${pointer}`);
  }
  return document;
}

export function parseSetSpec(spec) {
  const separator = spec.indexOf("=");
  if (separator <= 0) fail("INVALID_SET", `Expected <json-pointer>=<value>, received: ${spec}`);
  return { pointer: spec.slice(0, separator), valueSpec: spec.slice(separator + 1) };
}

export async function readValueSpec(spec, label) {
  if (spec === undefined) fail("MISSING_VALUE", `${label} is required.`);
  let text;
  if (spec === "-") {
    text = (await readFile(0)).toString("utf8");
  } else if (spec.startsWith("@")) {
    const source = absolutePath(spec.slice(1));
    text = (await readFile(source)).toString("utf8");
  } else {
    text = spec;
  }

  try {
    return JSON.parse(text);
  } catch {
    return parseYamlText(text, label);
  }
}

async function readFileMode(file) {
  try {
    const info = await stat(file);
    return info.mode & 0o777;
  } catch (error) {
    if (error.code === "ENOENT") return DEFAULT_MODE;
    throw error;
  }
}

async function syncDirectory(directory) {
  try {
    const handle = await open(directory, "r");
    try {
      await handle.sync();
    } finally {
      await handle.close();
    }
  } catch (error) {
    if (!["EINVAL", "ENOTSUP", "EPERM"].includes(error.code)) throw error;
  }
}

async function atomicWriteText(file, text) {
  const directory = dirname(file);
  const temporary = join(
    directory,
    `.${basename(file)}.tmp-${process.pid}-${randomBytes(8).toString("hex")}`,
  );
  const mode = await readFileMode(file);
  let handle;
  try {
    handle = await open(temporary, "wx", mode);
    await handle.writeFile(text, "utf8");
    await handle.sync();
    await handle.close();
    handle = undefined;
    await chmod(temporary, mode);
    await rename(temporary, file);
    await syncDirectory(directory);
  } catch (error) {
    if (handle) await handle.close().catch(() => {});
    await rm(temporary, { force: true }).catch(() => {});
    throw error;
  }
}

async function atomicWriteOwner(lockDirectory, owner) {
  await writeFile(join(lockDirectory, "owner.json"), `${JSON.stringify(owner)}\n`, { mode: 0o600 });
}

async function withFileLock(file, operation, { createParent = false } = {}) {
  const directory = dirname(file);
  if (createParent) await mkdir(directory, { recursive: true });
  const lockDirectory = `${file}.lock`;
  try {
    await mkdir(lockDirectory);
  } catch (error) {
    if (error.code === "EEXIST") {
      fail("LOCKED", `Another YAML operation owns the lock: ${lockDirectory}`);
    }
    throw error;
  }

  try {
    await atomicWriteOwner(lockDirectory, {
      pid: process.pid,
      acquired_at: new Date().toISOString(),
      file,
    });
    return await operation();
  } finally {
    await rm(lockDirectory, { recursive: true, force: true });
  }
}

async function readDocument(file) {
  const bytes = await readFile(file);
  const text = bytes.toString("utf8");
  return { file, value: parseYamlText(text, file), bytes, digest: digestBytes(bytes) };
}

async function writeDocument(file, value) {
  const text = serializeYaml(value);
  await atomicWriteText(file, text);
  const bytes = Buffer.from(text, "utf8");
  return { file, value, bytes, digest: digestBytes(bytes) };
}

function assertExpectedDigest(actual, expected) {
  const normalized = normalizeDigest(expected);
  if (actual !== normalized) {
    fail("STALE_DIGEST", "The YAML file changed since the expected digest was read.", {
      expected: normalized,
      actual,
    });
  }
}

function mutationResult(command, file, before, after, changed) {
  return {
    command,
    file,
    changed,
    previous_digest: before?.digest ?? null,
    digest: after.digest,
  };
}

export async function createYamlFile(filePath, value) {
  const file = absolutePath(filePath);
  requireBunYaml();
  return withFileLock(
    file,
    async () => {
      if (existsSync(file)) fail("EXISTS", `YAML file already exists: ${file}`);
      const after = await writeDocument(file, value);
      return { command: "create", file, changed: true, digest: after.digest };
    },
    { createParent: true },
  );
}

export async function updateYamlFile(filePath, expectedDigest, sets) {
  const file = absolutePath(filePath);
  if (!Array.isArray(sets) || sets.length === 0) fail("MISSING_SET", "At least one YAML update is required.");
  return withFileLock(file, async () => {
    const before = await readDocument(file);
    assertExpectedDigest(before.digest, expectedDigest);
    let value = cloneValue(before.value);
    for (const { pointer, value: replacement } of sets) {
      value = setAt(value, pointer, cloneValue(replacement));
    }
    if (deepEqual(before.value, value)) return mutationResult("update", file, before, before, false);
    const after = await writeDocument(file, value);
    return mutationResult("update", file, before, after, true);
  });
}

export async function appendYamlFile(
  filePath,
  expectedDigest,
  pointer,
  entry,
  { idField = "id", id = undefined } = {},
) {
  const file = absolutePath(filePath);
  if (!idField || typeof idField !== "string") fail("INVALID_ID_FIELD", "An append id field is required.");
  rejectUnsafeKey(idField);
  return withFileLock(file, async () => {
    const before = await readDocument(file);
    assertExpectedDigest(before.digest, expectedDigest);
    const value = cloneValue(before.value);
    const list = getAt(value, pointer);
    if (!Array.isArray(list)) fail("NOT_AN_ARRAY", `Append path is not an array: ${pointer}`);
    if (entry === null || typeof entry !== "object" || Array.isArray(entry)) {
      fail("INVALID_ENTRY", "Append entry must be a YAML mapping/object.");
    }

    const candidate = cloneValue(entry);
    if (id !== undefined) {
      if (candidate[idField] === undefined) candidate[idField] = id;
      if (!deepEqual(candidate[idField], id)) {
        fail("ID_MISMATCH", `Entry ${idField} does not match --id.`);
      }
    }
    const entryId = candidate[idField];
    if (entryId === undefined || entryId === null || entryId === "") {
      fail("APPEND_ID_REQUIRED", `Append entry must contain a non-empty ${idField}.`);
    }

    const existing = list.find((item) => item && typeof item === "object" && deepEqual(item[idField], entryId));
    if (existing !== undefined) {
      if (deepEqual(existing, candidate)) return mutationResult("append", file, before, before, false);
      fail("APPEND_CONFLICT", `An entry with ${idField}=${String(entryId)} already exists with different content.`, {
        id_field: idField,
        id: entryId,
      });
    }

    list.push(candidate);
    const after = await writeDocument(file, value);
    return mutationResult("append", file, before, after, true);
  });
}

export async function readYamlFile(filePath, pointer = undefined) {
  const file = absolutePath(filePath);
  const document = await readDocument(file);
  return pointer === undefined ? document : { ...document, value: getAt(document.value, pointer) };
}

export async function verifyYamlFile(filePath) {
  const document = await readDocument(absolutePath(filePath));
  return { valid: true, file: document.file, digest: document.digest };
}

export async function unlockYamlFile(filePath, force = false) {
  const file = absolutePath(filePath);
  if (!force) fail("FORCE_REQUIRED", "Unlock requires --force after confirming no YAML writer is active.");
  const lockDirectory = `${file}.lock`;
  if (!existsSync(lockDirectory)) return { command: "unlock", file, changed: false };
  await rm(lockDirectory, { recursive: true, force: false });
  return { command: "unlock", file, changed: true };
}

export function cloneValue(value) {
  return structuredClone(value);
}
