Now I have everything I need. Here is the plan:

---

# Edit Idea in Visual Studio Code — Implementation Plan

## Idea Type: A (User-facing feature)

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

Modify `src/i2code/scripts/brainstorm-idea.sh` to resolve the editor using a priority chain (`code --wait` > `$VISUAL` > `$EDITOR` > `vi`) and use `.md` file extension when VS Code is selected. The change is confined to `brainstorm-idea.sh`; no changes to `_helper.sh`, prompt templates, or the brainstorm session behavior.

### Key files

| File | Role |
|------|------|
| `src/i2code/scripts/brainstorm-idea.sh` | Production code — editor resolution and idea file creation |
| `src/i2code/scripts/_helper.sh` | **No changes** — already supports both `.txt` and `.md` via glob detection |
| `test-scripts/test-editor-resolution.sh` | New test script for editor resolution scenarios |
| `test-scripts/test-end-to-end.sh` | Add test-editor-resolution.sh invocation |

### Testing approach

`brainstorm-idea.sh` invokes external commands (`code`, `vi`, `claude`, `uuidgen`) that are unavailable or interactive in CI. Each test case:

1. Creates a temporary directory with a `mock-bin/` containing mock scripts for `code`, `claude`, `uuidgen`, and/or `vi`
2. Prepends `mock-bin/` to `PATH` (and removes real `code` from PATH for fallback tests)
3. Runs `brainstorm-idea.sh <temp-dir>`
4. Asserts the observable outcome: file extension, placeholder content, and which mock was invoked (mocks write a marker file recording their invocation arguments)

---

## Steel Thread 1: VS Code Editor Resolution

When `code` is found on `$PATH` and no idea file exists, `brainstorm-idea.sh` creates a `.md` idea file with placeholder content and opens it with `code --wait`.

- [x] **Task 1.1: brainstorm-idea.sh opens idea file in VS Code as .md when code is on PATH**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-editor-resolution.sh`
  - Observable: When `code` is found on `$PATH` and no idea file exists, brainstorm-idea.sh creates `<name>-idea.md` (not `.txt`) with content `PLEASE DESCRIBE YOUR IDEA` and invokes `code --wait <file>`
  - Evidence: `test-editor-resolution.sh` creates mock `code` (records invocation args to a marker file) and mock `claude` (no-op), runs `brainstorm-idea.sh` with a temp idea directory, asserts: (1) idea file has `.md` extension, (2) file contains placeholder text, (3) mock `code` marker shows `--wait` was passed
  - Steps:
    - [x] Create `test-scripts/test-editor-resolution.sh` with a test case for the VS Code scenario: set up mock `code` and `claude` in a temp `mock-bin/`, prepend to `PATH`, run `brainstorm-idea.sh`, assert `.md` extension and `--wait` flag
    - [x] Add `test-editor-resolution.sh` to `test-scripts/test-end-to-end.sh`
    - [x] Modify `src/i2code/scripts/brainstorm-idea.sh`: inside the `if ! ls "$IDEA_FILE"` block, add editor resolution logic — detect `code` on `PATH` using `command -v code`, override `IDEA_FILE` to use `.md` extension, invoke `code --wait "$IDEA_FILE"` instead of `vi "$IDEA_FILE"`; preserve `vi` as the else fallback

## Steel Thread 2: Environment Variable Editor Fallback

When `code` is not on `$PATH`, fall back to `$VISUAL` then `$EDITOR` with `.txt` extension, matching standard Unix editor conventions.

- [x] **Task 2.1: brainstorm-idea.sh uses $VISUAL editor when code is not on PATH**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-editor-resolution.sh`
  - Observable: When `code` is NOT on `$PATH` and `$VISUAL` is set, brainstorm-idea.sh creates `<name>-idea.txt` with placeholder content and invokes the `$VISUAL` command with the idea file path
  - Evidence: `test-editor-resolution.sh` includes a test case that uses a `PATH` with no `code` command, sets `VISUAL` to a mock editor script, runs `brainstorm-idea.sh`, asserts: (1) idea file has `.txt` extension, (2) mock `VISUAL` editor marker shows it was invoked with the file path
  - Steps:
    - [x] Add `$VISUAL` test case to `test-scripts/test-editor-resolution.sh`: create mock `VISUAL` editor script, exclude `code` from `PATH`, set `VISUAL` env var, run `brainstorm-idea.sh`, assert `.txt` and `VISUAL` editor invocation
    - [x] Add `$VISUAL` fallback to `src/i2code/scripts/brainstorm-idea.sh`: `elif` branch after `code` check that uses `$VISUAL` when set and non-empty

