#!/usr/bin/env node

/**
 * install-bundled-agents.mjs
 *
 * Scans bundled agent files from local skills and installs them into a target
 * directory with mode-specific frontmatter modifications.
 *
 * Usage:
 *   node install-bundled-agents.mjs --target-dir <path> [--install-mode <add|update>]
 *   node install-bundled-agents.mjs --target-dir <path> --model <model> [--install-mode <add|update>]
 *   node install-bundled-agents.mjs --target-dir <path> --discover-models
 *
 * Installation modes:
 *   add    — Install agents into the target directory. Existing files may be
 *            updated or skipped based on content comparison. (default)
 *   update — Delete the entire target directory, recreate it, then perform a
 *            fresh installation of all bundled agents.
 *
 * Frontmatter modes (determined internally from target path):
 *   - Standard (target is NOT .opencode/agents/): copies agents, removes
 *     `mode: subagent` from frontmatter, leaves model fields untouched.
 *   - Opencode (target IS .opencode/agents/): copies agents, adds or updates
 *     the `model` field in frontmatter to the selected model. Preserves
 *     all other frontmatter fields unchanged, including `mode: subagent`.
 *
 * Environment variables:
 *   SKILLS_DIR   — colon-separated extra skill search roots
 *   PROJECT_ROOT — project root directory (default: cwd)
 */

import { readdirSync, existsSync, mkdirSync, rmSync, cpSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join, resolve, normalize } from "node:path";
import { execSync } from "node:child_process";

// ── Argument parsing ──────────────────────────────────────────────────

const args = process.argv.slice(2);
let targetDir = null;
let model = null;
let discoverModelsFlag = false;
let installMode = "add";

for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case "--target-dir":
      targetDir = args[++i] || null;
      break;
    case "--model":
      model = args[++i] || null;
      break;
    case "--discover-models":
      discoverModelsFlag = true;
      break;
    case "--install-mode":
      installMode = (args[++i] || "add").toLowerCase();
      break;
  }
}

if (installMode !== "add" && installMode !== "update") {
  console.error(`ERROR: Invalid --install-mode "${installMode}". Must be "add" or "update".`);
  process.exit(1);
}

// ── Configuration ─────────────────────────────────────────────────────

const PROJECT_ROOT = normalize(process.env.PROJECT_ROOT || process.cwd());

function resolvePath(p) {
  if (p.startsWith("~")) return join(process.env.HOME, p.slice(1));
  if (p.startsWith("./") || p.startsWith("../")) return resolve(PROJECT_ROOT, p);
  return p;
}

targetDir = targetDir ? resolvePath(targetDir) : null;

// ── Helpers ───────────────────────────────────────────────────────────

function isOpencodeTarget(dir) {
  // Normalize to check trailing path component
  const normalized = dir.replace(/\/+$/, "");
  return normalized.endsWith("/.opencode/agents") || normalized.endsWith("\\.opencode\\agents");
}

function getSourceRoots() {
  const roots = [
    join(PROJECT_ROOT, ".agents", "skills"),
    PROJECT_ROOT,
  ];
  if (process.env.SKILLS_DIR) {
    for (const d of process.env.SKILLS_DIR.split(":")) {
      const dir = d.trim();
      if (dir) roots.push(dir);
    }
  }
  return roots;
}

