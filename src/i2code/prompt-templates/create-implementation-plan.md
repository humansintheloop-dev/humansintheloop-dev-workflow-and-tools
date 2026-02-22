# Create plan

Given the idea, specification, and (when applicable) user-stories files in
@${IDEA_FILE} @${SPEC_FILE}, create a detailed steel-thread implementation plan
that will be used by an LLM/GenAI coding agent.

The plan will be read directly by an LLM/GenAI coding agent (for example, Claude Code).
Separate skills control TDD execution and task progression, so the plan does NOT need
to restate how to do TDD/BDD or how to mark tasks complete.
It should note that the steps should be implemented using TDD.

IMPORTANT: Output the plan to stdout in MARKDOWN format only. DO NOT WRITE A FILE

---

## Skills to Follow

Before generating the plan, invoke and follow the guidance from these skills:
${PLAN_SKILLS}

Ensure the generated plan incorporates the requirements from each skill.

---

## Idea type

First, determine the idea type from the specification:

- A. User-facing feature
- B. Architecture POC
- C. Platform/infrastructure capability
- D. Educational/example repo

---

## Implementation context (CRITICAL)

The implementation agent runs from the project root directory (the working directory).

**Path rules:**
- All file paths must be relative to the project root
- Use `./docker-compose.yml` or `docker-compose.yml`, NOT the full path from the spec/idea file location
- Use `./scripts/init.sh`, NOT `tests/foo/scripts/init.sh`
- The directory path in `@${IDEA_FILE}` is irrelevant—do NOT include it in paths

**Command rules:**
- Commands execute from the project root—no `cd <project-dir> &&` prefix needed
- Use `docker compose up` NOT `cd tests/foo && docker compose up`
- Use `./scripts/test.sh` NOT `cd tests/foo && ./scripts/test.sh`

**Do NOT:**
- Include the idea/spec file directory path in any file paths or commands
- Create tasks to create the project root directory (it already exists)

---

## General principles

- Each steel thread is one very narrow end-to-end flow that delivers some value.
- **Steel Thread 1 MUST prove three things work together** before adding features:
  1. End-to-end flow through application architecture (e.g., REST → Service → DB)
  2. Deployment pipeline (CI validates all commits)
  3. Deployment architecture (e.g., Docker, docker-compose)
  - Use recommended starter/template/skeletons for the technology stack
  - Do NOT add multiple features before proving all three work together
  - Rationale: Catch integration issues immediately, not after building features that may all fail
  - Ensure proper .gitignore; add only minimal dependencies required for each task
  - See **Task 1.1 Requirements** section below for mandatory contents
- Subsequent steel threads implement exactly ONE scenario each:
  - If idea type A (user-facing feature):
    - Each steel thread implements exactly one user-story scenario.
  - If idea type B/C/D (architecture POC, platform capability, educational example):
    - Each steel thread implements exactly one validation scenario or example scenario.
- Implement happy-path scenarios first, then add error handling and edge cases.
- Organize the steel threads by causal dependencies and architectural priority.
- Build test scripts incrementally: each task includes adding its failing test as part of that task.
- When appropriate, incrementally update README.md as part of tasks.
  - Do NOT create a separate "update documentation" task at the end.

### Incremental build-up (dependencies, directories, configuration)

Add dependencies, directories, and configuration only when a task requires them—not upfront.

**Dependencies:**
- **Bad**: Task 1.1 adds all dependencies (web, JPA, validation, testcontainers, actuator)
- **Good**: Task 1.1 adds only spring-boot-starter-web; Task 2.1 adds JPA + testcontainers when persistence is needed

**Directories:**
- **Bad**: Task 1.1 creates entire project structure (domain/, repository/, service/, controller/)
- **Good**: Task 1.1 creates only the application entry point; Task 2.1 creates domain/ when adding entities

**Dockerfiles for Gradle/Maven projects:**
- Use simple Dockerfiles that copy a pre-built JAR (built by CI or locally)
- Do NOT use multi-stage builds that run Gradle/Maven inside Docker unless explicitly requested
- Multi-stage builds are slow (re-downloads dependencies) and complicate caching

This keeps each task focused and makes it clear why each element exists.

---

## Task 1.1 Requirements (MANDATORY)

Task 1.1 is special. It MUST include `.github/workflows/ci.yml` so that every commit after Task 1.1 is validated by CI.

**WHY:** If CI is created in Task 1.2, Task 1.1's commit is unvalidated—this defeats the purpose of steel threads.

