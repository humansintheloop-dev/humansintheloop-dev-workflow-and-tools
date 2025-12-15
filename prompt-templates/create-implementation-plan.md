== Step 3: Create plan

Given the idea, specification, and (when applicable) user-stories files in @${IDEA_FILE} @${SPEC_FILE}, create a detailed steel-thread implementation plan that will be used by an LLM/GenAI coding agent.

The plan will be read directly by an LLM/GenAI coding agent (for example, Claude Code).
Separate skills control TDD execution and task progression, so the plan does NOT need to restate how to do TDD/BDD or how to mark tasks complete.
It should note that the steps should be implemented using TDD.


First, determine the idea type from the specification:

- A. User-facing feature
- B. Architecture POC
- C. Platform/infrastructure capability
- D. Educational/example repo

General principles:

- Each steel thread is one very narrow end-to-end flow that delivers some value.
- The first steel thread must set up the project:
  - Use recommended starter/template/skeletons for the technology stack.
  - Set up an automated deployment pipeline (e.g., GitHub Actions) that builds and tests the application.
  - If applicable, the pipeline should also deploy the application.
- Subsequent steel threads must implement exactly ONE scenario each:
  - If idea type A (user-facing feature):
    - Each steel thread implements exactly one user-story scenario.
  - If idea type B/C/D (architecture POC, platform capability, educational example):
    - Each steel thread implements exactly one validation scenario or example scenario.
- Implement happy-path scenarios first, then add error handling and edge cases.
- Organize the steel threads by causal dependencies and architectural priority.
- Build test scripts incrementally: each steel thread should add its relevant test cases to the test script rather than creating all tests in a final steel thread. This ensures tests are verified as functionality is implemented.

Structure of the plan:

- The plan is a markdown document in the same directory as @${IDEA_FILE}.
- For the stories file called '<idea-name>-stories.md', call the plan file '<idea-name>-story-plan.md'.
- The plan MUST include an "Instructions for Coding Agent" section at the top that tells the agent to:
  - Use the `idea-to-code:plan-tracking` skill to track task completion
  - Use the `idea-to-code:tdd` skill when implementing code
  - Test functionality by running test scripts rather than doing the equivalent of manual testing, such as executing complex shell commands.

Steel thread and task structure:

- A steel thread consists of a hierarchy of tasks.
- Each task implements a meaningful chunk of functionality:
  - Lowest-level tasks implement software elements (class, function, module, endpoint, etc.).
  - Higher-level tasks compose lower-level tasks into larger elements (package, service, workflow).
- Each task consists of a series of steps.

Format and checklists:

- Represent each steel thread as a top-level markdown section (for example, `## Steel thread 1 – <short description>`).
- Under each steel thread, define one or more tasks.
- Each task must start with a checkbox `[ ]` followed by a short, imperative task name.
- Each task's steps should be listed underneath as indented checklist items, each starting with `[ ]`.
- Do NOT include instructions about how to run TDD/BDD or how to mark items as completed; those behaviors are handled by separate skills.
- Do NOT wrap tasks or threads in code blocks; the agent will read them directly from the markdown plan.

Goal:

- The final plan should be a sequence of steel threads, each with clearly defined tasks and steps that a coding LLM can follow to implement the idea incrementally from the first setup thread through all chosen scenarios.
- The steps should be small, concrete, and ordered so they are suitable for a TDD-oriented coding workflow, but you do not need to describe the TDD mechanics explicitly.
