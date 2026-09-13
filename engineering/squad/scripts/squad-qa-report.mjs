#!/usr/bin/env bun

import { runRoleReportCli } from "./_role-report-cli.mjs";

const config = {
  role: "squad-qa",
  logPath: "/incremental_qa_log",
  usage: `Usage:
  squad-qa-report.mjs create --file <path> --data <json|yaml|@file|->
  squad-qa-report.mjs update --file <path> --expect-digest <sha256:...> --set <json-pointer>=<value> [...]
  squad-qa-report.mjs append --file <path> --expect-digest <sha256:...> --entry <json|yaml|@file|-> [--id-field <field>] [--id <value>]
  squad-qa-report.mjs read --file <path> [--path <json-pointer>] [--format yaml|json]
  squad-qa-report.mjs digest --file <path>
  squad-qa-report.mjs verify --file <path>
  squad-qa-report.mjs unlock --file <path> --force

This QA-only entrypoint writes only a squad-qa report and its incremental QA
log. It never writes host lifecycle state.\n`,
};

export async function main(argv = process.argv.slice(2)) {
  return runRoleReportCli(argv, config);
}

if (import.meta.main) await main();
