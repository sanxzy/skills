#!/usr/bin/env bun

import { dirname, join } from "node:path";
import { YamlToolError } from "./_yaml-io.mjs";
import {
  buildExecutionManifest,
  generateHandoffFromManifest,
  prepareDispatch,
  preflightRun,
  reconcileAgent,
  resolveRunPath,
  resumeTicket,
  statusRun,
  commitUnitTransition,
  validateHandoffFile,
  verifyRun,
  writeExecutionManifest,
  bindAgent,
} from "./_squad-workflow.mjs";

const usage = `Usage:
  squad.mjs validate-handoff <handoff.yaml>
  squad.mjs manifest --run <run.yaml> --state <state.yaml> [--ticket <ticket.md>] [--role worker|reviewer] [--attempt N] [--output <manifest.yaml>]
  squad.mjs handoff --manifest <manifest.yaml> [--output <handoff.yaml>]
  squad.mjs prepare --run <run.yaml> --state <state.yaml> [--role worker|reviewer] [--output <manifest.yaml>] [--handoff <handoff.yaml>]
  squad.mjs dispatch --run <run.yaml> --state <state.yaml> [--role worker|reviewer] [--output <manifest.yaml>] [--handoff <handoff.yaml>]
  squad.mjs bind-agent <job-id> --operation <operation.yaml>
  squad.mjs preflight --run <run.yaml> | --run-dir <orchestration-dir>
  squad.mjs transition <work-unit-id> --state <state.yaml> | --run <run.yaml> --from <STATE> --to <STATE> --reason <text> [--operation <operation-id>]
  squad.mjs reconcile-agent <job-id> --state <state.yaml> [--operation <operation.yaml>] [--report <report.yaml>]
  squad.mjs resume-ticket <work-unit-id> --state <state.yaml> | --run <run.yaml> [--role worker|reviewer] [--strategy resume|replacement]
  squad.mjs status <run-id> [--run <run.yaml> | --run-dir <orchestration-dir>] [--ticket <work-unit-id>] [--explain]
  squad.mjs verify-run <run-id> [--run <run.yaml> | --run-dir <orchestration-dir>] [--final]

All commands are host-only. They validate and prepare durable artifacts; they
never spawn an agent, mutate the target branch, or delete retained evidence.
Use squad-host-state.mjs only for low-level expected-digest YAML primitives.
`;

function parseWorkflowArgs(argv) {
  const [command, ...tokens] = argv;
  if (!command || command === "help" || command === "--help") return { command: "help", positionals: [], options: {} };
  const positionals = [];
  const options = {};
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (token === "--help") return { command: "help", positionals: [], options: {} };
    if (!token.startsWith("--")) {
      positionals.push(token);
      continue;
    }
    const key = token.slice(2).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    if (["explain", "final", "force"].includes(key)) {
      options[key] = true;
      continue;
    }
    const value = tokens[++index];
    if (value === undefined || (value.startsWith("--") && value !== "-")) {
      throw new YamlToolError("MISSING_ARGUMENT", `Value required for --${token.slice(2)}.`);
    }
    options[key] = value;
  }
  return { command, positionals, options };
}

function requireOption(options, key, flag = key) {
  if (options[key] === undefined) throw new YamlToolError("MISSING_ARGUMENT", `--${flag} is required.`);
  return options[key];
}

function positional(positionals, index, label) {
  if (!positionals[index]) throw new YamlToolError("MISSING_ARGUMENT", `${label} is required.`);
  return positionals[index];
}

function printResult(result) {
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

async function manifestCommand(options) {
  const built = await buildExecutionManifest(options);
  const written = await writeExecutionManifest(built.manifest, built.manifestPath);
  return {
    command: "manifest",
    manifest_path: built.manifestPath,
    digest: written.digest,
    changed: written.changed,
    handoff_path: built.handoffPath,
    operation_path: built.manifest.artifact.operation_path,
    next_action: "PREPARE_DISPATCH",
  };
}

async function runCommand(argv) {
  const { command, positionals, options } = parseWorkflowArgs(argv);
  if (command === "help") return usage;
  switch (command) {
    case "validate-handoff": {
      const handoffPath = positional(positionals, 0, "handoff path");
      return validateHandoffFile(handoffPath);
    }
    case "manifest":
    case "generate-manifest":
      return manifestCommand(options);
    case "handoff": {
      const manifestPath = requireOption(options, "manifest");
      return generateHandoffFromManifest(manifestPath, options.output);
    }
    case "prepare":
    case "dispatch":
      return prepareDispatch({ ...options, runId: options.runId ?? undefined });
    case "bind-agent":
      return bindAgent({ ...options, position: positional(positionals, 0, "agent job ID") });
    case "preflight": {
      const runPath = await resolveRunPath(options, options.runId);
      const result = await preflightRun(runPath);
      if (!result.valid) throw new YamlToolError("PREFLIGHT_FAILED", `Run preflight failed: ${runPath}`, { issues: result.issues, checks: result.checks, run_id: result.run_id });
      return result;
    }
    case "transition": {
      const unitId = positional(positionals, 0, "work-unit ID");
      const transitionStatePath = options.state ?? join(dirname(await resolveRunPath(options, options.runId)), "work-units", unitId, "state.yaml");
      return commitUnitTransition({
        statePath: transitionStatePath,
        workUnitId: unitId,
        from: requireOption(options, "from"),
        to: requireOption(options, "to"),
        reason: requireOption(options, "reason"),
        operationId: options.operation,
      });
    }
    case "reconcile-agent":
      return reconcileAgent({ ...options, position: positional(positionals, 0, "agent job ID") });
    case "resume-ticket": {
      const unitId = positional(positionals, 0, "work-unit ID");
      const resumeStatePath = options.state ?? join(dirname(await resolveRunPath(options, options.runId)), "work-units", unitId, "state.yaml");
      return resumeTicket({ ...options, state: resumeStatePath, position: unitId });
    }
    case "status": {
      const runId = positional(positionals, 0, "run ID");
      const runPath = await resolveRunPath(options, runId);
      return statusRun(runPath, options);
    }
    case "verify-run": {
      const runId = positional(positionals, 0, "run ID");
      const runPath = await resolveRunPath(options, runId);
      const result = await verifyRun(runPath, options);
      if (!result.valid) throw new YamlToolError("RUN_VERIFICATION_FAILED", `Run verification failed: ${runPath}`, { issues: result.issues, run_id: result.run_id, final: result.final });
      return result;
    }
    default:
      throw new YamlToolError("INVALID_COMMAND", `Unknown command: ${command}`);
  }
}

export async function main(argv = process.argv.slice(2)) {
  try {
    const result = await runCommand(argv);
    if (typeof result === "string") process.stdout.write(result.endsWith("\n") ? result : `${result}\n`);
    else printResult(result);
    return result;
  } catch (error) {
    const payload = {
      error: error.code ?? "UNEXPECTED_ERROR",
      message: error.message,
      ...(error.details ? { details: error.details } : {}),
    };
    console.error(JSON.stringify(payload));
    process.exitCode = 1;
    return payload;
  }
}

if (import.meta.main) await main();
