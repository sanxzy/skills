#!/usr/bin/env bun

import { runRoleReportCli } from "./_role-report-cli.mjs";

const config = {
  role: "squad-reviewer",
  logPath: "/incremental_review_log",
  usage: `Usage:
  squad-reviewer-report.mjs create --file <path> --data <json|yaml|@file|->
  squad-reviewer-report.mjs update --file <path> --expect-digest <sha256:...> --set <json-pointer>=<value> [...]
  squad-reviewer-report.mjs append --file <path> --expect-digest <sha256:...> --entry <json|yaml|@file|-> [--id-field <field>] [--id <value>]
  squad-reviewer-report.mjs read --file <path> [--path <json-pointer>] [--format yaml|json]
  squad-reviewer-report.mjs digest --file <path>
  squad-reviewer-report.mjs verify --file <path>
  squad-reviewer-report.mjs unlock --file <path> --force

This reviewer-only entrypoint writes only a squad-reviewer report and its
incremental review log. It never writes host lifecycle state.\n`,
};

export async function main(argv = process.argv.slice(2)) {
  return runRoleReportCli(argv, config);
}

if (import.meta.main) await main();