function findAgentFiles(roots) {
  const seen = new Map();
  const agents = [];
  let duplicatesSkipped = 0;

  for (const root of roots) {
    let skillDirs;
    try {
      skillDirs = readdirSync(root, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of skillDirs) {
      if (!entry.isDirectory()) continue;
      const agentsDir = join(root, entry.name, "_agents");
      let agentFiles;
      try {
        agentFiles = readdirSync(agentsDir, { withFileTypes: true });
      } catch {
        continue; // no _agents/ in this skill
      }
      for (const agentFile of agentFiles) {
        if (!agentFile.name.endsWith(".md")) continue;
        const name = agentFile.name;
        if (seen.has(name)) {
          duplicatesSkipped++;
          continue; // first source root wins
        }
        seen.set(name, join(agentsDir, name));
        agents.push({ name, source: join(agentsDir, name) });
      }
    }
  }

  return { agents, duplicatesSkipped };
}

/**
 * Validate a target directory path before destructive operations.
 * Exits the process on unsafe paths.
 */
function validateTargetPath(target) {
  if (!target || target === "/") {
    console.error("ERROR: Refusing to operate on root directory '/'.");
    process.exit(1);
  }

  const homeDir = process.env.HOME;
  if (homeDir && normalize(target) === normalize(homeDir)) {
    console.error("ERROR: Refusing to operate on home directory.");
    process.exit(1);
  }

  try {
    const stats = statSync(target);
    if (!stats.isDirectory()) {
      console.error(`ERROR: Target path exists but is not a directory: ${target}`);
      process.exit(1);
    }
  } catch {
    // Path does not exist — that's fine, it will be created
  }
}

/**
 * Parse an agent file frontmatter section.
 * Returns { content: string, body: string, startIndex, endIndex }.
 * If no frontmatter, content is empty and startIndex/endIndex are 0.
 */
function parseFrontmatter(filePath) {
  const text = readFileSync(filePath, "utf-8");
  const lines = text.split("\n");
  if (lines.length === 0 || lines[0].trim() !== "---") {
    return { content: "", body: text, startIndex: 0, endIndex: 0, text };
  }

  let endIdx = 1;
  while (endIdx < lines.length && lines[endIdx].trim() !== "---") {
    endIdx++;
  }
  if (endIdx >= lines.length) {
    // Unterminated frontmatter — treat whole file as body
    return { content: "", body: text, startIndex: 0, endIndex: 0, text };
  }

  const fmLines = lines.slice(1, endIdx);
  const body = lines.slice(endIdx + 1).join("\n");
  return {
    content: fmLines.join("\n"),
    body: body,
    startIndex: 1,
    endIndex: endIdx,
    text,
    fmLines,
  };
}

function rebuildFile(fmLines, body) {
  return "---\n" + fmLines.join("\n") + "\n---\n" + body;
}

/**
 * Remove `mode: subagent` line from frontmatter lines.
 */
function stripModeSubagent(fmLines) {
  return fmLines.filter((line) => !/^mode:\s*subagent\b/.test(line.trim()));
}

/**
 * Add or update the `model` field in frontmatter lines.
 */
function setModelField(fmLines, modelName) {
  let found = false;
  const result = fmLines.map((line) => {
    if (/^model:/.test(line.trim())) {
      found = true;
      return `model: ${modelName}`;
    }
    return line;
  });
  if (!found) {
    result.push(`model: ${modelName}`);
  }
  return result;
}

// ── Opencode model discovery ──────────────────────────────────────────

function discoverModels() {
  try {
    const output = execSync("opencode models | grep 9router", {
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "pipe"],
      timeout: 15000,
    });
    const models = output
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0 && /9router/i.test(l));
    return models;
  } catch {
    return [];
  }
}

// ── Directory lifecycle ───────────────────────────────────────────────

function prepareTargetDirectory(target, mode) {
  validateTargetPath(target);

  if (mode === "add") {
    mkdirSync(target, { recursive: true });
    return;
  }

  // mode === "update"

  if (existsSync(target)) {
    console.log(`CLEAR  Removing existing directory: ${target}`);
    rmSync(target, { recursive: true, force: true });
  }

  console.log(`CREATE Creating directory: ${target}`);
  mkdirSync(target, { recursive: true });
}

// ── Installation ──────────────────────────────────────────────────────

