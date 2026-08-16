---
name: discussion
version: 0.0.1
description: Conduct a thorough, decision-driven interview until we reach a shared understanding of the topic and a clear, agreed-upon outcome.
---

# Discussion Skill

Conduct a thorough, decision-driven interview until we reach a shared understanding of the topic and a clear, agreed-upon outcome.

## Recommended Input

- `outcome` (optional, recommended): The result the user wants the discussion to reach. When provided, treat it as the discussion's guiding target: use it to prioritize questions, test decisions against the intended result, and refine it when the discussion reveals a better-defined outcome.
- If `outcome` is missing or unclear, normally ask the user what outcome they want before exploring dependent decisions. This initial question may be skipped when the topic is explicitly exploratory, the outcome itself is what the discussion must discover, or the existing context already gives the discussion a clear direction.
- Skipping the initial outcome question does not remove the completion requirement: before finalizing, the discussion must establish and obtain confirmation of a clear, agreed-upon outcome.

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

The optional `discussion-brainstormer` agent can be used after all material decisions and dependencies have been addressed, before final confirmation, to check for gaps. The skill does not assume that the agent is installed; it offers the user the option to invoke it via the question tool or equivalent mechanism. If the agent is unavailable, continue to the final confirmation step without it.
