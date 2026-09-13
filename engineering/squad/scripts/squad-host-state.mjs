#!/usr/bin/env bun

import {
  appendYamlFile,
  createYamlFile,
  readYamlFile,
  unlockYamlFile,
  updateYamlFile,
  verifyYamlFile,
} from "./_yaml-io.mjs";
import { formatValue, parseSetOptions, readValueSpec, requireOption, runCli } from "./_cli.mjs";

const usage = `Usage:
  squad-host-state.mjs create --file <path> --data <json|yaml|@file|->
  squad-host-state.mjs update --file <path> --expect-digest <sha256:...> --set <json-pointer>=<value> [...]
  squad-host-state.mjs append --file <path> --expect-digest <sha256:...> --path <json-pointer> --entry <json|yaml|@file|-> [--id-field <field>] [--id <value>]
  squad-host-state.mjs read --file <path> [--path <json-pointer>] [--format yaml|json]
  squad-host-state.mjs digest --file <path>
  squad-host-state.mjs verify --file <path>
  squad-host-state.mjs unlock --file <path> --force

This host-only entrypoint mutates canonical run/work-unit state, operations,
transitions, and host-owned indexes. It does not authorize lifecycle actions
or replace host schema validation.\n`;

export async function main(argv = process.argv.slice(2)) {
  return runCli(argv, {
    usage,
    commands: {
      create: async (options) =>
        createYamlFile(requireOption(options, "file"), await readValueSpec(requireOption(options, "data"), "--data")),
      update: async (options) =>
        updateYamlFile(
          requireOption(options, "file"),
          requireOption(options, "expectDigest", "expect-digest"),
          await parseSetOptions(options),
        ),
      append: async (options) =>
        appendYamlFile(
          requireOption(options, "file"),
          requireOption(options, "expectDigest", "expect-digest"),
          requireOption(options, "path"),
          await readValueSpec(requireOption(options, "entry"), "--entry"),
          { idField: options.idField ?? "id", id: options.id },
        ),
      read: async (options) => {
        const result = await readYamlFile(requireOption(options, "file"), options.path);
        return formatValue(result.value, options.format ?? "yaml");
      },
      digest: async (options) => (await readYamlFile(requireOption(options, "file"))).digest,
      verify: async (options) => verifyYamlFile(requireOption(options, "file")),
      unlock: async (options) => unlockYamlFile(requireOption(options, "file"), options.force === true),
    },
  });
}

if (import.meta.main) await main();
