import {
  createRoleReport,
  appendRoleReport,
  readRoleReport,
  unlockYamlFile,
  updateRoleReport,
  verifyRoleReport,
} from "./_role-report.mjs";
import { formatValue, readValueSpec, YamlToolError } from "./_yaml-io.mjs";
import { parseSetOptions, requireOption, runCli } from "./_cli.mjs";

export function roleReportCommands({ role, logPath }) {
  return {
    create: async (options) =>
      createRoleReport(
        requireOption(options, "file"),
        await readValueSpec(requireOption(options, "data"), "--data"),
        role,
        logPath,
      ),
    update: async (options) =>
      updateRoleReport(
        requireOption(options, "file"),
        requireOption(options, "expectDigest", "expect-digest"),
        await parseSetOptions(options),
        role,
      ),
    append: async (options) => {
      if (options.path !== undefined) {
        throw new YamlToolError("INVALID_ARGUMENT", `This role appends only to ${logPath}; do not pass --path.`);
      }
      return appendRoleReport(
        requireOption(options, "file"),
        requireOption(options, "expectDigest", "expect-digest"),
        logPath,
        await readValueSpec(requireOption(options, "entry"), "--entry"),
        role,
        { idField: options.idField ?? "id", id: options.id },
      );
    },
    read: async (options) => {
      const result = await readRoleReport(requireOption(options, "file"), role, options.path);
      return formatValue(result.value, options.format ?? "yaml");
    },
    digest: async (options) => (await readRoleReport(requireOption(options, "file"), role)).digest,
    verify: async (options) => verifyRoleReport(requireOption(options, "file"), role),
    unlock: async (options) => unlockYamlFile(requireOption(options, "file"), options.force === true),
  };
}

export async function runRoleReportCli(argv, config) {
  return runCli(argv, {
    usage: config.usage,
    commands: roleReportCommands(config),
  });
}
