Now I have a thorough understanding of the codebase. Let me generate the plan.

---

# Implementation Plan: Commit Uncommitted Changes Before Implement

## Idea Type

**Type A: User-facing feature** — Enhances the interactive `i2code go` workflow with a new menu option and git status check.

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
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./test-scripts/test-end-to-end.sh`, or `uv run --python 3.12 python3 -m pytest tests/ -v -m unit`), its exit code, and the last 20 lines of output

## Overview

This feature modifies `src/i2code/scripts/idea-to-code.sh` to detect uncommitted changes in the idea directory when the workflow reaches the `has_plan` state, and to offer a "Commit changes" menu option (as the default) before proceeding to implementation. The commit is performed via `git add` and `git commit` on the idea directory.

**Key files:**
- `src/i2code/scripts/idea-to-code.sh` — the main orchestrator script (lines 251-296 handle the `has_plan` state)
- `src/i2code/scripts/_helper.sh` — sets environment variables like `IDEA_DIR`, `IDEA_NAME`, etc.

**Architecture:**
- `i2code go <dir>` is a Click command that delegates to `idea-to-code.sh` via `script_runner.py`
- The shell script has a `detect_state()` function, a `get_user_choice()` menu function, a `handle_error()` retry pattern, and a main loop
- Tests: unit tests use pytest with `pytest.mark.unit`; shell script behavior is tested via `test-scripts/`

**Approach:**
- Extract a `has_uncommitted_changes()` function in `idea-to-code.sh` that runs `git status --porcelain -- "$dir"` and returns 0 (true) when changes exist
- Modify the `has_plan` case to conditionally show different menus based on `has_uncommitted_changes`
- Extract a `commit_idea_changes()` function that runs `git add "$dir"` followed by `git commit -m "Add idea docs for $IDEA_NAME" -- "$dir"`
- Use the existing `handle_error` pattern for commit failures
- Steps should be implemented using TDD

## Steel Thread 1: Detect Uncommitted Changes and Show Dynamic Menu

This steel thread implements the primary scenario (S-1): when the user has a plan and uncommitted changes exist, the menu shows "Commit changes" as the default. After committing, the next iteration shows "Implement" as the default.

- [x] **Task 1.1: `has_plan` menu shows "Commit changes" as default when idea directory has uncommitted changes**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go <test-idea-directory>` (simulated via automated input to `idea-to-code.sh`)
  - Observable: When the idea directory has a plan file and uncommitted changes (staged, unstaged, or untracked), the menu displays four options: "Revise the plan", "Commit changes [default]", "Implement the entire plan", "Exit". When there are no uncommitted changes, the menu displays the original three options with "Implement the entire plan [default]".
  - Evidence: Shell test script `test-scripts/test-go-commit-menu.sh` creates a temporary git repo, sets up an idea directory in `has_plan` state with uncommitted changes, runs `idea-to-code.sh` with piped input selecting "Exit", and asserts the menu output contains "Commit changes [default]". A second test case with all files committed asserts the menu output contains "Implement the entire plan [default]" and does NOT contain "Commit changes".
  - Steps:
    - [x] Create `test-scripts/test-go-commit-menu.sh` with two test cases: (1) uncommitted changes present — asserts "Commit changes [default]" appears in menu output; (2) no uncommitted changes — asserts "Implement the entire plan [default]" appears and "Commit changes" does NOT appear. Each test case sets up a temp git repo with an idea directory containing `*-idea.md`, `*-spec.md`, `*-plan.md` files, then pipes the "Exit" choice number into `idea-to-code.sh` and captures stderr output (menus are written to stderr).
    - [x] Add `test-scripts/test-go-commit-menu.sh` to `test-scripts/test-end-to-end.sh`
    - [x] Add a `has_uncommitted_changes()` function to `src/i2code/scripts/idea-to-code.sh` that runs `git status --porcelain -- "$1"` and returns 0 if output is non-empty (changes exist), 1 otherwise
    - [x] Modify the `has_plan)` case in `src/i2code/scripts/idea-to-code.sh` (starting at line 251): check `has_uncommitted_changes "$dir"` and conditionally show either the 4-option menu (with "Commit changes [default]" at position 2) or the original 3-option menu (with "Implement the entire plan [default]" at position 2)

