---
name: discussion
version: 0.0.1
description: Discussion with user relentlessly about every aspect of this until we reach a shared understanding.
---

# Discussion Skill

Conduct a thorough, decision-driven interview until we reach a shared understanding of the topic.

## Communication Defaults

- Understand and absorb the language the user uses, including mixed-language messages where possible.
- Continue the discussion in the same language the user is using unless they request another language.
- Use simple words and explanations suitable for a high-school reading level. Avoid unnecessary technical terms; explain any technical term that is needed.
- When a topic is difficult or abstract, use a clear analogy when it helps the user reason about or understand it.
- Write the final discussion transcript in English. Translate the discussion faithfully while preserving the user's decisions, reasoning, constraints, and important nuances.

## Modules

- [INTERVIEW-PROCESS.md](./references/INTERVIEW-PROCESS.md) — Interview workflow, question rules, and completion criteria.
- [TRANSCRIPT-FORMAT.md](./references/TRANSCRIPT-FORMAT.md) — Transcript file format and storage specification.

## Available Agents

The `discussion-brainstormer` agent is available for use when the discussion reaches a point where no further meaningful progress can be made. The skill does not assume how or whether this agent is installed — it only offers the user the option to invoke it via the question tool or equivalent mechanism.
