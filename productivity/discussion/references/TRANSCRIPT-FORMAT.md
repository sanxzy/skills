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

For a custom or free-form user answer, use a verbatim block instead of the compact answer line:

````markdown
AGENT-Q<N>: <question from the agent>

Recommended answer: <recommended answer>
Rationale: <brief rationale>

Answer: Custom answer (verbatim)

```
<the user's exact answer, unchanged>
```
````

The four-backtick fence is only the transcript wrapper; the three-backtick lines belong to the user's answer and must be copied exactly. Use an even longer outer fence when the answer contains a longer backtick run.

## Rules

- Write the transcript in English, translating questions and answers from the discussion language when necessary. The surrounding labels and agent-authored text remain English, but a user's custom/free-form answer is an explicit exception and must remain in its original form inside its verbatim block.
- Translate faithfully: preserve the user's decisions, reasoning, constraints, uncertainty, and important nuances without adding meaning.
- For every custom or free-form user answer, including a custom answer submitted through the question tool, copy the exact response into the transcript. Preserve the original language, spelling, punctuation, capitalization, line breaks, blank lines, indentation, Markdown syntax, code, tables, Mermaid or ASCII diagrams, and other meaningful whitespace. Do not translate, summarize, paraphrase, correct, normalize, trim, rewrap, or interpret the verbatim content.
- Label a custom answer `Answer: Custom answer (verbatim)` and place the unchanged response in a fenced block. Choose an outer fence longer than any backtick run in the response, and do not add text inside that block. The verbatim block is authoritative; any English explanation must be outside it and must never replace or alter it.
- Do not convert a user-provided diagram or flow into Mermaid or another format. The Mermaid rule below applies only when the agent creates a new diagram.
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
