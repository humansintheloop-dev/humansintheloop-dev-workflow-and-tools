Now I have everything I need. Here's the implementation plan:

---

# i2code go invoking implement - Implementation Plan

## Idea Type

**A. User-facing feature** — Adds interactive implementation configuration to the `i2code go` workflow.

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

This feature modifies the `i2code go` orchestrator (`src/i2code/scripts/idea-to-code.sh`) and its helper (`src/i2code/scripts/_helper.sh`) to:

1. Prompt the user for implementation options (interactive/non-interactive, worktree/trunk) before first implementation
2. Persist choices in `<idea-name>-implement-config.yaml`
3. Read the config and pass corresponding CLI flags to `i2code implement`
4. Display active configuration before implementation starts
5. Provide a "Configure implement options" menu item for reconfiguring

All changes are to shell scripts. Steps should be implemented using TDD.

### Key Files

- `src/i2code/scripts/_helper.sh` — file path variables; add `IMPLEMENT_CONFIG_FILE`
- `src/i2code/scripts/idea-to-code.sh` — orchestrator; add prompting, config I/O, display, menu changes
- `test-scripts/test-implement-config.sh` — new test script for config behavior
- `test-scripts/test-end-to-end.sh` — existing test runner; wire in new test script

### Architecture Notes

- `i2code go <dir>` is a Python Click command (`src/i2code/cli.py:47`) that delegates to `src/i2code/scripts/idea-to-code.sh` via `script_command`
- `get_user_choice` (`src/i2code/scripts/idea-to-code.sh:45-89`) displays menu to stderr, reads choice from stdin, returns the choice number via stdout; on EOF it exits the subshell
- The `has_plan` menu and implement invocation are at `src/i2code/scripts/idea-to-code.sh:251-296`
- `_helper.sh` defines file path variables using the pattern `$IDEA_DIR/${IDEA_NAME}-<suffix>`

### Test Strategy

Tests invoke `src/i2code/scripts/idea-to-code.sh` directly with piped input to simulate interactive selections. A mock `i2code` script placed first in `PATH` intercepts `i2code implement` calls and records the arguments to a file. A temporary idea directory in the `has_plan` state (containing `<name>-idea.txt`, `<name>-spec.md`, `<name>-plan.md` with uncompleted tasks) is created for each test case. After the mock `i2code implement` succeeds, the script loops back to the menu, where piped "Exit" input terminates it.

## Steel Thread 1: First-Time and Subsequent Implementation with Config

When a user selects "Implement the entire plan" and no config file exists, they are prompted for implementation options (interactive/non-interactive and worktree/trunk). Their choices are saved to `<idea-name>-implement-config.yaml` and used to invoke `i2code implement` with the corresponding CLI flags. The active configuration is displayed before implementation starts. On subsequent runs where the config already exists, prompting is skipped.

