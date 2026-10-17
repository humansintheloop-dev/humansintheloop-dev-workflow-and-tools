---
name: create-plan
description: Use when creating a steel-thread implementation plan for an idea from its idea, discussion and spec files.
---

# Create Plan

Create a detailed steel-thread implementation plan that will be used by an LLM/GenAI coding agent.
The steps of each task are implemented using TDD.

## Inputs

Locate the idea's files following the `idea-to-code:idea-organization` skill.

1. Read the idea file (`<name>-idea.md`), the discussion file (`<name>-discussion.md`) and the specification file (`<name>-spec.md`).
2. Read the idea's type from the `**Type:**` line of the discussion file, as described in `idea-organization`.
   Do not infer the type from prose.
   When the discussion file has no `**Type:**` line, tell the user that the idea's type is not recorded and ask which of A–D it is before writing the plan.

## Format

The plan follows the `idea-to-code:plan-format` skill: its skeleton, task types, task structure, rules and the verbatim Instructions for Coding Agent block.

---

## Implementation context (CRITICAL)

The implementation agent runs from the project root directory (the working directory).

**Path rules:**
- All file paths must be relative to the project root
- Use `./docker-compose.yml` or `docker-compose.yml`, NOT the full path from the spec/idea file location
- Use `./scripts/init.sh`, NOT `tests/foo/scripts/init.sh`
- The idea directory path is irrelevant—do NOT include it in paths

**Command rules:**
- Commands execute from the project root—no `cd <project-dir> &&` prefix needed
- Use `docker compose up` NOT `cd tests/foo && docker compose up`
- Use `./scripts/test.sh` NOT `cd tests/foo && ./scripts/test.sh`

**Do NOT:**
- Include the idea/spec file directory path in any file paths or commands
- Create tasks to create the project root directory (it already exists)

---

## Analyze existing code BEFORE planning (CRITICAL)

Before writing any plan, examine the existing codebase to understand what already exists:

1. **Read project structure:** build configuration, module/package layout, existing source directories
2. **Read existing source files:** identify which classes, functions, and tests already exist and what state they are in
3. **Read existing infrastructure:** CI workflows, Dockerfiles, deployment configs, test scripts
4. **Identify placeholder vs. real content:** skeleton-generated code often has boilerplate that needs to be fleshed out — not replaced from scratch

**Plan tasks must reflect what actually exists:**
- If a file exists with placeholder content → plan to **modify/flesh out** the file, not create it
- If CI, Dockerfile, or build config already exists → do NOT plan to create them again
- If Steel Thread 1 infrastructure (build, CI, deployment) already works → Steel Thread 1 should verify it builds, not recreate it
- Use "flesh out", "update", "modify" language for existing files — reserve "create" for files that genuinely don't exist

**Plan tasks must only cover what the idea/spec defines:**
- Only plan work for adapters, events, entities, and operations that appear in the spec or referenced YAML files
- Do NOT invent operations (e.g., `updateX`) or events (e.g., `XUpdated`) that are not defined in the source of truth
- Do NOT plan work for adapter types the service does not have (e.g., no web-api adapter → no REST controller tasks)

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

Task 1.1 is special. It MUST ensure CI exists so that every commit after Task 1.1 is validated.

**WHY:** If CI is created in Task 1.2, Task 1.1's commit is unvalidated—this defeats the purpose of steel threads.

**If the project already has a working build and CI** (e.g., generated from a skeleton/template), Task 1.1 should verify the existing build passes — not recreate infrastructure that already exists. In this case, Task 1.1 may be as simple as running the build and confirming all existing tests pass.

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

## Goal

The final plan should be a sequence of steel threads, each with clearly defined
tasks and steps that a coding LLM can follow to implement the idea incrementally,
starting from the initial setup thread through all chosen scenarios.

Tasks must be outcome-driven, testable via the entrypoint, and structured so
that unused code and unused tests cannot exist.
