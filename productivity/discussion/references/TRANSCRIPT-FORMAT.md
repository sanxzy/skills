# Transcript Format

The discussion transcript captures every question and answer in chronological order. It lives at `_xzy-ai/discussion/<topic>/transcript.md` and is the single source of truth for what has been decided.

## Entry Format

Each entry follows one of these patterns. `<N>` is the shared sequential question number across both participants:

```
USER-Q<N>: <question from the user>

Answer: <answer title> - <honest answer from the agent>

AGENT-Q<N>: <question from the agent>

Recommended answer: <recommended answer>
Rationale: <brief rationale>

Answer: <answer title> - <answer from the user>
```

For a custom or free-form user answer, use a compact English answer instead of copying the prose verbatim:

````markdown
AGENT-Q<N>: <question from the agent>

Recommended answer: <recommended answer>
Rationale: <brief rationale>

Answer: Custom answer - <compact English rewrite preserving the user's complete meaning>

<each user-provided diagram, if any, copied exactly as supplied>
````

The compact rewrite may shorten prose, but it must retain every decision, requirement, constraint, rationale, uncertainty, dependency, exception, and other context that could affect the outcome. If the answer contains a diagram, preserve the diagram in its original position and copy its content and formatting exactly; preserve its original fence when it has one. Do not add transcript text inside the diagram.

## Rules

- Write the transcript in English, translating questions and answers from the discussion language when necessary. This includes custom/free-form answers submitted directly or through the question tool.
- Translate faithfully: preserve the user's decisions, reasoning, constraints, uncertainty, and important nuances without adding meaning. For a long or comprehensive custom answer, compact the prose only when all of that context remains explicit; compactness must never become a lossy summary.
- For every custom or free-form user answer, translate its prose into English and rewrite it compactly when appropriate. Do not copy prose verbatim by default, and do not add, infer, omit, correct, normalize, or reinterpret meaning. Preserve code, commands, identifiers, formulas, tables, and other literal artifacts unchanged.
- Label a custom answer `Answer: Custom answer` and record the compact English rewrite. Do not label it `(verbatim)` and do not place the prose in a verbatim block.
- If a user answer contains a diagram or flow, copy that diagram exactly as supplied. Do not translate its labels, redraw it, change its syntax, normalize its whitespace, reformat it, or convert it to Mermaid or another format. Keep the original language, content, formatting, and relative position; only prose outside the diagram may be translated or compacted. The Mermaid rule below applies only when the agent creates a new diagram.
- Maintain the transcript in chronological order. After each response, immediately append the question and answer to the transcript.
- Prefix each question with `USER-Q<N>` when the user asks it and with `AGENT-Q<N>` when the agent asks it. The corresponding `Answer` must come from the other participant.
- For `USER-Q<N>`, omit `Recommended answer` and `Rationale`; the agent's task is to provide an answer that is correct, honest, faithful, and factual, directly addressing the user's question without steering toward a predetermined answer.
- For `AGENT-Q<N>`, include `Recommended answer` and `Rationale` before recording the user's answer. Ground the recommendation in verified facts and available evidence, not assumptions; state uncertainty when facts are incomplete.
- Number questions sequentially starting from 1 using one shared sequence for user and agent questions.
- The answer title should be a concise label for the decision or preference expressed.
- The detailed explanation should capture the reasoning, context, and any nuances the user provided.
- When an `outcome` input is provided, record it in the first applicable entry and preserve how it guided the discussion. If the outcome was clarified, refined, or discovered during the discussion, record that progression and the final agreed wording.
- Record explicit deferrals and the final confirmation as ordinary sequential Q&A entries so the transcript remains the source of truth for the agreed outcome.
- Only ask one question at a time. Never ask multiple questions in a single message.
- Use mermaid diagram format when need to create any diagrams/flows.
