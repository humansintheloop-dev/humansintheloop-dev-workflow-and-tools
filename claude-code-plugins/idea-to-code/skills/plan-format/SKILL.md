---
name: plan-format
description: Use when writing, revising or repairing an implementation plan file (<name>-plan.md).
---

# Plan Format

An implementation plan is a sequence of steel threads, each containing tasks with steps.
It is read directly by an LLM/GenAI coding agent (for example, Claude Code).
Separate skills control TDD execution and task progression, so the plan does NOT need
to restate how to do TDD/BDD or how to mark tasks complete.

## Plan skeleton

Every plan has these sections, in this order:

```markdown
# Implementation Plan: <title>

## Idea Type

**C. Platform/infrastructure capability** — <one-sentence rationale>

## Instructions for Coding Agent
...(verbatim block, see "Instructions for Coding Agent block" below)...

## Overview
...

## Steel Thread 1: <description>
...

## Change History
```

`# Implementation Plan:`, `## Idea Type` and `## Overview` are the headings i2code reads.
Copy the `## Idea Type` letter and name from the `**Type:**` line of the discussion file, as described in `idea-to-code:idea-organization`.

---

## Task model (IMPORTANT)

A task has **two layers**:

1. **Task contract** – why the task exists (externally observable)
2. **Task steps** – how the task is implemented (internal details)

Tasks MUST define their contract explicitly.
Internal work (helpers, parsing, DTOs, utilities, configuration files)
MUST appear only as steps under a task with a contract.
They MUST NOT be standalone tasks.

---

## Task types (strict definitions)

Every task MUST declare exactly one TaskType.
Allowed values are: OUTCOME, INFRA, REFACTOR.
No other task types are permitted.

### OUTCOME

Introduces or changes externally observable behavior reachable from the primary entrypoint.

An OUTCOME task MUST define:
- Entrypoint: exact CLI command or execution path
- Observable: stdout, stderr, exit code, file, branch, PR, etc.
- Evidence: the test/command that proves the observable via the entrypoint

Observable descriptions must be precise and testable.
If an Observable mentions creation, modification, or selection of state
(files, directories, branches, worktrees, PRs),
it must specify the key properties that distinguish correct behavior
(e.g. path, branch name, idempotence, ownership).

### INFRA

Enables building, testing, or running the system, but does not introduce user-visible behavior by itself.

INFRA tasks MUST still define:
- Entrypoint
- Observable
- Evidence

INFRA tasks MUST create test scripts following the `testing-scripts-and-infrastructure` skill:
- Create `test-scripts/test-*.sh` scripts for infrastructure behaviors
- If you need to test more infrastructure behavior OR another end-to-end flow, create a new script—do NOT append to an existing one
- Add new test scripts to `test-scripts/test-end-to-end.sh`
- GitHub Actions workflow MUST call `test-scripts/test-end-to-end.sh`
- Manual verification instructions are NOT valid Evidence

**Shell scripts vs JUnit tests:**
- JUnit integration tests thoroughly verify REST endpoints (all CRUD operations, validation, error handling)
- Shell scripts are smoke tests for Docker/infrastructure—verify the deployment works, not the application logic
- Do NOT create shell scripts that mirror JUnit tests (no `test-create-customer.sh`, `test-get-customer.sh`, etc.)
- ONE shell script with a simple end-to-end flow (e.g., POST then GET) is sufficient to prove the containerized app works
- Additional shell scripts are only for testing different infrastructure behaviors (e.g., `test-docker-health.sh`, `test-docker-crud-smoke.sh`)

INFRA tasks MUST NOT introduce business logic except as required to enable execution.

### REFACTOR

Changes code structure without changing behavior.

REFACTOR tasks:
- MUST reference existing OUTCOME behavior
- MUST state Observable: “no behavior change”
- MUST use existing tests as Evidence
- MUST appear only after at least one OUTCOME task in the same steel thread

---

## Steel thread heading format (MANDATORY)

Steel thread headings MUST use this exact format:

```
## Steel Thread N: Description
```

Example:
```
## Steel Thread 1: Spring Boot Application with Health Check
## Steel Thread 2: Create Customer Endpoint
```

Do NOT use `## Thread N:` — it must be `## Steel Thread N:`.

---

## Task structure (MANDATORY FORMAT)

Each task MUST use this exact format, with `TaskType:` set to exactly one of `OUTCOME`, `INFRA` or `REFACTOR`:

```markdown
- [ ] **Task X.Y: Outcome-oriented description**
  - TaskType: OUTCOME
  - Entrypoint: `<command>`
  - Observable: <what is observed>
  - Evidence: `<command>`
  - Steps:
    - [ ] <step>
```

Rules:
- Tasks MUST use checkbox format (`- [ ] **Task X.Y:**`), NOT markdown headers (`### Task X.Y:`)
- Entrypoint, Observable, and Evidence MUST NOT be empty.
- Do NOT use placeholders such as “N/A”.
- If you cannot define Entrypoint, Observable, and Evidence for a task,
  that task must not exist.

