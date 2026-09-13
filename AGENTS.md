# AGENTS.md

Xzy Skills is a repository of composable agent skills. Skills are organized by responsibility rather than kept in one flat root directory.

## Responsibility-based structure

```text
architecting/                  Architecture and design-system guidance
  generate-architecture/
  generate-design-md/
engineering/                   Direct implementation workflows
  implement/
general/                       Repository and agent utilities
  install-bundled-agents/
media/                         Visual, story, and image-prompt workflows
  canvas-design/
  character-design/
  story-page/
  storyboard/
office/                        Office-document workflows
  docx/
  pdf/
  pptx/
  xlsx/
planning/
  v1/                           Feature → spec → plan workflow
    generate-features/
    generate-specs/
    generate-plan/
  v2/                           Proposal → ticket workflow
    proposal/
    ticket/
productivity/                  Conversation and learning workflows
  discussion/
  teach/
```

Each skill lives at `<responsibility>/<skill-name>/` or, for a versioned track, `<responsibility>/<version>/<skill-name>/`, and contains a `SKILL.md`. A skill may also contain:

```text
_agents/       Bundled subagents used by the skill
agents/        Agent-platform metadata such as openai.yaml
references/    Supporting contracts and workflow references
scripts/       Skill-owned executable helpers
examples/      Example artifacts or inputs
```

These directories are optional. Keep skill-owned files inside the skill directory; do not create a second flat copy at the repository root.

## Skill conventions

- `SKILL.md` is the skill's source of truth and must declare the skill name in frontmatter.
- The frontmatter `name` must match the skill directory name.
- Root-level documentation must use the responsibility-based path when linking to a skill.
- Planning generations are intentionally separated: `planning/v1/` contains the feature/spec/plan workflow, while `planning/v2/` contains the proposal/ticket workflow.
- The public skill name used by installers is the `SKILL.md` frontmatter name, not the full filesystem path.

## Agent naming conventions

- Bundled agents use stable, role-oriented kebab-case names.
- Agent name = filename without the `.md` extension = the `name:` frontmatter field when frontmatter is present.
- Do not add an `-agent` suffix to agent names.
- Keep agent names unambiguous across the repository; use a skill or role prefix when necessary.

When adding or moving a skill, update the responsibility map in this file and the catalog in `README.md` in the same change. Verify that every documented path exists and that no removed skill remains in the public catalog.
