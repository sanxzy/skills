#!/usr/bin/env bun

import { runRoleReportCli } from "./_role-report-cli.mjs";

const config = {
  role: "squad-analysis-reconciliation",
  logPath: "/incremental_analysis_log",
  usage: `Usage:
  squad-analysis-report.mjs create --file <path> --data <json|yaml|@file|->
  squad-analysis-report.mjs update --file <path> --expect-digest <sha256:...> --set <json-pointer>=<value> [...]
  squad-analysis-report.mjs append --file <path> --expect-digest <sha256:...> --entry <json|yaml|@file|-> [--id-field <field>] [--id <value>]
  squad-analysis-report.mjs read --file <path> [--path <json-pointer>] [--format yaml|json]
  squad-analysis-report.mjs digest --file <path>
  squad-analysis-report.mjs verify --file <path>
  squad-analysis-report.mjs unlock --file <path> --force

This analysis-only entrypoint writes only a squad-analysis-reconciliation
report and its incremental analysis log. It never writes shared state.\n`,
};

export async function main(argv = process.argv.slice(2)) {
  return runRoleReportCli(argv, config);
}

if (import.meta.main) await main();
