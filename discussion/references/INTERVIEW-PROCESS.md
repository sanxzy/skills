# Interview Process

Conduct a thorough, decision-driven interview until every material decision has been made or explicitly deferred, every dependency has been resolved or explicitly deferred, and a clear, agreed-upon outcome is confirmed.

## Recommended Input

- `outcome` (optional, recommended): The result the user wants the discussion to reach. When provided, use it to prioritize questions, evaluate decisions, and keep the interview directed toward the intended result.
- If `outcome` is missing or unclear, normally ask the user what outcome they want before exploring dependent decisions. This question may be skipped when the topic is explicitly exploratory, the outcome itself is what the discussion must discover, or the existing context already provides a clear direction.
- Skipping the initial outcome question does not remove the completion requirement: establish and explicitly confirm a clear, agreed-upon outcome before finalizing.

## Core Principles

- Detect and understand the language the user uses, including mixed-language messages where possible.
- Continue the discussion in the same language the user is using unless they request another language.
- Use simple language and explanations suitable for a high-school level. Avoid unnecessary technical terms, and explain any technical term that is needed.
- When a topic is difficult or abstract, provide a clear analogy when it helps the user reason about or understand the topic.
- Interview the user about every relevant aspect of the topic until every material decision has been made or explicitly deferred, every dependency has been resolved or explicitly deferred, and a clear, agreed-upon outcome is confirmed.
- When an `outcome` is provided, use it as the guiding target for the decision tree. Keep questions and recommendations relevant to that target, and surface any decision that would materially change it.
- Explore each branch of the decision tree systematically, resolving prerequisite decisions before moving to dependent ones.
- Ask only one question at a time, and wait for the user's response before asking the next question. Never ask multiple questions in a single message.
- For every question, provide a recommended answer along with a brief rationale to help guide the discussion.
- If a required piece of information is an objective fact that can be discovered by exploring the environment (such as the filesystem, repository, documentation, tools, or configuration), retrieve it yourself instead of asking the user. Finding facts is your job, never the user's.
- Only ask the user to make subjective decisions, preferences, trade-offs, or requirements that cannot be determined automatically.

## Completion Gate

Do not begin implementation or proceed with the requested task until the user explicitly confirms that a shared understanding and a clear, agreed-upon outcome have been reached.

## Workflow

1. Identify the topic and scope of the discussion.
2. Resolve or intentionally defer the initial outcome question: use a supplied `outcome` when it is clear; otherwise ask what outcome the user wants unless the discussion is explicitly exploratory, the outcome itself is being discovered, or existing context already provides clear direction.
3. Map the decision tree — identify all decisions and their dependencies.
4. Resolve prerequisite decisions before moving to dependent ones.
5. For each question, present it interactively with a recommended answer and rationale.
6. After each response, append the Q&A to the transcript (see [TRANSCRIPT-FORMAT.md](./TRANSCRIPT-FORMAT.md)).
7. When all material decisions and dependencies have been resolved or explicitly deferred, and before final confirmation, present the user with the following option using the question tool: "Would you like to invoke the `discussion-brainstormer` agent to check for gaps before finalizing?" If the user agrees and the agent is available, invoke it by providing these inputs:

   - **Background detail**: A description of the topic, context, goals, constraints, or any other relevant information provided by the user.
   - **Transcript path**: The path to the `transcript.md` file containing the discussion history.

   These are the only required inputs. If the agent is unavailable, explain that to the user and continue to the final confirmation step. If the agent is invoked, wait for its output and present any gaps as follow-up discussion items.

8. Resolve every gap identified by the brainstormer, or explicitly defer it with the user's agreement. If the user declines the brainstormer or it is unavailable, continue without a brainstormer report.

9. Summarize the shared understanding, including the topic, decisions, dependencies, explicit deferrals, and clear, agreed-upon outcome. Ask the user to explicitly confirm that this understanding is correct, providing a recommended confirmation and a brief rationale. Do not consider the discussion finalized until the user confirms.
