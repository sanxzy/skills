# AGENTS.md

Skills development repository. Develops, stores, and manages custom skills (agent workflows) and their bundled subagents.

## Structure

```
<skill-name>/                    # Skill source directory
  SKILL.md                       # Skill definition (frontmatter + instructions)
  _agents/                       # Bundled subagents for this skill
  agents/                        # Agent convention output directory (openai.yaml)
  references/                    # Format/reference specifications (CONTRACT-FORMAT.md, WORKFLOW-PROCESS.md, etc.)
```

## Agent Naming Conventions

- Each skill's agents use a unique prefix: `spec-` (generate-specs), `tix-` (generate-tickets), etc.
- No `-agent` suffix in agent names.
- Agent name = filename (without `.md` extension) = `name:` frontmatter field.
