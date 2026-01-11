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
  - Ensure that the Git repository is setup with proper .gitignore
- Subsequent steel threads must implement exactly ONE scenario each:
  - If idea type A (user-facing feature):
    - Each steel thread implements exactly one user-story scenario.
  - If idea type B/C/D (architecture POC, platform capability, educational example):
    - Each steel thread implements exactly one validation scenario or example scenario.
- Implement happy-path scenarios first, then add error handling and edge cases.
- Organize the steel threads by causal dependencies and architectural priority.
- Build test scripts incrementally: each task should add its test case to the test script as part of that task, not as a separate "create test" task at the end. This ensures tests are written BEFORE implementations.
- When appropriate, incrementally update the README.md as part of each task - DO NOT HAVE a separate "update documentation" task at the end.

Structure of the plan:

- The plan is a markdown document in the same directory as @${IDEA_FILE}.
- The plan MUST include an "Instructions for Coding Agent" section at the top that tells the agent to:
  - IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.
  - ALWAYS Use the `idea-to-code:plan-tracking` skill to track task completion
  - ALWAYS Write code using TDD
    - Use the `idea-to-code:tdd` skill when implementing code
    - NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test (`src/test/java/**/*.java`)
    - Before using the Write tool on any `.java` file in `src/main/`, ask: "Do I have a failing test for this?" If not, write the test first.
    - When building something that requires scripting, never run the scripts or ad-hoc docker/curl/test commands that modify the state (e.g. start/stop containers etc.) directly. Always update the test script first, then run the test script. After the test script fails, you can inspect run ad-hoc commands to inspect the current state (e.g. examine logs, check container status, etc.) but do NOT modify the system state outside of the test script.
    - When task direction changes mid-implementation, return to TDD PLANNING state and write a test first
  - ALWAYS after completing a task, when the tests pass and the task has been marked as complete, commit the changes.

## Test-First Task Structure

For infrastructure/scripting steel threads:
- Do NOT create a separate "Create test script" task at the end
- Each implementation task implicitly includes: (1) add failing test, (2) implement to make it pass
- Name tasks by the observable outcome, not the implementation artifact


### Example: Bad task structure (test comes after implementations):

```
- Task 1.1: Create init-ca.sh script
- Task 1.2: Create stepca service
- Task 1.3: Create test script  ← Wrong
```

### Example: Good task structure (outcome-focused, test is implicit in each):

```
- Task 1.1: init-ca.sh creates CA and .env file
- Task 1.2: stepca service starts and becomes healthy
```

## Task Granularity Guidelines

When defining tasks:

- **Meaningful tasks** represent independently testable, deliverable units of functionality
- **NOT standalone tasks**: DTOs, helper classes, utility methods, configuration files - these are implementation details of larger tasks
- **Good task**: "Implement LocationController REST endpoint" (includes creating any DTOs, request/response objects needed)
- **Bad task**: "Create CreateLocationRequest DTO" (too granular, not independently valuable)
- A good heuristic: Would you make a separate git commit for just this task? If not, it's probably not a standalone task.

## TDD Enforcement

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
