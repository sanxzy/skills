---
name: install-bundled-agents
version: 1.0.0
description: |
  Install every agent bundled with locally available skills into the user-chosen agents directory. Use when the user wants to "install bundled agents", "sync skill agents", "set up skill agents", or "install agents from skills". Prompts for the target directory; for opencode targets additionally prompts for a 9router model. Delegates all scanning, copying, frontmatter processing, and reporting to the bundled `install-bundled-agents.mjs` script. Idempotent — safe to run repeatedly.
---

Synchronize the user-chosen target agents directory with every agent bundled inside locally available skills.

All scanning, deduplication, copy, frontmatter modification, model discovery, directory lifecycle, and reporting logic lives in `scripts/install-bundled-agents.mjs` (bundled alongside this SKILL.md). The agent only orchestrates user interaction and invokes the script.

## Step 0 — Resolve the install target

Before scanning, **always** ask the user where to install the agents using `AskUserQuestion`. Do not skip this step; the target must be confirmed every run. Put the recommended option first, labelled `(Recommended)`. Include an open `Other` option for free-text paths.

Ask:

> "Where should bundled agents be installed?"

Suggested options:

- `<cwd>/.claude/agents/` *(Recommended)* — Claude Code agent convention.
- `<cwd>/.opencode/agents/` — opencode agent convention.
- `<cwd>/.agents/agents/` — portable agent convention used by other tooling.
- `Other` — any absolute or `<cwd>`-relative path the user types (e.g. `~/global-agents`, `packages/agents`, `/abs/path/agents`).

**Resolution rules:**

- `<cwd>` resolves to the current working directory at invocation time.
- Normalize the chosen path: expand `~` to the user's home, resolve `<cwd>` to the absolute path, and strip any trailing `/`.
- Verify the target is a writable directory path. If the user picks a path that does not exist, create it (no need to ask again). If the user picks a path that is a file, surface an error and re-ask.
- Honor the `INSTALL_TARGET` environment variable as a non-interactive override; when set, skip the question and use the value directly. Otherwise, always ask.

**Completion:** a single absolute target path is known — assign it to a variable so it can be passed to the script in the next step.

## Step 1 — Discover mode and invoke the script

The script path is `scripts/install-bundled-agents.mjs` in the same directory as this SKILL.md. Resolve it to an absolute path before invoking.

**Opencode target (path ends with `.opencode/agents/` or `.opencode/agents`):**

1. Run the script with `--discover-models` to retrieve available 9router models:
   ```bash
   node <script-path> --target-dir <target-path> --discover-models
   ```
2. The script outputs a JSON array of model names. Parse it. If no models are found, surface an error and stop.
3. Use `AskUserQuestion` to prompt the user to select one of the available models. Present the parsed models as mutually exclusive single-select options. Use the first result as the `(Recommended)` choice. Do **not** include a free-text "Other" option — the user must pick from the available models.
4. Once the user selects a model, invoke the script:
   ```bash
   node <script-path> --target-dir <target-path> --model <selected-model> --install-mode <add|update>
   ```
   The script adds or updates `model: <selected-model>` in every installed agent. All other frontmatter — including `mode: subagent` — is preserved unchanged.
5. The script prints the installation summary. Report it to the user.

**Standard target (anything else):**

1. Invoke the script directly (no model argument):
   ```bash
   node <script-path> --target-dir <target-path> --install-mode <add|update>
   ```
2. The script prints the installation summary. Report it to the user.

**Constraint:** The model discovery and selection prompt MUST only occur in opencode mode. The script and agent MUST NOT execute `opencode models | grep 9router` or prompt for a model in standard mode.

## Script reference

The `install-bundled-agents.mjs` script accepts:

| Argument | Description |
|----------|-------------|
| `--target-dir <path>` | **Required.** Target directory for agent files (absolute or project-relative, e.g. `./.claude/agents`). |
| `--install-mode <mode>` | Installation mode: `add` (default) or `update`. `add` patches into existing directory; `update` deletes and recreates the target directory before installing. |
| `--model <model>` | Model to set as the `model` frontmatter field in every installed agent (opencode mode only). |
| `--discover-models` | Discover and print available 9router models as JSON, then exit. |

The script respects these environment variables:

| Variable | Description |
|----------|-------------|
| `PROJECT_ROOT` | Project root directory (default: cwd). |
| `SKILLS_DIR` | Colon-separated extra skill search roots to include in addition to `.agents/skills/` and the project root. |

In `add` mode, the script is idempotent — re-running produces no changes when bundles are unchanged. In `update` mode, the target directory is cleaned first for a fresh installation. Every existing agent is either skipped (identical) or updated (differs), and never duplicated. Duplicate basenames across source roots are silently deduplicated (first source root wins); the `Duplicates skipped` count in the summary reports how many were omitted.

## Source roots scanned by the script

1. `.agents/skills/*/_agents/*.md` — bundled skills under `.agents/`
2. `<cwd>/*/_agents/*.md` — skills at the project root where `<skill>/_agents/` exists (excludes paths already under `.agents/skills/`)
3. Additional paths from `SKILLS_DIR` env var, if set

Only one level of nesting is scanned — subdirectories of `_agents/` are not traversed.
