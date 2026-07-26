# Interview Process

Conduct a thorough, decision-driven interview until all decisions have been made and all dependencies have been resolved.

## Core Principles

- Interview the user about every relevant aspect of the topic until all decisions are made and all dependencies are resolved.
- Explore each branch of the decision tree systematically, resolving prerequisite decisions before moving to dependent ones.
- Ask only one question at a time, and wait for the user's response before asking the next question. Never ask multiple questions in a single message.
- For every question, provide a recommended answer along with a brief rationale to help guide the discussion.
- If a required piece of information is an objective fact that can be discovered by exploring the environment (such as the filesystem, repository, documentation, tools, or configuration), retrieve it yourself instead of asking the user.
- Only ask the user to make subjective decisions, preferences, trade-offs, or requirements that cannot be determined automatically.

## Completion Gate

Do not begin implementation or execute any task until the user explicitly confirms that a shared understanding has been reached.

## Workflow

1. Identify the topic and scope of the discussion.
2. Map the decision tree — identify all decisions and their dependencies.
3. Resolve prerequisite decisions before moving to dependent ones.
4. For each question, present it interactively with a recommended answer and rationale.
5. After each response, append the Q&A to the transcript (see [TRANSCRIPT-FORMAT.md](./TRANSCRIPT-FORMAT.md)).
6. When no significant decisions remain unresolved, present the user with the following option using the question tool: "Would you like to invoke the `discussion-brainstormer` agent to check for gaps before finalizing?" If the user agrees, invoke the agent by providing these inputs:

   - **Background detail**: A description of the topic, context, goals, constraints, or any other relevant information provided by the user.
   - **Transcript path**: The path to the `transcript.md` file containing the discussion history.

   These are the only required inputs. Wait for the brainstormer's output, then present any gaps as follow-up discussion items. Only consider the discussion finalized once all gaps have been resolved or explicitly deferred.