### For Java/Gradle Projects

Task 1.1 MUST include:
1. Application entry point with health check endpoint
2. JUnit test that verifies the health endpoint (e.g., `@SpringBootTest` with `TestRestTemplate`)
3. `.github/workflows/ci.yml` that runs `./gradlew build`

**Evidence:** "CI runs `./gradlew build` which executes JUnit tests and passes"

IMPORTANT: Do NOT create shell scripts to test Java applications. Use JUnit tests executed by Gradle.

### For Java/Gradle Projects with Docker Compose

When Task 1.1 includes both Java app AND Docker Compose infrastructure, Task 1.1 MUST include:
1. Application entry point with health check endpoint
2. JUnit test that verifies the health endpoint
3. `test-scripts/test-cleanup.sh` for cleaning up Docker state
4. `test-scripts/test-docker-health.sh` that runs `docker compose up`, curls health, runs `docker compose down`
5. `test-scripts/test-end-to-end.sh` that runs cleanup then all test scripts
6. `.github/workflows/ci.yml` that runs `./gradlew build` AND `./test-scripts/test-end-to-end.sh`

**Evidence:** "CI runs `./gradlew build` and `./test-scripts/test-end-to-end.sh` and both pass"

### For Infrastructure-Only Projects (no Java)

Task 1.1 MUST include:
1. The infrastructure scripts/configuration
2. `test-scripts/test-cleanup.sh` for cleaning up test state
3. `test-scripts/test-<behavior>.sh` that validates the behavior
4. `test-scripts/test-end-to-end.sh` that runs cleanup then all test scripts
5. `.github/workflows/ci.yml` that runs `./test-scripts/test-end-to-end.sh`

**Evidence:** "CI runs `./test-scripts/test-end-to-end.sh` and passes"

### Task 1.1 Anti-patterns (INVALID)

```
❌ Task 1.1: Create Spring Boot app
   Task 1.2: Add CI workflow
   (CI not in Task 1.1 - Task 1.1 commit is unvalidated)
```

```
❌ Task 1.1: Create Spring Boot app with health check
   Steps:
     - Create test-scripts/test-health.sh that curls the health endpoint
   (WRONG: Java apps must use JUnit tests, not shell scripts)
```

```
❌ Task 1.1: Create app with health check
   Steps:
     - Create CustomerServiceApplicationTest.java with @SpringBootTest context load test
   (Step tests context loading, not the health endpoint - doesn't match Observable)
```

### Valid Task 1.1 Example (Java/Gradle)

```
- [ ] **Task 1.1: Spring Boot application starts and responds to health check**
  - TaskType: INFRA
  - Entrypoint: `./gradlew build`
  - Observable: Health endpoint returns 200 OK with `{"status":"UP"}`
  - Evidence: CI runs `./gradlew build` which executes JUnit tests and passes
  - Steps:
    - [ ] Create `build.gradle` with Spring Boot, web, actuator, test dependencies
    - [ ] Create application entry point and health configuration
    - [ ] Create `HealthCheckTest.java` that uses TestRestTemplate to GET /actuator/health and asserts 200 with status UP
    - [ ] Create `.github/workflows/ci.yml` that runs `./gradlew build`
```

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

Each task MUST use this exact format:

- [ ] **Task X.Y: Outcome-oriented description**
  - TaskType: OUTCOME | INFRA | REFACTOR
  - Entrypoint:
  - Observable:
  - Evidence:
  - Steps:
    - [ ] ...

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

## Task granularity guidelines

- Meaningful tasks represent independently testable, deliverable units of functionality.
- NOT standalone tasks: DTOs, helper classes, utility methods, config files.
  - These MUST be listed only as steps under a task with a contract.
- Good task: “Implement LocationController REST endpoint”
- Bad task: “Create CreateLocationRequest DTO”
- Heuristic: Would you make a separate git commit for just this task?
  If not, it is not a standalone task.

---

## Goal

The final plan should be a sequence of steel threads, each with clearly defined
tasks and steps that a coding LLM can follow to implement the idea incrementally,
starting from the initial setup thread through all chosen scenarios.

Tasks must be outcome-driven, testable via the entrypoint, and structured so
that unused code and unused tests cannot exist.

---

## Instructions section (MUST BE INCLUDED VERBATIM)

Every generated plan MUST include the following section at the top, after the
Idea Type section, exactly as written:

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
