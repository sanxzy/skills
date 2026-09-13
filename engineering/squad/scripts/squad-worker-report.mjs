#!/usr/bin/env bun

import { runRoleReportCli } from "./_role-report-cli.mjs";

const config = {
  role: "squad-worker",
  logPath: "/incremental_worker_log",
  usage: `Usage:
  squad-worker-report.mjs create --file <path> --data <json|yaml|@file|->
  squad-worker-report.mjs update --file <path> --expect-digest <sha256:...> --set <json-pointer>=<value> [...]
  squad-worker-report.mjs append --file <path> --expect-digest <sha256:...> --entry <json|yaml|@file|-> [--id-field <field>] [--id <value>]
  squad-worker-report.mjs read --file <path> [--path <json-pointer>] [--format yaml|json]
  squad-worker-report.mjs digest --file <path>
  squad-worker-report.mjs verify --file <path>
  squad-worker-report.mjs unlock --file <path> --force

This worker-only entrypoint writes only a squad-worker report and its
incremental worker log. It never writes host lifecycle state.\n`,
};

export async function main(argv = process.argv.slice(2)) {
  return runRoleReportCli(argv, config);
}

if (import.meta.main) await main();