## Code reference formatting in steps

- File references: use relative path with suffix, wrapped in backticks — e.g., `src/i2code/implement/cli.py`
- Location references: use relative path:linenumber, wrapped in backticks — e.g., `src/i2code/implement/cli.py:55`
- Do NOT use bare filenames (e.g., `cli.py`) or separate "(line N)" annotations

## Evidence requirements (IMPORTANT)

Evidence is not a description of a test; it is a concrete command or test that proves
the Observable occurred **as a result of running the Entrypoint**.

Evidence MUST follow these rules:

- Evidence MUST invoke the Entrypoint.
- Evidence MUST fail if the Entrypoint is not executed.
- Evidence MUST validate the specific Observable stated for the task.
- Evidence MUST NOT rely solely on checking existing state that could have been created earlier.

For stateful operations (files, directories, git branches, worktrees, PRs):

- Evidence must show causality:
  - run the Entrypoint
  - then assert the expected state exists or changed
- If idempotence is a requirement, Evidence must demonstrate it
  (for example: running the Entrypoint twice does not create duplicates).

Invalid Evidence examples:
- Checking git state without invoking the Entrypoint
- Unit tests of helper functions
- Assertions that could pass even if the Entrypoint was never run

Valid Evidence examples:
- `command && assert-state`
- End-to-end tests that invoke the CLI and verify results

---

## Test-first task structure

- Do NOT create separate “create test” tasks.
- Each task implicitly includes:
  - writing a failing test
  - implementing code to make it pass
- Name tasks by the observable outcome, not the implementation artifact.

### Bad example:

```
- Task 1.1: Create init-ca.sh script
- Task 1.2: Create stepca service
- Task 1.3: Create test script
```

### Good example:

```
- Task 1.1: init-ca.sh creates CA and .env file
- Task 1.2: stepca service starts and becomes healthy
```

---

## No ambiguous alternatives in tasks or steps

Tasks and steps MUST NOT contain "X or Y", "X (or Y)", or "X / Y" alternatives.
Every decision must be resolved at plan-creation time so the coding agent has a
single unambiguous action to take.

- **Bad**: `Add re-export shim OR delete the old file if grep confirms no imports`
- **Good**: `Delete the old file (grep confirms no remaining imports)`
- **Bad**: `Write test in tests/foo/test_bar.py (or new tests/baz/test_bar.py)`
- **Good**: `Write test in tests/baz/test_bar.py`
- **Bad**: `Add function build_spec_prompt() (or similar) to prompt_builder.py`
- **Good**: `Add function build_spec_prompt() to prompt_builder.py`

If you cannot decide between alternatives without more information, investigate
first (e.g., grep for imports, check existing file structure) and then commit
to one option.

---

## Task granularity guidelines

- Meaningful tasks represent independently testable, deliverable units of functionality.
- NOT standalone tasks: DTOs, helper classes, utility methods, config files.
  - These MUST be listed only as steps under a task with a contract.
- Good task: “Implement LocationController REST endpoint”
- Bad task: “Create CreateLocationRequest DTO”
- Heuristic: Would you make a separate git commit for just this task?
  If not, it is not a standalone task.

---

## Instructions for Coding Agent block (MUST BE INCLUDED VERBATIM)

Every plan MUST contain the following section unchanged, immediately after the
`## Idea Type` section, exactly as written:

```markdown
## Instructions for Coding Agent

- IMPORTANT: Use simple commands that you have permission to execute. Avoid complex commands that may fail due to permission issues.

### Required Skills

Use these skills by invoking them before the relevant action:

| Skill | When to Use |
|-------|-------------|
| `idea-to-code:plan-tracking` | ALWAYS - track task completion in the plan file |
| `idea-to-code:tdd` | When implementing code - write failing tests first |
| `idea-to-code:commit-guidelines` | Before creating any git commit |
| `idea-to-code:incremental-development` | When writing multiple similar files (tests, classes, configs) |
| `idea-to-code:testing-scripts-and-infrastructure` | When building shell scripts or test infrastructure |
| `idea-to-code:dockerfile-guidelines` | When creating or modifying Dockerfiles |
| `idea-to-code:file-organization` | When moving, renaming, or reorganizing files |
| `idea-to-code:debugging-ci-failures` | When investigating CI build failures |
| `idea-to-code:test-runner-java-gradle` | When running tests in Java/Gradle projects |

### TDD Requirements

- NEVER write production code (`src/main/java/**/*.java`) without first writing a failing test
- Before using Write on any `.java` file in `src/main/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output
```

---

## Revisions

- Make structural changes (insert, delete, reorder or renumber threads and tasks) with the `idea-to-code:plan-file-management` skill.
- Record every change requested in a conversation under `## Change History`, the last section of the plan.
  Add one entry per change, headed `### YYYY-MM-DD: <brief description>`, stating what changed and why.
