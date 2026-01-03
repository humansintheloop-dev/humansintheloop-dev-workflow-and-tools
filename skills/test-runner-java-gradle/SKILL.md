---
name: test-runner-java-gradle
description: a definition of tests and testing in a Java project using Gradle and JUnit 5
---

# Skill: Project Test Runner (Java + Gradle, macOS, JUnit 5 Only)

This skill defines what a “test” is and how tests are executed for this Java project.
It is designed to be used together with a TDD skill that determines *when* tests must run.

Language: Java  
Test framework: JUnit 5 (Jupiter)  
Test runner: always `./gradlew test` (macOS only)  
Detailed test output: XML files under `build/test-results/test/TEST-*.xml`

---

## 1. Definition of a Test

A test in this project is:

- A Java method annotated with `@org.junit.jupiter.api.Test`
- Located in a test class under the directory `src/test/java`
- Part of a test class following normal JUnit 5 structure

Examples of valid test locations (inline only):
- `src/test/java/com/example/MyServiceTest.java`
- `src/test/java/com/example/domain/OrderProcessorTest.java`

A new behavior is defined by:
- Adding a new `@Test` method to an existing JUnit 5 test class, or
- Creating a new test class under `src/test/java` that contains one or more `@Test` methods

JUnit 5 assertions (e.g., `Assertions.assertEquals`, `assertThrows`) should be used.

No Kotlin and no JUnit 4 are present in this project.

---

## 2. Running Tests (macOS only)

When the TDD skill instructs the agent to "run the tests", the agent must execute:

`./gradlew test`

This command must be run from the project root (the directory containing `gradlew`).

### Gradle Daemon

Do not use the `--no-daemon` flag with Gradle commands unless specifically troubleshooting daemon issues. The Gradle daemon improves build performance by keeping the JVM warm between builds.

Exit code meaning:
- Exit code 0 → all tests passed
- Non-zero exit code → tests failed or tests could not run due to build errors

The console output of Gradle indicates only overall success or failure, not individual test results.

---

## 3. Detailed Test Results (XML)

Detailed per-test results are always located in:

`build/test-results/test/TEST-*.xml`

Each XML file corresponds to a test class and contains:
- `<testsuite>` metadata such as total tests and failures
- `<testcase classname="..." name="...">` elements
- Optional `<failure>` elements that contain the failure message and stack trace snippet

The agent must extract:
- The first failing test class name
- The failing test method name
- The failure message text
- A useful stack trace snippet if present

This information must be used to explain why tests failed and guide the next RED → GREEN change.

---

## 4. Evidence Integration (for the TDD skill)

The TDD skill uses an Evidence block with fields:
- `tests: pass | fail | not-run`
- `last_output: <text>`

This Test Runner skill defines how to populate those fields.

When tests pass:
- `tests: pass`
- `last_output` should mention that `./gradlew test` exited with code 0

When tests fail:
- `tests: fail`
- `last_output` should mention that `./gradlew test` exited with a non-zero code
- The agent must parse XML files (from `build/test-results/test/`) and describe the failing test(s)

When tests cannot run (environment error):
- `tests: not-run`
- `last_output` should say that Gradle could not be executed
- The agent must enter the BLOCKED state (as defined by the TDD skill)

---

## 5. Rules for the Coding Agent

1. The agent must always run tests using exactly: `./gradlew test`
2. The agent must not guess test results from reading code
3. The agent must never claim tests passed without real `./gradlew test` output
4. The agent must parse XML under `build/test-results/test` to identify failing tests
5. If Gradle cannot be run, the agent must enter BLOCKED and request user-provided output
6. The agent must not move to GREEN, VERIFY, or COMPLETE without real evidence

## 6. Test Failure Investigation

NEVER ignore test failures. When tests fail:

- **STOP** and investigate the cause before proceeding
- **Do NOT assume** the cause based on error message alone (e.g., "TimeoutException means Kafka isn't running")
- **Do NOT dismiss** failures as "infrastructure not running" without verification
- **Do NOT proceed** with commits or other work until failures are understood and resolved
- **Check test infrastructure** - many tests use testcontainers which auto-start dependencies

### After Fixing a Failing Test

When a test fails (whether from pre-commit hook, CI, or manual run):

1. Fix the test or the code causing the failure
2. Run the specific failing test to verify the fix
3. Only after the test passes, proceed with staging and committing

Never assume a fix is correct without running the test to verify.

---

## 7. Summary

- Tests are JUnit 5 `@Test` methods in Java only  
- Tests are executed exclusively via `./gradlew test` on macOS  
- Exit code indicates pass/fail at a high level  
- Detailed failures live in `build/test-results/test/TEST-*.xml`  
- The agent must never guess test results and must always rely on real output

# End of Java + Gradle Test Runner Skill