- [x] **Task 2.2: brainstorm-idea.sh uses $EDITOR when code and $VISUAL are not available**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-editor-resolution.sh`
  - Observable: When `code` is NOT on `$PATH`, `$VISUAL` is not set, and `$EDITOR` is set, brainstorm-idea.sh creates `<name>-idea.txt` with placeholder content and invokes the `$EDITOR` command with the idea file path
  - Evidence: `test-editor-resolution.sh` includes a test case with no `code` on `PATH`, `VISUAL` unset, `EDITOR` set to a mock editor script, asserts: (1) `.txt` extension, (2) mock `EDITOR` marker shows it was invoked
  - Steps:
    - [x] Add `$EDITOR` test case to `test-scripts/test-editor-resolution.sh`: exclude `code`, unset `VISUAL`, set `EDITOR` to mock, run `brainstorm-idea.sh`, assert `.txt` and `EDITOR` invocation
    - [x] Add `$EDITOR` fallback to `src/i2code/scripts/brainstorm-idea.sh`: `elif` branch after `$VISUAL` check that uses `$EDITOR` when set and non-empty

## Steel Thread 3: vi Fallback Backward Compatibility

When no other editor is available (no `code`, no `$VISUAL`, no `$EDITOR`), fall back to `vi` with `.txt` extension — preserving identical behavior to today.

- [x] **Task 3.1: brainstorm-idea.sh falls back to vi when no editor preferences exist**
  - TaskType: OUTCOME
  - Entrypoint: `./test-scripts/test-editor-resolution.sh`
  - Observable: When `code` is NOT on `$PATH`, `$VISUAL` is not set, and `$EDITOR` is not set, brainstorm-idea.sh creates `<name>-idea.txt` with placeholder content and invokes `vi`
  - Evidence: `test-editor-resolution.sh` includes a test case with no `code` on `PATH`, `VISUAL` unset, `EDITOR` unset, mock `vi` on `PATH`, asserts: (1) `.txt` extension, (2) file contains placeholder text, (3) mock `vi` marker shows it was invoked with the file path
  - Steps:
    - [x] Add vi fallback test case to `test-scripts/test-editor-resolution.sh`: create sanitized `PATH` with only mock `vi` and `claude` (no `code`), unset `VISUAL` and `EDITOR`, run `brainstorm-idea.sh`, assert `.txt` extension and mock `vi` invocation
    - [x] Verify `brainstorm-idea.sh` vi fallback is the final `else` branch (should already be correct from Thread 1)

---

## Change History
### 2026-02-21 15:14 - mark-step-complete
Added $VISUAL test case to test-editor-resolution.sh

### 2026-02-21 15:14 - mark-step-complete
Added elif branch for $VISUAL fallback in brainstorm-idea.sh

### 2026-02-21 15:14 - mark-task-complete
brainstorm-idea.sh uses $VISUAL editor when code is not on PATH — test passes

### 2026-02-21 15:19 - mark-step-complete
Added $EDITOR test case to test-editor-resolution.sh

### 2026-02-21 15:19 - mark-step-complete
Added $EDITOR elif branch to brainstorm-idea.sh

### 2026-02-21 15:19 - mark-task-complete
brainstorm-idea.sh falls back to $EDITOR when code and $VISUAL are not available; test passes

### 2026-02-21 15:23 - mark-task-complete
Added vi fallback test case; verified vi is the final else branch
