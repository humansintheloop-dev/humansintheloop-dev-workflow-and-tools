# Reimplement `claude-issue-report` — Implementation Plan

## Idea Type

**C. Platform/infrastructure capability** — Re-implements an existing capability (issue reporting) as a skill + CLI subcommand pair, following the project's established architectural pattern.

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

- NEVER write production code (`src/i2code/**/*.py`) without first writing a failing test
- Before using Write on any `.py` file in `src/i2code/`, ask: "Do I have a failing test?" If not, write the test first
- When task direction changes mid-implementation, return to TDD PLANNING state and write a test first

### Verification Requirements

- Hard rule: NEVER git commit, git push, or open a PR unless you have successfully run the project's test command and it exits 0
- Hard rule: If running tests is blocked for any reason (including permissions), ALWAYS STOP immediately. Print the failing command, the exact error output, and the permission/path required
- Before committing, ALWAYS print a Verification section containing the exact test command (NOT an ad-hoc command - it must be a proper test command such as `./test-scripts/*.sh`, `./scripts/test.sh`, or `./gradlew build`/`./gradlew check`), its exit code, and the last 20 lines of output

---

## Steel Thread 1: CLI `i2code issue create` Happy Path

Creates the core CLI command that reads JSON from stdin and writes a correctly formatted issue file. This proves the central capability works end-to-end from CLI invocation to file output.

Implement using TDD.

- [x] **Task 1.1: `i2code issue create` accepts JSON on stdin and creates a correctly formatted issue file**
  - TaskType: OUTCOME
  - Entrypoint: `echo '{"description":"Test issue","category":"rule-violation","analysis":"## 5 Whys Analysis\n\n1. Why?","context":"## Context (Last 5 Messages)\n\nUser: test","suggestion":"Add a rule"}' | uv run i2code issue create --session-id test-session-123`
  - Observable: A markdown file is created in `.hitl/issues/active/` with filename `YYYY-MM-DD-HH-MM-SS.md`, containing correct YAML frontmatter (`id`, `created`, `status: active`, `category: rule-violation`, `claude_session_id: test-session-123`) and all content sections (`# Test issue`, `## 5 Whys Analysis`, `## Context`, `## Suggested improvement`, `## Resolution`). The absolute path to the file is printed to stdout.
  - Evidence: Pytest unit tests in `tests/issue/` using Click's `CliRunner` with `input=` for stdin, writing to `tmp_path`, asserting file content, frontmatter fields, and stdout output. Run via `./test-scripts/test-unit.sh`.
  - Steps:
    - [x] Create `tests/issue/__init__.py` and `tests/issue/test_create.py` with a happy-path test: invoke `create` via `CliRunner` with valid JSON stdin and `--session-id`, assert exit code 0, file exists in target dir, frontmatter has correct fields, content sections present, stdout contains absolute path
    - [x] Create `src/i2code/issue/__init__.py` (empty package init)
    - [x] Create `src/i2code/issue/create.py` with issue creation logic: parse JSON from stdin, validate required fields, generate timestamp-based ID, render markdown template, write file to `.hitl/issues/active/`, return absolute path
    - [x] Create `src/i2code/issue/cli.py` with Click group `issue` and `create` subcommand that reads stdin, accepts optional `--session-id`, calls creation logic, prints path to stdout
    - [x] Modify `src/i2code/cli.py` to import and register the `issue` command group via `main.add_command(issue)`
    - [x] Add test for missing `--session-id` flag: file is created with `claude_session_id: unknown`

- [x] **Task 1.2: `i2code issue create` smoke test validates CLI is registered and callable**
  - TaskType: INFRA
  - Entrypoint: `./test-scripts/test-subcommands-smoke.sh`
  - Observable: `uv run i2code issue --help` lists `create`, and `uv run i2code issue create --help` exits 0
  - Evidence: `./test-scripts/test-subcommands-smoke.sh` passes with the new smoke test assertions. Run via `./test-scripts/test-end-to-end.sh`.
  - Steps:
    - [x] Add `i2code issue --help` and `i2code issue create --help` assertions to `test-scripts/test-subcommands-smoke.sh`, following the existing pattern

## Steel Thread 2: CLI Input Validation and Error Handling