- [x] **Task 1.2: Selecting "Commit changes" runs `git add`/`git commit` and loops back**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go <test-idea-directory>` (simulated via automated input to `idea-to-code.sh`)
  - Observable: When the user selects "Commit changes", the script runs `git add "$dir"` followed by `git commit -m "Add idea docs for $IDEA_NAME" -- "$dir"`. After a successful commit, the workflow loops back and on the next iteration (if no more uncommitted changes remain) shows the normal menu with "Implement" as default.
  - Evidence: Shell test script `test-scripts/test-go-commit-action.sh` creates a temporary git repo with uncommitted idea files, pipes input selecting "Commit changes" then "Exit" on the next iteration, and asserts: (1) the idea files are committed (verified via `git status`), (2) the commit message follows the expected format, (3) the second iteration's menu output shows "Implement the entire plan [default]" (not "Commit changes").
  - Steps:
    - [x] Create `test-scripts/test-go-commit-action.sh` that: sets up a temp git repo with uncommitted idea files in `has_plan` state; pipes input "2" (Commit changes) followed by "3" (Exit on next iteration) into `idea-to-code.sh`; asserts the idea files are committed via `git log` and `git status`; asserts the commit message matches the expected format; asserts the second menu iteration shows "Implement the entire plan [default]"
    - [x] Add `test-scripts/test-go-commit-action.sh` to `test-scripts/test-end-to-end.sh`
    - [x] Add a `commit_idea_changes()` function to `src/i2code/scripts/idea-to-code.sh` that runs `git add "$1"` followed by `git commit -m "Add idea docs for $IDEA_NAME" -- "$dir"`
    - [x] In the `has_plan)` case, when uncommitted changes exist and the user selects option 2, call `commit_idea_changes "$dir"` and if successful, `continue` the loop (which triggers re-detection and a fresh menu)

- [ ] **Task 1.3: User can skip commit and implement directly when uncommitted changes exist**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go <test-idea-directory>` (simulated via automated input to `idea-to-code.sh`)
  - Observable: When uncommitted changes exist and the user selects option 3 ("Implement the entire plan") instead of option 2 ("Commit changes"), implementation proceeds without committing idea files. The `i2code implement` command is invoked.
  - Evidence: Shell test script `test-scripts/test-go-skip-commit.sh` creates a temp git repo with uncommitted idea files in `has_plan` state, stubs `i2code` to record calls, pipes input "3" (Implement) into `idea-to-code.sh`, and asserts that `i2code implement` was invoked and idea files remain uncommitted.
  - Steps:
    - [ ] Create `test-scripts/test-go-skip-commit.sh` that: sets up a temp git repo with uncommitted idea files in `has_plan` state; stubs `i2code` command on PATH to record arguments and exit 0; pipes input "3" (Implement the entire plan) into `idea-to-code.sh`; asserts the stub recorded an `implement` invocation; asserts idea files are still uncommitted
    - [ ] Add `test-scripts/test-go-skip-commit.sh` to `test-scripts/test-end-to-end.sh`
    - [ ] Verify the `has_plan)` case with uncommitted changes handles option 3 as "Implement the entire plan" — this should already work from Task 1.1's menu restructuring, but confirm the case numbering maps correctly (option 3 in the 4-option menu maps to implement)

## Steel Thread 2: Commit Failure Handling

This steel thread implements scenario S-4: when the `git add`/`git commit` fails, the user is offered "Retry" or "Abort workflow" via the existing `handle_error` pattern.

- [ ] **Task 2.1: Commit failure triggers retry/abort prompt via `handle_error`**
  - TaskType: OUTCOME
  - Entrypoint: `i2code go <test-idea-directory>` (simulated via automated input to `idea-to-code.sh`)
  - Observable: When the user selects "Commit changes" and the `git commit` exits non-zero, the script calls `handle_error` which presents "Retry" or "Abort workflow". Selecting "Abort workflow" exits with code 1.
  - Evidence: Shell test script `test-scripts/test-go-commit-failure.sh` creates a temp git repo with uncommitted idea files, stubs `git` to fail on `commit` subcommand, pipes input selecting "Commit changes" then "Abort workflow", and asserts the script exits with code 1 and the output contains "Retry" and "Abort workflow".
  - Steps:
    - [ ] Create `test-scripts/test-go-commit-failure.sh` that: sets up a temp git repo with uncommitted idea files in `has_plan` state; stubs `git` to exit 1 on `commit` subcommand (pass-through for other subcommands); pipes input "2" (Commit changes) then "2" (Abort workflow from `handle_error` menu) into `idea-to-code.sh`; asserts exit code is 1; asserts output contains "Retry" and "Abort workflow"
    - [ ] Add `test-scripts/test-go-commit-failure.sh` to `test-scripts/test-end-to-end.sh`
    - [ ] In the `has_plan)` case, wrap the `commit_idea_changes` call with the existing `handle_error` pattern: if the command fails, call `handle_error` and if the user selects Retry, `continue` the loop; if Abort, exit. Follow the same pattern used by other steps (e.g., lines 176-182 in `src/i2code/scripts/idea-to-code.sh`)

## Change History

- **2026-02-22**: Replaced `claude -p "Commit the changes in the <idea-directory>"` with direct `git add "$dir"` + `git commit -m "Add idea docs for $IDEA_NAME" -- "$dir"`. Updated spec (FR-3, FR-5, S-1, S-4) and plan (overview, approach, tasks 1.2, 1.3, 2.1) to remove all `claude -p` references. Rationale: simpler, no dependency on Claude for a straightforward git operation.

### 2026-02-23 11:37 - mark-step-complete
Created test-scripts/test-go-commit-menu.sh with two test cases

### 2026-02-23 11:37 - mark-step-complete
Added test-go-commit-menu.sh to test-end-to-end.sh

### 2026-02-23 11:37 - mark-step-complete
Added has_uncommitted_changes() function

### 2026-02-23 11:37 - mark-step-complete
Modified has_plan case with conditional 4-option/3-option menu

### 2026-02-23 11:38 - mark-task-complete
Menu shows Commit changes [default] when uncommitted changes exist, original menu when clean

### 2026-02-23 11:44 - mark-task-complete
Test and implementation complete: commit_idea_changes() function extracted, continue added on success, all 6 tests pass
