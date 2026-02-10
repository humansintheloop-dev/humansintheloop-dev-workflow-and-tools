Now I have all the skill guidance. Let me generate the plan.

---

# HelloWorld Java — Steel-Thread Implementation Plan

## Idea Type

**D. Educational/example repo** — This is a didactic example demonstrating Java project structure, Gradle build automation, JUnit 5 testing, and GitHub Actions CI.

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

## Overview

This plan implements a HelloWorld Java application as a didactic example, organized into steel threads that each deliver a narrow, independently testable slice of functionality. The project uses Gradle (Groovy DSL), Java 21, JUnit 5, and GitHub Actions CI.

All steps should be implemented using TDD.

---

## Steel Thread 1: Minimal Compilable Project with CI

**Goal:** Prove the build pipeline works end-to-end — a Java application compiles, tests pass, and CI validates every commit.

- [ ] **Task 1.1: Gradle project compiles and CI validates the build**
  - TaskType: INFRA
  - Entrypoint: `./gradlew build`
  - Observable: Gradle compiles the Java source, runs JUnit 5 tests, and exits successfully. CI workflow runs `./gradlew build` on push.
  - Evidence: CI runs `./gradlew build` which executes JUnit tests and passes
  - Steps:
    - [ ] Initialize the Gradle wrapper using `gradle wrapper --gradle-version 8.11.1`
    - [ ] Create `build.gradle` with the `java` and `application` plugins, Java 21 toolchain, JUnit 5 dependency (`testImplementation 'org.junit.jupiter:junit-jupiter:5.11.3'`), and `test { useJUnitPlatform() }` configuration. Set `mainClass` to `com.example.helloworld.HelloWorld`
    - [ ] Create `settings.gradle` with `rootProject.name = 'hello-world'`
    - [ ] Add `.gitignore` for Gradle/Java projects (`.gradle/`, `build/`, `*.class`, etc.)
    - [ ] Create a JUnit 5 test `src/test/java/com/example/helloworld/HelloWorldTest.java` that captures stdout and asserts the output contains `Hello, World!` (this test will initially fail — TDD RED)
    - [ ] Create `src/main/java/com/example/helloworld/HelloWorld.java` with a `main` method that prints `Hello, World!` to stdout (TDD GREEN)
    - [ ] Create `.github/workflows/ci.yml` using the GitHub Actions Gradle template: `actions/checkout@v4`, `actions/setup-java@v4` with Java 21 temurin, `gradle/actions/setup-gradle@v4`, and `./gradlew build`
    - [ ] Verify `./gradlew build` passes locally

---

## Steel Thread 2: Application is Runnable via Gradle

**Goal:** Demonstrate that `./gradlew run` executes the application and prints the greeting — the primary educational scenario.

- [ ] **Task 2.1: `./gradlew run` prints "Hello, World!" to stdout**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew run`
  - Observable: Running `./gradlew run` prints `Hello, World!` to stdout
  - Evidence: `./gradlew run` exits 0 and output contains `Hello, World!`; JUnit test in Task 1.1 already validates the output programmatically via `./gradlew build`
  - Steps:
    - [ ] Verify `build.gradle` already has the `application` plugin and `mainClass` configured (from Task 1.1)
    - [ ] Run `./gradlew run` and confirm `Hello, World!` appears in stdout
    - [ ] Update `README.md` with project description, prerequisites (Java 21), and instructions for `./gradlew build`, `./gradlew run`, and `./gradlew test`

---

## Steel Thread 3: Exploratory Scenario — Modify and Verify

**Goal:** Demonstrate the TDD feedback loop — changing the greeting breaks the test, updating the test makes it pass again.

- [ ] **Task 3.1: Changing the greeting message causes the test to fail, and updating the test restores a green build**
  - TaskType: OUTCOME
  - Entrypoint: `./gradlew build`
  - Observable: After changing the greeting in `HelloWorld.java` to `Hello, Gradle!`, `./gradlew test` fails. After updating `HelloWorldTest.java` to expect `Hello, Gradle!`, `./gradlew build` succeeds. The final committed state has matching greeting and test.
  - Evidence: `./gradlew build` passes with the updated greeting and updated test assertion
  - Steps:
    - [ ] Change the greeting message in `HelloWorld.java` from `Hello, World!` to `Hello, Gradle!`
    - [ ] Run `./gradlew test` and observe the test failure (demonstrates the safety net)
    - [ ] Update `HelloWorldTest.java` to assert the output contains `Hello, Gradle!`
    - [ ] Run `./gradlew build` and confirm all tests pass