Adds error handling for all invalid input scenarios. Each error case produces a descriptive message on stderr and exits with code 1.

Implement using TDD.

- [x] **Task 2.1: CLI rejects invalid input with descriptive error messages**
  - TaskType: OUTCOME
  - Entrypoint: `echo '{"description":"test"}' | uv run i2code issue create` (missing required fields)
  - Observable: CLI exits with code 1 and prints descriptive error to stderr for each case: missing required field (`description`, `category`, `analysis`, `context`, `suggestion`), invalid category value, malformed JSON, and missing `.hitl/issues/active/` directory (mentioning `i2code tracking setup`)
  - Evidence: Pytest unit tests in `tests/issue/test_create.py` using `CliRunner`, asserting exit code 1 and stderr content for each error case. Run via `./test-scripts/test-unit.sh`.
  - Steps:
    - [x] Add test: JSON missing `description` field → exit 1, stderr mentions missing field
    - [x] Add test: JSON with `category: "foo"` → exit 1, stderr lists valid categories (`rule-violation`, `improvement`, `confusion`)
    - [x] Add test: malformed JSON on stdin → exit 1, stderr mentions invalid JSON
    - [x] Add test: `.hitl/issues/active/` directory doesn't exist → exit 1, stderr mentions `i2code tracking setup`
    - [x] Implement validation logic in `src/i2code/issue/create.py` to handle all error cases

## Steel Thread 3: PreToolUse Hook Injects Session ID

Creates the PreToolUse hook that transparently appends `--session-id` to `i2code issue create` commands when Claude Code provides a session ID.

Implement using TDD.

- [x] **Task 3.1: PreToolUse hook appends `--session-id` to `i2code issue create` commands**
  - TaskType: OUTCOME
  - Entrypoint: `echo '{"tool_name":"Bash","tool_input":{"command":"echo ... | i2code issue create"},"session_id":"abc123"}' | node claude-code-plugins/idea-to-code/hooks/issue-session-injector.js`
  - Observable: Hook outputs modified tool input JSON with `--session-id abc123` appended to the command. For non-matching commands (e.g., `git status`), commands without `session_id`, and commands that already contain `--session-id`, the hook exits 0 without modifying the command.
  - Evidence: Node.js unit tests in `claude-code-plugins/idea-to-code/hooks/issue-session-injector.test.js` following the `enforce-bash-conventions.test.js` pattern (using `assert` module). Run via `./test-scripts/test-plugin-javascript.sh`.
  - Steps:
    - [x] Create `claude-code-plugins/idea-to-code/hooks/issue-session-injector.test.js` with tests: (1) injects session ID into matching command, (2) no session_id → passes through unchanged, (3) non-matching command → passes through, (4) already has `--session-id` → not appended twice
    - [x] Create `claude-code-plugins/idea-to-code/hooks/issue-session-injector.js` implementing the PreToolUse hook: check `tool_name === 'Bash'`, check command contains `i2code issue create`, check `session_id` present and command doesn't already have `--session-id`, append `--session-id <id>`, output modified tool input JSON

## Steel Thread 4: Skill Definition and Migration

Creates the skill, updates plugin configuration, and removes the old slash command and PostToolUse hook.

- [ ] **Task 4.1: Create `claude-issue-report` skill definition**
  - TaskType: OUTCOME
  - Entrypoint: Invoke `/claude-issue-report` in Claude Code
  - Observable: Claude Code loads the skill from `claude-code-plugins/idea-to-code/skills/claude-issue-report/SKILL.md`, which instructs Claude to perform 5 whys analysis and pipe JSON to `i2code issue create`
  - Evidence: Skill file exists with correct frontmatter (`name: claude-issue-report`, `description`, `user-invokable: true`) and contains instructions for: extracting description, identifying persona, performing 5 whys analysis, extracting last 5 messages, suggesting improvement, piping JSON to CLI, and reporting the file path. Verified by inspection and by the E2E test in Task 4.3.
  - Steps:
    - [ ] Create `claude-code-plugins/idea-to-code/skills/claude-issue-report/SKILL.md` with frontmatter and step-by-step instructions matching the spec's C1 section. Include auto-suggest guidance and post-filing behavior.
    - [ ] Reference the JSON schema from the spec: `description`, `category`, `analysis`, `context`, `suggestion`
    - [ ] Include the invocation pattern: `echo '<json>' | i2code issue create`