function install(agents, target, fmMode, selectedModel, duplicatesSkipped = 0) {
  const result = {
    targetDirectory: target,
    fmMode,
    installMode,
    model: selectedModel || null,
    skillsScanned: 0,
    discovered: agents.length,
    duplicatesSkipped,
    installed: 0,
    updated: 0,
    skipped: 0,
    failed: 0,
    failures: [],
  };

  // Count skills by unique parent dirs
  const parentDirs = new Set(agents.map((a) => join(a.source, "..", "..")));
  result.skillsScanned = parentDirs.size;

  for (const agent of agents) {
    const dest = join(target, agent.name);

    let isUpdate = false;

    if (existsSync(dest)) {
      const existing = readFileSync(dest, "utf-8");
      const source = readFileSync(agent.source, "utf-8");
      if (existing === source) {
        // For identical files in opencode mode, still need to ensure model
        // field is correct. Apply post-processing directly.
        // Even for identical files, apply frontmatter modifications so that
        // previously-installed files (from an older script or manual copy) get
        // their frontmatter corrected on re-run.
        const parsed = parseFrontmatter(dest);
        if (parsed.fmLines) {
          try {
            let modified;
            if (fmMode === "opencode") {
              modified = setModelField(parsed.fmLines, selectedModel);
            } else {
              modified = stripModeSubagent(parsed.fmLines);
            }
            const newText = rebuildFile(modified, parsed.body);
            writeFileSync(dest, newText, "utf-8");
            result.updated++;
          } catch (err) {
            result.failed++;
            result.failures.push({ name: agent.name, reason: `post-processing failed: ${err.message}` });
          }
        } else {
          result.skipped++;
        }
        continue;
      }
      isUpdate = true;
    }

    // Copy the agent file
    try {
      cpSync(agent.source, dest, { force: true });
    } catch (err) {
      result.failed++;
      result.failures.push({ name: agent.name, reason: err.message });
      continue;
    }

    // Apply frontmatter modifications
    const parsed = parseFrontmatter(dest);
    if (!parsed.fmLines) {
      // No frontmatter — write the original content unchanged
      // (shouldn't happen for well-formed agent files, but guard against it)
      if (isUpdate) {
        result.updated++;
      } else {
        result.installed++;
      }
      continue;
    }

    let modifiedLines;

    if (fmMode === "opencode") {
      modifiedLines = setModelField(parsed.fmLines, selectedModel);
    } else {
      modifiedLines = stripModeSubagent(parsed.fmLines);
    }

    const newContent = rebuildFile(modifiedLines, parsed.body);
    try {
      writeFileSync(dest, newContent, "utf-8");
    } catch (err) {
      result.failed++;
      result.failures.push({ name: agent.name, reason: `post-processing write failed: ${err.message}` });
      continue;
    }

    // Classify
    if (isUpdate) {
      result.updated++;
    } else {
      result.installed++;
    }
  }

  return result;
}

// ── Report ────────────────────────────────────────────────────────────

function printSummary(result) {
  console.log(`Target directory:   ${result.targetDirectory}`);
  console.log(`Install mode:       ${result.installMode}`);
  console.log(`Frontmatter mode:   ${result.fmMode}`);
  if (result.model) console.log(`Selected model:     ${result.model}`);
  console.log(`Skills scanned:     ${result.skillsScanned}`);
  console.log(`Bundled agents:     ${result.discovered}`);
  if (result.duplicatesSkipped > 0) {
    console.log(`Duplicates skipped: ${result.duplicatesSkipped}`);
  }
  console.log(`Installed:          ${result.installed}`);
  console.log(`Updated:            ${result.updated}`);
  console.log(`Skipped (same):     ${result.skipped}`);
  console.log(`Failures:           ${result.failed}`);
  if (result.failures.length > 0) {
    for (const f of result.failures) {
      console.log(`  - ${f.name}: ${f.reason}`);
    }
  }
}

// ── Main ──────────────────────────────────────────────────────────────

function main() {
  if (!targetDir) {
    console.error("ERROR: --target-dir is required. Usage:");
    console.error("  node install-bundled-agents.mjs --target-dir <path> [--install-mode add|update] [--model <model>|--discover-models]");
    process.exit(1);
  }

  const opencode = isOpencodeTarget(targetDir);

  // Discover-models mode: only valid for opencode targets
  if (discoverModelsFlag) {
    if (!opencode) {
      console.log("[]");
      process.exit(0);
    }
    const models = discoverModels();
    if (models.length === 0) {
      console.error("ERROR: No 9router models found. Ensure `opencode models` lists 9router models.");
      process.exit(1);
    }
    // Output as JSON for machine parsing
    console.log(JSON.stringify(models));
    process.exit(0);
  }

  // For opencode mode, model is required
  if (opencode && !model) {
    console.error("ERROR: --model is required for .opencode/agents/ targets.");
    console.error("Run with --discover-models first to list available models.");
    process.exit(1);
  }
  if (!opencode && model) {
    console.warn("WARN  --model provided for non-opencode target; value ignored.");
  }

  const fmMode = opencode ? "opencode" : "standard";

  // Prepare target directory (delete + recreate in update mode)
  prepareTargetDirectory(targetDir, installMode);

  const roots = getSourceRoots();
  const { agents, duplicatesSkipped } = findAgentFiles(roots);

  if (agents.length === 0) {
    console.log("No bundled agent files found.");
    console.log(`Source roots scanned: ${roots.join(", ")}`);
    process.exit(0);
  }

  const result = install(agents, targetDir, fmMode, model, duplicatesSkipped);
  printSummary(result);

  if (result.failed > 0) {
    process.exit(1);
  }
}

main();
