import { formatValue, parseSetSpec, readValueSpec, YamlToolError } from "./_yaml-io.mjs";

export function parseArgs(argv) {
  const [command, ...tokens] = argv;
  const options = { set: [] };
  if (!command || command === "--help" || command === "help") return { command: "help", options };

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (token === "--help") return { command: "help", options };
    if (!token.startsWith("--")) {
      throw new YamlToolError("INVALID_ARGUMENT", `Unexpected argument: ${token}`);
    }
    const key = token.slice(2).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
    if (key === "force") {
      options.force = true;
      continue;
    }
    const value = tokens[++index];
    if (value === undefined || value.startsWith("--")) {
      throw new YamlToolError("MISSING_ARGUMENT", `Value required for --${token.slice(2)}.`);
    }
    if (key === "set") options.set.push(value);
    else options[key] = value;
  }
  return { command, options };
}

export function requireOption(options, key, flag = key) {
  if (options[key] === undefined) {
    throw new YamlToolError("MISSING_ARGUMENT", `--${flag} is required.`);
  }
  return options[key];
}

export async function parseSetOptions(options) {
  const sets = [];
  for (const spec of options.set) {
    const { pointer, valueSpec } = parseSetSpec(spec);
    sets.push({ pointer, value: await readValueSpec(valueSpec, `--set ${pointer}`) });
  }
  return sets;
}

export function printResult(result) {
  if (typeof result === "string") {
    process.stdout.write(result.endsWith("\n") ? result : `${result}\n`);
  } else {
    process.stdout.write(`${JSON.stringify(result)}\n`);
  }
}

export function createUsage(lines) {
  return `${lines.join("\n")}\n`;
}

export async function runCli(argv, { usage, commands }) {
  try {
    const { command, options } = parseArgs(argv);
    if (command === "help") {
      printResult(usage);
      return;
    }
    const handler = commands[command];
    if (!handler) throw new YamlToolError("INVALID_COMMAND", `Unknown command: ${command}`);
    printResult(await handler(options));
  } catch (error) {
    const payload = {
      error: error.code ?? "UNEXPECTED_ERROR",
      message: error.message,
      ...(error.details ? { details: error.details } : {}),
    };
    console.error(JSON.stringify(payload));
    process.exitCode = 1;
  }
}

export { formatValue, readValueSpec };
