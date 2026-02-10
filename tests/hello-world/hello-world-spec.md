# HelloWorld Java — Didactic Example Specification

## Learning Goals

1. **Project structure** — Understand the standard directory layout for a Gradle-based Java project (`src/main/java`, `src/test/java`, `build.gradle`).
2. **Build automation** — Learn how Gradle (Groovy DSL) compiles, tests, and packages a Java application.
3. **Unit testing** — Write and run a JUnit 5 test that verifies program output.
4. **Continuous integration** — Set up a GitHub Actions workflow that builds the project and runs tests on every push.

## Concepts and Patterns the Example Must Demonstrate

| Concept | How It Is Demonstrated |
|---|---|
| Java application entry point | A `main` method in a `HelloWorld` class that prints a greeting to stdout |
| Gradle project configuration | A `build.gradle` file that declares the `java` and `application` plugins, sets Java 21 toolchain, and configures JUnit 5 |
| Standard source layout | `src/main/java/com/example/helloworld/` for production code, `src/test/java/com/example/helloworld/` for tests |
| JUnit 5 unit test | A test class that captures stdout and asserts the greeting message |
| GitHub Actions CI | A `.github/workflows/ci.yml` that checks out code, sets up Java 21, and runs `./gradlew build` |

## Capabilities and Constraints

### Capabilities

- Run the application with `./gradlew run` and see "Hello, World!" printed to the console.
- Run the test suite with `./gradlew test` and see a passing JUnit 5 test.
- Push to GitHub and observe the CI workflow build and test the project.

### Constraints

- **Java version:** 21 (current LTS).
- **Build tool:** Gradle with Groovy DSL. The project includes the Gradle wrapper (`gradlew` / `gradlew.bat`) so no local Gradle installation is required.
- **Package:** `com.example.helloworld`.
- **No external dependencies** beyond JUnit 5 (test scope).
- **Single module** — no multi-project build.

### Default Assumptions

- The Gradle wrapper version should be current and stable.
- The `application` plugin is used so `./gradlew run` works out of the box.
- The CI workflow triggers on pushes to all branches and on pull requests to the default branch.

## End-to-End Example Flows

### Primary Scenario: Build, Test, and Run Locally

1. User clones the repository.
2. User runs `./gradlew build` — Gradle compiles the source, runs the JUnit 5 test, and produces a build artifact.
3. User runs `./gradlew run` — the application prints `Hello, World!` to stdout.
4. User runs `./gradlew test` — the test suite passes, confirming the output is correct.

### Secondary Scenario: CI Pipeline on Push

1. User pushes a commit to GitHub.
2. GitHub Actions triggers the CI workflow.
3. The workflow checks out the code, sets up Java 21, and runs `./gradlew build`.
4. The build succeeds and tests pass — the workflow reports a green status.

### Exploratory Scenario: Modify and Verify

1. User changes the greeting message in `HelloWorld.java`.
2. User runs `./gradlew test` — the test fails because the expected output no longer matches.
3. User updates the test to match the new greeting.
4. User runs `./gradlew test` — the test passes again.

## Scenarios Supporting a Steel-Thread Plan

The following scenarios are candidates for ordering into a steel-thread implementation plan (to be created in a subsequent step):

1. **Minimal compilable project** — `build.gradle` + `HelloWorld.java` compiles with `./gradlew build`.
2. **Runnable application** — `./gradlew run` prints `Hello, World!`.
3. **Tested application** — A JUnit 5 test verifies the output; `./gradlew test` passes.
4. **CI pipeline** — A GitHub Actions workflow runs `./gradlew build` and reports success.
