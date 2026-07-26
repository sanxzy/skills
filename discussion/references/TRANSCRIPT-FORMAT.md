# Transcript Format

The discussion transcript captures every question and answer in chronological order. It lives at `_xzy-ai/discussion/<topic>/transcript.md` and is the single source of truth for what has been decided.

## Entry Format

Each entry follows this pattern:

```
Q<N>: <question>

Answer: <answer title> - <detailed explanation>
```

## Rules

- Maintain the transcript in chronological order. After each user response, immediately append the question and answer to the transcript.
- Number questions sequentially starting from 1.
- The answer title should be a concise label for the decision or preference expressed.
- The detailed explanation should capture the reasoning, context, and any nuances the user provided.
- Only ask one question at a time. Never ask multiple questions in a single message.
- For every question, provide a recommended answer along with a brief rationale to help guide the discussion.
- Use mermaid diagram format when need to create any diagrams/flows.