- [x] **Task 1.1: IMPLEMENT_CONFIG_FILE variable defined and test infrastructure wired to CI**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-end-to-end.sh`
  - Observable: `test-implement-config.sh` runs as part of end-to-end tests and exits 0; `IMPLEMENT_CONFIG_FILE` is set to `<idea-dir>/<idea-name>-implement-config.yaml` when `_helper.sh` is sourced
  - Evidence: `./test-scripts/test-end-to-end.sh` includes and runs `test-implement-config.sh`, which sources `_helper.sh` with a test directory and asserts `IMPLEMENT_CONFIG_FILE` matches the expected path
  - Steps:
    - [x] Add `IMPLEMENT_CONFIG_FILE="$IDEA_DIR/${IDEA_NAME}-implement-config.yaml"` to `src/i2code/scripts/_helper.sh` after the `PLAN_WITH_STORIES_FILE` definition (after `src/i2code/scripts/_helper.sh:33`)
    - [x] Create `test-scripts/test-implement-config.sh` with: setup function that creates a temp idea directory (e.g., `/tmp/test-idea-XXXX/my-idea`) with `my-idea-idea.txt`, `my-idea-spec.md`, `my-idea-plan.md` (containing `- [x] Task 1`); teardown function that removes the temp directory; a test case that sources `src/i2code/scripts/_helper.sh` with the temp idea directory and asserts `IMPLEMENT_CONFIG_FILE` equals `<temp-dir>/my-idea/my-idea-implement-config.yaml`
    - [x] Add `"$SCRIPT_DIR/test-implement-config.sh"` to `test-scripts/test-end-to-end.sh` before the integration tests

- [x] **Task 1.2: Selecting "Implement" when no config exists prompts for options and saves config file**
  - TaskType: OUTCOME
  - Entrypoint: `printf '%s\n' 2 2 2 3 | src/i2code/scripts/idea-to-code.sh <idea-dir>` (Implement → Non-interactive → Trunk → Exit)
  - Observable: `<idea-name>-implement-config.yaml` created in the idea directory containing `interactive: false` and `trunk: true`
  - Evidence: `test-scripts/test-implement-config.sh` test case pipes menu selections and prompt choices to `idea-to-code.sh`, then asserts the config file exists with the expected values
  - Steps:
    - [x] Add `prompt_implement_config` function to `src/i2code/scripts/idea-to-code.sh` that uses `get_user_choice` to prompt for: (1) "How should Claude run?" with options "Interactive" (default 1) and "Non-interactive"; (2) "Where should implementation happen?" with options "Worktree (branch + PR)" (default 1) and "Trunk (current branch, no PR)"; sets `IMPLEMENT_INTERACTIVE` to `true`/`false` and `IMPLEMENT_TRUNK` to `false`/`true` based on choices
    - [x] Add `write_implement_config` function to `src/i2code/scripts/idea-to-code.sh` that writes `interactive: $IMPLEMENT_INTERACTIVE` and `trunk: $IMPLEMENT_TRUNK` to `$IMPLEMENT_CONFIG_FILE`
    - [x] In the `has_plan` case branch for option 2 (Implement) at `src/i2code/scripts/idea-to-code.sh:268`, before the `run_step` call, add: if `$IMPLEMENT_CONFIG_FILE` does not exist, call `prompt_implement_config` then `write_implement_config`
    - [x] Add a helper function `create_mock_i2code` to `test-scripts/test-implement-config.sh` that creates a temp directory with a mock `i2code` script; the mock checks if `$1` is `implement`, and if so writes all arguments to `$MOCK_ARGS_FILE` and exits 0
    - [x] Add test case `test_first_run_prompting_saves_config`: set up has_plan directory, create mock, prepend mock to PATH, pipe `printf '%s\n' 2 2 2 3` (Implement, Non-interactive, Trunk, Exit) to `idea-to-code.sh`, assert config file exists, assert it contains `interactive: false`, assert it contains `trunk: true`

- [x] **Task 1.3: Config-driven invocation passes correct flags to i2code implement**
  - TaskType: OUTCOME
  - Entrypoint: `printf '%s\n' 2 3 | src/i2code/scripts/idea-to-code.sh <idea-dir>` (Implement → Exit) with pre-existing config file
  - Observable: `i2code implement` invoked with `--non-interactive --trunk <idea-dir>` when config has `interactive: false` and `trunk: true`; invoked with just `<idea-dir>` when config has default values
  - Evidence: `test-scripts/test-implement-config.sh` test cases create config files with specific values, pipe "Implement → Exit", and assert mock `i2code` received the correct arguments
  - Steps:
    - [x] Add `read_implement_config` function to `src/i2code/scripts/idea-to-code.sh` that reads `$IMPLEMENT_CONFIG_FILE` using `grep`/`sed` to extract `interactive` and `trunk` values into `IMPLEMENT_INTERACTIVE` and `IMPLEMENT_TRUNK` variables; default to `true` for `interactive` and `false` for `trunk` when a value is missing
    - [x] Add `build_implement_flags` function to `src/i2code/scripts/idea-to-code.sh` that echoes `--non-interactive` if `IMPLEMENT_INTERACTIVE` is `false` and `--trunk` if `IMPLEMENT_TRUNK` is `true`
    - [x] In the Implement handler, after the config check/prompting from Task 1.2, call `read_implement_config`; change the invocation at `src/i2code/scripts/idea-to-code.sh:269` from `i2code implement "$dir"` to `i2code implement $(build_implement_flags) "$dir"`
    - [x] Add test case `test_config_with_non_interactive_trunk_passes_flags`: manually create config file with `interactive: false` and `trunk: true`, pipe `printf '%s\n' 2 3` (Implement, Exit), assert mock args file contains `implement --non-interactive --trunk`
    - [x] Add test case `test_config_with_defaults_passes_no_extra_flags`: manually create config file with `interactive: true` and `trunk: false`, pipe `printf '%s\n' 2 3` (Implement, Exit), assert mock args file contains `implement <idea-dir>` with no `--non-interactive` or `--trunk` flags

- [x] **Task 1.4: Active config displayed before implementation and prompting skipped when config exists**
  - TaskType: OUTCOME
  - Entrypoint: `printf '%s\n' 2 3 | src/i2code/scripts/idea-to-code.sh <idea-dir>` (Implement → Exit) with pre-existing config file
  - Observable: stderr output contains "Implementation options:", "Mode: non-interactive", and "Branch: trunk"; stderr does NOT contain "How should Claude run?"
  - Evidence: `test-scripts/test-implement-config.sh` test cases create config, capture stderr, assert display lines present and prompt lines absent
  - Steps:
    - [x] Add `display_implement_config` function to `src/i2code/scripts/idea-to-code.sh` that prints to stderr: `"Implementation options:"`, `"  Mode: interactive"` or `"  Mode: non-interactive"` based on `IMPLEMENT_INTERACTIVE`, `"  Branch: worktree"` or `"  Branch: trunk"` based on `IMPLEMENT_TRUNK`
    - [x] Call `display_implement_config` after `read_implement_config` and before the `run_step` invocation of `i2code implement`
    - [x] Add test case `test_config_display_shown`: create config with `interactive: false` and `trunk: true`, capture stderr from the piped run, assert stderr contains "Implementation options:", "Mode: non-interactive", "Branch: trunk"
    - [x] Add test case `test_no_prompting_when_config_exists`: create config with defaults, capture stderr from the piped run, assert stderr does NOT contain "How should Claude run?" or "Where should implementation happen?"

## Steel Thread 2: Reconfiguring Options

A new "Configure implement options" menu item in the `has_plan` state allows the user to re-enter implementation options and overwrite the existing config file without editing YAML manually.

- [x] **Task 2.1: "Configure implement options" menu item re-prompts and overwrites config**
  - TaskType: OUTCOME
  - Entrypoint: `printf '%s\n' 3 2 2 4 | src/i2code/scripts/idea-to-code.sh <idea-dir>` (Configure → Non-interactive → Trunk → Exit) with pre-existing default config
  - Observable: Config file overwritten with `interactive: false` and `trunk: true`; `has_plan` menu shows 4 options: "Revise the plan", "Implement the entire plan", "Configure implement options", "Exit" with default on option 2
  - Evidence: `test-scripts/test-implement-config.sh` test case creates config with defaults, pipes "Configure → choices → Exit", asserts config file overwritten with new values
  - Steps:
    - [x] Change the `get_user_choice` call in the `has_plan` case at `src/i2code/scripts/idea-to-code.sh:253` to include 4 options: `"Revise the plan" "Implement the entire plan" "Configure implement options" "Exit"` (default remains 2)
    - [x] Add `case 3)` handler that calls `prompt_implement_config` then `write_implement_config`, then continues the loop (the user returns to the menu to select Implement or Exit)
    - [x] Change the Exit handler from `case 3)` to `case 4)` at `src/i2code/scripts/idea-to-code.sh:291`
    - [x] Add test case `test_configure_menu_overwrites_config`: create config with `interactive: true` and `trunk: false`, pipe `printf '%s\n' 3 2 2 4` (Configure, Non-interactive, Trunk, Exit), assert config now has `interactive: false` and `trunk: true`
    - [x] Update ALL existing test cases in `test-scripts/test-implement-config.sh` that pipe "3" for Exit to pipe "4" instead (since Exit moved from option 3 to option 4)

## Steel Thread 3: Fallback for Corrupt or Missing Config

When the config file exists but contains unrecognizable content (neither `interactive:` nor `trunk:` can be parsed), `i2code go` falls back to prompting the user and saves a new valid config file. This ensures the workflow doesn't break if the config is accidentally corrupted.

- [ ] **Task 3.1: Corrupt config file triggers fallback to re-prompting**
  - TaskType: OUTCOME
  - Entrypoint: `printf '%s\n' 2 1 1 4 | src/i2code/scripts/idea-to-code.sh <idea-dir>` (Implement → Interactive → Worktree → Exit) with corrupt config file
  - Observable: Prompting occurs (stderr contains "How should Claude run?"); new valid config file saved with `interactive: true` and `trunk: false`
  - Evidence: `test-scripts/test-implement-config.sh` test cases write corrupt content to config, pipe choices, assert prompting occurred and valid config was created
  - Steps:
    - [ ] Modify the config-exists check in the Implement handler at `src/i2code/scripts/idea-to-code.sh`: instead of just `[ -f "$IMPLEMENT_CONFIG_FILE" ]`, also validate the file is parseable by checking that `read_implement_config` can extract at least one recognized field (`interactive:` or `trunk:`); if the file exists but is unparseable, treat it the same as a missing file (trigger prompting)
    - [ ] Implement the validation by having `read_implement_config` return a non-zero exit code when neither `interactive:` nor `trunk:` is found in the file; the caller checks this return code
    - [ ] Add test case `test_corrupt_config_triggers_reprompting`: write `"not yaml garbage"` to the config file, pipe `printf '%s\n' 2 1 1 4` (Implement, Interactive, Worktree, Exit), capture stderr, assert stderr contains "How should Claude run?", assert config file now has `interactive: true` and `trunk: false`
    - [ ] Add test case `test_empty_config_triggers_reprompting`: write empty file as config, pipe same input, assert prompting occurred and valid config saved
    - [ ] Verify that a config with only one valid field (e.g., `trunk: true` but no `interactive:` line) does NOT trigger re-prompting — instead, `read_implement_config` should use the default for the missing field (this validates the spec requirement: "If a config value is missing from the file, use the default for that value")

---

## Change History
### 2026-02-23 17:01 - mark-step-complete
Added IMPLEMENT_CONFIG_FILE to _helper.sh after PLAN_WITH_STORIES_FILE

### 2026-02-23 17:02 - mark-step-complete
Created test-implement-config.sh with setup, teardown, and assertion

### 2026-02-23 17:02 - mark-step-complete
Added test-implement-config.sh to test-end-to-end.sh before integration tests

### 2026-02-23 17:02 - mark-task-complete
IMPLEMENT_CONFIG_FILE defined, test created, wired to CI

### 2026-02-23 17:13 - mark-step-complete
Added read_implement_config function using sed to extract values from IMPLEMENT_CONFIG_FILE

### 2026-02-23 17:13 - mark-step-complete
Added build_implement_flags function that echoes --non-interactive and --trunk based on config values

### 2026-02-23 17:13 - mark-step-complete
Wired read_implement_config and build_implement_flags into both Implement handler locations

### 2026-02-23 17:13 - mark-step-complete
Added test_config_with_non_interactive_trunk_passes_flags - passes

### 2026-02-23 17:13 - mark-step-complete
Added test_config_with_defaults_passes_no_extra_flags - passes

### 2026-02-23 17:13 - mark-task-complete
Config-driven invocation passes correct flags: --non-interactive when interactive:false, --trunk when trunk:true, no extra flags for defaults

### 2026-02-23 17:19 - mark-task-complete
Added display_implement_config function, called it before implement invocation, and added tests verifying display output and prompting skipped
