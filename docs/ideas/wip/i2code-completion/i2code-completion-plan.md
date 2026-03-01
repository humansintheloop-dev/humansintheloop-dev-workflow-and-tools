Now I have all the context I need. Let me generate the plan.

# i2code Completion — Implementation Plan

## Idea Type

**A. User-facing feature** — CLI usability improvement adding a discoverable `i2code completion` command that wraps Click 8.x built-in shell completion.

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

This plan adds an `i2code completion` command to the existing Click-based Python CLI. The command wraps Click 8.x's built-in shell completion mechanism, making it discoverable via a first-class CLI command instead of requiring users to know the `_I2CODE_COMPLETE` environment variable convention.

**Existing project context:** The `i2code` CLI already exists with a Click command group, pytest test suite, and CI workflow. No new CI configuration or infrastructure is needed — new pytest tests will be auto-discovered by the existing CI pipeline.

**Implementation approach:** All steps should be implemented using TDD. Use Click's `click.shell_completion` module to generate completion scripts. Use `click.Choice` for shell argument validation. Use Click's `CliRunner` for testing.

**Design pattern note:** Before implementing, check `design-pattern-catalog/index.md` for applicable patterns. This feature is a thin wrapper around a framework feature, so no complex patterns are expected.

---

## Steel Thread 1: Generate Shell Completion Script

Implements **US-1 (Scenario 1, Scenario 4)**: User runs `i2code completion <shell>` and gets a valid completion script on stdout for bash, zsh, or fish.

- [ ] **Task 1.1: `i2code completion <shell>` outputs valid shell completion script**
  - TaskType: OUTCOME
  - Entrypoint: `i2code completion zsh`
  - Observable: Outputs valid zsh completion script to stdout, exits with code 0; similarly for `bash` and `fish` with their respective script formats
  - Evidence: Pytest test uses CliRunner to invoke `completion zsh`, asserts exit code 0 and output contains zsh-specific completion markers (e.g., `compdef`); parametrized across all three shells; existing CI runs pytest and passes
  - Steps:
    - [ ] Explore the existing CLI structure: find the main Click group definition, how commands/subcommands are registered, and the CLI entry point name (confirm `_I2CODE_COMPLETE` convention)
    - [ ] Write a failing pytest test in `tests/` that uses `CliRunner` to invoke `['completion', 'zsh']` on the main CLI group and asserts exit code 0 and output contains zsh completion script content
    - [ ] Create `src/i2code/completion.py` with a Click command that accepts a `shell` argument typed as `click.Choice(['bash', 'zsh', 'fish'])` and uses `click.shell_completion` (e.g., `get_completion_class`) to generate and print the completion script to stdout
    - [ ] Register the `completion` command in the main CLI group (follow the existing pattern for how other commands are added)
    - [ ] Run the test and verify it passes
    - [ ] Extend the test to parametrize across `bash`, `zsh`, and `fish`, asserting each produces shell-specific output markers (e.g., bash: `complete -o default`, zsh: `compdef`, fish: `complete -c i2code`)
    - [ ] Run the full test suite to verify no regressions

---

## Steel Thread 2: Discover Completion Setup

Implements **US-2 (Scenario 2)**: User runs `i2code completion` with no arguments and sees usage help with supported shells and installation instructions.

- [ ] **Task 2.1: `i2code completion` with no arguments shows usage help with installation instructions**
  - TaskType: OUTCOME
  - Entrypoint: `i2code completion` (no arguments)
  - Observable: Prints usage message containing supported shell list (`bash`, `zsh`, `fish`) and an installation example (e.g., `eval "$(i2code completion zsh)"`), exits with code 0
  - Evidence: Pytest test uses CliRunner to invoke `['completion']` with no shell argument and asserts exit code 0, output contains all three shell names, and output contains `eval` installation example
  - Steps:
    - [ ] Write a failing pytest test that invokes `['completion']` via CliRunner with no arguments and asserts exit code 0, output contains `bash`, `zsh`, `fish`, and output contains the `eval "$(i2code completion zsh)"` installation example
    - [ ] Make the `shell` argument optional (`required=False`) so Click does not error when no argument is provided
    - [ ] Add a handler in the completion command: when `shell` is `None`, print the usage message per FR-2 (command syntax, supported shells, installation instructions) and return
    - [ ] Run the test and verify it passes
    - [ ] Run the full test suite to verify no regressions

---

## Steel Thread 3: Invalid Shell Argument Feedback

Implements **US-3 (Scenario 3)**: User runs `i2code completion powershell` and gets a clear error listing valid shell choices.

- [ ] **Task 3.1: `i2code completion powershell` shows error listing valid shells**
  - TaskType: OUTCOME
  - Entrypoint: `i2code completion powershell`
  - Observable: Prints error message indicating `powershell` is not a valid choice and lists valid choices (`bash`, `zsh`, `fish`), exits with non-zero status code
  - Evidence: Pytest test uses CliRunner to invoke `['completion', 'powershell']` and asserts non-zero exit code and output contains the valid shell names
  - Steps:
    - [ ] Write a failing pytest test that invokes `['completion', 'powershell']` via CliRunner and asserts non-zero exit code and output contains `bash`, `zsh`, and `fish` as valid choices
    - [ ] Verify that `click.Choice(['bash', 'zsh', 'fish'])` validation already produces the expected error behavior (this should require no additional implementation — Click handles invalid choices automatically)
    - [ ] Run the test and verify it passes
    - [ ] Run the full test suite to verify no regressions