- [ ] **Task 4.2: Update `plugin.json` and delete old artifacts**
  - TaskType: INFRA
  - Entrypoint: `cat claude-code-plugins/idea-to-code/.claude-plugin/plugin.json`
  - Observable: `plugin.json` references `claude-issue-report` skill directory, has PreToolUse entry for `issue-session-injector.js`, does NOT reference `claude-issue-report.md` command or `issue-session-tagger.js` hook. Old files `commands/claude-issue-report.md` and `hooks/issue-session-tagger.js` no longer exist.
  - Evidence: `./test-scripts/test-end-to-end.sh` passes (existing tests still work after migration). Manual inspection confirms old files are deleted and `plugin.json` is updated.
  - Steps:
    - [ ] Modify `claude-code-plugins/idea-to-code/.claude-plugin/plugin.json`: add `skills/claude-issue-report` to `skills` array, add PreToolUse entry for `issue-session-injector.js` with `"matcher": "Bash"`, remove `commands/claude-issue-report.md` from `commands`, remove `issue-session-tagger.js` from PostToolUse hooks
    - [ ] Delete `claude-code-plugins/idea-to-code/commands/claude-issue-report.md`
    - [ ] Delete `claude-code-plugins/idea-to-code/hooks/issue-session-tagger.js`
    - [ ] Run `./test-scripts/test-end-to-end.sh` to verify nothing is broken

- [ ] **Task 4.3: End-to-end test validates full pipeline (skill → hook → CLI → file)**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/issue/test_e2e.py -v -m integration_claude`
  - Observable: A pytest test runs `claude -p "/claude-issue-report Test issue: wrong commit format"` in a temp git repo with `.hitl/issues/active/`, and verifies: exactly one `.md` file created, valid YAML frontmatter with `status: active` and valid `category`, contains `## 5 Whys Analysis`, `## Context (Last 5 Messages)`, `## Suggested improvement`, `## Resolution` sections, `claude_session_id` is not `unknown`
  - Evidence: `uv run python3 -m pytest tests/issue/test_e2e.py -v -m integration_claude` passes. This test is excluded from fast CI runs via the `integration_claude` marker.
  - Steps:
    - [ ] Create `tests/issue/test_e2e.py` with `@pytest.mark.integration_claude` marker
    - [ ] Test sets up temp git repo with `.hitl/issues/active/` directory, runs `claude -p` subprocess, asserts file creation and content per spec section T4

---

## Change History
### 2026-03-18 16:19 - mark-step-complete
Created tests/issue/__init__.py and tests/issue/test_create.py with 7 tests

### 2026-03-18 16:19 - mark-step-complete
Created empty src/i2code/issue/__init__.py

### 2026-03-18 16:19 - mark-step-complete
Created src/i2code/issue/create.py with JSON parsing, validation, template rendering, and file writing

### 2026-03-18 16:19 - mark-step-complete
Created src/i2code/issue/cli.py with Click group and create subcommand

### 2026-03-18 16:19 - mark-step-complete
Registered issue command group in src/i2code/cli.py

### 2026-03-18 16:19 - mark-step-complete
Added test for missing --session-id defaulting to unknown

### 2026-03-18 16:19 - mark-task-complete
All steps complete, 7 tests pass, full suite passes (1357 tests)

### 2026-03-18 16:35 - mark-step-complete
Test: missing description field exits with error

### 2026-03-18 16:35 - mark-step-complete
Test: invalid category lists valid values

### 2026-03-18 16:35 - mark-step-complete
Test: malformed JSON exits with error

### 2026-03-18 16:35 - mark-step-complete
Test: missing active directory mentions i2code tracking setup

### 2026-03-18 16:35 - mark-step-complete
Wrapped json.JSONDecodeError with descriptive Invalid JSON message

### 2026-03-18 16:35 - mark-task-complete
All 8 validation tests pass, 1365 total tests pass

### 2026-03-18 16:42 - mark-task-complete
Implemented issue-session-injector hook with tests
